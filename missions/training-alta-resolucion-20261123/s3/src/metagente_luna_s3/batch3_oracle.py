"""Checks for the third batch. They do not call the executors."""
from __future__ import annotations

import ipaddress


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
    return {"ok": arguments["address"].count("::") > 1 and observed["accepted"] is False, "method": "compression count, not ipaddress"}


def stated_prefix(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["prefix"] == "2001:db8:abcd:12::/64", "method": "prefix written in the case"}


def fever_rule(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["below_or_equal"] is False and observed["above"] is True and arguments["limit"] == 38, "method": "strict greater-than"}


def thirteen(arguments: dict, observed: dict) -> dict:
    square = sum(component * component for component in arguments["components"])
    return {"ok": square == 169 and observed["norm"] == 13 and observed["square"] == 169, "method": "integer square"}


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
