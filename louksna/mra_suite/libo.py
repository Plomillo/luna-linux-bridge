"""Oracle reference algorithms. Must not import libw or the worker package."""
from __future__ import annotations

import base64
import hashlib
import math
import struct
import unicodedata
import zlib
from collections import Counter


def bits_to_int(s: str) -> int:
    if not s or set(s) - {"0", "1"}:
        raise ValueError("BIN_GRAMMAR")
    return sum(1 << (len(s) - 1 - i) for i, c in enumerate(s) if c == "1")


def int_to_bits(n: int, width: int) -> str:
    if n < 0 or width < 1 or n >= 2**width:
        raise ValueError("BIN_RANGE")
    return format(n, "0{}b".format(width))


def to_base(n: int, base: int) -> str:
    if not 2 <= base <= 16 or n < 0:
        raise ValueError("BASE")
    alphabet = "0123456789abcdef"
    if n == 0:
        return "0"
    chars = []
    x = n
    while x:
        x, r = divmod(x, base)
        chars.append(alphabet[r])
    return "".join(reversed(chars))


def from_base(s: str, base: int) -> int:
    alphabet = "0123456789abcdef"
    if not 2 <= base <= 16 or not s:
        raise ValueError("BASE")
    n = 0
    for ch in s.lower():
        v = alphabet.find(ch)
        if v < 0 or v >= base:
            raise ValueError("DIGIT")
        n = n * base + v
    return n


def to_balanced(n: int) -> str:
    # powers search, not the divmod rewrite used by the worker
    if n == 0:
        return "0"
    width = 1
    while (3**width - 1) // 2 < abs(n):
        width += 1
    digits = []
    remain = n
    for exp in range(width - 1, -1, -1):
        place = 3**exp
        best = min((-1, 0, 1), key=lambda d: abs(remain - d * place))
        digits.append({-1: "N", 0: "0", 1: "P"}[best])
        remain -= best * place
    if remain != 0:
        raise ValueError("BAL")
    return "".join(digits).lstrip("0") or "0"


def from_balanced(s: str) -> int:
    vals = {"N": -1, "0": 0, "P": 1}
    total = 0
    power = 1
    for ch in reversed(s):
        if ch not in vals:
            raise ValueError("BAL")
        total += vals[ch] * power
        power *= 3
    return total


def b64_decode(s: str, url: bool = False) -> bytes:
    t = s.strip()
    if url:
        t = t.replace("-", "+").replace("_", "/")
        t += "=" * ((4 - len(t) % 4) % 4)
    return base64.b64decode(t, validate=True)


def b64_encode(data: bytes, url: bool = False) -> str:
    if url:
        return base64.urlsafe_b64encode(data).decode().rstrip("=")
    return base64.b64encode(data).decode()


def b32_encode(data: bytes) -> str:
    return base64.b32encode(data).decode()


def b32_decode(s: str) -> bytes:
    return base64.b32decode(s, casefold=False)


def crc32(data: bytes) -> int:
    return zlib.crc32(data) & 0xFFFFFFFF


_K = [
    0x428A2F98, 0x71374491, 0xB5C0FBCF, 0xE9B5DBA5, 0x3956C25B, 0x59F111F1, 0x923F82A4, 0xAB1C5ED5,
    0xD807AA98, 0x12835B01, 0x243185BE, 0x550C7DC3, 0x72BE5D74, 0x80DEB1FE, 0x9BDC06A7, 0xC19BF174,
    0xE49B69C1, 0xEFBE4786, 0x0FC19DC6, 0x240CA1CC, 0x2DE92C6F, 0x4A7484AA, 0x5CB0A9DC, 0x76F988DA,
    0x983E5152, 0xA831C66D, 0xB00327C8, 0xBF597FC7, 0xC6E00BF3, 0xD5A79147, 0x06CA6351, 0x14292967,
    0x27B70A85, 0x2E1B2138, 0x4D2C6DFC, 0x53380D13, 0x650A7354, 0x766A0ABB, 0x81C2C92E, 0x92722C85,
    0xA2BFE8A1, 0xA81A664B, 0xC24B8B70, 0xC76C51A3, 0xD192E819, 0xD6990624, 0xF40E3585, 0x106AA070,
    0x19A4C116, 0x1E376C08, 0x2748774C, 0x34B0BCB5, 0x391C0CB3, 0x4ED8AA4A, 0x5B9CCA4F, 0x682E6FF3,
    0x748F82EE, 0x78A5636F, 0x84C87814, 0x8CC70208, 0x90BEFFFA, 0xA4506CEB, 0xBEF9A3F7, 0xC67178F2,
]


def _rotr(x: int, n: int) -> int:
    return ((x >> n) | (x << (32 - n))) & 0xFFFFFFFF


def sha256(data: bytes) -> str:
    h = [0x6A09E667, 0xBB67AE85, 0x3C6EF372, 0xA54FF53A, 0x510E527F, 0x9B05688C, 0x1F83D9AB, 0x5BE0CD19]
    bitlen = len(data) * 8
    buf = data + b"\x80"
    while (len(buf) % 64) != 56:
        buf += b"\x00"
    buf += bitlen.to_bytes(8, "big")
    for off in range(0, len(buf), 64):
        w = list(struct.unpack(">16I", buf[off : off + 64]))
        for i in range(16, 64):
            s0 = _rotr(w[i - 15], 7) ^ _rotr(w[i - 15], 18) ^ (w[i - 15] >> 3)
            s1 = _rotr(w[i - 2], 17) ^ _rotr(w[i - 2], 19) ^ (w[i - 2] >> 10)
            w.append((w[i - 16] + s0 + w[i - 7] + s1) & 0xFFFFFFFF)
        a, b, c, d, e, f, g, hh = h
        for i in range(64):
            s1 = _rotr(e, 6) ^ _rotr(e, 11) ^ _rotr(e, 25)
            ch = (e & f) ^ ((~e & 0xFFFFFFFF) & g)
            t1 = (hh + s1 + ch + _K[i] + w[i]) & 0xFFFFFFFF
            s0 = _rotr(a, 2) ^ _rotr(a, 13) ^ _rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = (s0 + maj) & 0xFFFFFFFF
            hh, g, f, e, d, c, b, a = g, f, e, (d + t1) & 0xFFFFFFFF, c, b, a, (t1 + t2) & 0xFFFFFFFF
        h = [(x + y) & 0xFFFFFFFF for x, y in zip(h, (a, b, c, d, e, f, g, hh))]
    return "".join(f"{x:08x}" for x in h)


def shannon_milli(data: bytes) -> int:
    if not data:
        return 0
    n = len(data)
    buckets = [0] * 256
    for b in data:
        buckets[b] += 1
    h = 0.0
    for v in buckets:
        if v:
            p = v / n
            h -= p * math.log2(p)
    return int(round(h * 1000))


def elf_header(blob: bytes) -> dict:
    if blob[:4] != b"\x7fELF":
        raise ValueError("ELF")
    ei_class, ei_data = blob[4], blob[5]
    endian = "<" if ei_data == 1 else ">"
    e_type, e_machine = struct.unpack(endian + "HH", blob[16:20])
    types = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}
    return {
        "class": "ELF32" if ei_class == 1 else "ELF64",
        "endian": "LE" if ei_data == 1 else "BE",
        "type": types.get(e_type, str(e_type)),
        "machine": e_machine,
    }


def pe_header(blob: bytes) -> dict:
    lfanew = struct.unpack_from("<I", blob, 0x3C)[0]
    if blob[lfanew : lfanew + 4] != b"PE\x00\x00":
        raise ValueError("PE")
    machine, sections = struct.unpack_from("<HH", blob, lfanew + 4)
    return {"machine": machine, "sections": sections, "format": "PE"}


def macho_header(blob: bytes) -> dict:
    magic, cputype, _sub, filetype, ncmds, _sz, _flags, _res = struct.unpack("<8I", blob[:32])
    if magic != 0xFEEDFACF:
        raise ValueError("MAGIC")
    return {"format": "MACHO64", "cputype": cputype, "filetype": filetype, "ncmds": ncmds}


def class_header(blob: bytes) -> dict:
    magic, minor, major = struct.unpack(">IHH", blob[:8])
    if magic != 0xCAFEBABE:
        raise ValueError("CLASS")
    return {"format": "JVM_CLASS", "minor": minor, "major": major}


def wasm_summary(blob: bytes) -> dict:
    if blob[:4] != b"\x00asm":
        raise ValueError("WASM")
    version = struct.unpack_from("<I", blob, 4)[0]
    i = 8
    exports = []
    types = 0
    while i < len(blob):
        sid = blob[i]
        size = blob[i + 1]
        payload = blob[i + 2 : i + 2 + size]
        i = i + 2 + size
        if sid == 1:
            types = payload[0]
        elif sid == 7:
            count = payload[0]
            p = 1
            for _ in range(count):
                nlen = payload[p]
                name = payload[p + 1 : p + 1 + nlen].decode("ascii")
                exports.append(name)
                p = p + 1 + nlen + 2
    return {"version": version, "types": types, "exports": exports}


def g0_accepts(design: list, inp: list, out: list) -> bool:
    known = {}
    for row in design:
        known[tuple(row)] = tuple(sorted(row))
    key = tuple(inp)
    if key not in known:
        return True
    return known[key] == tuple(out)


def g1_accepts(properties: list[str], inp: list, out: list) -> bool:
    for name in properties:
        if name == "multiset":
            if sorted(inp) != sorted(out):
                return False
        elif name == "nondecreasing":
            prev = None
            for item in out:
                if prev is not None and item < prev:
                    return False
                prev = item
        elif name == "stable_dedup":
            folded = list(dict.fromkeys(inp))
            if list(out) != folded:
                return False
        else:
            raise ValueError(name)
    return True


def h1_controls(text: str, claim: str, anachronisms: list[str]) -> dict:
    text_tokens = set(text.lower().replace(".", " ").replace(",", " ").split())
    claim_tokens = [w.strip(",;:.") for w in claim.split()]
    extra = [w.lower() for w in claim_tokens if len(w) > 3 and w.lower() not in text_tokens]
    ana = [w for w in anachronisms if w.lower() in claim.lower() and w.lower() not in text.lower()]
    fragment = len(claim) < max(8, len(text) // 2) and claim.strip(". ") not in text
    return {
        "added_tokens": extra,
        "anachronisms": ana,
        "eisegesis": bool(extra) or bool(ana),
        "short_fragment_used_as_whole": fragment,
        "text_eq_claim": text.strip() == claim.strip(),
    }


def sha256_stdlib_crosscheck(data: bytes) -> str:
    pure = sha256(data)
    std = hashlib.sha256(data).hexdigest()
    if pure != std:
        raise RuntimeError("ORACLE_SHA256_DIVERGENCE")
    return pure
