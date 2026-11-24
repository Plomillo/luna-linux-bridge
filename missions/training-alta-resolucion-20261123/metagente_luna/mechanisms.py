"""General tools. They do not know case identifiers."""
from __future__ import annotations

import hashlib
import struct


def utf8_roundtrip(text: str) -> dict:
    encoded = text.encode("utf-8")
    decoded = encoded.decode("utf-8")
    return {"tool": "utf8_roundtrip", "text": decoded, "utf8_hex": encoded.hex(), "identical": decoded == text}


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
    return {
        "tool": "utf8_strict_decode",
        "input_hex": raw.hex(),
        "policy": "strict",
        "accepted_as_valid_utf8": accepted,
        "anomaly": error,
    }


def sum_ints(values: list[int]) -> dict:
    return {"tool": "sum_ints", "values": values, "sum": sum(values), "empty_sum": sum([])}


def bounds(values: list[int]) -> dict:
    return {"tool": "bounds", "values": values, "min": min(values), "max": max(values)}


def sha256_text(text: str) -> dict:
    return {"tool": "sha256_text", "text": text, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()}


def int16_roundtrip(values: list[int]) -> dict:
    recovered = []
    rejected = []
    for value in values:
        try:
            packed = struct.pack("<h", value)
        except struct.error:
            rejected.append(value)
            continue
        recovered.append({"value": value, "hex": packed.hex(), "recovered": struct.unpack("<h", packed)[0]})
    return {"tool": "int16_roundtrip", "recovered": recovered, "rejected": rejected}
