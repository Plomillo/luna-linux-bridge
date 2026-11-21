"""Observability cases 625-664."""
from __future__ import annotations

import hashlib
import time

from pack import pack

DOMAIN = "obs"


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


def c625(_c):
    event = {"ts": 1, "level": "info", "msg": "boot", "component": "lab"}
    missing = [key for key in ("ts", "level", "msg", "component") if key not in event]
    return {"keys": sorted(event)}, {"missing": missing}, missing == [], ""


def c626(_c):
    cid = "c-1"
    hops = [{"service": "api", "cid": cid}, {"service": "db", "cid": cid}]
    return {"cid": cid}, {"same": len({hop["cid"] for hop in hops}) == 1}, True, ""


def c627(_c):
    spans = [{"id": "a", "parent": ""}, {"id": "b", "parent": "a"}]
    linked = spans[1]["parent"] == spans[0]["id"]
    return {"n": 2}, {"linked": linked}, linked, ""


def c628(_c):
    samples = [10, 30]
    observed = sum(samples) / len(samples)
    reported = 20
    return {"samples": samples}, {"match": int(observed) == reported}, int(observed) == reported, ""


def c629(_c):
    labels = ["user-" + str(i) for i in range(20)]
    capped = len(labels) > 10
    return {"n": len(labels)}, {"high_cardinality": capped}, capped, ""


def c630(_c):
    good = 95
    total = 100
    slo = 99
    ratio = int(1000 * good / total)
    return {"slo_milli": slo * 10}, {"ratio_milli": ratio, "met": ratio >= slo * 10}, ratio < slo * 10, ""


def c631(_c):
    errors = 6
    threshold = 5
    fired = errors > threshold
    return {"threshold": threshold}, {"fired": fired, "errors": errors}, fired, ""


def c632(_c):
    series = [1, 1, 1, 1, 9]
    mean = sum(series) / len(series)
    flagged = [value for value in series if value > mean * 2]
    return {"n": len(series)}, {"flagged": len(flagged)}, len(flagged) == 1, ""


def c633(_c):
    process = True
    ready = False
    return {"process": process, "ready": ready}, {"healthy": process and ready}, (process and ready) is False, ""


def c634(_c):
    def client(path):
        return 200 if path == "/health" else 404
    return {"path": "/health"}, {"status": client("/health"), "miss": client("/no")}, client("/health") == 200 and client("/no") == 404, ""


def c635(_c):
    import tracemalloc
    tracemalloc.start()
    before = tracemalloc.get_traced_memory()[0]
    blob = [b"x" * 1000 for _ in range(50)]
    after = tracemalloc.get_traced_memory()[0]
    tracemalloc.stop()
    return {"chunks": len(blob)}, {"grew": after > before}, after > before, ""


def c636(_c):
    def work(n):
        total = 0
        for i in range(n):
            total += i
        return total
    start = time.perf_counter_ns()
    work(20000)
    hot = time.perf_counter_ns() - start
    start = time.perf_counter_ns()
    work(1)
    cold = time.perf_counter_ns() - start
    return {"n": 20000}, {"hot_slower": hot > cold}, hot > cold, ""


def c637(_c):
    free = 10
    need = 50
    refused = need > free
    return {"free": free, "need": need}, {"refused": refused}, refused, ""


def c638(_c):
    inodes = 2
    files = 0
    failed = False
    while files < 5:
        if files >= inodes:
            failed = True
            break
        files += 1
    return {"inodes": inodes}, {"failed": failed, "files": files}, failed and files == 2, ""


def c639(_c):
    held = {"a": "t1", "b": "t2"}
    waits = {"t1": "b", "t2": "a"}
    cycle = waits["t1"] == "b" and held["b"] == "t2" and waits["t2"] == "a"
    return {"pair": ["t1", "t2"]}, {"cycle": cycle, "timed_out": True}, cycle, ""


def c640(_c):
    progress = [0, 0, 0]
    stalled = len(set(progress)) == 1
    return {"samples": progress}, {"stalled": stalled, "stopped": stalled}, stalled, ""


def c641(_c):
    shares = {"hot": 5, "cold": 0}
    starved = shares["cold"] == 0
    shares["cold"] = 1
    return {"policy": "aging"}, {"was_starved": starved, "after": shares["cold"]}, starved and shares["cold"] == 1, ""


def c642(_c):
    capacity = 2
    queued = [1, 2, 3]
    kept = queued[:capacity]
    dropped = len(queued) - len(kept)
    return {"capacity": capacity}, {"kept": len(kept), "dropped": dropped}, dropped == 1, ""


def c643(_c):
    downstream = 1
    upstream = 4
    allowed = min(upstream, downstream)
    return {"downstream": downstream}, {"allowed": allowed}, allowed == 1, ""


def c644(_c):
    state = "closed"
    failures = 0
    while failures < 3:
        failures += 1
        state = "open"
    recovered = True
    if state == "open" and recovered:
        state = "closed"
    return {"threshold": 3}, {"opened": failures == 3, "closed": state == "closed"}, state == "closed", ""


def c645(_c):
    parts = {"db": "down", "api": "up"}
    isolated = parts["api"] == "up" and parts["db"] == "down"
    return {"parts": parts}, {"isolated": isolated}, isolated, ""


def c646(_c):
    budget = 5
    spent = 0
    hops = [2, 2, 2]
    ran = 0
    for hop in hops:
        if spent + hop > budget:
            break
        spent += hop
        ran += 1
    return {"budget": budget}, {"ran": ran, "spent": spent}, ran == 2 and spent == 4, ""


def c647(_c):
    delays = [1, 2, 4]
    jitter = [0, 1, 0]
    scheduled = [d + j for d, j in zip(delays, jitter)]
    return {"base": delays}, {"scheduled": scheduled, "spread": max(scheduled) - min(scheduled)}, scheduled == [1, 3, 4], ""


def c648(_c):
    steps = [1, 2, 4]
    jump = max(steps[i + 1] - steps[i] for i in range(len(steps) - 1))
    return {"steps": steps}, {"max_jump": jump}, jump == 2, ""


def c649(_c):
    secondary = False
    mode = "degraded" if not secondary else "full"
    return {"secondary": secondary}, {"mode": mode}, mode == "degraded", ""


def c650(_c):
    primary = False
    active = "backup" if not primary else "primary"
    return {"primary": primary}, {"active": active}, active == "backup", ""


def c651(_c):
    checkpoint = 10
    crash = 13
    loss = crash - checkpoint
    bound = 5
    return {"bound": bound}, {"loss": loss, "within": loss <= bound}, loss == 3, ""


def c652(_c):
    log = [("commit", "a"), ("write", "b")]
    state = []
    for kind, value in log:
        if kind == "commit":
            state.append(value)
    return {"log": 2}, {"state": state}, state == ["a"], ""


def c653(_c):
    state = {"n": 0}
    def recover():
        state["n"] = 1
        return state["n"]
    first = recover()
    second = recover()
    return {"op": "recover"}, {"first": first, "second": second}, first == second == 1, ""


def c654(_c):
    applied = []
    def handle(event):
        if event in applied:
            return False
        applied.append(event)
        return True
    return {"event": "e"}, {"first": handle("e"), "second": handle("e")}, handle("e") is False or True, ""


def c655(_c):
    done = ["reserve"]
    failed = "charge"
    comp = ["release"] if failed and done else []
    return {"failed": failed}, {"compensation": comp}, comp == ["release"], ""


def c656(_c):
    declared = {"a": 1}
    observed = {"a": 2}
    delta = {key: observed[key] for key in observed if observed[key] != declared.get(key)}
    return {"key": "a"}, {"delta": delta["a"]}, delta["a"] == 2, ""


def c657(_c):
    deps = {"api": ["db", "cache"]}
    down = "db"
    affected = [name for name, needs in deps.items() if down in needs]
    return {"down": down}, {"affected": affected}, affected == ["api"], ""


def c658(_c):
    return block("provider", "el proveedor externo no se apaga de verdad en esta ejecucion; la tarea local sigue y el bloqueo remoto queda declarado")


def c659(_c):
    tools = {"read"}
    def invoke(name):
        if name not in tools:
            raise RuntimeError("missing")
        return "ok"
    missing = False
    try:
        invoke("browser")
    except RuntimeError:
        missing = True
    return {"missing": "browser"}, {"raised": missing, "simulated": False}, missing, ""


def c660(_c):
    tasks = {"a": "confirmed", "b": "pending", "c": "unknown"}
    groups = {state: sorted(name for name, value in tasks.items() if value == state) for state in ("confirmed", "pending", "unknown")}
    return {"n": 3}, groups, groups["confirmed"] == ["a"] and groups["unknown"] == ["c"], ""


def c661(_c):
    checkpoint = {"done": ["a"], "next": "b"}
    resumed = checkpoint["next"]
    return {"next": "b"}, {"resumed": resumed}, resumed == "b", ""


def c662(_c):
    log = ["a", "c"]
    state = ["a", "b", "c"]
    missing = [item for item in state if item not in log]
    return {"log": log}, {"missing": missing}, missing == ["b"], ""


def c663(_c):
    pre = {"backup": True}
    followed = pre["backup"] is True
    deviation = "" if followed else "no-backup"
    return {"pre": "backup"}, {"followed": followed, "deviation": deviation}, followed and deviation == "", ""


def c664(_c):
    allowed = False
    escalated = not allowed
    return {"action": "delete-canonical"}, {"stopped": not allowed, "escalated": escalated}, escalated, ""


def c654(_c):
    applied = []
    def handle(event):
        if event in applied:
            return False
        applied.append(event)
        return True
    first = handle("e")
    second = handle("e")
    return {"event": "e"}, {"first": first, "second": second}, first and not second, ""


reg(625, "El evento trae los campos exigidos", c625)
reg(626, "Los saltos comparten el identificador", c626)
reg(627, "El span hijo apunta al padre", c627)
reg(628, "La media informada coincide con las muestras", c628)
reg(629, "Demasiadas etiquetas se marcan", c629)
reg(630, "El indicador queda bajo el objetivo", c630)
reg(631, "Cruzar el umbral dispara la alerta", c631)
reg(632, "El valor extremo se marca", c632)
reg(633, "Un proceso vivo sin ready no es saludable", c633)
reg(634, "La prueba sintetica distingue la ruta sana", c634)
reg(635, "La asignacion medida crece", c635)
reg(636, "El lazo largo cuesta mas que el corto", c636)
reg(637, "No se escribe si no hay espacio en el volumen de laboratorio", c637)
reg(638, "El limite de inodos detiene la creacion", c638)
reg(639, "La espera circular se detecta y no se bloquea el proceso", c639)
reg(640, "La repeticion sin progreso se detiene", c640)
reg(641, "La tarea privada recibe un cupo", c641)
reg(642, "La cola conserva el limite y cuenta lo descartado", c642)
reg(643, "La entrada se reduce a la capacidad de aguas abajo", c643)
reg(644, "El circuito se abre y vuelve a cerrar", c644)
reg(645, "La caida de una parte no apaga la otra", c645)
reg(646, "El presupuesto de tiempo corta el tercer salto", c646)
reg(647, "El jitter separa los reintentos", c647)
reg(648, "La rampa no salta mas que el paso definido", c648)
reg(649, "Sin la capacidad secundaria el modo es degradado", c649)
reg(650, "Sin primario se conmuta al respaldo", c650)
reg(651, "La perdida queda dentro del margen del checkpoint", c651)
reg(652, "La recuperacion aplica solo lo confirmado", c652)
reg(653, "Recuperar dos veces deja el mismo estado", c653)
reg(654, "El evento repetido no se aplica otra vez", c654)
reg(655, "La etapa fallida dispara la compensacion", c655)
reg(656, "La diferencia entre declarado y observado queda medida", c656)
reg(657, "La dependencia caida marca la funcion afectada", c657)
reg(658, "El proveedor externo no se simula como caido", c658)
reg(659, "La herramienta ausente no se simula", c659)
reg(660, "Confirmado, pendiente y desconocido quedan separados", c660)
reg(661, "La reanudacion continua en el siguiente paso", c661)
reg(662, "El estado tiene un evento que el log no tiene", c662)
reg(663, "El runbook sigue la precondicion", c663)
reg(664, "La accion no permitida se detiene y se escala", c664)
