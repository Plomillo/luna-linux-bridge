"""Checks for the third batch. They do not call the executors."""
from __future__ import annotations

import ipaddress
import math


def repeated(arguments: dict, observed: dict) -> dict:
    counts: dict[int, int] = {}
    for value in arguments["values"]:
        counts[value] = counts.get(value, 0) + 1
    expected = []
    for value in arguments["values"]:
        if counts[value] > 1 and value not in expected:
            expected.append(value)
    return {"ok": observed["duplicates"] == expected == [1, 2], "method": "second count"}


def bracket_pairs(arguments: dict, observed: dict) -> dict:
    expected = [{"text": "({[]})", "accepted": True}, {"text": "([)]", "accepted": False}]
    return {"ok": arguments["texts"] == ["({[]})", "([)]"] and observed["results"] == expected, "method": "fixed pair of strings"}


def sorted_values(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["inorder"] == sorted(arguments["values"]) == [1, 3, 6, 8, 10, 14], "method": "sort, not the tree"}


def stated_value(arguments: dict, observed: dict) -> dict:
    answers = {"2+3*4": 14, "(1+2)*3": 9, "2*3+4": 10}
    return {"ok": observed["value"] == answers[arguments["expression"]], "method": "stated value, not the parser"}


def exit_seven(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["exit_code"] == 7 and isinstance(observed["pid"], int) and observed["pid"] > 0, "method": "status seven"}


def two_compressions(arguments: dict, observed: dict) -> dict:
    try:
        ipaddress.IPv6Address(arguments["address"])
    except ipaddress.AddressValueError:
        expected = False
    else:
        expected = True
    return {"ok": observed.get("accepted") is expected, "method": "independent IPv6 address parser"}


def stated_prefix(arguments: dict, observed: dict) -> dict:
    try:
        network = ipaddress.ip_network(arguments["cidr"], strict=False)
    except ValueError:
        return {"ok": observed.get("rejected") is True, "method": "independent IPv6 prefix validation"}
    expected = f"{network.network_address}/{network.prefixlen}"
    return {"ok": observed.get("rejected") is False and observed.get("prefix") == expected, "method": "independent IPv6 network calculation"}


def fever_rule(arguments: dict, observed: dict) -> dict:
    at_or_below = arguments["low"] <= arguments["limit"]
    above = arguments["high"] > arguments["limit"]
    return {"ok": observed.get("at_or_below") is at_or_below and observed.get("above") is above, "method": "independent strict greater-than comparison"}


def thirteen(arguments: dict, observed: dict) -> dict:
    components = arguments["components"]
    if any(not isinstance(component, int) or isinstance(component, bool) for component in components):
        ok = observed.get("rejected") is True and observed.get("reason") == "components must be integers"
        return {"ok": ok, "method": "independent component type validation"}
    square = sum(component * component for component in components)
    expected_norm = math.isqrt(square)
    ok = observed.get("square") == square and observed.get("norm") == expected_norm
    return {"ok": ok, "method": "independent integer square root"}


def stated_ratio(arguments: dict, observed: dict) -> dict:
    value = arguments["numerator"] / arguments["denominator"]
    return {"ok": observed["value"] == value and observed["denominator"] == arguments["denominator"], "method": "division of the stated counts"}


def rates(arguments: dict, observed: dict) -> dict:
    precision = 40 / 50
    recall = 40 / 60
    return {"ok": arguments["true_positive"] == 40 and observed["precision"] == precision and observed["recall"] == recall, "method": "40/50 and 40/60"}


def harmonic(arguments: dict, observed: dict) -> dict:
    precision, recall = arguments["precision"], arguments["recall"]
    expected = 2 * precision * recall / (precision + recall)
    return {"ok": observed["f1"] == expected, "method": "harmonic mean"}


def library_available() -> bool:
    return ipaddress.IPv6Address("::1").compressed == "::1"
