"""Interpret an instruction. Never dispatch on an MGL5 identifier."""
from __future__ import annotations

import re


class Unmatched(Exception):
    pass


def _ints(blob: str) -> list[int]:
    return [int(n) for n in re.findall(r"-?\d+", blob)]


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
    m = re.search(r"bytes ([0-9A-Fa-f]{2}(?: [0-9A-Fa-f]{2})+) como entero de (\d+) bits", text, re.I)
    if m:
        found.append({"tool": "uint_from_bytes", "raw_hex": m.group(1).replace(" ", ""), "width": int(m.group(2))})
    if re.search(r"UINT16 en los l[ií]mites 0 y 65535", text, re.I):
        found.append({"tool": "uint16_limits"})
    m = re.search(r"INT16 con (-?\d+),\s*(-?\d+),\s*(-?\d+) y (-?\d+)", text, re.I)
    if m:
        found.append({"tool": "int16_roundtrip", "values": [int(m.group(i)) for i in range(1, 5)]})
    m = re.search(r"Interpretar (0x[0-9A-Fa-f]+) como entero con signo de (\d+) bits", text, re.I)
    if m:
        found.append({"tool": "signed_from_hex", "raw_hex": m.group(1), "width": int(m.group(2))})
    m = re.search(r"Serializar (-?\d+(?:\.\d+)?) como (float32|double)", text, re.I)
    if m:
        kind = "float32" if m.group(2).lower() == "float32" else "float64"
        found.append({"tool": "float_bits", "value": float(m.group(1)), "kind": kind})
    if re.search(r"Procesar NaN\b", text):
        found.append({"tool": "non_finite", "kind": "nan"})
    if re.search(r"\+∞|\-∞|\+inf|\-inf", text, re.I):
        found.append({"tool": "non_finite", "kind": "inf"})
    if re.search(r"menor subnormal positivo de float32", text, re.I):
        found.append({"tool": "min_subnormal_f32"})
    m = re.search(r'Normalizar "([^"]+)" \+ U\+([0-9A-Fa-f]+) y comparar con U\+([0-9A-Fa-f]+)', text)
    if m:
        left = m.group(1) + chr(int(m.group(2), 16))
        right = chr(int(m.group(3), 16))
        found.append({"tool": "nfc_compare", "left": left, "right": right})
    m = re.search(r"Descomponer U\+([0-9A-Fa-f]+)", text)
    if m:
        found.append({"tool": "nfd_decompose", "text": chr(int(m.group(1), 16))})
    if re.search(r"ligadura ﬁ|ligadura fi", text, re.I):
        found.append({"tool": "nfkc_note", "text": "ﬁ"})
    m = re.search(r'SHA-256 del vector de prueba "([^"]+)"', text, re.I)
    if m:
        found.append({"tool": "sha256_text", "text": m.group(1)})
    m = re.search(r"suma sobre arreglo \[([^\]]+)\]", text, re.I)
    if m:
        found.append({"tool": "sum_ints", "values": _ints(m.group(1))})
    m = re.search(r"Procesar \[([^\]]+)\]", text)
    if m and not any(item["tool"] == "sum_ints" for item in found):
        found.append({"tool": "bounds", "values": _ints(m.group(1))})
    m = re.search(r"Insertar (\w+) (-?\d+) .*CHECK \1 >= (\d+)", text, re.I)
    if m:
        found.append({"tool": "sqlite_check_insert", "column": m.group(1), "value": int(m.group(2)), "predicate": f"{m.group(1)} >= {m.group(3)}"})
    if re.search(r"UTF-8 con BOM", text, re.I):
        found.append({"tool": "utf8_bom_policy", "text": "hola"})
    if re.search(r"l[ií]neas terminadas en CRLF", text, re.I):
        found.append({"tool": "crlf_roundtrip"})
    if re.search(r"Convertir CRLF a LF", text, re.I):
        found.append({"tool": "crlf_to_lf"})
    if re.search(r"comas y comillas escapadas", text, re.I):
        found.append({"tool": "csv_quoted_comma"})
    if re.search(r"entrecomillado que contiene un salto de l[ií]nea", text, re.I):
        found.append({"tool": "csv_quoted_newline"})
    if re.search(r"string, booleano, null, entero, lista y objeto anidado", text, re.I):
        found.append({"tool": "json_typed_object"})
    if re.search(r"Serializar y parsear caracteres no ASCII", text, re.I):
        found.append({"tool": "json_non_ascii"})
    if re.search(r"dos claves id[eé]nticas", text, re.I):
        found.append({"tool": "json_duplicate_keys"})
    if re.search(r"coma final y clave sin comillas", text, re.I):
        found.append({"tool": "json_reject_invalid"})
    if re.search(r"pol[ií]tica can[oó]nica", text, re.I):
        found.append({"tool": "json_canonical"})
    m = re.search(r"decimal (\d+\.\d+)", text, re.I)
    if m:
        found.append({"tool": "decimal_exact", "text": m.group(1)})
    if re.search(r"Comprimir y descomprimir", text, re.I):
        found.append({"tool": "zlib_roundtrip"})
    if re.search(r"Alterar un byte del flujo comprimido", text, re.I):
        found.append({"tool": "zlib_corrupt"})
    if re.search(r"ausente, null y cadena vac[ií]a", text, re.I):
        found.append({"tool": "absent_null_empty"})
    if re.search(r"entero de 64 bits a float32", text, re.I):
        found.append({"tool": "int64_to_float32_boundary"})
    if re.search(r"bytes que incluyen 0x00 y 0xFF", text, re.I):
        found.append({"tool": "hex_bytes_roundtrip"})
    if re.search(r"longitud y checksum", text, re.I):
        found.append({"tool": "length_checksum"})
    if re.search(r"Truncar un registro binario", text, re.I):
        found.append({"tool": "reject_truncated_record"})
    if re.search(r"longitud superior al tama[nñ]o", text, re.I):
        found.append({"tool": "reject_oversized_length"})
    if len(found) != 1:
        raise Unmatched(text if not found else "ambiguous instruction")
    return found[0]
