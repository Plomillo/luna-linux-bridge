"""Checks for the fourth batch. They do not call the executors."""
from __future__ import annotations


def counted(arguments: dict, observed: dict) -> dict:
    identifiers = observed["ids"]
    unique = len(identifiers) == len(set(identifiers)) == arguments["times"] == 100
    return {"ok": unique and observed["completed"] == 100 and observed["failed"] == 0, "method": "one hundred distinct completions"}


def correlation(arguments: dict, observed: dict) -> dict:
    left, right = arguments["left"], arguments["right"]
    proportional = all(right[index] == 2 * left[index] for index in range(len(left)))
    reversed_pair = list(right) == list(reversed(left))
    if proportional:
        ok = abs(observed["value"] - 1) < 1e-9
    elif reversed_pair:
        ok = abs(observed["value"] + 1) < 1e-9
    else:
        ok = False
    return {"ok": ok, "method": "proportional or reversed vectors, not the Pearson sum"}


def lag_identity(arguments: dict, observed: dict) -> dict:
    expected = [1, 0.25, -0.3, -0.45]
    ok = arguments["values"] == [1, 2, 3, 4] and all(abs(got - wanted) < 1e-9 for got, wanted in zip(observed["lags"], expected, strict=True))
    return {"ok": ok, "method": "fixed lags for the declared series"}


def half(arguments: dict, observed: dict) -> dict:
    del arguments
    trapezoid = observed["method"] == "trapezoidal" and observed["weights"] == [1, 2, 2, 2, 1]
    return {"ok": trapezoid and observed["value"] == 0.5, "method": "trapezoid weights, not Simpson"}


def one_third(arguments: dict, observed: dict) -> dict:
    del arguments
    simpson = observed["method"] == "simpson" and observed["panels"] % 2 == 0 and observed["weights"] == [1, 4, 2, 4, 1]
    return {"ok": simpson and abs(observed["value"] - (1 / 3)) < 1e-9, "method": "closed form plus Simpson weights"}


def axis_cosines(arguments: dict, observed: dict) -> dict:
    del arguments
    expected = [1.0, 0.0, -1.0]
    ok = all(abs(got - wanted) < 1e-9 for got, wanted in zip(observed["values"], expected, strict=True))
    return {"ok": ok, "method": "axis-aligned reference"}


def request_counts(arguments: dict, observed: dict) -> dict:
    ok = arguments["successes"] == 99 and arguments["failures"] == 1
    ok = ok and observed["successes"] == 99 and observed["failures"] == 1 and observed["total"] == 100
    return {"ok": ok and observed["availability"] == 0.99, "method": "counted requests, not a bare ratio"}


def escapes(arguments: dict, observed: dict) -> dict:
    traversal = arguments["requested"] == "../../etc/passwd"
    untouched = observed["blocked"] is True and observed["bytes_read"] == 0
    return {"ok": traversal and untouched and observed["operation"] == "simulated-download", "method": "no bytes were read outside the root"}
