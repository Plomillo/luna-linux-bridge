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
from decimal import Decimal, InvalidOperation

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
    try:
        value = Decimal(text)
    except InvalidOperation:
        return {"rejected": True, "reason": "invalid-decimal"}
    print(value)
    return {"rejected": False, "text": str(value), "used_binary_float": False}


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
    try:
        payload = bytes.fromhex(payload_hex)
    except ValueError:
        return {"rejected": True, "reason": "invalid-hex-input"}
    encoded = base64.b64encode(payload).decode("ascii")
    print(encoded)
    return {"rejected": False, "decoded_hex": base64.b64decode(encoded).hex(), "encoded": encoded}


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


def binary_float_gap(left: float, right: float, target: float) -> dict:
    total = left + right
    difference = total - target
    decimal_exact = Decimal(str(left)) + Decimal(str(right)) == Decimal(str(target))
    print(difference)
    return {"equal": total == target, "difference": difference, "decimal_exact": decimal_exact, "explanation": "binary floating point compared with exact decimal arithmetic"}


def protobuf_old_reader(wire_hex: str) -> dict:
    """Read field 1 and skip unknown protobuf fields using their wire type."""
    try:
        raw = bytes.fromhex(wire_hex)
    except ValueError:
        return {"rejected": True, "reason": "invalid-hex"}
    cursor = 0

    def varint() -> int:
        nonlocal cursor
        value = 0
        for shift in range(0, 70, 7):
            if cursor >= len(raw):
                raise ValueError("truncated-varint")
            byte = raw[cursor]
            cursor += 1
            value |= (byte & 0x7F) << shift
            if byte < 0x80:
                return value
        raise ValueError("varint-overflow")

    known: dict[str, int] = {}
    unknown: list[int] = []
    try:
        while cursor < len(raw):
            key = varint()
            field_number, wire_type = key >> 3, key & 7
            if field_number == 0:
                raise ValueError("zero-field-number")
            if wire_type == 0:
                value = varint()
                if field_number == 1:
                    known[str(field_number)] = value
                else:
                    unknown.append(field_number)
            elif wire_type == 1:
                if len(raw) - cursor < 8:
                    raise ValueError("truncated-fixed64")
                cursor += 8
                unknown.append(field_number)
            elif wire_type == 2:
                size = varint()
                if size > len(raw) - cursor:
                    raise ValueError("truncated-length-delimited")
                payload = raw[cursor:cursor + size]
                cursor += size
                if field_number == 1:
                    try:
                        known[str(field_number)] = int(payload.decode("utf-8"))
                    except (UnicodeError, ValueError):
                        known[str(field_number)] = payload.hex()
                else:
                    unknown.append(field_number)
            elif wire_type == 5:
                if len(raw) - cursor < 4:
                    raise ValueError("truncated-fixed32")
                cursor += 4
                unknown.append(field_number)
            else:
                raise ValueError("unsupported-wire-type")
    except ValueError as exc:
        return {"rejected": True, "reason": str(exc)}
    return {"rejected": False, "accepted": True, "known_fields": known, "unknown_fields": unknown, "consumed": cursor}


def schema_migrate(document: dict) -> dict:
    if not isinstance(document, dict) or document.get("version") != 1:
        return {"rejected": True, "reason": "unsupported-version"}
    name, count = document.get("name"), document.get("count")
    if not isinstance(name, str) or not isinstance(count, int) or isinstance(count, bool) or count < 0:
        return {"rejected": True, "reason": "invalid-invariant-field"}
    migrated = {"version": 2, "name": name, "count": count, "enabled": True}
    return {"rejected": False, "migrated": True, "document": migrated, "invariants": {"name": name, "count": count}}


def schema_unknown_field(record: dict, known_fields: list[str]) -> dict:
    if not isinstance(record, dict) or not isinstance(known_fields, list):
        return {"rejected": True, "reason": "invalid-record"}
    known: dict = {}
    unknown: dict = {}
    for name in known_fields:
        if name not in record:
            continue
        value = record[name]
        if name == "name" and not isinstance(value, str):
            return {"rejected": True, "reason": "known-field-type"}
        if name == "version" and (not isinstance(value, int) or isinstance(value, bool)):
            return {"rejected": True, "reason": "known-field-type"}
        known[name] = value
    unknown = {key: value for key, value in record.items() if key not in known_fields}
    return {"rejected": False, "accepted": True, "known": known, "unknown": unknown, "policy": "PRESERVE_UNKNOWN_SEPARATELY"}


def _cbor_head(major: int, value: int) -> bytes:
    if value < 0:
        raise ValueError("negative-length")
    prefix = major << 5
    if value < 24:
        return bytes([prefix | value])
    if value <= 0xFF:
        return bytes([prefix | 24, value])
    if value <= 0xFFFF:
        return bytes([prefix | 25]) + value.to_bytes(2, "big")
    if value <= 0xFFFFFFFF:
        return bytes([prefix | 26]) + value.to_bytes(4, "big")
    if value <= 0xFFFFFFFFFFFFFFFF:
        return bytes([prefix | 27]) + value.to_bytes(8, "big")
    raise ValueError("integer-too-large")


def _cbor_encode(value) -> bytes:
    if value is None:
        return b"\xf6"
    if value is False:
        return b"\xf4"
    if value is True:
        return b"\xf5"
    if isinstance(value, int):
        return _cbor_head(0, value) if value >= 0 else _cbor_head(1, -1 - value)
    if isinstance(value, str):
        raw = value.encode("utf-8")
        return _cbor_head(3, len(raw)) + raw
    if isinstance(value, list):
        return _cbor_head(4, len(value)) + b"".join(_cbor_encode(item) for item in value)
    if isinstance(value, dict):
        if any(not isinstance(key, str) for key in value):
            raise TypeError("unsupported-map-key")
        pairs = [(_cbor_encode(key), _cbor_encode(item)) for key, item in value.items()]
        pairs.sort(key=lambda pair: (len(pair[0]), pair[0]))
        return _cbor_head(5, len(pairs)) + b"".join(key + item for key, item in pairs)
    raise TypeError("unsupported-value-type")


def _cbor_decode(raw: bytes) -> object:
    cursor = 0

    def uint(additional: int) -> int:
        nonlocal cursor
        if additional < 24:
            return additional
        sizes = {24: 1, 25: 2, 26: 4, 27: 8}
        size = sizes.get(additional)
        if size is None or len(raw) - cursor < size:
            raise ValueError("invalid-or-truncated-cbor-length")
        result = int.from_bytes(raw[cursor:cursor + size], "big")
        cursor += size
        return result

    def read():
        nonlocal cursor
        if cursor >= len(raw):
            raise ValueError("truncated-cbor-item")
        initial = raw[cursor]
        cursor += 1
        major, additional = initial >> 5, initial & 31
        if major in (0, 1):
            number = uint(additional)
            return number if major == 0 else -1 - number
        if major in (2, 3):
            length = uint(additional)
            if length > len(raw) - cursor:
                raise ValueError("truncated-cbor-string")
            value = raw[cursor:cursor + length]
            cursor += length
            return value if major == 2 else value.decode("utf-8")
        if major == 4:
            return [read() for _ in range(uint(additional))]
        if major == 5:
            result = {}
            for _ in range(uint(additional)):
                key, value = read(), read()
                if key in result:
                    raise ValueError("duplicate-cbor-map-key")
                result[key] = value
            return result
        if major == 7 and additional == 20:
            return False
        if major == 7 and additional == 21:
            return True
        if major == 7 and additional == 22:
            return None
        raise ValueError("unsupported-cbor-type")

    value = read()
    if cursor != len(raw):
        raise ValueError("trailing-cbor-data")
    return value


def cbor_roundtrip(document: dict) -> dict:
    try:
        encoded = _cbor_encode(document)
        decoded = _cbor_decode(encoded)
    except (TypeError, ValueError, UnicodeError) as exc:
        return {"rejected": True, "reason": str(exc)}
    return {"rejected": False, "accepted": True, "wire_hex": encoded.hex(), "decoded": decoded, "same_types": type(decoded) is type(document) and decoded == document}
