"""Executors for a third set of cases with a stated result."""
from __future__ import annotations

import ipaddress
import subprocess
import sys


def duplicates(values: list[int]) -> dict:
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    found = [value for value in values if counts[value] > 1]
    ordered = []
    for value in found:
        if value not in ordered:
            ordered.append(value)
    print(ordered)
    return {"duplicates": ordered}


def brackets(texts: list[str]) -> dict:
    pairs = {")": "(", "]": "[", "}": "{"}
    results = []
    for text in texts:
        stack = []
        ok = True
        for char in text:
            if char in "([{":
                stack.append(char)
            elif char in ")]}":
                ok = bool(stack) and stack.pop() == pairs[char]
                if not ok:
                    break
        results.append({"text": text, "accepted": ok and not stack})
    print(results)
    return {"results": results}


class _Node:
    def __init__(self, value: int) -> None:
        self.value = value
        self.left = None
        self.right = None


def binary_insert(values: list[int]) -> dict:
    root = None
    for value in values:
        root = _place(root, value)
    ordered = []
    _walk(root, ordered)
    print(ordered)
    return {"inorder": ordered}


def _place(node: _Node | None, value: int) -> _Node:
    if node is None:
        return _Node(value)
    if value < node.value:
        node.left = _place(node.left, value)
    else:
        node.right = _place(node.right, value)
    return node


def _walk(node: _Node | None, ordered: list[int]) -> None:
    if node is None:
        return
    _walk(node.left, ordered)
    ordered.append(node.value)
    _walk(node.right, ordered)


def _parse(expression: str) -> int:
    tokens = expression.replace("(", " ( ").replace(")", " ) ").replace("+", " + ").replace("*", " * ").split()
    position = 0

    def parse_sum() -> int:
        value = parse_product()
        while position < len(tokens) and tokens[position] == "+":
            advance()
            value += parse_product()
        return value

    def parse_product() -> int:
        value = parse_atom()
        while position < len(tokens) and tokens[position] == "*":
            advance()
            value *= parse_atom()
        return value

    def parse_atom() -> int:
        nonlocal position
        token = tokens[position]
        position += 1
        if token == "(":
            value = parse_sum()
            position += 1
            return value
        return int(token)

    def advance() -> None:
        nonlocal position
        position += 1

    return parse_sum()


def arithmetic(expression: str) -> dict:
    value = _parse(expression)
    print(value)
    return {"value": value, "expression": expression}


def child_status(exit_code: int) -> dict:
    if not isinstance(exit_code, int) or isinstance(exit_code, bool) or not 0 <= exit_code <= 255:
        return {"rejected": True, "reason": "exit code must be an integer from 0 through 255"}
    process = subprocess.Popen([sys.executable, "-c", f"import sys; sys.exit({exit_code})"])
    code = process.wait(timeout=5)
    print(process.pid, code)
    return {"pid": process.pid, "exit_code": code}


def ipv6_reject(address: str) -> dict:
    try:
        ipaddress.IPv6Address(address)
        accepted = True
    except ipaddress.AddressValueError:
        accepted = False
    print(accepted)
    return {"accepted": accepted}


def ipv6_prefix(cidr: str) -> dict:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        return {"rejected": True, "reason": str(exc)}
    print(network)
    return {"rejected": False, "prefix": f"{network.network_address}/{network.prefixlen}"}


def threshold(low: float, high: float, limit: float) -> dict:
    print(low, high)
    return {"at_or_below": low <= limit, "above": high > limit}


def l2_norm(components: list[int]) -> dict:
    if any(not isinstance(component, int) or isinstance(component, bool) for component in components):
        return {"rejected": True, "reason": "components must be integers"}
    total = 0
    for component in components:
        total += component * component
    root = int(total**0.5)
    print(root)
    return {"norm": root, "square": total}


def ratio(numerator: int, denominator: int) -> dict:
    if numerator < 0 or denominator <= 0:
        return {"rejected": True, "reason": "ratio requires non-negative numerator and positive denominator"}
    print(numerator, denominator)
    return {"rejected": False, "value": numerator / denominator, "denominator": denominator}


def precision_recall(true_positive: int, false_positive: int, false_negative: int) -> dict:
    if min(true_positive, false_positive, false_negative) < 0 or true_positive + false_positive == 0 or true_positive + false_negative == 0:
        return {"rejected": True, "reason": "precision and recall require non-negative counts and positive denominators"}
    precision = true_positive / (true_positive + false_positive)
    recall = true_positive / (true_positive + false_negative)
    print(precision, recall)
    return {"rejected": False, "precision": precision, "recall": recall}


def f1_score(precision: float, recall: float) -> dict:
    if precision < 0 or recall < 0 or precision + recall == 0:
        return {"rejected": True, "reason": "F1 requires non-negative rates with positive sum"}
    score = 2 * precision * recall / (precision + recall)
    print(score)
    return {"rejected": False, "f1": score}
