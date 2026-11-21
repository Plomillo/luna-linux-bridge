"""Oracle for observability cases 625-664."""
from __future__ import annotations

import time


def expect(n, inp):
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


def e625(inp):
    required = ("ts", "level", "msg", "component")
    return {"missing": [key for key in required if key not in inp["keys"]]}


def e626(inp):
    hops = ({"cid": inp["cid"]}, {"cid": inp["cid"]})
    return {"same": len({hop["cid"] for hop in hops}) == 1}


def e627(_inp):
    spans = (("a", ""), ("b", "a"))
    return {"linked": spans[1][1] == spans[0][0]}


def e628(inp):
    observed = sum(inp["samples"]) // len(inp["samples"])
    return {"match": observed == 20}


def e629(inp):
    return {"high_cardinality": inp["n"] > 10}


def e630(inp):
    ratio = 950
    return {"ratio_milli": ratio, "met": ratio >= inp["slo_milli"]}


def e631(inp):
    errors = 6
    return {"fired": errors > inp["threshold"], "errors": errors}


def e632(inp):
    series = [1, 1, 1, 1, 9]
    mean = sum(series) / len(series)
    return {"flagged": len([value for value in series if value > mean * 2])}


def e633(inp):
    return {"healthy": bool(inp["process"] and inp["ready"])}


def e634(_inp):
    def client(path):
        return 200 if path == "/health" else 404
    return {"status": client("/health"), "miss": client("/missing")}


def e635(inp):
    import tracemalloc
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    blob = bytearray(1000 * inp["chunks"])
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return {"grew": after > before or len(blob) > 0 and after >= before}


def e636(inp):
    def elapsed(n):
        start = time.perf_counter_ns()
        total = 0
        for i in range(n):
            total += i
        return time.perf_counter_ns() - start, total
    hot, _ = elapsed(inp["n"])
    cold, _ = elapsed(1)
    return {"hot_slower": hot > cold}


def e637(inp):
    return {"refused": inp["need"] > inp["free"]}


def e638(inp):
    files = 0
    failed = False
    while files < 5:
        if files >= inp["inodes"]:
            failed = True
            break
        files += 1
    return {"failed": failed, "files": files}


def e639(_inp):
    held = {"a": "t1", "b": "t2"}
    waits = {"t1": "b", "t2": "a"}
    cycle = waits[held["a"]] == "b" and waits[held["b"]] == "a"
    return {"cycle": cycle, "timed_out": True}


def e640(inp):
    stalled = len(set(inp["samples"])) == 1
    return {"stalled": stalled, "stopped": stalled}


def e641(_inp):
    cold = 0
    was = cold == 0
    cold = 1
    return {"was_starved": was, "after": cold}


def e642(inp):
    queued = [1, 2, 3]
    kept = queued[: inp["capacity"]]
    return {"kept": len(kept), "dropped": len(queued) - len(kept)}


def e643(inp):
    return {"allowed": min(4, inp["downstream"])}


def e644(inp):
    failures = 0
    state = "closed"
    while failures < inp["threshold"]:
        failures += 1
        state = "open"
    if state == "open":
        state = "closed"
    return {"opened": failures == inp["threshold"], "closed": state == "closed"}


def e645(inp):
    return {"isolated": inp["parts"]["api"] == "up" and inp["parts"]["db"] == "down"}


def e646(inp):
    spent = 0
    ran = 0
    for hop in (2, 2, 2):
        if spent + hop > inp["budget"]:
            break
        spent += hop
        ran += 1
    return {"ran": ran, "spent": spent}


def e647(inp):
    jitter = (0, 1, 0)
    scheduled = [base + extra for base, extra in zip(inp["base"], jitter)]
    return {"scheduled": scheduled, "spread": max(scheduled) - min(scheduled)}


def e648(inp):
    steps = inp["steps"]
    jump = max(steps[i + 1] - steps[i] for i in range(len(steps) - 1))
    return {"max_jump": jump}


def e649(inp):
    return {"mode": "full" if inp["secondary"] else "degraded"}


def e650(inp):
    return {"active": "primary" if inp["primary"] else "backup"}


def e651(inp):
    loss = 13 - 10
    return {"loss": loss, "within": loss <= inp["bound"]}


def e652(_inp):
    log = (("commit", "a"), ("write", "b"))
    state = [value for kind, value in log if kind == "commit"]
    return {"state": state}


def e653(_inp):
    state = {"n": 0}
    def recover():
        state["n"] = 1
        return state["n"]
    return {"first": recover(), "second": recover()}


def e654(inp):
    applied = []
    def handle():
        if inp["event"] in applied:
            return False
        applied.append(inp["event"])
        return True
    return {"first": handle(), "second": handle()}


def e655(inp):
    return {"compensation": ["release"] if inp["failed"] == "charge" else []}


def e656(_inp):
    declared, observed = 1, 2
    return {"delta": observed if observed != declared else 0}


def e657(inp):
    deps = {"api": ["db", "cache"]}
    return {"affected": [name for name, needs in deps.items() if inp["down"] in needs]}


def e658(inp):
    return blocked(inp)


def e659(inp):
    tools = {"read"}
    raised = inp["missing"] not in tools
    return {"raised": raised, "simulated": False}


def e660(_inp):
    tasks = {"a": "confirmed", "b": "pending", "c": "unknown"}
    return {state: sorted(name for name, value in tasks.items() if value == state) for state in ("confirmed", "pending", "unknown")}


def e661(inp):
    return {"resumed": inp["next"]}


def e662(inp):
    state = ["a", "b", "c"]
    return {"missing": [item for item in state if item not in inp["log"]]}


def e663(_inp):
    return {"followed": True, "deviation": ""}


def e664(_inp):
    return {"stopped": True, "escalated": True}


TABLE = {i: globals()[f"e{i}"] for i in range(625, 665)}
