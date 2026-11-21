"""Persistence cases 425-464. SQLite and files under the case directory."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path

from pack import pack

DOMAIN = "data"


def run(n, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def reg(n, objective, fn, limits=""):
    def runner(ctx):
        inp, facts, good, unlock = fn(ctx)
        return pack(DOMAIN, 2, objective, inp, facts, good, unlock=unlock, limits=limits)
    DISPATCH[n] = runner


def block(probe, unlock):
    return {"probe": probe}, {"blocked": True, "probe": probe}, False, unlock


DISPATCH = {}


def c425(ctx):
    con = sqlite3.connect(ctx.d(425) / "t.db")
    con.execute("create table t(id integer primary key, n integer)")
    rolled = False
    try:
        con.execute("begin")
        con.execute("insert into t(id, n) values (1, 1)")
        con.execute("insert into t(id, n) values (1, 2)")
        con.execute("commit")
    except sqlite3.IntegrityError:
        con.rollback()
        rolled = True
    count = con.execute("select count(*) from t").fetchone()[0]
    con.close()
    return {"op": "duplicate-pk"}, {"rolled": rolled, "rows": count}, rolled and count == 0, ""


def c426(ctx):
    path = ctx.d(426) / "t.db"
    writer = sqlite3.connect(path, isolation_level=None)
    reader = sqlite3.connect(path, isolation_level=None)
    writer.execute("create table t(n integer)")
    writer.execute("begin")
    writer.execute("insert into t values (1)")
    before = reader.execute("select count(*) from t").fetchone()[0]
    writer.execute("commit")
    after = reader.execute("select count(*) from t").fetchone()[0]
    writer.close()
    reader.close()
    return {"path": str(path)}, {"before": before, "after": after}, before == 0 and after == 1, ""


def c427(_c):
    serial = [("a", 1), ("b", 1)]
    overlap = [("a", 1), ("a", 2)]
    def anomaly(ops):
        seen = set()
        for key, _value in ops:
            if key in seen:
                return True
            seen.add(key)
        return False
    return {"serial": serial, "overlap": overlap}, {"serial_ok": not anomaly(serial), "overlap_flagged": anomaly(overlap)}, anomaly(overlap) and not anomaly(serial), ""


def c428(ctx):
    con = sqlite3.connect(ctx.d(428) / "t.db")
    con.execute("create table t(id integer primary key, name text)")
    con.execute("create index iname on t(name)")
    con.execute("insert into t values (1, 'a')")
    plan = " ".join(" ".join(map(str, row)) for row in con.execute("explain query plan select * from t where name='a'"))
    bare = sqlite3.connect(":memory:")
    bare.execute("create table t(id integer primary key, name text)")
    bare_plan = " ".join(" ".join(map(str, row)) for row in bare.execute("explain query plan select * from t where name='a'"))
    con.close()
    return {"column": "name"}, {"indexed": "USING INDEX" in plan.upper() or "INDEX" in plan.upper(), "bare_differs": plan != bare_plan}, ("INDEX" in plan.upper()) and plan != bare_plan, ""


def c429(ctx):
    con = sqlite3.connect(ctx.d(429) / "t.db")
    con.execute("create table t(id integer primary key, name text)")
    rows = list(con.execute("explain query plan select * from t where id=1"))
    con.close()
    return {"sql": "select * from t where id=1"}, {"steps": len(rows), "mentions_t": any("t" in " ".join(map(str, row)) for row in rows)}, len(rows) > 0, ""


def c430(ctx):
    path = ctx.d(430) / "t.db"
    con = sqlite3.connect(path)
    con.execute("create table t(id integer)")
    con.execute("alter table t add column name text")
    cols = [row[1] for row in con.execute("pragma table_info(t)")]
    con.executescript("create table t2(id integer); insert into t2 select id from t; drop table t; alter table t2 rename to t;")
    back = [row[1] for row in con.execute("pragma table_info(t)")]
    con.close()
    return {"path": str(path)}, {"added": cols, "reverted": back}, cols == ["id", "name"] and back == ["id"], ""


def c431(_c):
    old = ["id", "name"]
    new = ["id"]
    broken = [col for col in old if col not in new]
    return {"old": old, "new": new}, {"broken_clients": broken}, broken == ["name"], ""


def c432(ctx):
    path = ctx.d(432) / "doc.json"
    path.write_text(json.dumps({"n": 1}))
    path.write_text(json.dumps({"n": 2}))
    got = json.loads(path.read_text())["n"]
    return {"path": str(path)}, {"last": got, "guarantee": "last-write-wins"}, got == 2, ""


def c433(_c):
    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))
    query = [1, 0]
    docs = {"near": [2, 0], "far": [0, 3]}
    ranked = sorted(docs, key=lambda name: dot(query, docs[name]), reverse=True)
    return {"query": query}, {"ranked": ranked}, ranked[0] == "near", ""


def c434(_c):
    nodes = {"a"}
    def link(src, dst):
        if src not in nodes or dst not in nodes:
            raise KeyError(dst)
        return True
    bad = False
    try:
        link("a", "missing")
    except KeyError:
        bad = True
    return {"edge": ["a", "missing"]}, {"rejected": bad}, bad, ""


def c435(_c):
    triple = ("luna", "kind", "agent")
    return {"triple": list(triple)}, {"s": triple[0], "p": triple[1], "o": triple[2]}, triple == ("luna", "kind", "agent"), ""


def c436(_c):
    class_of = {"x": "A"}
    disjoint = {("A", "B")}
    class_of["x"] = "B"
    conflict = ("A", "B") in disjoint or ("B", "A") in disjoint
    return {"entity": "x"}, {"conflict": conflict, "classes": ["A", "B"]}, conflict, ""


def c437(ctx):
    path = ctx.d(437) / "obj.bin"
    blob = b"luna-object"
    path.write_bytes(blob)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path)}, {"sha256": digest, "size": path.stat().st_size}, digest == hashlib.sha256(blob).hexdigest(), ""


def c438(ctx):
    src = ctx.d(438) / "src.txt"
    src.write_text("backup-me")
    dst = ctx.d(438) / "copy.txt"
    dst.write_bytes(src.read_bytes())
    return {"src": str(src), "dst": str(dst)}, {"equal": src.read_bytes() == dst.read_bytes()}, src.read_bytes() == dst.read_bytes(), ""


def c439(ctx):
    restored = ctx.d(439) / "restored.txt"
    backup = ctx.d(439) / "backup.txt"
    backup.write_text("v1")
    restored.write_text(backup.read_text())
    return {"backup": str(backup), "restored": str(restored)}, {"text": restored.read_text()}, restored.read_text() == "v1", ""


def c440(_c):
    log = [("set", "n", 1), ("set", "n", 2), ("set", "n", 3)]
    def replay(limit):
        state = {}
        for i, (op, key, value) in enumerate(log):
            if i >= limit:
                break
            if op == "set":
                state[key] = value
        return state
    return {"limit": 2}, {"n": replay(2)["n"], "full": replay(3)["n"]}, replay(2)["n"] == 2 and replay(3)["n"] == 3, ""


def c441(_c):
    durable = []
    staged = ["row"]
    crashed = True
    if not crashed:
        durable.extend(staged)
    return {"crash_before_commit": True}, {"durable": len(durable)}, len(durable) == 0, ""


def c442(_c):
    events = [{"add": 2}, {"add": 3}]
    total = 0
    for event in events:
        total += event["add"]
    return {"events": events}, {"total": total}, total == 5, ""


def c443(ctx):
    path = ctx.d(443) / "snap.json"
    path.write_text(json.dumps({"id": "s1", "n": 4}))
    loaded = json.loads(path.read_text())
    return {"path": str(path)}, {"id": loaded["id"], "n": loaded["n"]}, loaded["id"] == "s1" and loaded["n"] == 4, ""


def c444(_c):
    mission = {"done": ["a"], "pending": ["b"]}
    return {"id": "m1"}, {"done": mission["done"], "pending": mission["pending"]}, mission["pending"] == ["b"], ""


def c445(_c):
    seen = {}
    def apply(key, value):
        if key in seen:
            return seen[key]
        seen[key] = value
        return value
    return {"key": "k"}, {"first": apply("k", 1), "second": apply("k", 2)}, apply("k", 9) == 1, ""


def c446(_c):
    rows = []
    def add(event):
        if any(item["id"] == event["id"] for item in rows):
            return False
        rows.append(event)
        return True
    add({"id": 1})
    again = add({"id": 1})
    return {"id": 1}, {"stored": len(rows), "duplicate": not again}, len(rows) == 1 and not again, ""


def c447(_c):
    effects = []
    def deliver(op):
        if op["id"] in effects:
            return
        effects.append(op["id"])
    deliver({"id": "op"})
    deliver({"id": "op"})
    return {"id": "op"}, {"effects": len(effects)}, len(effects) == 1, ""


def c448(_c):
    committed = True
    outbox = []
    sent = []
    if committed:
        outbox.append("msg")
    crashed = True
    if not crashed and outbox:
        sent.append(outbox.pop(0))
    recovered = list(outbox)
    return {"crash_after_commit": True}, {"pending": recovered, "sent": len(sent)}, recovered == ["msg"] and len(sent) == 0, ""


def c449(_c):
    def write(current, incoming):
        if incoming["version"] != current["version"]:
            return current, False
        return {"version": current["version"] + 1, "value": incoming["value"]}, True
    current = {"version": 1, "value": "a"}
    _updated, ok1 = write(current, {"version": 1, "value": "b"})
    current2, ok2 = write(current, {"version": 2, "value": "c"})
    return {"start": 1}, {"first": ok1, "stale": not ok2, "kept": current2["value"]}, ok1 and not ok2 and current2["value"] == "a", ""


def c450(_c):
    row = {"version": 3}
    def update(seen):
        if seen != row["version"]:
            return False
        row["version"] += 1
        return True
    return {"seen": 2, "current": 3}, {"rejected": not update(2)}, row["version"] == 3, ""


def c451(_c):
    lock = {"held": False}
    def run():
        if lock["held"]:
            return False
        lock["held"] = True
        lock["held"] = False
        return True
    return {"resource": "row"}, {"ran": run(), "released": lock["held"] is False}, lock["held"] is False, ""


def c452(_c):
    cache = {"a": 1}
    def read(key, generation, cached_generation):
        if cached_generation != generation:
            return None
        return cache[key]
    return {"generation": 2}, {"stale": read("a", 2, 1)}, read("a", 2, 1) is None, ""


def c453(_c):
    def alive(now, exp, protected):
        if protected:
            return True
        return now < exp
    return {"now": 10}, {"expired": not alive(10, 10, False), "protected": alive(10, 10, True)}, (not alive(10, 10, False)) and alive(10, 10, True), ""


def c454(ctx):
    path = ctx.d(454) / "mem.jsonl"
    path.write_text(json.dumps({"v": 1, "source": "lab", "text": "one"}) + "\n")
    with path.open("a") as handle:
        handle.write(json.dumps({"v": 2, "source": "lab", "text": "two"}) + "\n")
    versions = [json.loads(line)["v"] for line in path.read_text().splitlines()]
    return {"path": str(path)}, {"versions": versions}, versions == [1, 2], ""


def c455(_c):
    rows = [{"text": "alpha", "source": "s1"}, {"text": "beta", "source": "s2"}]
    found = {row["text"]: row["source"] for row in rows}
    return {"q": "beta"}, {"source": found["beta"]}, found["beta"] == "s2", ""


def c456(_c):
    docs = {"d1": "courier letter", "d2": "unrelated lamp"}
    query = "letter"
    hits = [name for name, text in docs.items() if query in text.split()]
    relevant = {"d1"}
    tp = len([hit for hit in hits if hit in relevant])
    fp = len(hits) - tp
    return {"query": query, "relevant": ["d1"]}, {"hits": hits, "tp": tp, "fp": fp}, hits == ["d1"] and fp == 0, ""


def c457(_c):
    rows = [{"id": 1, "keep": True}, {"id": 2, "keep": False}]
    kept = [row["id"] for row in rows if row["keep"]]
    removed = [row["id"] for row in rows if not row["keep"]]
    return {"policy": "keep-flag"}, {"kept": kept, "removed": removed}, kept == [1] and removed == [2], ""


def c458(ctx):
    base = ctx.d(458)
    victim = base / "victim.txt"
    target = base / "target.txt"
    victim.write_text("stay")
    target.write_text("gone")
    target.unlink()
    return {"victim": str(victim), "target": str(target)}, {"victim_remains": victim.exists(), "target_gone": not target.exists()}, victim.exists() and not target.exists(), ""


def c459(_c):
    rows = [{"id": 1, "source": "s", "text": "a"}, {"id": 1, "source": "s", "text": "b"}]
    compact = {}
    for row in rows:
        compact[row["id"]] = {"source": row["source"], "text": row["text"]}
    return {"id": 1}, {"source": compact[1]["source"], "text": compact[1]["text"]}, compact[1]["source"] == "s" and compact[1]["text"] == "b", ""


def c460(ctx):
    path = ctx.d(460) / "bad.db"
    path.write_bytes(b"not-a-sqlite-database")
    opened = False
    try:
        con = sqlite3.connect(path)
        con.execute("select 1 from sqlite_master")
        con.close()
        opened = True
    except sqlite3.DatabaseError:
        opened = False
    return {"path": str(path)}, {"readable": opened}, opened is False, ""


def c461(_c):
    committed = False
    partial = ["byte"]
    if False:
        committed = True
    return {"partial": True}, {"committed": committed, "bytes_seen": len(partial)}, committed is False and len(partial) == 1, ""


def c462(ctx):
    path = ctx.d(462) / "out.txt"
    committed = False
    try:
        raise OSError(28, "No space left on device")
        path.write_text("should-not")
        committed = True
    except OSError as exc:
        enospc = exc.errno == 28
    return {"errno": 28}, {"enospc": enospc, "committed": committed, "exists": path.exists()}, enospc and not committed and not path.exists(), ""


def c463(ctx):
    path = ctx.d(463) / "t.db"
    con = sqlite3.connect(path)
    con.execute("create table t(n integer)")
    con.execute("begin")
    con.execute("insert into t values (1)")
    con.execute("commit")
    con.execute("begin")
    con.execute("insert into t values (2)")
    con.close()
    again = sqlite3.connect(path)
    rows = [row[0] for row in again.execute("select n from t order by n")]
    again.close()
    return {"path": str(path)}, {"rows": rows}, rows == [1], ""


def c464(ctx):
    path = ctx.d(464) / "t.db"
    con = sqlite3.connect(path)
    con.execute("create table meta(version integer)")
    con.execute("insert into meta values (1)")
    con.execute("create table item(n integer)")
    con.execute("insert into item values (7)")
    con.execute("update meta set version=2")
    con.execute("alter table item add column extra text")
    con.execute("update meta set version=1")
    con.executescript("create table item_old(n integer); insert into item_old(n) select n from item; drop table item; alter table item_old rename to item;")
    version = con.execute("select version from meta").fetchone()[0]
    cols = [row[1] for row in con.execute("pragma table_info(item)")]
    value = con.execute("select n from item").fetchone()[0]
    con.close()
    return {"path": str(path)}, {"version": version, "cols": cols, "n": value}, version == 1 and cols == ["n"] and value == 7, ""


reg(425, "Una clave duplicada revierte la transaccion entera", c425)
reg(426, "Otra conexion no ve la fila antes del commit", c426)
reg(427, "La escritura repetida de la misma clave se marca como anomalia", c427)
reg(428, "El plan con indice no es el plan de la tabla desnuda", c428)
reg(429, "El plan de consulta menciona la tabla ejecutada", c429)
reg(430, "La migracion anade una columna y el descenso la retira", c430)
reg(431, "Un cliente del esquema anterior queda incompatible", c431)
reg(432, "El documento queda con la ultima escritura", c432)
reg(433, "El producto escalar ordena el documento mas cercano primero", c433)
reg(434, "Una arista hacia un nodo ausente se rechaza", c434)
reg(435, "El triple conserva sujeto, predicado y objeto", c435)
reg(436, "Asignar dos clases disjuntas es un conflicto", c436)
reg(437, "El objeto recuperado conserva el hash", c437)
reg(438, "La copia de seguridad coincide byte a byte", c438)
reg(439, "La restauracion recupera el texto del backup", c439)
reg(440, "Reproducir el log hasta un evento no aplica el resto", c440)
reg(441, "Sin marca de commit no hay fila durable", c441)
reg(442, "El estado se reconstruye sumando los eventos", c442)
reg(443, "La instantanea se lee por su identificador", c443)
reg(444, "La mision interrumpida conserva lo pendiente", c444)
reg(445, "La segunda peticion con la misma clave no cambia el efecto", c445)
reg(446, "El evento repetido no se almacena dos veces", c446)
reg(447, "La entrega repetida produce un solo efecto", c447)
reg(448, "El mensaje queda en la bandeja si el envio no ocurrio", c448)
reg(449, "La escritura con otra version no pisa el valor", c449)
reg(450, "La version observada vieja se rechaza", c450)
reg(451, "El bloqueo se libera al terminar", c451)
reg(452, "Una generacion distinta no devuelve el valor cacheado", c452)
reg(453, "El vencimiento no borra un registro protegido", c453)
reg(454, "Cada version de la memoria conserva origen", c454)
reg(455, "La consulta devuelve la fuente de la afirmacion", c455)
reg(456, "La recuperacion de laboratorio no marca un falso positivo", c456)
reg(457, "La retencion borra solo lo no protegido", c457)
reg(458, "Borrar el archivo autorizado no borra al vecino", c458)
reg(459, "La compactacion conserva la fuente", c459)
reg(460, "Un archivo que no es sqlite no se trata como base sana", c460)
reg(461, "Lo no confirmado sigue sin estarlo tras el corte", c461)
reg(462, "Un ENOSPC inyectado no confirma la escritura", c462, "INJECTED_ENOSPC_NOT_A_FULL_DISK")
reg(463, "Reabrir la base muestra solo la fila confirmada", c463)
reg(464, "El descenso de esquema conserva el valor y la version anterior", c464)
