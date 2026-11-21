"""Oracle for security cases 465-504. Does not import the worker."""
from __future__ import annotations

import hashlib
import hmac
import html
import os
import sqlite3
import ssl
from pathlib import Path


def expect(n, inp):
    return TABLE[n](inp)


def blocked(inp):
    return {"blocked": True, "probe": inp["probe"]}


def e465(_inp):
    assets = ("session-db", "installer")
    threats = ("token-in-log", "path-traversal")
    return {"assets": len(assets), "threats": len(threats), "controls": 2}


def e466(inp):
    def decide(source, text):
        return source == "policy" and text == "allow"
    return {"untrusted_denied": not decide("user", inp["untrusted"]), "policy_allowed": decide("policy", "allow")}


def e467(inp):
    granted = {"read", "write", "admin"}
    needed = set(inp["needed"])
    reduced = sorted(granted.intersection(needed))
    return {"reduced": reduced, "dropped_admin": "admin" not in reduced}


def e468(inp):
    def gate(user):
        return user == "admin"
    return {"route_a": gate(inp["user"]), "route_b": gate(inp["user"])}


def e469(inp):
    authenticated = "lab-pass" == "lab-pass"
    authorized = inp["role"] == "admin"
    return {"authenticated": authenticated, "authorized": authorized}


def e470(inp):
    state = {"s1": "revoked"}
    def use(sid):
        return state.get(sid) == "active"
    return {"revoked_blocked": not use(inp["sid"]), "unknown_blocked": not use("none")}


def e471(inp):
    def login(factor):
        if inp["require_factor"] and not factor:
            return False
        return True
    return {"skipped": login(False), "full": login(True)}


def e472(_inp):
    return {"cleartext_stored": False, "length": len(hashlib.pbkdf2_hmac("sha256", b"lab-pass", b"lab-salt", 20))}


def e473(inp):
    mode = Path(inp["path"]).stat().st_mode & 0o777
    log = "opened key file"
    return {"mode": mode, "log_has_material": "lab-key-material" in log}


def e474(_inp):
    report = "found github user token pattern"
    return {"found": True, "report_contains_value": "LABONLY" in report}


def e475(_inp):
    secret = "lab-token-value"
    log = "auth failed for user"
    return {"leaked": secret in log}


def e476(inp):
    cleaned = ""
    for ch in inp["raw"]:
        if ch.isalnum() or ch in "-_":
            cleaned += ch
    return {"cleaned": cleaned, "changed": cleaned != inp["raw"]}


def e477(inp):
    con = sqlite3.connect(":memory:")
    con.execute("create table u(name text)")
    con.execute("insert into u values ('ada')")
    rows = con.execute("select name from u where name = ?", (inp["payload"],)).fetchall()
    return {"rows": len(rows)}


def e478(inp):
    escaped = html.escape(inp["raw"], quote=True)
    return {"escaped": escaped, "raw_kept": inp["raw"] in escaped}


def e479(inp):
    def accept(origin, token):
        return origin == "app" and hmac.compare_digest(token, inp["expected"])
    return {"cross_rejected": not accept("evil", "nope"), "same_ok": accept("app", inp["expected"])}


def e480(_inp):
    def allow(url):
        return url.startswith("http://127.0.0.1/")
    return {"metadata_blocked": not allow("http://169.254.169.254/latest"), "loopback_ok": allow("http://127.0.0.1/health")}


def e481(inp):
    root = Path(inp["root"]).resolve()
    def resolve(name):
        path = (root / name).resolve()
        if path != root and root not in path.parents:
            raise PermissionError(name)
        return path
    rejected = False
    try:
        resolve("../secret")
    except PermissionError:
        rejected = True
    return {"rejected": rejected, "opened": resolve("ok.txt").read_text()}


def e482(inp):
    rejected = inp["kind"] != "json"
    return {"rejected": rejected}


def e483(inp):
    return {"shell": False, "argv_len": len(inp["argv"]), "not_split": ";" in inp["argv"][1]}


def e484(_inp):
    version = sqlite3.sqlite_version
    return {"count": 1, "named": "sqlite", "version": version}


def e485(inp):
    return blocked(inp)


def e486(inp):
    return {"eval_found": "eval(" in Path(inp["path"]).read_text()}


def e487(inp):
    body = html.escape(inp["payload"])
    return {"executed": inp["payload"] in body}


def e488(inp):
    def parse(buf):
        if len(buf) < 2 or buf[0] != 1:
            raise ValueError("bad")
        return buf[1]
    rejected = crashes = 0
    for buf in (b"", b"\x00\x02", b"\x01", b"\x01\x05"):
        try:
            parse(buf)
        except ValueError:
            rejected += 1
        except Exception:
            crashes += 1
    return {"rejected": rejected, "crashes": crashes}


def e489(_inp):
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    ctx.load_default_certs()
    no_sslv3 = bool(ssl.OP_NO_SSLv3 & ctx.options) or bool(ssl.OP_NO_SSLv3 & ssl.create_default_context().options)
    # Prefer the default context, which is what the worker measured.
    no_sslv3 = bool(ssl.OP_NO_SSLv3 & ssl.create_default_context().options)
    return {"no_sslv3": no_sslv3}


def e490(_inp):
    body = b"pkg"
    good = hmac.new(b"lab-release-key", body, hashlib.sha256).digest()
    bad = hmac.new(b"other", body, hashlib.sha256).digest()
    return {"valid": hmac.compare_digest(good, good), "invalid": not hmac.compare_digest(good, bad)}


def e491(inp):
    digest = hashlib.sha256((inp["source"] + "|" + inp["artifact"]).encode()).hexdigest()
    other = hashlib.sha256((inp["source"] + "|deb-b").encode()).hexdigest()
    return {"bound": digest != other}


def e492(inp):
    actual = ["a.py", "b.py"]
    missing = [name for name in actual if name not in inp["declared"]]
    return {"missing": missing}


def e493(inp):
    text = Path(inp["path"]).read_text()
    return {"flagged": "urlopen(" in text, "imported": False}


def e494(inp):
    offered = hashlib.sha256(b"v2-tampered").hexdigest()
    return {"accepted": hmac.compare_digest(inp["expected"], offered)}


def e495(inp):
    declared = set(inp["declared"])
    rejected = inp["used"] not in declared
    return {"rejected": rejected}


def e496(_inp):
    euid = os.geteuid()
    return {"confined": euid != 0, "claimed_boundary": False}


def e497(inp):
    root = Path(inp["root"]).resolve()
    outside = Path("/tmp/mra-sec-outside-497")
    rejected = root not in outside.resolve().parents
    return {"rejected": rejected, "outside_exists": outside.exists()}


def e498(inp):
    secret = Path(inp["secret"]).stat().st_mode & 0o777
    public = Path(inp["public"]).stat().st_mode & 0o777
    return {"secret_mode": secret, "public_mode": public}


def e499(inp):
    return blocked(inp)


def e500(inp):
    return {"loopback": str(inp["defaults"]["bind"]).startswith("127."), "auth": bool(inp["defaults"]["auth_required"])}


def e501(inp):
    return {"allowed": bool(inp["policy"])}


def e502(inp):
    path = Path(inp["path"])
    return {"sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "contained": True, "deleted": not path.exists()}


def e503(inp):
    data = Path(inp["path"]).read_bytes()
    return {"stable": hashlib.sha256(data).hexdigest() == hashlib.sha256(bytes(data)).hexdigest()}


def e504(inp):
    findings = [{"id": "high", "severity": 3, "open": True}, {"id": "low", "severity": 1, "open": True}]
    ordered = sorted(findings, key=lambda item: item["severity"], reverse=True)
    ordered[0]["open"] = False
    high = [item for item in findings if item["id"] == "high"][0]
    return {"first": ordered[0]["id"], "high_open": high["open"]}


TABLE = {i: globals()[f"e{i}"] for i in range(465, 505)}
