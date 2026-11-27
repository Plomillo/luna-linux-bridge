"""Capabilities that have a schema and an oracle id. Unknown ids cannot run."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable

from pydantic import BaseModel

from metagente_luna_s3 import (
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
    "zlib_roundtrip": _cap("zlib_roundtrip", "payload_hash", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "zlib_corrupt": _cap("zlib_corrupt", "damaged", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "base64_bytes": _cap("base64_bytes", "b64_table", {"type": "object", "required": ["payload_hex"], "properties": {"payload_hex": {"type": "string"}}, "additionalProperties": False}),
    "base64_reject": _cap("base64_reject", "bad_padding", _TEXT),
    "manifest_hash": _cap("manifest_hash", "stable_digest", {"type": "object", "required": ["document", "altered"], "properties": {"document": {"type": "object"}, "altered": {"type": "object"}}, "additionalProperties": False}),
    "magic_bytes": _cap("magic_bytes", "signature", {"type": "object", "required": ["name", "payload_hex"], "properties": {"name": {"type": "string"}, "payload_hex": {"type": "string"}}, "additionalProperties": False}),
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
    "payload_hash": more_oracle.payload_hash,
    "damaged": more_oracle.damaged,
    "b64_table": more_oracle.b64_table,
    "bad_padding": more_oracle.bad_padding,
    "stable_digest": more_oracle.stable_digest,
    "signature": more_oracle.signature,
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
    "zlib_roundtrip": more_exec.zlib_roundtrip,
    "zlib_corrupt": more_exec.zlib_corrupt,
    "base64_bytes": more_exec.base64_bytes,
    "base64_reject": more_exec.base64_reject,
    "manifest_hash": more_exec.manifest_hash,
    "magic_bytes": more_exec.magic_bytes,
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

EXECUTORS["c05_preflight_blocked"] = c05_preflight.blocked_preflight_probe

for _name, _oracle_name, _schema in batch5_exec.SPECS:
    REGISTRY[_name] = _cap(_name, _oracle_name, _schema)
    EXECUTORS[_name] = getattr(batch5_exec, _name)
    ORACLES[_oracle_name] = getattr(batch5_oracle, _oracle_name)


def run(capability_id: str, arguments: dict) -> dict:
    if capability_id not in REGISTRY or capability_id not in EXECUTORS:
        raise KeyError(capability_id)
    return EXECUTORS[capability_id](**arguments)
