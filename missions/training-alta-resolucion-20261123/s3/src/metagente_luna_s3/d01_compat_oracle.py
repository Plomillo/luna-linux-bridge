"""Independent fixed-vector adjudicators for D01 compatibility executors."""
from __future__ import annotations

import json


def yaml_types(arguments: dict, observed: dict) -> dict:
    expected = {"name": "Luna", "enabled": True, "count": 7, "items": ["one", "two"]}
    return {
        "ok": observed.get("accepted") is True and observed.get("parsed") == expected,
        "method": "fixed typed YAML fixture oracle",
    }


def yaml_ambiguous(arguments: dict, observed: dict) -> dict:
    expected = {"enabled": "yes", "date": "2026-11-27", "explicit": True}
    ok = (
        arguments.get("version") == "1.2"
        and observed.get("accepted") is True
        and observed.get("declared_version") == "1.2"
        and observed.get("parsed") == expected
    )
    return {"ok": ok, "method": "YAML 1.2 fixed scalar-semantics oracle"}


def _read_varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise ValueError("invalid varint")


def protobuf_compat(arguments: dict, observed: dict) -> dict:
    try:
        data = bytes.fromhex(arguments["payload_hex"])
        offset = 0
        name = None
        unknown = []
        while offset < len(data):
            tag, offset = _read_varint(data, offset)
            field, wire = tag >> 3, tag & 7
            if field == 0:
                raise ValueError("field zero")
            if wire == 0:
                _, offset = _read_varint(data, offset)
                if field != 1:
                    unknown.append(field)
            elif wire == 2:
                length, offset = _read_varint(data, offset)
                if length > len(data) - offset:
                    raise ValueError("truncated field")
                value = data[offset:offset + length]
                offset += length
                if field == 1:
                    name = value.decode("utf-8")
                else:
                    unknown.append(field)
            elif wire in {1, 5}:
                width = 8 if wire == 1 else 4
                if offset + width > len(data):
                    raise ValueError("truncated fixed field")
                offset += width
                unknown.append(field)
            else:
                raise ValueError("unsupported wire type")
        ok = (
            observed.get("accepted") is True
            and observed.get("name") == name
            and observed.get("unknown_fields") == unknown
            and observed.get("unknown_field_count") == len(unknown)
        )
        return {"ok": ok, "method": "independent protobuf wire-format parser"}
    except (ValueError, UnicodeError, TypeError):
        return {"ok": observed.get("rejected") is True, "method": "independent malformed-wire rejection"}


def schema_migrate(arguments: dict, observed: dict) -> dict:
    source = arguments["document"]
    expected = dict(source)
    expected["version"] = 2
    ok = source.get("version") == 1 and observed.get("accepted") is True and observed.get("document") == expected
    return {"ok": ok, "method": "source-invariant preservation and version transition"}


def unknown_field(arguments: dict, observed: dict) -> dict:
    record = arguments["record"]
    known = sorted(arguments["known_fields"])
    valid = all(field in record and isinstance(record[field], str) and record[field] for field in known)
    unknown = sorted(set(record) - set(known))
    ok = (
        observed.get("accepted") is valid
        and observed.get("rejected") is (not valid)
        and (not valid or (
            observed.get("record") == record
            and observed.get("known_fields") == known
            and observed.get("unknown_fields") == unknown
            and observed.get("unknown_fields_preserved") is True
        ))
    )
    return {"ok": ok, "method": "independent required-field and unknown-field set comparison"}


def _pack(value) -> bytes:
    if value is None:
        return b"\xc0"
    if value is False:
        return b"\xc2"
    if value is True:
        return b"\xc3"
    if isinstance(value, int) and not isinstance(value, bool):
        if 0 <= value <= 127:
            return bytes([value])
        if -32 <= value < 0:
            return bytes([value & 0xff])
        raise ValueError("fixture integer outside fixed-vector subset")
    if isinstance(value, str):
        raw = value.encode("utf-8")
        if len(raw) > 31:
            raise ValueError("fixture string outside fixed-vector subset")
        return bytes([0xa0 | len(raw)]) + raw
    if isinstance(value, list):
        if len(value) > 15:
            raise ValueError("fixture array outside fixed-vector subset")
        return bytes([0x90 | len(value)]) + b"".join(_pack(item) for item in value)
    if isinstance(value, dict):
        keys = sorted(value)
        if len(keys) > 15:
            raise ValueError("fixture map outside fixed-vector subset")
        return bytes([0x80 | len(keys)]) + b"".join(_pack(key) + _pack(value[key]) for key in keys)
    raise TypeError(type(value).__name__)


def mixed_roundtrip(arguments: dict, observed: dict) -> dict:
    document = arguments["document"]
    try:
        expected_hex = _pack(document).hex()
        expected_json = json.dumps(document, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ok = (
            observed.get("accepted") is True
            and observed.get("msgpack_hex") == expected_hex
            and observed.get("decoded") == document
            and observed.get("json_text") == expected_json
        )
    except (TypeError, ValueError):
        ok = observed.get("rejected") is True
    return {"ok": ok, "method": "independent fixed MessagePack byte vector and JSON structure"}
