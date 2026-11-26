"""Fail-closed check of C05 dossiers. A helper label is not a contractual PASS."""
from __future__ import annotations

EXPECTED = [f"MGL5-INF-{number:04d}" for number in range(1, 1001)]


def contradictions(row: dict) -> list[str]:
    found = []
    status = row.get("contract_status") or row.get("contractual_status")
    basis = row.get("basis") or row.get("promotion_basis")
    if status == "PASS" and basis == "CRITERION_MET":
        found.append("criterion-met-promoted-to-pass")
    if status == "PASS" and not row.get("fixture_sha256"):
        found.append("pass-without-fixture-hash")
    if status == "PASS" and row.get("oracle_mode") == "same-implementation":
        found.append("circular-oracle")
    runs = row.get("run_ids") or []
    if len(runs) != len(set(runs)):
        found.append("duplicate-run-id")
    if row.get("human_reviewer") and not row.get("human_review_evidence"):
        found.append("reviewer-without-evidence")
    if row.get("repetitions_copied") is True:
        found.append("copied-repetition")
    return found


def _authentic(row: dict) -> bool:
    status = row.get("execution_status")
    if status in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"} and row.get("evidence_sha256"):
        return True
    return status == "NOT_RUN" and row.get("individual_investigation") is True


def validate(rows: list[dict]) -> dict:
    identifiers = [row.get("CASE_ID") or row.get("case_id") for row in rows]
    problems = []
    if identifiers != EXPECTED:
        missing = [case_id for case_id in EXPECTED if case_id not in set(identifiers)]
        unknown = [case_id for case_id in identifiers if case_id not in set(EXPECTED)]
        problems.append({"missing": len(missing), "unknown": len(unknown), "duplicates": len(identifiers) - len(set(identifiers))})
    rejected = []
    not_run = 0
    contractual_pass = 0
    authentic = 0
    for row in rows:
        reasons = contradictions(row)
        if reasons:
            rejected.append({"case_id": row.get("CASE_ID") or row.get("case_id"), "reasons": reasons})
        if row.get("execution_status") == "NOT_RUN":
            not_run += 1
        if row.get("contract_status") == "PASS":
            contractual_pass += 1
        if _authentic(row):
            authentic += 1
    return {
        "c05_passed": not problems and not rejected and authentic == 1000,
        "c05_status": "PASS" if not problems and not rejected and authentic == 1000 else "NOT_PASSED",
        "expected": 1000,
        "rows": len(rows),
        "not_run": not_run,
        "authentic_results": authentic,
        "contractual_pass": contractual_pass,
        "rejected": rejected,
        "structure_problems": problems,
        "human_review_required": False,
        "reason": "a helper label or a historical NOT_RUN is not an authentic completed result",
    }
