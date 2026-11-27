"""Operations whose literals are in the training program."""
from __future__ import annotations

import ipaddress
import json
import math
import os
import sqlite3
import subprocess
import sys
import tempfile
import threading
import traceback
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def first_match(needle: int, values: list[int]) -> dict:
    duplicates = [index for index, value in enumerate(values) if value == needle]
    first = duplicates[0] if duplicates else None
    print(first, duplicates)
    return {"index": first, "duplicates": duplicates, "policy": "first-of-all-matches"}


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


def dequeue_named(values: list[str]) -> dict:
    queue = list(values)
    order = [queue.pop(0) for _ in range(len(queue))]
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


def _balanced(node: dict | None) -> tuple[int, int, bool]:
    if node is None:
        return 0, 0, True
    left_height, left_count, left_ok = _balanced(node["left"])
    right_height, right_count, right_ok = _balanced(node["right"])
    height = 1 + max(left_height, right_height)
    ok = left_ok and right_ok and abs(left_height - right_height) <= 1 and height == node["height"]
    return height, 1 + left_count + right_count, ok


def balanced_range() -> dict:
    root = None
    for key in range(1, 1001):
        root = _insert(root, key)
    height, nodes, balanced = _balanced(root)
    found = sum(_present(root, key) for key in range(1, 1001))
    print(height, nodes, balanced, found)
    return {"height": height, "nodes": nodes, "balanced": balanced, "found": found, "count": 1000}


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
    ratios = [counts[1] / counts[0], counts[2] / counts[1]]
    return {"comparisons": counts, "ratios": ratios, "count_noise": 0}


def factorials(values: list[int]) -> dict:
    def checked(number: int) -> int:
        if not isinstance(number, int) or isinstance(number, bool) or number < 0:
            raise ValueError("factorial domain is non-negative integers")
        result = 1
        for factor in range(1, number + 1):
            result *= factor
        return result

    try:
        results = [checked(number) for number in values]
    except ValueError as exc:
        return {"rejected": True, "reason": str(exc), "values": [], "negative_rejected": True}
    negative_rejected = False
    try:
        checked(-1)
    except ValueError:
        negative_rejected = True
    print(results[-1] if results else 1, negative_rejected)
    return {"rejected": False, "values": results, "negative_rejected": negative_rejected}


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
    data = list(range(length))
    reads = 0
    index = length
    if 0 <= index < len(data):
        reads += 1
        _value = data[index]
        del _value
        return {"out_of_range": False, "read": True, "reads": reads, "length": len(data)}
    print("blocked", reads)
    return {"out_of_range": True, "read": False, "reads": reads, "length": len(data)}


def divide_zero() -> dict:
    try:
        value = 1 / 0
    except ZeroDivisionError:
        frame = traceback.extract_tb(sys.exc_info()[2])[-1]
        print(frame.name, frame.lineno)
        return {"raised": True, "type": "ZeroDivisionError", "value": None, "function": frame.name, "line": frame.lineno}
    return {"raised": False, "type": None, "value": value, "function": None, "line": None}


def mode_0640() -> dict:
    directory = Path(tempfile.mkdtemp(prefix="luna-mode-"))
    path = directory / "sample"
    descriptor = os.open(path, os.O_CREAT | os.O_WRONLY, 0o666)
    os.close(descriptor)
    os.chmod(path, 0o640)
    mode = os.stat(path).st_mode & 0o777
    print(oct(mode))
    return {
        "mode": mode,
        "owner_read": os.access(path, os.R_OK),
        "owner_execute": os.access(path, os.X_OK),
        "group_write": bool(mode & 0o020),
        "other_bits": mode & 0o007,
    }


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
    try:
        ipaddress.IPv6Address(address)
    except ipaddress.AddressValueError as exc:
        return {"rejected": True, "reason": str(exc)}
    halves = address.split("::")
    left = halves[0].split(":") if halves[0] else []
    right = halves[1].split(":") if len(halves) > 1 and halves[1] else []
    missing = 8 - (len(left) + len(right))
    groups = left + ["0"] * missing + right
    expanded = ":".join(f"{int(group, 16):04x}" for group in groups)
    integer = 0
    for group in groups:
        integer = (integer << 16) | int(group, 16)
    print(expanded)
    return {"rejected": False, "expanded": expanded, "integer": integer}


def mask_bits(mask: str) -> dict:
    parts = mask.split(".")
    if len(parts) != 4 or any(not part.isdecimal() or not 0 <= int(part) <= 255 for part in parts):
        return {"rejected": True, "reason": "invalid IPv4 octet"}
    bits = "".join(f"{int(part):08b}" for part in parts)
    contiguous = "01" not in bits
    print(bits)
    return {"rejected": not contiguous, "bits": bits, "contiguous": contiguous}


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
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode()
            connection = sqlite3.connect(":memory:")
            connection.execute("create table user(name text)")
            connection.execute("insert into user(name) values ('ada')")
            matched = connection.execute("select name from user where name = ?", (body,)).fetchall()
            payload = json.dumps({"matched": len(matched)}).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, fmt: str, *args) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    request = urllib.request.Request(f"http://{host}:{port}/users", data=b"' OR 1=1 --", method="POST")
    with urllib.request.urlopen(request, timeout=5) as response:
        body = json.loads(response.read().decode())
        status = response.status
    server.shutdown()
    print(body["matched"], status)
    return {"matched": body["matched"], "status": status}


def exit_codes() -> dict:
    results = []
    for command in (["true"], ["false"], ["luna-command-absent"]):
        try:
            completed = subprocess.run(command, check=False, capture_output=True, timeout=5)
            results.append({"command": command[0], "code": completed.returncode})
        except FileNotFoundError:
            results.append({"command": command[0], "code": 127})
    print(results)
    return {"codes": [item["code"] for item in results], "commands": [item["command"] for item in results]}


def sqrt_two(value: float) -> dict:
    if value < 0:
        return {"rejected": True, "reason": "square root domain is non-negative"}
    if value == 0:
        return {"rejected": False, "estimate": 0.0, "residual": 0.0}
    guess = value if value >= 1 else 1.0
    for _ in range(12):
        guess = (guess + value / guess) / 2
    print(guess)
    return {"rejected": False, "estimate": guess, "residual": guess * guess - value}


def compensated_sum(start: float, increment: float, count: int) -> dict:
    if count < 0:
        return {"rejected": True, "reason": "count must be non-negative"}
    values = [start, *([increment] * count)]
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
    return {"rejected": False, "naive": naive, "kahan": total}


def newton_root(initial: float, target: float) -> dict:
    if initial <= 0 or target < 0:
        return {"rejected": True, "reason": "Newton square-root fixture requires positive initial value and non-negative target"}
    if target == 0:
        return {"rejected": False, "root": 0.0, "residual": 0.0}
    value = initial
    for _ in range(12):
        value = value - (value * value - target) / (2 * value)
    print(value)
    return {"rejected": False, "root": value, "residual": value * value - target}


def bracket_cube(low: float, high: float) -> dict:
    if low >= high or low**3 >= 2 or high**3 <= 2:
        return {"rejected": True, "reason": "interval must strictly bracket the real cube root of two"}
    left, right = low, high
    for _ in range(40):
        mid = (left + right) / 2
        if mid**3 - 2 < 0:
            left = mid
        else:
            right = mid
    print(left, right)
    return {"rejected": False, "low": left, "high": right, "interval_provenance": "PREREGISTERED_SIGN_CHANGE"}


def two_variances(values: list[int]) -> dict:
    if not values:
        return {"rejected": True, "reason": "variance requires at least one observation"}
    count = len(values)
    mean = sum(values) / count
    square = sum((item - mean) ** 2 for item in values)
    print(square)
    sample = square / (count - 1) if count > 1 else None
    return {"rejected": False, "population": square / count, "sample": sample}


def exact_line(xs: list[int], slope: float, intercept: float) -> dict:
    ys = [slope * item + intercept for item in xs]
    count = len(xs)
    mean_x = sum(xs) / count
    mean_y = sum(ys) / count
    fitted = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys, strict=True))
    fitted /= sum((x - mean_x) ** 2 for x in xs)
    fitted_intercept = mean_y - fitted * mean_x
    print(fitted, fitted_intercept)
    return {"xs": xs, "ys": ys, "slope": fitted, "intercept": fitted_intercept}


def _euler(step: float) -> float:
    value = 1.0
    for _ in range(round(1 / step)):
        value += step * value
    return value


def euler_decay(coarse_step: float, fine_step: float) -> dict:
    coarse = abs(_euler(coarse_step) - math.e)
    fine = abs(_euler(fine_step) - math.e)
    print(coarse, fine)
    return {"coarse_error": coarse, "fine_error": fine, "coarse_step": coarse_step, "fine_step": fine_step}


def rk4_decay(step: float) -> dict:
    value = 1.0
    for _ in range(round(1 / step)):
        first = value
        second = value + 0.5 * step * first
        third = value + 0.5 * step * second
        fourth = value + step * third
        value += step * (first + 2 * second + 2 * third + fourth) / 6
    euler = _euler(step)
    print(value, euler)
    return {"rk4": value, "euler": euler, "step": step}


def stable_ages(records: list[dict]) -> dict:
    ordered = sorted(records, key=lambda item: (item["age"],))
    print([item["id"] for item in ordered])
    return {"ids": [item["id"] for item in ordered]}


def _heapsort(values: list[int]) -> list[int]:
    heap = values[:]
    count = len(heap)

    def sift(start: int, end: int) -> None:
        root = start
        while root * 2 + 1 < end:
            child = root * 2 + 1
            if child + 1 < end and heap[child] < heap[child + 1]:
                child += 1
            if heap[root] < heap[child]:
                heap[root], heap[child] = heap[child], heap[root]
                root = child
            else:
                return

    for index in range(count // 2 - 1, -1, -1):
        sift(index, count)
    for end in range(count - 1, 0, -1):
        heap[0], heap[end] = heap[end], heap[0]
        sift(0, end)
    return heap


def descending_values(values: list[int]) -> dict:
    ordered = list(reversed(_heapsort(list(values))))
    print(ordered)
    return {"ordered": ordered, "length": len(ordered)}


def descending_seed(seed: int, count: int) -> dict:
    import random

    if (
        not isinstance(seed, int) or isinstance(seed, bool)
        or not isinstance(count, int) or isinstance(count, bool)
        or count < 1 or count > 10_000
    ):
        return {"rejected": True, "reason": "seed must be an integer and count must be in 1..10000"}
    generator = random.Random(seed)
    values = [generator.randrange(-1_000_000, 1_000_000) for _ in range(count)]
    ordered = list(reversed(_heapsort(values[:])))
    print(len(ordered), ordered[0], ordered[-1])
    return {
        "ordered": ordered, "length": len(ordered), "first": ordered[0],
        "last": ordered[-1], "checksum": sum(ordered), "rejected": False,
    }


def stack_script(steps: list[str]) -> dict:
    stack: list[int] = []
    outputs: list[str | int] = []
    for step in steps:
        if step.startswith("push:"):
            stack.append(int(step.split(":", 1)[1]))
            outputs.append("pushed")
        elif step == "peek":
            outputs.append(stack[-1] if stack else "underflow")
        elif step == "pop":
            outputs.append(stack.pop() if stack else "underflow")
    print(outputs)
    return {"outputs": outputs}


def moving_average(values: list[int], window: int) -> dict:
    means = [sum(values[index : index + window]) / window for index in range(len(values) - window + 1)]
    print(means)
    return {"means": means, "alignment": "window-end", "window": window}


_NONE = {"type": "object", "additionalProperties": False}
_VALUES = {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}
SPECS = [
    ("first_match", "scan_index", {"type": "object", "required": ["needle", "values"], "properties": {"needle": {"type": "integer"}, "values": {"type": "array"}}, "additionalProperties": False}),
    ("binary_find", "direct_index", {"type": "object", "required": ["needle", "start", "end"], "properties": {"needle": {"type": "integer"}, "start": {"type": "integer"}, "end": {"type": "integer"}}, "additionalProperties": False}),
    ("dequeue_named", "named_order", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    ("balanced_range", "range_sum", _NONE),
    ("linear_scans", "full_scans", _NONE),
    ("factorials", "reference_factorials", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
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
    ("sqrt_two", "library_sqrt", {"type": "object", "required": ["value"], "properties": {"value": {"type": "number"}}, "additionalProperties": False}),
    ("compensated_sum", "decimal_total", {"type": "object", "required": ["start", "increment", "count"], "properties": {"start": {"type": "number"}, "increment": {"type": "number"}, "count": {"type": "integer"}}, "additionalProperties": False}),
    ("newton_root", "library_root", {"type": "object", "required": ["initial", "target"], "properties": {"initial": {"type": "number"}, "target": {"type": "number"}}, "additionalProperties": False}),
    ("bracket_cube", "sign_change", {"type": "object", "required": ["low", "high"], "properties": {"low": {"type": "number"}, "high": {"type": "number"}}, "additionalProperties": False}),
    ("two_variances", "statistics_variance", _VALUES),
    ("exact_line", "two_points", {"type": "object", "required": ["xs", "slope", "intercept"], "properties": {"xs": {"type": "array"}, "slope": {"type": "number"}, "intercept": {"type": "number"}}, "additionalProperties": False}),
    ("euler_decay", "smaller_step", {"type": "object", "required": ["coarse_step", "fine_step"], "properties": {"coarse_step": {"type": "number"}, "fine_step": {"type": "number"}}, "additionalProperties": False}),
    ("rk4_decay", "series_exp", {"type": "object", "required": ["step"], "properties": {"step": {"type": "number"}}, "additionalProperties": False}),
    ("descending_values", "full_permutation", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    ("descending_seed", "seed_permutation", {"type": "object", "required": ["seed", "count"], "properties": {"seed": {"type": "integer"}, "count": {"type": "integer"}}, "additionalProperties": False}),
    ("stack_script", "script_replay", {"type": "object", "required": ["steps"], "properties": {"steps": {"type": "array"}}, "additionalProperties": False}),
    ("moving_average", "window_means", {"type": "object", "required": ["values", "window"], "properties": {"values": {"type": "array"}, "window": {"type": "integer"}}, "additionalProperties": False}),
]

