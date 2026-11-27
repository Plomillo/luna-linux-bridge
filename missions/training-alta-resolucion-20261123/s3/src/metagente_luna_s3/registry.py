"""Capabilities that have a schema and an oracle id. Unknown ids cannot run."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable

from pydantic import BaseModel

from metagente_luna_s3 import (
    archive_exec,
    archive_oracle,
    batch3_exec,
    batch3_oracle,
    batch4_exec,
    batch4_oracle,
    batch5_exec,
    batch5_oracle,
    batch6_exec,
    batch6_oracle,
    d01_exec,
    d01_oracle,
    format_exec,
    format_oracle,
    more_exec,
    more_oracle,
)
from metagente_luna_s3.independent_oracles import cidr_bounds_oracle
from metagente_luna_s4 import c05_preflight, c05_preflight_oracle


class Capability(BaseModel):
    capability_id: str
    version: str
    input_schema: dict
    output_schema: dict
    oracle_id: str
    status: str


def cidr_bounds(cidr: str) -> dict:
    """Calculate IPv4 CIDR bounds; invalid prefixes return an explicit rejection."""
    try:
        address, prefix_s = cidr.split("/")
        octets = address.split(".")
        if len(octets) != 4 or any(not part.isdecimal() for part in octets):
            return {"accepted": False, "rejected": True, "reason": "invalid IPv4 address"}
        values = [int(part) for part in octets]
        if any(value < 0 or value > 255 for value in values):
            return {"accepted": False, "rejected": True, "reason": "IPv4 octet out of range"}
        if not prefix_s.isdecimal() or not 0 <= int(prefix_s) <= 32:
            return {"accepted": False, "rejected": True, "reason": "IPv4 prefix length out of range"}
        ip = 0
        for part in values:
            ip = (ip << 8) | part
        prefix = int(prefix_s)
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        network = ip & mask
        broadcast = network | (0xFFFFFFFF ^ mask)

        def dotted(value: int) -> str:
            return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))

        return {"network": dotted(network), "broadcast": dotted(broadcast)}
    except (ValueError, TypeError):
        return {"accepted": False, "rejected": True, "reason": "malformed CIDR"}


def cidr_oracle(cidr: str, observed: dict) -> dict:
    try:
        network = ipaddress.ip_interface(cidr).network
    except ValueError:
        ok = observed.get("accepted") is False and observed.get("rejected") is True
        return {"ok": ok, "expected": {"rejected": True}, "method": "independent ipaddress input validation"}
    ok = (
        observed.get("accepted") is not False
        and observed.get("network") == str(network.network_address)
        and observed.get("broadcast") == str(network.broadcast_address)
    )
    return {"ok": ok, "expected": {"network": str(network.network_address), "broadcast": str(network.broadcast_address)}, "method": "independent ipaddress reference implementation"}


_OBJECT = {"type": "object"}
_TEXT = {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False}


def _cap(name: str, oracle: str, schema: dict) -> Capability:
    return Capability(capability_id=name, version="1", input_schema=schema, output_schema=_OBJECT, oracle_id=oracle, status="TESTED")


REGISTRY: dict[str, Capability] = {
    "cidr_bounds": _cap("cidr_bounds", "ipaddress", {"type": "object", "required": ["cidr"], "properties": {"cidr": {"type": "string"}}, "additionalProperties": False}),
    "utf8_roundtrip": _cap("utf8_roundtrip", "utf8_manual", _TEXT),
    "utf8_reject_invalid": _cap("utf8_reject_invalid", "utf8_state_machine", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "utf16_encode": _cap("utf16_encode", "utf16_units", {"type": "object", "required": ["text", "byte_order"], "properties": {"text": {"type": "string"}, "byte_order": {"type": "string"}}, "additionalProperties": False}),
    "u32_endian": _cap("u32_endian", "shifts", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "uint16_bounds": _cap("uint16_bounds", "uint16_range", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "int16_values": _cap("int16_values", "int16_range", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "twos_complement_16": _cap("twos_complement_16", "sign_bit", {"type": "object", "required": ["hex_value", "width"], "properties": {"hex_value": {"type": "string"}, "width": {"type": "integer"}}, "additionalProperties": False}),
    "float_bits": _cap("float_bits", "published_bits", {"type": "object", "required": ["value", "kind", "reference"], "properties": {"value": {"type": "number"}, "kind": {"type": "integer"}, "reference": {"type": "string"}}, "additionalProperties": False}),
    "nan_policy": _cap("nan_policy", "nan_bits", {"type": "object", "required": ["value_kind"], "properties": {"value_kind": {"type": "string", "enum": ["nan", "negative-nan", "finite"]}}, "additionalProperties": False}),
    "inf_policy": _cap("inf_policy", "inf_signs", {"type": "object", "required": ["value_kind"], "properties": {"value_kind": {"type": "string", "enum": ["both", "positive", "negative", "finite"]}}, "additionalProperties": False}),
    "subnormal_f32": _cap("subnormal_f32", "subnormal_bits", {"type": "object", "required": ["value_kind"], "properties": {"value_kind": {"type": "string", "enum": ["smallest-subnormal", "zero", "smallest-normal"]}}, "additionalProperties": False}),
    "nfc_compare": _cap("nfc_compare", "nfc_table", {"type": "object", "required": ["decomposed", "composed"], "properties": {"decomposed": {"type": "string"}, "composed": {"type": "string"}}, "additionalProperties": False}),
    "nfd_decompose": _cap("nfd_decompose", "nfd_table", {"type": "object", "required": ["composed"], "properties": {"composed": {"type": "string"}}, "additionalProperties": False}),
    "nfkc_compat": _cap("nfkc_compat", "nfkc_table", {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False}),
    "bom_policy": _cap("bom_policy", "bom_visible", {"type": "object", "required": ["without_bom", "with_bom_visible"], "properties": {"without_bom": {"type": "string"}, "with_bom_visible": {"type": "string"}}, "additionalProperties": False}),
    "yaml_ambiguous": _cap("yaml_ambiguous", "yaml_ambiguous_oracle", {"type": "object", "required": ["text", "schema_version"], "properties": {"text": {"type": "string"}, "schema_version": {"type": "string", "enum": ["1.1", "1.2"]}}, "additionalProperties": False}),
    "yaml_types": _cap("yaml_types", "yaml_types_oracle", {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False}),
    "json_roundtrip": _cap("json_roundtrip", "json_types", {"type": "object", "required": ["document"], "properties": {"document": {"type": "object"}}, "additionalProperties": False}),
    "json_reject": _cap("json_reject", "json_scan", {"type": "object", "required": ["texts"], "properties": {"texts": {"type": "array"}}, "additionalProperties": False}),
    "sha256_text": _cap("sha256_text", "nist_abc", _TEXT),
    "text_units": _cap("text_units", "units", _TEXT),
    "crlf_roundtrip": _cap("crlf_roundtrip", "crlf_lines", _TEXT),
    "crlf_to_lf": _cap("crlf_to_lf", "lf_only", _TEXT),
    "csv_roundtrip": _cap("csv_roundtrip", "csv_rows", {"type": "object", "required": ["rows"], "properties": {"rows": {"type": "array"}}, "additionalProperties": False}),
    "csv_newline": _cap("csv_newline", "one_record", _TEXT),
    "json_text": _cap("json_text", "json_string", _TEXT),
    "duplicate_keys": _cap("duplicate_keys", "key_count", _TEXT),
    "canonical_json": _cap("canonical_json", "canonical_pair", {"type": "object", "required": ["left", "right"], "properties": {"left": {"type": "object"}, "right": {"type": "object"}}, "additionalProperties": False}),
    "xml_expanded": _cap("xml_expanded", "expanded_name", {"type": "object", "required": ["document"], "properties": {"document": {"type": "string"}}, "additionalProperties": False}),
    "xml_entities": _cap("xml_entities", "predefined_entities", {"type": "object", "required": ["document"], "properties": {"document": {"type": "string"}}, "additionalProperties": False}),
    "xml_unbalanced": _cap("xml_unbalanced", "parse_error", {"type": "object", "required": ["document"], "properties": {"document": {"type": "string"}}, "additionalProperties": False}),
    "framed_record": _cap("framed_record", "frame_sum", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "truncated_records": _cap("truncated_records", "cuts", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "oversize_length": _cap("oversize_length", "huge_length", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "float32_exactness": _cap("float32_exactness", "f32_table", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "decimal_text": _cap("decimal_text", "decimal_literal", _TEXT),
    "three_states": _cap("three_states", "state_table", {"type": "object", "required": ["present", "absent_key"], "properties": {"present": {"type": "object"}, "absent_key": {"type": "string"}}, "additionalProperties": False}),
    "protobuf_old_reader": _cap("protobuf_old_reader", "protobuf_wire_oracle", {"type": "object", "required": ["wire_hex"], "properties": {"wire_hex": {"type": "string"}}, "additionalProperties": False}),
    "schema_migrate": _cap("schema_migrate", "schema_v2_oracle", {"type": "object", "required": ["document"], "properties": {"document": {"type": "object"}}, "additionalProperties": False}),
    "schema_unknown_field": _cap("schema_unknown_field", "unknown_field_oracle", {"type": "object", "required": ["record", "known_fields"], "properties": {"record": {"type": "object"}, "known_fields": {"type": "array", "items": {"type": "string"}}}, "additionalProperties": False}),
    "cbor_roundtrip": _cap("cbor_roundtrip", "cbor_vector_oracle", {"type": "object", "required": ["document"], "properties": {"document": {"type": "object"}}, "additionalProperties": False}),
    "zlib_roundtrip": _cap("zlib_roundtrip", "payload_hash", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "zlib_corrupt": _cap("zlib_corrupt", "damaged", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "base64_bytes": _cap("base64_bytes", "b64_table", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "base64_reject": _cap("base64_reject", "bad_padding", _TEXT),
    "manifest_hash": _cap("manifest_hash", "stable_digest", {"type": "object", "required": ["document", "altered"], "properties": {"document": {"type": "object"}, "altered": {"type": "object"}}, "additionalProperties": False}),
    "magic_bytes": _cap("magic_bytes", "signature", {"type": "object", "required": ["name", "payload_hex"], "properties": {"name": {"type": "string"}, "payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "elf_header": _cap("elf_header", "elf_header_oracle", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "array_sum": _cap("array_sum", "total", {"type": "object", "required": ["values", "empty"], "properties": {"values": {"type": "array"}, "empty": {"type": "array"}}, "additionalProperties": False}),
    "array_minmax": _cap("array_minmax", "extremes", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "tokenize": _cap("tokenize", "token_vector", _TEXT),
    "ipv4_check": _cap("ipv4_check", "ip_module", {"type": "object", "required": ["addresses"], "properties": {"addresses": {"type": "array"}}, "additionalProperties": False}),
    "binary_float_gap": _cap("binary_float_gap", "decimal_gap", {"type": "object", "required": ["left", "right", "target"], "properties": {"left": {"type": "number"}, "right": {"type": "number"}, "target": {"type": "number"}}, "additionalProperties": False}),
    "duplicates": _cap("duplicates", "repeated", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "brackets": _cap("brackets", "bracket_pairs", {"type": "object", "required": ["texts"], "properties": {"texts": {"type": "array"}}, "additionalProperties": False}),
    "binary_insert": _cap("binary_insert", "sorted_values", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "arithmetic": _cap("arithmetic", "stated_value", {"type": "object", "required": ["expression"], "properties": {"expression": {"type": "string"}}, "additionalProperties": False}),
    "child_status": _cap("child_status", "exit_seven", {"type": "object", "required": ["exit_code"], "properties": {"exit_code": {"type": "integer", "minimum": 0, "maximum": 255}}, "additionalProperties": False}),
    "ipv6_reject": _cap("ipv6_reject", "two_compressions", {"type": "object", "required": ["address"], "properties": {"address": {"type": "string"}}, "additionalProperties": False}),
    "ipv6_prefix": _cap("ipv6_prefix", "stated_prefix", {"type": "object", "required": ["cidr"], "properties": {"cidr": {"type": "string"}}, "additionalProperties": False}),
    "threshold": _cap("threshold", "fever_rule", {"type": "object", "required": ["low", "high", "limit"], "properties": {"low": {"type": "number"}, "high": {"type": "number"}, "limit": {"type": "number"}}, "additionalProperties": False}),
    "l2_norm": _cap("l2_norm", "thirteen", {"type": "object", "required": ["components"], "properties": {"components": {"type": "array"}}, "additionalProperties": False}),
    "ratio": _cap("ratio", "stated_ratio", {"type": "object", "required": ["numerator", "denominator"], "properties": {"numerator": {"type": "integer"}, "denominator": {"type": "integer"}}, "additionalProperties": False}),
    "precision_recall": _cap("precision_recall", "rates", {"type": "object", "required": ["true_positive", "false_positive", "false_negative"], "properties": {"true_positive": {"type": "integer"}, "false_positive": {"type": "integer"}, "false_negative": {"type": "integer"}}, "additionalProperties": False}),
    "f1_score": _cap("f1_score", "harmonic", {"type": "object", "required": ["precision", "recall"], "properties": {"precision": {"type": "number"}, "recall": {"type": "number"}}, "additionalProperties": False}),
    "increment": _cap("increment", "counted", {"type": "object", "required": ["times"], "properties": {"times": {"type": "integer"}}, "additionalProperties": False}),
    "pearson": _cap("pearson", "correlation", {"type": "object", "required": ["left", "right"], "properties": {"left": {"type": "array"}, "right": {"type": "array"}}, "additionalProperties": False}),
    "acf_lag0": _cap("acf_lag0", "lag_identity", {"type": "object", "required": ["values"], "properties": {"values": {"type": "array"}}, "additionalProperties": False}),
    "linear_integral": _cap("linear_integral", "half", {"type": "object", "required": ["panels"], "properties": {"panels": {"type": "integer", "minimum": 1}}, "additionalProperties": False}),
    "square_integral": _cap("square_integral", "one_third", {"type": "object", "required": ["panels"], "properties": {"panels": {"type": "integer", "minimum": 1}}, "additionalProperties": False}),
    "cosine_set": _cap("cosine_set", "axis_cosines", {"type": "object", "required": ["pairs"], "properties": {"pairs": {"type": "array"}}, "additionalProperties": False}),
    "confined": _cap("confined", "escapes", {"type": "object", "required": ["requested"], "properties": {"requested": {"type": "string"}}, "additionalProperties": False}),
    "request_log": _cap("request_log", "request_counts", {"type": "object", "required": ["successes", "failures"], "properties": {"successes": {"type": "integer"}, "failures": {"type": "integer"}}, "additionalProperties": False}),
    "stable_ages": _cap("stable_ages", "stable_age_records", {
        "type": "object", "required": ["records"],
        "properties": {"records": {"type": "array", "items": {
            "type": "object", "required": ["id", "age"],
            "properties": {"id": {"type": "string"}, "age": {"type": "integer"}},
            "additionalProperties": False,
        }}}, "additionalProperties": False,
    }),
    "stack_sequence": _cap("stack_sequence", "stack_state_machine", {
        "type": "object", "required": ["steps"],
        "properties": {"steps": {"type": "array", "items": {"type": "string"}}},
        "additionalProperties": False,
    }),
}

REGISTRY["c05_preflight_blocked"] = _cap(
    "c05_preflight_blocked", "c05_preflight_blocked_oracle",
    {"type": "object", "required": ["case_id", "blocker_code", "phase", "details"],
     "properties": {"case_id": {"type": "string"}, "blocker_code": {"type": "string"},
                    "phase": {"type": "string"}, "details": {"type": "string"}},
     "additionalProperties": False},
)

_ARCHIVE_SCHEMAS = {
    "zip_path_safety": {"type": "object", "required": ["entries"], "properties": {"entries": {"type": "array", "items": {"type": "object", "required": ["name", "data_hex"], "properties": {"name": {"type": "string"}, "data_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}}, "additionalProperties": False},
    "zip_crc": {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string", "minLength": 2, "pattern": "^([0-9a-fA-F]{2})+$"}}, "additionalProperties": False},
    "zip_duplicates": {"type": "object", "required": ["names", "payloads_hex"], "properties": {"names": {"type": "array", "items": {"type": "string"}}, "payloads_hex": {"type": "array", "items": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}}, "additionalProperties": False},
    "tar_offsets": {"type": "object", "required": ["entries"], "properties": {"entries": {"type": "array", "minItems": 3, "items": {"type": "object", "required": ["name", "data_hex"], "properties": {"name": {"type": "string"}, "data_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}}, "additionalProperties": False},
    "tar_truncated": {"type": "object", "required": ["first_hex", "second_hex", "cut_into_second"], "properties": {"first_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})+$"}, "second_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})+$"}, "cut_into_second": {"type": "integer", "minimum": 0}}, "additionalProperties": False},
    "gzip_crc": {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False},
}
_ARCHIVE_ORACLES = {"zip_path_safety": "archive_path", "zip_crc": "archive_zip_crc", "zip_duplicates": "archive_zip_duplicates", "tar_offsets": "archive_tar_offsets", "tar_truncated": "archive_tar_truncated", "gzip_crc": "archive_gzip_crc"}
for _archive_name, _archive_oracle in _ARCHIVE_ORACLES.items():
    REGISTRY[_archive_name] = _cap(_archive_name, _archive_oracle, _ARCHIVE_SCHEMAS[_archive_name])

_FORMAT_SCHEMAS = {
    "sqlite_header": {"type": "object", "required": ["page_size"], "properties": {"page_size": {"type": "integer", "enum": [512, 1024, 2048, 4096, 8192, 16384, 32768, 65536]}}, "additionalProperties": False},
    "sqlite_integrity": {"type": "object", "required": ["corrupt", "values"], "properties": {"corrupt": {"type": "boolean"}, "values": {"type": "array", "items": {"type": "string"}}}, "additionalProperties": False},
    "wasm_header": {"type": "object", "required": ["magic_hex", "version"], "properties": {"magic_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2}){4}$"}, "version": {"type": "integer", "minimum": 0, "maximum": 4294967295}}, "additionalProperties": False},
    "png_chunks": {"type": "object", "required": ["chunks", "tamper_index"], "properties": {"chunks": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["type", "data_hex"], "properties": {"type": {"type": "string", "pattern": "^[A-Z]{4}$"}, "data_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}, "tamper_index": {"type": "integer", "minimum": -1, "maximum": 100}}, "additionalProperties": False},
    "unknown_format": {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string", "minLength": 2, "pattern": "^([0-9a-fA-F]{2})+$"}}, "additionalProperties": False},
    "block_entropy": {"type": "object", "required": ["payload_hex", "block_size"], "properties": {"payload_hex": {"type": "string", "minLength": 2, "pattern": "^([0-9a-fA-F]{2})+$"}, "block_size": {"type": "integer", "minimum": 1, "maximum": 1048576}}, "additionalProperties": False},
    "binary_diff": {"type": "object", "required": ["left_hex", "right_hex"], "properties": {"left_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}, "right_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False},
    "bounded_declared_size": {"type": "object", "required": ["declared_size", "payload_hex"], "properties": {"declared_size": {"type": "integer", "minimum": 0}, "payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False},
    "reproducible_structure": {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False},
    "jpeg_markers": {"type": "object", "required": ["segments", "truncate_last"], "properties": {"segments": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "object", "required": ["marker", "payload_hex"], "properties": {"marker": {"type": "string", "enum": ["DQT", "SOF0"]}, "payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})+$"}}, "additionalProperties": False}}, "truncate_last": {"type": "boolean"}}, "additionalProperties": False},
    "partial_recovery": {"type": "object", "required": ["header_hex", "payload_hex", "expected_magic_hex"], "properties": {"header_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})+$"}, "payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}, "expected_magic_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})+$"}}, "additionalProperties": False},
    "timestamp_provenance": {"type": "object", "required": ["metadata_timestamp", "filesystem_timestamp"], "properties": {"metadata_timestamp": {"type": "integer"}, "filesystem_timestamp": {"type": "integer"}}, "additionalProperties": False},
    "dependency_graph": {"type": "object", "required": ["root", "nodes", "edges"], "properties": {"root": {"type": "string"}, "nodes": {"type": "array", "items": {"type": "string"}, "uniqueItems": True}, "edges": {"type": "array", "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "string"}}}}, "additionalProperties": False},
    "protocol_version_diff": {"type": "object", "required": ["old_fields", "new_fields"], "properties": {"old_fields": {"type": "array", "items": {"type": "object", "required": ["name", "width", "offset"], "properties": {"name": {"type": "string"}, "width": {"type": "integer", "minimum": 1}, "offset": {"type": "integer", "minimum": 0}}, "additionalProperties": False}}, "new_fields": {"type": "array", "items": {"type": "object", "required": ["name", "width", "offset"], "properties": {"name": {"type": "string"}, "width": {"type": "integer", "minimum": 1}, "offset": {"type": "integer", "minimum": 0}}, "additionalProperties": False}}}, "additionalProperties": False},
    "section_overlaps": {"type": "object", "required": ["sections"], "properties": {"sections": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["name", "offset", "size"], "properties": {"name": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "size": {"type": "integer", "minimum": 1}}, "additionalProperties": False}}}, "additionalProperties": False},
    "nested_zip_tar": {"type": "object", "required": ["entries"], "properties": {"entries": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["name", "data_hex"], "properties": {"name": {"type": "string"}, "data_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}}, "additionalProperties": False},
    "forensic_report": {"type": "object", "required": ["payload_hex", "declared_size", "stored_crc32", "sections"], "properties": {"payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}, "declared_size": {"type": "integer", "minimum": 0}, "stored_crc32": {"type": "integer", "minimum": 0, "maximum": 4294967295}, "sections": {"type": "array", "items": {"type": "object", "required": ["name", "offset", "size"], "properties": {"name": {"type": "string"}, "offset": {"type": "integer", "minimum": 0}, "size": {"type": "integer", "minimum": 1}}, "additionalProperties": False}}}, "additionalProperties": False},
    "seven_zip_list": {"type": "object", "required": ["entries"], "properties": {"entries": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["name", "data_hex"], "properties": {"name": {"type": "string", "minLength": 1}, "data_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}}, "additionalProperties": False},
    "seven_zip_missing_volume": {"type": "object", "required": ["payload_hex", "volume_size", "missing_part"], "properties": {"payload_hex": {"type": "string", "minLength": 2, "maxLength": 32768, "pattern": "^([0-9a-fA-F]{2})+$"}, "volume_size": {"type": "integer", "enum": [1024, 2048]}, "missing_part": {"type": "integer", "minimum": 1, "maximum": 99}}, "additionalProperties": False},
    "wasm_sections": {"type": "object", "required": ["sections", "truncate_index"], "properties": {"sections": {"type": "array", "maxItems": 100, "items": {"type": "object", "required": ["section_id", "payload_hex"], "properties": {"section_id": {"type": "integer", "minimum": 0, "maximum": 12}, "payload_hex": {"type": "string", "pattern": "^([0-9a-fA-F]{2})*$"}}, "additionalProperties": False}}, "truncate_index": {"type": "integer", "minimum": -1, "maximum": 99}}, "additionalProperties": False},
    "wasm_type_indices": {"type": "object", "required": ["type_count", "function_type_indices"], "properties": {"type_count": {"type": "integer", "minimum": 0}, "function_type_indices": {"type": "array", "items": {"type": "integer"}}}, "additionalProperties": False},
    "pdf_objects": {"type": "object", "required": ["references", "missing_object"], "properties": {"references": {"type": "array", "items": {"type": "array", "minItems": 2, "maxItems": 2, "items": {"type": "integer", "minimum": 0}}}, "missing_object": {"type": "integer", "minimum": 0}}, "additionalProperties": False},
    "pdf_xref": {"type": "object", "required": ["corrupt_object"], "properties": {"corrupt_object": {"type": "integer", "minimum": 0, "maximum": 2}}, "additionalProperties": False},
    "pdf_encryption_boundary": {"type": "object", "required": ["pdf_hex"], "properties": {"pdf_hex": {"type": "string", "minLength": 10, "pattern": "^([0-9a-fA-F]{2})+$"}}, "additionalProperties": False},
    "elf_symbol_tables": {"type": "object", "required": ["payload_hex", "require_complete"], "properties": {"payload_hex": {"type": "string", "minLength": 20, "maxLength": 32768, "pattern": "^([0-9a-fA-F]{2})+$"}, "require_complete": {"type": "boolean"}, "required_symbols": {"type": "array", "items": {"type": "string"}, "uniqueItems": True}}, "additionalProperties": False},
    "elf_host_compatibility": {"type": "object", "required": ["payload_hex", "native_machine"], "properties": {"payload_hex": {"type": "string", "minLength": 40, "pattern": "^([0-9a-fA-F]{2})+$"}, "native_machine": {"type": "integer", "minimum": 0, "maximum": 65535}}, "additionalProperties": False},
}
_FORMAT_ORACLES = {"sqlite_header": "sqlite_header_independent", "sqlite_integrity": "sqlite_integrity_independent", "wasm_header": "wasm_header_independent", "png_chunks": "png_chunks_independent", "unknown_format": "unknown_format_independent", "block_entropy": "block_entropy_independent", "binary_diff": "binary_diff_independent", "bounded_declared_size": "bounded_size_independent", "reproducible_structure": "reproducible_structure_independent", "jpeg_markers": "jpeg_markers_independent", "partial_recovery": "partial_recovery_independent", "timestamp_provenance": "timestamp_provenance_independent", "dependency_graph": "dependency_graph_independent", "protocol_version_diff": "protocol_version_diff_independent", "section_overlaps": "section_overlaps_independent", "nested_zip_tar": "nested_zip_tar_independent", "forensic_report": "forensic_report_independent", "seven_zip_list": "seven_zip_list_independent", "seven_zip_missing_volume": "seven_zip_missing_volume_independent", "wasm_sections": "wasm_sections_independent", "wasm_type_indices": "wasm_type_indices_independent", "pdf_objects": "pdf_objects_independent", "pdf_xref": "pdf_xref_independent", "pdf_encryption_boundary": "pdf_encryption_boundary_independent", "elf_symbol_tables": "elf_symbol_tables_independent", "elf_host_compatibility": "elf_host_compatibility_independent"}
for _format_name, _format_oracle in _FORMAT_ORACLES.items():
    REGISTRY[_format_name] = _cap(_format_name, _format_oracle, _FORMAT_SCHEMAS[_format_name])

ORACLES: dict[str, Callable[..., dict]] = {
    "ipaddress": cidr_bounds_oracle,
    "utf8_manual": d01_oracle.utf8_manual,
    "utf8_state_machine": d01_oracle.utf8_state_machine,
    "utf16_units": d01_oracle.utf16_units,
    "shifts": d01_oracle.shifts,
    "uint16_range": d01_oracle.uint16_range,
    "int16_range": d01_oracle.int16_range,
    "sign_bit": d01_oracle.sign_bit,
    "published_bits": d01_oracle.published_bits,
    "nan_bits": d01_oracle.nan_bits,
    "inf_signs": d01_oracle.inf_signs,
    "subnormal_bits": d01_oracle.subnormal_bits,
    "nfc_table": d01_oracle.nfc_table,
    "nfd_table": d01_oracle.nfd_table,
    "nfkc_table": d01_oracle.nfkc_table,
    "bom_visible": d01_oracle.bom_visible,
    "json_types": d01_oracle.json_types,
    "yaml_types_oracle": d01_oracle.yaml_types_oracle,
    "yaml_ambiguous_oracle": d01_oracle.yaml_ambiguous_oracle,
    "json_scan": d01_oracle.json_scan,
    "nist_abc": d01_oracle.nist_abc,
    "units": more_oracle.units,
    "crlf_lines": more_oracle.crlf_lines,
    "lf_only": more_oracle.lf_only,
    "csv_rows": more_oracle.csv_rows,
    "one_record": more_oracle.one_record,
    "json_string": more_oracle.json_string,
    "key_count": more_oracle.key_count,
    "canonical_pair": more_oracle.canonical_pair,
    "expanded_name": more_oracle.expanded_name,
    "predefined_entities": more_oracle.predefined_entities,
    "parse_error": more_oracle.parse_error,
    "frame_sum": more_oracle.frame_sum,
    "cuts": more_oracle.cuts,
    "huge_length": more_oracle.huge_length,
    "f32_table": more_oracle.f32_table,
    "decimal_literal": more_oracle.decimal_literal,
    "state_table": more_oracle.state_table,
    "protobuf_wire_oracle": more_oracle.protobuf_wire_oracle,
    "schema_v2_oracle": more_oracle.schema_v2_oracle,
    "unknown_field_oracle": more_oracle.unknown_field_oracle,
    "cbor_vector_oracle": more_oracle.cbor_vector_oracle,
    "payload_hash": more_oracle.payload_hash,
    "damaged": more_oracle.damaged,
    "b64_table": more_oracle.b64_table,
    "bad_padding": more_oracle.bad_padding,
    "stable_digest": more_oracle.stable_digest,
    "signature": more_oracle.signature,
    "elf_header_oracle": more_oracle.elf_header_oracle,
    "total": more_oracle.total,
    "extremes": more_oracle.extremes,
    "token_vector": more_oracle.token_vector,
    "ip_module": more_oracle.ip_module,
    "decimal_gap": more_oracle.decimal_gap,
    "repeated": batch3_oracle.repeated,
    "bracket_pairs": batch3_oracle.bracket_pairs,
    "sorted_values": batch3_oracle.sorted_values,
    "stated_value": batch3_oracle.stated_value,
    "exit_seven": batch3_oracle.exit_seven,
    "two_compressions": batch3_oracle.two_compressions,
    "stated_prefix": batch3_oracle.stated_prefix,
    "fever_rule": batch3_oracle.fever_rule,
    "thirteen": batch3_oracle.thirteen,
    "stated_ratio": batch3_oracle.stated_ratio,
    "rates": batch3_oracle.rates,
    "harmonic": batch3_oracle.harmonic,
    "counted": batch4_oracle.counted,
    "correlation": batch4_oracle.correlation,
    "lag_identity": batch4_oracle.lag_identity,
    "half": batch4_oracle.half,
    "one_third": batch4_oracle.one_third,
    "axis_cosines": batch4_oracle.axis_cosines,
    "escapes": batch4_oracle.escapes,
    "request_counts": batch4_oracle.request_counts,
    "stable_age_records": batch6_oracle.stable_ages_oracle,
    "stack_state_machine": batch6_oracle.stack_sequence_oracle,
}

ORACLES["c05_preflight_blocked_oracle"] = c05_preflight_oracle.blocked_preflight_oracle
ORACLES.update({"archive_path": archive_oracle.path_oracle, "archive_zip_crc": archive_oracle.crc_oracle, "archive_zip_duplicates": archive_oracle.duplicate_oracle, "archive_tar_offsets": archive_oracle.tar_offsets_oracle, "archive_tar_truncated": archive_oracle.truncated_oracle, "archive_gzip_crc": archive_oracle.gzip_oracle})
ORACLES.update({"sqlite_header_independent": format_oracle.sqlite_header_oracle, "sqlite_integrity_independent": format_oracle.sqlite_integrity_oracle, "wasm_header_independent": format_oracle.wasm_header_oracle})
ORACLES["png_chunks_independent"] = format_oracle.png_chunks_oracle
ORACLES.update({"unknown_format_independent": format_oracle.unknown_format_oracle, "block_entropy_independent": format_oracle.block_entropy_oracle, "binary_diff_independent": format_oracle.binary_diff_oracle, "bounded_size_independent": format_oracle.bounded_size_oracle, "reproducible_structure_independent": format_oracle.reproducible_oracle})
ORACLES["jpeg_markers_independent"] = format_oracle.jpeg_markers_oracle
ORACLES.update({"partial_recovery_independent": format_oracle.partial_recovery_oracle, "timestamp_provenance_independent": format_oracle.timestamp_provenance_oracle, "dependency_graph_independent": format_oracle.dependency_graph_oracle})
ORACLES.update({"protocol_version_diff_independent": format_oracle.protocol_version_diff_oracle, "section_overlaps_independent": format_oracle.section_overlaps_oracle, "nested_zip_tar_independent": format_oracle.nested_zip_tar_oracle})
ORACLES["forensic_report_independent"] = format_oracle.forensic_report_oracle
ORACLES.update({"seven_zip_list_independent": archive_oracle.seven_zip_list_oracle, "seven_zip_missing_volume_independent": archive_oracle.seven_zip_missing_volume_oracle})
ORACLES.update({"wasm_sections_independent": format_oracle.wasm_sections_oracle, "wasm_type_indices_independent": format_oracle.wasm_type_indices_oracle})
ORACLES.update({"pdf_objects_independent": format_oracle.pdf_objects_oracle, "pdf_xref_independent": format_oracle.pdf_xref_oracle})
ORACLES["pdf_encryption_boundary_independent"] = format_oracle.pdf_encryption_boundary_oracle
ORACLES["elf_symbol_tables_independent"] = format_oracle.elf_symbol_tables_oracle
ORACLES["elf_host_compatibility_independent"] = format_oracle.elf_host_compatibility_oracle

EXECUTORS: dict[str, Callable[..., dict]] = {
    "cidr_bounds": cidr_bounds,
    "utf8_roundtrip": d01_exec.utf8_roundtrip,
    "utf8_reject_invalid": d01_exec.utf8_reject_invalid,
    "utf16_encode": d01_exec.utf16_encode,
    "u32_endian": d01_exec.u32_endian,
    "uint16_bounds": d01_exec.uint16_bounds,
    "int16_values": d01_exec.int16_values,
    "twos_complement_16": d01_exec.twos_complement_16,
    "float_bits": lambda value, kind, reference: d01_exec.float_bits(value, kind),
    "nan_policy": d01_exec.nan_policy,
    "inf_policy": d01_exec.inf_policy,
    "subnormal_f32": d01_exec.subnormal_f32,
    "nfc_compare": d01_exec.nfc_compare,
    "nfd_decompose": d01_exec.nfd_decompose,
    "nfkc_compat": d01_exec.nfkc_compat,
    "bom_policy": d01_exec.bom_policy,
    "json_roundtrip": d01_exec.json_roundtrip,
    "yaml_types": d01_exec.yaml_types,
    "yaml_ambiguous": d01_exec.yaml_ambiguous,
    "json_reject": d01_exec.json_reject,
    "sha256_text": d01_exec.sha256_text,
    "text_units": more_exec.text_units,
    "crlf_roundtrip": more_exec.crlf_roundtrip,
    "crlf_to_lf": more_exec.crlf_to_lf,
    "csv_roundtrip": more_exec.csv_roundtrip,
    "csv_newline": more_exec.csv_newline,
    "json_text": more_exec.json_text,
    "duplicate_keys": more_exec.duplicate_keys,
    "canonical_json": more_exec.canonical_json,
    "xml_expanded": more_exec.xml_expanded,
    "xml_entities": more_exec.xml_entities,
    "xml_unbalanced": more_exec.xml_unbalanced,
    "framed_record": more_exec.framed_record,
    "truncated_records": more_exec.truncated_records,
    "oversize_length": more_exec.oversize_length,
    "float32_exactness": more_exec.float32_exactness,
    "decimal_text": more_exec.decimal_text,
    "three_states": more_exec.three_states,
    "protobuf_old_reader": more_exec.protobuf_old_reader,
    "schema_migrate": more_exec.schema_migrate,
    "schema_unknown_field": more_exec.schema_unknown_field,
    "cbor_roundtrip": more_exec.cbor_roundtrip,
    "zlib_roundtrip": more_exec.zlib_roundtrip,
    "zlib_corrupt": more_exec.zlib_corrupt,
    "base64_bytes": more_exec.base64_bytes,
    "base64_reject": more_exec.base64_reject,
    "manifest_hash": more_exec.manifest_hash,
    "magic_bytes": more_exec.magic_bytes,
    "elf_header": more_exec.elf_header,
    "array_sum": more_exec.array_sum,
    "array_minmax": more_exec.array_minmax,
    "tokenize": more_exec.tokenize,
    "ipv4_check": more_exec.ipv4_check,
    "binary_float_gap": more_exec.binary_float_gap,
    "duplicates": batch3_exec.duplicates,
    "brackets": batch3_exec.brackets,
    "binary_insert": batch3_exec.binary_insert,
    "arithmetic": batch3_exec.arithmetic,
    "child_status": batch3_exec.child_status,
    "ipv6_reject": batch3_exec.ipv6_reject,
    "ipv6_prefix": batch3_exec.ipv6_prefix,
    "threshold": batch3_exec.threshold,
    "l2_norm": batch3_exec.l2_norm,
    "ratio": batch3_exec.ratio,
    "precision_recall": batch3_exec.precision_recall,
    "f1_score": batch3_exec.f1_score,
    "increment": batch4_exec.increment,
    "pearson": batch4_exec.pearson,
    "acf_lag0": batch4_exec.acf_series,
    "linear_integral": batch4_exec.linear_integral,
    "square_integral": batch4_exec.square_integral,
    "cosine_set": batch4_exec.cosine_set,
    "confined": batch4_exec.confined,
    "request_log": batch4_exec.request_log,
    "stable_ages": batch6_exec.stable_ages,
    "stack_sequence": batch6_exec.stack_sequence,
}

EXECUTORS.update({"zip_path_safety": archive_exec.zip_path_safety, "zip_crc": archive_exec.zip_crc, "zip_duplicates": archive_exec.zip_duplicates, "tar_offsets": archive_exec.tar_offsets, "tar_truncated": archive_exec.tar_truncated, "gzip_crc": archive_exec.gzip_crc})
EXECUTORS.update({"sqlite_header": format_exec.sqlite_header, "sqlite_integrity": format_exec.sqlite_integrity, "wasm_header": format_exec.wasm_header})
EXECUTORS["png_chunks"] = format_exec.png_chunks
EXECUTORS.update({"unknown_format": format_exec.unknown_format, "block_entropy": format_exec.block_entropy, "binary_diff": format_exec.binary_diff, "bounded_declared_size": format_exec.bounded_declared_size, "reproducible_structure": format_exec.reproducible_structure})
EXECUTORS["jpeg_markers"] = format_exec.jpeg_markers
EXECUTORS.update({"partial_recovery": format_exec.partial_recovery, "timestamp_provenance": format_exec.timestamp_provenance, "dependency_graph": format_exec.dependency_graph})
EXECUTORS.update({"protocol_version_diff": format_exec.protocol_version_diff, "section_overlaps": format_exec.section_overlaps, "nested_zip_tar": format_exec.nested_zip_tar})
EXECUTORS["forensic_report"] = format_exec.forensic_report
EXECUTORS.update({"seven_zip_list": archive_exec.seven_zip_list, "seven_zip_missing_volume": archive_exec.seven_zip_missing_volume})
EXECUTORS.update({"wasm_sections": format_exec.wasm_sections, "wasm_type_indices": format_exec.wasm_type_indices})
EXECUTORS.update({"pdf_objects": format_exec.pdf_objects, "pdf_xref": format_exec.pdf_xref})
EXECUTORS["pdf_encryption_boundary"] = format_exec.pdf_encryption_boundary
EXECUTORS["elf_symbol_tables"] = format_exec.elf_symbol_tables
EXECUTORS["elf_host_compatibility"] = format_exec.elf_host_compatibility

EXECUTORS["c05_preflight_blocked"] = c05_preflight.blocked_preflight_probe

for _name, _oracle_name, _schema in batch5_exec.SPECS:
    REGISTRY[_name] = _cap(_name, _oracle_name, _schema)
    EXECUTORS[_name] = getattr(batch5_exec, _name)
    ORACLES[_oracle_name] = getattr(batch5_oracle, _oracle_name)


def run(capability_id: str, arguments: dict) -> dict:
    if capability_id not in REGISTRY or capability_id not in EXECUTORS:
        raise KeyError(capability_id)
    return EXECUTORS[capability_id](**arguments)
