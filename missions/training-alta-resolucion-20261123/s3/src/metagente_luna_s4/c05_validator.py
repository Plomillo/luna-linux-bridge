"""Fail-closed check of C05 dossiers. Investigation is not execution."""
from __future__ import annotations

import hashlib

EXPECTED = [f"MGL5-INF-{number:04d}" for number in range(1, 1001)]
EXECUTION_OUTCOMES = {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}


def _evidence_matches(row: dict) -> bool:
    digest = row.get("evidence_sha256")
    payload = row.get("evidence_payload")
    if not isinstance(digest, str) or len(digest) != 64 or not isinstance(payload, str):
        return False
    return hashlib.sha256(payload.encode("utf-8")).hexdigest() == digest


def contradictions(row: dict) -> list[str]:
    found = []
    status = row.get("contract_status") or row.get("contractual_status")
    execution = row.get("execution_status")
    basis = row.get("basis") or row.get("promotion_basis")
    if status == "PASS" and basis == "CRITERION_MET":
        found.append("criterion-met-promoted-to-pass")
    if status == "PASS" and execution == "NOT_RUN":
        found.append("not-run-promoted-to-pass")
    if status == "PASS" and execution not in EXECUTION_OUTCOMES:
        found.append("inflated-state")
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
    if row.get("evidence_missing") is True:
        found.append("missing-evidence")
    if row.get("evidence_sha256") and row.get("evidence_payload") is not None and not _evidence_matches(row):
        found.append("incorrect-evidence-hash")
    claimed = row.get("machinery_claimed")
    observed = row.get("machinery_observed")
    if claimed and observed and claimed != observed:
        found.append("false-machinery-identity")
    if execution == "NOT_RUN" and (row.get("individual_investigation") is True or row.get("counted_as_execution") is True):
        found.append("investigation-is-not-execution")
    return found


def _authentic(row: dict) -> bool:
    if row.get("execution_status") not in EXECUTION_OUTCOMES:
        return False
    if row.get("execution_status") == "NOT_RUN":
        return False
    if contradictions(row):
        return False
    return _evidence_matches(row)


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
    passed = not problems and not rejected and authentic == 1000 and not_run == 0
    return {
        "c05_passed": passed,
        "c05_status": "PASS" if passed else "NOT_PASSED",
        "expected": 1000,
        "rows": len(rows),
        "not_run": not_run,
        "not_run_counts_as_execution": False,
        "authentic_results": authentic,
        "contractual_pass": contractual_pass,
        "rejected": rejected,
        "structure_problems": problems,
        "human_review_required": False,
        "reason": "NOT_RUN is never an execution, including when an investigation flag is set",
    }
