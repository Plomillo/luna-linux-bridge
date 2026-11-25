"""Checks that do not import the executors."""
from __future__ import annotations

import os
import sqlite3
import subprocess
from decimal import Decimal
from pathlib import Path


def _descent(text: str) -> int:
    def parse_sum(tokens, i):
        value, i = parse_product(tokens, i)
        while i < len(tokens) and tokens[i] == "+":
            right, i = parse_product(tokens, i + 1)
            value += right
        return value, i
    def parse_product(tokens, i):
        value, i = parse_atom(tokens, i)
        while i < len(tokens) and tokens[i] == "*":
            right, i = parse_atom(tokens, i + 1)
            value *= right
        return value, i
    def parse_atom(tokens, i):
        if tokens[i] == "(":
            value, i = parse_sum(tokens, i + 1)
            return value, i + 1
        return int(tokens[i]), i + 1
    tokens = []
    buf = ""
    for ch in text:
        if ch.isdigit():
            buf += ch
        else:
            if buf:
                tokens.append(buf)
                buf = ""
            if ch.strip():
                tokens.append(ch)
    if buf:
        tokens.append(buf)
    value, pos = parse_sum(tokens, 0)
    if pos != len(tokens):
        raise ValueError("unused")
    return value


def _ipv4(text: str) -> bool:
    parts = text.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part.isdigit() or (part.startswith("0") and part != "0"):
            return False
        if not 0 <= int(part) <= 255:
            return False
    return True


def check(plan: dict) -> dict:
    observed = plan.get("observed") or {}
    tool = observed.get("tool")
    if plan.get("capability") == "baseline_m0":
        return {"ok": None, "method": "delegated; the M0 oracle is a separate module"}
    if tool == "utf16_be":
        encoded = bytes.fromhex(observed["hex"])
        chars = "".join(chr(encoded[i] * 256 + encoded[i + 1]) for i in range(0, len(encoded), 2))
        return {"ok": chars == observed["text"] and observed["decoded"] == observed["text"], "method": "manual byte pairs, not codecs"}
    if tool == "binary_identity":
        expected = bytes(item["value"] for item in plan["arguments"] if item["type"] == "byte")
        return {"ok": bytes(observed["roundtrip"]) == expected == bytes.fromhex(observed["hex"]), "method": "expected bytes taken from the instruction literals"}
    if tool == "arithmetic":
        value = _descent(observed["text"])
        return {"ok": value == 9 and observed["value"] == 9 and observed["sum_inside_product"] is True, "method": "hand-written precedence parser, not ast"}
    if tool == "ipv4_pair":
        return {"ok": _ipv4(observed["first"]) and not _ipv4(observed["second"]), "method": "manual octet bounds, not ipaddress"}
    if tool == "float_gap":
        left = sum(Decimal(part) for part in observed["expr"].split("+"))
        right = Decimal(observed["right"])
        return {"ok": observed["equal"] is False and left == right and observed["claims_universal_equality"] is False, "method": "decimal equality against binary inequality"}
    if tool == "host_facts":
        kernel = Path("/proc/sys/kernel/osrelease").read_text().strip()
        distro = None
        for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                distro = line.split("=", 1)[1].strip().strip('"')
        arch = os.uname().machine
        return {"ok": observed["kernel"] == kernel and observed["distro"] == distro and observed["arch"] == arch, "method": "os.uname and os-release, not platform.release"}
    if tool == "git_readme":
        if not observed.get("available"):
            return {"ok": False, "method": "git missing"}
        kind = subprocess.run(["git", "cat-file", "-t", "HEAD"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout
        return {"ok": kind == "commit" and status == "" and observed["clean"] is True, "method": "git cat-file and status"}
    if tool in {"brackets", "tokenize", "cliente_pedido", "query_simulation", "path_simulation"}:
        return {"ok": None, "method": "not accredited", "reason": plan.get("primary_cause") or "SIMULATION"}
    return {"ok": False, "method": "no check"}
