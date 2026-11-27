"""Fourth batch. None of these ids were executed before."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

PAIRS = [[[1, 0], [1, 0]], [[1, 0], [0, 1]], [[1, 0], [-1, 0]]]
CASES = [
    {"case_id": "MGL5-INF-0142", "capability_id": "confined", "arguments": {"requested": "../../etc/passwd"}},
    {"case_id": "MGL5-INF-0411", "capability_id": "cosine_set", "arguments": {"pairs": PAIRS}},
    {"case_id": "MGL5-INF-0555", "capability_id": "increment", "arguments": {"times": 100}},
    {"case_id": "MGL5-INF-0561", "capability_id": "request_log", "arguments": {"successes": 99, "failures": 1}},
    {"case_id": "MGL5-INF-0620", "capability_id": "linear_integral", "arguments": {"panels": 4}},
    {"case_id": "MGL5-INF-0621", "capability_id": "square_integral", "arguments": {"panels": 4}},
    {"case_id": "MGL5-INF-0626", "capability_id": "pearson", "arguments": {"left": [1, 2, 3], "right": [2, 4, 6]}},
    {"case_id": "MGL5-INF-0627", "capability_id": "pearson", "arguments": {"left": [1, 2, 3], "right": [3, 2, 1]}},
    {"case_id": "MGL5-INF-0633", "capability_id": "acf_lag0", "arguments": {"values": [1, 2, 3, 4]}},
]


def run_all() -> list[dict]:
    rows = []
    for spec in CASES:
        runs = [execute(spec["capability_id"], spec["arguments"], spec["case_id"]) for _ in range(3)]
        observed = [run["observed"] for run in runs]
        ok = all(run["execution_status"] == "EXECUTED" for run in runs) and all(item == observed[0] for item in observed)
        rows.append({
            "case_id": spec["case_id"],
            "observed": observed[0],
            "execution_status": "CRITERION_MET" if ok else "FAIL",
            "stderr": runs[0]["stderr"],
            "repetitions": [run["run_id"] for run in runs],
            "backend": "LOCAL_TEST_ONLY",
            "c05_gate": "NOT_PASSED",
        })
    return rows
