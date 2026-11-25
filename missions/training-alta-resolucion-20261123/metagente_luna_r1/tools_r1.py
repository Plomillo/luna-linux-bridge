"""Tools that M0 does not dispatch. They do not import M0."""
from __future__ import annotations

import ast
import ipaddress
import os
import platform
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path


def utf16_be(text: str) -> dict:
    encoded = b"".join(ord(ch).to_bytes(2, "big") for ch in text)
    decoded = "".join(chr(int.from_bytes(encoded[i:i + 2], "big")) for i in range(0, len(encoded), 2))
    return {"tool": "utf16_be", "text": text, "hex": encoded.hex(), "decoded": decoded, "byte_order": "big"}


def hex_bytes(values: list[int]) -> dict:
    data = bytes(values)
    encoded = data.hex()
    return {"tool": "hex_bytes", "input": list(data), "encoded": encoded, "decoded": list(bytes.fromhex(encoded))}


def brackets(left: str, right: str) -> dict:
    def ok(text: str) -> bool:
        pairs = {")": "(", "]": "[", "}": "{"}
        stack: list[str] = []
        for ch in text:
            if ch in "([{":
                stack.append(ch)
            elif ch in pairs:
                if not stack or stack.pop() != pairs[ch]:
                    return False
        return not stack
    return {"tool": "brackets", "left": left, "right": right, "left_ok": ok(left), "right_ok": ok(right)}


def query_as_data(payload: str) -> dict:
    con = sqlite3.connect(":memory:")
    con.execute("create table item(name text)")
    con.execute("insert into item(name) values ('known')")
    query = "select count(*) from item where name = ?"
    with_payload = con.execute(query, (payload,)).fetchone()[0]
    plain = con.execute(query, ("known",)).fetchone()[0]
    return {
        "tool": "query_as_data",
        "endpoint": "in-memory sqlite, not a recovered laboratory service",
        "query": query,
        "payload": payload,
        "rows_for_payload": with_payload,
        "rows_for_known": plain,
        "concatenated": False,
    }


def path_jail(relative: str) -> dict:
    base = Path(tempfile.mkdtemp(prefix="r1-jail-"))
    allowed = base / "allowed"
    allowed.mkdir()
    candidate = (allowed / relative).resolve()
    blocked = allowed.resolve() not in candidate.parents and candidate != allowed.resolve()
    return {"tool": "path_jail", "requested": relative, "resolved": str(candidate), "blocked": blocked, "read": False}


def tokenize(text: str) -> dict:
    tokens = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch.isalpha():
            j = i + 1
            while j < len(text) and (text[j].isalnum() or text[j] == "_"):
                j += 1
            word = text[i:j]
            kind = "keyword" if word in {"let"} else "ident"
            tokens.append({"kind": kind, "text": word, "start": i})
            i = j
            continue
        if ch.isdigit():
            j = i + 1
            while j < len(text) and text[j].isdigit():
                j += 1
            tokens.append({"kind": "number", "text": text[i:j], "start": i})
            i = j
            continue
        tokens.append({"kind": "symbol", "text": ch, "start": i})
        i += 1
    return {"tool": "tokenize", "text": text, "tokens": tokens}


def arithmetic(text: str) -> dict:
    tree = ast.parse(text, mode="eval")
    grouped_sum = any(isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult) and isinstance(node.left, ast.BinOp) and isinstance(node.left.op, ast.Add) for node in ast.walk(tree))
    value = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
    return {"tool": "arithmetic", "text": text, "value": value, "sum_grouped_before_product": grouped_sum}


def ipv4_pair(first: str, second: str) -> dict:
    def accept(text: str) -> bool:
        try:
            ipaddress.IPv4Address(text)
            return True
        except ipaddress.AddressValueError:
            return False
    return {"tool": "ipv4_pair", "first": first, "second": second, "first_ok": accept(first), "second_ok": accept(second)}


def ipv6_two_compressions(text: str) -> dict:
    rejected = text.count("::") != 1
    return {"tool": "ipv6_two_compressions", "text": text, "compressions": text.count("::"), "rejected": rejected}


def _simple_float(expr: str) -> float:
    if "+" in expr:
        a, b = expr.split("+", 1)
        return float(a) + float(b)
    return float(expr)


def float_gap(left: str, right: str) -> dict:
    a, b = _simple_float(left), _simple_float(right)
    return {"tool": "float_gap", "left": left, "right": right, "equal_as_float": a == b, "difference": format(a - b, ".20f")}


def host_facts() -> dict:
    distro = "unknown"
    osr = Path("/etc/os-release")
    if osr.exists():
        for line in osr.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                distro = line.split("=", 1)[1].strip().strip('"')
    return {
        "tool": "host_facts",
        "kernel_source": "platform.release",
        "kernel": platform.release(),
        "distro_source": "/etc/os-release" if osr.exists() else "absent",
        "distro": distro,
        "arch_source": "platform.machine",
        "arch": platform.machine(),
    }


def git_readme() -> dict:
    if shutil.which("git") is None:
        return {"tool": "git_readme", "available": False}
    base = Path(tempfile.mkdtemp(prefix="r1-git-"))
    subprocess.run(["git", "init"], cwd=base, check=True, capture_output=True, text=True)
    subprocess.run(["git", "config", "user.email", "r1@example.invalid"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "R1"], cwd=base, check=True, capture_output=True)
    (base / "README").write_text("README\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add README"], cwd=base, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=base, check=True, capture_output=True, text=True).stdout.strip()
    status = subprocess.run(["git", "status", "--porcelain"], cwd=base, check=True, capture_output=True, text=True).stdout
    return {"tool": "git_readme", "available": True, "path": str(base), "head": head, "clean": status == "", "readme_origin": "filename named by the operation; body is one line because the operation states none"}


def cliente_pedido() -> dict:
    con = sqlite3.connect(":memory:")
    con.execute("create table cliente(id integer primary key)")
    con.execute("create table pedido(id integer primary key, cliente_id integer references cliente(id))")
    tables = [row[0] for row in con.execute("select name from sqlite_master where type='table' order by name")]
    fks = list(con.execute("pragma foreign_key_list(pedido)"))
    return {"tool": "cliente_pedido", "tables": tables, "pedido_foreign_keys": len(fks)}
