"""Format checks using SQLite header constants and WebAssembly binary contract."""
from __future__ import annotations


def sqlite_header_oracle(arguments: dict, observed: dict) -> dict:
    expected_page_size = arguments["page_size"]
    ok = observed.get("page_size") == expected_page_size and observed.get("encoding") == "UTF-8" and observed.get("signature_valid") is True and observed.get("read_version") in {1, 2} and observed.get("write_version") in {1, 2}
    return {"ok": ok, "method": "SQLite file-format header offsets 16, 18, 19, and 56"}


def sqlite_integrity_oracle(arguments: dict, observed: dict) -> dict:
    if arguments["corrupt"]:
        ok = observed.get("integrity") is False and observed.get("corrupt_input") is True and bool(observed.get("messages"))
    else:
        ok = observed.get("integrity") is True and observed.get("messages") == ["ok"] and observed.get("corrupt_input") is False
    return {"ok": ok, "method": "source corruption flag and SQLite integrity result contract"}


def wasm_header_oracle(arguments: dict, observed: dict) -> dict:
    magic_ok = bytes.fromhex(arguments["magic_hex"]) == b"\0asm"
    return {"ok": observed.get("magic_valid") is magic_ok and observed.get("version") == arguments["version"] and observed.get("accepted") is (magic_ok and arguments["version"] == 1), "method": "WebAssembly core binary magic and little-endian version 1"}
