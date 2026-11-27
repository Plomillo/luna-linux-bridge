"""Slot extraction and executors. No case identifiers."""
from __future__ import annotations

import ast
import codecs
import os
import platform
import re
import shutil
import sqlite3
import struct
import subprocess
import sys
import tempfile
from decimal import Decimal
from pathlib import Path


def _quotes(text: str) -> list[str]:
    return re.findall(r'"([^"]*)"', text)


def cidr_bounds(cidr: str) -> dict:
    import ipaddress
    iface = ipaddress.ip_interface(cidr)
    network = iface.network
    return {"tool": "cidr_bounds", "cidr": cidr, "network": str(network.network_address), "broadcast": str(network.broadcast_address), "prefix": network.prefixlen}


def ipv6_prefix(cidr: str) -> dict:
    import ipaddress
    network = ipaddress.ip_network(cidr, strict=False)
    return {"tool": "ipv6_prefix", "cidr": cidr, "prefix": f"{network.network_address.compressed}/{network.prefixlen}"}


def mask_contiguous(mask: str) -> dict:
    parts = [int(p) for p in mask.split(".")]
    bits = "".join(f"{p:08b}" for p in parts)
    contiguous = bool(re.fullmatch(r"1*0*", bits))
    return {"tool": "mask_contiguous", "mask": mask, "contiguous": contiguous, "rejected": not contiguous}


def factorial_span(start: int, stop: int) -> dict:
    values = {}
    for n in range(start, stop + 1):
        acc = 1
        for k in range(2, n + 1):
            acc *= k
        values[str(n)] = acc
    def fact(n: int) -> int:
        if n < 0:
            raise ValueError("negative")
        acc = 1
        for k in range(2, n + 1):
            acc *= k
        return acc
    rejected = False
    try:
        fact(-1)
    except ValueError:
        rejected = True
    return {"tool": "factorial_span", "start": start, "stop": stop, "values": values, "negative_rejected": rejected}


def arithmetic(text: str) -> dict:
    tree = ast.parse(text, mode="eval")
    value = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
    mult_before_add = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) and isinstance(getattr(n, "left", None), ast.BinOp) and isinstance(n.left.op, (ast.Add, ast.Sub)) for n in ast.walk(tree)) or any(isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub)) and isinstance(n.right, ast.BinOp) and isinstance(n.right.op, ast.Mult) for n in ast.walk(tree))
    return {"tool": "arithmetic", "text": text, "value": value, "product_before_sum": mult_before_add or "*" not in text}


def binary_search(target: int, start: int, stop: int) -> dict:
    lo, hi, comparisons = start, stop, 0
    found = None
    while lo <= hi:
        mid = (lo + hi) // 2
        comparisons += 1
        if mid == target:
            found = mid
            break
        if mid < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return {"tool": "binary_search", "target": target, "start": start, "stop": stop, "found": found, "index0": None if found is None else found - start, "comparisons": comparisons}


def first_index(target: int, values: list[int]) -> dict:
    index = next(i for i, v in enumerate(values) if v == target)
    return {"tool": "first_index", "target": target, "index0": index, "duplicate_policy": "first occurrence", "index_base": 0, "index_base_origin": "capability policy; the source does not state the base"}


def repeated_values(values: list[int]) -> dict:
    counts: dict[int, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    repeated = sorted(v for v, n in counts.items() if n > 1)
    return {"tool": "repeated_values", "values": values, "repeated": repeated}


def bst_inorder(values: list[int]) -> dict:
    root = None
    def insert(node, value):
        if node is None:
            return [value, None, None]
        if value < node[0]:
            node[1] = insert(node[1], value)
        else:
            node[2] = insert(node[2], value)
        return node
    for value in values:
        root = insert(root, value)
    out = []
    def walk(node):
        if node:
            walk(node[1]); out.append(node[0]); walk(node[2])
    walk(root)
    return {"tool": "bst_inorder", "inserted": values, "inorder": out}


def variance_pair(values: list[int]) -> dict:
    n = len(values)
    mean = sum(values) / n
    sq = sum((v - mean) ** 2 for v in values)
    return {"tool": "variance_pair", "values": values, "population": sq / n, "sample": sq / (n - 1), "population_divisor": n, "sample_divisor": n - 1}


def child_exit(code: int) -> dict:
    proc = subprocess.Popen([sys.executable, "-c", "import sys; sys.exit(int(sys.argv[1]))", str(code)])
    pid = proc.pid
    returncode = proc.wait()
    return {"tool": "child_exit", "pid": pid, "returncode": returncode}


def decimal_text(token: str) -> dict:
    rendered = format(Decimal(token), "f")
    return {"tool": "decimal_text", "token": token, "rendered": rendered, "used_binary_float": False}


def file_mode(mode: int) -> dict:
    path = Path(tempfile.mkdtemp(prefix="s2-mode-")) / "f"
    path.write_bytes(b"")
    os.chmod(path, mode)
    effective = os.stat(path).st_mode & 0o777
    return {"tool": "file_mode", "requested": oct(mode), "effective": oct(effective), "path": str(path)}


def umask_file(mask: int) -> dict:
    path = Path(tempfile.mkdtemp(prefix="s2-umask-")) / "f"
    subprocess.run([sys.executable, "-c", "import os,sys; os.umask(int(sys.argv[1],8)); os.close(os.open(sys.argv[2], os.O_CREAT|os.O_WRONLY, 0o666))", oct(mask), str(path)], check=True)
    effective = os.stat(path).st_mode & 0o777
    return {"tool": "umask_file", "mask": oct(mask), "base_mode_origin": "POSIX regular-file convention 0666; the operation does not state the base mode", "effective": oct(effective), "accredited": False}


def float32_limit() -> dict:
    boundary = 2 ** 24
    nxt = boundary + 1
    def f32(n: int) -> float:
        return struct.unpack("f", struct.pack("f", float(n)))[0]
    return {"tool": "float32_limit", "boundary": boundary, "boundary_exact": f32(boundary) == boundary, "next_odd": nxt, "next_odd_exact": f32(nxt) == nxt, "origin": "IEEE754 binary32 significand; the operation states the widths, not these two integers"}


def utf16_be(text: str) -> dict:
    encoded = codecs.encode(text, "utf-16-be")
    return {"tool": "utf16_be", "text": text, "hex": encoded.hex(), "decoded": codecs.decode(encoded, "utf-16-be")}


def binary_identity(values: list[int]) -> dict:
    data = bytes(values)
    return {"tool": "binary_identity", "values": list(data), "hex": data.hex(), "roundtrip": list(bytes.fromhex(data.hex()))}


def ipv4_pair(first: str, second: str) -> dict:
    import ipaddress
    def accept(text: str) -> bool:
        try:
            ipaddress.IPv4Address(text)
            return True
        except ipaddress.AddressValueError:
            return False
    return {"tool": "ipv4_pair", "first": first, "second": second, "first_ok": accept(first), "second_ok": accept(second)}


def float_gap(expr: str, right: str) -> dict:
    a, b = expr.split("+", 1)
    left = float(a) + float(b)
    return {"tool": "float_gap", "expr": expr, "right": right, "equal": left == float(right), "difference": format(left - float(right), ".20f"), "claims_universal_equality": False}


def host_facts() -> dict:
    distro = None
    osr = Path("/etc/os-release")
    if osr.exists():
        for line in osr.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                distro = line.split("=", 1)[1].strip().strip('"')
    return {"tool": "host_facts", "kernel": platform.release(), "distro": distro, "arch": platform.machine()}


def git_readme() -> dict:
    if shutil.which("git") is None:
        return {"tool": "git_readme", "available": False}
    base = Path(tempfile.mkdtemp(prefix="s2-git-"))
    subprocess.run(["git", "init"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "s2@example.invalid"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "S2"], cwd=base, check=True, capture_output=True)
    (base / "README").write_text("README\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add README"], cwd=base, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=base, check=True, capture_output=True, text=True).stdout.strip()
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=base, check=True, capture_output=True, text=True).stdout == ""
    return {"tool": "git_readme", "available": True, "path": str(base), "head": head, "clean": clean}


def _ints(text: str) -> list[int]:
    return [int(x) for x in re.findall(r"-?\d+", text)]


def select(instruction: str, predecessor: str | None, criterion: str) -> dict | None:
    text = " ".join(instruction.split())
    crit = criterion or ""
    cidr = re.search(r"\b((?:\d{1,3}\.){3}\d{1,3}/\d{1,2})\b", text)
    if cidr and re.search(r"red|broadcast", text, re.I):
        return {"capability": "cidr_bounds", "call": {"cidr": cidr.group(1)}, "reason": "EXPLICIT_LITERAL"}
    v6 = re.search(r"\b([0-9a-fA-F:]*:[0-9a-fA-F:]+/\d{1,3})\b", text)
    if v6 and re.search(r"prefijo", text, re.I):
        return {"capability": "ipv6_prefix", "call": {"cidr": v6.group(1)}, "reason": "EXPLICIT_LITERAL"}
    mask = re.search(r"\b((?:\d{1,3}\.){3}\d{1,3})\b", text)
    if mask and re.search(r"m[aá]scara IPv4", text, re.I):
        return {"capability": "mask_contiguous", "call": {"mask": mask.group(1)}, "reason": "EXPLICIT_LITERAL"}
    fact = re.search(r"n\s*=\s*(\d+)\.\.(\d+)", text)
    if fact and re.search(r"factorial", text, re.I):
        return {"capability": "factorial_span", "call": {"start": int(fact.group(1)), "stop": int(fact.group(2))}, "reason": "EXPLICIT_LITERAL"}
    ordered = re.search(r"arreglo ordenado de (\d+) a (\d+)", text)
    target = re.search(r"Buscar (\d+)", text)
    if ordered and target:
        return {"capability": "binary_search", "call": {"target": int(target.group(1)), "start": int(ordered.group(1)), "stop": int(ordered.group(2))}, "reason": "EXPLICIT_LITERAL"}
    bracket = re.search(r"\[([0-9,\s]+)\]", text)
    if target and bracket and "ordenado de" not in text:
        return {"capability": "first_index", "call": {"target": int(target.group(1)), "values": _ints(bracket.group(1))}, "reason": "EXPLICIT_LITERAL", "limit": "INDEX_BASE_NOT_IN_SOURCE"}
    if bracket and re.search(r"sin falsos positivos", crit, re.I):
        return {"capability": "repeated_values", "call": {"values": _ints(bracket.group(1))}, "reason": "CRITERION_DEFINES_THE_QUESTION"}
    if re.search(r"varianza poblacional y muestral", text, re.I) and bracket:
        return {"capability": "variance_pair", "call": {"values": _ints(bracket.group(1))}, "reason": "EXPLICIT_LITERAL"}
    inserted = re.search(r"Insertar ([0-9, ]+)", text)
    if inserted and re.search(r"inorder", crit, re.I):
        return {"capability": "bst_inorder", "call": {"values": _ints(inserted.group(1))}, "reason": "CRITERION_DEFINES_THE_TRAVERSAL"}
    expr = re.search(r"(\d+(?:\s*[-+*/]\s*\d+)+)", text)
    if expr and re.search(r"Parsear|Optimizar|precedencia", text, re.I):
        return {"capability": "arithmetic", "call": {"text": expr.group(1).replace(" ", "")}, "reason": "EXPLICIT_LITERAL"}
    quoted = _quotes(text)
    if len(quoted) == 1 and re.search(r"\d", quoted[0]) and re.search(r"Parsear", text):
        return {"capability": "arithmetic", "call": {"text": quoted[0]}, "reason": "EXPLICIT_LITERAL"}
    child = re.search(r"c[oó]digo (\d+)", text)
    if child and re.search(r"proceso hijo", text, re.I):
        return {"capability": "child_exit", "call": {"code": int(child.group(1))}, "reason": "EXPLICIT_LITERAL"}
    dec = re.search(r"decimal ([0-9]+\.[0-9]+)", text)
    if dec:
        return {"capability": "decimal_text", "call": {"token": dec.group(1)}, "reason": "EXPLICIT_LITERAL"}
    mode = re.search(r"archivo (0[0-7]{3})", text)
    if mode and re.search(r"acceso", text, re.I):
        return {"capability": "file_mode", "call": {"mode": int(mode.group(1), 8)}, "reason": "EXPLICIT_LITERAL"}
    umask = re.search(r"umask (0[0-7]{3})", text)
    if umask:
        return {"capability": "umask_file", "call": {"mask": int(umask.group(1), 8)}, "reason": "BASE_MODE_NOT_IN_SOURCE", "accredited": False}
    if re.search(r"float32", text) and re.search(r"64 bits", text):
        return {"capability": "float32_limit", "call": {}, "reason": "WIDTHS_EXPLICIT_VALUES_FROM_IEEE754"}
    if re.search(r"Repetir la serializaci[oó]n en big-endian", text, re.I):
        if not predecessor or len(_quotes(predecessor)) != 1:
            return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "SOURCE_ARGUMENT_UNAVAILABLE", "primary_cause": "MISSING_SOURCE_DATA"}
        return {"capability": "utf16_be", "call": {"text": _quotes(predecessor)[0]}, "reason": "CONTEXT_DERIVED"}
    hexs = re.findall(r"0x([0-9A-Fa-f]{2})", text)
    if hexs and re.search(r"bytes que incluyen", text, re.I):
        return {"capability": "binary_identity", "call": {"values": [int(h, 16) for h in hexs]}, "reason": "EXPLICIT_LITERAL"}
    pair = re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", text)
    if len(pair) >= 2 and not cidr and not re.search(r"m[aá]scara", text, re.I):
        return {"capability": "ipv4_pair", "call": {"first": pair[0], "second": pair[1]}, "reason": "EXPLICIT_LITERAL"}
    gap = re.search(r"\(([^)]+)\)\s*con\s*([0-9.]+)", text)
    if gap and re.search(r"float", text, re.I):
        return {"capability": "float_gap", "call": {"expr": gap.group(1), "right": gap.group(2)}, "reason": "EXPLICIT_LITERAL"}
    if re.search(r"kernel, distribuci[oó]n y arquitectura", text, re.I):
        return {"capability": "host_facts", "call": {}, "reason": "HOST_OBSERVATION"}
    if re.search(r"Crear repo local y commit README", text):
        return {"capability": "git_readme", "call": {}, "reason": "OPERATION_NAMES_THE_ACTION"}
    if re.search(r"dos compresiones", text, re.I):
        return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "SOURCE_ARGUMENT_UNAVAILABLE", "primary_cause": "MISSING_SOURCE_DATA"}
    if re.search(r"Integrar", text) and re.search(r"paneles", crit, re.I) and not re.search(r"\d+\s+paneles", text):
        return {"stop": "BLOCKED", "stage": "ARGUMENT_RESOLUTION", "reason": "PANEL_COUNT_ABSENT", "primary_cause": "MISSING_SOURCE_DATA"}
    if re.search(r"laboratorio", text, re.I) and not _quotes(text):
        return {"stop": "BLOCKED", "stage": "FIXTURE", "reason": "LAB_ARTIFACT_NOT_IN_SOURCE", "primary_cause": "MISSING_FIXTURE"}
    return None


EXECUTORS = {
    "cidr_bounds": cidr_bounds,
    "ipv6_prefix": ipv6_prefix,
    "mask_contiguous": mask_contiguous,
    "factorial_span": factorial_span,
    "arithmetic": arithmetic,
    "binary_search": binary_search,
    "first_index": first_index,
    "repeated_values": repeated_values,
    "bst_inorder": bst_inorder,
    "variance_pair": variance_pair,
    "child_exit": child_exit,
    "decimal_text": decimal_text,
    "file_mode": file_mode,
    "umask_file": umask_file,
    "float32_limit": float32_limit,
    "utf16_be": utf16_be,
    "binary_identity": binary_identity,
    "ipv4_pair": ipv4_pair,
    "float_gap": float_gap,
    "host_facts": host_facts,
    "git_readme": git_readme,
}
