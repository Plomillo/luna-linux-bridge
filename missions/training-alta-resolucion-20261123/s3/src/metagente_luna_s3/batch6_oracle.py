"""Independent reference implementations for D03 batch-six executors."""
from __future__ import annotations


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

def shortest_path_oracle(arguments: dict, observed: dict) -> dict:
    nodes, edges = arguments["nodes"], arguments["edges"]
    start, target = arguments["start"], arguments["target"]
    valid = (
        isinstance(nodes, list) and bool(nodes)
        and all(isinstance(node, str) and node for node in nodes)
        and len(set(nodes)) == len(nodes)
        and isinstance(edges, list)
        and all(isinstance(edge, list) and len(edge) == 2
                and all(isinstance(node, str) and node in nodes for node in edge) for edge in edges)
        and start in nodes and target in nodes
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent graph input contract"}
    frontier = [start]
    paths = {start: [start]}
    while frontier and target not in paths:
        next_frontier = []
        for vertex in frontier:
            for source, destination in edges:
                if source == vertex and destination not in paths:
                    paths[destination] = paths[vertex] + [destination]
                    next_frontier.append(destination)
        frontier = next_frontier
    expected_path = paths.get(target)
    expected = (
        {"rejected": False, "reachable": False, "path": [], "distance": None}
        if expected_path is None
        else {"rejected": False, "reachable": True, "path": expected_path, "distance": len(expected_path) - 1}
    )
    return {"ok": observed == expected, "expected": expected, "method": "independent layer-expansion shortest-path oracle"}


def matrix_multiply_oracle(arguments: dict, observed: dict) -> dict:
    left, right = arguments["left"], arguments["right"]
    valid = (
        isinstance(left, list) and bool(left)
        and all(isinstance(row, list) and bool(row)
                and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in row) for row in left)
        and len({len(row) for row in left}) == 1
        and isinstance(right, list) and bool(right)
        and all(isinstance(row, list) and bool(row)
                and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in row) for row in right)
        and len({len(row) for row in right}) == 1
        and len(left[0]) == len(right)
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent matrix shape validation"}
    rows, cols = len(left), len(right[0])
    expected_values = []
    for row in range(rows):
        output_row = []
        for column in range(cols):
            accumulator = 0
            for inner in range(len(right)):
                accumulator += left[row][inner] * right[inner][column]
            output_row.append(accumulator)
        expected_values.append(output_row)
    expected = {"rejected": False, "rows": rows, "columns": cols, "result": expected_values}
    return {"ok": observed == expected, "expected": expected, "method": "independent triple-loop matrix oracle"}


def determinant_3x3_oracle(arguments: dict, observed: dict) -> dict:
    matrix = arguments["matrix"]
    valid = isinstance(matrix, list) and len(matrix) == 3 and all(
        isinstance(row, list) and len(row) == 3
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in row)
        for row in matrix
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent determinant shape check"}
    rows = matrix
    expected_value = (
        rows[0][0] * rows[1][1] * rows[2][2]
        + rows[0][1] * rows[1][2] * rows[2][0]
        + rows[0][2] * rows[1][0] * rows[2][1]
        - rows[0][2] * rows[1][1] * rows[2][0]
        - rows[0][1] * rows[1][0] * rows[2][2]
        - rows[0][0] * rows[1][2] * rows[2][1]
    )
    expected = {"rejected": False, "determinant": expected_value}
    return {"ok": observed == expected, "expected": expected, "method": "independent six-term determinant expansion"}


def moving_average_oracle(arguments: dict, observed: dict) -> dict:
    values, window = arguments["values"], arguments["window"]
    valid = (
        isinstance(values, list)
        and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values)
        and isinstance(window, int) and not isinstance(window, bool)
        and 0 < window <= len(values)
    )
    if not valid:
        return {"ok": observed.get("rejected") is True, "method": "independent moving-window preconditions"}
    expected_values = []
    for index in range(window - 1, len(values)):
        expected_values.append(sum(values[index - window + 1:index + 1]) / window)
    expected = {
        "rejected": False, "window": window,
        "start_indices": list(range(len(expected_values))), "averages": expected_values,
    }
    return {"ok": observed == expected, "expected": expected, "method": "independent window-index recomputation"}
