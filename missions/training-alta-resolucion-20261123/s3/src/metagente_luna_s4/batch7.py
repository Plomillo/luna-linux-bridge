"""Source-bound scientific-computing case additions with independent ACF oracle."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

# FX-MGL5-INF-0634: deterministic synthetic series, seed 0634.
CASES = [
    {
        "case_id": "MGL5-INF-0634",
        "capability_id": "acf_lag0",
        "arguments": {"values": [1, 2, 3, 4]},
        "fixture_provenance": "SYNTHETIC_MINIMAL: seed=0634; linear-trend series [1,2,3,4]; independently recomputed lagged covariance reference",
    },
]


def run_all() -> list[dict]:
    rows = []
    for spec in CASES:
        run = execute(spec["capability_id"], spec["arguments"], spec["case_id"])
        rows.append({
            "case_id": spec["case_id"],
            "capability_id": spec["capability_id"],
            "arguments": spec["arguments"],
            "observed": run["observed"],
            "oracle_result": run["oracle_result"],
            "execution_status": run["execution_status"],
            "run_id": run["run_id"],
            "backend": run["backend"],
            "c05_gate": "NOT_PASSED",
        })
    return rows
