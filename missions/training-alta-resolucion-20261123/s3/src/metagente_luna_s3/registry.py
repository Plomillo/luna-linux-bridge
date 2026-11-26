"""Capabilities that have a schema and an oracle id. Unknown ids cannot run."""
from __future__ import annotations

import ipaddress
from collections.abc import Callable

from pydantic import BaseModel

from metagente_luna_s3 import d01_exec, d01_oracle


class Capability(BaseModel):
    capability_id: str
    version: str
    input_schema: dict
    output_schema: dict
    oracle_id: str
    status: str


def cidr_bounds(cidr: str) -> dict:
    address, prefix_s = cidr.split("/")
    ip = 0
    for part in address.split("."):
        ip = (ip << 8) | int(part)
    prefix = int(prefix_s)
    mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
    network = ip & mask
    broadcast = network | (0xFFFFFFFF ^ mask)

    def dotted(value: int) -> str:
        return ".".join(str((value >> shift) & 255) for shift in (24, 16, 8, 0))

    return {"network": dotted(network), "broadcast": dotted(broadcast)}


def cidr_oracle(cidr: str, observed: dict) -> dict:
    network = ipaddress.ip_interface(cidr).network
    ok = observed["network"] == str(network.network_address) and observed["broadcast"] == str(network.broadcast_address)
    return {"ok": ok, "method": "ipaddress, not the integer mask"}


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
    "nan_policy": _cap("nan_policy", "nan_bits", {"type": "object", "additionalProperties": False}),
    "inf_policy": _cap("inf_policy", "inf_signs", {"type": "object", "additionalProperties": False}),
    "subnormal_f32": _cap("subnormal_f32", "subnormal_bits", {"type": "object", "additionalProperties": False}),
    "nfc_compare": _cap("nfc_compare", "nfc_table", {"type": "object", "required": ["decomposed", "composed"], "properties": {"decomposed": {"type": "string"}, "composed": {"type": "string"}}, "additionalProperties": False}),
    "nfd_decompose": _cap("nfd_decompose", "nfd_table", {"type": "object", "required": ["composed"], "properties": {"composed": {"type": "string"}}, "additionalProperties": False}),
    "nfkc_compat": _cap("nfkc_compat", "nfkc_table", {"type": "object", "required": ["text"], "properties": {"text": {"type": "string"}}, "additionalProperties": False}),
    "bom_policy": _cap("bom_policy", "bom_visible", {"type": "object", "required": ["without_bom", "with_bom_visible"], "properties": {"without_bom": {"type": "string"}, "with_bom_visible": {"type": "string"}}, "additionalProperties": False}),
    "json_roundtrip": _cap("json_roundtrip", "json_types", {"type": "object", "required": ["document"], "properties": {"document": {"type": "object"}}, "additionalProperties": False}),
    "json_reject": _cap("json_reject", "json_scan", {"type": "object", "required": ["texts"], "properties": {"texts": {"type": "array"}}, "additionalProperties": False}),
    "sha256_text": _cap("sha256_text", "nist_abc", _TEXT),
}

ORACLES: dict[str, Callable[..., dict]] = {
    "ipaddress": lambda arguments, observed: cidr_oracle(arguments["cidr"], observed),
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
    "json_scan": d01_oracle.json_scan,
    "nist_abc": d01_oracle.nist_abc,
}

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
    "nan_policy": lambda: d01_exec.nan_policy(),
    "inf_policy": lambda: d01_exec.inf_policy(),
    "subnormal_f32": lambda: d01_exec.subnormal_f32(),
    "nfc_compare": d01_exec.nfc_compare,
    "nfd_decompose": d01_exec.nfd_decompose,
    "nfkc_compat": d01_exec.nfkc_compat,
    "bom_policy": d01_exec.bom_policy,
    "json_roundtrip": d01_exec.json_roundtrip,
    "json_reject": d01_exec.json_reject,
    "sha256_text": d01_exec.sha256_text,
}


def run(capability_id: str, arguments: dict) -> dict:
    if capability_id not in REGISTRY or capability_id not in EXECUTORS:
        raise KeyError(capability_id)
    return EXECUTORS[capability_id](**arguments)
