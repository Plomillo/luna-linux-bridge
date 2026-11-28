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
def fifo_queue(steps: list[str]) -> dict:
    if not isinstance(steps, list) or any(not isinstance(step, str) for step in steps):
        return {"rejected": True, "reason": "steps_must_be_strings"}
    queue, removed, events, underflow = [], [], [], 0
    for step in steps:
        if step.startswith("enqueue:") and step[8:]:
            queue.append(step[8:])
            events.append({"operation": "enqueue", "value": step[8:]})
        elif step == "dequeue":
            if queue:
                value = queue.pop(0)
                removed.append(value)
                events.append({"operation": "dequeue", "value": value})
            else:
                underflow += 1
                events.append({"operation": "underflow", "source": "dequeue"})
        else:
            return {"rejected": True, "reason": "unsupported_queue_step"}
    return {"rejected": False, "queue": queue, "dequeued": removed, "events": events, "underflow_count": underflow}


def bst_inorder(values: list[int]) -> dict:
    if not isinstance(values, list) or any(not isinstance(v, int) or isinstance(v, bool) for v in values):
        return {"rejected": True, "reason": "values_must_be_integers"}
    class Node:
        __slots__ = ("value", "left", "right")
        def __init__(self, value):
            self.value, self.left, self.right = value, None, None
    root = None
    for value in values:
        if root is None:
            root = Node(value)
            continue
        node = root
        while True:
            if value == node.value:
                return {"rejected": True, "reason": "duplicate_value"}
            branch = "left" if value < node.value else "right"
            child = getattr(node, branch)
            if child is None:
                setattr(node, branch, Node(value))
                break
            node = child
    ordered = []
    def visit(node):
        if node is None:
            return 0
        left = visit(node.left)
        ordered.append(node.value)
        right = visit(node.right)
        return max(left, right) + 1
    height = visit(root)
    return {"rejected": False, "inorder": ordered, "count": len(ordered), "height": height}


def dfs_graph(nodes: list[str], edges: list[list[str]], start: str) -> dict:
    if (not isinstance(nodes, list) or not nodes or len(set(nodes)) != len(nodes)
        or any(not isinstance(n, str) or not n for n in nodes)
        or not isinstance(edges, list)
        or any(not isinstance(e, list) or len(e) != 2 or any(not isinstance(v, str) for v in e) for e in edges)
        or any(v not in nodes for e in edges for v in e) or start not in nodes):
        return {"rejected": True, "reason": "invalid_graph"}
    adjacency = {node: [] for node in nodes}
    for source, target in edges:
        adjacency[source].append(target)
    colors = {node: 0 for node in nodes}
    order, cycle, stack = [], False, [(start, 0)]
    colors[start] = 1
    order.append(start)
    while stack:
        node, index = stack[-1]
        if index == len(adjacency[node]):
            colors[node] = 2
            stack.pop()
            continue
        neighbor = adjacency[node][index]
        stack[-1] = (node, index + 1)
        if colors[neighbor] == 1:
            cycle = True
        elif colors[neighbor] == 0:
            colors[neighbor] = 1
            order.append(neighbor)
            stack.append((neighbor, 0))
    return {"rejected": False, "order": order, "visited_count": len(order), "cycle": cycle}


def linked_list(operations: list[dict]) -> dict:
    if not isinstance(operations, list):
        return {"rejected": True, "reason": "operations_must_be_list"}
    class Node:
        __slots__ = ("value", "next")
        def __init__(self, value):
            self.value, self.next = value, None
    head, size, history = None, 0, []
    for op in operations:
        if not isinstance(op, dict) or op.get("op") not in {"insert", "delete"}:
            return {"rejected": True, "reason": "invalid_operation"}
        index = op.get("index")
        if not isinstance(index, int) or isinstance(index, bool):
            return {"rejected": True, "reason": "index_must_be_integer"}
        if op["op"] == "insert":
            if not 0 <= index <= size or not isinstance(op.get("value"), int) or isinstance(op.get("value"), bool):
                return {"rejected": True, "reason": "insert_bounds_or_value_invalid"}
            new = Node(op["value"])
            if index == 0:
                new.next, head = head, new
            else:
                previous = head
                for _ in range(index - 1):
                    previous = previous.next
                new.next, previous.next = previous.next, new
            size += 1
            history.append({"operation": "insert", "index": index, "value": op["value"], "length": size})
        else:
            if not 0 <= index < size:
                return {"rejected": True, "reason": "delete_index_out_of_bounds"}
            if index == 0:
                removed, head = head.value, head.next
            else:
                previous = head
                for _ in range(index - 1):
                    previous = previous.next
                removed, previous.next = previous.next.value, previous.next.next
            size -= 1
            history.append({"operation": "delete", "index": index, "value": removed, "length": size})
    values, node = [], head
    while node is not None:
        values.append(node.value)
        node = node.next
    return {"rejected": False, "values": values, "length": size, "history": history}
