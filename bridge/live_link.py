#!/usr/bin/env python3
"""Bounded same-user Unix-socket transport for LOUKSNA's local bridge.

Never exposes a TCP port, arbitrary shell, sudo, screenshots or privileged
operations. GitHub/SSH access is a separately authenticated external hop.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import hashlib
import os
from pathlib import Path
import signal
import socket
import socketserver
import stat
import struct
import sys
import threading
import time

import lrb_core as base
import elastic_automation as elastic
import elastic_tick
import metacog_diagnosis as metacog
import model_handrail
import external_gates

SCHEMA = "LRB_LOCAL_TRANSPORT/0.3"
MAX_REQUEST_BYTES = 8192
MAX_RESPONSE_BYTES = 32 * 1024
MAX_CLIENTS = 3
MAX_FRAMES = 5
MAX_INTERVAL_SEC = 5
MAX_WATCH_SEC = 25


class Transport:
    def __init__(self, state, contract, observer=None, clock=None, sleeper=None):
        if contract.get("schema") != "LOUKSNA_REMOTE_BRIDGE_CONTRACT/0.1" or contract["release"]["certified"] is not False:
            raise RuntimeError("BRIDGE_CONTRACT_INVALID")
        self.state = base.secure_state(state)
        self.contract = contract
        self.observe = observer or base.snapshot
        self.clock = clock or time.monotonic
        self.sleeper = sleeper or time.sleep
        self.ledger = base.EvidenceLedger(self.state)
        self.ledger.verify()
        self.automation = elastic.Automation(self.state, contract, observer=self.observe)
        self.scheduler = elastic_tick.Scheduler(self.automation)

    def dispatch(self, request):
        if not isinstance(request, dict) or type(request.get("op")) is not str:
            raise RuntimeError("INVALID_TYPED_REQUEST")
        allowed = {"status": {"op"}, "observe": {"op"},
                   "tick_readonly": {"op"}, "report": {"op", "mission_id"},
                   "diagnose": {"op", "mission_id"},
                   "review_model": {"op", "mission_id", "envelope", "evidence_index"},
                   "gate_preflight": {"op", "mission_id", "request_path",
                                      "owner_signature", "receipts", "strong"}}
        op = request["op"]
        if op not in allowed or set(request) != allowed[op]:
            raise RuntimeError("UNREGISTERED_OPERATION_DENIED")
        if op == "status":
            head = self.ledger.verify()
            return {"schema": SCHEMA, "status": "OBSERVATION_ONLY_UNCERTIFIED",
                    "host": socket.gethostname(), "boot_id": base.boot_id(),
                    "evidence_head": head, "github_control": "EXTERNAL_ASYNC",
                    "local_transport": "CONNECTED_SAME_UID",
                    "sudo_root_shell": "NOT_EXPOSED", "g23": "NOT_EXECUTED",
                    "g24": "NOT_EXECUTED", "certified": False}
        if op == "observe":
            observed = self.observe()
            entry = self.ledger.append("TRANSPORT_READONLY_OBSERVATION",
                                       {"observation_sha256": base.digest(observed)})
            return {"schema": SCHEMA, "status": "OBSERVED_NOT_CERTIFIED",
                    "observation": observed, "evidence_seq": entry["seq"],
                    "evidence_sha256": entry["entry_hash"], "certified": False}
        if op == "tick_readonly":
            result = self.scheduler.tick()
            return {"schema": SCHEMA, "result": result, "privileged": False,
                    "certified": False}
        if not isinstance(request["mission_id"], str) or not elastic.MID.fullmatch(request["mission_id"]):
            raise RuntimeError("MISSION_ID_INVALID")
        if op == "diagnose":
            return metacog.diagnose(self.automation, request["mission_id"],
                                    observation=self.observe(),
                                    same_uid_socket_verified=True)
        if op == "review_model":
            with self.automation.exclusive() as commits:
                document = self.automation.read(commits)
                row = document["missions"].get(request["mission_id"])
                if row is None:
                    raise RuntimeError("MISSION_UNKNOWN")
                owner_goal = row["request"]["user_objective"]
            if (not isinstance(request["envelope"], dict)
                    or request["envelope"].get("user_objective") != owner_goal):
                raise RuntimeError("MODEL_OWNER_SCOPE_DRIFT")
            report = model_handrail.review(request["envelope"], request["evidence_index"])
            self.ledger.append("MODEL_STRUCTURAL_REVIEW", {
                "mission_id": request["mission_id"], "mission_sha256": row["mission_sha256"],
                "review_sha256": base.digest(report), "correction_count": len(report["corrections"]),
                "certified": False})
            return report
        if op == "gate_preflight":
            if request["strong"] is not True or not isinstance(request["receipts"], dict):
                raise RuntimeError("STRONG_EXTERNAL_GATES_REQUIRED")
            with self.automation.exclusive() as commits:
                document = self.automation.read(commits)
                row = document["missions"].get(request["mission_id"])
                if row is None or row["status"] != "WAITING_FRESH_G23_G24":
                    raise RuntimeError("GATED_MISSION_CHECKPOINT_REQUIRED")
                next_step = row["request"]["steps"][row["next_step"]]
                if next_step["kind"] != "GATED_OPERATION":
                    raise RuntimeError("GATED_STEP_NOT_CURRENT")
            raw = external_gates.read_regular(request["request_path"])
            signed_request = json.loads(raw)
            if (signed_request.get("mission_id") != request["mission_id"]
                    or signed_request.get("mission_sha256") != row["mission_sha256"]
                    or signed_request.get("owner_objective_sha256") != base.digest(
                        row["request"]["user_objective"])
                    or signed_request.get("capability") != next_step["requested_capability"]
                    or signed_request.get("source_sha256") != hashlib.sha256(
                        Path(__file__).read_bytes()).hexdigest()):
                raise RuntimeError("SIGNED_SCOPE_MISSION_OR_LIVE_CODE_MISMATCH")
            verifier = external_gates.ExternalGateVerifier("/etc/louksna/remote-bridge",
                                                          enforce_root_owned=True)
            result = verifier.preflight(request["request_path"],
                         request["owner_signature"], request["receipts"], strong=True)
            self.ledger.append("STRONG_EXTERNAL_GATE_PREFLIGHT", {
                "mission_id":request["mission_id"], "receipt_hashes": result["hashes"],
                "privileged_execution":False, "certified":False})
            return {**result, "material_dispatch_registered": False,
                    "execution_authorized_by_this_transport":False}
        return {"schema": SCHEMA, "mission": self.automation.report(request["mission_id"]),
                "privileged": False, "certified": False}

    def watch(self, request):
        if set(request) != {"op", "frames", "interval_sec"} or request.get("op") != "watch":
            raise RuntimeError("INVALID_WATCH_REQUEST")
        frames, interval = request.get("frames"), request.get("interval_sec")
        if type(frames) is not int or type(interval) is not int or not (1 <= frames <= MAX_FRAMES) or not (1 <= interval <= MAX_INTERVAL_SEC):
            raise RuntimeError("WATCH_RESOURCE_BUDGET_DENIED")
        if frames * interval > MAX_WATCH_SEC:
            raise RuntimeError("WATCH_TIME_BUDGET_EXCEEDED")
        self.ledger.append("WATCH_SESSION_ACCEPTED", {"frames": frames, "interval": interval})
        for i in range(frames):
            snap = self.observe()
            evidence = self.ledger.append("LIVE_OBSERVATION", {
                "observation_sha256": base.digest(snap), "frame": i + 1})
            yield {"schema": SCHEMA, "event": "LIVE_SNAPSHOT",
                   "frame": i + 1, "total_frames": frames, "observation": snap,
                   "evidence_seq": evidence["seq"], "evidence_hash": evidence["entry_hash"],
                   "host_privilege_mutation": False, "certified": False}
            if i + 1 < frames:
                self.sleeper(interval)


class Handler(socketserver.StreamRequestHandler):
    def _write(self, obj):
        line = base.canonical(obj)
        if len(line) >= MAX_RESPONSE_BYTES:
            obj = {"schema": SCHEMA, "status": "HOLD_RESPONSE_BUDGET",
                   "payload_sha256": base.digest(obj), "certified": False}
            line = base.canonical(obj)
        self.wfile.write(line + b"\n")
        self.wfile.flush()

    def handle(self):
        self.connection.settimeout(4)
        line = self.rfile.readline(MAX_REQUEST_BYTES + 1)
        if not line or len(line) > MAX_REQUEST_BYTES or not line.endswith(b"\n"):
            self._write({"status": "HOLD_REQUEST_BOUNDARY", "certified": False})
            return
        try:
            req = json.loads(line)
            if isinstance(req, dict) and req.get("op") == "watch":
                self.connection.settimeout(MAX_WATCH_SEC + 5)
                for frame in self.server.bridge.watch(req):
                    self._write(frame)
            else:
                self._write(self.server.bridge.dispatch(req))
        except (BrokenPipeError, ConnectionResetError, TimeoutError):
            return
        except Exception as exc:
            try:
                self.server.bridge.ledger.append("TRANSPORT_OPERATION_HOLD", {
                    "error_class": type(exc).__name__, "reason_code": str(exc)[:120],
                    "no_material_execution": True})
            except Exception:
                pass
            self._write({"schema": SCHEMA, "status": "HOLD", "code": str(exc)[:120],
                         "certified": False})


class Server(socketserver.ThreadingMixIn, socketserver.UnixStreamServer):
    daemon_threads = True
    request_queue_size = 3
    allow_reuse_address = False

    def __init__(self, path, bridge):
        self.bridge = bridge
        self.slots = threading.BoundedSemaphore(MAX_CLIENTS)
        super().__init__(str(path), Handler)
        os.chmod(path, 0o600)

    def verify_request(self, request, client_address):
        if not self.slots.acquire(blocking=False):
            return False
        if not hasattr(socket, "SO_PEERCRED"):
            self.slots.release()
            return False
        try:
            pid, uid, gid = struct.unpack("3i",
                request.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")))
            if pid <= 0 or uid != os.getuid():
                self.slots.release()
                return False
            return True
        except OSError:
            self.slots.release()
            return False

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.slots.release()


def guarded_socket_path(state):
    state = base.secure_state(state)
    target = state / "BRIDGE.sock"
    if target.is_symlink():
        raise RuntimeError("SOCKET_SYMLINK_DENIED")
    if target.exists():
        obj = target.lstat()
        if not stat.S_ISSOCK(obj.st_mode) or obj.st_uid != os.getuid():
            raise RuntimeError("FOREIGN_OR_INVALID_SOCKET_DENIED")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.5)
            try:
                probe.connect(str(target))
            except ConnectionRefusedError:
                target.unlink()
            except OSError as exc:
                raise RuntimeError("SOCKET_STATE_UNVERIFIED") from exc
            else:
                raise RuntimeError("LIVE_SERVER_ALREADY_BOUND")
    if len(os.fsencode(str(target))) >= 108:
        raise RuntimeError("AF_UNIX_SOCKET_PATH_EXCEEDS_KERNEL_LIMIT")
    return target


def client(path, command, stream=False):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
        s.settimeout(MAX_WATCH_SEC + 5 if stream else 5)
        s.connect(str(path))
        s.sendall(base.canonical(command) + b"\n")
        received = 0
        with s.makefile("rb") as f:
            for line in f:
                if len(line) > MAX_RESPONSE_BYTES:
                    raise RuntimeError("SERVER_RESPONSE_BUDGET_EXCEEDED")
                msg = json.loads(line)
                print(json.dumps(msg, sort_keys=True, ensure_ascii=False))
                received += 1
                if not stream:
                    break
        if received != (command["frames"] if stream else 1):
            raise RuntimeError("INCOMPLETE_TRANSPORT_RESPONSE")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("--state-dir", required=True)
    p.add_argument("--socket-dir", help="Separate short, private 0700 socket directory")
    p.add_argument("--contract", default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    sp = p.add_subparsers(dest="verb", required=True)
    sp.add_parser("serve")
    ask = sp.add_parser("request")
    ask.add_argument("--op", choices=("status", "observe", "tick_readonly", "report", "watch", "diagnose"), required=True)
    ask.add_argument("--mission-id")
    ask.add_argument("--frames", type=int, default=2)
    ask.add_argument("--interval-sec", type=int, default=1)
    a = p.parse_args(argv)
    try:
        socket_dir = a.socket_dir or a.state_dir
        path = Path(socket_dir).expanduser() / "BRIDGE.sock"
        if a.verb == "request":
            if a.op in ("report", "diagnose"):
                req = {"op": a.op, "mission_id": a.mission_id}
            elif a.op == "watch":
                req = {"op": "watch", "frames": a.frames, "interval_sec": a.interval_sec}
            else:
                req = {"op": a.op}
            client(path, req, a.op == "watch")
            return 0
        config = json.loads(Path(a.contract).read_text(encoding="utf-8"))
        bridge = Transport(a.state_dir, config)
        target = guarded_socket_path(socket_dir)
        server = Server(target, bridge)
        try:
            server.serve_forever(poll_interval=0.5)
        finally:
            server.server_close()
            if target.exists() and target.is_socket() and target.stat().st_uid == os.getuid():
                target.unlink()
        return 0
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "code": str(exc)[:120]}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
