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


def exception_applies(contract: str, event: str, pr_number: str, head: str, base: str):
    return (
        event == "pull_request"
        and bool(declared_value(contract, "PR_BASE_EXCEPTION_ID"))
        and pr_number == declared_value(contract, "PR_BASE_EXCEPTION_PR")
        and head == declared_value(contract, "PR_BASE_EXCEPTION_HEAD")
        and base == declared_value(contract, "PR_BASE_EXCEPTION_BASE")
        and declared_value(contract, "PR_BASE_EXCEPTION_STATUS") == "REVIEW_ONLY"
        and declared_value(contract, "PR_BASE_EXCEPTION_NO_MERGE") == "TRUE"
        and declared_value(contract, "PR_BASE_EXCEPTION_NO_MAIN_MUTATION") == "TRUE"
        and declared_value(contract, "PR_BASE_EXCEPTION_NO_AUTO_CERTIFICATION") == "TRUE"
    )


def findings(contract: str, target: str, mission_branch: str, event: str, base: str, head: str, pr_number: str):
    result = []
    if not target:
        result.append("TARGET_WORK_BRANCH_MISSING")
    if not mission_branch:
        result.append("MISSION_WORK_BRANCH_MISSING")
    elif target and mission_branch != target:
        result.append("MISSION_CONTRACT_WORK_BRANCH_MISMATCH")
    if event == "pull_request" and target and base != target and not exception_applies(contract, event, pr_number, head, base):
        result.append("PR_BASE_BRANCH_MISMATCH")
    return result


contract_text = CONTRACT.read_text(encoding="utf-8")
mission_text = MISSION.read_text(encoding="utf-8")
workflow_text = WORKFLOW.read_text(encoding="utf-8")
target = declared_value(contract_text, "TARGET_WORK_BRANCH")
mission_branch = declared_value(mission_text, "WORK_BRANCH")
exception_id = declared_value(contract_text, "PR_BASE_EXCEPTION_ID")
exception_head = declared_value(contract_text, "PR_BASE_EXCEPTION_HEAD")
exception_base = declared_value(contract_text, "PR_BASE_EXCEPTION_BASE")

checks = {
    "contract_declares_target_branch": bool(target),
    "mission_declares_work_branch": bool(mission_branch),
    "mission_and_contract_agree": bool(target) and mission_branch == target,
    "workflow_reads_pull_request_base": 'os.getenv("GITHUB_BASE_REF","")' in workflow_text,
    "workflow_reads_PR_event_number": 'event_payload.get("number","")' in workflow_text,
    "workflow_enforces_base_or_exact_exception": '"PR_BASE_BRANCH_MISMATCH"' in workflow_text and 'not exception_applies' in workflow_text,
    "declared_base_passes": findings(contract_text, target, mission_branch, "pull_request", target, exception_head or "", "62") == [],
    "exact_review_only_exception_passes": bool(exception_id) and exception_applies(contract_text, "pull_request", "62", exception_head or "", exception_base or ""),
    "exception_rejects_wrong_head": "PR_BASE_BRANCH_MISMATCH" in findings(contract_text, target, mission_branch, "pull_request", exception_base or "", "work/unexpected-head", "62"),
    "exception_rejects_wrong_PR": "PR_BASE_BRANCH_MISMATCH" in findings(contract_text, target, mission_branch, "pull_request", exception_base or "", exception_head or "", "999"),
    "branch_declaration_mismatch_fails": "MISSION_CONTRACT_WORK_BRANCH_MISMATCH" in findings(contract_text, target, "work/unexpected-branch", "pull_request", target or "", exception_head or "", "62"),
}
report = {"schema": "louksna.zd.v03.branch-linkage-regression.v1", "checks": checks, "status": "PASS" if all(checks.values()) else "FAIL"}
print(json.dumps(report, indent=2, sort_keys=True))
if not all(checks.values()):
    raise SystemExit(1)
