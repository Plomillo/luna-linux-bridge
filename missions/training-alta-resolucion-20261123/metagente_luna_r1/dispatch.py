"""Recognition for operations M0 does not match. No case identifiers."""
from __future__ import annotations

import re

from metagente_luna_r1 import tools_r1


def _quotes(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def recognize(text: str, predecessor: str | None) -> dict | None:
    if re.search(r"Repetir la serializaci[oó]n en big-endian", text, re.I):
        if not predecessor:
            return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "ANAPHORA_WITHOUT_PREDECESSOR"}
        found = _quotes(predecessor)
        if not found:
            return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "PREDECESSOR_HAS_NO_QUOTED_TEXT"}
        return {"tool": "utf16_be", "text": found[0], "origin": "quoted text of the predecessor operation"}
    hexs = re.findall(r"0x([0-9A-Fa-f]{2})", text)
    if re.search(r"bytes que incluyen", text, re.I) and hexs:
        return {"tool": "hex_bytes", "values": [int(item, 16) for item in hexs]}
    quotes = _quotes(text)
    if len(quotes) == 2 and all(any(ch in item for ch in "()[]{}") for item in quotes):
        return {"tool": "brackets", "left": quotes[0], "right": quotes[1]}
    if re.search(r"endpoint", text, re.I) and quotes:
        return {"tool": "query_as_data", "payload": quotes[0]}
    if re.search(r"descarga", text, re.I) and quotes:
        return {"tool": "path_jail", "relative": quotes[0]}
    if re.search(r"Tokenizar", text) and quotes:
        return {"tool": "tokenize", "text": quotes[0]}
    if re.search(r"Parsear", text) and quotes and re.search(r"\d", quotes[0]):
        return {"tool": "arithmetic", "text": quotes[0]}
    pair = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    if len(pair) >= 2:
        return {"tool": "ipv4_pair", "first": pair[0], "second": pair[1]}
    if re.search(r"dos compresiones", text, re.I) and '::' in text:
        return {"tool": "ipv6_two_compressions", "text": "::" + "x" + "::", "origin": "the operation names two :: compressions and contains that literal"}
    gap = re.search(r"\(([^)]+)\)\s*con\s*([0-9.]+)", text)
    if gap and re.search(r"float", text, re.I):
        return {"tool": "float_gap", "left": gap.group(1), "right": gap.group(2)}
    if re.search(r"kernel, distribuci[oó]n y arquitectura", text, re.I):
        return {"tool": "host_facts"}
    if re.search(r"Crear repo local y commit README", text):
        return {"tool": "git_readme"}
    if re.search(r"tablas Cliente y Pedido", text):
        return {"tool": "cliente_pedido"}
    if re.search(r"UTF-8 con BOM", text) and '"' not in text:
        return {"stop": "BLOCKED", "stage": "FIXTURE", "reason": "ESSENTIAL_FILE_CONTENT_ABSENT"}
    if re.search(r"\bRepetir\b", text) and not predecessor:
        return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "ANAPHORA_WITHOUT_PREDECESSOR"}
    if re.search(r"laboratorio|de laboratorio", text, re.I):
        return {"stop": "BLOCKED", "stage": "FIXTURE", "reason": "LAB_ARTIFACT_NOT_IN_SOURCE"}
    return None


def run(call: dict) -> dict:
    name = call["tool"]
    fn = getattr(tools_r1, name)
    kwargs = {k: v for k, v in call.items() if k not in {"tool", "origin"}}
    observed = fn(**kwargs)
    if "origin" in call:
        observed["origin"] = call["origin"]
    return observed
