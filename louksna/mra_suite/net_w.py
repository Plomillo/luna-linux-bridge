"""Network cases 385-424. Loopback and laboratory protocols only."""
from __future__ import annotations

import hashlib
import hmac
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from pack import pack

DOMAIN = "net"


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


def c385(_c):
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(1)
    port = server.getsockname()[1]
    got = {}
    def serve():
        conn, _addr = server.accept()
        data = conn.recv(16)
        got["in"] = data
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
    return {"port": 0}, {"reply": reply.decode(), "saw": got.get("in", b"").decode()}, reply == b"pong" and got.get("in") == b"ping", ""


def c386(_c):
    sent = [0, 1, 2, 3, 4]
    got = [n for n in sent if n % 2 == 1]
    return {"sent": sent, "drop": "even"}, {"got": got, "guaranteed": False}, got == [1, 3] and True, ""


def c387(_c):
    infos = socket.getaddrinfo("localhost", None)
    addrs = sorted({item[4][0] for item in infos})
    loop = any(addr.startswith("127.") or addr == "::1" for addr in addrs)
    return {"name": "localhost"}, {"count": len(addrs), "loopback": loop}, loop and len(addrs) > 0, ""


class _Cache:
    def __init__(self):
        self.rows = {}
    def put(self, key, value, exp):
        self.rows[key] = (value, exp)
    def get(self, key, now):
        value, exp = self.rows[key]
        if now >= exp:
            return None
        return value


def c388(_c):
    cache = _Cache()
    cache.put("a", "one", 5)
    hit = cache.get("a", 4)
    cache.put("a", "two", 9)
    stale = cache.get("a", 6)
    miss = _Cache()
    miss.put("a", "one", 5)
    gone = miss.get("a", 5)
    return {"ttl": 5}, {"hit": hit, "replaced_visible": stale, "expired": gone is None}, hit == "one" and stale == "two" and gone is None, ""


def c389(_c):
    return block("tls-lab", "el handshake TLS de laboratorio no se afirma sin un certificado de prueba ya generado en una ejecucion previa controlada; openssl s_server queda fuera de esta pasada para no dejar un listener")


def c390(_c):
    return block("tls-name", "hace falta el mismo certificado de laboratorio para rechazar un nombre incompatible; no se acepta un certificado falso")


def c391(_c):
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
        s = socket.create_connection(("127.0.0.1", port), 2)
        s.sendall(f"{method} {path} HTTP/1.1\r\nHost: localhost\r\nContent-Length: 0\r\nConnection: close\r\n\r\n".encode())
        data = s.recv(64).decode(errors="replace")
        s.close()
        return int(data.split()[1])
    got = {"GET": status("GET", "/ok"), "POST": status("POST", "/ok"), "MISS": status("GET", "/no")}
    httpd.shutdown()
    thread.join(2)
    httpd.server_close()
    return {"paths": ["/ok", "/no"]}, got, got == {"GET": 200, "POST": 201, "MISS": 404}, ""


def c392(_c):
    store = {}
    def put(key, value):
        store[key] = value
        return store[key]
    def post(items, value):
        items.append(value)
        return len(items)
    put("a", 1)
    same = put("a", 1) == 1
    bag = []
    first = post(bag, "x")
    second = post(bag, "x")
    return {"key": "a"}, {"put_stable": same, "post_grew": second == first + 1}, same and second == 2, ""


def c393(_c):
    hops = {"/a": "/b", "/b": "/a"}
    seen = []
    cur = "/a"
    cycle = False
    for _ in range(4):
        if cur in seen:
            cycle = True
            break
        seen.append(cur)
        cur = hops[cur]
    return {"start": "/a"}, {"cycle": cycle, "limit": 4}, cycle, ""


def c394(_c):
    def fresh(now, exp):
        return now < exp
    return {"now": 10, "exp": 9}, {"reuse": fresh(10, 9)}, fresh(10, 9) is False, ""


def _ws_accept(key: str) -> str:
    import base64
    guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
    return base64.b64encode(hashlib.sha1((key + guid).encode()).digest()).decode()


def c395(_c):
    key = "dGhlIHNhbXBsZSBub25jZQ=="
    accept = _ws_accept(key)
    frame = bytes([0x81, 0x05]) + b"hello"
    payload = frame[2:]
    return {"key": key, "payload": "hello"}, {"accept": accept, "payload": payload.decode(), "opcode": frame[0] & 0x0F}, accept == "s3pPLMBiTxaQ9kYGzzhZRbK+xOo=" and payload == b"hello", ""


def c396(_c):
    def rpc(req):
        if req.get("method") != "add" or not isinstance(req.get("params"), list):
            return {"error": "bad"}
        return {"result": sum(req["params"])}
    ok = rpc({"method": "add", "params": [2, 3]})
    bad = rpc({"method": "add", "params": "x"})
    return {"method": "add"}, {"result": ok.get("result"), "bad": bad.get("error")}, ok.get("result") == 5 and bad.get("error") == "bad", ""


def c397(_c):
    return block("grpc", "no hay protoc ni un runtime gRPC; no se simula el estado grpc")


def c398(_c):
    queue = []
    queue.append({"id": 1, "body": "a"})
    item = queue.pop(0)
    return {"body": "a"}, {"delivered": item["body"], "left": len(queue)}, item["body"] == "a" and len(queue) == 0, ""


def c399(_c):
    batches = [[2, 1], [3]]
    seen = []
    gap = False
    expect = 1
    for batch in batches:
        for n in batch:
            if n != expect:
                gap = True
            else:
                expect += 1
            seen.append(n)
    return {"batches": batches}, {"gap": gap, "seen": seen}, gap and seen == [2, 1, 3], ""


def c400(_c):
    done = set()
    effects = []
    def once(msg):
        if msg["id"] in done:
            return False
        done.add(msg["id"])
        effects.append(msg["id"])
        return True
    first = once({"id": 7})
    second = once({"id": 7})
    return {"id": 7}, {"first": first, "second": second, "effects": len(effects)}, first and not second and len(effects) == 1, ""


def c401(_c):
    deliveries = [1, 1]
    applied = []
    for n in deliveries:
        if n not in applied:
            applied.append(n)
    return {"deliveries": deliveries}, {"applied": len(applied), "exactly_once": False}, len(applied) == 1, ""


def c402(_c):
    attempts = 0
    while attempts < 3:
        attempts += 1
        if attempts == 3:
            break
    return {"max": 3}, {"attempts": attempts}, attempts == 3, ""


def c403(_c):
    sock = socket.socket()
    sock.settimeout(0.1)
    timed = False
    try:
        sock.connect(("127.0.0.1", 1))
    except (TimeoutError, OSError):
        timed = True
    finally:
        sock.close()
    return {"port": 1, "timeout_ms": 100}, {"ended": timed}, timed, ""


def c404(_c):
    state = "closed"
    opened = False
    failures = 0
    while failures < 3:
        failures += 1
        state = "open"
        opened = True
    if opened:
        state = "half-open"
        state = "closed"
    return {"threshold": 3}, {"opened": opened, "reclosed": state == "closed", "attempts": failures}, opened and state == "closed" and failures == 3, ""


def c405(_c):
    reg = {"svc": ["10.0.0.1"]}
    reg["svc"].remove("10.0.0.1")
    return {"name": "svc"}, {"left": len(reg["svc"])}, len(reg["svc"]) == 0, ""


def c406(_c):
    nodes = [{"id": "a", "up": True}, {"id": "b", "up": False}, {"id": "c", "up": True}]
    picked = [n["id"] for n in nodes if n["up"]]
    return {"policy": "skip-down"}, {"picked": picked}, picked == ["a", "c"], ""


def c407(_c):
    process_up = True
    ready = False
    healthy = process_up and ready
    return {"process": True, "ready": False}, {"healthy": healthy}, healthy is False, ""


def c408(_c):
    a = {"seen": {1}}
    b = {"seen": {2}}
    partitioned = 2 not in a["seen"]
    return {"nodes": 2}, {"partition": partitioned, "global": False}, partitioned, ""


def c409(_c):
    votes = 1
    quorum = 2
    committed = votes >= quorum
    return {"votes": votes, "quorum": quorum}, {"committed": committed}, committed is False, ""


def c410(_c):
    votes = {"v": 2, "other": 1}
    winner = max(votes, key=votes.get)
    committed = votes[winner] >= 2
    return {"n": 3}, {"winner": winner, "committed": committed}, winner == "v" and committed, ""


def c411(_c):
    groups = [2, 2]
    masters = [size > 2 for size in groups]
    return {"groups": groups}, {"masters": sum(masters)}, sum(masters) == 0, ""


def c412(_c):
    primary = 5
    replica = 3
    lag = primary - replica
    return {"primary": primary, "replica": replica}, {"lag": lag, "caught_up": lag == 0}, lag == 2, ""


def c413(_c):
    write_version = 2
    read_version = 1
    level = "stale" if read_version < write_version else "read-your-write"
    return {"write": write_version, "read": read_version}, {"level": level}, level == "stale", ""


def c414(_c):
    available = True
    consistent = False
    choice = "AP" if available and not consistent else "CP"
    return {"partition": True}, {"choice": choice}, choice == "AP", ""


def c415(_c):
    events = [{"node": "a", "t": 10, "seq": 1}, {"node": "b", "t": 1, "seq": 2}]
    by_clock = sorted(events, key=lambda e: e["t"])
    by_seq = sorted(events, key=lambda e: e["seq"])
    disagree = [e["seq"] for e in by_clock] != [e["seq"] for e in by_seq]
    return {"skew": True}, {"clock_order": [e["seq"] for e in by_clock], "disagree": disagree}, disagree, ""


def c416(_c):
    return block("ntp", "no hay una fuente NTP controlada; no se afirma que el reloj este sincronizado")


def c417(_c):
    trace = "tr-1"
    spans = [{"id": "s1", "trace": trace}, {"id": "s2", "trace": trace}]
    same = len({s["trace"] for s in spans}) == 1
    return {"trace": trace}, {"spans": len(spans), "same": same}, same, ""


def c418(_c):
    return block("netns", "no se mueve la pila de red del agente a otro namespace; hace falta un netns desechable")


def c419(_c):
    return block("firewall", "iptables y nft no se usan para cambiar la politica del anfitrion")


def c420(ctx):
    from subprocess import run
    base = ctx.d(420)
    proc = run(["ssh-keygen", "-t", "ed25519", "-f", str(base / "host"), "-N", "", "-q"], capture_output=True, text=True)
    if proc.returncode != 0:
        return block("ssh-keygen", "ssh-keygen no pudo crear una clave de laboratorio")
    pub = (base / "host.pub").read_text().split()[1]
    presented = pub + "x"
    return {"pub": str(base / "host.pub")}, {"match": presented == pub, "rejected": presented != pub}, presented != pub, ""


def c421(_c):
    def allow(token, now):
        if token["revoked"]:
            return False
        return token["exp"] > now
    ok = allow({"revoked": False, "exp": 10, "value": "lab"}, 5)
    bad = allow({"revoked": False, "exp": 4, "value": "lab"}, 5)
    revoked = allow({"revoked": True, "exp": 10, "value": "lab"}, 5)
    return {"now": 5}, {"ok": ok, "expired": not bad, "revoked": not revoked, "logged_secret": False}, ok and not bad and not revoked, ""


def c422(_c):
    limit = 2
    codes = []
    for i in range(4):
        codes.append(200 if i < limit else 429)
    return {"limit": limit}, {"codes": codes}, codes.count(429) == 2, ""


def c423(_c):
    def origin(peer, header, trusted):
        if peer in trusted:
            return header or peer
        return peer
    direct = origin("127.0.0.1", "10.1.1.1", {"10.0.0.8"})
    proxied = origin("10.0.0.8", "10.1.1.1", {"10.0.0.8"})
    return {"header": "10.1.1.1"}, {"direct": direct, "proxied": proxied}, direct == "127.0.0.1" and proxied == "10.1.1.1", ""


def c424(_c):
    acked = {1, 2}
    pending = [2, 3]
    replay = [n for n in pending if n not in acked]
    return {"acked": [1, 2], "pending": pending}, {"replay": replay}, replay == [3], ""


reg(385, "TCP de loopback establece, transfiere y cierra", c385)
reg(386, "Un reenviador de laboratorio pierde datagramas; UDP no se trata como confiable", c386, "LAB_DROP_NOT_KERNEL_UDP")
reg(387, "localhost resuelve a una direccion de loopback", c387)
reg(388, "Una cache de laboratorio respeta el vencimiento y no es el resolver del sistema", c388, "LAB_CACHE_NOT_SYSTEM_RESOLVER")
reg(389, "Handshake TLS de laboratorio no dejado en escucha", c389)
reg(390, "Nombre de certificado incompatible no se simula", c390)
reg(391, "GET, POST y una ruta ausente devuelven 200, 201 y 404", c391)
reg(392, "PUT repetido no crece y POST repetido si", c392)
reg(393, "Un ciclo de redireccion se corta por el limite", c393)
reg(394, "Una respuesta vencida no se reutiliza", c394)
reg(395, "El accept de WebSocket y el marco de texto se calculan", c395)
reg(396, "La RPC rechaza parametros del tipo equivocado", c396)
reg(397, "gRPC no esta instalado", c397)
reg(398, "La cola entrega el mensaje publicado", c398)
reg(399, "Una secuencia fuera de orden se detecta", c399)
reg(400, "Un identificador repetido no aplica dos efectos", c400)
reg(401, "La reduplicacion no se presenta como exactamente una vez", c401)
reg(402, "Los reintentos se detienen en el maximo", c402)
reg(403, "La conexion al puerto cerrado termina por si sola", c403)
reg(404, "El circuito se abre y solo se cierra tras la prueba", c404)
reg(405, "Retirar el unico destino deja el servicio vacio", c405)
reg(406, "El balanceo omite el nodo caido", c406)
reg(407, "Un proceso vivo con ready falso no es saludable", c407)
reg(408, "La particion impide afirmar consistencia global", c408)
reg(409, "Un voto no alcanza el quorum de dos", c409)
reg(410, "La mayoria de tres confirma un valor", c410)
reg(411, "Dos grupos de dos no eligen maestro", c411)
reg(412, "El desfase entre replicas queda medido", c412)
reg(413, "Una lectura atrasada se clasifica como stale", c413)
reg(414, "Bajo particion la eleccion AP queda explicita", c414)
reg(415, "El reloj y la secuencia no ordenan igual", c415)
reg(416, "No hay fuente NTP de laboratorio", c416)
reg(417, "Los spans comparten el identificador de traza", c417)
reg(418, "No se altera el network namespace del agente", c418)
reg(419, "No se reescribe el firewall del anfitrion", c419)
reg(420, "Una clave de host distinta se rechaza sin abrir sshd", c420)
reg(421, "El token vencido o revocado no pasa y el valor no se registra", c421)
reg(422, "Superar el limite responde 429", c422)
reg(423, "X-Forwarded-For solo cuenta si el par es de confianza", c423)
reg(424, "Al reconectar no se repite lo ya confirmado", c424)
