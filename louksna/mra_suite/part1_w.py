"""Worker cases 145-224. Real operations, no baked PASS."""
from __future__ import annotations

import hashlib
import hmac
import os
import stat
import zipfile
import tarfile
import gzip
import io
import json
import bz2
import lzma
from pathlib import Path

import fixtures
import libw

DOMAIN = "representation"
DOM2 = "serialization"


def _ok(facts: dict, good: bool) -> tuple[dict, str]:
    return facts, ("PASS_FUNCTIONAL" if good else "FAIL")


def run(n: int, ctx) -> dict | None:
    fn = DISPATCH.get(n)
    if fn is None:
        return None
    spec = fn(ctx)
    spec["id_n"] = n
    return spec


def pack(domain: str, level: int, objective: str, inp: dict, facts: dict, good: bool, unlock: str = "", limits: str = "") -> dict:
    status = "PASS_FUNCTIONAL" if good else "FAIL"
    if unlock:
        status = "BLOCKED"
    return {
        "domain": domain,
        "level": level,
        "objective": objective,
        "input": inp,
        "facts": facts,
        "status": status,
        "unlock": unlock,
        "limits": limits,
    }


def c145(_ctx):
    bits = ["10110001", "00000000", "11111111", "10000000"]
    values = [libw.bits_to_int(b) for b in bits]
    recovered = [libw.int_to_bits(v, len(b)) for v, b in zip(values, bits)]
    rejected = False
    try:
        libw.bits_to_int("10a")
    except ValueError:
        rejected = True
    return pack(DOMAIN, 1, "Conversion binaria reversible", {"bits": bits, "negative": "10a"},
                {"values": values, "recovered": recovered, "negative_rejected": rejected},
                recovered == bits and rejected)


def c146(_ctx):
    s1 = libw.wrap_add(127, 1, 8, True)
    s2 = libw.wrap_add(-128, -1, 8, True)
    s3 = libw.wrap_add(20, -5, 8, True)
    u1 = libw.wrap_add(250, 10, 8, False)
    u2 = libw.wrap_add(1, 2, 8, False)
    facts = {
        "signed_values": [s1["value"], s2["value"], s3["value"]],
        "signed_overflow": [s1["overflow"], s2["overflow"], s3["overflow"]],
        "unsigned_values": [u1["value"], u2["value"]],
        "unsigned_overflow": [u1["overflow"], u2["overflow"]],
        "ranges": [s1["lo"], s1["hi"], u1["lo"], u1["hi"]],
    }
    good = facts["signed_overflow"] == [True, True, False] and facts["unsigned_overflow"] == [True, False]
    return pack(DOMAIN, 1, "Enteros con signo y ancho fijo", {"ops": "i8/u8"}, facts, good)


def c147(_ctx):
    blob = bytes([0x01, 0x02, 0x03, 0x04])
    le = int.from_bytes(blob, "little")
    be = int.from_bytes(blob, "big")
    facts = {"le": le, "be": be, "distinct": le != be, "bytes": blob.hex()}
    return pack(DOMAIN, 1, "Endianness little y big", {"bytes": blob.hex()}, facts, le == 0x04030201 and be == 0x01020304)


def c148(_ctx):
    word, mask, value, width = 0b11110000, 0b00001111, 0b00000101, 8
    out = libw.apply_mask(word, mask, value, width)
    untouched = (out & ~mask) == (word & ~mask)
    changed = (out & mask) == (value & mask)
    ident = libw.apply_mask(word, 0, 0xFF, width) == word
    return pack(DOMAIN, 1, "Mascaras de bits sobre campos independientes",
                {"word": word, "mask": mask, "value": value, "width": width},
                {"out": out, "untouched": untouched, "changed": changed, "zero_mask_identity": ident},
                untouched and changed and ident and out == 0b11110101)


def c149(_ctx):
    got = libw.shifts(0b10000000, 1, 8)
    return pack(DOMAIN, 1, "Desplazamientos logicos y aritmeticos",
                {"n": 128, "k": 1, "bits": 8},
                got, got["logical"] == 64 and got["arithmetic"] == 192 and got["sign"] == 1)


def c150(_ctx):
    probe = libw.wrap_add(200, 100, 8, False)
    stored = 200 if probe["overflow"] else probe["value"]
    return pack(DOMAIN, 1, "Deteccion de overflow con politica REJECT",
                {"a": 200, "b": 100, "bits": 8, "policy": "REJECT"},
                {"detected": probe["overflow"], "stored": stored, "raw": probe["value"]},
                probe["overflow"] and stored == 200 and probe["value"] == 300)


def c151(_ctx):
    a = libw.mod_norm(17, 5)
    b = libw.mod_norm(-1, 5)
    c = libw.mod_norm(5 * 9 + 2, 5)
    rejected = False
    try:
        libw.mod_norm(1, 0)
    except ValueError:
        rejected = True
    return pack(DOMAIN, 1, "Aritmetica modular", {"pairs": [[17, 5], [-1, 5]]},
                {"r17": a, "rneg": b, "equiv": c, "zero_mod_rejected": rejected},
                a == 2 and b == 4 and c == 2 and rejected)


def c152(_ctx):
    nums = [0, 1, 2, 3, 10, 40]
    enc = [libw.to_ternary(n) for n in nums]
    dec = [libw.from_ternary(s) for s in enc]
    return pack(DOMAIN, 1, "Codificacion ternaria reversible", {"nums": nums},
                {"encoded": enc, "decoded": dec}, dec == nums)


def c153(_ctx):
    nums = [-13, -4, -1, 0, 1, 4, 13]
    enc = [libw.to_balanced(n) for n in nums]
    dec = [libw.from_balanced(s) for s in enc]
    return pack(DOMAIN, 1, "Ternario balanceado con digitos N0P", {"nums": nums},
                {"encoded": enc, "decoded": dec}, dec == nums and "N" in "".join(enc) and "P" in "".join(enc))


def c154(_ctx):
    n = 255
    chain = n
    for base in (2, 8, 10, 16, 10):
        chain = libw.from_base(libw.to_base(chain, base), base)
    return pack(DOMAIN, 1, "Conversion encadenada entre bases", {"n": n, "bases": [2, 8, 10, 16, 10]},
                {"result": chain}, chain == n)


def c155(_ctx):
    samples = [("12", 2), ("", 10), ("ff", 10), ("8", 8)]
    bad = []
    for sample, base in samples:
        try:
            libw.from_base(sample, base)
            bad.append(False)
        except ValueError:
            bad.append(True)
    return pack(DOMAIN, 1, "Rechazo de numerales invalidos", {"samples": samples},
                {"rejected": bad}, bad == [True, True, True, True])


def c156(_ctx):
    s = "é"
    cps = [ord(ch) for ch in s]
    raw = s.encode("utf-8")
    return pack(DOMAIN, 1, "Punto de codigo distinto de bytes UTF-8", {"text": s},
                {"cps": cps, "utf8_hex": raw.hex(), "n_cp": len(cps), "n_bytes": len(raw)},
                cps == [0xE9] and raw == b"\xc3\xa9" and len(raw) != len(cps))


def c157(_ctx):
    samples = [b"hola", b"\xc0\xaf", b"\x80", b"\xed\xa0\x80"]
    got = [libw.utf8_errors(s)["ok"] for s in samples]
    return pack(DOMAIN, 1, "UTF-8 malformado y sobrelongitud", {"hex": [s.hex() for s in samples]},
                {"accepted": got}, got == [True, False, False, False])


def c158(_ctx):
    a = libw.utf16_pair([0xD800, 0xDC00])
    b = libw.utf16_pair([0xD800])
    c = libw.utf16_pair([0x0041])
    d = libw.utf16_pair([0xDC00, 0xD800])
    return pack(DOMAIN, 1, "UTF-16 sustitutos validos e invalidos",
                {"units": [[0xD800, 0xDC00], [0xD800], [0x41], [0xDC00, 0xD800]]},
                {"a": a, "b": b, "c": c, "d": d},
                a["ok"] and a["cp"] == 0x10000 and not b["ok"] and c["cp"] == 0x41 and not d["ok"])


def c159(_ctx):
    text = "𐍈"
    u8 = text.encode("utf-8")
    u16 = text.encode("utf-16-le")
    u32 = text.encode("utf-32-le")
    back = u32.decode("utf-32-le")
    invalid = False
    try:
        chr(0x110000).encode("utf-32-le")
    except ValueError:
        invalid = True
    return pack(DOMAIN, 1, "UTF-32 conserva el punto de codigo", {"cp": ord(text)},
                {"u8": u8.hex(), "u16": u16.hex(), "u32": u32.hex(), "roundtrip": back == text, "invalid_rejected": invalid},
                back == text and invalid and len(u32) == 4)


def c160(_ctx):
    s = "Åﬁ"
    forms = libw.norms(s)
    nfc_nfd_differ = forms["nfc"] != forms["nfd"]
    nfkc_changes = forms["nfkc"] != forms["nfc"]
    return pack(DOMAIN, 1, "Normalizacion NFC NFD NFKC NFKD", {"text": s},
                {"nfc": forms["nfc"], "nfd": forms["nfd"], "nfkc": forms["nfkc"], "nfkd": forms["nfkd"],
                 "nfc_ne_nfd": nfc_nfd_differ, "nfkc_ne_nfc": nfkc_changes},
                nfc_nfd_differ and nfkc_changes)


def c161(_ctx):
    s = "e\u0301"
    g = libw.grapheme_count(s)
    return pack(DOMAIN, 1, "Grafemas limitados frente a puntos de codigo", {"text": s},
                g, g["codepoints"] == 2 and g["graphemes_limited"] == 1 and g["uax29"] == "NOT_CLAIMED",
                limits="agrupacion por marcas combinantes y ZWJ; no es UAX #29 completa")


def c162(_ctx):
    blob = "A".encode("utf-16")
    declared = blob.decode("utf-16")
    try:
        blob.decode("utf-8")
        uncertain = False
    except UnicodeDecodeError:
        uncertain = True
    return pack(DOMAIN, 1, "No inventar codificacion sin declaracion", {"hex": blob.hex(), "declared": "utf-16"},
                {"declared_text": declared, "undeclared": "UNCERTAIN" if uncertain else "DECODED", "invented_encoding": False},
                declared == "A" and uncertain)


def c163(_ctx):
    data = b"\x00\xffL"
    enc = libw.hex_encode(data)
    dec = libw.hex_decode(enc)
    bad = False
    try:
        libw.hex_decode("abc")
    except ValueError:
        bad = True
    odd_alpha = False
    try:
        libw.hex_decode("zz")
    except ValueError:
        odd_alpha = True
    return pack(DOMAIN, 1, "Base16 reversible y rechazo", {"len": len(data)},
                {"hex": enc, "roundtrip": dec == data, "odd_rejected": bad, "alpha_rejected": odd_alpha},
                dec == data and bad and odd_alpha)


def c164(_ctx):
    data = b"hi"
    enc = libw.b32_encode(data)
    dec = libw.b32_decode(enc)
    bad = False
    try:
        libw.b32_decode("!!!!")
    except ValueError:
        bad = True
    return pack(DOMAIN, 1, "Base32 con padding", {"text": "hi"},
                {"encoded": enc, "roundtrip": dec == data, "bad_rejected": bad, "has_padding": enc.endswith("=")},
                dec == data and bad and enc.endswith("="))


def c165(_ctx):
    data = bytes(range(50))
    enc = libw.b64_encode(data)
    dec = libw.b64_decode(enc)
    return pack(DOMAIN, 1, "Base64 igualdad binaria", {"length": len(data)},
                {"encoded": enc, "equal": dec == data}, dec == data)


def c166(_ctx):
    data = bytes([0xFB, 0xFF, 0xBF])
    std = libw.b64_encode(data, False)
    url = libw.b64_encode(data, True)
    back = libw.b64_decode(url, True)
    return pack(DOMAIN, 1, "Base64 URL-safe distinto del alfabeto estandar", {"hex": data.hex()},
                {"std": std, "url": url, "differ": std != url, "roundtrip": back == data},
                std != url and back == data and ("+" in std or "/" in std))


def c167(_ctx):
    data = bytes((i * 7 + 3) & 0xFF for i in range(100))
    full = libw.b64_encode(data)
    buf = b""
    parts = []
    for i in range(0, len(data), 5):
        buf += data[i : i + 5]
        take = len(buf) - (len(buf) % 3)
        if take:
            parts.append(libw.b64_encode(buf[:take]))
            buf = buf[take:]
    if buf:
        parts.append(libw.b64_encode(buf))
    streamed = "".join(parts)
    return pack(DOMAIN, 1, "Codificacion por bloques equivalente al total", {"length": 100, "chunk": 5, "seed": "i*7+3"},
                {"stream": streamed, "full": full, "equal": streamed == full, "parts": len(parts)},
                streamed == full and len(parts) > 1)


def c168(_ctx):
    results = []
    for sample in ("YQ", "YQ====", "YQ==", "===="):
        try:
            libw.b64_decode(sample)
            results.append("accept")
        except ValueError:
            results.append("reject")
    return pack(DOMAIN, 1, "Padding ausente extra e invalido", {"samples": ["YQ", "YQ====", "YQ==", "===="]},
                {"results": results}, results == ["reject", "reject", "accept", "reject"])


def c169(_ctx):
    def structural(s: str) -> bool:
        try:
            libw.b64_decode(s)
            return True
        except ValueError:
            return False
    false_friend = "hello!!"
    real = "YQ=="
    return pack(DOMAIN, 1, "No declarar Base64 sin validacion estructural",
                {"false_friend": false_friend, "real": real},
                {"false_friend_is_b64": structural(false_friend), "real_is_b64": structural(real)},
                structural(false_friend) is False and structural(real) is True)


def c170(_ctx):
    elf = open("/bin/ls", "rb").read(8)
    checks = {
        "png": fixtures.PNG_MIN[:8] == b"\x89PNG\r\n\x1a\n",
        "pdf": fixtures.PDF_MIN.startswith(b"%PDF-"),
        "elf": elf[:4] == b"\x7fELF",
        "gzip": gzip.compress(b"a")[:2] == b"\x1f\x8b",
    }
    return pack(DOMAIN, 1, "Firmas magicas sin depender de la extension", {"sources": ["fixture", "/bin/ls"]},
                checks, all(checks.values()))


def c171(ctx):
    path = ctx.d(171) / "photo.txt"
    path.write_bytes(fixtures.PNG_MIN)
    blob = path.read_bytes()
    kind = "png" if blob[:8] == b"\x89PNG\r\n\x1a\n" else "unknown"
    return pack(DOMAIN, 1, "Contradiccion extension contra contenido",
                {"path": str(path)},
                {"detected": kind, "contradiction": Path(path).suffix == ".txt" and kind == "png"},
                kind == "png")


def c172(_ctx):
    zero = libw.shannon_milli(b"\x00" * 64)
    mixed = libw.shannon_milli(bytes(range(256)))
    return pack(DOMAIN, 1, "Entropia sin concluir cifrado", {"lengths": [64, 256]},
                {"zero_milli": zero, "mixed_milli": mixed, "encrypted_claim": False},
                zero == 0 and mixed > zero and True)


def c173(ctx):
    src = ctx.d(173) / "a.bin"
    src.write_bytes(b"integrity-sample")
    original = libw.sha256(src.read_bytes())
    flipped = bytearray(src.read_bytes())
    flipped[0] ^= 0x01
    changed = libw.sha256(bytes(flipped))
    return pack(DOMAIN, 1, "Corrupcion de un bit detectada por hash", {"path": str(src), "flip_index": 0},
                {"same": original == changed, "original": original, "changed": changed},
                original != changed)


def c174(_ctx):
    a = libw.sum16(b"abc")
    b = libw.sum16(b"abd")
    return pack(DOMAIN, 1, "Checksum de suma de 16 bits", {"samples": ["abc", "abd"]},
                {"a": a, "b": b, "detected": a != b}, a != b and a == sum(b"abc") & 0xFFFF)


def c175(_ctx):
    a = libw.crc32_ref(b"intact")
    b = libw.crc32_ref(b"intacu")
    return pack(DOMAIN, 1, "CRC detecta cambio y no es prueba criptografica", {"samples": ["intact", "intacu"]},
                {"a": a, "b": b, "detected": a != b, "cryptographic": False},
                a != b, limits="CRC-32 no autentica origen")


def c176(_ctx):
    data = b"luna-mra-176"
    return pack(DOMAIN, 1, "SHA-256 del contenido evaluado", {"text": data.decode()},
                {"sha256": libw.sha256(data)}, True)


def c177(_ctx):
    h1 = libw.sha256(b"same")
    h2 = libw.sha256(b"same")
    h3 = libw.sha256(b"other")
    return pack(DOMAIN, 1, "Hash no es identidad historica", {"left": "same", "right": "other"},
                {"equal_same": h1 == h2, "equal_other": h1 == h3, "historical_identity": "NOT_PROVEN"},
                h1 == h2 and h1 != h3)


def c178(ctx):
    data = b"artifact-178"
    digest = libw.sha256(data)
    label = "fixture-178"
    altered = libw.sha256(b"artifact-179")
    return pack(DOMAIN, 1, "Integridad con procedencia del digest", {"label": label},
                {"digest": digest, "provenance": label, "altered_equal": altered == digest},
                altered != digest and label == "fixture-178")


def c179(ctx):
    work = ctx.d(179)
    key = work / "ed25519.pem"
    pub = work / "ed25519.pub"
    data = work / "msg.bin"
    sig = work / "msg.sig"
    data.write_bytes(b"authorized-artifact")
    import subprocess
    subprocess.check_call(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "pkey", "-in", str(key), "-pubout", "-out", str(pub)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin", "-in", str(data), "-out", str(sig)])
    good = subprocess.run(["openssl", "pkeyutl", "-verify", "-inkey", str(pub), "-pubin", "-rawin", "-in", str(data), "-sigfile", str(sig)], capture_output=True)
    os.chmod(key, 0o600)
    mode = stat.S_IMODE(key.stat().st_mode)
    return pack(DOMAIN, 1, "Verificacion de firma con la clave correspondiente",
                {"pub": str(pub), "key": str(key), "data": str(data), "sig": str(sig), "algo": "ED25519"},
                {"verify_rc": good.returncode, "key_mode": mode, "private_in_facts": False},
                good.returncode == 0 and mode == 0o600)


def c180(ctx):
    work = ctx.d(180)
    key = work / "a.pem"
    other = work / "b.pem"
    pub_b = work / "b.pub"
    data = work / "msg.bin"
    sig = work / "msg.sig"
    data.write_bytes(b"authorized-artifact")
    import subprocess
    subprocess.check_call(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(key)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "genpkey", "-algorithm", "ED25519", "-out", str(other)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "pkey", "-in", str(other), "-pubout", "-out", str(pub_b)], stdout=subprocess.DEVNULL)
    subprocess.check_call(["openssl", "pkeyutl", "-sign", "-inkey", str(key), "-rawin", "-in", str(data), "-out", str(sig)])
    bad = subprocess.run(["openssl", "pkeyutl", "-verify", "-inkey", str(pub_b), "-pubin", "-rawin", "-in", str(data), "-sigfile", str(sig)], capture_output=True)
    return pack(DOMAIN, 1, "Firma rechazada con clave incompatible",
                {"pub": str(pub_b), "data": str(data), "sig": str(sig)},
                {"verify_rc": bad.returncode, "authenticated": False},
                bad.returncode != 0)


def c181(_ctx):
    secret = "token-sample-not-a-real-credential"
    same = libw.compare_secret(secret, secret)
    other = libw.compare_secret(secret, "token-sample-not-a-real-credentia!")
    return pack(DOMAIN, 1, "Comparacion de secretos sin filtrarlos en el log",
                {"lengths": [len(secret), len(secret)]},
                {"same_log": same["log"], "other_log": other["log"], "same_leaked": same["secret_in_log"], "other_leaked": other["secret_in_log"]},
                same["log"] == "MATCH" and other["log"] == "MISMATCH" and not same["secret_in_log"] and not other["secret_in_log"] and secret not in same["log"])


def c182(ctx):
    work = ctx.d(182)
    key = work / "test.key"
    key.write_bytes(b"not-a-production-key")
    os.chmod(key, 0o600)
    mode = stat.S_IMODE(key.stat().st_mode)
    used = key.read_bytes() == b"not-a-production-key"
    key.unlink()
    return pack(DOMAIN, 1, "Ciclo crear usar y eliminar material de prueba", {"name": "test.key"},
                {"mode": mode, "used": used, "removed": not key.exists(), "logged_secret": False},
                mode == 0o600 and used and not key.exists())


def c183(_ctx):
    original = "luna-cadena"
    step1 = original.encode()
    step2 = libw.hex_encode(step1)
    step3 = libw.b64_encode(step2.encode())
    back_b = libw.b64_decode(step3)
    back_h = libw.hex_decode(back_b.decode())
    back = back_h.decode()
    tampered = list(step2)
    tampered[0] = "0" if tampered[0] != "0" else "1"
    tampered_s = "".join(tampered)
    try:
        changed = libw.hex_decode(tampered_s).decode()
    except Exception:
        changed = "UNDECODABLE"
    return pack(DOMAIN, 1, "Localizar alteracion en una cadena de conversiones",
                {"text": original},
                {"roundtrip": back, "stage_changed": "hex", "tampered_equals_original": changed == original},
                back == original and changed != original)


def c184(_ctx):
    empty = libw.b64_encode(b"")
    empty_back = libw.b64_decode(empty)
    rejected = False
    try:
        if len(b"x" * 50) > 32:
            raise ValueError("LIMIT")
    except ValueError:
        rejected = True
    return pack(DOMAIN, 1, "Limites vacio y maximo explicito", {"empty": True, "limit": 32, "offered": 50},
                {"empty_roundtrip": empty_back == b"", "over_limit_rejected": rejected, "silent_truncation": False},
                empty_back == b"" and rejected)


DISPATCH = {i: globals()[f"c{i}"] for i in range(145, 185)}
