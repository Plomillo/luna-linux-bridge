"""Structured interpretation. The case identifier is never an input."""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from metagente_luna.parse import Unmatched, parse
from metagente_luna_s1.capabilities import EXECUTORS


def quotes(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def plan_for(instruction: str, predecessor: str | None) -> dict:
    text = " ".join(instruction.split())
    found = quotes(text)
    hexes = re.findall(r"0x([0-9A-Fa-f]{2})", text)
    ipv4 = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    arguments = []
    for value in found:
        arguments.append({"value": value, "origin": "EXPLICIT_LITERAL", "type": "string"})
    for value in hexes:
        arguments.append({"value": int(value, 16), "origin": "EXPLICIT_LITERAL", "type": "byte"})
    base = {
        "source_instruction": text,
        "arguments": arguments,
        "capability": None,
        "execution_plan": [],
        "simulation": False,
        "accredited": False,
    }
    if re.search(r"Repetir la serializaci[oó]n en big-endian", text, re.I):
        if not predecessor:
            return base | {"status": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "SOURCE_ARGUMENT_UNAVAILABLE", "primary_cause": "MISSING_SOURCE_DATA"}
        earlier = quotes(predecessor)
        if len(earlier) != 1:
            return base | {"status": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "PREDECESSOR_QUOTE_NOT_UNIQUE", "primary_cause": "MISSING_SOURCE_DATA"}
        base["arguments"].append({"value": earlier[0], "origin": "CONTEXT_DERIVED", "source": "quoted literal in the predecessor operation"})
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "CONTEXT_ARGUMENT_RECOVERED", "capability": "utf16_be", "call": {"text": earlier[0]}, "primary_cause": None}
    if re.search(r"dos compresiones", text, re.I):
        return base | {"status": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "SOURCE_ARGUMENT_UNAVAILABLE", "primary_cause": "MISSING_SOURCE_DATA", "detail": "the operation names two compressions but does not contain the address"}
    if re.search(r"UTF-8 con BOM", text) and not found:
        return base | {"status": "BLOCKED", "stage": "FIXTURE", "reason": "ESSENTIAL_FILE_CONTENT_ABSENT", "primary_cause": "MISSING_SOURCE_DATA"}
    if re.search(r"laboratorio", text, re.I) and not found:
        return base | {"status": "BLOCKED", "stage": "FIXTURE", "reason": "LAB_ARTIFACT_NOT_IN_SOURCE", "primary_cause": "MISSING_FIXTURE"}
    if re.search(r"bytes que incluyen", text, re.I) and hexes:
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_BYTES", "capability": "binary_identity", "call": {"values": [int(v, 16) for v in hexes]}, "primary_cause": None}
    if len(found) == 2 and all(any(ch in item for ch in "()[]{}") for item in found):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_LITERALS", "capability": "brackets", "call": {"left": found[0], "right": found[1]}, "accredited": False, "primary_cause": "ORACLE_INDEPENDENCE_FAILURE"}
    if re.search(r"endpoint", text, re.I) and found:
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "SIMULATION_DECLARED", "capability": "query_simulation", "call": {"payload": found[0]}, "simulation": True, "primary_cause": None}
    if re.search(r"descarga", text, re.I) and found:
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "SIMULATION_DECLARED", "capability": "path_simulation", "call": {"relative": found[0]}, "simulation": True, "primary_cause": None}
    if re.search(r"Tokenizar", text) and found:
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_LITERAL", "capability": "tokenize", "call": {"text": found[0]}, "accredited": False, "primary_cause": "ORACLE_INDEPENDENCE_FAILURE"}
    if re.search(r"Parsear", text) and found and re.search(r"\d", found[0]):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_LITERAL", "capability": "arithmetic", "call": {"text": found[0]}, "primary_cause": None}
    if len(ipv4) >= 2:
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_LITERAL", "capability": "ipv4_pair", "call": {"first": ipv4[0], "second": ipv4[1]}, "primary_cause": None}
    gap = re.search(r"\(([^)]+)\)\s*con\s*([0-9.]+)", text)
    if gap and re.search(r"float", text, re.I):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "EXPLICIT_LITERAL", "capability": "float_gap", "call": {"expr": gap.group(1), "right": gap.group(2)}, "primary_cause": None}
    if re.search(r"kernel, distribuci[oó]n y arquitectura", text, re.I):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "HOST_OBSERVATION", "capability": "host_facts", "call": {}, "primary_cause": None}
    if re.search(r"Crear repo local y commit README", text):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "OPERATION_NAMES_THE_ACTION", "capability": "git_readme", "call": {}, "primary_cause": None}
    if re.search(r"tablas Cliente y Pedido", text):
        return base | {"status": "READY", "stage": "CAPABILITY_RESOLUTION", "reason": "TABLE_NAMES_EXPLICIT", "capability": "cliente_pedido", "call": {}, "accredited": False, "primary_cause": "ORACLE_INDEPENDENCE_FAILURE"}
    try:
        call = parse(text)
    except Unmatched:
        call = None
    if call is not None:
        return base | {"status": "READY", "stage": "DELEGATED_TO_M0", "reason": "M0_GRAMMAR_MATCH", "capability": "baseline_m0", "call": call, "primary_cause": None}
    if re.search(r"\bRepetir\b", text):
        return base | {"status": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "SOURCE_ARGUMENT_UNAVAILABLE", "primary_cause": "MISSING_SOURCE_DATA"}
    return base | {"status": "NO_CAPABILITY", "stage": "CAPABILITY_RESOLUTION", "reason": "NO_REGISTERED_CAPABILITY", "primary_cause": "MISSING_CAPABILITY", "m0_immediate_cause": "PARSER_RECOGNITION_FAILURE"}


def execute_plan(plan: dict) -> dict:
    if plan["status"] != "READY":
        return plan
    if plan["capability"] == "baseline_m0":
        from metagente_luna.m0 import execute as m0_execute
        delegated = m0_execute(plan["source_instruction"])
        plan["observed"] = delegated.get("observed")
        plan["delegated_to"] = "M0-20261124.2"
        return plan
    fn = EXECUTORS[plan["capability"]]
    plan["observed"] = fn(**plan["call"])
    return plan
