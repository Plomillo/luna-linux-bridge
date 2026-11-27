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

def shortest_path(nodes: list[str], edges: list[list[str]], start: str, target: str) -> dict:
    if (
        not isinstance(nodes, list) or not nodes
        or any(not isinstance(node, str) or not node for node in nodes)
        or len(set(nodes)) != len(nodes)
        or not isinstance(edges, list)
        or any(not isinstance(edge, list) or len(edge) != 2
               or any(not isinstance(node, str) for node in edge) for edge in edges)
        or any(node not in nodes for edge in edges for node in edge)
        or start not in nodes or target not in nodes
    ):
        return {"rejected": True, "reason": "invalid_graph_or_endpoint"}
    adjacency = {node: [] for node in nodes}
    for source, destination in edges:
        adjacency[source].append(destination)
    queue = [start]
    parent: dict[str, str | None] = {start: None}
    cursor = 0
    while cursor < len(queue):
        node = queue[cursor]
        cursor += 1
        if node == target:
            break
        for neighbor in adjacency[node]:
            if neighbor not in parent:
                parent[neighbor] = node
                queue.append(neighbor)
    if target not in parent:
        return {"rejected": False, "reachable": False, "path": [], "distance": None}
    path = []
    node: str | None = target
    while node is not None:
        path.append(node)
        node = parent[node]
    path.reverse()
    return {"rejected": False, "reachable": True, "path": path, "distance": len(path) - 1}


def matrix_multiply(left: list[list[float]], right: list[list[float]]) -> dict:
    def valid(matrix: object) -> bool:
        return isinstance(matrix, list) and bool(matrix) and all(
            isinstance(row, list) and bool(row)
            and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in row)
            for row in matrix
        ) and len({len(row) for row in matrix}) == 1

    if not valid(left) or not valid(right) or len(left[0]) != len(right):
        return {"rejected": True, "reason": "matrix_dimensions_invalid"}
    result = [
        [sum(left[row][k] * right[k][column] for k in range(len(right)))
         for column in range(len(right[0]))]
        for row in range(len(left))
    ]
    return {"rejected": False, "rows": len(result), "columns": len(result[0]), "result": result}


def determinant_3x3(matrix: list[list[float]]) -> dict:
    if not isinstance(matrix, list) or len(matrix) != 3 or any(
        not isinstance(row, list) or len(row) != 3
        or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in row)
        for row in matrix
    ):
        return {"rejected": True, "reason": "matrix_must_be_3x3"}
    a, b, c = matrix[0]
    d, e, f = matrix[1]
    g, h, i = matrix[2]
    value = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return {"rejected": False, "determinant": value}


def moving_average(values: list[float], window: int) -> dict:
    if (
        not isinstance(values, list)
        or any(not isinstance(value, (int, float)) or isinstance(value, bool) for value in values)
        or not isinstance(window, int) or isinstance(window, bool) or window <= 0
        or window > len(values)
    ):
        return {"rejected": True, "reason": "invalid_window_or_series"}
    averages = [
        sum(values[start:start + window]) / window
        for start in range(len(values) - window + 1)
    ]
    return {"rejected": False, "window": window, "start_indices": list(range(len(averages))), "averages": averages}
