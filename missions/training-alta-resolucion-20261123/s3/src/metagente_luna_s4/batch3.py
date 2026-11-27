"""Third batch. These ids were not in the first fifty."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

CASES = [
    {"case_id": "MGL5-INF-0107", "capability_id": "duplicates", "arguments": {"values": [1, 2, 3, 2, 4, 1]}},
    {"case_id": "MGL5-INF-0108", "capability_id": "brackets", "arguments": {"texts": ["({[]})", "([)]"]}},
    {"case_id": "MGL5-INF-0112", "capability_id": "binary_insert", "arguments": {"values": [8, 3, 10, 1, 6, 14]}},
    {"case_id": "MGL5-INF-0125", "capability_id": "arithmetic", "arguments": {"expression": "2+3*4"}},
    {"case_id": "MGL5-INF-0155", "capability_id": "arithmetic", "arguments": {"expression": "(1+2)*3"}},
    {"case_id": "MGL5-INF-0168", "capability_id": "arithmetic", "arguments": {"expression": "2*3+4"}},
    {"case_id": "MGL5-INF-0202", "capability_id": "child_status", "arguments": {"exit_code": 7}},
    {"case_id": "MGL5-INF-0253", "capability_id": "ipv6_reject", "arguments": {"address": "2001:db8::1::2"}},
    {"case_id": "MGL5-INF-0254", "capability_id": "cidr_bounds", "arguments": {"cidr": "192.0.2.130/26"}},
    {"case_id": "MGL5-INF-0255", "capability_id": "ipv6_prefix", "arguments": {"cidr": "2001:db8:abcd:12::5/64"}},
    {"case_id": "MGL5-INF-0435", "capability_id": "threshold", "arguments": {"low": 38, "high": 38.1, "limit": 38}},
    {"case_id": "MGL5-INF-0608", "capability_id": "l2_norm", "arguments": {"components": [3, 4, 12]}},
    {"case_id": "MGL5-INF-0763", "capability_id": "ratio", "arguments": {"numerator": 80, "denominator": 100}},
    {"case_id": "MGL5-INF-0764", "capability_id": "precision_recall", "arguments": {"true_positive": 40, "false_positive": 10, "false_negative": 20}},
    {"case_id": "MGL5-INF-0765", "capability_id": "f1_score", "arguments": {"precision": 0.8, "recall": 40 / 60}},
]


def run_all() -> list[dict]:
    rows = []
    for spec in CASES:
        runs = [execute(spec["capability_id"], spec["arguments"], spec["case_id"]) for _ in range(3)]
        observed = [run["observed"] for run in runs]
        stable = [{key: value for key, value in item.items() if key != "pid"} if isinstance(item, dict) else item for item in observed]
        ok = all(run["execution_status"] == "EXECUTED" for run in runs) and all(item == stable[0] for item in stable)
        rows.append({
            "case_id": spec["case_id"],
            "observed": observed[0],
            "execution_status": "CRITERION_MET" if ok else "FAIL",
            "stderr": runs[0]["stderr"],
            "oracle_method": None if not runs[0]["oracle_result"] else runs[0]["oracle_result"].get("method"),
            "repetitions": [run["run_id"] for run in runs],
            "backend": "LOCAL_TEST_ONLY",
            "c05_gate": "NOT_PASSED",
        })
    return rows
