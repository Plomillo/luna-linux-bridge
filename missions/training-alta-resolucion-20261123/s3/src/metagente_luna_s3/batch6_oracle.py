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
def fifo_queue_oracle(arguments: dict, observed: dict) -> dict:
    steps = arguments.get("steps")
    if not isinstance(steps, list) or any(not isinstance(step, str) for step in steps):
        expected = {"rejected": True, "reason": "steps_must_be_strings"}
    else:
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
                expected = {"rejected": True, "reason": "unsupported_queue_step"}
                break
        else:
            expected = {"rejected": False, "queue": queue, "dequeued": removed, "events": events, "underflow_count": underflow}
    return {"ok": observed == expected, "expected": expected, "method": "independent FIFO reference model"}


def bst_inorder_oracle(arguments: dict, observed: dict) -> dict:
    values = arguments.get("values")
    if not isinstance(values, list) or any(not isinstance(v, int) or isinstance(v, bool) for v in values):
        expected = {"rejected": True, "reason": "values_must_be_integers"}
    elif len(set(values)) != len(values):
        expected = {"rejected": True, "reason": "duplicate_value"}
    else:
        root = None
        def insert(node, value):
            if node is None:
                return {"value": value, "low": None, "high": None}
            side = "low" if value < node["value"] else "high"
            node[side] = insert(node[side], value)
            return node
        for value in values:
            root = insert(root, value)
        order = []
        def traverse(node):
            if node is None:
                return 0
            left = traverse(node["low"])
            order.append(node["value"])
            right = traverse(node["high"])
            return max(left, right) + 1
        height = traverse(root)
        expected = {"rejected": False, "inorder": sorted(values), "count": len(values), "height": height}
    return {"ok": observed == expected, "expected": expected, "method": "independent dictionary BST model"}


def dfs_graph_oracle(arguments: dict, observed: dict) -> dict:
    nodes, edges, start = arguments.get("nodes"), arguments.get("edges"), arguments.get("start")
    valid = isinstance(nodes, list) and bool(nodes) and len(set(nodes)) == len(nodes) and isinstance(edges, list) and all(
        isinstance(edge, list) and len(edge) == 2 and all(v in nodes for v in edge) for edge in edges
    ) and start in nodes
    if not valid:
        expected = {"rejected": True, "reason": "invalid_graph"}
    else:
        adjacency = {node: [] for node in nodes}
        for source, destination in edges:
            adjacency[source].append(destination)
        visited, active, order, cycle = set(), set(), [], False
        def visit(node):
            nonlocal cycle
            visited.add(node)
            active.add(node)
            order.append(node)
            for child in adjacency[node]:
                if child in active:
                    cycle = True
                elif child not in visited:
                    visit(child)
            active.remove(node)
        visit(start)
        expected = {"rejected": False, "order": order, "visited_count": len(order), "cycle": cycle}
    return {"ok": observed == expected, "expected": expected, "method": "recursive DFS reference model"}


def linked_list_oracle(arguments: dict, observed: dict) -> dict:
    ops = arguments.get("operations")
    values, history = [], []
    if not isinstance(ops, list):
        expected = {"rejected": True, "reason": "operations_must_be_list"}
    else:
        for op in ops:
            if not isinstance(op, dict) or op.get("op") not in {"insert", "delete"}:
                expected = {"rejected": True, "reason": "invalid_operation"}
                break
            index = op.get("index")
            if not isinstance(index, int) or isinstance(index, bool):
                expected = {"rejected": True, "reason": "index_must_be_integer"}
                break
            if op["op"] == "insert":
                if not 0 <= index <= len(values) or not isinstance(op.get("value"), int) or isinstance(op.get("value"), bool):
                    expected = {"rejected": True, "reason": "insert_bounds_or_value_invalid"}
                    break
                values.insert(index, op["value"])
                history.append({"operation": "insert", "index": index, "value": op["value"], "length": len(values)})
            else:
                if not 0 <= index < len(values):
                    expected = {"rejected": True, "reason": "delete_index_out_of_bounds"}
                    break
                value = values.pop(index)
                history.append({"operation": "delete", "index": index, "value": value, "length": len(values)})
        else:
            expected = {"rejected": False, "values": values, "length": len(values), "history": history}
    return {"ok": observed == expected, "expected": expected, "method": "independent array reference"}
def dijkstra_oracle(arguments, observed):
    nodes,edges,start,target=(arguments.get("nodes"),arguments.get("edges"),arguments.get("start"),arguments.get("target"))
    valid=isinstance(nodes,list) and bool(nodes) and len(set(nodes))==len(nodes) and isinstance(edges,list) and all(isinstance(e,list) and len(e)==3 and e[0] in nodes and e[1] in nodes and isinstance(e[2],(int,float)) and not isinstance(e[2],bool) for e in edges) and start in nodes and target in nodes
    if not valid:expected={"rejected":True,"reason":"invalid_graph"}
    elif any(weight<0 for _,_,weight in edges):expected={"rejected":True,"reason":"negative_weight_rejected"}
    else:
        dist={node:float("inf") for node in nodes};pred={};dist[start]=0
        for _ in range(len(nodes)-1):
            changed=False
            for source,destination,weight in edges:
                if dist[source]!=float("inf") and dist[source]+weight<dist[destination]:
                    dist[destination]=dist[source]+weight;pred[destination]=source;changed=True
            if not changed:break
        reachable=dist[target]!=float("inf");path=[]
        if reachable:
            cursor=target
            while cursor!=start:path.append(cursor);cursor=pred[cursor]
            path.append(start);path.reverse()
        expected={"rejected":False,"reachable":reachable,"distance":dist[target] if reachable else None,"path":path,"distances":{node:dist[node] if dist[node]!=float("inf") else None for node in nodes}}
    return {"ok":observed==expected,"expected":expected,"method":"independent Bellman-Ford oracle"}


def avl_tree_oracle(arguments, observed):
    values=arguments.get("values")
    if not isinstance(values,list) or any(not isinstance(v,int) or isinstance(v,bool) for v in values):return {"ok":observed=={"rejected":True,"reason":"values_must_be_integers"},"method":"input contract"}
    if len(set(values))!=len(values):return {"ok":observed=={"rejected":True,"reason":"duplicate_value"},"method":"duplicate contract"}
    order=[];balanced=True
    def audit(node):
        nonlocal balanced
        if node is None:return 0
        if not isinstance(node,dict) or set(node)!={"value","left","right"} or not isinstance(node["value"],int) or isinstance(node["value"],bool):balanced=False;return 0
        left=audit(node["left"]);order.append(node["value"]);right=audit(node["right"])
        if abs(left-right)>1:balanced=False
        return max(left,right)+1
    height=audit(observed.get("root"));sorted_values=sorted(values)
    ok=observed.get("rejected") is False and order==sorted_values and observed.get("inorder")==sorted_values and observed.get("count")==len(values) and observed.get("height")==height and observed.get("balanced") is balanced and balanced
    if len(values)==1000:ok=ok and height<=10
    return {"ok":ok,"method":"independent structural AVL audit"}


def bellman_ford_cycle_oracle(arguments, observed):
    nodes,edges,start=arguments.get("nodes"),arguments.get("edges"),arguments.get("start")
    valid=isinstance(nodes,list) and bool(nodes) and len(set(nodes))==len(nodes) and isinstance(edges,list) and all(isinstance(e,list) and len(e)==3 and e[0] in nodes and e[1] in nodes and isinstance(e[2],(int,float)) and not isinstance(e[2],bool) for e in edges) and start in nodes
    if not valid:expected={"rejected":True,"reason":"invalid_graph"}
    else:
        dist={node:None for node in nodes};dist[start]=0
        for _ in range(len(nodes)-1):
            for source,destination,weight in edges:
                if dist[source] is not None and (dist[destination] is None or dist[source]+weight<dist[destination]):dist[destination]=dist[source]+weight
        cycle=any(dist[source] is not None and (dist[destination] is None or dist[source]+weight<dist[destination]) for source,destination,weight in edges)
        expected={"rejected":False,"negative_cycle_reachable":cycle,"distances":None if cycle else dist}
    return {"ok":observed==expected,"expected":expected,"method":"independent Bellman-Ford relaxation"}


def linear_search_complexity_oracle(arguments, observed):
    sizes,target=arguments.get("sizes"),arguments.get("target")
    if not isinstance(sizes,list) or any(not isinstance(n,int) or isinstance(n,bool) or n<=0 for n in sizes) or not isinstance(target,int) or isinstance(target,bool):expected={"rejected":True,"reason":"invalid_sizes_or_target"}
    else:
        rows=[]
        for size in sizes:
            comparisons,index=0,None
            for candidate in range(size):
                comparisons+=1
                if candidate==target:index=candidate;break
            rows.append({"size":size,"comparisons":comparisons,"index":index,"found":index is not None})
        expected={"rejected":False,"measurements":rows,"growth_ratios":[rows[i]["comparisons"]/rows[i-1]["comparisons"] for i in range(1,len(rows))],"complexity":"LINEAR"}
    return {"ok":observed==expected,"expected":expected,"method":"independent direct-count search"}
