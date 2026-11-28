"""Independent ZIP local/central record oracle for INF-0069."""
from __future__ import annotations

def zip_central_compare_oracle(arguments: dict, observed: dict) -> dict:
    expected_local = [row["name"] for row in arguments["entries"]]
    expected_central = expected_local.copy()
    if arguments.get("tamper_central_name") and expected_central:
        expected_central[0] = "X" * len(expected_central[0])
        if expected_central[0] == expected_local[0]:
            expected_central[0] = "Y" + expected_central[0][1:]
    mismatches = [
        {"index": index, "local_name": local, "central_name": central, "field": "filename"}
        for index, (local, central) in enumerate(zip(expected_local, expected_central))
        if local != central
    ]
    expected_detected = bool(mismatches)
    ok = (
        observed.get("rejected") is False
        and observed.get("local_names") == expected_local
        and observed.get("central_names") == expected_central
        and observed.get("mismatch_detected") is expected_detected
        and observed.get("extraction_performed") is False
        and observed.get("outside_destination_write") is False
        and (not expected_detected or observed.get("discrepancies") == mismatches)
    )
    return {"ok": ok, "expected_mismatch": expected_detected, "method": "independent source member order/name comparison and no-extraction side-effect assertion"}
