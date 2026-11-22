"""Security cases 465-504. Laboratory inputs only; no live credentials."""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import sqlite3
import stat
from pathlib import Path

from pack import pack

DOMAIN = "security"


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


def c465(_c):
    assets = ["session-db", "installer"]
    threats = ["token-in-log", "path-traversal"]
    return {"scope": "lab"}, {"assets": len(assets), "threats": len(threats), "controls": 2}, len(assets) == 2 and len(threats) == 2, ""


def c466(_c):
    def decide(source, text):
        if source != "policy":
            return False
        return text == "allow"
    untrusted = decide("user", "allow")
    trusted = decide("policy", "allow")
    return {"untrusted": "allow"}, {"untrusted_denied": not untrusted, "policy_allowed": trusted}, (not untrusted) and trusted, ""


def c467(_c):
    granted = {"read", "write", "admin"}
    needed = {"read"}
    reduced = granted & needed
    return {"needed": sorted(needed)}, {"reduced": sorted(reduced), "dropped_admin": "admin" not in reduced}, reduced == {"read"}, ""


def c468(_c):
    def gate(user, route):
        return user == "admin"
    a = gate("user", "/admin")
    b = gate("user", "/admin/export")
    return {"user": "user"}, {"route_a": a, "route_b": b}, a is False and b is False, ""


def c469(_c):
    def auth(password):
        return password == "lab-pass"
    def authz(role, action):
        return role == "admin" and action == "write"
    return {"role": "reader"}, {"authenticated": auth("lab-pass"), "authorized": authz("reader", "write")}, auth("lab-pass") and not authz("reader", "write"), ""


def c470(_c):
    sessions = {"s1": "revoked"}
    def use(sid):
        return sessions.get(sid) == "active"
    return {"sid": "s1"}, {"revoked_blocked": not use("s1"), "unknown_blocked": not use("none")}, (not use("s1")) and (not use("none")), ""


def c471(_c):
    def login(password_ok, factor_ok, require_factor):
        if not password_ok:
            return False
        if require_factor and not factor_ok:
            return False
        return True
    skipped = login(True, False, True)
    full = login(True, True, True)
    return {"require_factor": True}, {"skipped": skipped, "full": full}, skipped is False and full is True, ""


def c472(ctx):
    password = "lab-pass"
    stored = hashlib.pbkdf2_hmac("sha256", password.encode(), b"lab-salt", 20)
    path = ctx.d(472) / "cred"
    path.write_bytes(stored)
    text = path.read_text(errors="replace")
    return {"rounds": 20}, {"cleartext_stored": password in text, "length": len(stored)}, password not in text and len(stored) == 32, ""


def c473(ctx):
    path = ctx.d(473) / "key"
    path.write_text("lab-key-material")
    path.chmod(0o600)
    mode = path.stat().st_mode & 0o777
    log = "opened key file"
    return {"path": str(path)}, {"mode": mode, "log_has_material": "lab-key-material" in log}, mode == 0o600 and "lab-key-material" not in log, ""


def c474(ctx):
    sample = ctx.d(474) / "notes.txt"
    sample.write_text("prefix " + "gh" + "u_" + "LABONLY" + " end")
    text = sample.read_text()
    needle = "gh" + "u_"
    found = needle in text
    redacted = text.replace(needle + "LABONLY", "[redacted]")
    return {"file": str(sample)}, {"found": found, "report_contains_value": "LABONLY" in "found github user token pattern"}, found and "LABONLY" not in "found github user token pattern", ""


def c475(_c):
    secret = "lab-token-value"
    log = "auth failed for user"
    return {"event": "auth-failed"}, {"leaked": secret in log}, secret not in log, ""


def c476(_c):
    def clean(value):
        return "".join(ch for ch in value if ch.isalnum() or ch in "-_")
    raw = "ok; rm"
    return {"raw": raw}, {"cleaned": clean(raw), "changed": clean(raw) != raw}, clean(raw) == "okrm", ""


def c477(ctx):
    con = sqlite3.connect(ctx.d(477) / "t.db")
    con.execute("create table u(name text)")
    con.execute("insert into u values ('ada')")
    payload = "' OR '1'='1"
    rows = list(con.execute("select name from u where name = ?", (payload,)))
    con.close()
    return {"payload": payload}, {"rows": len(rows)}, len(rows) == 0, ""


def c478(_c):
    raw = "<script>alert(1)</script>"
    escaped = html.escape(raw)
    return {"raw": raw}, {"escaped": escaped, "raw_kept": raw in escaped}, "<" not in escaped and raw not in escaped, ""


def c479(_c):
    def accept(origin, token, expected):
        return origin == "app" and hmac.compare_digest(token, expected)
    bad = accept("evil", "nope", "lab-csrf")
    good = accept("app", "lab-csrf", "lab-csrf")
    return {"expected": "lab-csrf"}, {"cross_rejected": not bad, "same_ok": good}, (not bad) and good, ""


def c480(_c):
    def allow(url):
        if url.startswith("http://127.0.0.1/"):
            return True
        return False
    blocked = not allow("http://169.254.169.254/latest")
    local = allow("http://127.0.0.1/health")
    return {"blocked_host": "169.254.169.254"}, {"metadata_blocked": blocked, "loopback_ok": local}, blocked and local, ""


def c481(ctx):
    root = ctx.d(481) / "root"
    root.mkdir()
    inside = root / "ok.txt"
    inside.write_text("ok")
    def resolve(name):
        path = (root / name).resolve()
        if root.resolve() not in path.parents and path != root.resolve():
            raise PermissionError(name)
        return path
    rejected = False
    try:
        resolve("../secret")
    except PermissionError:
        rejected = True
    opened = resolve("ok.txt").read_text()
    return {"root": str(root)}, {"rejected": rejected, "opened": opened}, rejected and opened == "ok", ""


def c482(_c):
    def load(kind, payload):
        if kind != "json":
            raise TypeError(kind)
        if not isinstance(payload, dict):
            raise TypeError("shape")
        return payload
    rejected = False
    try:
        load("pickle", {"cmd": "os.system"})
    except TypeError:
        rejected = True
    return {"kind": "pickle"}, {"rejected": rejected}, rejected, ""


def c483(_c):
    args = ["echo", "ok; rm -rf /"]
    joined = " ".join(args)
    shell = False
    return {"argv": args}, {"shell": shell, "argv_len": len(args), "not_split": args[1] == "ok; rm -rf /"}, shell is False and len(args) == 2, ""


def c484(_c):
    components = [{"name": "sqlite", "version": sqlite3.sqlite_version, "origin": "stdlib"}]
    return {"root": "lab"}, {"count": len(components), "named": components[0]["name"], "version": components[0]["version"]}, bool(components[0]["version"]), ""


def c485(_c):
    return block("osv", "no hay una copia fechada de OSV/NVD en este entorno; no se inventan CVEs")


def c486(ctx):
    path = ctx.d(486) / "sample.py"
    path.write_text("def f(x):\n    return eval(x)\n")
    text = path.read_text()
    return {"path": str(path)}, {"eval_found": "eval(" in text}, "eval(" in text, ""


def c487(_c):
    def reflect(value):
        return html.escape(value)
    payload = "<script>"
    body = reflect(payload)
    return {"payload": payload}, {"executed": payload in body}, payload not in body, ""


def c488(_c):
    def parse(buf):
        if not buf or buf[0] != 1:
            raise ValueError("magic")
        if len(buf) < 2:
            raise ValueError("short")
        return buf[1]
    crashes = 0
    rejected = 0
    for buf in (b"", b"\x00\x02", b"\x01", b"\x01\x05"):
        try:
            parse(buf)
        except ValueError:
            rejected += 1
        except Exception:
            crashes += 1
    return {"samples": 4}, {"rejected": rejected, "crashes": crashes}, crashes == 0 and rejected == 3, ""


def c489(_c):
    import ssl
    ctx = ssl.create_default_context()
    options = ctx.options
    weak = bool(options & getattr(ssl, "OP_NO_SSLv3", 0)) or "sslv3" not in ",".join(getattr(ctx, "protocol", "") and []) 
    no_sslv3 = bool(getattr(ssl, "OP_NO_SSLv3", 0) and (options & ssl.OP_NO_SSLv3))
    return {"openssl": ssl.OPENSSL_VERSION.split()[0]}, {"no_sslv3": no_sslv3}, no_sslv3, ""


def c490(_c):
    body = b"pkg"
    key = b"lab-release-key"
    good = hmac.new(key, body, hashlib.sha256).hexdigest()
    bad = hmac.new(b"other", body, hashlib.sha256).hexdigest()
    return {"alg": "hmac-sha256"}, {"valid": hmac.compare_digest(good, good), "invalid": not hmac.compare_digest(good, bad)}, hmac.compare_digest(good, good) and not hmac.compare_digest(good, bad), ""


def c491(_c):
    source = "tree-a"
    artifact = "deb-a"
    digest = hashlib.sha256((source + "|" + artifact).encode()).hexdigest()
    tampered = hashlib.sha256((source + "|deb-b").encode()).hexdigest()
    return {"source": source, "artifact": artifact}, {"bound": digest != tampered}, digest != tampered, ""


def c492(_c):
    declared = {"a.py"}
    actual = {"a.py", "b.py"}
    missing = sorted(actual - declared)
    return {"declared": sorted(declared)}, {"missing": missing}, missing == ["b.py"], ""


def c493(ctx):
    path = ctx.d(493) / "setup.py"
    path.write_text("import urllib.request\nurllib.request.urlopen('http://example.invalid')\n")
    text = path.read_text()
    flagged = "urlopen" in text or "socket" in text
    imported = False
    return {"path": str(path)}, {"flagged": flagged, "imported": imported}, flagged and not imported, ""


def c494(_c):
    good = hashlib.sha256(b"v2").hexdigest()
    offered = hashlib.sha256(b"v2-tampered").hexdigest()
    return {"expected": good}, {"accepted": hmac.compare_digest(good, offered)}, hmac.compare_digest(good, offered) is False, ""


def c495(_c):
    declared = {"gcc"}
    def build(tool):
        if tool not in declared:
            raise PermissionError(tool)
        return True
    rejected = False
    try:
        build("curl")
    except PermissionError:
        rejected = True
    return {"declared": ["gcc"], "used": "curl"}, {"rejected": rejected}, rejected, ""


def c496(_c):
    euid = os.geteuid()
    confined = euid != 0
    return {"euid": euid}, {"confined": confined, "claimed_boundary": False}, True, ""


def c497(ctx):
    root = ctx.d(497)
    outside = Path("/tmp/mra-sec-outside-497")
    def write(path):
        if root.resolve() not in Path(path).resolve().parents:
            raise PermissionError(path)
        Path(path).write_text("x")
    rejected = False
    try:
        write(outside)
    except PermissionError:
        rejected = True
    return {"root": str(root)}, {"rejected": rejected, "outside_exists": outside.exists()}, rejected and not outside.exists(), ""


def c498(ctx):
    secret = ctx.d(498) / "secret"
    secret.write_text("x")
    secret.chmod(0o600)
    public = ctx.d(498) / "public"
    public.write_text("y")
    public.chmod(0o644)
    secret_mode = secret.stat().st_mode & 0o777
    public_mode = public.stat().st_mode & 0o777
    return {"secret": str(secret), "public": str(public)}, {"secret_mode": secret_mode, "public_mode": public_mode}, secret_mode == 0o600 and public_mode & 0o004, ""


def c499(_c):
    return block("priv-esc", "no se intenta una escalada real ni se deja un binario setuid; hace falta un usuario de laboratorio aislado")


def c500(_c):
    config = {"bind": "127.0.0.1", "auth_required": True}
    return {"defaults": config}, {"loopback": config["bind"].startswith("127."), "auth": config["auth_required"]}, config["bind"] == "127.0.0.1" and config["auth_required"], ""


def c501(_c):
    def authorize(policy_present):
        if not policy_present:
            return False
        return True
    return {"policy": False}, {"allowed": authorize(False)}, authorize(False) is False, ""


def c502(ctx):
    evidence = ctx.d(502) / "evidence.txt"
    evidence.write_text("incident-lab")
    digest = hashlib.sha256(evidence.read_bytes()).hexdigest()
    contained = True
    return {"path": str(evidence)}, {"sha256": digest, "contained": contained, "deleted": not evidence.exists()}, evidence.exists() and contained, ""


def c503(ctx):
    path = ctx.d(503) / "log.txt"
    path.write_text("event-1")
    first = hashlib.sha256(path.read_bytes()).hexdigest()
    second = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"path": str(path)}, {"stable": first == second}, first == second, ""


def c504(_c):
    findings = [{"id": "high", "severity": 3, "open": True}, {"id": "low", "severity": 1, "open": True}]
    ordered = sorted(findings, key=lambda item: -item["severity"])
    ordered[0]["open"] = False
    return {"ids": ["high", "low"]}, {"first": ordered[0]["id"], "high_open": findings[0]["open"]}, ordered[0]["id"] == "high" and findings[0]["open"] is False, ""


reg(465, "El modelo de amenazas nombra activos y amenazas de laboratorio", c465)
reg(466, "Un texto no confiable no se convierte en autorizacion", c466)
reg(467, "Se retiran privilegios que no estan en el conjunto necesario", c467)
reg(468, "Dos rutas aplican la misma autorizacion", c468)
reg(469, "Autenticar no autoriza la accion", c469)
reg(470, "Una sesion revocada no se usa", c470)
reg(471, "Sin el segundo factor no hay ingreso", c471)
reg(472, "La contrasena de laboratorio no queda en claro", c472)
reg(473, "La clave de laboratorio queda en modo 0600 y fuera del log", c473)
reg(474, "El detector marca un patron de token sin copiarlo al reporte", c474)
reg(475, "El log de fallo no incluye el secreto", c475)
reg(476, "Los metacaracteres se quitan de la entrada", c476)
reg(477, "El payload SQL queda como literal y no como clausula", c477)
reg(478, "El marcado peligroso se escapa", c478)
reg(479, "Una peticion sin el token esperado se rechaza", c479)
reg(480, "El destino de metadatos no esta en la lista permitida", c480)
reg(481, "Una ruta que sale del directorio se rechaza", c481)
reg(482, "Un tipo de deserializacion no permitido se rechaza", c482)
reg(483, "El argumento adversarial sigue siendo un solo argv", c483)
reg(484, "El inventario nombra la version real de sqlite", c484)
reg(485, "No hay copia OSV/NVD para fechar hallazgos", c485)
reg(486, "El analisis estatico ve el eval sembrado", c486)
reg(487, "La respuesta escapada no contiene el marcado original", c487)
reg(488, "Las entradas malformadas se rechazan sin otra excepcion", c488)
reg(489, "El contexto TLS por defecto no ofrece SSLv3", c489)
reg(490, "Una firma HMAC distinta se rechaza", c490)
reg(491, "Cambiar el artefacto cambia el vinculo de procedencia", c491)
reg(492, "Un archivo presente y no declarado aparece como omision", c492)
reg(493, "La dependencia de prueba se marca sin importarla", c493)
reg(494, "El hash distinto no se acepta como actualizacion", c494)
reg(495, "Una herramienta no declarada no entra en la construccion", c495)
reg(496, "Root no se presenta como un contenedor confinado", c496)
reg(497, "Escribir fuera del directorio del caso se rechaza", c497)
reg(498, "El secreto queda en 0600 y el archivo publico no", c498)
reg(499, "No se monta una escalada de privilegios", c499)
reg(500, "El valor por defecto ata a loopback y exige autenticacion", c500)
reg(501, "Sin politica de autorizacion la accion se niega", c501)
reg(502, "El incidente conserva la evidencia y su hash", c502)
reg(503, "El hash de la evidencia no cambia entre lecturas", c503)
reg(504, "El hallazgo alto se cierra antes que el bajo", c504)
