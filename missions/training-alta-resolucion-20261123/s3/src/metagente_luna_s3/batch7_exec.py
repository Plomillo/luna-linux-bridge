"""Deterministic trend diagnostic for source case MGL5-INF-0634."""
from __future__ import annotations

import math


def trend_stationarity(values: list[float]) -> dict:
    if any(not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value) for value in values):
        return {"rejected": True, "reason": "non-finite-or-nonnumeric-value"}
    count = len(values)
    if count < 4:
        return {
            "rejected": False,
            "status": "INSUFFICIENT_POWER",
            "n": count,
            "slope": None,
            "r_squared": None,
            "method": "linear-regression-diagnostic",
            "limitation": "fewer than four observations; no stationarity inference",
        }
    mean_y = sum(values) / count
    total_sum_squares = sum((value - mean_y) ** 2 for value in values)
    if total_sum_squares == 0:
        return {
            "rejected": False,
            "status": "NO_VARIATION",
            "n": count,
            "slope": 0.0,
            "r_squared": None,
            "method": "linear-regression-diagnostic",
            "limitation": "constant series; trend regression is not informative",
        }
    mean_x = (count - 1) / 2
    numerator = sum((index - mean_x) * (value - mean_y) for index, value in enumerate(values))
    denominator = sum((index - mean_x) ** 2 for index in range(count))
    slope = numerator / denominator
    intercept = mean_y - slope * mean_x
    residual_sum_squares = sum((value - (intercept + slope * index)) ** 2 for index, value in enumerate(values))
    r_squared = 1 - residual_sum_squares / total_sum_squares
    status = "TREND_EVIDENCE" if abs(slope) >= 0.5 and r_squared >= 0.8 else "NO_TREND_EVIDENCE"
    return {
        "rejected": False,
        "status": status,
        "n": count,
        "slope": slope,
        "r_squared": r_squared,
        "method": "linear-regression-diagnostic",
        "limitation": "descriptive threshold diagnostic; not a formal stationarity hypothesis test",
    }
