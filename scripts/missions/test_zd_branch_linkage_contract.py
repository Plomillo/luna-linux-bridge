#!/usr/bin/env python3
"""Regression tests for fail-closed mission/contract/PR-base linkage."""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = ROOT / "governance/zona-directiva-v03/12_STAGE_GOVERNANCE_CONTRACT.md"
MISSION = ROOT / "missions/inbox/louksna-zona-directiva-v03-functional-20261006/MISSION.md"
WORKFLOW = ROOT / ".github/workflows/louksna-zd-v03-governance.yml"


def declared_value(text: str, key: str):
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(key) and "=" in stripped:
            return stripped.split("=", 1)[1].split("#", 1)[0].strip().strip('"').strip("'")
    return None


def findings(target: str, mission_branch: str, event: str, base: str):
    result = []
    if not target:
        result.append("TARGET_WORK_BRANCH_MISSING")
    if not mission_branch:
        result.append("MISSION_WORK_BRANCH_MISSING")
    elif target and mission_branch != target:
        result.append("MISSION_CONTRACT_WORK_BRANCH_MISMATCH")
    if event == "pull_request" and target and base != target:
        result.append("PR_BASE_BRANCH_MISMATCH")
    return result


contract_text = CONTRACT.read_text(encoding="utf-8")
mission_text = MISSION.read_text(encoding="utf-8")
workflow_text = WORKFLOW.read_text(encoding="utf-8")
target = declared_value(contract_text, "TARGET_WORK_BRANCH")
mission_branch = declared_value(mission_text, "WORK_BRANCH")

checks = {
    "contract_declares_target_branch": bool(target),
    "mission_declares_work_branch": bool(mission_branch),
    "mission_and_contract_agree": bool(target) and mission_branch == target,
    "workflow_reads_pull_request_base": 'os.getenv("GITHUB_BASE_REF","")' in workflow_text,
    "workflow_fails_closed_on_base_drift": '"PR_BASE_BRANCH_MISMATCH"' in workflow_text and 'pr_base_branch != target_work_branch' in workflow_text,
    "declared_base_passes": findings(target, mission_branch, "pull_request", target) == [],
    "main_base_fails_without_explicit_exception": "PR_BASE_EXCEPTION_ID" not in contract_text and "PR_BASE_BRANCH_MISMATCH" in findings(target, mission_branch, "pull_request", "main"),
    "branch_declaration_mismatch_fails": "MISSION_CONTRACT_WORK_BRANCH_MISMATCH" in findings(target, "work/unexpected-branch", "pull_request", target),
}
report = {"schema": "louksna.zd.v03.branch-linkage-regression.v1", "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"}
print(json.dumps(report, indent=2, sort_keys=True))
if not all(checks.values()):
    raise SystemExit(1)
