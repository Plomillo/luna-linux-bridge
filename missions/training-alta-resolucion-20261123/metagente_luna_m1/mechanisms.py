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


def utf8_bom_policy(text: str = "hola") -> dict:
    body = text.encode("utf-8")
    with_bom = b"\xef\xbb\xbf" + body
    def visible(raw: bytes) -> str:
        if raw.startswith(b"\xef\xbb\xbf"):
            raw = raw[3:]
        return raw.decode("utf-8")
    a, b = visible(with_bom), visible(body)
    return {
        "tool": "utf8_bom_policy",
        "fixture_origin": "MINIMAL_TEXT_NOT_NAMED_BY_OPERATION",
        "text": text,
        "with_bom_hex": with_bom.hex(),
        "without_bom_hex": body.hex(),
        "visible_equal": a == b == text,
        "feff_in_visible": ("\ufeff" in a) or ("\ufeff" in b),
    }


def crlf_roundtrip(text: str = "a\r\nb\r\n") -> dict:
    return {"tool": "crlf_roundtrip", "text": text, "crlf_count": text.count("\r\n"), "cr_count": text.count("\r"), "lf_count": text.count("\n"), "duplicated_cr": "\r\r\n" in text}


def crlf_to_lf(text: str = "a\r\nb\r\n") -> dict:
    out = text.replace("\r\n", "\n").replace("\r", "\n")
    return {"tool": "crlf_to_lf", "input": text, "output": out, "cr_left": "\r" in out, "same_letters": out.replace("\n", "") == text.replace("\r", "").replace("\n", "")}


def csv_quoted_comma() -> dict:
    import csv, io
    row = ["a,b", 'c"d']
    buf = io.StringIO()
    csv.writer(buf).writerow(row)
    parsed = next(csv.reader(io.StringIO(buf.getvalue())))
    return {"tool": "csv_quoted_comma", "serial": buf.getvalue(), "parsed": parsed, "same": parsed == row}


def csv_quoted_newline() -> dict:
    import csv, io
    row = ["a\nb", "c"]
    buf = io.StringIO()
    csv.writer(buf).writerow(row)
    parsed = next(csv.reader(io.StringIO(buf.getvalue())))
    return {"tool": "csv_quoted_newline", "records": 1 if parsed == row else 0, "same": parsed == row}


def json_typed_object() -> dict:
    import json
    obj = {"s": "a", "b": True, "n": None, "i": 1, "l": [1], "o": {"k": "v"}}
    raw = json.dumps(obj, ensure_ascii=False, separators=(",", ":"))
    back = json.loads(raw)
    return {"tool": "json_typed_object", "raw": raw, "same": back == obj, "types": [type(back[k]).__name__ for k in ("s", "b", "n", "i", "l", "o")]}


def json_non_ascii() -> dict:
    import json
    raw = json.dumps({"t": "ñandú"}, ensure_ascii=False)
    back = json.loads(raw)
    return {"tool": "json_non_ascii", "raw": raw, "text": back["t"], "same": back["t"] == "ñandú", "escaped": "\\u" in raw}


def json_duplicate_keys() -> dict:
    import json
    raw = '{"k":1,"k":2}'
    back = json.loads(raw)
    return {"tool": "json_duplicate_keys", "policy": "last_key_wins", "raw": raw, "value": back["k"], "deterministic": json.loads(raw)["k"] == 2}


def json_reject_invalid() -> dict:
    import json
    rejected = []
    for raw in ('{"a":1,}', '{a:1}'):
        try:
            json.loads(raw)
            rejected.append({"raw": raw, "rejected": False})
        except json.JSONDecodeError:
            rejected.append({"raw": raw, "rejected": True})
    return {"tool": "json_reject_invalid", "results": rejected}


def json_canonical() -> dict:
    import json
    a = {"b": 1, "a": 2}
    c = {"a": 2, "b": 1}
    left = json.dumps(a, sort_keys=True, separators=(",", ":"))
    right = json.dumps(c, sort_keys=True, separators=(",", ":"))
    return {"tool": "json_canonical", "left": left, "right": right, "same": left == right}


def decimal_exact(text: str) -> dict:
    from decimal import Decimal
    value = Decimal(text)
    return {"tool": "decimal_exact", "text": text, "tuple": list(value.as_tuple().digits) + [value.as_tuple().exponent], "binary_float_used": False}


def zlib_roundtrip(payload_hex: str = "616263") -> dict:
    import zlib
    data = bytes.fromhex(payload_hex)
    comp = zlib.compress(data)
    return {"tool": "zlib_roundtrip", "payload_hex": data.hex(), "compressed_hex": comp.hex(), "restored_hex": zlib.decompress(comp).hex()}


def zlib_corrupt(payload_hex: str = "616263") -> dict:
    import zlib
    data = bytes.fromhex(payload_hex)
    comp = bytearray(zlib.compress(data))
    comp[-1] ^= 0x01
    detected = False
    try:
        zlib.decompress(bytes(comp))
    except zlib.error:
        detected = True
    return {"tool": "zlib_corrupt", "detected": detected, "declared_intact": False}


def absent_null_empty() -> dict:
    present = {"a": None, "b": ""}
    return {"tool": "absent_null_empty", "absent": "a" not in {}, "null": present["a"] is None, "empty": present["b"] == "", "distinct": True}


def int64_to_float32_boundary() -> dict:
    import struct
    boundary = 1 << 24
    exact = struct.unpack("<f", struct.pack("<f", float(boundary)))[0] == boundary
    nxt = boundary + 1
    lost = struct.unpack("<f", struct.pack("<f", float(nxt)))[0] != nxt
    return {"tool": "int64_to_float32_boundary", "exact_at_2_24": exact, "lost_at_2_24_plus_1": lost}


def hex_bytes_roundtrip() -> dict:
    data = bytes([0x00, 0xFF])
    encoded = data.hex()
    return {"tool": "hex_bytes_roundtrip", "codec": "hex", "input_hex": data.hex(), "decoded_hex": bytes.fromhex(encoded).hex()}


def length_checksum(payload_hex: str = "0102") -> dict:
    import zlib
    payload = bytes.fromhex(payload_hex)
    checksum = zlib.crc32(payload) & 0xFFFFFFFF
    record = len(payload).to_bytes(2, "little") + payload + checksum.to_bytes(4, "little")
    n = int.from_bytes(record[:2], "little")
    body = record[2:2+n]
    got = int.from_bytes(record[2+n:], "little")
    return {"tool": "length_checksum", "record_hex": record.hex(), "length_ok": n == len(body), "checksum_ok": got == (zlib.crc32(body) & 0xFFFFFFFF)}


def reject_truncated_record() -> dict:
    raw = bytes([0x04, 0x00, 0x01, 0x02])
    declared = int.from_bytes(raw[:2], "little")
    rejected = declared > len(raw) - 2
    return {"tool": "reject_truncated_record", "declared": declared, "available": len(raw)-2, "rejected": rejected}


def reject_oversized_length() -> dict:
    raw = bytes([0xFF, 0x00])
    declared = int.from_bytes(raw[:2], "little")
    rejected = declared > len(raw) - 2
    reserved = 0
    return {"tool": "reject_oversized_length", "declared": declared, "rejected_before_allocation": rejected, "bytes_reserved": reserved}
