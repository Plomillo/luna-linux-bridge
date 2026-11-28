"""Source-grounded D03 programming and resource-lifecycle executors."""
from __future__ import annotations

import io
import re
from functools import cache


def fibonacci_compare(n: int) -> dict:
    if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > 35:
        return {"rejected": True, "reason": "invalid_fibonacci_index"}
    naive_calls = 0

    def naive(value: int) -> int:
        nonlocal naive_calls
        naive_calls += 1
        if value < 2:
            return value
        return naive(value - 1) + naive(value - 2)

    memo_calls = 0

    @cache
    def memoized(value: int) -> int:
        nonlocal memo_calls
        memo_calls += 1
        if value < 2:
            return value
        return memoized(value - 1) + memoized(value - 2)

    plain = naive(n)
    cached = memoized(n)
    info = memoized.cache_info()
    return {
        "rejected": False,
        "n": n,
        "naive_result": plain,
        "memoized_result": cached,
        "naive_calls": naive_calls,
        "memoized_misses": memo_calls,
        "memoized_hits": info.hits,
        "memoized_total_calls": memo_calls + info.hits,
    }


def knapsack_01(items: list[dict], capacity: int) -> dict:
    if (not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 0
            or not isinstance(items, list)
            or any(not isinstance(row, dict) or set(row) != {"weight", "value"}
                   or not isinstance(row["weight"], int) or isinstance(row["weight"], bool)
                   or row["weight"] <= 0 or not isinstance(row["value"], int)
                   or isinstance(row["value"], bool) or row["value"] < 0 for row in items)):
        return {"rejected": True, "reason": "invalid_knapsack_fixture"}
    table = [0] * (capacity + 1)
    for item in items:
        weight, value = item["weight"], item["value"]
        for room in range(capacity, weight - 1, -1):
            table[room] = max(table[room], table[room - weight] + value)
    best_value = table[capacity]
    return {
        "rejected": False,
        "capacity": capacity,
        "maximum_value": best_value,
        "algorithm": "0/1_DYNAMIC_PROGRAMMING",
        "items_considered": len(items),
    }


_EMAIL = re.compile(r"^[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+$")


def email_syntax(addresses: list[str]) -> dict:
    if not isinstance(addresses, list) or any(not isinstance(item, str) for item in addresses):
        return {"rejected": True, "reason": "addresses_must_be_strings"}
    accepted = [item for item in addresses if _EMAIL.fullmatch(item)]
    rejected = [item for item in addresses if item not in accepted]
    return {
        "rejected": False,
        "accepted": accepted,
        "invalid": rejected,
        "scope": "syntactic-smoke-test-only-not-rfc-complete-validation",
    }


def optional_value(present: bool, value: str | None, default: str) -> dict:
    if not isinstance(present, bool) or not isinstance(default, str) or (value is not None and not isinstance(value, str)):
        return {"rejected": True, "reason": "invalid_optional_value_input"}
    if not present:
        return {"rejected": False, "source": "absent", "value": default, "dereferenced": False}
    if value is None:
        return {"rejected": False, "source": "null", "value": default, "dereferenced": False}
    return {"rejected": False, "source": "value", "value": value, "dereferenced": True}


def read_cleanup(payload_hex: str, fail_read: bool) -> dict:
    try:
        payload = bytes.fromhex(payload_hex)
    except (TypeError, ValueError):
        return {"rejected": True, "reason": "invalid_hex", "closed": False}
    stream = io.BytesIO(payload)
    bytes_read = 0
    error = None
    try:
        if fail_read:
            raise OSError("fixture_read_failure")
        bytes_read = len(stream.read())
    except OSError as exc:
        error = type(exc).__name__
    finally:
        stream.close()
    return {
        "rejected": False,
        "bytes_read": bytes_read,
        "error": error,
        "closed": stream.closed,
    }


def finally_once(raise_error: bool, message: str) -> dict:
    if not isinstance(raise_error, bool) or not isinstance(message, str):
        return {"rejected": True, "reason": "invalid_finally_fixture"}
    finalizer_count = 0
    error_type = None
    error_message = None
    try:
        if raise_error:
            raise ValueError(message)
    except ValueError as exc:
        error_type = type(exc).__name__
        error_message = str(exc)
    finally:
        finalizer_count += 1
    return {
        "rejected": False,
        "error_type": error_type,
        "error_message": error_message,
        "finalizer_count": finalizer_count,
        "original_error_preserved": error_type == ("ValueError" if raise_error else None),
    }


class _ManagedResource:
    def __init__(self) -> None:
        self.release_count = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        self.release_count += 1
        return False


def raii_release(early_exit: bool, payload_hex: str) -> dict:
    if not isinstance(early_exit, bool):
        return {"rejected": True, "reason": "invalid_exit_mode"}
    try:
        payload = bytes.fromhex(payload_hex)
    except (TypeError, ValueError):
        return {"rejected": True, "reason": "invalid_hex"}
    resource = _ManagedResource()
    with resource:
        path = "early_exit" if early_exit else "normal_exit"
        consumed = 0 if early_exit else len(payload)
    return {
        "rejected": False,
        "exit_path": path,
        "bytes_consumed": consumed,
        "released": resource.release_count == 1,
        "release_count": resource.release_count,
    }
