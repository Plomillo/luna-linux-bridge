"""Independent reference implementations for D03 batch-six executors."""
from __future__ import annotations

from collections import Counter


def stable_ages_oracle(arguments: dict, observed: dict) -> dict:
    records = arguments["records"]
    valid = isinstance(records, list) and all(
        isinstance(row, dict)
        and isinstance(row.get("id"), str)
        and bool(row.get("id"))
        and isinstance(row.get("age"), int)
        and not isinstance(row.get("age"), bool)
        for row in records
    )
    if not valid:
        ok = isinstance(observed, dict) and observed.get("rejected") is True
        return {"ok": ok, "expected": {"rejected": True}, "method": "independent input-contract rejection"}
    expected = []
    for row in records:
        insertion = len(expected)
        for index, current in enumerate(expected):
            if current["age"] > row["age"]:
                insertion = index
                break
        expected.insert(insertion, row)
    ordered = observed.get("records") if isinstance(observed, dict) else None
    stable = ordered == expected
    nondecreasing = all(
        ordered[index]["age"] <= ordered[index + 1]["age"]
        for index in range(len(ordered) - 1)
    ) if isinstance(ordered, list) else False
    return {
        "ok": stable and nondecreasing and observed.get("rejected") is False,
        "expected": {"records": expected},
        "method": "independent stable insertion-sort oracle",
    }


def stack_sequence_oracle(arguments: dict, observed: dict) -> dict:
    steps = arguments["steps"]
    if not isinstance(steps, list) or any(not isinstance(step, str) for step in steps):
        ok = isinstance(observed, dict) and observed.get("rejected") is True
        return {"ok": ok, "expected": {"rejected": True}, "method": "independent input-contract rejection"}
    reference_stack = []
    reference_events = []
    underflows = 0
    for step in steps:
        if step.startswith("push:"):
            try:
                value = int(step.split(":", 1)[1])
            except ValueError:
                return {"ok": observed.get("rejected") is True, "expected": {"rejected": True}, "method": "independent malformed-push rejection"}
            reference_stack.append(value)
            reference_events.append({"operation": "push", "value": value})
        elif step == "peek":
            if reference_stack:
                reference_events.append({"operation": "peek", "value": reference_stack[-1]})
            else:
                underflows += 1
                reference_events.append({"operation": "underflow", "source": "peek"})
        elif step == "pop":
            if reference_stack:
                reference_events.append({"operation": "pop", "value": reference_stack.pop()})
            else:
                underflows += 1
                reference_events.append({"operation": "underflow", "source": "pop"})
        else:
            return {"ok": observed.get("rejected") is True, "expected": {"rejected": True}, "method": "independent unsupported-operation rejection"}
    expected = {
        "events": reference_events,
        "stack": reference_stack,
        "underflow_count": underflows,
        "rejected": False,
    }
    return {
        "ok": observed == expected,
        "expected": expected,
        "method": "independent stack state-machine oracle",
    }


def descending_values_oracle(arguments: dict, observed: dict) -> dict:
    values = arguments["values"]
    valid = isinstance(values, list) and all(
        isinstance(value, int) and not isinstance(value, bool) for value in values
    )
    if not valid:
        ok = isinstance(observed, dict) and observed.get("rejected") is True
        return {"ok": ok, "expected": {"rejected": True}, "method": "independent integer-domain validation"}
    ordered = observed.get("ordered") if isinstance(observed, dict) else None
    observed_values_valid = isinstance(ordered, list) and all(
        isinstance(value, int) and not isinstance(value, bool) for value in ordered
    )
    is_permutation = observed_values_valid and Counter(ordered) == Counter(values)
    nonincreasing = isinstance(ordered, list) and all(
        ordered[index] >= ordered[index + 1] for index in range(len(ordered) - 1)
    )
    return {
        "ok": observed.get("rejected") is False and is_permutation and nonincreasing,
        "expected": {"count": len(values), "nonincreasing": True, "permutation": True},
        "method": "independent multiset equality and adjacent-order invariants",
    }
