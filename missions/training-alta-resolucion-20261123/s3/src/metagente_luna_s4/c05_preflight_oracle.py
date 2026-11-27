"""Independent verification of source-bound preflight BLOCKED records."""
from __future__ import annotations


def blocked_preflight_oracle(arguments: dict, observed: dict) -> dict:
    expected = {
        "case_id": arguments["case_id"],
        "blocker_code": arguments["blocker_code"],
        "phase": arguments["phase"],
        "operation_invoked": False,
        "blocked": True,
    }
    valid = all(observed.get(key) == value for key, value in expected.items())
    valid = valid and isinstance(observed.get("details"), str) and bool(observed["details"])
    # A BLOCKED preflight is not an oracle PASS or FAIL for the underlying operation.
    return {
        "ok": None,
        "method": "independent preflight-state verification",
        "valid_blocked_record": valid,
        "underlying_operation_result": "NOT_OBSERVED",
    }
