"""Executors for cases outside the earlier batches."""
from __future__ import annotations

import tempfile
from pathlib import Path


def increment(times: int) -> dict:
    value = 0
    for _ in range(times):
        value += 1
    print(value)
    return {"value": value}


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


def acf_lag0(values: list[int]) -> dict:
    mean = sum(values) / len(values)
    variance = sum((item - mean) ** 2 for item in values)
    lag0 = sum((item - mean) ** 2 for item in values) / variance
    print(lag0)
    return {"lag0": lag0}


def linear_integral() -> dict:
    panels = 4
    step = 1 / panels
    total = 0.0 + 1.0
    for index in range(1, panels):
        total += 2 * (index * step)
    print(total * step / 2)
    return {"value": total * step / 2}


def square_integral() -> dict:
    panels = 1000
    step = 1 / panels
    total = 0.0
    for index in range(panels):
        point = (index + 0.5) * step
        total += point * point * step
    print(total)
    return {"value": total}


def cosine_set(pairs: list[list[list[int]]]) -> dict:
    values = []
    for left, right in pairs:
        dot = sum(item * other for item, other in zip(left, right, strict=True))
        left_scale = sum(item * item for item in left) ** 0.5
        right_scale = sum(item * item for item in right) ** 0.5
        values.append(dot / (left_scale * right_scale))
    print(values)
    return {"values": values}


def confined(requested: str) -> dict:
    root = Path(tempfile.mkdtemp(prefix="luna-root-"))
    target = (root / requested).resolve()
    print(target)
    return {"blocked": not target.is_relative_to(root)}
