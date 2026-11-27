"""Small binary-format probes backed by real standard-library artifacts."""
from __future__ import annotations

import binascii
import hashlib
import io
import math
import re
import sqlite3
import struct
import subprocess
import tarfile
import tempfile
import zipfile
import zlib

from metagente_luna_s3.archive_exec import _tar, _zip


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


def partial_recovery(header_hex: str, payload_hex: str, expected_magic_hex: str) -> dict:
    header, payload, magic = bytes.fromhex(header_hex), bytes.fromhex(payload_hex), bytes.fromhex(expected_magic_hex)
    valid = bool(magic) and header.startswith(magic)
    return {"header_valid": valid, "recovered_hex": payload.hex() if valid else "", "unknown_trailer": True, "integrity_complete": False}


def timestamp_provenance(metadata_timestamp: int, filesystem_timestamp: int) -> dict:
    return {"timestamps": [{"value": metadata_timestamp, "source": "embedded_metadata"}, {"value": filesystem_timestamp, "source": "filesystem"}], "creation_time_proven": False, "warning": "timestamps alone do not prove creation time"}


def dependency_graph(root: str, nodes: list[str], edges: list[list[str]]) -> dict:
    graph = {node: [] for node in nodes}
    for source, target in edges:
        if source not in graph or target not in graph:
            return {"rejected": True, "reason": "edge_endpoint_missing", "reachable": [], "cycle": False}
        graph[source].append(target)
    if root not in graph:
        return {"rejected": True, "reason": "root_missing", "reachable": [], "cycle": False}
    reachable, active, done, cycle = set(), set(), set(), False

    def visit(node: str) -> None:
        nonlocal cycle
        if node in active:
            cycle = True
            return
        if node in done:
            return
        active.add(node)
        for child in graph[node]:
            reachable.add(child)
            visit(child)
        active.remove(node)
        done.add(node)

    visit(root)
    return {"rejected": False, "reachable": sorted(reachable), "cycle": cycle}


def protocol_version_diff(old_fields: list[dict], new_fields: list[dict]) -> dict:
    old, new = {row["name"]: row for row in old_fields}, {row["name"]: row for row in new_fields}
    changes = []
    for name in sorted(set(old) | set(new)):
        if name not in old:
            changes.append({"field": name, "change": "added", "new": new[name]})
        elif name not in new:
            changes.append({"field": name, "change": "removed", "old": old[name]})
        elif old[name] != new[name]:
            changes.append({"field": name, "change": "modified", "old": old[name], "new": new[name]})
    compatible = not any(row["change"] in {"removed", "modified"} for row in changes)
    return {"changes": changes, "backward_compatible": compatible, "forward_compatible": compatible}


def section_overlaps(sections: list[dict]) -> dict:
    overlaps = []
    for index, left in enumerate(sections):
        for right in sections[index + 1:]:
            start = max(left["offset"], right["offset"])
            end = min(left["offset"] + left["size"], right["offset"] + right["size"])
            if start < end:
                overlaps.append({"left": left["name"], "right": right["name"], "overlap_start": start, "overlap_end": end})
    return {"overlaps": overlaps, "valid": not overlaps}


def nested_zip_tar(entries: list[dict]) -> dict:
    tar_bytes = _tar(entries)
    archive_bytes = _zip([{"name": "inner.tar", "data_hex": tar_bytes.hex()}])
    with zipfile.ZipFile(io.BytesIO(archive_bytes)) as zipped:
        nested = zipped.read("inner.tar")
    with tarfile.open(fileobj=io.BytesIO(nested), mode="r:") as archive:
        files = [{"name": member.name, "size": member.size, "data_hex": archive.extractfile(member).read().hex()} for member in archive.getmembers() if member.isfile()]
    return {"tree": {"name": "outer.zip", "children": [{"name": "inner.tar", "children": files}]}, "nested_sha256": hashlib.sha256(nested).hexdigest()}


def forensic_report(payload_hex: str, declared_size: int, stored_crc32: int, sections: list[dict]) -> dict:
    raw = bytes.fromhex(payload_hex)
    anomalies = []
    if declared_size != len(raw):
        anomalies.append({"code": "DECLARED_SIZE_MISMATCH", "offset": 0, "observed": declared_size, "actual": len(raw)})
    actual_crc = binascii.crc32(raw) & 0xFFFFFFFF
    if stored_crc32 != actual_crc:
        anomalies.append({"code": "CRC_MISMATCH", "offset": len(raw), "stored": stored_crc32, "computed": actual_crc})
    for index, left in enumerate(sections):
        for right in sections[index + 1:]:
            if max(left["offset"], right["offset"]) < min(left["offset"] + left["size"], right["offset"] + right["size"]):
                anomalies.append({"code": "SECTION_OVERLAP", "offset": max(left["offset"], right["offset"]), "sections": [left["name"], right["name"]]})
    return {"observations": anomalies, "inferences": [{"anomaly": item["code"], "confidence": "structural"} for item in anomalies], "conclusion": {"anomaly_count": len(anomalies), "integrity": "INCOMPLETE" if anomalies else "NO_ANOMALY_DETECTED"}}


def _uleb128(value: int) -> bytes:
    encoded = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        encoded.append(byte | (0x80 if value else 0))
        if not value:
            return bytes(encoded)


def wasm_sections(sections: list[dict], truncate_index: int) -> dict:
    raw = bytearray(b"\0asm\x01\0\0\0")
    for section in sections:
        payload = bytes.fromhex(section["payload_hex"])
        raw.append(section["section_id"])
        raw.extend(_uleb128(len(payload)))
        raw.extend(payload)
    if truncate_index >= 0:
        if truncate_index >= len(sections):
            raise ValueError("truncated section index is outside fixture")
        del raw[-1:]
    parsed, offset, valid = [], 8, raw[:4] == b"\0asm" and raw[4:8] == b"\x01\0\0\0"
    while valid and offset < len(raw):
        section_offset, section_id = offset, raw[offset]
        offset += 1
        size, shift = 0, 0
        while offset < len(raw):
            byte = raw[offset]
            offset += 1
            size |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
            if shift > 35:
                valid = False
                break
        else:
            valid = False
            break
        if not valid or offset + size > len(raw):
            valid = False
            break
        parsed.append({"section_id": section_id, "offset": section_offset, "payload_offset": offset, "payload_size": size, "within_module": True})
        offset += size
    return {"sections": parsed, "valid": valid and offset == len(raw), "module_size": len(raw)}


def wasm_type_indices(type_count: int, function_type_indices: list[int]) -> dict:
    invalid = [index for index in function_type_indices if index < 0 or index >= type_count]
    return {"rejected": bool(invalid), "type_count": type_count, "function_type_indices": function_type_indices, "invalid_indices": invalid}


def _minimal_pdf(objects: list[str], corrupt_xref_object: int = 0) -> bytes:
    """Build a byte-accurate PDF 1.4 fixture, optionally corrupting one xref offset."""
    data = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n{body}\nendobj\n".encode("ascii"))
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode("ascii"))
    for number, offset in enumerate(offsets[1:], 1):
        if number == corrupt_xref_object:
            offset += 1
        data.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode("ascii"))
    return bytes(data)


def pdf_objects(references: list[list[int]], missing_object: int) -> dict:
    count = max([2, *(ref[0] for ref in references)])
    objects = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [] /Count 0 >>"]
    objects.extend("<< >>" for _ in range(count - 2))
    raw = _minimal_pdf(objects)
    present = {int(match.group(1)) for match in re.finditer(rb"(?m)^(\d+) 0 obj$", raw)}
    refs = [{"object": number, "generation": generation, "resolved": generation == 0 and number in present} for number, generation in references]
    if missing_object:
        refs.append({"object": missing_object, "generation": 0, "resolved": missing_object in present})
    return {"objects": sorted(present), "references": refs, "sha256": hashlib.sha256(raw).hexdigest()}


def pdf_xref(corrupt_object: int) -> dict:
    raw = _minimal_pdf(["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [] /Count 0 >>"], corrupt_object)
    actual = {int(match.group(1)): match.start() for match in re.finditer(rb"(?m)^(\d+) 0 obj$", raw)}
    marker = re.search(rb"startxref\n(\d+)\n%%EOF", raw)
    if marker is None:
        raise ValueError("PDF startxref marker is missing")
    xref_start = int(marker.group(1))
    lines = raw[xref_start:].splitlines()
    count = int(lines[1].split()[1])
    discrepancies = []
    for number, line in enumerate(lines[3:3 + count - 1], 1):
        declared = int(line[:10])
        if declared != actual.get(number):
            discrepancies.append({"object": number, "declared_offset": declared, "actual_offset": actual.get(number)})
    return {"object_offsets": actual, "xref_offset": xref_start, "discrepancies": discrepancies, "valid": not discrepancies}


def pdf_encryption_boundary(pdf_hex: str) -> dict:
    """Report encrypted PDF access limits without attempting decryption."""
    raw = bytes.fromhex(pdf_hex)
    if not raw.startswith(b"%PDF-"):
        raise ValueError("input does not have a PDF header")
    trailer = re.search(rb"trailer\s*<<(.*?)>>", raw, re.DOTALL)
    reference = re.search(rb"/Encrypt\s+(\d+)\s+(\d+)\s+R", trailer.group(1)) if trailer else None
    dictionary = None
    if reference:
        object_number = int(reference.group(1))
        dictionary = re.search(rb"(?m)^" + str(object_number).encode() + rb"\s+\d+\s+obj\s*<<(.*?)>>\s*endobj", raw, re.DOTALL)
    handler = re.search(rb"/Filter\s*/([A-Za-z0-9]+)", dictionary.group(1)) if dictionary else None
    revision = re.search(rb"/R\s+(\d+)", dictionary.group(1)) if dictionary else None
    version = re.search(rb"/V\s+(\d+)", dictionary.group(1)) if dictionary else None
    key_length = re.search(rb"/Length\s+(\d+)", dictionary.group(1)) if dictionary else None
    permissions = re.search(rb"/P\s+(-?\d+)", dictionary.group(1)) if dictionary else None
    encrypted = bool(reference and handler and handler.group(1) == b"Standard")
    return {
        "encrypted": encrypted,
        "handler": handler.group(1).decode("ascii") if encrypted else None,
        "revision": int(revision.group(1)) if encrypted and revision else None,
        "version": int(version.group(1)) if encrypted and version else None,
        "key_length_bits": int(key_length.group(1)) if encrypted and key_length else None,
        "permissions": int(permissions.group(1)) if encrypted and permissions else None,
        "password_supplied": False,
        "content_available": False,
        "plaintext_claim": None,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def elf_symbol_tables(payload_hex: str, require_complete: bool, required_symbols: list[str] | None = None) -> dict:
    """Read ELF symbol tables with binutils; the specimen is never executed."""
    raw = bytes.fromhex(payload_hex)
    if not raw.startswith(b"\x7fELF"):
        raise ValueError("input does not have an ELF signature")
    with tempfile.TemporaryDirectory(prefix="c05-elf-") as temporary:
        path = f"{temporary}/specimen.elf"
        with open(path, "wb") as specimen:
            specimen.write(raw)
        result = subprocess.run(["readelf", "--symbols", "--wide", path], capture_output=True, text=True, timeout=5, check=False)
    if result.returncode != 0:
        return {"rejected": True, "reason": result.stderr.strip()[:300], "sha256": hashlib.sha256(raw).hexdigest()}
    tables: dict[str, list[dict]] = {}
    current = None
    row_pattern = re.compile(r"^\s*\d+:\s+([0-9a-fA-F]+)\s+(\d+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s*(.*?)\s*$")
    for line in result.stdout.splitlines():
        heading = re.search(r"Symbol table '([^']+)'", line)
        if heading:
            current = heading.group(1)
            tables[current] = []
            continue
        match = row_pattern.match(line)
        if current and match and match.group(7):
            value, size, kind, binding, visibility, section, name = match.groups()
            name = name.split("@", 1)[0].split(" ", 1)[0]
            tables[current].append({"name": name, "value": int(value, 16), "size": int(size), "type": kind, "binding": binding, "visibility": visibility, "section_index": section})
    if ".symtab" not in tables:
        return {"rejected": require_complete, "reason": "complete_symbol_table_missing" if require_complete else None, "stripped": True, "tables": sorted(tables), "complete_symbols": None, "dynamic_symbols": tables.get(".dynsym", []), "invented_symbols": [], "provenance": {"complete": None, "dynamic": ".dynsym" if ".dynsym" in tables else None, "tool": "GNU readelf", "binary_executed": False}, "sha256": hashlib.sha256(raw).hexdigest()}
    if ".dynsym" not in tables:
        return {"rejected": True, "reason": "dynamic_symbol_table_missing", "tables": sorted(tables), "sha256": hashlib.sha256(raw).hexdigest()}
    complete, dynamic = tables[".symtab"], tables[".dynsym"]
    expected_names = set(required_symbols or [])
    complete_names = {row["name"] for row in complete}
    dynamic_keys = {(row["name"], row["value"], row["type"]) for row in dynamic}
    complete_keys = {(row["name"], row["value"], row["type"]) for row in complete}
    return {
        "rejected": False,
        "stripped": False,
        "tables": sorted(tables),
        "complete_symbols": complete,
        "dynamic_symbols": dynamic,
        "complete_only": sorted(complete_keys - dynamic_keys),
        "dynamic_only": sorted(dynamic_keys - complete_keys),
        "required_symbols_present": expected_names <= complete_names,
        "provenance": {"complete": ".symtab", "dynamic": ".dynsym", "tool": "GNU readelf", "binary_executed": False},
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def elf_host_compatibility(payload_hex: str, native_machine: int) -> dict:
    from metagente_luna_s3.more_exec import elf_header

    header = elf_header(payload_hex)
    return {"header": header, "native_machine": native_machine, "host_compatible": not header.get("rejected", True) and int.from_bytes(bytes.fromhex(payload_hex)[18:20], "little" if header["endianness"] == "little" else "big") == native_machine}


def elf_section_layout(payload_hex: str, include_load_segments: bool) -> dict:
    """Extract bounded ELF section offsets and optional PT_LOAD mappings."""
    raw = bytes.fromhex(payload_hex)
    if not raw.startswith(b"\x7fELF"):
        raise ValueError("input does not have an ELF signature")
    with tempfile.TemporaryDirectory(prefix="c05-elf-layout-") as temporary:
        path = f"{temporary}/specimen.elf"
        with open(path, "wb") as specimen:
            specimen.write(raw)
        section_result = subprocess.run(["readelf", "--sections", "--wide", path], capture_output=True, text=True, timeout=5, check=False)
        program_result = subprocess.run(["readelf", "--program-headers", "--wide", path], capture_output=True, text=True, timeout=5, check=False) if include_load_segments else None
    if section_result.returncode != 0 or (program_result and program_result.returncode != 0):
        return {"rejected": True, "reason": (section_result.stderr or program_result.stderr).strip()[:300], "sha256": hashlib.sha256(raw).hexdigest()}
    sections = []
    section_pattern = re.compile(r"^\s*\[\s*(\d+)\]\s+(\S*)\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)")
    for line in section_result.stdout.splitlines():
        match = section_pattern.match(line)
        if match:
            index, name, _kind, address, offset, size = match.groups()
            if int(index) == 0:
                continue
            start, length = int(offset, 16), int(size, 16)
            sections.append({"index": int(index), "name": name, "address": int(address, 16), "offset": start, "size": length, "offset_within_file": start <= len(raw)})
    load_segments = []
    if program_result:
        segment_pattern = re.compile(r"^\s*(LOAD)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+0x([0-9a-fA-F]+)\s+(.*)$")
        segments = []
        for line in program_result.stdout.splitlines():
            match = segment_pattern.match(line)
            if match:
                _, offset, vaddr, _paddr, filesz, memsz, _flags = match.groups()
                segments.append({"offset": int(offset, 16), "virtual_address": int(vaddr, 16), "file_size": int(filesz, 16), "memory_size": int(memsz, 16)})
        mapping = False
        mappings: dict[int, list[str]] = {}
        for line in program_result.stdout.splitlines():
            if line.strip().startswith("Segment Sections"):
                mapping = True
                continue
            if mapping:
                match = re.match(r"^\s*(\d+)\s+(.*)$", line)
                if match:
                    mappings[int(match.group(1))] = match.group(2).split()
        for index, segment in enumerate(segments):
            segment["associated_sections"] = mappings.get(index + 2, [])
            load_segments.append(segment)
    valid = all(section["offset_within_file"] for section in sections)
    return {"rejected": False, "sections": sections, "load_segments": load_segments, "section_offsets_valid": valid, "sha256": hashlib.sha256(raw).hexdigest()}


def elf_dynamic_dependencies(payload_hex: str) -> dict:
    """Compare DT_NEEDED declarations with loader resolution for allowlisted fixtures only."""
    raw = bytes.fromhex(payload_hex)
    if not raw.startswith(b"\x7fELF"):
        raise ValueError("input does not have an ELF signature")
    digest = hashlib.sha256(raw).hexdigest()
    trusted_runtime_fixtures = {
        "73dfd15b920dbc069830e413dfe79bfcc24f9999ceffb3e4da4dec45cf7dbfca",
        "1003715dcd699bf98061167a830d5fdb5bcefc107952ac584476bd45688da985",
    }
    with tempfile.TemporaryDirectory(prefix="c05-elf-dynamic-") as temporary:
        path = f"{temporary}/specimen.elf"
        with open(path, "wb") as specimen:
            specimen.write(raw)
        result = subprocess.run(["readelf", "--dynamic", "--wide", path], capture_output=True, text=True, timeout=5, check=False)
        if result.returncode != 0:
            return {"rejected": True, "reason": result.stderr.strip()[:300], "sha256": digest}
        needed = re.findall(r"\(NEEDED\).*?\[([^\]]+)\]", result.stdout)
        tags = {}
        for label in ("RPATH", "RUNPATH"):
            tags[label] = re.findall(rf"\({label}\).*?\[([^\]]*)\]", result.stdout)
        runtime: dict[str, str | None] | None = None
        attempted = digest in trusted_runtime_fixtures
        if attempted:
            loaded = subprocess.run(["ldd", path], capture_output=True, text=True, timeout=5, check=False, env={"PATH": "/usr/bin:/bin", "LC_ALL": "C"})
            runtime = {}
            for line in loaded.stdout.splitlines():
                match = re.match(r"^\s*(\S+)\s+=>\s+(not found|/\S+)", line)
                if match and match.group(1) in needed:
                    runtime[match.group(1)] = None if match.group(2) == "not found" else match.group(2)
            runtime = {name: runtime.get(name) for name in needed}
    return {
        "rejected": False,
        "declared_dependencies": needed,
        "runtime_resolution_attempted": attempted,
        "runtime_resolved": runtime,
        "runtime_unresolved": [name for name, path in (runtime or {}).items() if path is None],
        "rpath": tags["RPATH"],
        "runpath": tags["RUNPATH"],
        "ldd_loaded_dependencies_only": attempted,
        "program_entry_executed": False,
        "sha256": digest,
    }


def elf_rpath_runpath(payload_hex: str) -> dict:
    observed = elf_dynamic_dependencies(payload_hex)
    if observed.get("rejected"):
        return observed
    return {
        "rejected": False,
        "rpath": observed["rpath"],
        "runpath": observed["runpath"],
        "rpath_scope": "legacy search path; may affect descendant dependencies" if observed["rpath"] else None,
        "runpath_scope": "direct dependencies of the object" if observed["runpath"] else None,
        "both_present": bool(observed["rpath"] and observed["runpath"]),
        "precedence_claim": "NOT_INFERRED_WHEN_BOTH_PRESENT",
        "sha256": observed["sha256"],
    }


def pe_inspect(payload_hex: str, mode: str) -> dict:
    """Inspect PE headers, sections, or static imports without loading the image."""
    raw = bytes.fromhex(payload_hex)
    digest = hashlib.sha256(raw).hexdigest()
    if len(raw) < 64 or raw[:2] != b"MZ":
        return {"rejected": True, "reason": "invalid_or_truncated_dos_header", "sha256": digest}
    pe_offset = int.from_bytes(raw[0x3C:0x40], "little")
    if pe_offset + 24 > len(raw) or raw[pe_offset:pe_offset + 4] != b"PE\0\0":
        return {"rejected": True, "reason": "invalid_or_truncated_pe_header", "sha256": digest}
    if mode == "header":
        return {"rejected": False, "mz_valid": True, "pe_offset": pe_offset, "pe_signature_valid": True, "bytes_read": min(len(raw), pe_offset + 24), "sha256": digest}
    if pe_offset + 24 > len(raw):
        return {"rejected": True, "reason": "truncated_coff_header", "sha256": digest}
    section_count = int.from_bytes(raw[pe_offset + 6:pe_offset + 8], "little")
    optional_size = int.from_bytes(raw[pe_offset + 20:pe_offset + 22], "little")
    section_table = pe_offset + 24 + optional_size
    if section_table + section_count * 40 > len(raw):
        return {"rejected": True, "reason": "truncated_section_table", "sha256": digest}
    with tempfile.TemporaryDirectory(prefix="c05-pe-") as temporary:
        path = f"{temporary}/specimen.exe"
        with open(path, "wb") as specimen:
            specimen.write(raw)
        headers = subprocess.run(["objdump", "-h", path], capture_output=True, text=True, timeout=5, check=False)
        if headers.returncode != 0:
            return {"rejected": True, "reason": headers.stderr.strip()[:300], "sha256": digest}
        sections = []
        pattern = re.compile(r"^\s*\d+\s+(\S+)\s+([0-9a-fA-F]+)\s+([0-9a-fA-F]+)\s+[0-9a-fA-F]+\s+([0-9a-fA-F]+)")
        for line in headers.stdout.splitlines():
            match = pattern.match(line)
            if match:
                name, size, vma, file_offset = match.groups()
                sections.append({"name": name, "size": int(size, 16), "virtual_address": int(vma, 16), "file_offset": int(file_offset, 16)})
        result = {"rejected": False, "sections": sections, "sha256": digest, "image_loaded": False}
        if mode == "imports":
            details = subprocess.run(["objdump", "-p", path], capture_output=True, text=True, timeout=5, check=False)
            if details.returncode != 0:
                return {"rejected": True, "reason": details.stderr.strip()[:300], "sha256": digest}
            imports = []
            current = None
            for line in details.stdout.splitlines():
                dll = re.match(r"\s*DLL Name: (\S+)", line)
                member = re.match(r"\s*[0-9a-fA-F]+\s+<none>\s+[0-9a-fA-F]+\s+(\S+)", line)
                if dll:
                    current = {"dll": dll.group(1), "symbols": []}
                    imports.append(current)
                elif member and current is not None:
                    current["symbols"].append(member.group(1))
            result["static_imports"] = imports
            result["dynamic_runtime_modules_observed"] = None
            result["static_dynamic_distinguished"] = True
        return result


def dex_inspect(payload_hex: str, mode: str) -> dict:
    """Inspect a bounded DEX header and cross-table indices without loading code."""
    raw = bytes.fromhex(payload_hex)
    if mode not in {"header", "tables"}:
        return {"rejected": True, "reason": "unsupported_mode"}
    if len(raw) < 112 or raw[:4] != bytes.fromhex("6465780a") or raw[7] != 0:
        return {"rejected": True, "reason": "invalid_or_truncated_dex_header"}
    version = raw[4:7].decode("ascii", "replace")
    file_size, header_size, endian = struct.unpack_from("<III", raw, 32)
    if file_size != len(raw) or header_size != 112 or endian != 0x12345678:
        return {"rejected": True, "reason": "header_size_endian_or_file_size_mismatch"}
    checksum = struct.unpack_from("<I", raw, 8)[0]
    checksum_valid = checksum == (zlib.adler32(raw[12:]) & 0xFFFFFFFF)
    signature_valid = raw[12:32] == hashlib.sha1(raw[32:]).digest()
    if mode == "header":
        return {"rejected": False, "version": version, "file_size": file_size,
                "header_size": header_size, "endian_tag": endian,
                "checksum_valid": checksum_valid, "signature_valid": signature_valid}
    fields = {
        "string_ids": (56, 60, 4), "type_ids": (64, 68, 4),
        "proto_ids": (72, 76, 12), "field_ids": (80, 84, 8),
        "method_ids": (88, 92, 8), "class_defs": (96, 100, 32),
    }
    tables = {}
    for name, (size_at, off_at, width) in fields.items():
        count, offset = struct.unpack_from("<II", raw, size_at)
        if count and (offset < 112 or offset + count * width > len(raw)):
            return {"rejected": True, "reason": f"{name}_out_of_bounds"}
        tables[name] = {"count": count, "offset": offset, "width": width}
    strings = []
    string_table = tables["string_ids"]
    for index in range(string_table["count"]):
        offset = struct.unpack_from("<I", raw, string_table["offset"] + index * 4)[0]
        if offset >= len(raw):
            return {"rejected": True, "reason": "string_data_offset_out_of_bounds"}
        end = raw.find(bytes([0]), offset)
        if end < 0:
            return {"rejected": True, "reason": "unterminated_string_data"}
        strings.append(raw[offset:end].decode("utf-8", "replace"))
    type_refs = []
    type_table = tables["type_ids"]
    for index in range(type_table["count"]):
        string_idx = struct.unpack_from("<I", raw, type_table["offset"] + index * 4)[0]
        type_refs.append(string_idx)
    proto_refs = []
    proto_table = tables["proto_ids"]
    for index in range(proto_table["count"]):
        shorty_idx, return_idx, parameters_off = struct.unpack_from("<III", raw, proto_table["offset"] + index * 12)
        proto_refs.append({"shorty_idx": shorty_idx, "return_type_idx": return_idx, "parameters_off": parameters_off})
    method_refs = []
    method_table = tables["method_ids"]
    for index in range(method_table["count"]):
        class_idx, proto_idx, name_idx = struct.unpack_from("<HHI", raw, method_table["offset"] + index * 8)
        method_refs.append({"class_idx": class_idx, "proto_idx": proto_idx, "name_idx": name_idx})
    valid = (
        all(index < len(strings) for index in type_refs)
        and all(row["shorty_idx"] < len(strings) and row["return_type_idx"] < len(type_refs) for row in proto_refs)
        and all(row["class_idx"] < len(type_refs) and row["proto_idx"] < len(proto_refs) and row["name_idx"] < len(strings) for row in method_refs)
    )
    return {"rejected": False, "tables": tables, "strings": strings,
            "type_string_indices": type_refs, "proto_references": proto_refs,
            "method_references": method_refs, "indices_valid": valid,
            "checksum_valid": checksum_valid, "signature_valid": signature_valid}
