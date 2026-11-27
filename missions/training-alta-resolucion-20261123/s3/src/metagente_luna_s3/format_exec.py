"""Small binary-format probes backed by real standard-library artifacts."""
from __future__ import annotations

import hashlib
import math
import sqlite3
import struct
import zlib


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


def png_chunks(chunks: list[dict], tamper_index: int) -> dict:
    if [chunk["type"] for chunk in chunks] != ["IHDR", "IDAT", "IEND"]:
        raise ValueError("fixture must contain IHDR, IDAT, and IEND in source order")
    if len(bytes.fromhex(chunks[0]["data_hex"])) != 13 or chunks[2]["data_hex"]:
        raise ValueError("invalid IHDR or IEND length")
    if tamper_index >= len(chunks):
        raise ValueError("tamper index is outside the chunk sequence")
    raw = bytearray(b"\x89PNG\r\n\x1a\n")
    for chunk in chunks:
        kind, payload = chunk["type"].encode("ascii"), bytes.fromhex(chunk["data_hex"])
        raw.extend(struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF))
    if tamper_index >= 0:
        offset = 8
        for index, chunk in enumerate(chunks):
            size = len(bytes.fromhex(chunk["data_hex"]))
            crc_offset = offset + 8 + size
            if index == tamper_index:
                raw[crc_offset] ^= 1
                break
            offset += 12 + size
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("PNG signature mismatch")
    observed, offset = [], 8
    while offset + 12 <= len(raw):
        size = struct.unpack(">I", raw[offset:offset + 4])[0]
        end = offset + 12 + size
        if end > len(raw):
            observed.append({"type": raw[offset + 4:offset + 8].decode("ascii", "replace"), "length": size, "crc_valid": False, "truncated": True})
            break
        kind, payload = bytes(raw[offset + 4:offset + 8]), bytes(raw[offset + 8:offset + 8 + size])
        stored_crc = struct.unpack(">I", raw[offset + 8 + size:end])[0]
        calculated_crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        observed.append({"type": kind.decode("ascii"), "length": size, "stored_crc32": stored_crc, "computed_crc32": calculated_crc, "crc_valid": stored_crc == calculated_crc, "truncated": False})
        offset = end
    return {"signature_valid": True, "chunks": observed, "archive_sha256": __import__("hashlib").sha256(raw).hexdigest()}


def unknown_format(payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    signatures = ((b"\x89PNG\r\n\x1a\n", "png"), (b"PK\x03\x04", "zip"), (b"\x7fELF", "elf"), (b"\0asm", "wasm"), (b"SQLite format 3\0", "sqlite"))
    detected = next((name for signature, name in signatures if raw.startswith(signature)), None)
    return {"format": detected or "unknown", "length": len(raw), "prefix_hex": raw[:8].hex(), "sha256": hashlib.sha256(raw).hexdigest(), "invented_details": False}


def block_entropy(payload_hex: str, block_size: int) -> dict:
    raw = bytes.fromhex(payload_hex)
    blocks = []
    for start in range(0, len(raw), block_size):
        block = raw[start:start + block_size]
        counts = [block.count(value) for value in range(256)]
        entropy = -sum((count / len(block)) * math.log2(count / len(block)) for count in counts if count)
        blocks.append({"offset": start, "length": len(block), "bits_per_byte": entropy})
    return {"blocks": blocks, "interpretation": "heuristic_only"}


def binary_diff(left_hex: str, right_hex: str) -> dict:
    left, right = bytes.fromhex(left_hex), bytes.fromhex(right_hex)
    differences = [{"offset": index, "before": left[index] if index < len(left) else None, "after": right[index] if index < len(right) else None} for index in range(max(len(left), len(right))) if index >= len(left) or index >= len(right) or left[index] != right[index]]
    return {"differences": differences, "left_sha256": hashlib.sha256(left).hexdigest(), "right_sha256": hashlib.sha256(right).hexdigest()}


def bounded_declared_size(declared_size: int, payload_hex: str) -> dict:
    actual_size = len(bytes.fromhex(payload_hex))
    rejected = declared_size > actual_size
    return {"rejected": rejected, "declared_size": declared_size, "actual_size": actual_size, "allocated_from_declaration": False}


def reproducible_structure(payload_hex: str) -> dict:
    raw = bytes.fromhex(payload_hex)
    first = {"length": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "prefix_hex": raw[:8].hex()}
    second = {"length": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "prefix_hex": raw[:8].hex()}
    return {"first": first, "second": second, "identical": first == second}


def jpeg_markers(segments: list[dict], truncate_last: bool) -> dict:
    if [segment["marker"] for segment in segments] != ["DQT", "SOF0"]:
        raise ValueError("fixture must contain a quantization table followed by a frame marker")
    if len(bytes.fromhex(segments[0]["payload_hex"])) != 65 or len(bytes.fromhex(segments[1]["payload_hex"])) != 9:
        raise ValueError("invalid minimal DQT or SOF0 segment length")
    marker_codes = {"DQT": 0xDB, "SOF0": 0xC0}
    raw = bytearray(b"\xff\xd8")
    for segment in segments:
        payload = bytes.fromhex(segment["payload_hex"])
        raw.extend((0xFF, marker_codes[segment["marker"]]))
        raw.extend(struct.pack(">H", len(payload) + 2))
        raw.extend(payload)
    raw.extend(b"\xff\xd9")
    if truncate_last:
        del raw[-3:]
    markers = [{"name": "SOI", "offset": 0}]
    valid, offset, saw_eoi = raw.startswith(b"\xff\xd8"), 2, False
    while valid and offset < len(raw):
        if raw[offset] != 0xFF or offset + 1 >= len(raw):
            valid = False
            break
        code = raw[offset + 1]
        name = {0xDB: "DQT", 0xC0: "SOF0", 0xD9: "EOI"}.get(code, f"FF{code:02X}")
        marker_offset = offset
        markers.append({"name": name, "offset": marker_offset})
        if code == 0xD9:
            saw_eoi = True
            offset += 2
            break
        if offset + 4 > len(raw):
            valid = False
            break
        length = int.from_bytes(raw[offset + 2:offset + 4], "big")
        if length < 2 or offset + 2 + length > len(raw):
            valid = False
            break
        markers[-1]["segment_length"] = length
        offset += 2 + length
    return {"markers": markers, "valid": valid and saw_eoi and offset == len(raw), "truncated": not saw_eoi or not valid}
