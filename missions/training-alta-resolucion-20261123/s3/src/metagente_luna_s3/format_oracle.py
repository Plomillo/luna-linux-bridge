"""Format checks using SQLite header constants and WebAssembly binary contract."""
from __future__ import annotations

import hashlib
import math
import struct
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


def protocol_version_diff_oracle(arguments: dict, observed: dict) -> dict:
    old = {row["name"]: (row["width"], row["offset"]) for row in arguments["old_fields"]}
    new = {row["name"]: (row["width"], row["offset"]) for row in arguments["new_fields"]}
    names = set(old) | set(new)
    expected = []
    for name in sorted(names):
        if old.get(name) != new.get(name):
            expected.append((name, "added" if name not in old else "removed" if name not in new else "modified"))
    actual = [(row.get("field"), row.get("change")) for row in observed.get("changes", [])]
    compatible = all(change == "added" for _, change in expected)
    return {"ok": actual == expected and observed.get("backward_compatible") is compatible and observed.get("forward_compatible") is compatible, "method": "independent field tuple comparison and compatibility policy"}


def section_overlaps_oracle(arguments: dict, observed: dict) -> dict:
    ordered = sorted(arguments["sections"], key=lambda row: (row["offset"], row["size"], row["name"]))
    overlaps = []
    for index, left in enumerate(ordered):
        for right in ordered[index + 1:]:
            if right["offset"] >= left["offset"] + left["size"]:
                break
            overlaps.append({"left": left["name"], "right": right["name"], "overlap_start": right["offset"], "overlap_end": min(left["offset"] + left["size"], right["offset"] + right["size"])})
    actual = sorted(observed.get("overlaps", []), key=lambda row: (row["overlap_start"], row["overlap_end"], row["left"], row["right"]))
    expected = sorted(overlaps, key=lambda row: (row["overlap_start"], row["overlap_end"], row["left"], row["right"]))
    return {"ok": actual == expected and observed.get("valid") is (not bool(expected)), "method": "independent sorted interval sweep"}


def nested_zip_tar_oracle(arguments: dict, observed: dict) -> dict:
    expected_files = [{"name": row["name"], "size": len(bytes.fromhex(row["data_hex"])), "data_hex": row["data_hex"]} for row in arguments["entries"]]
    tree = observed.get("tree", {})
    children = tree.get("children", [])
    return {"ok": tree.get("name") == "outer.zip" and len(children) == 1 and children[0].get("name") == "inner.tar" and children[0].get("children") == expected_files and bool(observed.get("nested_sha256")), "method": "source-entry equality through expected parent-child container path"}


def forensic_report_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    expected = []
    if arguments["declared_size"] != len(raw):
        expected.append({"code": "DECLARED_SIZE_MISMATCH", "offset": 0, "observed": arguments["declared_size"], "actual": len(raw)})
    checksum = zlib.crc32(raw) & 0xFFFFFFFF
    if arguments["stored_crc32"] != checksum:
        expected.append({"code": "CRC_MISMATCH", "offset": len(raw), "stored": arguments["stored_crc32"], "computed": checksum})
    sections = arguments["sections"]
    for index, left in enumerate(sections):
        for right in sections[index + 1:]:
            start, end = max(left["offset"], right["offset"]), min(left["offset"] + left["size"], right["offset"] + right["size"])
            if start < end:
                expected.append({"code": "SECTION_OVERLAP", "offset": start, "sections": [left["name"], right["name"]]})
    inference_rows = [{"anomaly": item["code"], "confidence": "structural"} for item in expected]
    conclusion = {"anomaly_count": len(expected), "integrity": "INCOMPLETE" if expected else "NO_ANOMALY_DETECTED"}
    return {"ok": observed.get("observations") == expected and observed.get("inferences") == inference_rows and observed.get("conclusion") == conclusion, "method": "independent size, CRC32, and interval reconstruction"}


def wasm_sections_oracle(arguments: dict, observed: dict) -> dict:
    offset, expected = 8, []
    for item in arguments["sections"]:
        payload_size = len(bytes.fromhex(item["payload_hex"]))
        length_size = 1
        remaining = payload_size
        while remaining >= 128:
            length_size += 1
            remaining >>= 7
        expected.append({"section_id": item["section_id"], "offset": offset, "payload_offset": offset + 1 + length_size, "payload_size": payload_size, "within_module": True})
        offset += 1 + length_size + payload_size
    valid = arguments["truncate_index"] == -1
    if valid:
        matching = observed.get("sections") == expected and observed.get("valid") is True and observed.get("module_size") == offset
    else:
        matching = observed.get("valid") is False and observed.get("module_size") == offset - 1 and all(row.get("within_module") is True for row in observed.get("sections", []))
    return {"ok": matching, "method": "independent ULEB128 length-width and module-offset reconstruction"}


def wasm_type_indices_oracle(arguments: dict, observed: dict) -> dict:
    count, indices = arguments["type_count"], arguments["function_type_indices"]
    invalid = [index for index in indices if index < 0 or index >= count]
    return {"ok": observed.get("rejected") is bool(invalid) and observed.get("type_count") == count and observed.get("function_type_indices") == indices and observed.get("invalid_indices") == invalid, "method": "independent function-index range check"}


def pdf_objects_oracle(arguments: dict, observed: dict) -> dict:
    count = max([2, *(row[0] for row in arguments["references"])])
    present = list(range(1, count + 1))
    expected = [{"object": number, "generation": generation, "resolved": generation == 0 and number in present} for number, generation in arguments["references"]]
    if arguments["missing_object"]:
        expected.append({"object": arguments["missing_object"], "generation": 0, "resolved": arguments["missing_object"] in present})
    ok = observed.get("objects") == present and observed.get("references") == expected and all(row["resolved"] for row in expected[:-1]) and (not arguments["missing_object"] or expected[-1]["resolved"] is False)
    return {"ok": ok, "method": "independent fixture object population and generation-aware reference resolution"}


def pdf_xref_oracle(arguments: dict, observed: dict) -> dict:
    header = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    bodies = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"]
    offsets, cursor = {}, len(header)
    for number, body in enumerate(bodies, 1):
        offsets[number] = cursor
        cursor += len(f"{number} 0 obj\n".encode()) + len(body) + len(b"\nendobj\n")
    discrepancies = []
    if arguments["corrupt_object"]:
        number = arguments["corrupt_object"]
        discrepancies.append({"object": number, "declared_offset": offsets[number] + 1, "actual_offset": offsets[number]})
    ok = observed.get("object_offsets") == offsets and observed.get("discrepancies") == discrepancies and observed.get("valid") is (not bool(discrepancies))
    return {"ok": ok, "method": "independent PDF byte-offset reconstruction from header, object headers, and body lengths"}


def pdf_encryption_boundary_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["pdf_hex"])
    trailer_start = raw.rfind(b"trailer")
    trailer = raw[trailer_start:] if trailer_start >= 0 else b""
    encrypted = b"/Encrypt " in trailer and b" R" in trailer
    match = __import__("re").search(rb"/Encrypt\s+(\d+)\s+(\d+)\s+R", trailer)
    dictionary = b""
    if match:
        number = int(match.group(1))
        object_start = raw.find(f"{number} 0 obj".encode())
        object_end = raw.find(b"endobj", object_start)
        if object_start >= 0 and object_end >= 0:
            dictionary = raw[object_start:object_end]
    valid_handler = b"/Filter /Standard" in dictionary
    def integer(key: bytes):
        found = __import__("re").search(rb"/" + key + rb"\s+(-?\d+)", dictionary)
        return int(found.group(1)) if found else None
    expected = {
        "encrypted": encrypted and valid_handler,
        "handler": "Standard" if encrypted and valid_handler else None,
        "revision": integer(b"R") if encrypted else None,
        "version": integer(b"V") if encrypted else None,
        "key_length_bits": integer(b"Length") if encrypted else None,
        "permissions": integer(b"P") if encrypted else None,
        "password_supplied": False,
        "content_available": False,
        "plaintext_claim": None,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    return {"ok": observed == expected and (not encrypted or valid_handler), "method": "independent trailer reference and Standard security-dictionary inspection; no plaintext assertion"}


def elf_symbol_tables_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    if raw[:6] != b"\x7fELF\x02\x01" or len(raw) < 64:
        return {"ok": observed.get("rejected") is True, "method": "independent ELF identification and readelf failure contract"}
    shoff = struct.unpack_from("<Q", raw, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", raw, 58)
    if shentsize < 64 or shnum == 0 or shstrndx >= shnum or shoff + shentsize * shnum > len(raw):
        return {"ok": observed.get("rejected") is True, "method": "independent ELF section-table bounds validation"}
    section_rows = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + i * shentsize) for i in range(shnum)]
    names_header = section_rows[shstrndx]
    names_data = raw[names_header[4]:names_header[4] + names_header[5]]
    def cstring(data: bytes, offset: int) -> str:
        end = data.find(b"\0", offset)
        return data[offset:end if end >= 0 else len(data)].decode("utf-8", "replace")
    sections = {cstring(names_data, row[0]): row for row in section_rows}
    binding_names = {0: "LOCAL", 1: "GLOBAL", 2: "WEAK"}
    type_names = {0: "NOTYPE", 1: "OBJECT", 2: "FUNC", 3: "SECTION", 4: "FILE", 5: "COMMON", 6: "TLS", 10: "IFUNC"}
    visibility_names = {0: "DEFAULT", 1: "INTERNAL", 2: "HIDDEN", 3: "PROTECTED"}
    section_names = {0: "UND", 0xFFF1: "ABS", 0xFFF2: "COM"}
    parsed = {}
    for name, section in sections.items():
        if section[1] not in (2, 11):
            continue
        strings = section_rows[section[6]]
        string_data = raw[strings[4]:strings[4] + strings[5]]
        entries = []
        for offset in range(section[4], section[4] + section[5], section[9]):
            st_name, info, other, shndx, value, size = struct.unpack_from("<IBBHQQ", raw, offset)
            symbol_name = cstring(string_data, st_name).split("@", 1)[0].split(" ", 1)[0]
            if not symbol_name:
                continue
            entries.append({"name": symbol_name, "value": value, "size": size, "type": type_names.get(info & 15, f"{info & 15}"), "binding": binding_names.get(info >> 4, f"{info >> 4}"), "visibility": visibility_names.get(other & 3, f"{other & 3}"), "section_index": section_names.get(shndx, str(shndx))})
        parsed[name] = entries
    if ".symtab" not in parsed:
        expected_rejected = arguments.get("require_complete", False)
        ok = observed.get("rejected") is expected_rejected and observed.get("stripped") is True and observed.get("tables") == sorted(parsed) and observed.get("complete_symbols") is None and observed.get("invented_symbols") == [] and (not expected_rejected or observed.get("reason") == "complete_symbol_table_missing")
        return {"ok": ok, "method": "independent ELF section-header and symbol-table decoding; absence of SHT_SYMTAB retained"}
    complete, dynamic = parsed.get(".symtab", []), parsed.get(".dynsym", [])
    key = lambda row: (row["name"], row["value"], row["type"])
    complete_keys, dynamic_keys = {key(row) for row in complete}, {key(row) for row in dynamic}
    required = set(arguments.get("required_symbols", []))
    actual_names = {row["name"] for row in complete}
    ok = (
        observed.get("rejected") is False
        and observed.get("stripped") is False
        and observed.get("tables") == sorted(parsed)
        and observed.get("complete_symbols") == complete
        and observed.get("dynamic_symbols") == dynamic
        and observed.get("complete_only") == sorted(complete_keys - dynamic_keys)
        and observed.get("dynamic_only") == sorted(dynamic_keys - complete_keys)
        and required <= actual_names
        and observed.get("required_symbols_present") is True
        and observed.get("provenance") == {"complete": ".symtab", "dynamic": ".dynsym", "tool": "GNU readelf", "binary_executed": False}
        and observed.get("sha256") == hashlib.sha256(raw).hexdigest()
    )
    return {"ok": ok, "method": "independent ELF64 section and symbol-table reconstruction from linked string tables"}


def elf_host_compatibility_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    valid = len(raw) >= 20 and raw[:4] == b"\x7fELF" and raw[4] in (1, 2) and raw[5] in (1, 2)
    endian = "little" if valid and raw[5] == 1 else "big" if valid else None
    machine = int.from_bytes(raw[18:20], endian) if valid else None
    expected_compatible = valid and machine == arguments["native_machine"]
    header = observed.get("header", {})
    return {"ok": observed.get("native_machine") == arguments["native_machine"] and observed.get("host_compatible") is expected_compatible and header.get("rejected") is (not valid) and (not valid or header.get("architecture") is not None), "method": "independent ELF identification bounds and e_machine field decoding"}


def elf_section_layout_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01":
        return {"ok": observed.get("rejected") is True, "method": "independent ELF64 identification check"}
    shoff, phoff = struct.unpack_from("<QQ", raw, 40)[0], struct.unpack_from("<Q", raw, 32)[0]
    phentsize, phnum, shentsize, shnum, shstrndx = struct.unpack_from("<HHHHH", raw, 54)
    if shentsize < 64 or shnum == 0 or shstrndx >= shnum or shoff + shentsize * shnum > len(raw):
        return {"ok": observed.get("rejected") is True, "method": "independent ELF section table bounds validation"}
    section_headers = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + i * shentsize) for i in range(shnum)]
    names_header = section_headers[shstrndx]
    names_data = raw[names_header[4]:names_header[4] + names_header[5]]
    def cstring(data: bytes, offset: int) -> str:
        end = data.find(b"\0", offset)
        return data[offset:end if end >= 0 else len(data)].decode("utf-8", "replace")
    sections = []
    for index, row in enumerate(section_headers):
        if index == 0:
            continue
        name = cstring(names_data, row[0])
        sections.append({"index": index, "name": name, "address": row[3], "offset": row[4], "size": row[5], "offset_within_file": row[4] <= len(raw)})
    expected_loads = []
    if arguments["include_load_segments"]:
        if phentsize < 56 or phoff + phentsize * phnum > len(raw):
            return {"ok": observed.get("rejected") is True, "method": "independent ELF program header bounds validation"}
        for index in range(phnum):
            header = struct.unpack_from("<IIQQQQQQ", raw, phoff + index * phentsize)
            kind, _flags, offset, vaddr, _paddr, filesz, memsz, _alignment = header
            if kind != 1:
                continue
            associated = [row["name"] for row, section in zip(sections, section_headers[1:], strict=True) if section[2] & 2 and section[3] >= vaddr and section[3] + section[5] <= vaddr + memsz]
            expected_loads.append({"offset": offset, "virtual_address": vaddr, "file_size": filesz, "memory_size": memsz, "associated_sections": associated})
    expected = {"rejected": False, "sections": sections, "load_segments": expected_loads, "section_offsets_valid": all(row["offset_within_file"] for row in sections), "sha256": hashlib.sha256(raw).hexdigest()}
    ok = observed == expected
    return {"ok": ok, "method": "independent ELF section-name string table and program-header interval reconstruction"}


def _elf_dynamic_entries(raw: bytes) -> tuple[list[str], list[str], list[str]] | None:
    if len(raw) < 64 or raw[:6] != b"\x7fELF\x02\x01":
        return None
    shoff = struct.unpack_from("<Q", raw, 40)[0]
    shentsize, shnum, shstrndx = struct.unpack_from("<HHH", raw, 58)
    if shentsize < 64 or shnum == 0 or shstrndx >= shnum or shoff + shentsize * shnum > len(raw):
        return None
    headers = [struct.unpack_from("<IIQQQQIIQQ", raw, shoff + index * shentsize) for index in range(shnum)]
    names_header = headers[shstrndx]
    names = raw[names_header[4]:names_header[4] + names_header[5]]
    def cstring(data: bytes, offset: int) -> str:
        end = data.find(b"\0", offset)
        return data[offset:end if end >= 0 else len(data)].decode("utf-8", "replace")
    sections = {cstring(names, row[0]): row for row in headers}
    dynamic, dynstr = sections.get(".dynamic"), sections.get(".dynstr")
    if dynamic is None or dynstr is None or dynamic[6] >= len(headers):
        return None
    strings = raw[dynstr[4]:dynstr[4] + dynstr[5]]
    needed, rpath, runpath = [], [], []
    entry_size = dynamic[9] or 16
    if entry_size < 16 or dynamic[4] + dynamic[5] > len(raw):
        return None
    for offset in range(dynamic[4], dynamic[4] + dynamic[5], entry_size):
        tag, value = struct.unpack_from("<qQ", raw, offset)
        if tag == 0:
            break
        if tag == 1:
            needed.append(cstring(strings, value))
        elif tag == 15:
            rpath.append(cstring(strings, value))
        elif tag == 29:
            runpath.append(cstring(strings, value))
    return needed, rpath, runpath


def elf_dynamic_dependencies_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    parsed = _elf_dynamic_entries(raw)
    if parsed is None:
        return {"ok": observed.get("rejected") is True, "method": "independent ELF dynamic-section bounds and string-table decoder"}
    needed, rpath, runpath = parsed
    digest = hashlib.sha256(raw).hexdigest()
    trusted = digest in {"73dfd15b920dbc069830e413dfe79bfcc24f9999ceffb3e4da4dec45cf7dbfca", "1003715dcd699bf98061167a830d5fdb5bcefc107952ac584476bd45688da985"}
    resolved = observed.get("runtime_resolved")
    runtime_ok = (
        observed.get("runtime_resolution_attempted") is trusted
        and (not trusted and resolved is None or trusted and isinstance(resolved, dict) and set(resolved) == set(needed))
        and observed.get("runtime_unresolved") == [name for name, path in (resolved or {}).items() if path is None]
        and all(path is None or (isinstance(path, str) and path.startswith("/")) for path in (resolved or {}).values())
    )
    ok = observed.get("rejected") is False and observed.get("declared_dependencies") == needed and observed.get("rpath") == rpath and observed.get("runpath") == runpath and observed.get("program_entry_executed") is False and observed.get("ldd_loaded_dependencies_only") is trusted and runtime_ok and observed.get("sha256") == digest
    return {"ok": ok, "method": "independent ELF SHT_DYNAMIC and linked SHT_STRTAB decoding; runtime outputs constrained to declared names"}


def elf_rpath_runpath_oracle(arguments: dict, observed: dict) -> dict:
    raw = bytes.fromhex(arguments["payload_hex"])
    parsed = _elf_dynamic_entries(raw)
    if parsed is None:
        return {"ok": observed.get("rejected") is True, "method": "independent ELF dynamic-section bounds validation"}
    _needed, rpath, runpath = parsed
    ok = observed == {
        "rejected": False,
        "rpath": rpath,
        "runpath": runpath,
        "rpath_scope": "legacy search path; may affect descendant dependencies" if rpath else None,
        "runpath_scope": "direct dependencies of the object" if runpath else None,
        "both_present": bool(rpath and runpath),
        "precedence_claim": "NOT_INFERRED_WHEN_BOTH_PRESENT",
        "sha256": hashlib.sha256(raw).hexdigest(),
    } and bool(rpath) and bool(runpath)
    return {"ok": ok, "method": "independent DT_RPATH and DT_RUNPATH extraction with bounded interpretation"}
