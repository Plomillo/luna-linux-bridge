#!/usr/bin/env python3
"""LOUKSNA Remote Bridge 0.1: deliberately read-only local reference core.

This is not a privileged deployment, a real-time network transport, or a
self-certifying G23/G24 authority. External certifications are mandatory.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import hmac
import ipaddress
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
from urllib.parse import urlsplit
import webbrowser

SCHEMA = "LOUKSNA_REMOTE_BRIDGE_EVENT/0.1"
STATE_DEFAULT = Path.home() / ".local/state/louksna/remote-bridge"
MAX_LOG_BYTES = 10 * 1024 * 1024
MAX_STATE_ENTRIES = 10000


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00", "Z")


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()


def secure_state(path):
    path = Path(path).expanduser()
    if path.is_symlink():
        raise RuntimeError("STATE_DIR_SYMLINK_FORBIDDEN")
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if path.is_symlink() or not path.is_dir():
        raise RuntimeError("STATE_DIR_INVALID")
    if path.stat().st_uid != os.getuid():
        raise RuntimeError("STATE_DIR_OWNERSHIP")
    path.chmod(0o700)
    return path


def atomic_json(path, obj):
    path = Path(path)
    tmp = path.with_name(path.name + ".tmp-" + str(os.getpid()))
    fd = os.open(str(tmp), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(canonical(obj) + b"\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        dirfd = os.open(str(path.parent), os.O_DIRECTORY)
        try:
            os.fsync(dirfd)
        finally:
            os.close(dirfd)
    finally:
        if tmp.exists():
            tmp.unlink()


def load_time_policy(state, contract):
    path = state / "TIME_POLICY.json"
    defaults = contract["resource_defaults"]
    if not path.exists():
        return {"revision": 0, "heartbeat_sec": defaults["heartbeat_sec"],
                "max_work_seconds": defaults["max_work_seconds"],
                "hard_deadline_sec": defaults["hard_deadline_sec"]}
    policy = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(policy.get("revision"), int)
        or policy.get("heartbeat_sec") not in range(defaults["min_heartbeat_sec"], defaults["max_heartbeat_sec"] + 1)
        or policy.get("max_work_seconds", 0) < 1
        or policy["max_work_seconds"] > policy.get("hard_deadline_sec", 0)
        or policy.get("hard_deadline_sec") != defaults["hard_deadline_sec"]):
        raise RuntimeError("TIME_POLICY_INVALID")
    return policy


def update_time_policy(state, contract, revision, heartbeat, work):
    lock = state / "TIME_POLICY.lock"
    with lock.open("a+b") as mutex:
        fcntl.flock(mutex, fcntl.LOCK_EX)
        current = load_time_policy(state, contract)
        if current["revision"] != revision:
            raise RuntimeError("STALE_TIME_REVISION")
        limits = contract["resource_defaults"]
        if not limits["min_heartbeat_sec"] <= heartbeat <= limits["max_heartbeat_sec"]:
            raise RuntimeError("HEARTBEAT_OUT_OF_BOUNDS")
        if not 1 <= work <= current["hard_deadline_sec"]:
            raise RuntimeError("WORK_TIME_OUT_OF_BOUNDS")
        if work > current["max_work_seconds"]:
            raise RuntimeError("EXTENDED_BUDGET_REQUIRES_NEW_AUTHORITY")
        change = {**current, "revision": revision + 1,
                  "heartbeat_sec": heartbeat, "max_work_seconds": work}
        atomic_json(state / "TIME_POLICY.json", change)
    return change


class EvidenceLedger:
    """Tamper-evident hash chain; no signature unless independently keyed."""

    def __init__(self, state):
        self.state = Path(state)
        self.path = self.state / "EVENTS.jsonl"
        self.lock = self.state / "EVENTS.lock"

    def _records(self):
        if not self.path.exists():
            return []
        if self.path.stat().st_size > MAX_LOG_BYTES:
            raise RuntimeError("EVIDENCE_LOG_LIMIT")
        with self.path.open("r", encoding="utf-8") as stream:
            records = [json.loads(line) for line in stream if line.strip()]
        if len(records) > MAX_STATE_ENTRIES:
            raise RuntimeError("EVIDENCE_RECORD_LIMIT")
        return records

    def verify(self):
        prev = "0" * 64
        for index, record in enumerate(self._records(), start=1):
            body = {key: value for key, value in record.items() if key != "entry_hash"}
            if body.get("previous_hash") != prev or body.get("seq") != index:
                raise RuntimeError("EVIDENCE_CHAIN_BROKEN")
            if digest(body) != record.get("entry_hash"):
                raise RuntimeError("EVIDENCE_HASH_BROKEN")
            prev = record["entry_hash"]
        return prev

    def append(self, kind, payload):
        with self.lock.open("a+b") as mutex:
            fcntl.flock(mutex, fcntl.LOCK_EX)
            previous = self.verify()
            number = len(self._records()) + 1
            if number > MAX_STATE_ENTRIES:
                raise RuntimeError("EVIDENCE_RECORD_LIMIT")
            body = {"schema": SCHEMA, "seq": number,
                    "ts_utc": utc(), "boot_id": boot_id(),
                    "previous_hash": previous, "kind": kind, "payload": payload}
            record = {**body, "entry_hash": digest(body)}
            data = canonical(record) + b"\n"
            if self.path.exists() and self.path.stat().st_size + len(data) > MAX_LOG_BYTES:
                raise RuntimeError("EVIDENCE_LOG_LIMIT")
            fd = os.open(str(self.path), os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
            with os.fdopen(fd, "ab") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            return record


def boot_id():
    path = Path("/proc/sys/kernel/random/boot_id")
    return path.read_text().strip() if path.is_file() else "UNAVAILABLE"


def meminfo():
    path = Path("/proc/meminfo")
    if not path.exists():
        return {"available": False}
    wanted = ("MemTotal", "MemAvailable", "SwapTotal", "SwapFree")
    values = {}
    with path.open() as stream:
        for line in stream:
            label = line.partition(":")[0]
            if label in wanted:
                values[label] = int(line.partition(":")[2].strip().split()[0]) * 1024
    return values


def sudo_probe():
    try:
        result = subprocess.run(["sudo", "-n", "true"], stdin=subprocess.DEVNULL,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                timeout=3, check=False)
        return "AVAILABLE_FOR_CHECK_ONLY" if result.returncode == 0 else "UNAVAILABLE"
    except (OSError, subprocess.TimeoutExpired):
        return "UNAVAILABLE"


def snapshot(check_sudo=False):
    disk = os.statvfs("/")
    total_bytes = disk.f_blocks * disk.f_frsize
    available = disk.f_bavail * disk.f_frsize
    memory = meminfo()
    return {"observed_utc": utc(), "host": os.uname().nodename,
            "boot_id": boot_id(), "pid": os.getpid(),
            "uid": os.getuid(), "gid": os.getgid(),
            "load": list(os.getloadavg()), "memory_bytes": memory,
            "root_fs_bytes": {"total": total_bytes, "available": available},
            "sudo_noninteractive": sudo_probe() if check_sudo else "NOT_PROBED",
            "project_partition": "NOT_LIVE_VERIFIED",
            "screen": "NOT_ENABLED",
            "bridge_root_shell": "NOT_DEPLOYED",
            "github_transport": "NOT_DEPLOYED"}


def validate_claims(user_requirements, model_expectations, model_name, model_version):
    if not isinstance(user_requirements, str) or not user_requirements.strip():
        raise RuntimeError("USER_OBJECTIVE_REQUIRED")
    if not isinstance(model_expectations, str):
        raise RuntimeError("MODEL_EXPECTATIONS_MUST_BE_SEPARATE")
    if not model_name or not model_version:
        raise RuntimeError("MODEL_AND_VERSION_DECLARATION_REQUIRED")
    return {"user_requirements": user_requirements.strip(),
            "model_expectations": model_expectations.strip(),
            "model": {"declared_name": model_name,
                      "declared_version": model_version,
                      "verified_by_provider": False},
            "status": "PROPOSED_UNCERTIFIED",
            "execution_allowed": False, "g23": "NOT_EXECUTED",
            "g24": "NOT_EXECUTED", "second_order": "NOT_EXECUTED"}


def validate_url(url, host):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise RuntimeError("URL_REQUIRES_PUBLIC_HTTPS")
    if not host or parsed.hostname != host.lower() or not host.isascii():
        raise RuntimeError("HOST_NOT_EXPLICITLY_AUTHORIZED")
    if parsed.port not in (None, 443):
        raise RuntimeError("UNEXPECTED_PORT")
    try:
        ipaddress.ip_address(parsed.hostname)
    except ValueError:
        pass
    else:
        raise RuntimeError("RAW_IP_ADDRESS_DENIED")
    if (parsed.hostname in ("localhost", "metadata.google.internal")
        or parsed.hostname.endswith(".local")
        or parsed.hostname.endswith(".internal")):
        raise RuntimeError("LOCAL_OR_METADATA_URL_DENIED")
    return url


def priority_index(root, limit=40):
    root = Path(root).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("USER_PROJECT_ROOT_MUST_EXIST_AND_NOT_BE_SYMLINK")
    if not 1 <= limit <= 100:
        raise RuntimeError("INDEX_LIMIT_OUT_OF_BOUNDS")
    indexed = []
    with os.scandir(root) as entries:
        for entry in entries:
            if len(indexed) >= limit:
                break
            if entry.is_symlink():
                continue
            indexed.append({"name": entry.name,
                            "kind": "directory" if entry.is_dir(follow_symlinks=False) else "file"})
    return {"root": str(root.resolve()), "items": indexed,
            "recursive_scan": False, "truncated_possible": len(indexed) == limit}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-dir", default=str(STATE_DEFAULT))
    parser.add_argument("--contract", default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status")
    p = commands.add_parser("observe")
    p.add_argument("--sudo-probe", action="store_true")
    p = commands.add_parser("monitor")
    p.add_argument("--cycles", type=int, default=1)
    p = commands.add_parser("time-update")
    p.add_argument("--revision", type=int, required=True)
    p.add_argument("--heartbeat-sec", type=int, required=True)
    p.add_argument("--work-seconds", type=int, required=True)
    p = commands.add_parser("plan")
    p.add_argument("--objective", required=True)
    p.add_argument("--model-expectation", default="")
    p.add_argument("--model-name", required=True)
    p.add_argument("--model-version", required=True)
    p = commands.add_parser("open-url")
    p.add_argument("--url", required=True)
    p.add_argument("--authorized-host", required=True)
    p = commands.add_parser("projects")
    p.add_argument("--root", required=True)
    p.add_argument("--limit", type=int, default=40)
    args = parser.parse_args(argv)
    contract = json.loads(Path(args.contract).read_text(encoding="utf-8"))
    if contract.get("schema") != "LOUKSNA_REMOTE_BRIDGE_CONTRACT/0.1" or contract.get("release", {}).get("certified") is not False:
        raise RuntimeError("CONTRACT_VERSION_OR_CERTIFICATION_MISMATCH")
    state = secure_state(args.state_dir)
    ledger = EvidenceLedger(state)
    if args.command == "status":
        result = {"status": "DRAFT_UNCERTIFIED",
                  "evidence_chain_head": ledger.verify(),
                  "time_policy": load_time_policy(state, contract),
                  "g23": "NOT_EXECUTED", "g24": "NOT_EXECUTED",
                  "root_mutations_enabled": False}
    elif args.command == "observe":
        result = snapshot(args.sudo_probe)
        ledger.append("READONLY_OBSERVATION", result)
    elif args.command == "monitor":
        if args.cycles < 0 or args.cycles > 10000:
            raise RuntimeError("MONITOR_CYCLES_OUT_OF_BOUNDS")
        stop = False
        def quit_signal(_sig, _frame):
            nonlocal stop
            stop = True
        signal.signal(signal.SIGTERM, quit_signal)
        signal.signal(signal.SIGINT, quit_signal)
        index = 0
        begin = time.monotonic()
        result = {}
        while not stop and (args.cycles == 0 or index < args.cycles):
            policy = load_time_policy(state, contract)  # live time reload at safe checkpoint
            if time.monotonic() - begin > policy["max_work_seconds"]:
                result = {"status": "HOLD_TIME_BUDGET", "cycles": index}
                ledger.append("MONITOR_HOLD", result)
                break
            result = snapshot()
            mem = result["memory_bytes"]
            low_memory = isinstance(mem, dict) and mem.get("MemTotal", 0) > 0 and mem.get("MemAvailable", 0) / mem["MemTotal"] < 0.15
            result["adaptation"] = "LOW_RESOURCE" if low_memory else "NORMAL"
            ledger.append("READONLY_HEARTBEAT", result)
            index += 1
            if args.cycles == 0 or index < args.cycles:
                interval = min(contract["resource_defaults"]["max_heartbeat_sec"],
                               policy["heartbeat_sec"] * (2 if low_memory else 1))
                time.sleep(interval)
        result["completed_cycles"] = index
    elif args.command == "time-update":
        result = update_time_policy(state, contract, args.revision, args.heartbeat_sec, args.work_seconds)
        ledger.append("TIME_POLICY_REDUCED_OR_RETIMED", result)
    elif args.command == "plan":
        result = validate_claims(args.objective, args.model_expectation,
                                 args.model_name, args.model_version)
        ledger.append("MISSION_PROPOSED", {"mission_hash": digest(result),
                     "model": result["model"],
                     "execution_allowed": False})
    elif args.command == "open-url":
        url = validate_url(args.url, args.authorized_host)
        # Opens only on the local desktop; not a remote browsing execution service.
        launched = bool(webbrowser.open(url, new=2))
        result = {"status": "LAUNCH_REQUESTED" if launched else "NO_BROWSER_AVAILABLE",
                  "authorized_host": args.authorized_host,
                  "page_content_verified": False}
        ledger.append("BROWSER_LAUNCH", result)
    elif args.command == "projects":
        result = priority_index(args.root, args.limit)
        ledger.append("PROJECT_INDEX_READONLY", {"root": result["root"],
                      "entries": len(result["items"]), "recursive_scan": False})
    else:
        raise RuntimeError("UNKNOWN_COMMAND")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as error:
        print(json.dumps({"status": "HOLD", "error_type": type(error).__name__,
                          "reason": str(error)[:250]}, ensure_ascii=False), file=sys.stderr)
        sys.exit(3)
