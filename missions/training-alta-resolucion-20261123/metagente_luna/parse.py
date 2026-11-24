"""Interpret an instruction. Never dispatch on an MGL5 identifier."""
from __future__ import annotations

import re


class Unmatched(Exception):
    pass


def parse(instruction: str) -> dict:
    text = " ".join(instruction.strip().split())
    if re.fullmatch(r"MGL5-(INF|TEO)-\d{4}", text):
        raise Unmatched("an identifier is not an instruction")
    found = []
    m = re.search(r'Serializar "([^"]+)" en UTF-16 (little-endian|big-endian)', text, re.I)
    if m:
        found.append({"tool": "utf16_roundtrip", "text": m.group(1), "endian": "little" if m.group(2).lower().startswith("little") else "big"})
    m = re.search(r'Codificar "([^"]+)"(?: en UTF-8)?', text, re.I)
    if m and "UTF-16" not in text.upper():
        found.append({"tool": "utf8_roundtrip", "text": m.group(1)})
    m = re.search(r"continuaci[oó]n aislada (0x[0-9A-Fa-f]+)", text, re.I)
    if m:
        found.append({"tool": "reject_isolated_continuation", "byte_hex": m.group(1)})
    m = re.search(r"suma sobre arreglo \[([^\]]+)\]", text, re.I)
    if m:
        found.append({"tool": "sum_ints", "values": [int(n) for n in re.findall(r"-?\d+", m.group(1))]})
    m = re.search(r"(?:Procesar|arreglo) \[([^\]]+)\]", text)
    if m and not any(item["tool"] == "sum_ints" for item in found):
        found.append({"tool": "bounds", "values": [int(n) for n in re.findall(r"-?\d+", m.group(1))]})
    m = re.search(r'SHA-256 del vector de prueba "([^"]+)"', text, re.I)
    if m:
        found.append({"tool": "sha256_text", "text": m.group(1)})
    m = re.search(r"INT16 con (-?\d+),\s*(-?\d+),\s*(-?\d+) y (-?\d+)", text, re.I)
    if m:
        found.append({"tool": "int16_roundtrip", "values": [int(m.group(i)) for i in range(1, 5)]})
    if len(found) != 1:
        raise Unmatched(text if not found else "ambiguous instruction")
    return found[0]
