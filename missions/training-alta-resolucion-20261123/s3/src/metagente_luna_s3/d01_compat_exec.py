"""Typed D01 compatibility executors for YAML, Protobuf, schema evolution and mixed serialization."""
from __future__ import annotations

import datetime as _datetime
import json
import re

import msgpack
import yaml


class _Yaml12Loader(yaml.SafeLoader):
    pass


_Yaml12Loader.yaml_implicit_resolvers = {
    first: [
        (tag, regexp)
        for tag, regexp in resolvers
        if tag not in {"tag:yaml.org,2002:bool", "tag:yaml.org,2002:timestamp"}
    ]
    for first, resolvers in yaml.SafeLoader.yaml_implicit_resolvers.items()
}
_Yaml12Loader.add_implicit_resolver(
    "tag:yaml.org,2002:bool",
    re.compile(r"^(?:true|false)$", re.IGNORECASE),
    list("tTfF"),
)


def _jsonable(value):
    if isinstance(value, (_datetime.date, _datetime.datetime)):
        return value.isoformat()
    if isinstance(value, list):
        return [_jsonable(item) for item in value]
    if isinstance(value, dict):
        return {key: _jsonable(item) for key, item in value.items()}
    return value


def yaml_types(yaml_text: str) -> dict:
    try:
        parsed = yaml.safe_load(yaml_text)
    except yaml.YAMLError as exc:
        return {"accepted": False, "rejected": True, "reason": type(exc).__name__}
    return {"accepted": True, "rejected": False, "parsed": _jsonable(parsed)}


def yaml_ambiguous(version: str, yaml_text: str) -> dict:
    if version not in {"1.1", "1.2"}:
        return {"accepted": False, "rejected": True, "reason": "unsupported YAML version"}
    try:
        loader = _Yaml12Loader if version == "1.2" else yaml.SafeLoader
        parsed = yaml.load(yaml_text, Loader=loader)
    except yaml.YAMLError as exc:
        return {"accepted": False, "rejected": True, "reason": type(exc).__name__}
    return {
        "accepted": True,
        "rejected": False,
        "declared_version": version,
        "parsed": _jsonable(parsed),
    }


def _varint(data: bytes, offset: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while offset < len(data) and shift <= 63:
        byte = data[offset]
        offset += 1
        value |= (byte & 0x7F) << shift
        if byte < 0x80:
            return value, offset
        shift += 7
    raise ValueError("truncated or oversized protobuf varint")


def protobuf_compat(payload_hex: str) -> dict:
    try:
        data = bytes.fromhex(payload_hex)
        offset = 0
        name = None
        unknown_fields = []
        while offset < len(data):
            tag, offset = _varint(data, offset)
            field_number, wire_type = tag >> 3, tag & 7
            if field_number == 0:
                raise ValueError("protobuf field number zero")
            if wire_type == 0:
                _, offset = _varint(data, offset)
                if field_number != 1:
                    unknown_fields.append(field_number)
            elif wire_type == 1:
                if offset + 8 > len(data):
                    raise ValueError("truncated fixed64")
                offset += 8
                unknown_fields.append(field_number)
            elif wire_type == 2:
                length, offset = _varint(data, offset)
                if length > len(data) - offset:
                    raise ValueError("truncated length-delimited field")
                value = data[offset:offset + length]
                offset += length
                if field_number == 1:
                    if name is not None:
                        raise ValueError("duplicate known field")
                    name = value.decode("utf-8")
                else:
                    unknown_fields.append(field_number)
            elif wire_type == 5:
                if offset + 4 > len(data):
                    raise ValueError("truncated fixed32")
                offset += 4
                unknown_fields.append(field_number)
            else:
                raise ValueError("unsupported protobuf wire type")
        return {
            "accepted": True,
            "rejected": False,
            "name": name,
            "unknown_fields": unknown_fields,
            "unknown_field_count": len(unknown_fields),
        }
    except (ValueError, UnicodeError, TypeError) as exc:
        return {"accepted": False, "rejected": True, "reason": str(exc)}


def schema_migrate(document: dict) -> dict:
    if not isinstance(document, dict) or document.get("version") != 1:
        return {"accepted": False, "rejected": True, "reason": "only schema version 1 is migratable"}
    migrated = dict(document)
    migrated["version"] = 2
    return {"accepted": True, "rejected": False, "document": migrated}


def unknown_field(record: dict, known_fields: list[str]) -> dict:
    if not isinstance(record, dict) or not isinstance(known_fields, list):
        return {"accepted": False, "rejected": True, "reason": "invalid record shape"}
    if any(field not in record for field in known_fields):
        return {"accepted": False, "rejected": True, "reason": "required known field missing"}
    if not all(isinstance(record[field], str) and record[field] for field in known_fields):
        return {"accepted": False, "rejected": True, "reason": "known field has invalid type or value"}
    unknown = sorted(set(record) - set(known_fields))
    return {
        "accepted": True,
        "rejected": False,
        "record": dict(record),
        "known_fields": sorted(known_fields),
        "unknown_fields": unknown,
        "unknown_fields_preserved": all(field in record for field in unknown),
    }


def mixed_roundtrip(document: dict) -> dict:
    try:
        if not isinstance(document, dict):
            raise TypeError("document must be an object")
        canonical = {key: document[key] for key in sorted(document)}
        payload = msgpack.packb(canonical, use_bin_type=True, strict_types=True)
        decoded = msgpack.unpackb(payload, raw=False, strict_map_key=False)
        json_text = json.dumps(decoded, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return {
            "accepted": True,
            "rejected": False,
            "msgpack_hex": payload.hex(),
            "decoded": decoded,
            "json_text": json_text,
        }
    except (TypeError, ValueError, OverflowError, msgpack.PackException, msgpack.UnpackException) as exc:
        return {"accepted": False, "rejected": True, "reason": type(exc).__name__}
