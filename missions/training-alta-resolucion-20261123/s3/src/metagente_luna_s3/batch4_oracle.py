"""Checks for the fourth batch. They do not call the executors."""
from __future__ import annotations


def counted(arguments: dict, observed: dict) -> dict:
    identifiers = observed["ids"]
    unique = len(identifiers) == len(set(identifiers)) == arguments["times"] == 100
    return {"ok": unique and observed["completed"] == 100 and observed["failed"] == 0, "method": "one hundred distinct completions"}


def correlation(arguments: dict, observed: dict) -> dict:
    left, right = arguments["left"], arguments["right"]
    count = len(left)
    sum_x, sum_y = sum(left), sum(right)
    sum_xy = sum(item * other for item, other in zip(left, right, strict=True))
    sum_x2 = sum(item * item for item in left)
    sum_y2 = sum(item * item for item in right)
    numerator = count * sum_xy - sum_x * sum_y
    denominator = ((count * sum_x2 - sum_x**2) * (count * sum_y2 - sum_y**2)) ** 0.5
    expected = numerator / denominator
    ok = observed["error"] is None and abs(observed["value"] - expected) < 1e-9
    return {"ok": ok, "method": "raw-score Pearson; residual shared definition"}


def lag_identity(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    count = len(values)
    mean = sum(values) / count
    denominator = sum((item - mean) ** 2 for item in values)
    expected = []
    for lag in range(count):
        total = 0.0
        for index in range(lag, count):
            total += (values[index - lag] - mean) * (values[index] - mean)
        expected.append(total / denominator)
    ok = observed["error"] is None and all(abs(got - wanted) < 1e-9 for got, wanted in zip(observed["lags"], expected, strict=True))
    return {"ok": ok, "method": "reverse-index products; shared global-mean definition"}


def half(arguments: dict, observed: dict) -> dict:
    del arguments
    weights, points = observed["weights"], observed["points"]
    step = 1 / observed["panels"]
    recomputed = sum(weight * point for weight, point in zip(weights, points, strict=True)) * step / 2
    trapezoid = observed["method"] == "trapezoidal" and weights == [1, 2, 2, 2, 1]
    return {"ok": trapezoid and observed["value"] == recomputed == 0.5, "method": "recomputed trapezoid, not the label"}


def one_third(arguments: dict, observed: dict) -> dict:
    del arguments
    weights, points = observed["weights"], observed["points"]
    step = 1 / observed["panels"]
    recomputed = sum(weight * point for weight, point in zip(weights, points, strict=True)) * step / 3
    simpson = observed["method"] == "simpson" and observed["panels"] % 2 == 0 and weights == [1, 4, 2, 4, 1]
    close = abs(observed["value"] - recomputed) < 1e-12 and abs(recomputed - (1 / 3)) < 1e-12
    return {"ok": simpson and close, "method": "recomputed Simpson weights"}


def axis_cosines(arguments: dict, observed: dict) -> dict:
    del arguments
    expected = [1.0, 0.0, -1.0]
    ok = all(abs(got - wanted) < 1e-9 for got, wanted in zip(observed["values"], expected, strict=True))
    return {"ok": ok, "method": "axis-aligned reference"}


def request_counts(arguments: dict, observed: dict) -> dict:
    del arguments
    statuses = observed["statuses"]
    ok_count = sum(status == 200 for status in statuses)
    bad_count = sum(status == 500 for status in statuses)
    total = len(statuses)
    recomputed = ok_count / total
    ok = ok_count == 99 and bad_count == 1 and total == 100 and observed["availability"] == recomputed
    return {"ok": ok, "method": "recounted status codes"}


def escapes(arguments: dict, observed: dict) -> dict:
    traversal = arguments["requested"] == "../../etc/passwd"
    untouched = observed["blocked"] is True and observed["bytes_read"] == 0 and observed["opened_outside"] is False
    return {"ok": traversal and untouched and observed["operation"] == "simulated-download", "method": "no bytes were read outside the root"}
