"""Small binary-format probes backed by real standard-library artifacts."""
from __future__ import annotations

import sqlite3


def sqlite_header(page_size: int) -> dict:
    connection = sqlite3.connect(":memory:")
    try:
        connection.execute(f"PRAGMA page_size={page_size}")
        connection.execute("CREATE TABLE sample(value TEXT)")
        raw = connection.serialize()
    finally:
        connection.close()
    if raw[:16] != b"SQLite format 3\0":
        raise ValueError("SQLite signature mismatch")
    encoded_page_size = int.from_bytes(raw[16:18], "big")
    stored_page_size = 65536 if encoded_page_size == 1 else encoded_page_size
    encoding_id = int.from_bytes(raw[56:60], "big")
    return {
        "page_size": stored_page_size,
        "encoding": {1: "UTF-8", 2: "UTF-16le", 3: "UTF-16be"}.get(encoding_id, "unknown"),
        "read_version": raw[18],
        "write_version": raw[19],
        "signature_valid": True,
    }


def sqlite_integrity(corrupt: bool, values: list[str]) -> dict:
    source = sqlite3.connect(":memory:")
    try:
        source.execute("CREATE TABLE sample(value TEXT NOT NULL)")
        source.executemany("INSERT INTO sample(value) VALUES (?)", [(value,) for value in values])
        raw = bytearray(source.serialize())
    finally:
        source.close()
    if corrupt:
        raw[:16] = b"Broken SQLite!!!"
    target = sqlite3.connect(":memory:")
    try:
        try:
            target.deserialize(bytes(raw))
            result = target.execute("PRAGMA integrity_check").fetchall()
            return {"integrity": result == [("ok",)], "messages": [row[0] for row in result], "corrupt_input": corrupt}
        except sqlite3.DatabaseError as exc:
            return {"integrity": False, "messages": [str(exc)], "corrupt_input": corrupt}
    finally:
        target.close()


def wasm_header(magic_hex: str, version: int) -> dict:
    raw = bytes.fromhex(magic_hex) + version.to_bytes(4, "little")
    valid_magic = raw[:4] == b"\0asm"
    parsed_version = int.from_bytes(raw[4:8], "little") if len(raw) >= 8 else None
    return {"accepted": valid_magic and parsed_version == 1, "magic_valid": valid_magic, "version": parsed_version}
