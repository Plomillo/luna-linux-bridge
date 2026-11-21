"""Independent expectations for cases 145-184. Does not import libw."""
from __future__ import annotations

import gzip
import os
import stat
import subprocess
import unicodedata
from pathlib import Path

import fixtures
import libo


def expect(n: int, inp: dict) -> dict:
    return TABLE[n](inp)


def e145(inp):
    values = [libo.bits_to_int(b) for b in inp["bits"]]
    recovered = [libo.int_to_bits(v, len(b)) for v, b in zip(values, inp["bits"])]
    rejected = False
    try:
        libo.bits_to_int(inp["negative"])
    except ValueError:
        rejected = True
    return {"values": values, "recovered": recovered, "negative_rejected": rejected}


def e146(_inp):
    def sadd(a, b):
        raw = a + b
        return raw, raw < -128 or raw > 127
    def uadd(a, b):
        raw = a + b
        return raw, raw > 255
    pairs = [(127, 1), (-128, -1), (20, -5)]
    signed = [sadd(a, b) for a, b in pairs]
    unsigned = [uadd(a, b) for a, b in ((250, 10), (1, 2))]
    return {
        "signed_values": [v for v, _ in signed],
        "signed_overflow": [o for _, o in signed],
        "unsigned_values": [v for v, _ in unsigned],
        "unsigned_overflow": [o for _, o in unsigned],
        "ranges": [-128, 127, 0, 255],
    }


def e147(inp):
    blob = bytes.fromhex(inp["bytes"])
    le = int.from_bytes(blob, "little")
    be = int.from_bytes(blob, "big")
    return {"le": le, "be": be, "distinct": le != be, "bytes": blob.hex()}


def e148(inp):
    word, mask, value, width = inp["word"], inp["mask"], inp["value"], inp["width"]
    out = (word & ~mask) | (value & mask)
    return {"out": out, "untouched": (out & ~mask) == (word & ~mask), "changed": (out & mask) == (value & mask),
            "zero_mask_identity": (word & ~0) == word}


def e149(inp):
    n, k, bits = inp["n"], inp["k"], inp["bits"]
    mask = (1 << bits) - 1
    logical = (n & mask) >> k
    sign = (n >> (bits - 1)) & 1
    arith = logical if sign == 0 else (logical | (((1 << k) - 1) << (bits - k)))
    return {"logical": logical & mask, "arithmetic": arith & mask, "sign": sign}


def e150(inp):
    raw = inp["a"] + inp["b"]
    overflow = raw > 255
    stored = inp["a"] if overflow and inp["policy"] == "REJECT" else raw
    return {"detected": overflow, "stored": stored, "raw": raw}


def e151(_inp):
    return {"r17": 17 % 5, "rneg": (-1) % 5, "equiv": (5 * 9 + 2) % 5, "zero_mod_rejected": True}


def e152(inp):
    enc = [libo.to_base(n, 3) for n in inp["nums"]]
    dec = [libo.from_base(s, 3) for s in enc]
    return {"encoded": enc, "decoded": dec}


def e153(inp):
    enc = [libo.to_balanced(n) for n in inp["nums"]]
    dec = [libo.from_balanced(s) for s in enc]
    return {"encoded": enc, "decoded": dec}


def e154(inp):
    chain = inp["n"]
    for base in inp["bases"]:
        chain = libo.from_base(libo.to_base(chain, base), base)
    return {"result": chain}


def e155(inp):
    bad = []
    for sample, base in inp["samples"]:
        try:
            libo.from_base(sample, base)
            bad.append(False)
        except ValueError:
            bad.append(True)
    return {"rejected": bad}


def e156(inp):
    s = inp["text"]
    raw = s.encode("utf-8")
    return {"cps": [ord(ch) for ch in s], "utf8_hex": raw.hex(), "n_cp": len(s), "n_bytes": len(raw)}


def e157(inp):
    accepted = []
    for hexed in inp["hex"]:
        try:
            bytes.fromhex(hexed).decode("utf-8")
            accepted.append(True)
        except UnicodeDecodeError:
            accepted.append(False)
    return {"accepted": accepted}


def e158(inp):
    def one(units):
        if len(units) >= 2 and 0xD800 <= units[0] <= 0xDBFF and 0xDC00 <= units[1] <= 0xDFFF:
            cp = 0x10000 + ((units[0] - 0xD800) << 10) + (units[1] - 0xDC00)
            return {"ok": True, "cp": cp}
        if any(0xD800 <= u <= 0xDFFF for u in units):
            return {"ok": False, "cp": -1}
        if len(units) == 1:
            return {"ok": True, "cp": units[0]}
        return {"ok": False, "cp": -1}
    a, b, c, d = [one(u) for u in inp["units"]]
    return {"a": a, "b": b, "c": c, "d": d}


def e159(inp):
    text = chr(inp["cp"])
    u32 = text.encode("utf-32-le")
    invalid = False
    try:
        chr(0x110000)
    except ValueError:
        invalid = True
    return {"u8": text.encode("utf-8").hex(), "u16": text.encode("utf-16-le").hex(), "u32": u32.hex(),
            "roundtrip": u32.decode("utf-32-le") == text, "invalid_rejected": invalid}


def e160(inp):
    s = inp["text"]
    forms = {k: unicodedata.normalize(k.upper(), s) for k in ("nfc", "nfd", "nfkc", "nfkd")}
    return {**forms, "nfc_ne_nfd": forms["nfc"] != forms["nfd"], "nfkc_ne_nfc": forms["nfkc"] != forms["nfc"]}


def e161(inp):
    s = inp["text"]
    clusters = 0
    for ch in s:
        extends = unicodedata.category(ch) in {"Mn", "Mc", "Me"} or ch == "\u200d"
        if clusters == 0 or not extends:
            clusters += 1
    return {"codepoints": len(s), "graphemes_limited": clusters, "uax29": "NOT_CLAIMED"}


def e162(inp):
    blob = bytes.fromhex(inp["hex"])
    declared = blob.decode(inp["declared"])
    try:
        blob.decode("utf-8")
        flag = "DECODED"
    except UnicodeDecodeError:
        flag = "UNCERTAIN"
    return {"declared_text": declared, "undeclared": flag, "invented_encoding": False}


def e163(_inp):
    data = b"\x00\xffL"
    enc = data.hex()
    odd = True
    try:
        bytes.fromhex("abc")
    except ValueError:
        odd = True
    alpha = True
    try:
        int("zz", 16)
        alpha = False
    except ValueError:
        alpha = True
    return {"hex": enc, "roundtrip": bytes.fromhex(enc) == data, "odd_rejected": odd, "alpha_rejected": alpha}


def e164(inp):
    data = inp["text"].encode()
    enc = libo.b32_encode(data)
    bad = False
    try:
        libo.b32_decode("!!!!")
    except Exception:
        bad = True
    return {"encoded": enc, "roundtrip": libo.b32_decode(enc) == data, "bad_rejected": bad, "has_padding": enc.endswith("=")}


def e165(_inp):
    data = bytes(range(50))
    enc = libo.b64_encode(data)
    return {"encoded": enc, "equal": libo.b64_decode(enc) == data}


def e166(inp):
    data = bytes.fromhex(inp["hex"])
    std = libo.b64_encode(data, False)
    url = libo.b64_encode(data, True)
    return {"std": std, "url": url, "differ": std != url, "roundtrip": libo.b64_decode(url, True) == data}


def e167(inp):
    data = bytes((i * 7 + 3) & 0xFF for i in range(inp["length"]))
    full = libo.b64_encode(data)
    buf = b""
    parts = []
    for i in range(0, len(data), inp["chunk"]):
        buf += data[i : i + inp["chunk"]]
        take = len(buf) - (len(buf) % 3)
        if take:
            parts.append(libo.b64_encode(buf[:take]))
            buf = buf[take:]
    if buf:
        parts.append(libo.b64_encode(buf))
    streamed = "".join(parts)
    return {"stream": streamed, "full": full, "equal": streamed == full, "parts": len(parts)}


def e168(inp):
    results = []
    for sample in inp["samples"]:
        try:
            libo.b64_decode(sample)
            results.append("accept")
        except Exception:
            results.append("reject")
    return {"results": results}


def e169(inp):
    def structural(s: str) -> bool:
        try:
            libo.b64_decode(s)
            return True
        except Exception:
            return False
    return {"false_friend_is_b64": structural(inp["false_friend"]), "real_is_b64": structural(inp["real"])}


def e170(_inp):
    elf = open("/bin/ls", "rb").read(8)
    return {
        "png": fixtures.PNG_MIN[:8] == b"\x89PNG\r\n\x1a\n",
        "pdf": fixtures.PDF_MIN.startswith(b"%PDF-"),
        "elf": elf[:4] == b"\x7fELF",
        "gzip": gzip.compress(b"a")[:2] == b"\x1f\x8b",
    }


def e171(inp):
    blob = Path(inp["path"]).read_bytes()
    kind = "png" if blob[:8] == b"\x89PNG\r\n\x1a\n" else "unknown"
    return {"detected": kind, "contradiction": Path(inp["path"]).suffix == ".txt" and kind == "png"}


def e172(_inp):
    zero = libo.shannon_milli(b"\x00" * 64)
    mixed = libo.shannon_milli(bytes(range(256)))
    return {"zero_milli": zero, "mixed_milli": mixed, "encrypted_claim": False}


def e173(inp):
    blob = Path(inp["path"]).read_bytes()
    original = libo.sha256(blob)
    flipped = bytearray(blob)
    flipped[inp["flip_index"]] ^= 0x01
    changed = libo.sha256(bytes(flipped))
    return {"same": original == changed, "original": original, "changed": changed}


def e174(_inp):
    a = sum(b"abc") & 0xFFFF
    b = sum(b"abd") & 0xFFFF
    return {"a": a, "b": b, "detected": a != b}


def e175(_inp):
    a = libo.crc32(b"intact")
    b = libo.crc32(b"intacu")
    return {"a": a, "b": b, "detected": a != b, "cryptographic": False}


def e176(inp):
    return {"sha256": libo.sha256_stdlib_crosscheck(inp["text"].encode())}


def e177(_inp):
    return {"equal_same": True, "equal_other": False, "historical_identity": "NOT_PROVEN"}


def e178(_inp):
    digest = libo.sha256(b"artifact-178")
    altered = libo.sha256(b"artifact-179")
    return {"digest": digest, "provenance": "fixture-178", "altered_equal": altered == digest}


def e179(inp):
    good = subprocess.run(["openssl", "pkeyutl", "-verify", "-inkey", inp["pub"], "-pubin", "-rawin", "-in", inp["data"], "-sigfile", inp["sig"]], capture_output=True)
    mode = stat.S_IMODE(os.stat(inp["key"]).st_mode)
    return {"verify_rc": good.returncode, "key_mode": mode, "private_in_facts": False}


def e180(inp):
    bad = subprocess.run(["openssl", "pkeyutl", "-verify", "-inkey", inp["pub"], "-pubin", "-rawin", "-in", inp["data"], "-sigfile", inp["sig"]], capture_output=True)
    return {"verify_rc": bad.returncode, "authenticated": False}


def e181(_inp):
    return {"same_log": "MATCH", "other_log": "MISMATCH", "same_leaked": False, "other_leaked": False}


def e182(inp):
    return {"mode": 0o600, "used": True, "removed": True, "logged_secret": False}


def e183(inp):
    original = inp["text"]
    step2 = original.encode().hex()
    back = bytes.fromhex(step2).decode()
    tampered = ("0" if step2[0] != "0" else "1") + step2[1:]
    changed = bytes.fromhex(tampered).decode(errors="replace")
    return {"roundtrip": back, "stage_changed": "hex", "tampered_equals_original": changed == original}


def e184(inp):
    return {"empty_roundtrip": True, "over_limit_rejected": inp["offered"] > inp["limit"], "silent_truncation": False}


TABLE = {i: globals()[f"e{i}"] for i in range(145, 185)}
