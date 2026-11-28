"""Independent D03 reference oracles; no executor imports."""
from __future__ import annotations


def fibonacci_oracle(arguments: dict, observed: dict) -> dict:
    n = arguments["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n < 0 or n > 35:
        return {"ok": observed.get("rejected") is True, "method": "independent input-domain validation"}
    values = [0, 1]
    for index in range(2, n + 1):
        values.append(values[-1] + values[-2])
    result = values[n] if n < 2 else values[n]
    naive_calls = 1 if n < 2 else 1
    if n >= 2:
        counts = [1, 1]
        for index in range(2, n + 1):
            counts.append(1 + counts[index - 1] + counts[index - 2])
        naive_calls = counts[n]
    seen: set[int] = set()
    memo_calls = 0

    def visit(index: int) -> None:
        nonlocal memo_calls
        memo_calls += 1
        if index in seen or index < 2:
            return
        seen.add(index)
        visit(index - 1)
        visit(index - 2)

    visit(n)
    expected_misses = len(seen) + min(n + 1, 2)
    expected_hits = memo_calls - expected_misses
    ok = (
        observed.get("rejected") is False
        and observed.get("naive_result") == result
        and observed.get("memoized_result") == result
        and observed.get("naive_calls") == naive_calls
        and observed.get("memoized_misses") == expected_misses
        and observed.get("memoized_hits") == expected_hits
        and observed.get("memoized_total_calls") == memo_calls
        and naive_calls > memo_calls
    )
    return {"ok": ok, "method": "iterative Fibonacci vector and independent memo traversal count"}


def knapsack_oracle(arguments: dict, observed: dict) -> dict:
    items, capacity = arguments["items"], arguments["capacity"]
    if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 0:
        return {"ok": observed.get("rejected") is True, "method": "independent capacity-domain check"}
    if any(not isinstance(row, dict) or set(row) != {"weight", "value"} or row["weight"] <= 0 or row["value"] < 0 for row in items):
        return {"ok": observed.get("rejected") is True, "method": "independent fixture-domain check"}
    best = 0
    for mask in range(1 << len(items)):
        weight = sum(items[i]["weight"] for i in range(len(items)) if mask & (1 << i))
        value = sum(items[i]["value"] for i in range(len(items)) if mask & (1 << i))
        if weight <= capacity:
            best = max(best, value)
    return {"ok": observed.get("rejected") is False and observed.get("maximum_value") == best and observed.get("items_considered") == len(items), "method": "exhaustive subset enumeration"}


def email_oracle(arguments: dict, observed: dict) -> dict:
    def syntactic(address: str) -> bool:
        if address.count("@") != 1 or any(character.isspace() for character in address):
            return False
        local, domain = address.split("@")
        if not local or len(local) > 64 or local.startswith(".") or local.endswith(".") or ".." in local:
            return False
        labels = domain.split(".")
        return (
            len(labels) >= 2
            and all(label and len(label) <= 63 and not label.startswith("-") and not label.endswith("-")
                    and all(character.isalnum() or character == "-" for character in label)
                    for label in labels)
        )
    addresses = arguments["addresses"]
    accepted = [item for item in addresses if syntactic(item)]
    invalid = [item for item in addresses if not syntactic(item)]
    ok = (
        observed.get("rejected") is False
        and observed.get("accepted") == accepted
        and observed.get("invalid") == invalid
        and observed.get("scope") == "syntactic-smoke-test-only-not-rfc-complete-validation"
    )
    return {"ok": ok, "method": "independent address decomposition and label invariants; explicitly not RFC-complete"}


def optional_value_oracle(arguments: dict, observed: dict) -> dict:
    present, value, default = arguments["present"], arguments["value"], arguments["default"]
    source = "absent" if not present else "null" if value is None else "value"
    expected = value if source == "value" else default
    ok = (
        observed.get("rejected") is False
        and observed.get("source") == source
        and observed.get("value") == expected
        and observed.get("dereferenced") is (source == "value")
    )
    return {"ok": ok, "method": "explicit presence/null/value state table"}


def cleanup_oracle(arguments: dict, observed: dict) -> dict:
    try:
        payload = bytes.fromhex(arguments["payload_hex"])
    except (TypeError, ValueError):
        return {"ok": observed.get("rejected") is True and observed.get("reason") == "invalid_hex", "method": "independent hex input rejection"}
    if arguments["fail_read"]:
        ok = observed.get("rejected") is False and observed.get("error") == "OSError" and observed.get("bytes_read") == 0 and observed.get("closed") is True
    else:
        ok = observed.get("rejected") is False and observed.get("error") is None and observed.get("bytes_read") == len(payload) and observed.get("closed") is True
    return {"ok": ok, "method": "input length plus resource lifecycle postcondition"}


def finally_oracle(arguments: dict, observed: dict) -> dict:
    raise_error = arguments["raise_error"]
    expected_type = "ValueError" if raise_error else None
    expected_message = arguments["message"] if raise_error else None
    ok = (
        observed.get("rejected") is False
        and observed.get("finalizer_count") == 1
        and observed.get("error_type") == expected_type
        and observed.get("error_message") == expected_message
        and observed.get("original_error_preserved") is True
    )
    return {"ok": ok, "method": "exception/finalizer state contract independently checked"}


def raii_oracle(arguments: dict, observed: dict) -> dict:
    try:
        payload = bytes.fromhex(arguments["payload_hex"])
    except (TypeError, ValueError):
        return {"ok": observed.get("rejected") is True and observed.get("reason") == "invalid_hex", "method": "independent fixture validation"}
    expected_path = "early_exit" if arguments["early_exit"] else "normal_exit"
    expected_consumed = 0 if arguments["early_exit"] else len(payload)
    ok = (
        observed.get("rejected") is False
        and observed.get("exit_path") == expected_path
        and observed.get("bytes_consumed") == expected_consumed
        and observed.get("released") is True
        and observed.get("release_count") == 1
    )
    return {"ok": ok, "method": "resource acquisition/release invariant and payload-length check"}
