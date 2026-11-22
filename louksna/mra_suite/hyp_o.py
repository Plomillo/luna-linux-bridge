"""Oracle for orchestration cases 585-624."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


def e585(inp):
    return {"terminal": "hash", "deps": ["a"]} if inp["n"] == 2 else {"terminal": "", "deps": []}


def e586(inp):
    graph = {}
    for src, dst in inp["edges"]:
        graph.setdefault(src, []).append(dst)
    color = {}
    def walk(node):
        color[node] = 1
        for nxt in graph.get(node, []):
            if color.get(nxt) == 1 or (color.get(nxt) != 2 and walk(nxt)):
                return True
        color[node] = 2
        return False
    return {"cycle": any(walk(node) for node in list(graph) if color.get(node) != 2)}


def e587(inp):
    return {"builder_deploy": "deploy" in []}


def e588(inp):
    return {"recorded": inp["agent"], "authorized": True}


def e589(inp):
    scope = set(inp["scope"])
    return {"read": "read" in scope, "write": "write" in scope}


def e590(inp):
    evidence = ["e1"]
    return {"owner": "b", "evidence": evidence}


def e591(inp):
    version = inp["start"]
    text = "a"
    def update(seen, value):
        nonlocal version, text
        if seen != version:
            return False
        version += 1
        text = value
        return True
    first = update(1, "b")
    second = update(1, "c")
    return {"first": first, "second": second, "text": text}


def e592(_inp):
    def accept(msg):
        return isinstance(msg.get("id"), int) and set(msg) == {"id", "body"}
    return {"good": accept({"id": 1, "body": "a"}), "bad": accept({"id": "x", "body": "a", "extra": 1})}


def e593(_inp):
    choices = ["x", "x"]
    return {"agreed": len(set(choices)) == 1, "evidence": "e"}


def e594(inp):
    return {"open": len(set(inp["choices"].values())) > 1}


def e595(inp):
    tied = inp["scores"][0] == inp["scores"][1]
    return {"tied": tied, "auto_decided": not tied}


def e596(inp):
    return {"accepted": inp["agent"] == "verified"}


def e597(inp):
    return {"extra": [perm for perm in inp["builder"] if perm != "build"]}


def e598(_inp):
    plans = (("fast", 2, 1), ("safe", 0, 3))
    chosen = sorted(plans, key=lambda plan: (plan[1], plan[2]))[0][0]
    return {"chosen": chosen}


def e599(inp):
    over = any(inp["used"][key] > inp["budget"][key] for key in inp["budget"])
    return {"over": over}


def e600(inp):
    return {"merged": sorted(inp["left"] + inp["right"])}


def e601(inp):
    busy = 0
    def critical():
        nonlocal busy
        if busy:
            return False
        busy = 1
        busy = 0
        return inp["value"]
    return {"ok": critical() == inp["value"], "free": busy == 0}


def e602(_inp):
    tasks = ({"id": "a", "done": True, "reversible": False}, {"id": "b", "done": False, "reversible": True})
    return {"stopped": [task["id"] for task in tasks if not task["done"]], "irreversible": [task["id"] for task in tasks if task["done"] and not task["reversible"]]}


def e603(inp):
    return {"late": inp["finished"] > inp["deadline"]}


def e604(_inp):
    def run(kind):
        return "retried" if kind == "retryable" else "stopped"
    return {"retryable": run("retryable"), "side_effect": run("side-effect")}


def e605(_inp):
    tools = (("local", True), ("remote", False))
    return {"chosen": [name for name, ok in tools if ok]}


def e606(inp):
    installed = {"read"}
    return {"replaced": inp["candidate"] in installed, "browser": inp["removed"] in installed}


def e607(inp):
    return blocked(inp)


def e608(inp):
    session = os.environ.get("XDG_SESSION_TYPE", "")
    display = os.environ.get("WAYLAND_DISPLAY", "")
    runtime = os.environ.get("XDG_RUNTIME_DIR", "")
    socket_ok = bool(display and runtime and (Path(runtime) / display).is_socket())
    plasma = kwin = False
    for pid in Path("/proc").iterdir():
        if not pid.name.isdigit():
            continue
        try:
            cmd = (pid / "cmdline").read_bytes().replace(b"\x00", b" ").decode(errors="replace")
        except OSError:
            continue
        if "plasmashell" in cmd:
            plasma = True
        if "kwin_wayland" in cmd or cmd.startswith("kwin ") or "/kwin " in cmd:
            kwin = True
    if not (session == "wayland" and socket_ok and plasma and kwin):
        return blocked(inp)
    return {"blocked": False, "probe": "desktop", "kde_wayland": True}


def e609(inp):
    proc = subprocess.run([sys.executable, "-c", "import os; print(os.getcwd()); print(os.environ['MRA_LAB'])"], cwd=inp["cwd"], env={"MRA_LAB": "one", "PATH": "/usr/bin:/bin"}, capture_output=True, text=True)
    cwd, lab = proc.stdout.splitlines()
    return {"cwd_ok": cwd == inp["cwd"], "lab": lab, "code": proc.returncode}


def e610(inp):
    return {"result": "ok" if inp["status"] == 200 else "error"}


def e611(inp):
    rows = json.loads(Path(inp["path"]).read_text())
    return {"latest": rows[-1]["v"], "approved": rows[-1]["approved"]}


def e612(inp):
    flags = [True, False]
    started = []
    for ok in flags:
        started.append(ok)
        if not ok:
            break
    return {"ran": len(started), "packaged": False}


def e613(inp):
    digest = hashlib.sha256(Path(inp["src"]).read_bytes()).hexdigest()
    return {"linked": Path(inp["art"]).read_text() == digest}


def e614(inp):
    return {"deployed": all(inp["pre"].values()), "rollback": "previous"}


def e615(inp):
    evidence = {step: hashlib.sha256(step.encode()).hexdigest()[:8] for step in inp["steps"]}
    return {"n": len(evidence)}


def e616(_inp):
    event = {"id": "e1", "t": 1, "origin": "worker", "result": "ok"}
    return {"complete": all(event.values())}


def e617(_inp):
    old, new = ["a", "b"], ["a", "c"]
    return {"old": old, "new": new, "kept_old": old != new}


def e618(inp):
    return {"blocked_remote": not inp["provider"], "local": True}


def e619(inp):
    return {"pending": json.loads(Path(inp["path"]).read_text())["pending"]}


def e620(inp):
    seen = set()
    def accept():
        if inp["key"] in seen:
            return False
        seen.add(inp["key"])
        return True
    return {"first": accept(), "second": accept()}


def e621(_inp):
    return {"trace": ["builder", "reviewer"]}


def e622(_inp):
    stages = (("build", "ok", "h1"), ("test", "fail", "h2"))
    return {"failed": [name for name, state, _ev in stages if state != "ok"], "evidence": stages[1][2]}


def e623(_inp):
    return {"state": "suspended"}


def e624(inp):
    return {"closed": bool(inp["deliverables"])}


TABLE = {i: globals()[f"e{i}"] for i in range(585, 625)}
