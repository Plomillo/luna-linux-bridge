"""Append-only reconciliation. Historical dossiers are read and never rewritten."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REPORTS = ROOT / "reports"
LEDGERS = [
    "S4_2_CASE_EXECUTION_RESULTS.jsonl",
    "S4_2_CASE_EXECUTION_RESULTS_BATCH2.jsonl",
    "S4_2_CASE_EXECUTION_RESULTS_BATCH3.jsonl",
    "S4_2_CASE_EXECUTION_RESULTS_BATCH4.jsonl",
    "S4_2_CASE_EXECUTION_RESULTS_BATCH5.jsonl",
    "S4_2_CASE_EXECUTION_RESULTS_BATCH6.jsonl",
]
WITHDRAWN = {"MGL5-INF-0106", "MGL5-INF-0109", "MGL5-INF-0632"}
REASONS = {
    "MGL5-INF-0106": "The length is explicit. The 10000 integers are not. A seed does not define the generator or the distribution, and a checksum is not a permutation.",
    "MGL5-INF-0109": "The instruction says the sequence is predefined but does not contain the steps.",
    "MGL5-INF-0632": "Window 3 is explicit. The series and its length are not. The earlier length of 6 was not in the source.",
}


def _rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def corpus_path() -> Path:
    candidate = Path(__file__).resolve().parents[3] / "results" / "M0-20261124.2" / "CORPUS_RESULTS.jsonl"
    if candidate.exists():
        return candidate
    fallback = Path("/tmp/CORPUS_RESULTS.jsonl")
    if fallback.exists():
        return fallback
    raise FileNotFoundError(candidate)


def helper_index() -> dict[str, dict]:
    found: dict[str, dict] = {}
    for name in LEDGERS:
        for row in _rows(REPORTS / name):
            found[row["case_id"]] = row
    return found


def intersection() -> dict:
    m0 = _rows(corpus_path())
    passed = {row["CASE_ID"] for row in m0 if row["VERDICT"] == "PASS"}
    failed = {row["CASE_ID"] for row in m0 if row["VERDICT"] == "FAIL"}
    helpers = helper_index()
    met = {case_id for case_id, row in helpers.items() if row.get("execution_status") == "CRITERION_MET"}
    blocked = {case_id for case_id, row in helpers.items() if row.get("execution_status") == "BLOCKED"}
    return {
        "m0_pass": len(passed),
        "m0_fail": len(failed),
        "helper_records": len(helpers),
        "helper_criterion_met": len(met),
        "helper_blocked": len(blocked),
        "met_inside_m0_fail": len(met & failed),
        "met_inside_m0_pass": len(met & passed),
        "blocked_inside_m0_fail": len(blocked & failed),
        "m0_fail_without_helper": len(failed - set(helpers)),
        "identity": "83 + 3 + 894 = 980" if (len(met & failed), len(blocked & failed), len(failed - set(helpers))) == (83, 3, 894) else "MISMATCH",
        "withdrawn_helper_claims": sorted(WITHDRAWN),
        "contractual_pass": 0,
    }


def amendments() -> list[dict]:
    m0 = {row["CASE_ID"]: row for row in _rows(corpus_path())}
    records = []
    for case_id, helper in sorted(helper_index().items()):
        historical = helper.get("execution_status")
        withdrawn = case_id in WITHDRAWN
        records.append({
            "CASE_ID": case_id,
            "AMENDMENT_ID": f"AMD-{case_id}-HELPER",
            "M0_HISTORICAL_RESULT": m0[case_id]["VERDICT"],
            "S4_HELPER_RESULT": historical,
            "HELPER_DISPOSITION": "WITHDRAWN" if withdrawn else historical,
            "ROOT_CAUSE": REASONS.get(case_id),
            "CONTRACTUAL_RESULT": "BLOCKED" if withdrawn or historical == "BLOCKED" else "NOT_RUN",
            "STATE_JUSTIFICATION": "helper output is not contractual PASS",
            "TIMESTAMP": "2026-11-26T20:48:00Z",
            "AUTHOR_OR_PROCESS": "metagente-luna-s4-reconcile",
        })
    return records


def projection() -> list[dict]:
    linked = {row["CASE_ID"]: row for row in amendments()}
    projected = []
    for row in _rows(REPORTS / "S4_2_C05_DOSSIERS.jsonl"):
        amendment = linked.get(row["CASE_ID"])
        projected.append({
            "CASE_ID": row["CASE_ID"],
            "historical_execution_status": row["execution_status"],
            "historical_contract_status": row.get("contract_status"),
            "amendment_id": None if amendment is None else amendment["AMENDMENT_ID"],
            "m0_historical_result": None if amendment is None else amendment["M0_HISTORICAL_RESULT"],
            "s4_helper_result": None if amendment is None else amendment["S4_HELPER_RESULT"],
            "helper_disposition": None if amendment is None else amendment["HELPER_DISPOSITION"],
            "contractual_result": "NOT_RUN" if amendment is None else amendment["CONTRACTUAL_RESULT"],
        })
    return projected


def manifest() -> dict:
    historical = REPORTS / "S4_2_C05_DOSSIERS.jsonl"
    digest = hashlib.sha256(historical.read_bytes()).hexdigest()
    rows = _rows(historical)
    return {
        "historical_dossier_sha256": digest,
        "historical_rows": len(rows),
        "historical_not_run": sum(row.get("execution_status") == "NOT_RUN" for row in rows),
        "amendments": len(amendments()),
        "projection_rows": len(projection()),
        "intersection": intersection(),
        "c05_status": "NOT_PASSED",
        "global_condition_counter": "4/26",
    }
