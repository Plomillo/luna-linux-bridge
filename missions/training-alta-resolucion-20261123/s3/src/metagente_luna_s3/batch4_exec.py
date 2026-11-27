"""Executors for cases outside the earlier batches."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def run_operation(token: str) -> dict:
    prefix, separator, number = token.partition("-")
    if prefix != "op" or separator != "-" or not number.isdigit():
        return {"ok": False, "id": None}
    return {"ok": True, "id": int(number)}


def increment(times: int) -> dict:
    if times < 0:
        return {"rejected": True, "reason": "operation count must be non-negative"}
    records = [run_operation(f"op-{index}") for index in range(times)]
    completed = [item["id"] for item in records if item["ok"]]
    print(len(completed))
    return {"rejected": False, "completed": len(completed), "failed": len(records) - len(completed), "ids": completed}


def pearson(left: list[int], right: list[int]) -> dict:
    if len(left) != len(right) or len(left) < 2:
        return {"value": None, "error": "invalid-sample"}
    if len(set(left)) < 2 or len(set(right)) < 2:
        return {"value": None, "error": "zero-variance"}
    count = len(left)
    mean_left = sum(left) / count
    mean_right = sum(right) / count
    numerator = sum((item - mean_left) * (other - mean_right) for item, other in zip(left, right, strict=True))
    left_scale = sum((item - mean_left) ** 2 for item in left) ** 0.5
    right_scale = sum((item - mean_right) ** 2 for item in right) ** 0.5
    value = numerator / (left_scale * right_scale)
    print(value)
    return {"value": value, "error": None}


def acf_series(values: list[int]) -> dict:
    if len(values) < 2:
        return {"lags": None, "error": "too-short"}
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values)
    if variance == 0:
        return {"lags": None, "error": "zero-variance"}
    lags = []
    for lag in range(len(values)):
        numerator = sum((values[index] - mean) * (values[index + lag] - mean) for index in range(len(values) - lag))
        lags.append(numerator / variance)
    print(lags)
    return {"lags": lags, "error": None}


def linear_integral(panels: int) -> dict:
    if panels < 1:
        return {"rejected": True, "reason": "trapezoid requires at least one panel"}
    step = 1 / panels
    weights = [1, *([2] * (panels - 1)), 1]
    points = [index * step for index in range(panels + 1)]
    total = sum(weight * point for weight, point in zip(weights, points, strict=True))
    value = total * step / 2
    print(value)
    return {"rejected": False, "value": value, "method": "trapezoidal", "panels": panels, "weights": weights, "points": points}


def square_integral(panels: int) -> dict:
    if panels < 2 or panels % 2:
        return {"rejected": True, "reason": "Simpson integration requires a positive even panel count"}
    step = 1 / panels
    weights = [1 if index in {0, panels} else 4 if index % 2 else 2 for index in range(panels + 1)]
    points = [(index * step) ** 2 for index in range(panels + 1)]
    total = sum(weight * point for weight, point in zip(weights, points, strict=True))
    value = total * step / 3
    print(value)
    return {"rejected": False, "value": value, "method": "simpson", "panels": panels, "weights": weights, "points": points}


def cosine_set(pairs: list[list[list[int]]]) -> dict:
    values = []
    for pair in pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            return {"rejected": True, "reason": "each pair must contain two vectors"}
        left, right = pair
        if len(left) != len(right) or not left:
            return {"rejected": True, "reason": "vector dimensions must match and be non-empty"}
        left_square = sum(item * item for item in left)
        right_square = sum(item * item for item in right)
        if left_square == 0 or right_square == 0:
            return {"rejected": True, "reason": "zero vector has undefined cosine"}
        dot = sum(item * other for item, other in zip(left, right, strict=True))
        values.append(dot / ((left_square ** 0.5) * (right_square ** 0.5)))
    print(values)
    return {"rejected": False, "values": values}


def handle_request(index: int, fail_index: int) -> dict:
    status = 500 if index == fail_index else 200
    return {"id": index, "status": status}


def request_log(successes: int, failures: int) -> dict:
    if successes < 0 or failures < 0 or successes + failures <= 0:
        return {"rejected": True, "reason": "request counts must be non-negative with positive total"}
    total = successes + failures
    fail_index = successes if failures else -1
    responses = [handle_request(index, fail_index) for index in range(total)]
    ok_count = sum(item["status"] == 200 for item in responses)
    bad_count = sum(item["status"] == 500 for item in responses)
    print(ok_count, bad_count)
    return {
        "rejected": False,
        "availability": ok_count / total,
        "successes": ok_count,
        "failures": bad_count,
        "total": total,
        "statuses": [item["status"] for item in responses],
    }


def _refused(reason: str) -> dict:
    return {"blocked": True, "bytes_read": 0, "opened_outside": False, "operation": "simulated-download", "reason": reason}


def confined(requested: str) -> dict:
    root = Path(tempfile.mkdtemp(prefix="luna-root-"))
    (root / "allowed.txt").write_text("payload")
    (root / "inside-link").symlink_to("allowed.txt")
    outside = Path(tempfile.mkdtemp(prefix="luna-out-"))
    (outside / "secret.txt").write_text("secret")
    (root / "escape").symlink_to(outside / "secret.txt")
    (root / "nest").mkdir()
    (root / "nest" / "out").symlink_to(outside / "secret.txt")
    if requested.startswith("/") or "\x00" in requested:
        return _refused("absolute-or-nul")
    parts = [part for part in requested.split("/") if part not in {"", "."}]
    if any(part == ".." for part in parts):
        return _refused("parent-segment")
    root_fd = os.open(root, os.O_RDONLY | os.O_DIRECTORY)
    opened: list[int] = []
    try:
        current = root_fd
        for index, part in enumerate(parts):
            last = index == len(parts) - 1
            flags = os.O_RDONLY | os.O_NOFOLLOW | (0 if last else os.O_DIRECTORY)
            try:
                handle = os.open(part, flags, dir_fd=current)
            except OSError:
                return _open_relative_link(current, part) if last else _refused("symlink-or-missing")
            if last:
                data = os.read(handle, 64)
                os.close(handle)
                return {"blocked": False, "bytes_read": len(data), "opened_outside": False, "operation": "simulated-download", "reason": "allowed"}
            opened.append(handle)
            current = handle
        return _refused("empty")
    finally:
        for handle in opened:
            os.close(handle)
        os.close(root_fd)


def _open_relative_link(directory: int, name: str) -> dict:
    try:
        link = os.readlink(name, dir_fd=directory)
    except OSError:
        return _refused("missing")
    if link.startswith("/") or ".." in link.split("/"):
        return _refused("symlink-escapes")
    if "/" in link:
        return _refused("nested-link")
    try:
        handle = os.open(link, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory)
    except OSError:
        return _refused("link-target-unavailable")
    data = os.read(handle, 64)
    os.close(handle)
    return {"blocked": False, "bytes_read": len(data), "opened_outside": False, "operation": "simulated-download", "reason": "internal-link"}
