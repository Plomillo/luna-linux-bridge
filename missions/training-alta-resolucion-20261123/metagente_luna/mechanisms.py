"""General tools. No case identifiers."""
from __future__ import annotations

import hashlib
import sqlite3
import struct
import unicodedata


def utf8_roundtrip(text: str) -> dict:
    encoded = text.encode("utf-8")
    decoded = encoded.decode("utf-8")
    return {"tool": "utf8_roundtrip", "text": decoded, "utf8_hex": encoded.hex(), "identical": decoded == text, "replacement_used": "\ufffd" in decoded}


def utf16_roundtrip(text: str, endian: str) -> dict:
    codec = "utf-16-le" if endian == "little" else "utf-16-be"
    encoded = text.encode(codec)
    decoded = encoded.decode(codec)
    return {"tool": "utf16_roundtrip", "endian": endian, "text": decoded, "utf16_hex": encoded.hex(), "identical": decoded == text}


def reject_isolated_continuation(byte_hex: str) -> dict:
    raw = bytes.fromhex(byte_hex.removeprefix("0x"))
    try:
        raw.decode("utf-8")
        accepted = True
        error = None
    except UnicodeDecodeError as exc:
        accepted = False
        error = exc.reason
    return {"tool": "utf8_strict_decode", "input_hex": raw.hex(), "policy": "strict", "accepted_as_valid_utf8": accepted, "anomaly": error}


def uint_from_bytes(raw_hex: str, width: int) -> dict:
    raw = bytes.fromhex(raw_hex)
    fmt = {16: "H", 32: "I", 64: "Q"}[width]
    little = struct.unpack("<" + fmt, raw)[0]
    big = struct.unpack(">" + fmt, raw)[0]
    return {"tool": "uint_from_bytes", "width": width, "input_hex": raw.hex(), "little": little, "big": big}


def uint16_limits() -> dict:
    kept = []
    for value in (0, 65535):
        packed = struct.pack("<H", value)
        kept.append({"value": value, "hex": packed.hex(), "recovered": struct.unpack("<H", packed)[0]})
    rejected = []
    for value in (65536, -1):
        try:
            struct.pack("<H", value)
            rejected.append({"value": value, "rejected": False})
        except struct.error:
            rejected.append({"value": value, "rejected": True})
    return {"tool": "uint16_limits", "kept": kept, "rejected": rejected}


def int16_roundtrip(values: list[int]) -> dict:
    recovered = []
    rejected = []
    probes = list(values)
    for edge in (-32769, 32768):
        if edge not in probes:
            probes.append(edge)
    for value in probes:
        try:
            packed = struct.pack("<h", value)
        except struct.error:
            rejected.append(value)
            continue
        recovered.append({"value": value, "hex": packed.hex(), "recovered": struct.unpack("<h", packed)[0]})
    return {"tool": "int16_roundtrip", "recovered": recovered, "rejected": rejected}


def signed_from_hex(raw_hex: str, width: int) -> dict:
    raw = bytes.fromhex(raw_hex.removeprefix("0x").zfill(width // 4))
    fmt = {16: "h", 32: "i"}[width]
    value = struct.unpack(">" + fmt, raw)[0]
    return {"tool": "signed_from_hex", "width": width, "input_hex": raw.hex(), "value": value}


def float_bits(value: float, kind: str) -> dict:
    fmt = "<f" if kind == "float32" else "<d"
    packed = struct.pack(fmt, value)
    return {"tool": "float_bits", "kind": kind, "value": value, "hex": packed.hex()}


def non_finite(kind: str) -> dict:
    if kind == "nan":
        value = struct.unpack("<d", struct.pack("<d", float("nan")))[0]
        return {"tool": "non_finite", "kind": "nan", "equal_to_self": value == value, "classified": value != value}
    pos = float("inf")
    neg = float("-inf")
    return {
        "tool": "non_finite",
        "kind": "inf",
        "positive_hex": struct.pack("<d", pos).hex(),
        "negative_hex": struct.pack("<d", neg).hex(),
        "signs_distinct": struct.pack("<d", pos) != struct.pack("<d", neg),
    }


def min_subnormal_f32() -> dict:
    raw = (1).to_bytes(4, "little")
    value = struct.unpack("<f", raw)[0]
    return {"tool": "min_subnormal_f32", "hex": raw.hex(), "value": value, "is_subnormal": value != 0.0 and value < 1.1754944e-38}


def nfc_compare(left: str, right: str) -> dict:
    a = unicodedata.normalize("NFC", left)
    b = unicodedata.normalize("NFC", right)
    return {"tool": "nfc_compare", "left_hex": a.encode().hex(), "right_hex": b.encode().hex(), "same": a == b}


def nfd_decompose(text: str) -> dict:
    out = unicodedata.normalize("NFD", text)
    return {"tool": "nfd_decompose", "codepoints": [f"U+{ord(ch):04X}" for ch in out], "hex": out.encode().hex()}


def nfkc_note(text: str) -> dict:
    out = unicodedata.normalize("NFKC", text)
    return {"tool": "nfkc_note", "input": text, "output": out, "preserved_original": out == text}


def sha256_text(text: str) -> dict:
    return {"tool": "sha256_text", "text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def sum_ints(values: list[int]) -> dict:
    return {"tool": "sum_ints", "values": values, "sum": sum(values), "empty_sum": sum([])}


def bounds(values: list[int]) -> dict:
    return {"tool": "bounds", "values": values, "min": min(values), "max": max(values)}


def sqlite_check_insert(column: str, value: int, predicate: str) -> dict:
    conn = sqlite3.connect(":memory:")
    try:
        conn.execute(f"CREATE TABLE t({column} INTEGER CHECK ({predicate}))")
        try:
            conn.execute(f"INSERT INTO t({column}) VALUES (?)", (value,))
            rejected = False
            error = None
        except sqlite3.IntegrityError as exc:
            rejected = True
            error = str(exc)
        return {"tool": "sqlite_check_insert", "engine": "sqlite3", "column": column, "value": value, "predicate": predicate, "rejected": rejected, "error": error}
    finally:
        conn.close()
