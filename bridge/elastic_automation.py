#!/usr/bin/env python3
"""Resumable, resource-aware LOUKSNA automation candidate: registered read-only steps only.

An independent G23/G24 authority must review any proposed privileged step.
This module cannot grant approvals, launch shells, or certify itself.
"""
from __future__ import annotations
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import sys

import lrb_core as base

SCHEMA = "LOUKSNA_ELASTIC_AUTOMATION/0.1"
KINDS = {"OBSERVE_LOCAL", "INDEX_PRIORITY", "GATED_OPERATION"}
MID = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.-]{0,63}$")


def deadline(value):
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise RuntimeError("UTC_DEADLINE_REQUIRED") from exc
    if result.tzinfo is None or result.utcoffset().total_seconds() != 0:
        raise RuntimeError("UTC_DEADLINE_REQUIRED")
    return result


def validate(mission, policy):
    if not isinstance(mission, dict) or set(mission) - {
        "mission_id", "user_objective", "model_proposal", "model",
        "deadline_utc", "max_auto_steps", "steps"}:
        raise RuntimeError("UNREVIEWED_MISSION_FIELDS")
    if not isinstance(mission.get("mission_id"), str) or not MID.fullmatch(mission["mission_id"]):
        raise RuntimeError("MISSION_ID_INVALID")
    if not isinstance(mission.get("user_objective"), str) or not 0 < len(mission["user_objective"].strip()) <= 4096:
        raise RuntimeError("USER_OBJECTIVE_MISSING")
    if not isinstance(mission.get("model_proposal"), str) or len(mission["model_proposal"]) > 4096:
        raise RuntimeError("USER_AND_MODEL_EXPECTATIONS_MUST_BE_SEPARATE")
    model = mission.get("model", {})
    if not isinstance(model, dict) or not all(
        isinstance(model.get(k), str) and 0 < len(model[k]) <= 128
        for k in ("declared_name", "declared_version")):
        raise RuntimeError("DECLARED_MODEL_AND_VERSION_REQUIRED")
    steps = mission.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 8:
        raise RuntimeError("STEP_COUNT_INVALID")
    if type(mission.get("max_auto_steps")) is not int or not 1 <= mission["max_auto_steps"] <= 8:
        raise RuntimeError("AUTO_STEP_BUDGET_INVALID")
    for step in steps:
        if not isinstance(step, dict) or step.get("kind") not in KINDS:
            raise RuntimeError("UNREGISTERED_STEP_DENIED")
        allowed = {
            "OBSERVE_LOCAL": {"kind"},
            "INDEX_PRIORITY": {"kind", "root", "limit"},
            "GATED_OPERATION": {"kind", "requested_capability"}
        }[step["kind"]]
        if set(step) - allowed:
            raise RuntimeError("UNREVIEWED_STEP_FIELDS_DENIED")
        if step["kind"] == "INDEX_PRIORITY":
            if not isinstance(step.get("root"), str) or not step["root"]:
                raise RuntimeError("EXACT_PROJECT_ROOT_REQUIRED")
            if type(step.get("limit", 40)) is not int or not 1 <= step.get("limit", 40) <= 100:
                raise RuntimeError("PROJECT_LIMIT_INVALID")
        if step["kind"] == "GATED_OPERATION" and (
            not isinstance(step.get("requested_capability"), str) or
            not step["requested_capability"].strip()):
            raise RuntimeError("GATED_CAPABILITY_UNSPECIFIED")
    deadline(mission.get("deadline_utc"))
    if policy["max_work_seconds"] <= 0:
        raise RuntimeError("TIME_POLICY_INVALID")


class Automation:
    def __init__(self, state, contract, observer=None, indexer=None, clock=None):
        if (contract.get("schema") != "LOUKSNA_REMOTE_BRIDGE_CONTRACT/0.1"
                or contract.get("release", {}).get("certified") is not False):
            raise RuntimeError("BRIDGE_CONTRACT_NOT_UNCERTIFIED_CANDIDATE")
        self.state = base.secure_state(state)
        self.contract = contract
        self.ledger = base.EvidenceLedger(self.state)
        self.store = self.state / "ELASTIC_STATE.json"
        self.lock = self.state / "ELASTIC.lock"
        self.observer = observer or base.snapshot
        self.indexer = indexer or base.priority_index
        self.clock = clock or (lambda: datetime.now(timezone.utc))

    @contextmanager
    def exclusive(self):
        with self.lock.open("a+b") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            self.ledger.verify()
            pending = set()
            commits = []
            for rec in self.ledger._records():
                if rec["kind"] == "ELASTIC_INTENT":
                    pending.add(rec["payload"]["tx"])
                elif rec["kind"] == "ELASTIC_COMMIT":
                    pending.discard(rec["payload"]["tx"])
                    commits.append(rec["payload"])
            if pending:
                raise RuntimeError("INCOMPLETE_TRANSACTION_HOLD")
            yield commits

    def read(self, commits):
        if not self.store.exists():
            document = {"schema": SCHEMA, "revision": 0, "missions": {}}
        else:
            if self.store.is_symlink() or self.store.stat().st_size > 256 * 1024:
                raise RuntimeError("ELASTIC_STATE_UNSAFE")
            document = json.loads(self.store.read_text())
        if (document.get("schema") != SCHEMA or type(document.get("revision")) is not int
                or not isinstance(document.get("missions"), dict)):
            raise RuntimeError("ELASTIC_STATE_INVALID")
        if commits and (base.digest(document) != commits[-1]["state_sha256"]):
            raise RuntimeError("ELASTIC_STATE_ROLLBACK_OR_TAMPERING")
        if not commits and self.store.exists():
            raise RuntimeError("ELASTIC_STATE_WITHOUT_EVIDENCE")
        for name, row in document["missions"].items():
            if row["request"].get("mission_id") != name or base.digest(row["request"]) != row["mission_sha256"]:
                raise RuntimeError("MISSION_DATA_TAMPERING")
        return document

    def commit(self, document, kind, report):
        tx = base.digest({"revision": document["revision"], "kind": kind,
                          "state": base.digest(document), "report": report})
        self.ledger.append("ELASTIC_INTENT", {"tx": tx, "kind": kind})
        base.atomic_json(self.store, document)
        self.ledger.append("ELASTIC_COMMIT", {"tx": tx, "kind": kind,
                           "state_sha256": base.digest(document), "report": report})

    @staticmethod
    def output(name, row, operation):
        return {"schema": SCHEMA, "mission_id": name, "operation": operation,
                "status": row["status"], "next_step": row["next_step"],
                "evidence": row["evidence"], "mission_sha256": row["mission_sha256"],
                "g23": "NOT_EXECUTED", "g24": "NOT_EXECUTED",
                "g23_2": "NOT_EXECUTED", "g24_2": "NOT_EXECUTED",
                "privileged_execution": False, "certified": False}

    def admit(self, request):
        with self.exclusive() as commits:
            validate(request, base.load_time_policy(self.state, self.contract))
            doc = self.read(commits)
            name = request["mission_id"]
            h = base.digest(request)
            if name in doc["missions"]:
                row = doc["missions"][name]
                if row["mission_sha256"] != h:
                    raise RuntimeError("MISSION_SCOPE_COLLISION")
                return self.output(name, row, "IDEMPOTENT_EXISTING")
            if len(doc["missions"]) >= 32 or self.clock() >= deadline(request["deadline_utc"]):
                raise RuntimeError("MISSION_CAPACITY_OR_DEADLINE")
            row = {"request": request, "mission_sha256": h, "status": "ADMITTED_UNCERTIFIED",
                   "next_step": 0, "evidence": []}
            doc["missions"][name] = row
            doc["revision"] += 1
            self.commit(doc, "ADMIT", {"id": name, "sha256": h})
            return self.output(name, row, "ADMITTED")

    @staticmethod
    def resource_guard(observation):
        memory = observation.get("memory_bytes", {})
        disk = observation.get("root_fs_bytes", {})
        total = memory.get("MemTotal") if isinstance(memory, dict) else None
        free = memory.get("MemAvailable") if isinstance(memory, dict) else None
        diskfree = disk.get("available") if isinstance(disk, dict) else None
        load = observation.get("load")
        if not all(type(n) in (int, float) for n in (total, free, diskfree)):
            return "HOLD_MISSING_RESOURCE_EVIDENCE"
        if total <= 0 or free / total < 0.15 or diskfree < 64 * 1024 * 1024:
            return "HOLD_RESOURCE_PRESSURE"
        if not isinstance(load, list) or not load or load[0] > max(1, os.cpu_count() or 1) * 0.85:
            return "HOLD_CPU_PRESSURE_OR_UNKNOWN"
        return None

    def run_once(self, name):
        if not isinstance(name, str) or not MID.fullmatch(name):
            raise RuntimeError("MISSION_ID_INVALID")
        with self.exclusive() as commits:
            doc = self.read(commits)
            if name not in doc["missions"]:
                raise RuntimeError("MISSION_UNKNOWN")
            row = doc["missions"][name]
            if row["status"] in ("COMPLETE_READONLY_UNCERTIFIED", "WAITING_FRESH_G23_G24"):
                return self.output(name, row, "IDEMPOTENT_NOOP")
            req = row["request"]
            policy = base.load_time_policy(self.state, self.contract)  # hot reload
            validate(req, policy)
            if self.clock() >= deadline(req["deadline_utc"]):
                return self.output(name, {**row, "status": "HOLD_DEADLINE"}, "NO_EXECUTION")
            if row["next_step"] >= req["max_auto_steps"]:
                return self.output(name, {**row, "status": "HOLD_AUTOMATION_BUDGET"}, "NO_EXECUTION")
            step = req["steps"][row["next_step"]]
            if step["kind"] == "GATED_OPERATION":
                row["status"] = "WAITING_FRESH_G23_G24"
                doc["revision"] += 1
                self.commit(doc, "HOLD_GATED", {"id": name, "capability": step["requested_capability"]})
                return self.output(name, row, "EXPLICIT_GATE_REQUIRED")
            observation = self.observer()
            reason = self.resource_guard(observation)
            if reason:
                self.ledger.append("ELASTIC_RESOURCE_HOLD", {"id": name, "reason": reason})
                return self.output(name, {**row, "status": reason}, "NO_EXECUTION")
            payload = observation if step["kind"] == "OBSERVE_LOCAL" else self.indexer(
                step["root"], limit=step.get("limit", 40))
            digest = base.digest(payload)
            row["evidence"].append({"step": row["next_step"], "kind": step["kind"],
                                     "result_sha256": digest, "effect": "READ_ONLY"})
            row["next_step"] += 1
            row["status"] = ("COMPLETE_READONLY_UNCERTIFIED" if row["next_step"] == len(req["steps"])
                             else "ADMITTED_UNCERTIFIED")
            doc["revision"] += 1
            self.commit(doc, "READONLY_STEP", {"id": name, "sha256": digest})
            return self.output(name, row, "STEP_COMPLETE")

    def report(self, name):
        with self.exclusive() as commits:
            row = self.read(commits)["missions"].get(name)
            if row is None:
                raise RuntimeError("MISSION_UNKNOWN")
            return self.output(name, row, "REPORT")


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--state-dir", default=str(base.STATE_DEFAULT))
    ap.add_argument("--contract", default=str(Path(__file__).with_name("CONTRACT.v0.json")))
    subs = ap.add_subparsers(dest="verb", required=True)
    subs.add_parser("admit").add_argument("--mission-file", required=True)
    for verb in ("run-once", "report"):
        subs.add_parser(verb).add_argument("--mission-id", required=True)
    args = ap.parse_args(argv)
    try:
        contract = json.loads(Path(args.contract).read_text())
        agent = Automation(args.state_dir, contract)
        if args.verb == "admit":
            p = Path(args.mission_file)
            if p.is_symlink() or p.stat().st_size > 32 * 1024:
                raise RuntimeError("MISSION_FILE_UNSAFE")
            output = agent.admit(json.loads(p.read_text()))
        elif args.verb == "run-once":
            output = agent.run_once(args.mission_id)
        else:
            output = agent.report(args.mission_id)
        print(json.dumps(output, indent=2, sort_keys=True))
        return 0 if not output["status"].startswith("HOLD") else 3
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "reason": str(exc)[:180]}), file=sys.stderr)
        return 3


if __name__ == "__main__":
    sys.exit(main())
