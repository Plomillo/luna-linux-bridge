"""Checks for the fourth batch. They do not call the executors."""
from __future__ import annotations


def counted(arguments: dict, observed: dict) -> dict:
    return {"ok": arguments["times"] == 100 and observed["value"] == 100, "method": "stated count"}


def correlation(arguments: dict, observed: dict) -> dict:
    same_direction = arguments["right"][0] < arguments["right"][-1]
    expected = 1.0 if same_direction else -1.0
    return {"ok": abs(observed["value"] - expected) < 1e-9, "method": "direction of the declared vectors"}


def lag_identity(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["lag0"] == 1, "method": "lag zero is the series against itself"}


def half(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["value"] == 0.5, "method": "integral of x on the unit interval"}


def one_third(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": abs(observed["value"] - (1 / 3)) < 1e-4, "method": "closed form, not the panel sum"}


def axis_cosines(arguments: dict, observed: dict) -> dict:
    del arguments
    expected = [1.0, 0.0, -1.0]
    ok = all(abs(got - wanted) < 1e-9 for got, wanted in zip(observed["values"], expected, strict=True))
    return {"ok": ok, "method": "axis-aligned reference"}


def escapes(arguments: dict, observed: dict) -> dict:
    return {"ok": ".." in arguments["requested"] and observed["blocked"] is True, "method": "the request leaves the root"}
