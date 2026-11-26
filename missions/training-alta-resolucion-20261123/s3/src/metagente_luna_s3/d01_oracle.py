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
    del arguments
    probe = struct.unpack(">d", bytes.fromhex("7ff8000000000000"))[0]
    return {"ok": observed["is_nan"] is True and observed["equals_itself"] is False and math.isnan(probe), "method": "canonical NaN payload"}


def inf_signs(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["positive_sign"] is True and observed["negative_sign"] is True and bool(observed["output_format"]), "method": "separate sign check"}


def subnormal_bits(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["float32_bits_hex"] == "00000001" and observed["is_subnormal"] is True, "method": "IEEE bit 0"}


def nfc_table(arguments: dict, observed: dict) -> dict:
    if arguments["decomposed"] == arguments["composed"]:
        ok = observed["same_nfc"] is True and observed["nfc"] == arguments["composed"]
        return {"ok": ok, "method": "identity pair, not unicodedata"}
    table = {("e\u0301", "\u00e9"): "\u00e9"}
    expected = table[(arguments["decomposed"], arguments["composed"])]
    return {"ok": observed["same_nfc"] is True and observed["nfc"] == expected, "method": "fixed pair, not unicodedata"}


def nfd_table(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["codepoints"] == ["U+0065", "U+0301"], "method": "fixed decomposition"}


def nfkc_table(arguments: dict, observed: dict) -> dict:
    del arguments
    return {"ok": observed["compatibility"] == "fi" and observed["preserves_original_form"] is False, "method": "fixed ligature"}


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
    vector = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    ok = arguments["text"] == "abc" and observed["digest_hex"] == vector
    return {"ok": ok, "method": "NIST vector, not hashlib"}
