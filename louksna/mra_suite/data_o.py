"""Oracle for persistence cases 425-464. Own SQLite files; does not import the worker."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def e425(_inp):
    con = sqlite3.connect(":memory:")
    con.execute("create table t(id integer primary key, n integer)")
    rolled = False
    try:
        with con:
            con.execute("insert into t(id, n) values (1, 1)")
            con.execute("insert into t(id, n) values (1, 2)")
    except sqlite3.IntegrityError:
        rolled = True
    count = con.execute("select count(*) from t").fetchone()[0]
    return {"rolled": rolled, "rows": count}


def e426(_inp):
    path = Path("/tmp/mra-oracle-426.db")
    if path.exists():
        path.unlink()
    writer = sqlite3.connect(path, isolation_level=None)
    reader = sqlite3.connect(path, isolation_level=None)
    writer.execute("create table t(n integer)")
    writer.execute("begin")
    writer.execute("insert into t values (1)")
    before = reader.execute("select count(*) from t").fetchone()[0]
    writer.commit()
    after = reader.execute("select count(*) from t").fetchone()[0]
    writer.close()
    reader.close()
    return {"before": before, "after": after}


def e427(inp):
    def flag(ops):
        keys = []
        for key, _value in ops:
            if key in keys:
                return True
            keys.append(key)
        return False
    return {"serial_ok": not flag(inp["serial"]), "overlap_flagged": flag(inp["overlap"])}


def e428(_inp):
    con = sqlite3.connect(":memory:")
    con.execute("create table t(id integer primary key, name text)")
    con.execute("create index iname on t(name)")
    plan = " ".join(str(cell) for row in con.execute("explain query plan select id, name from t where name='a'") for cell in row)
    bare = sqlite3.connect(":memory:")
    bare.execute("create table t(id integer primary key, name text)")
    bare_plan = " ".join(str(cell) for row in bare.execute("explain query plan select id, name from t where name='a'") for cell in row)
    return {"indexed": "INDEX" in plan.upper(), "bare_differs": plan != bare_plan}


def e429(inp):
    con = sqlite3.connect(":memory:")
    con.execute("create table t(id integer primary key, name text)")
    rows = list(con.execute("explain query plan " + "select * from t where id=1"))
    return {"steps": len(rows), "mentions_t": any("t" in str(row) for row in rows)}


def e430(_inp):
    con = sqlite3.connect(":memory:")
    con.execute("create table t(id integer)")
    con.execute("alter table t add column name text")
    cols = [row[1] for row in con.execute("pragma table_info(t)")]
    con.executescript("create table t2(id integer); insert into t2 select id from t; drop table t; alter table t2 rename to t;")
    back = [row[1] for row in con.execute("pragma table_info(t)")]
    return {"added": cols, "reverted": back}


def e431(inp):
    broken = [col for col in inp["old"] if col not in inp["new"]]
    return {"broken_clients": broken}


def e432(inp):
    got = json.loads(Path(inp["path"]).read_text())["n"]
    return {"last": got, "guarantee": "last-write-wins"}


def e433(inp):
    docs = (("near", (2, 0)), ("far", (0, 3)))
    def score(vec):
        return sum(a * b for a, b in zip(inp["query"], vec))
    ranked = [name for name, _vec in sorted(docs, key=lambda item: score(item[1]), reverse=True)]
    return {"ranked": ranked}


def e434(inp):
    nodes = {"a"}
    rejected = inp["edge"][1] not in nodes or inp["edge"][0] not in nodes
    return {"rejected": rejected}


def e435(inp):
    s, p, o = inp["triple"]
    return {"s": s, "p": p, "o": o}


def e436(_inp):
    disjoint = frozenset({frozenset({"A", "B"})})
    assigned = ["A", "B"]
    return {"conflict": frozenset(assigned) in disjoint, "classes": assigned}


def e437(inp):
    data = Path(inp["path"]).read_bytes()
    return {"sha256": hashlib.sha256(data).hexdigest(), "size": len(data)}


def e438(inp):
    return {"equal": Path(inp["src"]).read_bytes() == Path(inp["dst"]).read_bytes()}


def e439(inp):
    return {"text": Path(inp["restored"]).read_text()}


def e440(inp):
    log = (("set", "n", 1), ("set", "n", 2), ("set", "n", 3))
    def replay(limit):
        state = {}
        for index, (op, key, value) in enumerate(log):
            if index >= limit:
                break
            if op == "set":
                state[key] = value
        return state
    return {"n": replay(inp["limit"])["n"], "full": replay(len(log))["n"]}


def e441(inp):
    durable = []
    if inp["crash_before_commit"] is False:
        durable.append("row")
    return {"durable": len(durable)}


def e442(inp):
    total = 0
    for event in inp["events"]:
        total += event["add"]
    return {"total": total}


def e443(inp):
    loaded = json.loads(Path(inp["path"]).read_text())
    return {"id": loaded["id"], "n": loaded["n"]}


def e444(_inp):
    mission = {"done": ["a"], "pending": ["b"]}
    return {"done": list(mission["done"]), "pending": list(mission["pending"])}


def e445(inp):
    seen = {}
    def apply(value):
        seen.setdefault(inp["key"], value)
        return seen[inp["key"]]
    return {"first": apply(1), "second": apply(2)}


def e446(inp):
    rows = []
    def add(i):
        if i in [row["id"] for row in rows]:
            return False
        rows.append({"id": i})
        return True
    add(inp["id"])
    again = add(inp["id"])
    return {"stored": len(rows), "duplicate": not again}


def e447(inp):
    effects = []
    for _ in (1, 2):
        if inp["id"] not in effects:
            effects.append(inp["id"])
    return {"effects": len(effects)}


def e448(inp):
    outbox = ["msg"] if inp["crash_after_commit"] else []
    sent = []
    return {"pending": outbox, "sent": len(sent)}


def e449(inp):
    current = {"version": inp["start"], "value": "a"}
    def write(incoming):
        if incoming["version"] != current["version"]:
            return False, current["value"]
        return True, incoming["value"]
    ok1, _v1 = write({"version": 1, "value": "b"})
    ok2, kept = write({"version": 2, "value": "c"})
    return {"first": ok1, "stale": not ok2, "kept": kept}


def e450(inp):
    version = inp["current"]
    rejected = inp["seen"] != version
    if not rejected:
        version += 1
    return {"rejected": rejected}


def e451(_inp):
    held = False
    def run():
        nonlocal held
        if held:
            return False
        held = True
        held = False
        return True
    ran = run()
    return {"ran": ran, "released": held is False}


def e452(inp):
    cache = {"a": 1}
    cached_generation = 1
    value = cache["a"] if cached_generation == inp["generation"] else None
    return {"stale": value}


def e453(inp):
    def alive(exp, protected):
        return True if protected else inp["now"] < exp
    return {"expired": not alive(10, False), "protected": alive(10, True)}


def e454(inp):
    versions = [json.loads(line)["v"] for line in Path(inp["path"]).read_text().splitlines() if line]
    return {"versions": versions}


def e455(inp):
    rows = ({"text": "alpha", "source": "s1"}, {"text": "beta", "source": "s2"})
    source = ""
    for row in rows:
        if row["text"] == inp["q"]:
            source = row["source"]
    return {"source": source}


def e456(inp):
    docs = (("d1", "courier letter"), ("d2", "unrelated lamp"))
    hits = [name for name, text in docs if inp["query"] in text.split()]
    tp = len([hit for hit in hits if hit in inp["relevant"]])
    return {"hits": hits, "tp": tp, "fp": len(hits) - tp}


def e457(_inp):
    rows = ((1, True), (2, False))
    return {"kept": [i for i, keep in rows if keep], "removed": [i for i, keep in rows if not keep]}


def e458(inp):
    return {"victim_remains": Path(inp["victim"]).exists(), "target_gone": not Path(inp["target"]).exists()}


def e459(inp):
    rows = ({"id": 1, "source": "s", "text": "a"}, {"id": 1, "source": "s", "text": "b"})
    last = {}
    for row in rows:
        last[row["id"]] = row
    return {"source": last[inp["id"]]["source"], "text": last[inp["id"]]["text"]}


def e460(inp):
    readable = True
    try:
        con = sqlite3.connect(inp["path"])
        con.execute("pragma schema_version")
        con.execute("select count(*) from sqlite_master")
        con.close()
    except sqlite3.DatabaseError:
        readable = False
    return {"readable": readable}


def e461(inp):
    committed = False
    if inp["partial"] and False:
        committed = True
    return {"committed": committed, "bytes_seen": 1}


def e462(inp):
    enospc = False
    committed = False
    try:
        raise OSError(inp["errno"], "No space left on device")
    except OSError as exc:
        enospc = exc.errno == 28
    return {"enospc": enospc, "committed": committed, "exists": False}


def e463(inp):
    con = sqlite3.connect(inp["path"])
    rows = [row[0] for row in con.execute("select n from t order by n")]
    con.close()
    return {"rows": rows}


def e464(_inp):
    con = sqlite3.connect(":memory:")
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
    return {"version": version, "cols": cols, "n": value}


TABLE = {i: globals()[f"e{i}"] for i in range(425, 465)}
