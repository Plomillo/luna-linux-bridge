#!/usr/bin/env python3
"""Deterministic positive/negative tests for both mailbox dispatch modes."""
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).with_name("dispatch_execution.py")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def execute(mode="WORKFLOW_DISPATCH", mutator=None):
    with tempfile.TemporaryDirectory(prefix="mailbox-dispatch-test-") as td:
        root = pathlib.Path(td)
        wf = root / ".github/workflows/test-target.yml"
        wf.parent.mkdir(parents=True)
        if mode == "WORKFLOW_DISPATCH":
            wf.write_text(
                "name: test\non:\n  workflow_dispatch:\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n",
                encoding="utf-8",
            )
        else:
            wf.write_text(
                "name: test\non:\n  push:\n    branches:\n      - target-branch\n    paths:\n      - mission-control/test/**\n",
                encoding="utf-8",
            )
        results = root / "results"
        out = root / "out"
        results.mkdir()
        adapter = {
            "adapter_id": "TEST",
            "provides_executor_binding": True,
            "dispatch_mode": mode,
            "dedicated_workflow": ".github/workflows/test-target.yml",
            "dedicated_workflow_sha256": sha(wf),
        }
        if mode == "PUSH_TRIGGER_FILE":
            adapter["dispatch_ref"] = "target-branch"
            adapter["dispatch_trigger_path_prefix"] = "mission-control/test/"
        plan = {
            "schema": "CUSTOSZ_EXECUTION_PLAN/1.1",
            "mail_id": "MAIL-TEST",
            "adapter": adapter,
            "binding_mode": "ADAPTER_PROVIDED_PENDING",
            "status": "ROUTED_READY_NOT_YET_EXECUTED",
        }
        (results / "EXECUTION_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
        (results / "MISSION_STATE.json").write_text(json.dumps({"history": []}), encoding="utf-8")
        if mutator:
            mutator(root, plan)
            (results / "EXECUTION_PLAN.json").write_text(json.dumps(plan), encoding="utf-8")
        p = subprocess.run([
            sys.executable, "-B", "-I", str(SCRIPT),
            "--results", str(results), "--repo-root", str(root),
            "--repo", "owner/repo", "--ref", "source-branch",
            "--out", str(out), "--dry-run",
        ], text=True, capture_output=True)
        report = json.loads((out / "MATERIAL_DISPATCH.json").read_text())
        return p.returncode, report


for mode in ("WORKFLOW_DISPATCH", "PUSH_TRIGGER_FILE"):
    rc, rep = execute(mode)
    assert rc == 0 and rep["status"] == "PASS" and rep["dispatch_performed"] is False, (mode, rc, rep)

def corrupt(root, plan):
    (root / ".github/workflows/test-target.yml").write_text("name: changed\non:\n  workflow_dispatch:\n", encoding="utf-8")

rc, rep = execute("WORKFLOW_DISPATCH", corrupt)
assert rc == 23 and rep["root_blocker"] == "WORKFLOW_SHA256_MISMATCH"

def remove_binding(root, plan):
    plan["adapter"].pop("dedicated_workflow")

rc, rep = execute("WORKFLOW_DISPATCH", remove_binding)
assert rc == 23 and rep["root_blocker"] == "MATERIAL_DISPATCH_CONTRACT_INCOMPLETE"

print("MAILBOX_DISPATCH_BRIDGE_SELFTEST=PASS")
