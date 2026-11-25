"""Executors. Selection is by operation shape, never by case id."""
from __future__ import annotations

import ast
import codecs
import os
import platform
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path


def utf16_be(text: str) -> dict:
    encoded = codecs.encode(text, "utf-16-be")
    return {"tool": "utf16_be", "text": text, "hex": encoded.hex(), "decoded": codecs.decode(encoded, "utf-16-be")}


def binary_identity(values: list[int]) -> dict:
    data = bytes(values)
    return {"tool": "binary_identity", "values": list(data), "hex": data.hex(), "roundtrip": list(bytes.fromhex(data.hex()))}


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
    return {"tool": "brackets", "left": left, "right": right, "left_ok": ok(left), "right_ok": ok(right), "independence": "partial"}


def query_simulation(payload: str) -> dict:
    path = Path(tempfile.mkdtemp(prefix="s1-sql-")) / "lab.sqlite"
    con = sqlite3.connect(path)
    con.execute("create table item(name text)")
    con.execute("insert into item(name) values ('known')")
    con.commit()
    query = "select count(*) from item where name = ?"
    rows = con.execute(query, (payload,)).fetchone()[0]
    con.close()
    return {"tool": "query_simulation", "simulation": True, "endpoint": "not a recovered laboratory service", "path": str(path), "query": query, "payload": payload, "rows": rows}


def path_simulation(relative: str) -> dict:
    base = Path(tempfile.mkdtemp(prefix="s1-jail-"))
    allowed = base / "allowed"
    allowed.mkdir()
    resolved = (allowed / relative).resolve()
    inside = resolved == allowed.resolve() or allowed.resolve() in resolved.parents
    return {"tool": "path_simulation", "simulation": True, "requested": relative, "resolved": str(resolved), "blocked": not inside, "read": False}


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
            tokens.append({"kind": "keyword" if word in {"let"} else "ident", "text": word, "start": i})
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
    return {"tool": "tokenize", "text": text, "tokens": tokens, "independence": "partial"}


def arithmetic(text: str) -> dict:
    tree = ast.parse(text, mode="eval")
    grouped = any(isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mult) and isinstance(n.left, ast.BinOp) and isinstance(n.left.op, ast.Add) for n in ast.walk(tree))
    value = eval(compile(tree, "<expr>", "eval"), {"__builtins__": {}}, {})
    return {"tool": "arithmetic", "text": text, "value": value, "sum_inside_product": grouped}


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
    other = float(right)
    return {"tool": "float_gap", "expr": expr, "right": right, "equal": left == other, "difference": format(left - other, ".20f"), "claims_universal_equality": False}


def host_facts() -> dict:
    distro = None
    osr = Path("/etc/os-release")
    if osr.exists():
        for line in osr.read_text(encoding="utf-8").splitlines():
            if line.startswith("PRETTY_NAME="):
                distro = line.split("=", 1)[1].strip().strip('"')
    return {"tool": "host_facts", "kernel": platform.release(), "kernel_source": "platform.release", "distro": distro, "distro_source": "/etc/os-release" if distro else "absent", "arch": platform.machine(), "arch_source": "platform.machine"}


def git_readme() -> dict:
    if shutil.which("git") is None:
        return {"tool": "git_readme", "available": False}
    base = Path(tempfile.mkdtemp(prefix="s1-git-"))
    subprocess.run(["git", "init"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "s1@example.invalid"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "S1"], cwd=base, check=True, capture_output=True)
    (base / "README").write_text("README\n", encoding="utf-8")
    subprocess.run(["git", "add", "README"], cwd=base, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "add README"], cwd=base, check=True, capture_output=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=base, check=True, capture_output=True, text=True).stdout.strip()
    clean = subprocess.run(["git", "status", "--porcelain"], cwd=base, check=True, capture_output=True, text=True).stdout == ""
    return {"tool": "git_readme", "available": True, "path": str(base), "head": head, "clean": clean, "readme_body_origin": "filename is in the operation; the one-line body is not"}


def cliente_pedido() -> dict:
    path = Path(tempfile.mkdtemp(prefix="s1-db-")) / "db.sqlite"
    con = sqlite3.connect(path)
    con.execute("create table cliente(id integer primary key)")
    con.execute("create table pedido(id integer primary key, cliente_id integer references cliente(id))")
    con.commit()
    con.close()
    return {"tool": "cliente_pedido", "path": str(path), "column_origin": "table names and primary key are in the operation; column names are the minimum needed to declare those constraints"}


EXECUTORS = {
    "utf16_be": utf16_be,
    "binary_identity": binary_identity,
    "brackets": brackets,
    "query_simulation": query_simulation,
    "path_simulation": path_simulation,
    "tokenize": tokenize,
    "arithmetic": arithmetic,
    "ipv4_pair": ipv4_pair,
    "float_gap": float_gap,
    "host_facts": host_facts,
    "git_readme": git_readme,
    "cliente_pedido": cliente_pedido,
}
