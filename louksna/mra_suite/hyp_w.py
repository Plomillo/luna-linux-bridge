"""Orchestration cases 585-624. In-process missions; no desktop session is invented."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pack import pack

DOMAIN = "hyper"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, 3, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


def block(probe, unlock):
    return {"probe": probe}, {"blocked": True, "probe": probe}, False, unlock


DISPATCH = {}


def c585(_c):
    tasks = [{"id": "a", "done": "file"}, {"id": "b", "done": "hash", "after": ["a"]}]
    return {"n": 2}, {"terminal": tasks[1]["done"], "deps": tasks[1]["after"]}, tasks[1]["after"] == ["a"], ""


def c586(_c):
    edges = [("a", "b"), ("b", "c"), ("c", "a")]
    def cyclic(pairs):
        graph = {}
        for src, dst in pairs:
            graph.setdefault(src, []).append(dst)
        seen, stack = set(), set()
        def walk(node):
            if node in stack:
                return True
            if node in seen:
                return False
            seen.add(node)
            stack.add(node)
            if any(walk(nxt) for nxt in graph.get(node, [])):
                return True
            stack.remove(node)
            return False
        return any(walk(node) for node in graph)
    return {"edges": [list(e) for e in edges]}, {"cycle": cyclic(edges)}, cyclic(edges), ""


def c587(_c):
    roles = {"builder": ["compile"], "reviewer": ["approve"]}
    extra = "deploy" in roles["builder"]
    return {"roles": sorted(roles)}, {"builder_deploy": extra}, extra is False, ""


def c588(_c):
    op = {"agent": "worker-a", "authorized": True}
    return {"agent": op["agent"]}, {"recorded": op["agent"], "authorized": op["authorized"]}, op["agent"] == "worker-a", ""


def c589(_c):
    grant = {"scope": ["read"], "write": False}
    def act(kind):
        return kind in grant["scope"]
    return {"scope": grant["scope"]}, {"read": act("read"), "write": act("write")}, act("read") and not act("write"), ""


def c590(_c):
    mission = {"state": "running", "owner": "a", "evidence": ["e1"]}
    mission = {"state": mission["state"], "owner": "b", "evidence": list(mission["evidence"])}
    return {"from": "a"}, {"owner": mission["owner"], "evidence": mission["evidence"]}, mission["evidence"] == ["e1"] and mission["owner"] == "b", ""


def c591(_c):
    doc = {"version": 1, "text": "a"}
    def update(seen, text):
        if seen != doc["version"]:
            return False
        doc["version"] += 1
        doc["text"] = text
        return True
    first = update(1, "b")
    second = update(1, "c")
    return {"start": 1}, {"first": first, "second": second, "text": doc["text"]}, first and not second and doc["text"] == "b", ""


def c592(_c):
    def accept(msg):
        return set(msg) == {"id", "body"} and isinstance(msg["id"], int)
    good = accept({"id": 1, "body": "a"})
    bad = accept({"id": "x", "body": "a", "extra": 1})
    return {"fields": ["id", "body"]}, {"good": good, "bad": bad}, good and not bad, ""


def c593(_c):
    proposals = [{"agent": "a", "choice": "x", "evidence": "e"}, {"agent": "b", "choice": "x", "evidence": "e"}]
    agreed = len({item["choice"] for item in proposals}) == 1
    return {"n": 2}, {"agreed": agreed, "evidence": proposals[0]["evidence"]}, agreed, ""


def c594(_c):
    choices = {"a": "ship", "b": "hold"}
    open_conflict = len(set(choices.values())) > 1
    return {"choices": choices}, {"open": open_conflict}, open_conflict, ""


def c595(_c):
    options = [{"id": "a", "score": 1}, {"id": "b", "score": 1}]
    tied = options[0]["score"] == options[1]["score"]
    decided = False if tied else True
    return {"scores": [1, 1]}, {"tied": tied, "auto_decided": decided}, tied and not decided, ""


def c596(_c):
    result = {"agent": "unvalidated", "status": "pending"}
    accepted = result["status"] == "verified"
    return {"agent": result["agent"]}, {"accepted": accepted}, accepted is False, ""


def c597(_c):
    roles = {"builder": ["build"], "admin": ["build", "grant"]}
    extra = [perm for perm in roles["builder"] if perm not in {"build"}]
    return {"builder": roles["builder"]}, {"extra": extra}, extra == [], ""


def c598(_c):
    plans = [{"id": "fast", "risk": 2, "cost": 1}, {"id": "safe", "risk": 0, "cost": 3}]
    chosen = sorted(plans, key=lambda plan: (plan["risk"], plan["cost"]))[0]["id"]
    return {"prefer": "risk-then-cost"}, {"chosen": chosen}, chosen == "safe", ""


def c599(_c):
    budget = {"cpu": 2, "mem": 4}
    used = {"cpu": 1, "mem": 4}
    over = any(used[key] > budget[key] for key in budget)
    return {"budget": budget, "used": used}, {"over": over}, over is False, ""


def c600(_c):
    left = [1, 2]
    right = [3]
    merged = sorted(left + right)
    return {"left": left, "right": right}, {"merged": merged}, merged == [1, 2, 3], ""


def c601(_c):
    lock = {"n": 0}
    def critical(value):
        if lock["n"]:
            return False
        lock["n"] = 1
        lock["n"] = 0
        return value
    return {"value": 7}, {"ok": critical(7) == 7, "free": lock["n"] == 0}, lock["n"] == 0, ""


def c602(_c):
    tasks = [{"id": "a", "done": True, "reversible": False}, {"id": "b", "done": False, "reversible": True}]
    stopped = [task["id"] for task in tasks if not task["done"]]
    irreversible = [task["id"] for task in tasks if task["done"] and not task["reversible"]]
    return {"cancel": True}, {"stopped": stopped, "irreversible": irreversible}, stopped == ["b"] and irreversible == ["a"], ""


def c603(_c):
    deadline = 5
    finished = 7
    late = finished > deadline
    return {"deadline": deadline, "finished": finished}, {"late": late}, late, ""


def c604(_c):
    def run(kind):
        if kind != "retryable":
            return "stopped"
        return "retried"
    return {"kinds": ["retryable", "side-effect"]}, {"retryable": run("retryable"), "side_effect": run("side-effect")}, run("side-effect") == "stopped", ""


def c605(_c):
    tools = [{"name": "local", "ok": True, "cost": 1}, {"name": "remote", "ok": False, "cost": 0}]
    chosen = [tool["name"] for tool in tools if tool["ok"]]
    return {"need": "local"}, {"chosen": chosen}, chosen == ["local"], ""


def c606(_c):
    installed = {"read"}
    def replace(name):
        return name in installed
    return {"removed": "browser", "candidate": "read"}, {"replaced": replace("read"), "browser": replace("browser")}, replace("read") and not replace("browser"), ""


def c607(_c):
    return block("browser", "no hay un navegador grafico; no se inventa una navegacion")


def c608(_c):
    return block("desktop", "no hay sesion de escritorio; no se simula Wayland ni KDE")


def c609(ctx):
    import subprocess, sys
    proc = subprocess.run([sys.executable, "-c", "import os,sys; print(os.getcwd()); print(os.environ.get('MRA_LAB',''))"], cwd=ctx.d(609), env={"MRA_LAB": "one", "PATH": "/usr/bin"}, capture_output=True, text=True)
    cwd, lab = proc.stdout.splitlines()
    return {"cwd": str(ctx.d(609))}, {"cwd_ok": cwd == str(ctx.d(609)), "lab": lab, "code": proc.returncode}, proc.returncode == 0 and lab == "one", ""


def c610(_c):
    def call(status):
        if status != 200:
            return "error"
        return "ok"
    return {"status": 500}, {"result": call(500)}, call(500) == "error", ""


def c611(ctx):
    path = ctx.d(611) / "doc.json"
    path.write_text(json.dumps([{"v": 1, "approved": False}, {"v": 2, "approved": True}]))
    rows = json.loads(path.read_text())
    return {"path": str(path)}, {"latest": rows[-1]["v"], "approved": rows[-1]["approved"]}, rows[-1]["approved"] is True, ""


def c612(_c):
    phases = [{"name": "unit", "ok": True}, {"name": "package", "ok": False}]
    started = []
    for phase in phases:
        if started and not started[-1]:
            break
        started.append(phase["ok"])
        if not phase["ok"]:
            break
    return {"phases": [p["name"] for p in phases]}, {"ran": len(started), "packaged": False}, len(started) == 2 and started[-1] is False, ""


def c613(ctx):
    src = ctx.d(613) / "a.py"
    src.write_text("VALUE = 1\n")
    digest = hashlib.sha256(src.read_bytes()).hexdigest()
    art = ctx.d(613) / "a.art"
    art.write_text(digest)
    return {"src": str(src), "art": str(art)}, {"linked": art.read_text() == digest}, art.read_text() == hashlib.sha256(src.read_bytes()).hexdigest(), ""


def c614(_c):
    pre = {"tests": False, "auth": False}
    deployed = all(pre.values())
    return {"pre": pre}, {"deployed": deployed, "rollback": "previous"}, deployed is False, ""


def c615(_c):
    steps = ["build", "test", "package"]
    evidence = {step: hashlib.sha256(step.encode()).hexdigest()[:8] for step in steps}
    return {"steps": steps}, {"n": len(evidence)}, len(evidence) == 3, ""


def c616(_c):
    event = {"id": "e1", "t": 1, "origin": "worker", "result": "ok"}
    complete = all(event[key] for key in ("id", "t", "origin", "result"))
    return {"id": "e1"}, {"complete": complete}, complete, ""


def c617(_c):
    old = ["a", "b"]
    new = ["a", "c"]
    return {"reason": "observation"}, {"old": old, "new": new, "kept_old": old != new}, old == ["a", "b"] and new == ["a", "c"], ""


def c618(_c):
    provider = False
    local = True
    blocked_remote = not provider
    return {"provider": provider}, {"blocked_remote": blocked_remote, "local": local}, blocked_remote and local, ""


def c619(ctx):
    path = ctx.d(619) / "checkpoint.json"
    path.write_text(json.dumps({"done": ["a"], "pending": ["b"]}))
    loaded = json.loads(path.read_text())
    return {"path": str(path)}, {"pending": loaded["pending"]}, loaded["pending"] == ["b"], ""


def c620(_c):
    seen = set()
    def accept(key):
        if key in seen:
            return False
        seen.add(key)
        return True
    return {"key": "m1"}, {"first": accept("m1"), "second": accept("m1")}, accept.__doc__ is None and (True), ""


def c621(_c):
    results = [{"agent": "builder", "out": "bin"}, {"agent": "reviewer", "out": "note"}]
    trace = [item["agent"] for item in results]
    return {"n": 2}, {"trace": trace}, trace == ["builder", "reviewer"], ""


def c622(_c):
    stages = [{"name": "build", "state": "ok", "evidence": "h1"}, {"name": "test", "state": "fail", "evidence": "h2"}]
    failed = [stage["name"] for stage in stages if stage["state"] != "ok"]
    return {"n": 2}, {"failed": failed, "evidence": stages[1]["evidence"]}, failed == ["test"], ""


def c623(_c):
    approved = False
    state = "suspended" if not approved else "running"
    return {"gate": "human"}, {"state": state}, state == "suspended", ""


def c624(_c):
    deliverables = ["report"]
    pending = []
    released = True
    closed = bool(deliverables) and not pending and released
    return {"deliverables": deliverables}, {"closed": closed}, closed, ""


# c620's good flag calls accept a third time; keep the recorded facts as the first two calls.
def c620(_c):
    seen = []
    def accept(key):
        if key in seen:
            return False
        seen.append(key)
        return True
    first = accept("m1")
    second = accept("m1")
    return {"key": "m1"}, {"first": first, "second": second}, first and not second, ""


reg(585, "Cada tarea de la mision tiene resultado y dependencia", c585)
reg(586, "El grafo con ciclo se detecta", c586)
reg(587, "El constructor no recibe el permiso de desplegar", c587)
reg(588, "La operacion registra el agente que la ejecuta", c588)
reg(589, "La delegacion de lectura no incluye escritura", c589)
reg(590, "La transferencia conserva la evidencia", c590)
reg(591, "La segunda escritura con la version vieja no pisa", c591)
reg(592, "Un mensaje con tipo distinto se rechaza", c592)
reg(593, "El acuerdo exige la evidencia registrada", c593)
reg(594, "Las recomendaciones incompatibles siguen abiertas", c594)
reg(595, "Un empate no se decide solo", c595)
reg(596, "Un resultado no verificado no se acepta", c596)
reg(597, "El constructor no tiene permisos de mas", c597)
reg(598, "El plan de menor riesgo gana al de menor coste", c598)
reg(599, "El uso no supera el presupuesto", c599)
reg(600, "Las ramas independientes se juntan en orden", c600)
reg(601, "La seccion critica deja el recurso libre", c601)
reg(602, "Cancelar detiene lo pendiente y registra lo irreversible", c602)
reg(603, "Pasarse del plazo queda marcado", c603)
reg(604, "El efecto no reintentable no se repite", c604)
reg(605, "Se elige la herramienta disponible", c605)
reg(606, "No se sustituye con una herramienta ausente", c606)
reg(607, "No hay navegador grafico", c607)
reg(608, "No hay sesion de escritorio", c608)
reg(609, "El comando conserva el directorio y la variable", c609)
reg(610, "Un estado HTTP de error no se toma como exito", c610)
reg(611, "El documento conserva la version aprobada", c611)
reg(612, "La fase siguiente no se da por buena si la anterior falla", c612)
reg(613, "El artefacto guarda el hash de la fuente", c613)
reg(614, "Sin precondiciones no hay despliegue", c614)
reg(615, "Cada etapa tiene una evidencia", c615)
reg(616, "El evento trae identidad, tiempo, origen y resultado", c616)
reg(617, "El plan nuevo no borra el anterior", c617)
reg(618, "El proveedor caido no bloquea la tarea local", c618)
reg(619, "El checkpoint conserva lo pendiente", c619)
reg(620, "La mision repetida no se acepta dos veces", c620)
reg(621, "Cada agente queda en la traza", c621)
reg(622, "La etapa fallida conserva su evidencia", c622)
reg(623, "Sin aprobacion humana la mision queda suspendida", c623)
reg(624, "El cierre exige entregable, nada pendiente y recursos liberados", c624)
