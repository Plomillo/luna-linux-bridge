"""Checks for the fourth batch. They do not call the executors."""
from __future__ import annotations


def counted(arguments: dict, observed: dict) -> dict:
    times = arguments["times"]
    if times < 0:
        return {"ok": observed.get("rejected") is True, "method": "negative operation count rejected"}
    identifiers = observed["ids"]
    unique = len(identifiers) == len(set(identifiers)) == times
    return {"ok": observed.get("rejected") is False and unique and observed["completed"] == times and observed["failed"] == 0, "method": "independent operation identity count"}


def correlation(arguments: dict, observed: dict) -> dict:
    left, right = arguments["left"], arguments["right"]
    count = len(left)
    sum_x, sum_y = sum(left), sum(right)
    sum_xy = sum(item * other for item, other in zip(left, right, strict=True))
    sum_x2 = sum(item * item for item in left)
    sum_y2 = sum(item * item for item in right)
    numerator = count * sum_xy - sum_x * sum_y
    denominator_squared = (count * sum_x2 - sum_x**2) * (count * sum_y2 - sum_y**2)
    if denominator_squared == 0:
        ok = observed.get("error") == "zero-variance" and observed.get("value") is None
        return {"ok": ok, "method": "independent zero-variance condition"}
    expected = numerator / denominator_squared**0.5
    ok = observed["error"] is None and abs(observed["value"] - expected) < 1e-9
    return {"ok": ok, "method": "raw-score Pearson; residual shared definition"}


def lag_identity(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    if not isinstance(values, list) or any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in values):
        return {"ok": observed.get("rejected") is True and observed.get("error") == "invalid-values", "method": "independent input validation"}
    if len(values) < 2:
        return {"ok": observed.get("rejected") is True and observed.get("error") == "too-short", "method": "independent minimum sample validation"}
    count = len(values)
    mean = sum(values) / count
    denominator = sum((item - mean) ** 2 for item in values)
    if denominator == 0:
        return {"ok": observed.get("rejected") is True and observed.get("error") == "zero-variance", "method": "independent variance validation"}
    expected = []
    for lag in range(count):
        total = 0.0
        for index in range(lag, count):
            total += (values[index - lag] - mean) * (values[index] - mean)
        expected.append(total / denominator)
    got = observed.get("lags")
    ok = observed.get("accepted") is True and observed.get("error") is None and isinstance(got, list) and len(got) == len(expected)
    if ok:
        ok = all(abs(value - target) < 1e-9 for value, target in zip(got, expected, strict=True))
    return {"ok": ok, "method": "independent reverse-index products and global-mean calculation"}


def half(arguments: dict, observed: dict) -> dict:
    panels = arguments["panels"]
    if panels < 1:
        return {"ok": observed.get("rejected") is True, "method": "positive panel count required"}
    weights, points = observed["weights"], observed["points"]
    step = 1 / panels
    expected_weights = [1, *([2] * (panels - 1)), 1]
    recomputed = sum(weight * point for weight, point in zip(weights, points, strict=True)) * step / 2
    ok = observed.get("rejected") is False and observed["panels"] == panels and weights == expected_weights and observed["value"] == recomputed == 0.5
    return {"ok": ok, "method": "recomputed trapezoid, not the label"}


def one_third(arguments: dict, observed: dict) -> dict:
    panels = arguments["panels"]
    if panels < 2 or panels % 2:
        return {"ok": observed.get("rejected") is True, "method": "Simpson requires an even panel count"}
    weights, points = observed["weights"], observed["points"]
    step = 1 / panels
    expected_weights = [1 if index in {0, panels} else 4 if index % 2 else 2 for index in range(panels + 1)]
    recomputed = sum(weight * point for weight, point in zip(weights, points, strict=True)) * step / 3
    close = abs(observed["value"] - recomputed) < 1e-12 and abs(recomputed - (1 / 3)) < 1e-12
    return {"ok": observed.get("rejected") is False and observed["panels"] == panels and observed["method"] == "simpson" and weights == expected_weights and close, "method": "recomputed Simpson weights"}


def axis_cosines(arguments: dict, observed: dict) -> dict:
    expected = []
    for pair in arguments["pairs"]:
        if not isinstance(pair, list) or len(pair) != 2:
            return {"ok": observed.get("rejected") is True, "method": "independent vector-pair validation"}
        left, right = pair
        if (
            not isinstance(left, list) or not isinstance(right, list) or not left
            or len(left) != len(right)
            or any(not isinstance(item, (int, float)) or isinstance(item, bool) for item in left + right)
        ):
            return {"ok": observed.get("rejected") is True, "method": "independent vector-shape validation"}
        left_norm = sum(item * item for item in left) ** 0.5
        right_norm = sum(item * item for item in right) ** 0.5
        if left_norm == 0 or right_norm == 0:
            return {"ok": observed.get("rejected") is True, "method": "independent zero-vector rejection"}
        expected.append(sum(item * other for item, other in zip(left, right, strict=True)) / (left_norm * right_norm))
    got = observed.get("values")
    ok = observed.get("accepted") is True and isinstance(got, list) and len(got) == len(expected)
    if ok:
        ok = all(abs(value - target) < 1e-9 for value, target in zip(got, expected, strict=True))
    return {"ok": ok, "method": "independent dot-product and norm calculation"}


def request_counts(arguments: dict, observed: dict) -> dict:
    successes, failures = arguments["successes"], arguments["failures"]
    if successes < 0 or failures < 0 or successes + failures <= 0:
        return {"ok": observed.get("rejected") is True, "method": "invalid request counts rejected"}
    statuses = observed["statuses"]
    ok_count = sum(status == 200 for status in statuses)
    bad_count = sum(status == 500 for status in statuses)
    total = len(statuses)
    recomputed = ok_count / total
    ok = ok_count == successes and bad_count == failures and total == successes + failures and observed.get("rejected") is False and observed["availability"] == recomputed
    return {"ok": ok, "method": "recounted status codes"}


def escapes(arguments: dict, observed: dict) -> dict:
    requested = arguments["requested"]
    if requested in {"../../etc/passwd", "escape"}:
        ok = observed.get("blocked") is True and observed.get("bytes_read") == 0 and observed.get("opened_outside") is False
    elif requested == "inside-link":
        ok = observed.get("blocked") is False and observed.get("bytes_read") == 7 and observed.get("opened_outside") is False
    else:
        ok = False
    return {"ok": ok and observed.get("operation") == "simulated-download", "method": "no bytes were read outside the root"}
