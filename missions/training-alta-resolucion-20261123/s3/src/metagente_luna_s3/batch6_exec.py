"""Executors for the source-grounded D03 batch-six cases."""
from __future__ import annotations


def stable_ages(records: list[dict]) -> dict:
    if not isinstance(records, list) or any(
        not isinstance(row, dict)
        or not isinstance(row.get("id"), str)
        or not row.get("id")
        or not isinstance(row.get("age"), int)
        or isinstance(row.get("age"), bool)
        for row in records
    ):
        return {"rejected": True, "reason": "records require string id and integer age"}
    ordered = sorted(records, key=lambda row: row["age"])
    ids_by_age: dict[str, list[str]] = {}
    for row in ordered:
        ids_by_age.setdefault(str(row["age"]), []).append(row["id"])
    return {"records": ordered, "ids_by_age": ids_by_age, "rejected": False}


def stack_sequence(steps: list[str]) -> dict:
    if not isinstance(steps, list) or any(not isinstance(step, str) for step in steps):
        return {"rejected": True, "reason": "steps must be a list of strings"}
    stack: list[int] = []
    events: list[dict] = []
    underflow_count = 0
    for step in steps:
        if step.startswith("push:"):
            try:
                value = int(step.split(":", 1)[1])
            except ValueError:
                return {"rejected": True, "reason": "push requires an integer"}
            stack.append(value)
            events.append({"operation": "push", "value": value})
        elif step == "peek":
            if stack:
                events.append({"operation": "peek", "value": stack[-1]})
            else:
                underflow_count += 1
                events.append({"operation": "underflow", "source": "peek"})
        elif step == "pop":
            if stack:
                events.append({"operation": "pop", "value": stack.pop()})
            else:
                underflow_count += 1
                events.append({"operation": "underflow", "source": "pop"})
        else:
            return {"rejected": True, "reason": f"unsupported stack operation: {step}"}
    return {
        "events": events,
        "stack": stack,
        "underflow_count": underflow_count,
        "rejected": False,
    }
