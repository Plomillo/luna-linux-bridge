"""Executors for the encoding cases whose inputs are written in the program."""
from __future__ import annotations

import hashlib
import json
import math
import struct
import unicodedata


def utf8_roundtrip(text: str) -> dict:
    raw = text.encode("utf-8")
    recovered = raw.decode("utf-8")
    print(raw.hex())
    return {"recovered": recovered, "bytes_hex": raw.hex(), "replacement_used": "\ufffd" in recovered}


def utf8_reject_invalid(payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        print(f"rejected at {exc.start}")
        return {"accepted_as_valid_utf8": False, "anomaly_recorded": True, "policy": "REJECT"}
    return {"accepted_as_valid_utf8": True, "anomaly_recorded": False, "policy": "REJECT"}


def utf16_encode(text: str, byte_order: str) -> dict:
    codec = {"LE": "utf-16-le", "BE": "utf-16-be"}[byte_order]
    raw = text.encode(codec)
    print(raw.hex())
    return {"recovered": raw.decode(codec), "bytes_hex": raw.hex(), "byte_order": byte_order}


def u32_endian(payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    little = int.from_bytes(raw, "little")
    big = int.from_bytes(raw, "big")
    print(f"{little:08x} {big:08x}")
    return {"little_endian_hex": f"0x{little:08x}", "big_endian_hex": f"0x{big:08x}"}


def uint16_bounds(values: list[int]) -> dict:
    kept, rejected = [], []
    for value in values:
        try:
            struct.pack(">H", value)
        except struct.error:
            rejected.append(value)
        else:
            kept.append(value)
    print(kept, rejected)
    return {"kept": kept, "rejected": rejected}


def int16_values(values: list[int]) -> dict:
    kept, rejected = [], []
    for value in values:
        try:
            struct.pack(">h", value)
        except struct.error:
            rejected.append(value)
        else:
            kept.append(value)
    print(kept, rejected)
    return {"kept": kept, "rejected": rejected}


def twos_complement_16(hex_value: str, width: int) -> dict:
    raw = int(hex_value, 16)
    signed = raw - (1 << width) if raw >> (width - 1) else raw
    print(signed)
    return {"signed": signed, "width": width}


def float_bits(value: float, kind: str) -> dict:
    fmt = {32: ">f", 64: ">d"}[kind]
    raw = struct.pack(fmt, value)
    print(raw.hex())
    return {"bits_hex": "0x" + raw.hex()}


def nan_policy(value_kind: str) -> dict:
    if value_kind == "nan":
        value = float("nan")
    elif value_kind == "negative-nan":
        value = struct.unpack(">d", bytes.fromhex("fff8000000000000"))[0]
    elif value_kind == "finite":
        value = 1.0
    else:
        return {"rejected": True, "reason": "unsupported NaN fixture"}
    print(value_kind)
    return {"is_nan": math.isnan(value), "equals_itself": bool(value == value), "ordinary": math.isfinite(value), "negative_sign": math.copysign(1.0, value) < 0}  # noqa: PLR0124


def inf_policy(value_kind: str) -> dict:
    values = {"both": (math.inf, -math.inf), "positive": (math.inf, 0.0), "negative": (0.0, -math.inf), "finite": (1.0, -1.0)}
    if value_kind not in values:
        return {"rejected": True, "reason": "unsupported infinity fixture"}
    positive, negative = values[value_kind]
    print(value_kind)
    return {
        "positive_sign": math.isinf(positive) and math.copysign(1.0, positive) > 0,
        "negative_sign": math.isinf(negative) and math.copysign(1.0, negative) < 0,
        "output_format": f"{positive} {negative}",
    }


def subnormal_f32(value_kind: str) -> dict:
    encodings = {"smallest-subnormal": "00000001", "zero": "00000000", "smallest-normal": "00800000"}
    if value_kind not in encodings:
        return {"rejected": True, "reason": "unsupported float32 fixture"}
    value = struct.unpack(">f", bytes.fromhex(encodings[value_kind]))[0]
    bits = struct.pack(">f", value).hex()
    widened = struct.pack(">d", float(value)).hex()
    exponent = int(bits[:3], 16) >> 1
    mantissa_nonzero = int(bits, 16) & 0x7FFFFF != 0
    is_subnormal = exponent == 0 and mantissa_nonzero
    print(bits)
    return {"is_subnormal": is_subnormal, "float32_bits_hex": bits, "float64_bits_hex": widened, "precision_loss_on_widening": False}


def nfc_compare(decomposed: str, composed: str) -> dict:
    left = unicodedata.normalize("NFC", decomposed)
    right = unicodedata.normalize("NFC", composed)
    print(left == right)
    return {"same_nfc": left == right, "nfc": left}


def nfd_decompose(composed: str) -> dict:
    decomposed = unicodedata.normalize("NFD", composed)
    print(" ".join(f"U+{ord(ch):04X}" for ch in decomposed))
    return {"codepoints": [f"U+{ord(ch):04X}" for ch in decomposed]}


def nfkc_compat(text: str) -> dict:
    converted = unicodedata.normalize("NFKC", text)
    print(converted)
    return {"compatibility": converted, "preserves_original_form": converted == text}


def bom_policy(without_bom: str, with_bom_visible: str) -> dict:
    plain = without_bom.encode("utf-8")
    marked = b"\xef\xbb\xbf" + with_bom_visible.encode("utf-8")
    visible = marked.decode("utf-8-sig")
    print(visible)
    return {"visible": visible, "contains_bom_character": "\ufeff" in visible, "plain_text": plain.decode("utf-8")}


def json_roundtrip(document: dict) -> dict:
    raw = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    parsed = json.loads(raw)
    print(raw)
    return {"parsed": parsed, "raw": raw}


def json_reject(texts: list[str]) -> dict:
    rejected = []
    for text in texts:
        try:
            json.loads(text)
        except json.JSONDecodeError:
            rejected.append(text)
    print(len(rejected))
    return {"rejected": rejected, "rejected_count": len(rejected)}


def sha256_text(text: str) -> dict:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    print(digest)
    return {"digest_hex": digest}
