"""Oracle for network cases 385-424. Does not import the worker."""
from __future__ import annotations

import base64
import hashlib
import shutil
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


def e385(_inp):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    box = {}
    def serve():
        conn, _addr = server.accept()
        box["in"] = conn.recv(16)
        conn.sendall(b"pong")
        conn.close()
    thread = threading.Thread(target=serve)
    thread.start()
    client = socket.create_connection(("127.0.0.1", port), 2)
    client.sendall(b"ping")
    reply = client.recv(16)
    client.close()
    thread.join(2)
    server.close()
    return {"reply": reply.decode(), "saw": box.get("in", b"").decode()}


def e386(inp):
    got = [n for n in inp["sent"] if n % 2]
    return {"got": got, "guaranteed": False}


def e387(inp):
    found = set()
    for item in socket.getaddrinfo(inp["name"], None):
        found.add(item[4][0])
    addrs = sorted(found)
    loop = False
    for addr in addrs:
        if addr == "::1" or addr.startswith("127."):
            loop = True
    return {"count": len(addrs), "loopback": loop}


def e388(inp):
    class Store(dict):
        def read(self, key, now):
            value, exp = self[key]
            if now >= exp:
                return None
            return value
    live = Store()
    live["a"] = ("one", inp["ttl"])
    hit = live.read("a", 4)
    live["a"] = ("two", 9)
    stale = live.read("a", 6)
    dead = Store()
    dead["a"] = ("one", inp["ttl"])
    gone = dead.read("a", inp["ttl"])
    return {"hit": hit, "replaced_visible": stale, "expired": gone is None}


def e389(inp):
    return blocked(inp)


def e390(inp):
    return blocked(inp)


def e391(_inp):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200 if self.path == "/ok" else 404)
            self.end_headers()
        def do_POST(self):
            self.send_response(201)
            self.end_headers()
        def log_message(self, *_a):
            return
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever)
    thread.start()
    port = httpd.server_address[1]
    def status(method, path):
        sock = socket.create_connection(("127.0.0.1", port), 2)
        sock.sendall(("%s %s HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\nConnection: close\r\n\r\n" % (method, path)).encode())
        line = sock.recv(80).split()
        sock.close()
        return int(line[1])
    got = {"GET": status("GET", "/ok"), "POST": status("POST", "/ok"), "MISS": status("GET", "/no")}
    httpd.shutdown()
    thread.join(2)
    httpd.server_close()
    return got


def e392(_inp):
    state = {}
    def put(key, value):
        state[key] = value
        return state[key]
    bag = []
    stable = put("a", 1) == put("a", 1)
    bag.append("x")
    n1 = len(bag)
    bag.append("x")
    n2 = len(bag)
    return {"put_stable": stable, "post_grew": n2 == n1 + 1}


def e393(_inp):
    hops = {"/a": "/b", "/b": "/a"}
    seen = []
    cur = "/a"
    cycle = False
    step = 0
    while step < 4:
        if cur in seen:
            cycle = True
            break
        seen.append(cur)
        cur = hops[cur]
        step += 1
    return {"cycle": cycle, "limit": 4}


def e394(inp):
    return {"reuse": inp["now"] < inp["exp"]}


def e395(inp):
    digest = hashlib.sha1()
    digest.update(inp["key"].encode())
    digest.update(b"258EAFA5-E914-47DA-95CA-C5AB0DC85B11")
    accept = base64.b64encode(digest.digest()).decode()
    raw = inp["payload"].encode()
    frame = bytes([0x81, len(raw)]) + raw
    return {"accept": accept, "payload": frame[2:].decode(), "opcode": frame[0] & 15}


def e396(_inp):
    def call(params):
        if not isinstance(params, list):
            return {"error": "bad"}
        return {"result": params[0] + params[1]}
    ok = call([2, 3])
    bad = call("x")
    return {"result": ok.get("result"), "bad": bad.get("error")}


def e397(inp):
    if shutil.which("protoc") or shutil.which("grpc_cli"):
        return {"blocked": False, "probe": inp["probe"]}
    return blocked(inp)


def e398(inp):
    queue = [{"id": 1, "body": inp["body"]}]
    item = queue.pop(0)
    return {"delivered": item["body"], "left": len(queue)}


def e399(inp):
    expect_n = 1
    gap = False
    seen = []
    for batch in inp["batches"]:
        for n in batch:
            if n != expect_n:
                gap = True
            else:
                expect_n += 1
            seen.append(n)
    return {"gap": gap, "seen": seen}


def e400(inp):
    seen = []
    def apply(i):
        if i in seen:
            return False
        seen.append(i)
        return True
    return {"first": apply(inp["id"]), "second": apply(inp["id"]), "effects": len(seen)}


def e401(inp):
    applied = []
    for n in inp["deliveries"]:
        if applied.count(n) == 0:
            applied.append(n)
    return {"applied": len(applied), "exactly_once": False}


def e402(inp):
    attempts = 0
    while attempts < inp["max"]:
        attempts += 1
    return {"attempts": attempts}


def e403(inp):
    sock = socket.socket()
    sock.settimeout(inp["timeout_ms"] / 1000)
    ended = False
    try:
        sock.connect(("127.0.0.1", inp["port"]))
    except OSError:
        ended = True
    finally:
        sock.close()
    return {"ended": ended}


def e404(inp):
    failures = 0
    opened = False
    while failures < inp["threshold"]:
        failures += 1
        opened = True
    state = "closed" if opened else "open"
    return {"opened": opened, "reclosed": state == "closed", "attempts": failures}


def e405(_inp):
    reg = ["10.0.0.1"]
    del reg[0]
    return {"left": len(reg)}


def e406(_inp):
    nodes = (("a", True), ("b", False), ("c", True))
    return {"picked": [name for name, up in nodes if up]}


def e407(inp):
    return {"healthy": bool(inp["process"] and inp["ready"])}


def e408(_inp):
    left = {1}
    right = {2}
    return {"partition": 2 not in left or 1 not in right, "global": False}


def e409(inp):
    return {"committed": inp["votes"] >= inp["quorum"]}


def e410(inp):
    tally = {"v": 2, "other": 1}
    winner = sorted(tally, key=lambda k: (-tally[k], k))[0]
    return {"winner": winner, "committed": tally[winner] >= (inp["n"] // 2 + 1)}


def e411(inp):
    masters = [1 for size in inp["groups"] if size > sum(inp["groups"]) / 2]
    return {"masters": len(masters)}


def e412(inp):
    lag = inp["primary"] - inp["replica"]
    return {"lag": lag, "caught_up": lag == 0}


def e413(inp):
    level = "stale" if inp["read"] < inp["write"] else "read-your-write"
    return {"level": level}


def e414(inp):
    choice = "AP" if inp["partition"] else "CP"
    return {"choice": choice}


def e415(_inp):
    events = ({"t": 10, "seq": 1}, {"t": 1, "seq": 2})
    by_clock = sorted(events, key=lambda e: e["t"])
    by_seq = sorted(events, key=lambda e: e["seq"])
    clock_order = [e["seq"] for e in by_clock]
    return {"clock_order": clock_order, "disagree": clock_order != [e["seq"] for e in by_seq]}


def e416(inp):
    return blocked(inp)


def e417(inp):
    spans = ("s1", "s2")
    return {"spans": len(spans), "same": True and inp["trace"] == inp["trace"]}


def e418(inp):
    return blocked(inp)


def e419(inp):
    return blocked(inp)


def e420(inp):
    pub = Path(inp["pub"]).read_text().split()[1]
    presented = pub + "x"
    return {"match": presented == pub, "rejected": presented != pub}


def e421(inp):
    def allow(exp, revoked):
        if revoked:
            return False
        return exp > inp["now"]
    ok = allow(10, False)
    bad = allow(4, False)
    revoked = allow(10, True)
    return {"ok": ok, "expired": not bad, "revoked": not revoked, "logged_secret": False}


def e422(inp):
    codes = []
    i = 0
    while i < inp["limit"] + 2:
        codes.append(200 if i < inp["limit"] else 429)
        i += 1
    return {"codes": codes}


def e423(inp):
    trusted = {"10.0.0.8"}
    def origin(peer, header):
        if peer in trusted:
            return header
        return peer
    return {"direct": origin("127.0.0.1", inp["header"]), "proxied": origin("10.0.0.8", inp["header"])}


def e424(inp):
    acked = set(inp["acked"])
    replay = [n for n in inp["pending"] if n not in acked]
    return {"replay": replay}


TABLE = {i: globals()[f"e{i}"] for i in range(385, 425)}
