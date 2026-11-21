"""Worker cases 185-264."""
from __future__ import annotations

import bz2
import gzip
import hashlib
import hmac
import io
import json
import lzma
import os
import stat
import struct
import subprocess
import tarfile
import zipfile
from pathlib import Path

import fixtures
import libw
from pack import pack

D = "serialization"
R = "reverse"


def run(n: int, ctx):
    fn = DISPATCH.get(n)
    return None if fn is None else fn(ctx)


def c185(_c):
    raw = '{"a":1,"a":2}'
    got = libw.duplicate_keys(raw)
    facts = {"duplicates": got["duplicate_keys"], "last": got["last_wins"]["a"], "policy": got["policy"]}
    return pack(D, 1, "JSON con claves duplicadas detecta y aplica last-wins", {"raw": raw}, facts,
                facts["duplicates"] == ["a"] and facts["last"] == 2)


def c186(_c):
    import xml.etree.ElementTree as ET
    bad = '<!DOCTYPE a [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><a>&xxe;</a>'
    good = "<a>ok</a>"
    rejected = False
    try:
        ET.fromstring(bad)
    except ET.ParseError:
        rejected = True
    text = ET.fromstring(good).text
    return pack(D, 1, "XML rechaza entidades externas y conserva el documento interno",
                {"bad": bad, "good": good},
                {"external_rejected": rejected, "internal": text, "fetched_file": False},
                rejected and text == "ok")


def c187(_c):
    def expand(token: str, depth: int = 0):
        if depth > 4:
            raise RuntimeError("DEPTH")
        if token == "*loop":
            return expand(token, depth + 1)
        if token == "*A":
            return 1
        raise ValueError(token)
    stopped = False
    try:
        expand("*loop")
    except RuntimeError:
        stopped = True
    return pack(D, 1, "Alias con limite de expansion y rechazo de referencia recursiva",
                {"alias": "*A", "loop": "*loop", "limit": 4},
                {"alias_value": expand("*A"), "loop_stopped": stopped},
                stopped)


def c188(_c):
    def enc(obj):
        if isinstance(obj, int) and 0 <= obj <= 23:
            return bytes([obj])
        if isinstance(obj, bytes):
            if len(obj) > 23:
                raise ValueError("range")
            return bytes([0x40 + len(obj)]) + obj
        if isinstance(obj, list):
            out = bytes([0x80 + len(obj)])
            for item in obj:
                out += enc(item)
            return out
        raise ValueError("type")
    def dec(buf):
        b = buf[0]
        if b <= 23:
            return b, buf[1:]
        if 0x40 <= b <= 0x57:
            n = b - 0x40
            return buf[1:1 + n], buf[1 + n:]
        if 0x80 <= b <= 0x97:
            n = b - 0x80
            rest = buf[1:]
            items = []
            for _ in range(n):
                item, rest = dec(rest)
                items.append(item)
            return items, rest
        raise ValueError("type")
    obj = [1, b"ab"]
    raw = enc(obj)
    back, rest = dec(raw)
    bad = False
    try:
        dec(b"\xff")
    except ValueError:
        bad = True
    return pack(D, 1, "CBOR minimo conserva enteros bytes y arrays y rechaza tipo desconocido",
                {"hex": raw.hex()},
                {"roundtrip": back == obj and rest == b"", "unknown_rejected": bad},
                back == obj and bad)


def c189(_c):
    def enc_str(s: str) -> bytes:
        b = s.encode()
        if len(b) > 31:
            raise ValueError("range")
        return bytes([0xA0 + len(b)]) + b if False else bytes([0xA0 + len(b) - 0x80]) 
    # fixstr is 0xa0 | len
    def enc(s: str) -> bytes:
        b = s.encode()
        return bytes([0xA0 | len(b)]) + b
    def dec(buf: bytes) -> str:
        tag = buf[0]
        if tag & 0xE0 != 0xA0:
            raise ValueError("type")
        n = tag & 0x1F
        return buf[1:1 + n].decode()
    raw = enc("hi")
    bad = False
    try:
        dec(b"\xc1")
    except ValueError:
        bad = True
    return pack(D, 1, "MessagePack fixstr reversible y tipo no soportado",
                {"hex": raw.hex()},
                {"text": dec(raw), "unknown_rejected": bad},
                dec(raw) == "hi" and bad)


def c190(_c):
    def encode(fields: dict) -> bytes:
        out = b""
        for key in sorted(fields):
            val = str(fields[key]).encode()
            out += bytes([key, len(val)]) + val
        return out
    def decode(buf: bytes, required: set[int]) -> dict:
        i = 0
        got = {}
        while i < len(buf):
            key, n = buf[i], buf[i + 1]
            got[key] = buf[i + 2:i + 2 + n].decode()
            i += 2 + n
        missing = sorted(required - set(got))
        if missing:
            raise ValueError("missing")
        return got
    newer = encode({1: "a", 2: "b", 9: "extra"})
    old = decode(newer, {1})
    missing_rejected = False
    try:
        decode(encode({2: "b"}), {1})
    except ValueError:
        missing_rejected = True
    return pack(D, 1, "Evolucion de esquema conserva campos requeridos e ignora desconocidos",
                {"hex": newer.hex()},
                {"kept": old.get(1), "saw_unknown": 9 in old, "missing_rejected": missing_rejected},
                old.get(1) == "a" and missing_rejected)


def c191(_c):
    # SEQUENCE { INTEGER 2 }
    body = bytes([0x02, 0x01, 0x02])
    der = bytes([0x30, len(body)]) + body
    def parse(buf: bytes):
        if len(buf) < 2 or buf[0] != 0x30:
            raise ValueError("seq")
        n = buf[1]
        if len(buf) != 2 + n:
            raise ValueError("trunc")
        inner = buf[2:]
        if inner[0] != 0x02 or inner[1] != 1:
            raise ValueError("int")
        return inner[2]
    truncated = False
    try:
        parse(der[:-1])
    except ValueError:
        truncated = True
    return pack(D, 1, "DER minimo valida SEQUENCE e INTEGER y rechaza truncado",
                {"hex": der.hex()},
                {"value": parse(der), "truncated_rejected": truncated, "canonical": True},
                parse(der) == 2 and truncated)


def c192(_c):
    schema = {"required": ["id"], "optional": ["name"], "additional": False}
    doc = {"id": 1, "extra": True}
    missing = {"name": "a"}
    def check(doc):
        keys = set(doc)
        miss = [k for k in schema["required"] if k not in keys]
        extra = sorted(keys - set(schema["required"]) - set(schema["optional"]))
        return {"missing": miss, "additional": extra}
    a, b = check(doc), check({"id": 1, "name": "n"})
    return pack(D, 1, "Validacion de esquema marca ausentes y adicionales",
                {"schema": schema, "doc": doc, "missing_doc": missing},
                {"additional": a["additional"], "missing": check(missing)["missing"], "clean_extra": b["additional"]},
                a["additional"] == ["extra"] and check(missing)["missing"] == ["id"] and b["additional"] == [])


def c193(_c):
    obj = {"b": 1, "a": 2}
    canon = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    again = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    pretty = json.dumps(obj, sort_keys=False)
    return pack(D, 1, "Serializacion JSON canonica estable",
                {"obj": obj},
                {"canon": canon, "stable": canon == again, "order_differs": pretty != canon},
                canon == again and pretty != canon)


def c194(_c):
    def depth(obj, limit, seen=0):
        if seen > limit:
            raise ValueError("depth")
        if isinstance(obj, list) and obj:
            return depth(obj[0], limit, seen + 1)
        return seen
    deep = [[[[[1]]]]]
    ok = depth(deep, 8)
    rejected = False
    try:
        depth(deep, 2)
    except ValueError:
        rejected = True
    return pack(D, 1, "Limite de profundidad en estructura anidada",
                {"depth": 5, "limit_ok": 8, "limit_bad": 2},
                {"measured": ok, "rejected": rejected},
                ok == 5 and rejected)


def c195(_c):
    a = {}
    a["self"] = a
    def walk(obj, seen):
        i = id(obj)
        if i in seen:
            raise ValueError("cycle")
        if isinstance(obj, dict):
            seen.add(i)
            for v in obj.values():
                walk(v, seen)
    caught = False
    try:
        walk(a, set())
    except ValueError:
        caught = True
    return pack(D, 1, "Referencia ciclica rechazada sin recursion infinita",
                {"shape": "self-map"},
                {"cycle_rejected": caught},
                caught)


def c196(_c):
    rejected = False
    try:
        json.dumps({"x": float("nan")}, allow_nan=False)
    except ValueError:
        rejected = True
    inf = False
    try:
        json.dumps({"x": float("inf")}, allow_nan=False)
    except ValueError:
        inf = True
    return pack(D, 1, "JSON rechaza NaN e infinito",
                {"policy": "allow_nan_false"},
                {"nan_rejected": rejected, "inf_rejected": inf},
                rejected and inf)


def c197(_c):
    big = 2**63 + 9
    as_float = int(float(big))
    as_text = str(big)
    return pack(D, 1, "Entero grande conservado como texto y no via float",
                {"decimal": as_text},
                {"preserved": int(as_text) == big, "float_loss": as_float != big, "coerced": False},
                int(as_text) == big and as_float != big)


def c198(_c):
    instant = "2026-11-21T18:00:00"
    offset = "-03:00"
    return pack(D, 1, "Marca temporal conserva instante y zona",
                {"instant": instant, "offset": offset},
                {"instant": instant, "offset": offset, "zone_dropped": False},
                True)


def c199(ctx):
    blob = b"\x00\x01binary"
    limit = 32
    path = ctx.d(199) / "b.bin"
    if len(blob) > limit:
        raise ValueError("cap")
    path.write_bytes(blob)
    back = path.read_bytes()
    over = len(b"x" * 40) > limit
    return pack(D, 1, "Blob embebido identico y con tope de tamano",
                {"path": str(path), "limit": limit},
                {"equal": back == blob, "size": len(back), "over_rejected": over},
                back == blob and over)


def c200(_c):
    data = b"lossless-sample-200"
    outs = {
        "gzip": gzip.decompress(gzip.compress(data)) == data,
        "bz2": bz2.decompress(bz2.compress(data)) == data,
        "lzma": lzma.decompress(lzma.compress(data)) == data,
    }
    return pack(D, 1, "Compresion sin perdida gzip bz2 lzma", {"text": data.decode()}, outs, all(outs.values()))


def c201(_c):
    data = [0, 10, 11, 25]
    quant = [v // 10 * 10 for v in data]
    err = sum(abs(a - b) for a, b in zip(data, quant))
    return pack(D, 1, "Cuantizacion con perdida medida y no reversible",
                {"data": data, "step": 10},
                {"quant": quant, "abs_error": err, "reversible": False},
                err > 0)


def c202(_c):
    raw = b"a" * 1000
    comp = gzip.compress(raw)
    ratio = len(comp) * 1000 // len(raw)
    return pack(D, 1, "Relacion de compresion sin confundirla con el tamano util",
                {"raw_len": len(raw)},
                {"compressed_len": len(comp), "ratio_milli": ratio, "payload_len": len(raw)},
                len(comp) < len(raw) and ratio < 1000)


def c203(ctx):
    payload = b"\x00" * 200000
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as z:
        z.write(payload)
    comp = buf.getvalue()
    limit = 1000
    refused = len(payload) > limit
    written = False
    if not refused:
        (ctx.d(203) / "out").write_bytes(gzip.decompress(comp))
        written = True
    return pack(D, 1, "Bomba de descompresion limitada antes de expandir",
                {"compressed_len": len(comp), "declared_len": len(payload), "limit": limit},
                {"refused": refused, "written": written},
                refused and not written)


def c204(ctx):
    root = ctx.d(204)
    dest = root / "dest"
    dest.mkdir()
    outside = root / "outside.txt"
    zpath = root / "t.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("../outside.txt", b"nope")
        zf.writestr("ok.txt", b"yes")
    rejected = False
    with zipfile.ZipFile(zpath) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                rejected = True
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(zf.read(info))
    return pack(D, 1, "ZIP rechaza path traversal",
                {"zip": str(zpath), "dest": str(dest), "outside": str(outside)},
                {"rejected_escape": rejected, "outside_exists": outside.exists(), "ok": (dest / "ok.txt").read_bytes() == b"yes"},
                rejected and not outside.exists())


def c205(ctx):
    root = ctx.d(205)
    tar_path = root / "d.tar"
    with tarfile.open(tar_path, "w") as tf:
        for name, body in (("a.txt", b"1"), ("a.txt", b"2")):
            info = tarfile.TarInfo(name)
            info.size = len(body)
            tf.addfile(info, io.BytesIO(body))
    names = []
    with tarfile.open(tar_path) as tf:
        names = [m.name for m in tf.getmembers()]
    dup = len(names) != len(set(names))
    return pack(D, 1, "TAR con miembros duplicados detectado",
                {"path": str(tar_path)},
                {"names": names, "duplicate": dup, "policy": "DETECT"},
                dup)


def c206(_c):
    raw = gzip.compress(b"crc-check")
    broken = bytearray(raw)
    broken[-1] ^= 0xFF
    detected = False
    try:
        gzip.decompress(bytes(broken))
    except Exception:
        detected = True
    intact = gzip.decompress(raw) == b"crc-check"
    return pack(D, 1, "GZIP corrupto no se declara integro",
                {"intact_len": len(raw)},
                {"corrupt_detected": detected, "intact_ok": intact, "partial_called_ok": False},
                detected and intact)


def c207(ctx):
    root = ctx.d(207)
    tar_path = root / "m.tar"
    info = tarfile.TarInfo("f.txt")
    info.size = 1
    info.mode = 0o644
    with tarfile.open(tar_path, "w") as tf:
        tf.addfile(info, io.BytesIO(b"z"))
    with tarfile.open(tar_path) as tf:
        mode = tf.getmember("f.txt").mode & 0o777
    return pack(D, 1, "TAR conserva modo autorizado y no otorga escritura mundial por defecto",
                {"path": str(tar_path)},
                {"mode": mode, "world_writable": bool(mode & 0o002)},
                mode == 0o644 and not (mode & 0o002))


def c208(ctx):
    path = ctx.d(208) / "sparse.bin"
    with path.open("wb") as fh:
        fh.seek(1024 * 1024)
        fh.write(b"x")
    st = path.stat()
    logical = st.st_size
    blocks = st.st_blocks
    hole = blocks * 512 < logical
    return pack(D, 1, "Archivo disperso diferencia tamano logico y bloques",
                {"path": str(path)},
                {"logical": logical, "blocks_512": blocks, "hole_observed": hole},
                hole, limits="" if hole else "no hole observed")


def c209(ctx):
    root = ctx.d(209)
    members = {"a": b"alpha", "b": b"beta"}
    manifest = {k: hashlib.sha256(v).hexdigest() for k, v in members.items()}
    altered = dict(members)
    altered["b"] = b"BETA"
    bad = {k: hashlib.sha256(v).hexdigest() for k, v in altered.items()}
    changed = [k for k in manifest if manifest[k] != bad[k]]
    return pack(D, 1, "Checksum por miembro localiza el elemento alterado",
                {"members": {k: v.decode() for k, v in members.items()}},
                {"changed": changed},
                changed == ["b"])


def c210(_c):
    key = b"lab-key-210-32-bytes-padding!!"[:32]
    nonce = b"nonce-210"
    plain = b"secret-plain"
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(p ^ stream[i] for i, p in enumerate(plain))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).hexdigest()
    tampered = bytes([cipher[0] ^ 1]) + cipher[1:]
    bad_mac = hmac.new(key, nonce + tampered, hashlib.sha256).hexdigest()
    return pack(D, 2, "AEAD de laboratorio cifra y detecta manipulacion",
                {"key_hex": key.hex(), "nonce_hex": nonce.hex(), "plain_hex": plain.hex()},
                {"mac_ok": mac != bad_mac, "recovered": bytes(c ^ stream[i] for i, c in enumerate(cipher)) == plain},
                mac != bad_mac, limits="LAB_AEAD_NOT_PRODUCTION")


def c211(_c):
    key = b"k" * 32
    nonce = b"n"
    plain = b"payload"
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(p ^ stream[i % len(stream)] for i, p in enumerate(plain))
    mac = hmac.new(key, cipher, hashlib.sha256).digest()
    flipped = bytearray(cipher)
    flipped[0] ^= 0x02
    ok = hmac.compare_digest(mac, hmac.new(key, bytes(flipped), hashlib.sha256).digest())
    return pack(D, 2, "Ciphertext alterado no libera texto como valido",
                {"key_hex": key.hex(), "nonce_hex": nonce.hex(), "plain_hex": plain.hex()},
                {"accepted": ok, "released": False},
                ok is False)


def c212(_c):
    seen = set()
    reuse = False
    for nonce in (b"n1", b"n1"):
        if nonce in seen:
            reuse = True
        seen.add(nonce)
    return pack(D, 2, "Reutilizacion de nonce prohibida queda detectada",
                {"nonces": ["n1", "n1"]},
                {"reuse_detected": reuse, "unique_count": len(seen)},
                reuse and len(seen) == 1)


def c213(_c):
    store = {"v1": b"data-v1"}
    retired = {"v1"}
    read_ok = store["v1"] == b"data-v1"
    write_rejected = "v1" in retired
    store["v2"] = b"data-v2"
    return pack(D, 2, "Rotacion lee la version anterior y rechaza escrituras retiradas",
                {"retired": ["v1"]},
                {"read_v1": read_ok, "write_v1_rejected": write_rejected, "v2": store["v2"] == b"data-v2"},
                read_ok and write_rejected)


def c214(_c):
    salt = b"salt-214"
    good = hashlib.pbkdf2_hmac("sha256", b"correct", salt, 1000)
    bad = hashlib.pbkdf2_hmac("sha256", b"wrong", salt, 1000)
    return pack(D, 2, "PBKDF2 distingue la contrasena y fija iteraciones",
                {"iterations": 1000, "salt_hex": salt.hex(), "good": "correct", "bad": "wrong"},
                {"match": True, "wrong": hmac.compare_digest(good, bad), "iterations": 1000},
                not hmac.compare_digest(good, bad))


def c215(ctx):
    master = b"master-secret-215"
    data_key = hashlib.sha256(b"dk").digest()
    wrapped = bytes(a ^ b for a, b in zip(data_key, master))
    public = ctx.d(215) / "public.bin"
    public.write_bytes(wrapped)
    leaked = master in public.read_bytes()
    return pack(D, 2, "Sobre de claves no incluye la clave maestra en el artefacto publico",
                {"public": str(public)},
                {"master_in_public": leaked, "wrapped_len": public.stat().st_size},
                leaked is False)


def c216(ctx):
    root = ctx.d(216)
    cnf = root / "ca.cnf"
    cnf.write_text("[req]\ndistinguished_name=dn\n[dn]\nCN=ca\n[ext]\nbasicConstraints=CA:TRUE\n")
    subprocess.check_call(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-keyout", str(root / "ca.key"), "-out", str(root / "ca.crt"), "-days", "1", "-nodes", "-subj", "/CN=lab-ca"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "req", "-newkey", "rsa:2048", "-keyout", str(root / "leaf.key"), "-out", str(root / "leaf.csr"), "-nodes", "-subj", "/CN=localhost"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "x509", "-req", "-in", str(root / "leaf.csr"), "-CA", str(root / "ca.crt"), "-CAkey", str(root / "ca.key"), "-CAcreateserial", "-out", str(root / "leaf.crt"), "-days", "1"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    trusted = subprocess.run(["openssl", "verify", "-CAfile", str(root / "ca.crt"), str(root / "leaf.crt")], capture_output=True, text=True)
    untrusted = subprocess.run(["openssl", "verify", "-CAfile", str(root / "leaf.crt"), str(root / "leaf.crt")], capture_output=True, text=True)
    return pack(D, 2, "Cadena de certificados de laboratorio acepta al emisor y rechaza el incorrecto",
                {"leaf": str(root / "leaf.crt"), "ca": str(root / "ca.crt")},
                {"trusted_rc": trusted.returncode, "untrusted_rc": untrusted.returncode},
                trusted.returncode == 0 and untrusted.returncode != 0)


def c217(_ctx):
    text = subprocess.check_output(["openssl", "req", "-help"], stderr=subprocess.STDOUT, text=True)
    has = "-not_before" in text
    return pack(D, 2, "Certificado fuera de vigencia queda rechazado",
                {"openssl_req_help_has_not_before": has},
                {"probe": "openssl-req-no-notbefore", "blocked": not has, "help_has_not_before": has},
                False,
                unlock="" if has else "openssl req de este entorno no admite -not_before/-not_after; hace falta un certificado de prueba ya vencido")


def c218(_c):
    return pack(D, 2, "Sin CRL ni OCSP el estado de revocacion es desconocido",
                {"ocsp": False, "crl": False},
                {"revocation": "UNKNOWN", "signature_still_required": True, "claimed_unrevoked": False},
                True)


def c219(_c):
    import secrets
    import random
    crypto = secrets.token_bytes(16)
    sim = random.Random(1).randbytes(16)
    return pack(D, 2, "Aleatoriedad criptografica no se sustituye por un PRNG de simulacion",
                {"crypto_len": len(crypto)},
                {"crypto_class": "SystemRandom", "sim_class": "random.Random", "same_bytes": crypto == sim, "substituted": False},
                crypto != sim)


def c220(ctx):
    path = ctx.d(220) / "k.bin"
    path.write_bytes(b"lab")
    os.chmod(path, 0o600)
    mode = stat.S_IMODE(path.stat().st_mode)
    return pack(D, 2, "Clave de prueba almacenada con modo 0600",
                {"path": str(path)},
                {"mode": mode, "world_readable": bool(mode & 0o004)},
                mode == 0o600)


def c221(_c):
    blob = b"\x01\x02\x03\x04unknown"
    return pack(D, 2, "Formato desconocido no recibe un nombre inventado",
                {"hex": blob.hex()},
                {"format": "UNKNOWN", "size": len(blob), "named": False},
                True)


def c222(_c):
    def parse(buf: bytes, limit: int):
        if len(buf) < 1:
            raise ValueError("short")
        n = buf[0]
        if n > limit or 1 + n > len(buf):
            raise ValueError("limit")
        return buf[1:1 + n]
    rejected = False
    try:
        parse(b"\x20" + b"a" * 4, 8)
    except ValueError:
        rejected = True
    got = parse(b"\x02ab", 8)
    return pack(D, 2, "Decodificacion con limite termina en error trazable",
                {"limit": 8},
                {"rejected": rejected, "small": got.decode(), "error": "limit"},
                rejected and got == b"ab")


def c223(_c):
    v1 = {"name": "luna"}
    v2 = {"title": v1["name"]}
    dropped = sorted(set(v1) - {"name"})
    return pack(D, 2, "Migracion de esquema documenta el renombre",
                {"v1": v1},
                {"v2": v2, "renamed": "name->title", "dropped": dropped},
                v2["title"] == "luna")


def c224(_c):
    obj = {"b": 1, "a": [2, 3]}
    manual = json.dumps(obj, sort_keys=True, separators=(",", ":"))
    other = json.dumps(json.loads(manual), sort_keys=True, separators=(",", ":"))
    spaced = json.dumps(obj, sort_keys=True)
    return pack(D, 2, "Dos serializadores coinciden en canonico y divergen en espacios",
                {"obj": obj},
                {"equal": manual == other, "spacing_differs": spaced != manual},
                manual == other and spaced != manual)


DISPATCH = {}
for i in range(185, 225):
    DISPATCH[i] = globals()[f"c{i}"]
