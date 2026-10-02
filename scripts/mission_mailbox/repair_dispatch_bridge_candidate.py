#!/usr/bin/env python3
"""Build the governed candidate that closes the CUSTOSZ mailbox router->execution gap.

This script edits only the mailbox dispatch surface in a checked-out worktree.
It does not dispatch workflows itself and does not mutate Louksna.md.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

BRANCH = "staging/mailbox-dispatch-bridge-repair-20261002"
REGISTRY = Path("mission-mailbox/runtime-adapters/registry.json")
MAILBOX_WF = Path(".github/workflows/custosz-mission-mailbox.yml")
DISPATCHER = Path("scripts/mission_mailbox/dispatch_execution.py")
TESTER = Path("scripts/mission_mailbox/test_dispatch_execution.py")
MARKER = "MAILBOX_TERMINAL_DISPATCH_BRIDGE_V1"

WORKFLOW_BINDINGS = {
    "FINAL_SERVER_READY_CLOSURE_V1": ".github/workflows/server-ready-final-material.yml",
    "SERVER_READY_TERMINAL_10M_V1": ".github/workflows/server-ready-terminal-chain.yml",
    "LUNA_R4_PART1_RESUME_APC48_V2_36519487206": ".github/workflows/luna-r4-master-resume-now.yml",
}

DISPATCHER_SOURCE = r'''#!/usr/bin/env python3
"""Dispatch one already-routed mailbox mission through its pinned GitHub workflow.

The router remains a classifier/binder. This bridge consumes EXECUTION_PLAN.json,
verifies the exact workflow binding and SHA-256 pin, and performs workflow_dispatch.
It never invents an executor and never treats dispatch as terminal success.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def utc():
    return datetime.now(timezone.utc).isoformat()


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def fail(out, mail_id, blocker, checks, plan=None):
    report = {
        "schema": "CUSTOSZ_MAILBOX_MATERIAL_DISPATCH/1.0",
        "status": "HOLD",
        "mail_id": mail_id,
        "root_blocker": blocker,
        "checks": checks,
        "dispatch_performed": False,
        "terminal_success_claimed": False,
        "plan": plan,
        "utc": utc(),
    }
    atomic_json(Path(out) / "MATERIAL_DISPATCH.json", report)
    return 23


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", required=True)
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--repo", required=True)
    ap.add_argument("--ref", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true")
    q = ap.parse_args()

    results = Path(q.results)
    root = Path(q.repo_root).resolve()
    out = Path(q.out)
    out.mkdir(parents=True, exist_ok=True)
    plan_path = results / "EXECUTION_PLAN.json"
    state_path = results / "MISSION_STATE.json"

    if not plan_path.is_file():
        return fail(out, "UNKNOWN", "EXECUTION_PLAN_MISSING", {"execution_plan_present": False})

    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    mail_id = str(plan.get("mail_id") or "UNKNOWN")
    adapter = plan.get("adapter") or {}
    workflow = adapter.get("dedicated_workflow")
    expected_sha = adapter.get("dedicated_workflow_sha256")

    checks = {
        "plan_status": plan.get("status") == "ROUTED_READY_NOT_YET_EXECUTED",
        "adapter_present": bool(adapter),
        "provider_binding_explicit": adapter.get("provides_executor_binding") is True,
        "workflow_declared": isinstance(workflow, str) and bool(workflow),
        "workflow_sha_declared": isinstance(expected_sha, str) and len(expected_sha) == 64,
        "workflow_path_bounded": isinstance(workflow, str) and workflow.startswith(".github/workflows/") and ".." not in workflow,
    }
    if not all(checks.values()):
        return fail(out, mail_id, "MATERIAL_DISPATCH_CONTRACT_INCOMPLETE", checks, plan)

    wf = (root / workflow).resolve()
    workflows_root = (root / ".github/workflows").resolve()
    checks["workflow_within_root"] = workflows_root in wf.parents
    checks["workflow_exists"] = wf.is_file()
    if wf.is_file():
        checks["workflow_sha256_match"] = sha(wf) == expected_sha
        text = wf.read_text(encoding="utf-8", errors="strict")
        checks["workflow_dispatch_supported"] = "workflow_dispatch:" in text
    else:
        checks["workflow_sha256_match"] = False
        checks["workflow_dispatch_supported"] = False

    if not all(checks.values()):
        blocker = "WORKFLOW_SHA256_MISMATCH" if checks.get("workflow_exists") and not checks.get("workflow_sha256_match") else "PINNED_WORKFLOW_NOT_DISPATCHABLE"
        return fail(out, mail_id, blocker, checks, plan)

    action = {
        "repo": q.repo,
        "ref": q.ref,
        "workflow_path": workflow,
        "workflow_file": Path(workflow).name,
        "workflow_sha256": expected_sha,
    }

    if not q.dry_run:
        if not os.environ.get("GH_TOKEN"):
            return fail(out, mail_id, "GH_TOKEN_MISSING", checks, plan)
        cmd = [
            "gh", "api", "--method", "POST",
            f"repos/{q.repo}/actions/workflows/{Path(workflow).name}/dispatches",
            "-f", f"ref={q.ref}",
        ]
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=45)
        action["exit_code"] = proc.returncode
        action["stdout"] = proc.stdout[-2000:]
        action["stderr"] = proc.stderr[-2000:]
        if proc.returncode != 0:
            return fail(out, mail_id, "WORKFLOW_DISPATCH_FAILED", {**checks, "gh_dispatch_exit_zero": False}, plan)
        checks["gh_dispatch_exit_zero"] = True

    report = {
        "schema": "CUSTOSZ_MAILBOX_MATERIAL_DISPATCH/1.0",
        "status": "PASS" if q.dry_run else "DISPATCHED",
        "mail_id": mail_id,
        "adapter_id": adapter.get("adapter_id"),
        "binding_mode": plan.get("binding_mode"),
        "checks": checks,
        "dispatch": action,
        "dispatch_performed": not q.dry_run,
        "terminal_success_claimed": False,
        "next_gate": "MATERIAL_EXECUTION_WORKFLOW",
        "utc": utc(),
    }
    atomic_json(out / "MATERIAL_DISPATCH.json", report)

    if state_path.is_file():
        state = json.loads(state_path.read_text(encoding="utf-8"))
        history = list(state.get("history", []))
        history.append({
            "utc": utc(),
            "state": "DISPATCH_READY" if q.dry_run else "DISPATCHED",
            "adapter_id": adapter.get("adapter_id"),
            "workflow": workflow,
        })
        state.update({
            "workflow_technical_status": "PASS",
            "mission_terminal_status": None,
            "current_state": "DISPATCH_READY" if q.dry_run else "DISPATCHED",
            "current_gate": "MATERIAL_EXECUTION_WORKFLOW",
            "root_blocker": None,
            "history": history,
        })
        atomic_json(out / "MISSION_STATE.json", state)

    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''

TEST_SOURCE = r'''#!/usr/bin/env python3
"""Deterministic negative/positive tests for the mailbox dispatch bridge."""
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import tempfile

SCRIPT = pathlib.Path(__file__).with_name("dispatch_execution.py")


def sha(p):
    return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()


def run_case(mutator=None):
    with tempfile.TemporaryDirectory(prefix="mailbox-dispatch-test-") as td:
        root = pathlib.Path(td)
        wf = root / ".github/workflows/test-target.yml"
        wf.parent.mkdir(parents=True)
        wf.write_text("name: test\non:\n  workflow_dispatch:\njobs:\n  x:\n    runs-on: ubuntu-24.04\n    steps:\n      - run: true\n", encoding="utf-8")
        results = root / "results"
        out = root / "out"
        results.mkdir()
        adapter = {
            "adapter_id": "TEST",
            "provides_executor_binding": True,
            "dedicated_workflow": ".github/workflows/test-target.yml",
            "dedicated_workflow_sha256": sha(wf),
        }
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
            "--repo", "owner/repo", "--ref", "branch",
            "--out", str(out), "--dry-run",
        ], text=True, capture_output=True)
        report = json.loads((out / "MATERIAL_DISPATCH.json").read_text())
        return p.returncode, report


rc, rep = run_case()
assert rc == 0 and rep["status"] == "PASS" and rep["dispatch_performed"] is False

def corrupt(root, plan):
    (root / ".github/workflows/test-target.yml").write_text("name: changed\non:\n  workflow_dispatch:\n", encoding="utf-8")

rc, rep = run_case(corrupt)
assert rc == 23 and rep["root_blocker"] == "WORKFLOW_SHA256_MISMATCH"

def remove_binding(root, plan):
    plan["adapter"].pop("dedicated_workflow")

rc, rep = run_case(remove_binding)
assert rc == 23 and rep["root_blocker"] == "MATERIAL_DISPATCH_CONTRACT_INCOMPLETE"

print("MAILBOX_DISPATCH_BRIDGE_SELFTEST=PASS")
'''

DISPATCH_JOB = r'''
  dispatch:
    name: "Dispatch pinned material workflow"
    needs: [compile, route]
    if: needs.compile.outputs.pending_count != '0' && needs.route.result == 'success'
    runs-on: ubuntu-24.04
    timeout-minutes: 5
    permissions:
      contents: read
      actions: write
    steps:
      - name: Checkout exact dispatch surface
        uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683
        with:
          persist-credentials: false
          fetch-depth: 1
          sparse-checkout: |
            .github/workflows
            scripts/mission_mailbox/dispatch_execution.py
          sparse-checkout-cone-mode: false

      - name: Recover routed execution plans
        uses: actions/download-artifact@d3f86a106a0bac45b974a628896c90dbdf5c8093
        with:
          name: custosz-mailbox-results
          path: ${{ runner.temp }}/mailbox-results

      - name: MAILBOX_TERMINAL_DISPATCH_BRIDGE_V1
        shell: bash
        env:
          GH_TOKEN: ${{ github.token }}
          RESULTS: ${{ runner.temp }}/mailbox-results
          OUT: ${{ runner.temp }}/mailbox-dispatch
        run: |
          set -Eeuo pipefail
          mkdir -p "$OUT"
          failures=0
          count=0
          while IFS= read -r plan; do
            count=$((count+1))
            src="$(dirname "$plan")"
            mail_id="$(basename "$src")"
            mkdir -p "$OUT/$mail_id"
            rc=0
            python3 -B -I scripts/mission_mailbox/dispatch_execution.py               --results "$src"               --repo-root .               --repo "$GITHUB_REPOSITORY"               --ref "$GITHUB_REF_NAME"               --out "$OUT/$mail_id" || rc=$?
            if [ "$rc" -ne 0 ]; then failures=$((failures+1)); fi
          done < <(find "$RESULTS" -mindepth 2 -maxdepth 2 -name EXECUTION_PLAN.json -print | sort)
          echo "EXECUTION_PLANS=$count"
          echo "DISPATCH_FAILURES=$failures"
          test "$failures" -eq 0

      - name: Preserve material dispatch evidence
        if: always()
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02
        with:
          name: custosz-mailbox-dispatch
          path: ${{ runner.temp }}/mailbox-dispatch
          if-no-files-found: warn
'''

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo-root", default=".")
    ap.add_argument("--out", required=True)
    q = ap.parse_args()
    root = Path(q.repo_root).resolve()
    out = Path(q.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    reg_path = root / REGISTRY
    wf_path = root / MAILBOX_WF
    if not reg_path.is_file() or not wf_path.is_file():
        raise SystemExit("MAILBOX_SURFACE_MISSING")

    current = wf_path.read_text(encoding="utf-8")
    if "ROUTED_READY_NOT_YET_EXECUTED" not in (root / "scripts/mission_mailbox/route_mission.py").read_text(encoding="utf-8"):
        raise SystemExit("DEFECT_SIGNATURE_NOT_PRESENT")
    if MARKER in current:
        raise SystemExit("DISPATCH_BRIDGE_ALREADY_PRESENT")

    registry = json.loads(reg_path.read_text(encoding="utf-8"))
    for entry in registry.get("adapters", []):
        aid = entry.get("adapter_id")
        if aid in WORKFLOW_BINDINGS:
            entry["dedicated_workflow"] = WORKFLOW_BINDINGS[aid]
        workflow = entry.get("dedicated_workflow")
        if entry.get("status") == "ACTIVE_PINNED":
            if not workflow:
                raise SystemExit("ACTIVE_PINNED_ADAPTER_WITHOUT_WORKFLOW:" + str(aid))
            wp = root / workflow
            if not wp.is_file():
                raise SystemExit("DEDICATED_WORKFLOW_MISSING:" + str(workflow))
            if "workflow_dispatch:" not in wp.read_text(encoding="utf-8"):
                raise SystemExit("DEDICATED_WORKFLOW_NOT_DISPATCHABLE:" + str(workflow))
            entry["dedicated_workflow_sha256"] = sha(wp)

    reg_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (root / DISPATCHER).write_text(DISPATCHER_SOURCE, encoding="utf-8")
    (root / TESTER).write_text(TEST_SOURCE, encoding="utf-8")
    wf_path.write_text(current.rstrip() + "\n" + DISPATCH_JOB.lstrip("\n"), encoding="utf-8")

    changed = [REGISTRY, MAILBOX_WF, DISPATCHER, TESTER]
    manifest = {
        "schema": "LOUKSNA_MAILBOX_DISPATCH_BRIDGE_REPAIR_CANDIDATE/1.0",
        "status": "CANDIDATE",
        "authority": "Louksna.md",
        "branch": BRANCH,
        "defect": "ROUTER_STOPS_AT_ROUTED_READY_NOT_YET_EXECUTED_WITHOUT_GENERAL_MATERIAL_DISPATCH",
        "repair": "HOSTED_POST_ROUTE_WORKFLOW_DISPATCH_BOUND_TO_PINNED_ADAPTER_WORKFLOW",
        "changed_files": [
            {"path": str(p), "sha256": sha(root / p), "bytes": (root / p).stat().st_size}
            for p in changed
        ],
        "invariants": {
            "louksna_mutated": False,
            "router_classification_semantics_mutated": False,
            "material_dispatch_is_terminal_success": False,
            "active_pinned_requires_dispatch_contract": True,
            "workflow_sha256_pin_required": True,
            "dispatch_runs_on_github_hosted": True,
            "self_certification": False,
        },
    }
    raw = json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    (out / "REPAIR_MANIFEST.json").write_text(raw, encoding="utf-8")
    print(raw, end="")


if __name__ == "__main__":
    raise SystemExit(main())
