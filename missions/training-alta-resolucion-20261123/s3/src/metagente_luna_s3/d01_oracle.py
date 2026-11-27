"""Checks that do not call the executors. A published vector is not recomputed with the same function."""
from __future__ import annotations

import json
import math
import struct


def _utf8(text: str) -> bytes:
    out = bytearray()
    for code in map(ord, text):
        if code < 0x80:
            out.append(code)
        elif code < 0x800:
            out.extend((0xC0 | code >> 6, 0x80 | code & 0x3F))
        elif code < 0x10000:
            out.extend((0xE0 | code >> 12, 0x80 | (code >> 6) & 0x3F, 0x80 | code & 0x3F))
        else:
            out.extend((0xF0 | code >> 18, 0x80 | (code >> 12) & 0x3F, 0x80 | (code >> 6) & 0x3F, 0x80 | code & 0x3F))
    return bytes(out)


def utf8_manual(arguments: dict, observed: dict) -> dict:
    raw = _utf8(arguments["text"])
    ok = observed["recovered"] == arguments["text"] and observed["bytes_hex"] == raw.hex() and observed["replacement_used"] is False
    return {"ok": ok, "method": "bit encoder, not str.encode"}


def utf8_state_machine(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    valid = not (raw and raw[0] & 0xC0 == 0x80)
    ok = observed["accepted_as_valid_utf8"] is valid and observed["anomaly_recorded"] is not valid
    return {"ok": ok, "method": "lead-byte state machine"}


def utf16_units(arguments: dict, observed: dict) -> dict:
    order = "<" if arguments["byte_order"] == "LE" else ">"
    raw = b"".join(struct.pack(order + "H", ord(char)) for char in arguments["text"])
    ok = observed["bytes_hex"] == raw.hex() and observed["recovered"] == arguments["text"] and observed["byte_order"] == arguments["byte_order"]
    return {"ok": ok, "method": "code-unit packing, not str.encode"}


def shifts(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    little = raw[0] | raw[1] << 8 | raw[2] << 16 | raw[3] << 24
    big = raw[3] | raw[2] << 8 | raw[1] << 16 | raw[0] << 24
    ok = observed["little_endian_hex"] == f"0x{little:08x}" and observed["big_endian_hex"] == f"0x{big:08x}"
    return {"ok": ok, "method": "manual shifts, not int.from_bytes"}


def range_check(arguments: dict, observed: dict, low: int, high: int) -> dict:
    kept = [value for value in arguments["values"] if low <= value <= high]
    rejected = [value for value in arguments["values"] if value not in kept]
    return {"ok": observed["kept"] == kept and observed["rejected"] == rejected, "method": f"range {low}..{high}, not struct"}


def uint16_range(arguments: dict, observed: dict) -> dict:
    return range_check(arguments, observed, 0, 65535)


def int16_range(arguments: dict, observed: dict) -> dict:
    return range_check(arguments, observed, -32768, 32767)


def sign_bit(arguments: dict, observed: dict) -> dict:
    raw = int(arguments["hex_value"], 16)
    width = arguments["width"]
    signed = raw - (1 << width) if raw & (1 << (width - 1)) else raw
    return {"ok": observed["signed"] == signed and observed["width"] == width, "method": "sign bit"}


def published_bits(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["bits_hex"].lower() == arguments["reference"].lower(), "method": "vector printed in the case"}


def nan_bits(arguments: dict, observed: dict) -> dict:
    probe = struct.unpack(">d", bytes.fromhex(arguments["payload_hex"]))[0]
    expected_nan = math.isnan(probe)
    ok = (
        observed.get("payload_hex") == arguments["payload_hex"].lower()
        and observed.get("is_nan") is expected_nan
        and observed.get("equals_itself") is (probe == probe)  # noqa: PLR0124
        and observed.get("ordinary") is (not expected_nan)
    )
    return {"ok": ok, "method": "independent IEEE-754 payload interpretation"}


def inf_signs(arguments: dict, observed: dict) -> dict:
    if arguments["encoding"] == "literal":
        positive, negative = math.inf, -math.inf
    else:
        positive = struct.unpack(">d", bytes.fromhex(arguments["positive_hex"]))[0]
        negative = struct.unpack(">d", bytes.fromhex(arguments["negative_hex"]))[0]
    ok = (
        observed.get("positive_sign") is (math.copysign(1.0, positive) > 0)
        and observed.get("negative_sign") is (math.copysign(1.0, negative) < 0)
        and observed.get("positive_is_infinite") is math.isinf(positive)
        and observed.get("negative_is_infinite") is math.isinf(negative)
    )
    return {"ok": ok, "method": "independent sign and exponent check"}


def subnormal_bits(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["bits_hex"])
    value = struct.unpack(">f", raw)[0]
    expected_subnormal = math.isfinite(value) and value != 0.0 and abs(value) < 2 ** -126
    ok = observed.get("bits_hex") == raw.hex() and observed.get("is_subnormal") is expected_subnormal
    return {"ok": ok, "method": "independent IEEE-754 exponent/fraction classification"}


def nfc_table(arguments: dict, observed: dict) -> dict:
    if arguments["decomposed"] == arguments["composed"]:
        ok = observed["same_nfc"] is True and observed["nfc"] == arguments["composed"]
        return {"ok": ok, "method": "identity pair, not unicodedata"}
    table = {
        ("e\u0301", "\u00e9"): ("\u00e9", True),
        ("e\u0301", "e"): ("\u00e9", False),
    }
    expected, same = table[(arguments["decomposed"], arguments["composed"])]
    return {"ok": observed["same_nfc"] is same and observed["nfc"] == expected, "method": "fixed normalization table, not unicodedata"}


def nfd_table(arguments: dict, observed: dict) -> dict:
    expected = {
        "a": ["U+0061"],
        "é": ["U+0065", "U+0301"],
        "ñ": ["U+006E", "U+0303"],
    }[arguments["composed"]]
    return {"ok": observed["codepoints"] == expected, "method": "fixed decomposition"}


def nfkc_table(arguments: dict, observed: dict) -> dict:
    expected = {
        "A": ("A", True),
        "ﬁ": ("fi", False),
        "Ａ": ("A", False),
    }[arguments["text"]]
    ok = (observed["compatibility"], observed["preserves_original_form"]) == expected
    return {"ok": ok, "method": "fixed ligature"}


def bom_visible(arguments: dict, observed: dict) -> dict:
    return {"ok": observed["contains_bom_character"] is False and observed["visible"] == arguments["with_bom_visible"] and observed["plain_text"] == arguments["without_bom"], "method": "BOM bytes are EF BB BF"}


def _canonical(value) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_canonical(item) for item in value) + "]"
    if isinstance(value, dict):
        keys = sorted(value)
        return "{" + ",".join(json.dumps(key, ensure_ascii=False) + ":" + _canonical(value[key]) for key in keys) + "}"
    raise TypeError(type(value).__name__)


def json_types(arguments: dict, observed: dict) -> dict:
    expected = _canonical(arguments["document"])
    return {"ok": observed["parsed"] == arguments["document"] and observed["raw"] == expected, "method": "hand-built canonical form"}


def json_scan(arguments: dict, observed: dict) -> dict:
    bad = [text for text in arguments["texts"] if ",}" in text or "{a:" in text]
    return {"ok": observed["rejected"] == arguments["texts"] and len(bad) == len(arguments["texts"]), "method": "textual scan, not json.loads"}


def nist_abc(arguments: dict, observed: dict) -> dict:
    vectors = {
        "abc": "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        "": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    }
    expected = vectors.get(arguments["text"])
    ok = expected is not None and observed["digest_hex"] == expected
    return {"ok": ok, "method": "published SHA-256 vectors, not hashlib"}
