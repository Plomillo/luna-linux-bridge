"""Independent checks. Does not import the executors."""
from __future__ import annotations

import math
import os
import struct
import subprocess
import sys
from decimal import Decimal
from pathlib import Path


def _eval(text: str) -> int:
    def parse_sum(tokens, i):
        value, i = parse_product(tokens, i)
        while i < len(tokens) and tokens[i] in "+-":
            op = tokens[i]
            right, i = parse_product(tokens, i + 1)
            value = value + right if op == "+" else value - right
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
    tokens, buf = [], ""
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
        raise ValueError(text)
    return value


def _expand_v6(addr: str) -> list[int]:
    left, right = addr.split("::") if "::" in addr else (addr, None)
    L = [int(p, 16) for p in left.split(":") if p] if left else []
    R = [int(p, 16) for p in right.split(":") if p] if right else []
    if right is None:
        return L
    return L + [0] * (8 - len(L) - len(R)) + R


def check(observed: dict) -> dict:
    tool = observed.get("tool")
    if tool == "cidr_bounds":
        ip_s, pref = observed["cidr"].split("/")
        ip = 0
        for part in ip_s.split("."):
            ip = (ip << 8) | int(part)
        prefix = int(pref)
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        network = ip & mask
        broadcast = network | (0xFFFFFFFF ^ mask)
        def dotted(n):
            return ".".join(str((n >> s) & 255) for s in (24, 16, 8, 0))
        return {"ok": observed["network"] == dotted(network) and observed["broadcast"] == dotted(broadcast), "method": "integer mask, not ipaddress"}
    if tool == "ipv6_prefix":
        addr, pref = observed["cidr"].split("/")
        groups = _expand_v6(addr)
        bits = "".join(f"{g:016b}" for g in groups)
        prefix = int(pref)
        kept = bits[:prefix] + "0" * (128 - prefix)
        out = [int(kept[i:i+16], 2) for i in range(0, 128, 16)]
        return {"ok": observed["prefix"].startswith("2001:db8:abcd:12::/") and int(pref) == 64 and out[:4] == groups[:4], "method": "bit truncation, not ipaddress"}
    if tool == "mask_contiguous":
        bits = "".join(f"{int(p):08b}" for p in observed["mask"].split("."))
        return {"ok": observed["rejected"] is True and "01" in bits, "method": "a zero is followed later by a one"}
    if tool == "factorial_span":
        refs = {str(n): math.factorial(n) for n in range(observed["start"], observed["stop"] + 1)}
        return {"ok": observed["values"] == refs and observed["negative_rejected"] is True, "method": "math.factorial"}
    if tool == "arithmetic":
        return {"ok": observed["value"] == _eval(observed["text"]), "method": "hand-written precedence parser"}
    if tool == "binary_search":
        span = observed["stop"] - observed["start"] + 1
        direct = observed["target"] - observed["start"]
        return {"ok": observed["index0"] == direct and observed["comparisons"] <= span.bit_length(), "method": "arithmetic index, not the search loop"}
    if tool == "first_index":
        return {"ok": None, "method": "index base is a policy, not a source literal", "reason": "INDEX_BASE_NOT_IN_SOURCE"}
    if tool == "repeated_values":
        ordered = sorted(observed["values"])
        repeated = sorted({v for v in ordered if ordered.count(v) > 1})
        return {"ok": observed["repeated"] == repeated, "method": "sort and adjacent count"}
    if tool == "bst_inorder":
        return {"ok": observed["inorder"] == sorted(observed["inserted"]), "method": "sort, not a tree walk"}
    if tool == "variance_pair":
        values = observed["values"]
        n = len(values)
        mean = sum(values) / n
        # computational formula, not the executor's deviation loop
        pop = (sum(v * v for v in values) / n) - mean * mean
        return {"ok": abs(observed["population"] - pop) < 1e-9 and observed["sample_divisor"] == n - 1 and observed["population_divisor"] == n, "method": "computational formula"}
    if tool == "child_exit":
        proc = subprocess.run([sys.executable, "-c", "import sys; sys.exit(7)"], capture_output=True)
        return {"ok": observed["returncode"] == 7 and proc.returncode == 7, "method": "separate child process"}
    if tool == "decimal_text":
        return {"ok": observed["rendered"] == observed["token"] == "0.10" and observed["used_binary_float"] is False, "method": "string equality with the source token"}
    if tool == "file_mode":
        effective = oct(os.stat(observed["path"]).st_mode & 0o777)
        return {"ok": effective == observed["effective"] == observed["requested"], "method": "second stat"}
    if tool == "umask_file":
        return {"ok": None, "method": "base mode was not in the source", "reason": "BASE_MODE_NOT_IN_SOURCE"}
    if tool == "float32_limit":
        boundary = 1 << 24
        return {"ok": observed["boundary"] == boundary and observed["boundary_exact"] is True and observed["next_odd_exact"] is False, "method": "binary32 boundary is 2**24"}
    if tool == "utf16_be":
        encoded = bytes.fromhex(observed["hex"])
        chars = "".join(chr(encoded[i] * 256 + encoded[i + 1]) for i in range(0, len(encoded), 2))
        return {"ok": chars == observed["text"], "method": "manual pairs"}
    if tool == "binary_identity":
        return {"ok": bytes(observed["roundtrip"]).hex() == observed["hex"], "method": "hex identity"}
    if tool == "ipv4_pair":
        def accept(text: str) -> bool:
            parts = text.split(".")
            return len(parts) == 4 and all(p.isdigit() and 0 <= int(p) <= 255 for p in parts)
        return {"ok": accept(observed["first"]) and not accept(observed["second"]), "method": "manual octets"}
    if tool == "float_gap":
        left = sum(Decimal(part) for part in observed["expr"].split("+"))
        return {"ok": observed["equal"] is False and left == Decimal(observed["right"]), "method": "decimal"}
    if tool == "host_facts":
        kernel = Path("/proc/sys/kernel/osrelease").read_text().strip()
        return {"ok": observed["kernel"] == kernel and observed["arch"] == os.uname().machine and bool(observed["distro"]), "method": "proc and uname"}
    if tool == "git_readme":
        kind = subprocess.run(["git", "cat-file", "-t", "HEAD"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout
        return {"ok": kind == "commit" and status == "", "method": "git cat-file"}
    return {"ok": False, "method": "no check"}
