"""Operations whose literals are in the training program."""
from __future__ import annotations

import math
import os
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path


def first_match(needle: int, values: list[int]) -> dict:
    for index, value in enumerate(values):
        if value == needle:
            print(index)
            return {"index": index, "policy": "first-zero-based"}
    return {"index": None, "policy": "first-zero-based"}


def binary_find(needle: int, start: int, end: int) -> dict:
    low, high = start, end
    comparisons = 0
    found = None
    while low <= high:
        mid = (low + high) // 2
        comparisons += 1
        if mid == needle:
            found = mid - start
            break
        if mid < needle:
            low = mid + 1
        else:
            high = mid - 1
    print(found, comparisons)
    return {"index": found, "comparisons": comparisons}


def dequeue_named() -> dict:
    queue = ["A", "B", "C"]
    order = [queue.pop(0) for _ in range(3)]
    print(order)
    return {"order": order, "remaining": len(queue)}


def _height(node: dict | None) -> int:
    return node["height"] if node else 0


def _refresh(node: dict) -> None:
    node["height"] = 1 + max(_height(node["left"]), _height(node["right"]))


def _rotate_left(node: dict) -> dict:
    child = node["right"]
    node["right"] = child["left"]
    child["left"] = node
    _refresh(node)
    _refresh(child)
    return child


def _rotate_right(node: dict) -> dict:
    child = node["left"]
    node["left"] = child["right"]
    child["right"] = node
    _refresh(node)
    _refresh(child)
    return child


def _insert(node: dict | None, key: int) -> dict:
    if node is None:
        return {"key": key, "left": None, "right": None, "height": 1}
    if key < node["key"]:
        node["left"] = _insert(node["left"], key)
    else:
        node["right"] = _insert(node["right"], key)
    _refresh(node)
    balance = _height(node["left"]) - _height(node["right"])
    if balance > 1 and key < node["left"]["key"]:
        return _rotate_right(node)
    if balance < -1 and key > node["right"]["key"]:
        return _rotate_left(node)
    if balance > 1 and key > node["left"]["key"]:
        node["left"] = _rotate_left(node["left"])
        return _rotate_right(node)
    if balance < -1 and key < node["right"]["key"]:
        node["right"] = _rotate_right(node["right"])
        return _rotate_left(node)
    return node


def _present(node: dict | None, key: int) -> bool:
    while node is not None:
        if key == node["key"]:
            return True
        node = node["left"] if key < node["key"] else node["right"]
    return False


def balanced_range() -> dict:
    root = None
    for key in range(1, 1001):
        root = _insert(root, key)
    found = sum(_present(root, key) for key in range(1, 1001))
    print(root["height"], found)
    return {"height": root["height"], "found": found, "count": 1000}


def linear_scans() -> dict:
    counts = []
    for size in (1000, 2000, 4000):
        comparisons = 0
        for value in range(size):
            comparisons += 1
            if value == -1:
                break
        counts.append(comparisons)
    print(counts)
    return {"comparisons": counts}


def factorials() -> dict:
    def checked(number: int) -> int:
        if number < 0:
            raise ValueError("negative")
        result = 1
        for factor in range(1, number + 1):
            result *= factor
        return result

    values = [checked(number) for number in range(13)]
    rejected = False
    try:
        checked(-1)
    except ValueError:
        rejected = True
    print(values[-1], rejected)
    return {"values": values, "negative_rejected": rejected}


def precedence_tree() -> dict:
    text = "1+2*3-4"
    values: list = []
    operators: list[str] = []
    precedence = {"+": 1, "-": 1, "*": 2}

    def apply() -> None:
        operator = operators.pop()
        right = values.pop()
        left = values.pop()
        values.append({"op": operator, "left": left, "right": right})

    number = ""
    for character in text:
        if character.isdigit():
            number += character
            continue
        values.append(int(number))
        number = ""
        while operators and precedence[operators[-1]] >= precedence[character]:
            apply()
        operators.append(character)
    values.append(int(number))
    while operators:
        apply()

    def evaluate(node):
        if isinstance(node, int):
            return node
        left = evaluate(node["left"])
        right = evaluate(node["right"])
        if node["op"] == "+":
            return left + right
        if node["op"] == "-":
            return left - right
        return left * right

    tree = values[0]
    value = evaluate(tree)
    print(value)
    return {"tree": tree, "value": value}


def index_limit(length: int) -> dict:
    index = length
    if index < 0 or index >= length:
        print("blocked")
        return {"out_of_range": True, "read": False}
    return {"out_of_range": False, "read": True}


def divide_zero() -> dict:
    try:
        value = 1 / 0
    except ZeroDivisionError as exc:
        print(type(exc).__name__)
        return {"raised": True, "type": type(exc).__name__, "value": None}
    return {"raised": False, "type": None, "value": value}


def mode_0640() -> dict:
    directory = Path(tempfile.mkdtemp(prefix="luna-mode-"))
    path = directory / "sample"
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY, 0o666)
    os.close(descriptor)
    os.chmod(path, 0o640)
    mode = os.stat(path).st_mode & 0o777
    print(oct(mode))
    return {"mode": mode}


def umask_0027() -> dict:
    directory = Path(tempfile.mkdtemp(prefix="luna-umask-"))
    path = directory / "sample"
    previous = os.umask(0o027)
    try:
        descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o666)
        os.close(descriptor)
        mode = os.stat(path).st_mode & 0o777
    finally:
        os.umask(previous)
    print(oct(mode))
    return {"mode": mode}


def child_env() -> dict:
    completed = subprocess.run(
        [sys.executable, "-c", "import os; print(os.environ['test'])"],
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
        env={"PATH": os.environ.get("PATH", ""), "test": "123"},
    )
    print(completed.stdout)
    return {"value": completed.stdout.strip(), "code": completed.returncode}


def expand_v6(address: str) -> dict:
    halves = address.split("::")
    left = halves[0].split(":") if halves[0] else []
    right = halves[1].split(":") if len(halves) > 1 and halves[1] else []
    missing = 8 - (len(left) + len(right))
    groups = left + ["0"] * missing + right
    expanded = ":".join(f"{int(group, 16):04x}" for group in groups)
    print(expanded)
    return {"expanded": expanded}


def mask_bits(mask: str) -> dict:
    bits = "".join(f"{int(part):08b}" for part in mask.split("."))
    print(bits)
    return {"bits": bits, "contiguous": "01" not in bits}


def reject_age() -> dict:
    connection = sqlite3.connect(":memory:")
    connection.execute("create table person(age integer check (age >= 0))")
    rejected = False
    try:
        connection.execute("insert into person(age) values (-4)")
    except sqlite3.IntegrityError:
        rejected = True
    rows = connection.execute("select count(*) from person").fetchone()[0]
    print(rejected, rows)
    return {"rejected": rejected, "rows": rows}


def parameterized_name() -> dict:
    connection = sqlite3.connect(":memory:")
    connection.execute("create table user(name text)")
    connection.execute("insert into user(name) values ('ada')")
    payload = "' OR 1=1 --"
    matched = connection.execute("select name from user where name = ?", (payload,)).fetchall()
    print(len(matched))
    return {"matched": len(matched)}


def exit_codes() -> dict:
    codes = []
    for command in (["true"], ["false"], ["luna-command-absent"]):
        try:
            completed = subprocess.run(command, check=False, capture_output=True, timeout=5)
            codes.append(completed.returncode)
        except FileNotFoundError:
            codes.append(127)
    print(codes)
    return {"codes": codes}


def sqrt_two() -> dict:
    guess = 1.0
    for _ in range(8):
        guess = (guess + 2 / guess) / 2
    print(guess)
    return {"estimate": guess}


def compensated_sum() -> dict:
    values = [1.0, *([1e-8] * 100_000)]
    naive = 0.0
    for value in values:
        naive += value
    total = 0.0
    compensation = 0.0
    for value in values:
        adjusted = value - compensation
        updated = total + adjusted
        compensation = (updated - total) - adjusted
        total = updated
    print(naive, total)
    return {"naive": naive, "kahan": total}


def newton_root() -> dict:
    value = 1.0
    for _ in range(8):
        value = value - (value * value - 2) / (2 * value)
    print(value)
    return {"root": value, "residual": value * value - 2}


def bracket_cube() -> dict:
    low, high = 1.0, 2.0
    for _ in range(40):
        mid = (low + high) / 2
        if mid**3 - 2 < 0:
            low = mid
        else:
            high = mid
    print(low, high)
    return {"low": low, "high": high, "interval_provenance": "DERIVED_SIGN_CHANGE"}


def two_variances(values: list[int]) -> dict:
    count = len(values)
    mean = sum(values) / count
    square = sum((item - mean) ** 2 for item in values)
    print(square)
    return {"population": square / count, "sample": square / (count - 1)}


def exact_line() -> dict:
    xs = [0, 1, 2]
    ys = [2 * item + 3 for item in xs]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    slope /= sum((x - mean_x) ** 2 for x in xs)
    intercept = mean_y - slope * mean_x
    print(slope, intercept)
    return {"slope": slope, "intercept": intercept, "x_provenance": "DERIVED_FROM_EQUATION"}


def _euler(step: float) -> float:
    value = 1.0
    for _ in range(round(1 / step)):
        value += step * value
    return value


def euler_decay() -> dict:
    coarse = abs(_euler(0.1) - math.e)
    fine = abs(_euler(0.05) - math.e)
    print(coarse, fine)
    return {"coarse_error": coarse, "fine_error": fine, "step_provenance": "DECLARED_LAB_STEP"}


def rk4_decay() -> dict:
    step = 0.1
    value = 1.0
    for _ in range(10):
        first = value
        second = value + 0.5 * step * first
        third = value + 0.5 * step * second
        fourth = value + step * third
        value += step * (first + 2 * second + 2 * third + fourth) / 6
    euler = _euler(step)
    print(value, euler)
    return {"rk4": value, "euler": euler, "step": step, "step_provenance": "DECLARED_LAB_STEP"}


_NONE = {"type": "object", "additionalProperties": False}
_VALUES = {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}
SPECS = [
    ("first_match", "scan_index", {"type": "object", "required": ["needle", "values"], "properties": {"needle": {"type": "integer"}, "values": {"type": "array"}}, "additionalProperties": False}),
    ("binary_find", "direct_index", {"type": "object", "required": ["needle", "start", "end"], "properties": {"needle": {"type": "integer"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "additionalProperties": False}),
    ("dequeue_named", "named_order", _NONE),
    ("balanced_range", "range_sum", _NONE),
    ("linear_scans", "full_scans", _NONE),
    ("factorials", "reference_factorials", _NONE),
    ("precedence_tree", "folded_value", _NONE),
    ("index_limit", "refused_index", {"type": "object", "required": ["length"], "properties": {"length": {"type": "integer"}}, "additionalProperties": False}),
    ("divide_zero", "zero_type", _NONE),
    ("mode_0640", "octal_mode", _NONE),
    ("umask_0027", "masked_create", _NONE),
    ("child_env", "declared_env", _NONE),
    ("expand_v6", "library_v6", {"type": "object", "required": ["address"], "properties": {"address": {"type": "string"}}, "additionalProperties": False}),
    ("mask_bits", "one_run", {"type": "object", "required": ["mask"], "properties": {"mask": {"type": "string"}}, "additionalProperties": False}),
    ("reject_age", "own_check", _NONE),
    ("parameterized_name", "own_query", _NONE),
    ("exit_codes", "posix_codes", _NONE),
    ("sqrt_two", "library_sqrt", _NONE),
    ("compensated_sum", "decimal_total", _NONE),
    ("newton_root", "library_root", _NONE),
    ("bracket_cube", "sign_change", _NONE),
    ("two_variances", "statistics_variance", _VALUES),
    ("exact_line", "two_points", _NONE),
    ("euler_decay", "smaller_step", _NONE),
    ("rk4_decay", "series_exp", _NONE),
]

