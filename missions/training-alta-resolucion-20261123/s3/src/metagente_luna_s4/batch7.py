"""Source-bound stationarity diagnostic for MGL5-INF-0634."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

# Canonical JSON fixture SHA-256 for {"values":[1,2,3,4,5,6,7,8]}.
CASES = [
    {
        "case_id": "MGL5-INF-0634",
        "capability_id": "trend_stationarity",
        "arguments": {"values": [1, 2, 3, 4, 5, 6, 7, 8]},
        "fixture_provenance": "SYNTHETIC_MINIMAL: deterministic linear trend; canonical fixture SHA-256=e1008f4fb4eb6e2a120d9e06bf2a610192f0e1ca242d715b3daa41154e4f74a7; diagnostic is not a formal stationarity test",
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
