"""Executors for cases outside the earlier batches."""
from __future__ import annotations

import tempfile
from pathlib import Path


def increment(times: int) -> dict:
    completed = [{"id": index, "status": "ok"} for index in range(times)]
    print(len(completed))
    return {"completed": len(completed), "failed": 0, "ids": [item["id"] for item in completed]}


def pearson(left: list[int], right: list[int]) -> dict:
    count = len(left)
    mean_left = sum(left) / count
    mean_right = sum(right) / count
    numerator = sum((item - mean_left) * (other - mean_right) for item, other in zip(left, right, strict=True))
    left_scale = sum((item - mean_left) ** 2 for item in left) ** 0.5
    right_scale = sum((item - mean_right) ** 2 for item in right) ** 0.5
    value = numerator / (left_scale * right_scale)
    print(value)
    return {"value": value}


def acf_series(values: list[int]) -> dict:
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values)
    lags = []
    for lag in range(len(values)):
        numerator = sum((values[index] - mean) * (values[index + lag] - mean) for index in range(len(values) - lag))
        lags.append(numerator / variance)
    print(lags)
    return {"lags": lags}


def linear_integral() -> dict:
    panels = 4
    step = 1 / panels
    weights = [1, *([2] * (panels - 1)), 1]
    total = 0.0
    for index, weight in enumerate(weights):
        total += weight * (index * step)
    value = total * step / 2
    print(value)
    return {"value": value, "method": "trapezoidal", "panels": panels, "weights": weights}


def square_integral() -> dict:
    panels = 4
    step = 1 / panels
    weights = [1 if index in {0, panels} else 4 if index % 2 else 2 for index in range(panels + 1)]
    total = 0.0
    for index, weight in enumerate(weights):
        point = index * step
        total += weight * point * point
    value = total * step / 3
    print(value)
    return {"value": value, "method": "simpson", "panels": panels, "weights": weights}


def cosine_set(pairs: list[list[list[int]]]) -> dict:
    values = []
    for left, right in pairs:
        dot = sum(item * other for item, other in zip(left, right, strict=True))
        left_scale = sum(item * item for item in left) ** 0.5
        right_scale = sum(item * item for item in right) ** 0.5
        values.append(dot / (left_scale * right_scale))
    print(values)
    return {"values": values}


def request_log(successes: int, failures: int) -> dict:
    requests = [{"id": index, "ok": True} for index in range(successes)]
    requests.extend({"id": successes + index, "ok": False} for index in range(failures))
    completed = sum(item["ok"] for item in requests)
    total = len(requests)
    print(completed, total)
    return {"availability": completed / total, "successes": completed, "failures": total - completed, "total": total}


def confined(requested: str) -> dict:
    root = Path(tempfile.mkdtemp(prefix="luna-root-"))
    (root / "allowed.txt").write_text("payload")
    outside = Path(tempfile.mkdtemp(prefix="luna-out-"))
    secret = outside / "secret.txt"
    secret.write_text("secret")
    (root / "escape").symlink_to(secret)
    target = (root / requested).resolve()
    try:
        target.relative_to(root.resolve())
        inside = True
    except ValueError:
        inside = False
    read = len(target.read_bytes()) if inside and target.is_file() else 0
    print(inside, read)
    return {"blocked": not inside, "bytes_read": read, "operation": "simulated-download"}
