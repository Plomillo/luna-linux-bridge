"""Oracle for cases 185-224. Does not import the worker."""
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
import subprocess
import zipfile
from collections import Counter
from pathlib import Path


def expect(n: int, inp: dict) -> dict:
    return TABLE[n](inp)


def e185(inp):
    keys = []
    raw = inp["raw"]
    i = 0
    while True:
        j = raw.find('"', i)
        if j < 0:
            break
        k = raw.find('"', j + 1)
        key = raw[j + 1:k]
        if k + 1 < len(raw) and raw[k + 1] == ":":
            keys.append(key)
        i = k + 1
    dups = [k for k, v in Counter(keys).items() if v > 1]
    return {"duplicates": dups, "last": json.loads(raw)["a"], "policy": "DETECT_AND_LAST_WINS"}


def e186(inp):
    import xml.etree.ElementTree as ET
    rejected = False
    try:
        ET.fromstring(inp["bad"])
    except ET.ParseError:
        rejected = True
    return {"external_rejected": rejected, "internal": ET.fromstring(inp["good"]).text, "fetched_file": False}


def e187(inp):
    def expand(token: str):
        steps = 0
        while token == inp["loop"]:
            steps += 1
            if steps > inp["limit"]:
                raise RuntimeError("DEPTH")
        if token == inp["alias"]:
            return 1
        raise ValueError(token)
    stopped = False
    try:
        expand(inp["loop"])
    except RuntimeError:
        stopped = True
    return {"alias_value": 1, "loop_stopped": stopped}


def e188(inp):
    buf = bytes.fromhex(inp["hex"])
    def dec(buf):
        b = buf[0]
        if b <= 23:
            return b, buf[1:]
        if 0x40 <= b <= 0x57:
            n = b & 0x1F
            return buf[1:1 + n], buf[1 + n:]
        if 0x80 <= b <= 0x97:
            n = b & 0x1F
            rest = buf[1:]
            items = []
            for _ in range(n):
                item, rest = dec(rest)
                items.append(item)
            return items, rest
        raise ValueError("type")
    back, rest = dec(buf)
    bad = False
    try:
        dec(b"\xff")
    except ValueError:
        bad = True
    return {"roundtrip": back == [1, b"ab"] and rest == b"", "unknown_rejected": bad}


def e189(inp):
    buf = bytes.fromhex(inp["hex"])
    tag = buf[0]
    if tag & 0xE0 != 0xA0:
        raise ValueError("type")
    n = tag & 0x1F
    text = buf[1:1 + n].decode()
    bad = True
    try:
        if b"\xc1"[0] & 0xE0 == 0xA0:
            bad = False
    except ValueError:
        bad = True
    return {"text": text, "unknown_rejected": bad}


def e190(inp):
    buf = bytes.fromhex(inp["hex"])
    i = 0
    got = {}
    while i < len(buf):
        key, n = buf[i], buf[i + 1]
        got[key] = buf[i + 2:i + 2 + n].decode()
        i += 2 + n
    missing = 1 not in {2: "b"}
    return {"kept": got.get(1), "saw_unknown": 9 in got, "missing_rejected": True if missing else False}


def e191(inp):
    buf = bytes.fromhex(inp["hex"])
    if buf[0] != 0x30 or len(buf) != 2 + buf[1]:
        raise ValueError("trunc")
    value = buf[4]
    trunc = False
    try:
        short = buf[:-1]
        if len(short) != 2 + short[1]:
            raise ValueError("trunc")
    except Exception:
        trunc = True
    return {"value": value, "truncated_rejected": trunc, "canonical": True}


def e192(inp):
    schema = inp["schema"]
    def check(doc):
        keys = set(doc)
        miss = [k for k in schema["required"] if k not in keys]
        extra = sorted(keys - set(schema["required"]) - set(schema["optional"]))
        return miss, extra
    extra = check(inp["doc"])[1]
    missing = check(inp["missing_doc"])[0]
    clean = check({"id": 1, "name": "n"})[1]
    return {"additional": extra, "missing": missing, "clean_extra": clean}


def e193(inp):
    canon = json.dumps(inp["obj"], sort_keys=True, separators=(",", ":"))
    pretty = json.dumps(inp["obj"], sort_keys=False)
    return {"canon": canon, "stable": canon == json.dumps(inp["obj"], sort_keys=True, separators=(",", ":")), "order_differs": pretty != canon}


def e194(inp):
    return {"measured": inp["depth"], "rejected": inp["depth"] > inp["limit_bad"]}


def e195(_inp):
    return {"cycle_rejected": True}


def e196(_inp):
    nan = inf = False
    try:
        json.dumps({"x": float("nan")}, allow_nan=False)
    except ValueError:
        nan = True
    try:
        json.dumps({"x": float("inf")}, allow_nan=False)
    except ValueError:
        inf = True
    return {"nan_rejected": nan, "inf_rejected": inf}


def e197(inp):
    big = int(inp["decimal"])
    return {"preserved": int(inp["decimal"]) == big, "float_loss": int(float(big)) != big, "coerced": False}


def e198(inp):
    return {"instant": inp["instant"], "offset": inp["offset"], "zone_dropped": False}


def e199(inp):
    blob = Path(inp["path"]).read_bytes()
    return {"equal": blob == b"\x00\x01binary", "size": len(blob), "over_rejected": 40 > inp["limit"]}


def e200(inp):
    data = inp["text"].encode()
    return {"gzip": gzip.decompress(gzip.compress(data)) == data, "bz2": bz2.decompress(bz2.compress(data)) == data, "lzma": lzma.decompress(lzma.compress(data)) == data}


def e201(inp):
    quant = [v // inp["step"] * inp["step"] for v in inp["data"]]
    err = sum(abs(a - b) for a, b in zip(inp["data"], quant))
    return {"quant": quant, "abs_error": err, "reversible": False}


def e202(inp):
    raw = b"a" * inp["raw_len"]
    comp = gzip.compress(raw)
    return {"compressed_len": len(comp), "ratio_milli": len(comp) * 1000 // len(raw), "payload_len": len(raw)}


def e203(inp):
    return {"refused": inp["declared_len"] > inp["limit"], "written": False}


def e204(inp):
    dest = Path(inp["dest"])
    outside = Path(inp["outside"])
    rejected = False
    with zipfile.ZipFile(inp["zip"]) as zf:
        for info in zf.infolist():
            target = (dest / info.filename).resolve()
            if not str(target).startswith(str(dest.resolve())):
                rejected = True
    return {"rejected_escape": rejected, "outside_exists": outside.exists(), "ok": (dest / "ok.txt").read_bytes() == b"yes"}


def e205(inp):
    import tarfile
    with tarfile.open(inp["path"]) as tf:
        names = [m.name for m in tf.getmembers()]
    return {"names": names, "duplicate": len(names) != len(set(names)), "policy": "DETECT"}


def e206(_inp):
    raw = gzip.compress(b"crc-check")
    broken = bytearray(raw)
    broken[-1] ^= 0xFF
    detected = False
    try:
        gzip.decompress(bytes(broken))
    except Exception:
        detected = True
    intact = gzip.decompress(raw) == b"crc-check"
    return {"corrupt_detected": detected, "intact_ok": intact, "partial_called_ok": False}


def e207(inp):
    import tarfile
    with tarfile.open(inp["path"]) as tf:
        mode = tf.getmember("f.txt").mode & 0o777
    return {"mode": mode, "world_writable": bool(mode & 0o002)}


def e208(inp):
    st = Path(inp["path"]).stat()
    return {"logical": st.st_size, "blocks_512": st.st_blocks, "hole_observed": st.st_blocks * 512 < st.st_size}


def e209(inp):
    members = {k: v.encode() for k, v in inp["members"].items()}
    altered = dict(members)
    altered["b"] = b"BETA"
    changed = [k for k in members if hashlib.sha256(members[k]).digest() != hashlib.sha256(altered[k]).digest()]
    return {"changed": changed}


def e210(inp):
    key = bytes.fromhex(inp["key_hex"])
    nonce = bytes.fromhex(inp["nonce_hex"])
    plain = bytes.fromhex(inp["plain_hex"])
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(p ^ stream[i] for i, p in enumerate(plain))
    mac = hmac.new(key, nonce + cipher, hashlib.sha256).hexdigest()
    tampered = bytes([cipher[0] ^ 1]) + cipher[1:]
    bad = hmac.new(key, nonce + tampered, hashlib.sha256).hexdigest()
    return {"mac_ok": mac != bad, "recovered": bytes(c ^ stream[i] for i, c in enumerate(cipher)) == plain}


def e211(inp):
    key = bytes.fromhex(inp["key_hex"])
    plain = bytes.fromhex(inp["plain_hex"])
    nonce = bytes.fromhex(inp["nonce_hex"])
    stream = hashlib.sha256(key + nonce).digest()
    cipher = bytes(p ^ stream[i % len(stream)] for i, p in enumerate(plain))
    mac = hmac.new(key, cipher, hashlib.sha256).digest()
    flipped = bytearray(cipher)
    flipped[0] ^= 0x02
    ok = hmac.compare_digest(mac, hmac.new(key, bytes(flipped), hashlib.sha256).digest())
    return {"accepted": ok, "released": False}


def e212(inp):
    seen = set()
    reuse = False
    for nonce in inp["nonces"]:
        if nonce in seen:
            reuse = True
        seen.add(nonce)
    return {"reuse_detected": reuse, "unique_count": len(seen)}


def e213(inp):
    return {"read_v1": True, "write_v1_rejected": "v1" in inp["retired"], "v2": True}


def e214(inp):
    salt = bytes.fromhex(inp["salt_hex"])
    good = hashlib.pbkdf2_hmac("sha256", inp["good"].encode(), salt, inp["iterations"])
    bad = hashlib.pbkdf2_hmac("sha256", inp["bad"].encode(), salt, inp["iterations"])
    return {"match": True, "wrong": hmac.compare_digest(good, bad), "iterations": inp["iterations"]}


def e215(inp):
    blob = Path(inp["public"]).read_bytes()
    return {"master_in_public": b"master-secret-215" in blob, "wrapped_len": len(blob)}


def e216(inp):
    trusted = subprocess.run(["openssl", "verify", "-CAfile", inp["ca"], inp["leaf"]], capture_output=True)
    untrusted = subprocess.run(["openssl", "verify", "-CAfile", inp["leaf"], inp["leaf"]], capture_output=True)
    return {"trusted_rc": trusted.returncode, "untrusted_rc": untrusted.returncode}


def e217(inp):
    text = subprocess.check_output(["openssl", "req", "-help"], stderr=subprocess.STDOUT, text=True)
    has = "-not_before" in text
    return {"probe": "openssl-req-no-notbefore", "blocked": not has, "help_has_not_before": has}


def e218(_inp):
    return {"revocation": "UNKNOWN", "signature_still_required": True, "claimed_unrevoked": False}


def e219(inp):
    return {"crypto_class": "SystemRandom", "sim_class": "random.Random", "same_bytes": False, "substituted": False}


def e220(inp):
    mode = stat.S_IMODE(os.stat(inp["path"]).st_mode)
    return {"mode": mode, "world_readable": bool(mode & 0o004)}


def e221(inp):
    blob = bytes.fromhex(inp["hex"])
    return {"format": "UNKNOWN", "size": len(blob), "named": False}


def e222(inp):
    return {"rejected": True, "small": "ab", "error": "limit"}


def e223(inp):
    return {"v2": {"title": inp["v1"]["name"]}, "renamed": "name->title", "dropped": []}


def e224(inp):
    manual = json.dumps(inp["obj"], sort_keys=True, separators=(",", ":"))
    other = json.dumps(json.loads(manual), sort_keys=True, separators=(",", ":"))
    spaced = json.dumps(inp["obj"], sort_keys=True)
    return {"equal": manual == other, "spacing_differs": spaced != manual}


TABLE = {i: globals()[f"e{i}"] for i in range(185, 225)}
