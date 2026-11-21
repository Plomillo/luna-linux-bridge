"""Worker-side algorithms. The oracle must not import this module."""
from __future__ import annotations

import hashlib
import hmac
import math
import struct
import unicodedata
from collections import Counter


def bits_to_int(s: str) -> int:
    if not s or any(c not in "01" for c in s):
        raise ValueError("BIN_GRAMMAR")
    n = 0
    for c in s:
        n = (n << 1) | (1 if c == "1" else 0)
    return n


def int_to_bits(n: int, width: int) -> str:
    if n < 0 or width < 1 or n >= (1 << width):
        raise ValueError("BIN_RANGE")
    return "".join("1" if (n >> (width - 1 - i)) & 1 else "0" for i in range(width))


def wrap_add(a: int, b: int, bits: int, signed: bool) -> dict:
    mask = (1 << bits) - 1
    if signed:
        lo = -(1 << (bits - 1))
        hi = (1 << (bits - 1)) - 1
        if not lo <= a <= hi or not lo <= b <= hi:
            raise ValueError("RANGE")
        raw = a + b
        overflow = raw < lo or raw > hi
        return {"value": raw, "overflow": overflow, "lo": lo, "hi": hi}
    if a < 0 or b < 0 or a > mask or b > mask:
        raise ValueError("RANGE")
    raw = a + b
    return {"value": raw, "overflow": raw > mask, "lo": 0, "hi": mask}


def apply_mask(word: int, mask: int, value: int, width: int) -> int:
    if word < 0 or mask < 0 or value < 0:
        raise ValueError("NEG")
    limit = 1 << width
    if word >= limit or mask >= limit or value >= limit:
        raise ValueError("WIDTH")
    return (word & ~mask) | (value & mask)


def shifts(n: int, k: int, bits: int) -> dict:
    mask = (1 << bits) - 1
    logical = (n & mask) >> k
    sign = (n >> (bits - 1)) & 1
    if sign:
        arith = (n & mask) >> k
        fill = ((1 << k) - 1) << (bits - k)
        arith |= fill
    else:
        arith = logical
    return {"logical": logical & mask, "arithmetic": arith & mask, "sign": sign}


def mod_norm(a: int, m: int) -> int:
    if m <= 0:
        raise ValueError("MOD")
    return a % m


def to_base(n: int, base: int) -> str:
    if base < 2 or base > 16:
        raise ValueError("BASE")
    if n < 0:
        raise ValueError("NEG")
    digits = "0123456789abcdef"
    if n == 0:
        return "0"
    out = []
    while n:
        n, r = divmod(n, base)
        out.append(digits[r])
    return "".join(reversed(out))


def from_base(s: str, base: int) -> int:
    digits = "0123456789abcdef"
    if base < 2 or base > 16 or not s:
        raise ValueError("BASE")
    n = 0
    for c in s.lower():
        v = digits.find(c)
        if v < 0 or v >= base:
            raise ValueError("DIGIT")
        n = n * base + v
    return n


def to_ternary(n: int) -> str:
    return to_base(n, 3)


def from_ternary(s: str) -> int:
    return from_base(s, 3)


def to_balanced(n: int) -> str:
    if n == 0:
        return "0"
    digits = []
    x = n
    while x:
        x, rem = divmod(x, 3)
        if rem == 2:
            digits.append("N")
            x += 1
        elif rem == 0:
            digits.append("0")
        else:
            digits.append("P")
    return "".join(reversed(digits))


def from_balanced(s: str) -> int:
    n = 0
    for c in s:
        n *= 3
        if c == "N":
            n -= 1
        elif c == "P":
            n += 1
        elif c == "0":
            pass
        else:
            raise ValueError("BAL")
    return n


_B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"
_B64URL = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_B32 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"


def b64_encode(data: bytes, url: bool = False) -> str:
    alphabet = _B64URL if url else _B64
    out = []
    i = 0
    while i + 3 <= len(data):
        n = (data[i] << 16) | (data[i + 1] << 8) | data[i + 2]
        out.append(alphabet[(n >> 18) & 63])
        out.append(alphabet[(n >> 12) & 63])
        out.append(alphabet[(n >> 6) & 63])
        out.append(alphabet[n & 63])
        i += 3
    rem = data[i:]
    if len(rem) == 1:
        n = rem[0] << 16
        out.append(alphabet[(n >> 18) & 63])
        out.append(alphabet[(n >> 12) & 63])
        if not url:
            out.append("=")
            out.append("=")
    elif len(rem) == 2:
        n = (rem[0] << 16) | (rem[1] << 8)
        out.append(alphabet[(n >> 18) & 63])
        out.append(alphabet[(n >> 12) & 63])
        out.append(alphabet[(n >> 6) & 63])
        if not url:
            out.append("=")
    return "".join(out)


def b64_decode(s: str, url: bool = False) -> bytes:
    alphabet = _B64URL if url else _B64
    t = s.strip()
    if url:
        t = t.replace("-", "+").replace("_", "/")
        alphabet = _B64
    if any(c not in alphabet + "=" for c in t):
        raise ValueError("ALPHABET")
    if len(t) % 4 != 0:
        raise ValueError("LEN")
    pad = len(t) - len(t.rstrip("="))
    if pad > 2 or "=" in t.rstrip("="):
        raise ValueError("PAD")
    core = t[:-pad] if pad else t
    out = bytearray()
    acc = 0
    bits = 0
    for c in core:
        acc = (acc << 6) | alphabet.index(c)
        bits += 6
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
            acc &= (1 << bits) - 1
    return bytes(out)


def b32_encode(data: bytes) -> str:
    acc = 0
    bits = 0
    out = []
    for b in data:
        acc = (acc << 8) | b
        bits += 8
        while bits >= 5:
            bits -= 5
            out.append(_B32[(acc >> bits) & 31])
    if bits:
        out.append(_B32[(acc << (5 - bits)) & 31])
    while len(out) % 8:
        out.append("=")
    return "".join(out)


def b32_decode(s: str) -> bytes:
    t = s.strip().upper()
    if len(t) % 8 != 0:
        raise ValueError("LEN")
    pad = len(t) - len(t.rstrip("="))
    core = t[:-pad] if pad else t
    acc = 0
    bits = 0
    out = bytearray()
    for c in core:
        if c not in _B32:
            raise ValueError("ALPHABET")
        acc = (acc << 5) | _B32.index(c)
        bits += 5
        if bits >= 8:
            bits -= 8
            out.append((acc >> bits) & 0xFF)
    return bytes(out)


def hex_encode(data: bytes) -> str:
    return data.hex()


def hex_decode(s: str) -> bytes:
    t = s.strip().lower()
    if len(t) % 2 or any(c not in "0123456789abcdef" for c in t):
        raise ValueError("HEX")
    return bytes(int(t[i : i + 2], 16) for i in range(0, len(t), 2))


def utf8_errors(data: bytes) -> dict:
    try:
        data.decode("utf-8")
        return {"ok": True, "error": ""}
    except UnicodeDecodeError as exc:
        return {"ok": False, "error": f"{exc.start}:{exc.reason}"}


def utf16_pair(units: list[int]) -> dict:
    if len(units) >= 2 and 0xD800 <= units[0] <= 0xDBFF and 0xDC00 <= units[1] <= 0xDFFF:
        cp = 0x10000 + ((units[0] - 0xD800) << 10) + (units[1] - 0xDC00)
        return {"ok": True, "cp": cp}
    if any(0xD800 <= u <= 0xDFFF for u in units):
        return {"ok": False, "cp": -1}
    if len(units) == 1 and units[0] <= 0xFFFF:
        return {"ok": True, "cp": units[0]}
    return {"ok": False, "cp": -1}


def norms(s: str) -> dict:
    return {
        "nfc": unicodedata.normalize("NFC", s),
        "nfd": unicodedata.normalize("NFD", s),
        "nfkc": unicodedata.normalize("NFKC", s),
        "nfkd": unicodedata.normalize("NFKD", s),
    }


def grapheme_count(s: str) -> dict:
    cps = len(s)
    count = 0
    for ch in s:
        cat = unicodedata.category(ch)
        if count == 0 or not (cat in {"Mn", "Mc", "Me"} or ch == "\u200d"):
            if cat in {"Mn", "Mc", "Me"} or ch == "\u200d":
                count += 1
            else:
                count += 1
        # combining mark or ZWJ extends the current cluster
        if cat in {"Mn", "Mc", "Me"} or ch == "\u200d":
            continue
    # recount with an explicit cluster walker so the first branch cannot drift
    clusters = 0
    for ch in s:
        cat = unicodedata.category(ch)
        if clusters == 0 or not (cat in {"Mn", "Mc", "Me"} or ch == "\u200d"):
            clusters += 1
    return {"codepoints": cps, "graphemes_limited": clusters, "uax29": "NOT_CLAIMED"}


def shannon_milli(data: bytes) -> int:
    if not data:
        return 0
    n = len(data)
    counts = Counter(data)
    h = 0.0
    for v in counts.values():
        p = v / n
        h -= p * math.log2(p)
    return int(round(h * 1000))


def sum16(data: bytes) -> int:
    return sum(data) & 0xFFFF


def crc32_ref(data: bytes) -> int:
    crc = 0xFFFFFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xEDB88320 if crc & 1 else crc >> 1
    return crc ^ 0xFFFFFFFF


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(obj) -> str:
    import json
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def duplicate_keys(raw: str) -> dict:
    import json
    dec = json.JSONDecoder()
    parsed = json.loads(raw)
    dupes = []

    def walk(text: str) -> None:
        text = text.strip()
        if not text.startswith("{"):
            return
        i = 1
        seen = set()
        while i < len(text):
            while i < len(text) and text[i] in " \n\r\t,":
                i += 1
            if i < len(text) and text[i] == "}":
                return
            key, end = dec.raw_decode(text[i:])
            i += end
            while i < len(text) and text[i] in " \n\r\t":
                i += 1
            if i >= len(text) or text[i] != ":":
                raise ValueError("COLON")
            i += 1
            val, vend = dec.raw_decode(text[i:])
            i += vend
            if isinstance(key, str):
                if key in seen:
                    dupes.append(key)
                seen.add(key)
            if isinstance(val, str):
                pass

    walk(raw)
    return {"last_wins": parsed, "duplicate_keys": dupes, "policy": "DETECT_AND_LAST_WINS"}


def elf_header(blob: bytes) -> dict:
    if len(blob) < 20 or blob[:4] != b"\x7fELF":
        raise ValueError("ELF")
    ei_class = blob[4]
    ei_data = blob[5]
    if ei_class not in (1, 2) or ei_data not in (1, 2):
        raise ValueError("ELF_IDENT")
    endian = "little" if ei_data == 1 else "big"
    e_type = int.from_bytes(blob[16:18], endian)
    e_machine = int.from_bytes(blob[18:20], endian)
    types = {1: "REL", 2: "EXEC", 3: "DYN", 4: "CORE"}
    return {
        "class": "ELF32" if ei_class == 1 else "ELF64",
        "endian": "LE" if ei_data == 1 else "BE",
        "type": types.get(e_type, str(e_type)),
        "machine": e_machine,
    }


def pe_header(blob: bytes) -> dict:
    if len(blob) < 0x18 or blob[:2] != b"MZ":
        raise ValueError("MZ")
    lfanew = int.from_bytes(blob[0x3C:0x40], "little")
    if lfanew < 0 or lfanew + 8 > len(blob):
        raise ValueError("LFANEW")
    if blob[lfanew : lfanew + 4] != b"PE\x00\x00":
        raise ValueError("PE")
    machine = int.from_bytes(blob[lfanew + 4 : lfanew + 6], "little")
    sections = int.from_bytes(blob[lfanew + 6 : lfanew + 8], "little")
    return {"machine": machine, "sections": sections, "format": "PE"}


def macho_header(blob: bytes) -> dict:
    if len(blob) < 32:
        raise ValueError("SHORT")
    magic = int.from_bytes(blob[:4], "little")
    if magic != 0xFEEDFACF:
        raise ValueError("MAGIC")
    cputype = int.from_bytes(blob[4:8], "little")
    filetype = int.from_bytes(blob[12:16], "little")
    ncmds = int.from_bytes(blob[16:20], "little")
    return {"format": "MACHO64", "cputype": cputype, "filetype": filetype, "ncmds": ncmds}


def class_header(blob: bytes) -> dict:
    if len(blob) < 8 or blob[:4] != b"\xca\xfe\xba\xbe":
        raise ValueError("CLASS")
    minor = int.from_bytes(blob[4:6], "big")
    major = int.from_bytes(blob[6:8], "big")
    return {"format": "JVM_CLASS", "minor": minor, "major": major}


def wasm_summary(blob: bytes) -> dict:
    if blob[:4] != b"\x00asm" or len(blob) < 8:
        raise ValueError("WASM")
    version = int.from_bytes(blob[4:8], "little")
    i = 8
    exports = []
    types = 0
    while i < len(blob):
        sid = blob[i]
        i += 1
        if i >= len(blob):
            raise ValueError("TRUNC")
        size = blob[i]
        if size & 0x80:
            raise ValueError("LEB_UNSUPPORTED_IN_FIXTURE")
        i += 1
        payload = blob[i : i + size]
        if len(payload) != size:
            raise ValueError("TRUNC")
        i += size
        if sid == 1 and payload:
            types = payload[0]
        if sid == 7 and payload:
            count = payload[0]
            p = 1
            for _ in range(count):
                nlen = payload[p]
                p += 1
                name = payload[p : p + nlen].decode("ascii")
                p += nlen
                p += 2  # kind + index (single byte index in fixture)
                exports.append(name)
    return {"version": version, "types": types, "exports": exports}


def compare_secret(a: str, b: str) -> dict:
    match = hmac.compare_digest(a.encode(), b.encode()) if len(a) == len(b) else False
    log = "MATCH" if match else "MISMATCH"
    leaked = a in log or b in log
    return {"log": log, "match": match, "secret_in_log": leaked}


def g0_table(design: list[list[int]]):
    table = {tuple(row): tuple(sorted(row)) for row in design}

    def check(inp: list[int], out: list[int]) -> bool:
        key = tuple(inp)
        if key not in table:
            return True
        return table[key] == tuple(out)

    return check


def g1_properties(properties: list[str]):
    def check(inp: list[int], out: list[int]) -> bool:
        for name in properties:
            if name == "multiset":
                if Counter(inp) != Counter(out):
                    return False
            elif name == "nondecreasing":
                if any(out[i] > out[i + 1] for i in range(len(out) - 1)):
                    return False
            elif name == "stable_dedup":
                seen = []
                for x in inp:
                    if x not in seen:
                        seen.append(x)
                if out != seen:
                    return False
            else:
                raise ValueError(name)
        return True

    return check


def h0_gloss(memory: dict[str, str], text: str) -> str:
    if text not in memory:
        return "ACCEPT_UNSEEN"
    return memory[text]


def h1_controls(text: str, claim: str, anachronisms: list[str]) -> dict:
    extra = []
    for word in claim.replace(".", " ").split():
        token = word.strip(",;:").lower()
        if token and token not in text.lower() and len(token) > 3:
            extra.append(token)
    ana = [w for w in anachronisms if w.lower() in claim.lower() and w.lower() not in text.lower()]
    fragment = len(claim) < max(8, len(text) // 2) and claim.strip(". ") not in text
    return {
        "added_tokens": extra,
        "anachronisms": ana,
        "eisegesis": bool(extra) or bool(ana),
        "short_fragment_used_as_whole": fragment,
        "text_eq_claim": text.strip() == claim.strip(),
    }
