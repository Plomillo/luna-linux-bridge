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
    values = arguments["values"]
    valid = isinstance(values, list) and all(isinstance(value, int) and not isinstance(value, bool) for value in values)
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent binary-search-tree input validation"}
    return {
        "ok": observed.get("accepted") is True and observed.get("inorder") == sorted(values),
        "method": "independent sort, not the tree",
    }


def _ast_integer(node):
    import ast
    if isinstance(node, ast.Expression):
        return _ast_integer(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return _ast_integer(node.left) + _ast_integer(node.right)
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
        return _ast_integer(node.left) * _ast_integer(node.right)
    raise ValueError("unsupported arithmetic syntax")


def stated_value(arguments: dict, observed: dict) -> dict:
    try:
        import ast
        expected = _ast_integer(ast.parse(arguments["expression"], mode="eval"))
    except (SyntaxError, ValueError, TypeError):
        return {"ok": observed.get("rejected") is True, "method": "independent AST rejection"}
    return {
        "ok": observed.get("accepted") is True and observed.get("value") == expected,
        "method": "independent AST arithmetic evaluation",
    }


def exit_seven(arguments: dict, observed: dict) -> dict:
    expected = arguments["exit_code"]
    if not isinstance(expected, int) or isinstance(expected, bool) or not 0 <= expected <= 255:
        return {"ok": observed.get("rejected") is True, "method": "independent process status range"}
    return {
        "ok": observed.get("accepted") is True and observed.get("exit_code") == expected
        and isinstance(observed.get("pid"), int) and observed["pid"] > 0,
        "method": "independent child exit status",
    }


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
    numerator, denominator = arguments["numerator"], arguments["denominator"]
    if numerator < 0 or denominator <= 0:
        return {"ok": observed.get("rejected") is True, "method": "independent ratio domain validation"}
    value = numerator / denominator
    return {"ok": observed.get("rejected") is False and observed["value"] == value and observed["denominator"] == denominator, "method": "independent division of declared counts"}


def rates(arguments: dict, observed: dict) -> dict:
    tp, fp, fn = arguments["true_positive"], arguments["false_positive"], arguments["false_negative"]
    if min(tp, fp, fn) < 0 or tp + fp == 0 or tp + fn == 0:
        return {"ok": observed.get("rejected") is True, "method": "independent precision/recall domain validation"}
    precision, recall = tp / (tp + fp), tp / (tp + fn)
    return {"ok": observed.get("rejected") is False and abs(observed["precision"] - precision) < 1e-12 and abs(observed["recall"] - recall) < 1e-12, "method": "independent count ratios"}


def harmonic(arguments: dict, observed: dict) -> dict:
    precision, recall = arguments["precision"], arguments["recall"]
    if precision < 0 or recall < 0 or precision + recall == 0:
        return {"ok": observed.get("rejected") is True, "method": "independent harmonic-mean domain validation"}
    expected = 2 * precision * recall / (precision + recall)
    return {"ok": observed.get("rejected") is False and abs(observed["f1"] - expected) < 1e-12, "method": "harmonic mean"}


def library_available() -> bool:
    return ipaddress.IPv6Address("::1").compressed == "::1"
