"""E10 rule engine. Facts in, structured predicates out. eval and exec are refused."""

from __future__ import annotations

import ast


class RuleError(Exception):
    pass


_ALLOWED_COMPARE = {
    ast.Eq: lambda a, b: a == b,
    ast.NotEq: lambda a, b: a != b,
    ast.Lt: lambda a, b: a < b,
    ast.LtE: lambda a, b: a <= b,
    ast.Gt: lambda a, b: a > b,
    ast.GtE: lambda a, b: a >= b,
}


def evaluate(expression: str, facts: dict) -> bool:
    if not isinstance(expression, str) or not isinstance(facts, dict):
        raise RuleError("BAD_INPUT")
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise RuleError("SYNTAX") from exc
    return bool(_eval(tree.body, facts))


def _eval(node: ast.AST, facts: dict):
    if isinstance(node, ast.BoolOp):
        values = [_eval(value, facts) for value in node.values]
        if isinstance(node.op, ast.And):
            return all(values)
        if isinstance(node.op, ast.Or):
            return any(values)
        raise RuleError("FORBIDDEN_OPERATOR")
    if isinstance(node, ast.Compare) and len(node.ops) == 1 and len(node.comparators) == 1:
        op = type(node.ops[0])
        if op not in _ALLOWED_COMPARE:
            raise RuleError("FORBIDDEN_OPERATOR")
        return _ALLOWED_COMPARE[op](_eval(node.left, facts), _eval(node.comparators[0], facts))
    if isinstance(node, ast.Name):
        if node.id not in facts:
            raise RuleError("UNKNOWN_FACT")
        return facts[node.id]
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, str, bool)) and not isinstance(node.value, float):
        return node.value
    raise RuleError("FORBIDDEN_EXPRESSION")
