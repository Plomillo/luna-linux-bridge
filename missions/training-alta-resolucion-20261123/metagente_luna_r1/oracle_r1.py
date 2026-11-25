"""Independent checks. This module does not import the agent tools."""
from __future__ import annotations

import ast
import ipaddress
import os
import platform
import sqlite3
import subprocess
from pathlib import Path


def check(observed: dict) -> dict:
    tool = observed.get("tool")
    if tool == "utf16_be":
        encoded = bytes.fromhex(observed["hex"])
        chars = [chr(encoded[i] * 256 + encoded[i + 1]) for i in range(0, len(encoded), 2)]
        return {"ok": "".join(chars) == observed["text"] and observed["byte_order"] == "big"}
    if tool == "hex_bytes":
        return {"ok": bytes(observed["decoded"]).hex() == observed["encoded"]}
    if tool == "brackets":
        def ok(text: str) -> bool:
            pairs = {")": "(", "]": "[", "}": "{"}
            stack = []
            for ch in text:
                if ch in "([{":
                    stack.append(ch)
                elif ch in pairs:
                    if not stack or stack.pop() != pairs[ch]:
                        return False
            return not stack
        return {"ok": ok(observed["left"]) is True and ok(observed["right"]) is False}
    if tool == "query_as_data":
        con = sqlite3.connect(":memory:")
        con.execute("create table item(name text)")
        con.execute("insert into item(name) values ('known')")
        payload_rows = con.execute(observed["query"], (observed["payload"],)).fetchone()[0]
        return {"ok": "?" in observed["query"] and payload_rows == 0 and observed["rows_for_known"] == 1}
    if tool == "path_jail":
        resolved = Path(observed["resolved"]).resolve()
        return {"ok": observed["blocked"] is True and observed["read"] is False and "etc/passwd" in observed["requested"] and not str(resolved).startswith("/etc/")}
    if tool == "tokenize":
        kinds = [item["kind"] for item in observed["tokens"]]
        return {"ok": kinds[:4] == ["keyword", "ident", "symbol", "number"] and observed["tokens"][-1]["text"] == ";"}
    if tool == "arithmetic":
        tree = ast.parse(observed["text"], mode="eval")
        value = eval(compile(tree, "<oracle>", "eval"), {"__builtins__": {}}, {})
        return {"ok": value == 9 and observed["value"] == 9 and observed["sum_grouped_before_product"] is True}
    if tool == "ipv4_pair":
        def accept(text: str) -> bool:
            try:
                ipaddress.IPv4Address(text)
                return True
            except ipaddress.AddressValueError:
                return False
        return {"ok": accept(observed["first"]) and not accept(observed["second"])}
    if tool == "ipv6_two_compressions":
        return {"ok": observed["text"].count("::") == 2 and observed["rejected"] is True}
    if tool == "float_gap":
        left = observed["left"]
        got = float(left.split("+")[0]) + float(left.split("+")[1]) if "+" in left else float(left)
        return {"ok": observed["equal_as_float"] is False and got != float(observed["right"])}
    if tool == "host_facts":
        kernel = Path("/proc/sys/kernel/osrelease").read_text().strip()
        return {"ok": bool(observed["kernel"] == kernel and observed["arch"] == platform.machine() and observed["kernel_source"])}
    if tool == "git_readme":
        if not observed.get("available"):
            return {"ok": False, "reason": "git missing"}
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout.strip()
        status = subprocess.run(["git", "status", "--porcelain"], cwd=observed["path"], check=True, capture_output=True, text=True).stdout
        return {"ok": head == observed["head"] and status == "" and observed["clean"] is True}
    if tool == "cliente_pedido":
        return {"ok": observed["tables"] == ["cliente", "pedido"] and observed["pedido_foreign_keys"] == 1}
    return {"ok": False, "reason": "ORACLE_HAS_NO_CHECK"}
