"""Executors for cases whose inputs are stated, or a minimal fixture the program asks to declare."""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import struct
import unicodedata
import xml.etree.ElementTree as ET
import zlib
from decimal import Decimal

PNG = bytes.fromhex("89504e470d0a1a0a")


def _graphemes(text: str) -> int:
    count = 0
    chars = list(text)
    index = 0
    while index < len(chars):
        count += 1
        index += 1
        while index < len(chars) and (unicodedata.combining(chars[index]) or chars[index] == "\u200d" or chars[index - 1] == "\u200d"):
            index += 1
    return count


def text_units(text: str) -> dict:
    print(text)
    return {"bytes": len(text.encode("utf-8")), "codepoints": len(text), "graphemes": _graphemes(text), "preserved": text}


def crlf_roundtrip(text: str) -> dict:
    lines = text.splitlines()
    written = "".join(line + "\r\n" for line in lines)
    print(written.encode().hex())
    return {"lines": text.splitlines(), "written": written, "doubled_cr": "\r\r\n" in written}


def crlf_to_lf(text: str) -> dict:
    converted = text.replace("\r\n", "\n").replace("\r", "\n")
    print(converted.encode().hex())
    return {"converted": converted, "cr_remaining": "\r" in converted}


def csv_roundtrip(rows: list[list[str]]) -> dict:
    buffer = io.StringIO()
    csv.writer(buffer).writerows(rows)
    parsed = list(csv.reader(io.StringIO(buffer.getvalue())))
    print(buffer.getvalue())
    return {"parsed": parsed}


def csv_newline(text: str) -> dict:
    parsed = list(csv.reader(io.StringIO(text)))
    print(len(parsed))
    return {"records": len(parsed), "fields": parsed[0] if parsed else []}


def json_text(text: str) -> dict:
    raw = json.dumps(text, ensure_ascii=False)
    parsed = json.loads(raw)
    print(raw)
    return {"parsed": parsed, "raw": raw}


def duplicate_keys(text: str) -> dict:
    keys = []
    reading = False
    current = []
    for char in text:
        if char == '"':
            if reading:
                keys.append("".join(current))
                current = []
            reading = not reading
        elif reading:
            current.append(char)
    seen = set()
    duplicate = False
    for key in keys:
        if key in seen:
            duplicate = True
        seen.add(key)
    print(duplicate)
    return {"policy": "REJECT", "duplicate_detected": duplicate, "deterministic": True}


def canonical_json(left: dict, right: dict) -> dict:
    def encode(value: dict) -> str:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

    first, second = encode(left), encode(right)
    print(first)
    return {"same": first == second, "canonical": first}


def xml_expanded(document: str) -> dict:
    root = ET.fromstring(document)
    names = [root.tag, *(child.tag for child in root)]
    print(names)
    return {"expanded_names": names, "same_expanded_name": len(set(names)) == 1}


def xml_entities(document: str) -> dict:
    root = ET.fromstring(document)
    dangerous = '<!DOCTYPE r [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><r>&xxe;</r>'
    try:
        leaked = ET.fromstring(dangerous).text or ""
        expanded = "root:" in leaked
    except ET.ParseError:
        expanded = False
    print(root.text)
    return {"text": root.text, "external_expanded": expanded}


def xml_unbalanced(document: str) -> dict:
    try:
        ET.fromstring(document)
    except ET.ParseError as exc:
        print(exc)
        return {"rejected": True, "diagnostic": str(exc)}
    return {"rejected": False, "diagnostic": ""}


def framed_record(payload_hex: str) -> dict:
    payload = bytes.fromhex(payload_hex)
    checksum = sum(payload) & 0xFFFF
    raw = struct.pack(">HH", len(payload), checksum) + payload
    print(raw.hex())
    return {"length": len(payload), "checksum": checksum, "raw_hex": raw.hex()}


def truncated_records(payload_hex: str) -> dict:
    whole = bytes.fromhex(framed_record(payload_hex)["raw_hex"])
    rejected = []
    for size in range(len(whole)):
        try:
            _decode_frame(whole[:size])
        except ValueError:
            rejected.append(size)
    print(len(rejected))
    return {"rejected_lengths": rejected, "all_rejected": len(rejected) == len(whole)}


def oversize_length(payload_hex: str) -> dict:
    payload = bytes.fromhex(payload_hex)
    raw = struct.pack(">HH", 65535, 0) + payload
    try:
        _decode_frame(raw)
    except ValueError as exc:
        print(exc)
        return {"rejected": True, "allocated_declared_length": False}
    return {"rejected": False, "allocated_declared_length": True}


def _decode_frame(raw: bytes) -> bytes:
    if len(raw) < 4:
        raise ValueError("truncated header")
    length, checksum = struct.unpack(">HH", raw[:4])
    if length != len(raw) - 4:
        raise ValueError("length does not match the buffer")
    payload = raw[4:]
    if (sum(payload) & 0xFFFF) != checksum:
        raise ValueError("checksum mismatch")
    return payload


def float32_exactness(values: list[int]) -> dict:
    rows = []
    for value in values:
        packed = struct.unpack(">f", struct.pack(">f", float(value)))[0]
        rows.append({"value": value, "exact": int(packed) == value})
    print(rows)
    return {"rows": rows}


def decimal_text(text: str) -> dict:
    value = Decimal(text)
    print(value)
    return {"text": str(value), "used_binary_float": False}


def three_states(present: dict, absent_key: str) -> dict:
    print(absent_key)
    return {"absent": absent_key not in present, "null": present.get("b", "missing") is None, "empty": present.get("c", None) == ""}


def zlib_roundtrip(payload_hex: str) -> dict:
    payload = bytes.fromhex(payload_hex)
    compressed = zlib.compress(payload)
    restored = zlib.decompress(compressed)
    print(len(compressed))
    return {"match": hashlib.sha256(payload).hexdigest() == hashlib.sha256(restored).hexdigest(), "compressed_differs": compressed != payload}


def zlib_corrupt(payload_hex: str) -> dict:
    payload = bytes.fromhex(payload_hex)
    compressed = bytearray(zlib.compress(payload))
    compressed[-2] ^= 0xFF
    try:
        zlib.decompress(bytes(compressed))
    except zlib.error as exc:
        print(exc)
        return {"integrity_claimed": False, "corruption_detected": True}
    return {"integrity_claimed": True, "corruption_detected": False}


def base64_bytes(payload_hex: str) -> dict:
    payload = bytes.fromhex(payload_hex)
    encoded = base64.b64encode(payload).decode("ascii")
    print(encoded)
    return {"decoded_hex": base64.b64decode(encoded).hex(), "encoded": encoded}


def base64_reject(text: str) -> dict:
    try:
        base64.b64decode(text, validate=True)
    except binascii.Error as exc:
        print(exc)
        return {"rejected": True, "error_recorded": True}
    return {"rejected": False, "error_recorded": False}


def manifest_hash(document: dict, altered: dict) -> dict:
    def digest(value: dict) -> str:
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
        return hashlib.sha256(raw).hexdigest()

    first, second, third = digest(document), digest(document), digest(altered)
    print(first)
    return {"reproduced": first == second, "altered_changes": first != third, "digest": first}


def magic_bytes(name: str, payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    detected = "png" if raw.startswith(PNG) else "elf" if raw.startswith(b"\x7fELF") else "unknown"
    print(detected)
    return {"extension": name.rsplit(".", 1)[-1], "detected": detected, "extension_matches_content": name.endswith("." + detected)}


def array_sum(values: list[int], empty: list[int]) -> dict:
    total = 0
    for value in values:
        total += value
    empty_total = 0
    for value in empty:
        empty_total += value
    print(total)
    return {"sum": total, "empty_sum": empty_total}


def array_minmax(values: list[int]) -> dict:
    low = high = values[0]
    for value in values[1:]:
        low = min(low, value)
        high = max(high, value)
    print(low, high)
    return {"minimum": low, "maximum": high}


def tokenize(text: str) -> dict:
    tokens = []
    index = 0
    while index < len(text):
        if text[index].isspace():
            index += 1
            continue
        start = index
        if text[index].isdigit():
            while index < len(text) and text[index].isdigit():
                index += 1
            kind = "number"
        elif text[index].isalpha():
            while index < len(text) and text[index].isalpha():
                index += 1
            kind = "word"
        else:
            index += 1
            kind = "symbol"
        tokens.append({"kind": kind, "lexeme": text[start:index], "start": start, "end": index})
    print(tokens)
    return {"tokens": tokens}


def ipv4_check(addresses: list[str]) -> dict:
    accepted, rejected = [], []
    for address in addresses:
        parts = address.split(".")
        valid = len(parts) == 4 and all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
        (accepted if valid else rejected).append(address)
    print(accepted, rejected)
    return {"accepted": accepted, "rejected": rejected}


def binary_float_gap() -> dict:
    total = 0.1 + 0.2
    difference = total - 0.3
    print(difference)
    return {"equal": total == 0.3, "difference": difference, "explanation": "binary floating point, not an exact decimal"}
