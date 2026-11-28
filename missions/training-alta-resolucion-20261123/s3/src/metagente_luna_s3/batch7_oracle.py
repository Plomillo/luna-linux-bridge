"""Independent fixed-vector adjudication for MGL5-INF-0634."""
from __future__ import annotations


_REFERENCE = {
    (1, 2, 3, 4, 5, 6, 7, 8): ("TREND_EVIDENCE", 1.0, 1.0),
    (2, 4, 3, 4, 3, 2, 4, 3): ("NO_TREND_EVIDENCE", 1 / 28, 1 / 91),
    (1, 2): ("INSUFFICIENT_POWER", None, None),
    (5, 5, 5, 5): ("NO_VARIATION", 0.0, None),
}


def trend_stationarity_oracle(arguments: dict, observed: dict) -> dict:
    values = tuple(arguments.get("values", ()))
    expected = _REFERENCE.get(values)
    if expected is None:
        return {"ok": False, "method": "fixed reference vectors independent of executor"}
    status, slope, r_squared = expected
    ok = (
        observed.get("rejected") is False
        and observed.get("status") == status
        and observed.get("n") == len(values)
        and observed.get("slope") == slope
        and observed.get("r_squared") == r_squared
        and observed.get("method") == "linear-regression-diagnostic"
        and isinstance(observed.get("limitation"), str)
        and bool(observed.get("limitation"))
    )
    return {"ok": ok, "method": "frozen exact slope/R-squared reference vectors; no executor call"}
