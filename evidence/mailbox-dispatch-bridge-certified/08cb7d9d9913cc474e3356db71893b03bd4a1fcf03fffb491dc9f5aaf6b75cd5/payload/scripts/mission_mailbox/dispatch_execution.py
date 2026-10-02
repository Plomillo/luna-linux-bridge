#!/usr/bin/env python3
"""Dispatch one already-routed mailbox mission through an explicit GitHub contract.

Supported contracts:
- WORKFLOW_DISPATCH: GitHub Actions workflow_dispatch on a SHA-pinned workflow.
- PUSH_TRIGGER_FILE: create one immutable mission-control trigger in the pinned
  target branch for an existing push/path-triggered workflow.

The bridge never invents an executor and never treats dispatch as terminal success.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
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


def gh(cmd):
    return subprocess.run(["gh", "api", *cmd], text=True, capture_output=True, timeout=45)


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
    mode = adapter.get("dispatch_mode")
    workflow = adapter.get("dedicated_workflow")
    expected_sha = adapter.get("dedicated_workflow_sha256")
    target_ref = adapter.get("dispatch_ref") or q.ref
    trigger_prefix = adapter.get("dispatch_trigger_path_prefix")

    checks = {
        "plan_status": plan.get("status") == "ROUTED_READY_NOT_YET_EXECUTED",
        "adapter_present": bool(adapter),
        "provider_binding_explicit": adapter.get("provides_executor_binding") is True,
        "dispatch_mode_known": mode in {"WORKFLOW_DISPATCH", "PUSH_TRIGGER_FILE"},
        "workflow_declared": isinstance(workflow, str) and bool(workflow),
        "workflow_sha_declared": isinstance(expected_sha, str) and len(expected_sha) == 64,
        "workflow_path_bounded": isinstance(workflow, str) and workflow.startswith(".github/workflows/") and ".." not in workflow,
        "target_ref_declared": isinstance(target_ref, str) and bool(target_ref),
    }
    if mode == "PUSH_TRIGGER_FILE":
        checks["trigger_prefix_declared"] = (
            isinstance(trigger_prefix, str)
            and trigger_prefix.startswith("mission-control/")
            and trigger_prefix.endswith("/")
            and ".." not in trigger_prefix
        )

    if not all(checks.values()):
        return fail(out, mail_id, "MATERIAL_DISPATCH_CONTRACT_INCOMPLETE", checks, plan)

    wf = (root / workflow).resolve()
    workflows_root = (root / ".github/workflows").resolve()
    checks["workflow_within_root"] = workflows_root in wf.parents
    checks["workflow_exists"] = wf.is_file()
    text = wf.read_text(encoding="utf-8", errors="strict") if wf.is_file() else ""
    checks["workflow_sha256_match"] = wf.is_file() and sha(wf) == expected_sha

    if mode == "WORKFLOW_DISPATCH":
        checks["dispatch_surface_matches_mode"] = "workflow_dispatch:" in text
    else:
        checks["dispatch_surface_matches_mode"] = (
            trigger_prefix in text and target_ref in text
        )

    if not all(checks.values()):
        blocker = (
            "WORKFLOW_SHA256_MISMATCH"
            if checks.get("workflow_exists") and not checks.get("workflow_sha256_match")
            else "PINNED_WORKFLOW_NOT_DISPATCHABLE"
        )
        return fail(out, mail_id, blocker, checks, plan)

    action = {
        "repo": q.repo,
        "source_ref": q.ref,
        "target_ref": target_ref,
        "dispatch_mode": mode,
        "workflow_path": workflow,
        "workflow_file": Path(workflow).name,
        "workflow_sha256": expected_sha,
    }

    if not q.dry_run:
        if not os.environ.get("GH_TOKEN"):
            return fail(out, mail_id, "GH_TOKEN_MISSING", checks, plan)

        if mode == "WORKFLOW_DISPATCH":
            proc = gh([
                "--method", "POST",
                f"repos/{q.repo}/actions/workflows/{Path(workflow).name}/dispatches",
                "-f", f"ref={target_ref}",
            ])
            action["api_operation"] = "ACTIONS_WORKFLOW_DISPATCH"
        else:
            safe_mail = re.sub(r"[^A-Za-z0-9_.-]+", "-", mail_id).strip("-") or "MAIL"
            run_id = os.environ.get("GITHUB_RUN_ID", "manual")
            trigger_path = f"{trigger_prefix}{safe_mail}-{run_id}.json"
            payload = {
                "schema": "CUSTOSZ_MAILBOX_PUSH_TRIGGER/1.0",
                "mail_id": mail_id,
                "adapter_id": adapter.get("adapter_id"),
                "source_sha256": adapter.get("source_sha256"),
                "source_ref": q.ref,
                "target_ref": target_ref,
                "workflow_sha256": expected_sha,
                "created_utc": utc(),
                "terminal_success_claimed": False,
            }
            encoded = base64.b64encode(
                (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()
            ).decode()
            proc = gh([
                "--method", "PUT",
                f"repos/{q.repo}/contents/{trigger_path}",
                "-f", f"message=mission(mailbox): dispatch {mail_id}",
                "-f", f"branch={target_ref}",
                "-f", f"content={encoded}",
            ])
            action["api_operation"] = "CONTENTS_PUSH_TRIGGER"
            action["trigger_path"] = trigger_path

        action["exit_code"] = proc.returncode
        action["stdout"] = proc.stdout[-2000:]
        action["stderr"] = proc.stderr[-2000:]
        if proc.returncode != 0:
            return fail(out, mail_id, "WORKFLOW_DISPATCH_FAILED", {**checks, "github_dispatch_exit_zero": False}, plan)
        checks["github_dispatch_exit_zero"] = True

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
            "dispatch_mode": mode,
            "target_ref": target_ref,
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
