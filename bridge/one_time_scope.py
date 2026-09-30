#!/usr/bin/env python3
"""Crash-safe single-use scope reservation for externally signed LRB gate bundles.

This does NOT execute an operation, mint a root token, issue G23/G24, attest
human independence, or authorize sudo. A separate independent, registered
material executor must recheck live signatures and consume its own authority.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import socket

import elastic_automation as elastic
import external_gates
import lrb_core as base
import live_link

SCHEMA = "LRB_SCOPE_RESERVATION/0.1"
SCOPE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,95}$")
RE_SHA256 = re.compile(r"^[a-f0-9]{64}$")
REQUIRED_RECEIPTS = ("G23", "G24", "G23_2", "G24_2")


class SingleUseScope:
    """Local-only reservation, serialized against mission transitions."""

    def __init__(self, state, contract, verifier=None, source_file=None, host=None, boot=None):
        self.agent = elastic.Automation(state, contract)
        self.ledger = self.agent.ledger
        self.state = self.agent.state
        self.lock = self.state / "ONE_TIME_SCOPE.lock"
        self.verifier = verifier
        self.source_file = Path(source_file or live_link.__file__)
        self.host = host or socket.gethostname()
        self.boot = boot or base.boot_id()

    def reserve(self, mission_id, request_path, owner_signature, receipts):
        """Reserve exact strong-signature scope once; no executable authority.

        Append-only intent is fsync'd BEFORE a caller can observe acceptance.
        A crash after reservation intentionally leaves an unusable scope until
        an independently reviewed new owner request with a new scope ID.
        """
        if not isinstance(mission_id, str) or not elastic.MID.fullmatch(mission_id):
            raise RuntimeError("MISSION_ID_INVALID")
        if not isinstance(receipts, dict) or set(receipts) != set(REQUIRED_RECEIPTS):
            raise RuntimeError("ALL_FOUR_INDEPENDENT_GATE_RECEIPTS_REQUIRED")
        if any(not isinstance(value, dict) or set(value) != {"document", "signature"}
               for value in receipts.values()):
            raise RuntimeError("GATE_RECEIPT_STRUCTURE_INVALID")
        if self.source_file.is_symlink() or not self.source_file.is_file():
            raise RuntimeError("LIVE_SOURCE_UNVERIFIED")
        current_source_sha = hashlib.sha256(self.source_file.read_bytes()).hexdigest()
        reservation_module_sha = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        raw = external_gates.read_regular(request_path)
        try:
            request = json.loads(raw)
        except (ValueError, UnicodeDecodeError) as exc:
            raise RuntimeError("SIGNED_REQUEST_INVALID") from exc
        scope = request.get("scope_id")
        if not isinstance(scope, str) or not SCOPE.fullmatch(scope):
            raise RuntimeError("INVALID_SCOPE_ID")
        signed_request_sha = hashlib.sha256(raw).hexdigest()
        # The checked trust set must belong to the actual local owner, not this
        # LLM or a synthetic CI fixture. Fake verifiers are for unit tests only.
        with self.lock.open("a+b") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            with self.agent.exclusive() as commits:
                data = self.agent.read(commits)
                row = data["missions"].get(mission_id)
                if row is None or row["status"] != "WAITING_FRESH_G23_G24":
                    raise RuntimeError("SIGNED_MISSION_NOT_AT_GATE_CHECKPOINT")
                if row["next_step"] >= len(row["request"]["steps"]):
                    raise RuntimeError("SIGNED_MISSION_OUT_OF_RANGE")
                next_step = row["request"]["steps"][row["next_step"]]
                if next_step.get("kind") != "GATED_OPERATION":
                    raise RuntimeError("SIGNED_MISSION_NOT_GATED")
                if (request.get("schema") != "LRB_SCOPED_REQUEST/0.3"
                        or request.get("mission_id") != mission_id
                        or request.get("mission_sha256") != row["mission_sha256"]
                        or request.get("owner_objective_sha256") !=
                            base.digest(row["request"]["user_objective"])
                        or request.get("capability") != next_step["requested_capability"]
                        or request.get("source_sha256") != current_source_sha
                        or request.get("reservation_module_sha256") != reservation_module_sha
                        or request.get("host") != self.host
                        or request.get("boot_id") != self.boot):
                    raise RuntimeError("SIGNED_SCOPE_MISSION_HOST_OR_SOURCE_MISMATCH")
                # Check both scope and exact request hash in the authoritative
                # tamper-evident ledger. Never rely on a mutable cache alone.
                for prior in self.ledger._records():
                    if prior.get("kind") == "STRONG_SCOPE_RESERVED":
                        previous = prior["payload"]
                        if (previous.get("scope_id") == scope or
                            previous.get("request_sha256") == signed_request_sha or
                            previous.get("mission_id") == mission_id):
                            raise RuntimeError("SIGNED_SCOPE_ALREADY_RESERVED_NO_REPLAY")
                verifier = self.verifier or external_gates.ExternalGateVerifier(
                    "/etc/louksna/remote-bridge", enforce_root_owned=True)
                result = verifier.preflight(
                    request_path, owner_signature, receipts, strong=True,
                    expected_host=self.host, expected_boot=self.boot)
                if (result.get("status") !=
                        "SIGNED_RECEIPTS_CRYPTOGRAPHICALLY_VERIFIED"
                        or result.get("scope_id") != scope
                        or result.get("capability") != request["capability"]
                        or result.get("host") != self.host
                        or result.get("boot_id") != self.boot
                        or result.get("strong_second_order_receipts_verified") is not True
                        or result.get("execution_authorized_by_this_verifier") is not False
                        or result.get("certified") is not False
                        or not isinstance(result.get("hashes"), dict)
                        or result["hashes"].get("request_sha256") != signed_request_sha
                        or not all(isinstance(result["hashes"].get(k), str)
                            and RE_SHA256.fullmatch(result["hashes"][k])
                            for k in ("g23_sha256", "g24_sha256",
                                      "g23_2_sha256", "g24_2_sha256"))):
                    raise RuntimeError("EXTERNAL_CRYPTOGRAPHIC_REPORT_UNTRUSTED")
                record = self.ledger.append("STRONG_SCOPE_RESERVED", {
                    "scope_id": scope, "mission_id": mission_id,
                    "mission_sha256": row["mission_sha256"],
                    "owner_objective_sha256": request["owner_objective_sha256"],
                    "source_sha256": current_source_sha,
                    "reservation_module_sha256": reservation_module_sha,
                    "request_sha256": signed_request_sha,
                    "gate_receipt_sha256": {role: result["hashes"][role.lower()+"_sha256"]
                                           for role in REQUIRED_RECEIPTS},
                    "host": self.host, "boot_id": self.boot,
                    "review_of_real_signer_independence": "EXTERNAL_REQUIRED",
                    "root_operation": "NOT_EXECUTED",
                    "material_dispatch": "NOT_REGISTERED",
                    "certified": False
                })
                return {
                    "schema": SCHEMA,
                    "status": "RESERVED_ONCE_AWAITING_INDEPENDENT_EXECUTOR",
                    "scope_id": scope, "mission_id": mission_id,
                    "reservation_evidence_hash": record["entry_hash"],
                    "source_sha256": current_source_sha,
                    "cryptographic_receipts_checked": True,
                    "issuer_operator_independence_certified": False,
                    "authorization_consumed_for_root": False,
                    "root_operation_executed": False,
                    "certified": False
                }


def main(argv=None):
    """CLI is deliberately reservation-only, never a root-shell entrypoint."""
    import argparse
    import sys
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--state-dir", required=True)
    p.add_argument("--contract", default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    p.add_argument("--mission-id", required=True)
    p.add_argument("--request", required=True)
    p.add_argument("--owner-signature", required=True)
    for role in ("g23", "g24", "g23-2", "g24-2"):
        p.add_argument("--"+role, required=True)
        p.add_argument("--"+role+"-signature", required=True)
    a = p.parse_args(argv)
    try:
        if os.geteuid() == 0:
            raise RuntimeError("ROOT_PROCESS_MUST_NOT_RUN_RESERVATION_CLI")
        contract_path = Path(a.contract)
        if contract_path.is_symlink() or contract_path.stat().st_size > 32768:
            raise RuntimeError("CONTRACT_FILE_UNSAFE")
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        refs = {}
        for role in ("g23","g24","g23-2","g24-2"):
            refs[role.upper().replace("-","_")] = {
                "document": getattr(a,role.replace("-","_")),
                "signature": getattr(a,role.replace("-","_")+"_signature")
            }
        result = SingleUseScope(a.state_dir,contract).reserve(
            a.mission_id,a.request,a.owner_signature,refs)
        print(json.dumps(result,sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status":"HOLD","reason":str(exc)[:180],
                          "root_execution":False,"certified":False}),file=sys.stderr)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
