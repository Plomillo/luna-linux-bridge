"""Format checks using SQLite header constants and WebAssembly binary contract."""
from __future__ import annotations

import hashlib
import math
import zlib


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


def png_chunks_oracle(arguments: dict, observed: dict) -> dict:
    chunks = observed.get("chunks", [])
    expected_types = [chunk["type"] for chunk in arguments["chunks"]]
    if len(chunks) != len(arguments["chunks"]):
        return {"ok": False, "method": "independent PNG type/length/CRC reconstruction"}
    expected_crc = [zlib.crc32(chunk["type"].encode("ascii") + bytes.fromhex(chunk["data_hex"])) & 0xFFFFFFFF for chunk in arguments["chunks"]]
    expected_valid = [index != arguments["tamper_index"] for index in range(len(chunks))]
    ok = (
        observed.get("signature_valid") is True
        and [row.get("type") for row in chunks] == expected_types
        and [row.get("length") for row in chunks] == [len(bytes.fromhex(chunk["data_hex"])) for chunk in arguments["chunks"]]
        and [row.get("crc_valid") for row in chunks] == expected_valid
        and [row.get("computed_crc32") for row in chunks] == expected_crc
        and all((row.get("stored_crc32") == expected_crc[index]) is expected_valid[index] for index, row in enumerate(chunks))
        and all(row.get("truncated") is False for row in chunks)
    )
    return {"ok": ok, "method": "independent PNG type/length/CRC reconstruction"}


def unknown_format_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    signatures = ((b"\x89PNG\r\n\x1a\n", "png"), (b"PK\x03\x04", "zip"), (b"\x7fELF", "elf"), (b"\0asm", "wasm"), (b"SQLite format 3\0", "sqlite"))
    expected_format = next((name for signature, name in signatures if raw.startswith(signature)), "unknown")
    return {"ok": observed.get("format") == expected_format and observed.get("length") == len(raw) and observed.get("prefix_hex") == raw[:8].hex() and observed.get("sha256") == hashlib.sha256(raw).hexdigest() and observed.get("invented_details") is False, "method": "independent known-signature catalog, exact length, and SHA-256"}


def block_entropy_oracle(arguments: dict, observed: dict) -> dict:
    raw, size = bytes.fromhex(arguments["payload_hex"]), arguments["block_size"]
    expected = []
    for start in range(0, len(raw), size):
        block = raw[start:start + size]
        entropy = -sum((count / len(block)) * math.log2(count / len(block)) for count in (block.count(value) for value in set(block)) if count)
        expected.append({"offset": start, "length": len(block), "bits_per_byte": entropy})
    actual = observed.get("blocks", [])
    equal = len(actual) == len(expected) and all(a["offset"] == e["offset"] and a["length"] == e["length"] and abs(a["bits_per_byte"] - e["bits_per_byte"]) < 1e-12 for a, e in zip(actual, expected, strict=True))
    return {"ok": equal and observed.get("interpretation") == "heuristic_only", "method": "independent frequency histogram and Shannon formula"}


def binary_diff_oracle(arguments: dict, observed: dict) -> dict:
    left, right = bytes.fromhex(arguments["left_hex"]), bytes.fromhex(arguments["right_hex"])
    expected = [{"offset": i, "before": left[i] if i < len(left) else None, "after": right[i] if i < len(right) else None} for i in range(max(len(left), len(right))) if i >= len(left) or i >= len(right) or left[i] != right[i]]
    return {"ok": observed.get("differences") == expected and observed.get("left_sha256") == hashlib.sha256(left).hexdigest() and observed.get("right_sha256") == hashlib.sha256(right).hexdigest(), "method": "bytewise comparison and independent SHA-256"}


def bounded_size_oracle(arguments: dict, observed: dict) -> dict:
    actual = len(bytes.fromhex(arguments["payload_hex"]))
    return {"ok": observed.get("actual_size") == actual and observed.get("declared_size") == arguments["declared_size"] and observed.get("rejected") is (arguments["declared_size"] > actual) and observed.get("allocated_from_declaration") is False, "method": "measured input length and no-allocation invariant"}


def reproducible_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    expected = {"length": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "prefix_hex": raw[:8].hex()}
    return {"ok": observed.get("first") == expected and observed.get("second") == expected and observed.get("identical") is True, "method": "independent source digest and byte-length derivation"}


def jpeg_markers_oracle(arguments: dict, observed: dict) -> dict:
    expected = [{"name": "SOI", "offset": 0}]
    offset = 2
    for segment in arguments["segments"]:
        length = len(bytes.fromhex(segment["payload_hex"])) + 2
        expected.append({"name": segment["marker"], "offset": offset, "segment_length": length})
        offset += 2 + length
    if not arguments["truncate_last"]:
        expected.append({"name": "EOI", "offset": offset})
    complete = not arguments["truncate_last"]
    return {"ok": observed.get("markers") == expected and observed.get("valid") is complete and observed.get("truncated") is (not complete), "method": "independent marker offsets and length-field reconstruction"}


def partial_recovery_oracle(arguments: dict, observed: dict) -> dict:
    header, magic = bytes.fromhex(arguments["header_hex"]), bytes.fromhex(arguments["expected_magic_hex"])
    valid = bool(magic) and header.startswith(magic)
    recovered = bytes.fromhex(arguments["payload_hex"]).hex() if valid else ""
    return {"ok": observed.get("header_valid") is valid and observed.get("recovered_hex") == recovered and observed.get("unknown_trailer") is True and observed.get("integrity_complete") is False, "method": "independent magic-prefix validation and exact payload provenance"}


def timestamp_provenance_oracle(arguments: dict, observed: dict) -> dict:
    expected = [{"value": arguments["metadata_timestamp"], "source": "embedded_metadata"}, {"value": arguments["filesystem_timestamp"], "source": "filesystem"}]
    return {"ok": observed.get("timestamps") == expected and observed.get("creation_time_proven") is False and bool(observed.get("warning")), "method": "input-source equality and non-inference invariant"}


def dependency_graph_oracle(arguments: dict, observed: dict) -> dict:
    nodes, edges, root = arguments["nodes"], arguments["edges"], arguments["root"]
    if root not in nodes or any(source not in nodes or target not in nodes for source, target in edges):
        return {"ok": observed.get("rejected") is True and observed.get("reachable") == [], "method": "independent endpoint validation"}
    adjacency = {node: [] for node in nodes}
    for source, target in edges:
        adjacency[source].append(target)
    reachable, queue = set(), [root]
    while queue:
        current = queue.pop(0)
        for target in adjacency[current]:
            if target not in reachable:
                reachable.add(target)
                queue.append(target)
    relevant = {root, *reachable}
    indegree = {node: 0 for node in relevant}
    for source, target in edges:
        if source in relevant and target in relevant:
            indegree[target] += 1
    queue = [node for node, degree in indegree.items() if degree == 0]
    removed = 0
    while queue:
        source = queue.pop()
        removed += 1
        for target in adjacency[source]:
            if target in indegree:
                indegree[target] -= 1
                if indegree[target] == 0:
                    queue.append(target)
    cycle = removed != len(relevant)
    return {"ok": observed.get("rejected") is False and observed.get("reachable") == sorted(reachable) and observed.get("cycle") is cycle, "method": "independent BFS closure and Kahn cycle detection"}
