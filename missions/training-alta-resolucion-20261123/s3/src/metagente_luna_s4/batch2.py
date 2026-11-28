"""Second execution batch. A matched criterion is not a closed C05 gate."""
from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path


def _build_dex_fixture() -> bytes:
    strings = [b"LExample;", b"V", b"run"]
    string_ids_off = 112
    type_ids_off = string_ids_off + 4 * len(strings)
    proto_ids_off = type_ids_off + 4
    method_ids_off = proto_ids_off + 12
    data_off = method_ids_off + 8
    data = bytearray()
    string_offsets = []
    for value in strings:
        string_offsets.append(data_off + len(data))
        data.append(len(value))
        data.extend(value + bytes([0]))
    raw = bytearray(data_off + len(data))
    raw[:8] = bytes.fromhex("6465780a30333500")
    struct.pack_into("<I", raw, 32, len(raw))
    struct.pack_into("<I", raw, 36, 112)
    struct.pack_into("<I", raw, 40, 0x12345678)
    struct.pack_into("<II", raw, 56, len(strings), string_ids_off)
    struct.pack_into("<II", raw, 64, 1, type_ids_off)
    struct.pack_into("<II", raw, 72, 1, proto_ids_off)
    struct.pack_into("<II", raw, 80, 0, 0)
    struct.pack_into("<II", raw, 88, 1, method_ids_off)
    struct.pack_into("<II", raw, 96, 0, 0)
    struct.pack_into("<II", raw, 104, len(data), data_off)
    for index, offset in enumerate(string_offsets):
        struct.pack_into("<I", raw, string_ids_off + index * 4, offset)
    struct.pack_into("<I", raw, type_ids_off, 0)
    struct.pack_into("<III", raw, proto_ids_off, 1, 0, 0)
    struct.pack_into("<HHI", raw, method_ids_off, 0, 0, 2)
    raw[data_off:] = data
    raw[12:32] = hashlib.sha1(raw[32:]).digest()
    struct.pack_into("<I", raw, 8, zlib.adler32(raw[12:]) & 0xFFFFFFFF)
    return bytes(raw)


_DEX_FIXTURE = _build_dex_fixture()
_DEX_HEX = _DEX_FIXTURE.hex()
_DEX_BOUNDARY_FIXTURE = bytearray(_DEX_FIXTURE)
_DEX_BOUNDARY_FIXTURE[4:7] = b"036"
_DEX_BOUNDARY_FIXTURE[12:32] = hashlib.sha1(_DEX_BOUNDARY_FIXTURE[32:]).digest()
struct.pack_into("<I", _DEX_BOUNDARY_FIXTURE, 8, zlib.adler32(_DEX_BOUNDARY_FIXTURE[12:]) & 0xFFFFFFFF)
_DEX_BOUNDARY_HEX = bytes(_DEX_BOUNDARY_FIXTURE).hex()

from metagente_luna_s4.runner import execute

_ENTITIES = "<r>" + "".join(chr(code) for code in (38, 108, 116, 59, 38, 103, 116, 59, 38, 97, 109, 112, 59)) + "</r>"
_ZWJ = "\U0001f468\u200d\U0001f680"
_PDF_FIXTURES = Path(__file__).parents[2] / "fixtures"
_PDF_ENCRYPTED_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0084.pdf").read_bytes().hex()
_PDF_ENCRYPTED_BOUNDARY_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0084-boundary.pdf").read_bytes().hex()
_ELF_SYMBOLS_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0054-0095.elf").read_bytes().hex()
_ELF_SYMBOLS_BOUNDARY_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0095-boundary.elf").read_bytes().hex()
_ELF_STRIPPED_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0057-stripped.elf").read_bytes().hex()
_ELF_STRIPPED_BOUNDARY_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0057-boundary-stripped.elf").read_bytes().hex()
_ELF_ARM_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0060-arm.elf").read_bytes().hex()
_ELF_RPATH_RUNPATH_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0059-rpath-runpath.elf").read_bytes().hex()
_ELF_RPATH_RUNPATH_BOUNDARY_HEX = (_PDF_FIXTURES / "FX-MGL5-INF-0059-boundary-rpath-runpath.elf").read_bytes().hex()
_PE_FIXTURE = (_PDF_FIXTURES / "FX-MGL5-INF-0061-0064-pe64.bin").read_bytes()
_PE_HEX = _PE_FIXTURE.hex()
CASES = [
    {"case_id": "MGL5-INF-0019", "capability_id": "text_units", "arguments": {"text": _ZWJ}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0020", "capability_id": "text_units", "arguments": {"text": "e\u0301"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0021", "capability_id": "crlf_roundtrip", "arguments": {"text": "a\r\nb\r\n"}},
    {"case_id": "MGL5-INF-0022", "capability_id": "crlf_to_lf", "arguments": {"text": "a\r\nb\r\n"}},
    {"case_id": "MGL5-INF-0023", "capability_id": "csv_roundtrip", "arguments": {"rows": [['say "hi"', "a,b"]]}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0024", "capability_id": "csv_newline", "arguments": {"text": '"hello\nworld",1\n'}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0026", "capability_id": "json_text", "arguments": {"text": "ñandú"}},
    {"case_id": "MGL5-INF-0027", "capability_id": "duplicate_keys", "arguments": {"text": '{"a":1,"a":2}'}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0029", "capability_id": "canonical_json", "arguments": {"left": {"b": 1, "a": 2}, "right": {"a": 2, "b": 1}}},
    {"case_id": "MGL5-INF-0030", "capability_id": "xml_expanded", "arguments": {"document": '<a:x xmlns:a="urn:x"><b:x xmlns:b="urn:x" /></a:x>'}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0031", "capability_id": "xml_entities", "arguments": {"document": _ENTITIES}},
    {"case_id": "MGL5-INF-0032", "capability_id": "xml_unbalanced", "arguments": {"document": "<a></b>"}},
    {"case_id": "MGL5-INF-0033", "capability_id": "yaml_types", "arguments": {"text": "name: Luna\nenabled: true\ncount: 3\nitems:\n  - uno\n  - dos\n"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0034", "capability_id": "yaml_ambiguous", "arguments": {"text": "flag: yes\ndate: 2026-01-02\n", "schema_version": "1.1"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0035", "capability_id": "protobuf_old_reader", "arguments": {"wire_hex": "080712036e6577"}, "fixture_provenance": "SYNTHETIC_MINIMAL: field 1 known, field 2 optional and unknown to previous reader"},
    {"case_id": "MGL5-INF-0039", "capability_id": "schema_migrate", "arguments": {"document": {"version": 1, "name": "Luna", "count": 3}}, "fixture_provenance": "SYNTHETIC_MINIMAL: source literals versions 1 and 2"},
    {"case_id": "MGL5-INF-0040", "capability_id": "schema_unknown_field", "arguments": {"record": {"name": "Luna", "version": 2, "extra": "future"}, "known_fields": ["name", "version"]}, "fixture_provenance": "SYNTHETIC_MINIMAL: known fields plus future field"},
    {"case_id": "MGL5-INF-0049", "capability_id": "cbor_roundtrip", "arguments": {"document": {"name": "Luna", "count": 2, "enabled": True, "items": [1, None, False]}}, "fixture_provenance": "SYNTHETIC_MINIMAL: mixed JSON-compatible CBOR map"},
    {"case_id": "MGL5-INF-0036", "capability_id": "framed_record", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0037", "capability_id": "truncated_records", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0038", "capability_id": "oversize_length", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0041", "capability_id": "float32_exactness", "arguments": {"values": [16777216, 16777217, 16777219]}},
    {"case_id": "MGL5-INF-0042", "capability_id": "decimal_text", "arguments": {"text": "0.10"}},
    {"case_id": "MGL5-INF-0043", "capability_id": "three_states", "arguments": {"present": {"b": None, "c": ""}, "absent_key": "a"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0044", "capability_id": "zlib_roundtrip", "arguments": {"payload_hex": "00ff"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0045", "capability_id": "zlib_corrupt", "arguments": {"payload_hex": "00ff"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0046", "capability_id": "base64_bytes", "arguments": {"payload_hex": "0000ff"}},
    {"case_id": "MGL5-INF-0047", "capability_id": "base64_reject", "arguments": {"text": "****"}},
    {"case_id": "MGL5-INF-0050", "capability_id": "manifest_hash", "arguments": {"document": {"name": "luna"}, "altered": {"name": "luna-x"}}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0051", "capability_id": "magic_bytes", "arguments": {"name": "sample.dat", "payload_hex": "89504e470d0a1a0a"}, "fixture_provenance": "SIGNATURE_PREFIX_NOT_A_FULL_PNG"},
    {"case_id": "MGL5-INF-0052", "capability_id": "magic_bytes", "arguments": {"name": "sample.jpg", "payload_hex": "7f454c46020101000000000000000000"}, "fixture_provenance": "ELF64_LE_IDENT_HEADER_PREFIX"},
    {"case_id": "MGL5-INF-0053", "capability_id": "elf_header", "arguments": {"payload_hex": "7f454c4602010100000000000000000002003e000100000000004000000000004000000000000000000000000000000000000000400038000000400000000000"}, "fixture_provenance": "SYNTHETIC_MINIMAL: exact 64-byte ELF64 little-endian EXEC header"},
    {"case_id": "MGL5-INF-0070", "capability_id": "zip_path_safety", "arguments": {"entries": [{"name": "../outside.txt", "data_hex": "736563726574"}, {"name": "inside.txt", "data_hex": "6f6b"}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: source specifies ../outside.txt; companion safe member added to prove containment"},
    {"case_id": "MGL5-INF-0071", "capability_id": "zip_crc", "arguments": {"payload_hex": "4352432d74657374"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: deterministic member bytes; executor mutates data byte only"},
    {"case_id": "MGL5-INF-0072", "capability_id": "zip_duplicates", "arguments": {"names": ["same.txt", "same.txt"], "payloads_hex": ["6f6e65", "74776f"]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: two distinct payloads use the required duplicate member name"},
    {"case_id": "MGL5-INF-0073", "capability_id": "tar_offsets", "arguments": {"entries": [{"name": "a", "data_hex": "61"}, {"name": "b", "data_hex": "62"}, {"name": "c", "data_hex": "6363"}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: three USTAR members, deterministic 512-byte blocks"},
    {"case_id": "MGL5-INF-0074", "capability_id": "tar_truncated", "arguments": {"first_hex": "6669727374", "second_hex": "7365636f6e64", "cut_into_second": 2}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: truncation two bytes into second member payload"},
    {"case_id": "MGL5-INF-0075", "capability_id": "gzip_crc", "arguments": {"payload_hex": "677a69702d637263"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: deterministic payload; executor alters trailer CRC32 only"},
    {"case_id": "MGL5-INF-0078", "capability_id": "sqlite_header", "arguments": {"page_size": 4096}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: generated in-memory SQLite database; header fields read from serialized bytes"},
    {"case_id": "MGL5-INF-0079", "capability_id": "sqlite_integrity", "arguments": {"corrupt": False, "values": ["alpha", "beta"]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: SQLite lab copy generated in memory; negative mutates only the copy header"},
    {"case_id": "MGL5-INF-0085", "capability_id": "wasm_header", "arguments": {"magic_hex": "0061736d", "version": 1}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: WebAssembly magic and version encoded per binary format"},
    {"case_id": "MGL5-INF-0080", "capability_id": "png_chunks", "arguments": {"chunks": [{"type": "IHDR", "data_hex": "00000001000000010802000000"}, {"type": "IDAT", "data_hex": "00"}, {"type": "IEND", "data_hex": ""}], "tamper_index": -1}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: 1x1 RGB PNG chunk sequence; integrity fields generated per PNG chunk CRC rule"},
    {"case_id": "MGL5-INF-0088", "capability_id": "unknown_format", "arguments": {"payload_hex": "4c554e415f554e4b4e4f574e"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: opaque bytes with no recognized registered signature"},
    {"case_id": "MGL5-INF-0089", "capability_id": "block_entropy", "arguments": {"payload_hex": "00000101ffff", "block_size": 2}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: three deterministic mixed-entropy blocks"},
    {"case_id": "MGL5-INF-0090", "capability_id": "binary_diff", "arguments": {"left_hex": "10203040", "right_hex": "10203140"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: fixed-width vectors differ at exactly one byte"},
    {"case_id": "MGL5-INF-0097", "capability_id": "bounded_declared_size", "arguments": {"declared_size": 4096, "payload_hex": "4142"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: declared size exceeds the actual two-byte buffer"},
    {"case_id": "MGL5-INF-0099", "capability_id": "reproducible_structure", "arguments": {"payload_hex": "434f50592d4944454e544943414c"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: identical immutable byte input is analyzed twice"},
    {"case_id": "MGL5-INF-0081", "capability_id": "jpeg_markers", "arguments": {"segments": [{"marker": "DQT", "payload_hex": "00" + "01" * 64}, {"marker": "SOF0", "payload_hex": "080001000101011100"}], "truncate_last": False}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: JPEG SOI, one DQT, one 1x1 SOF0, and EOI marker stream"},
    {"case_id": "MGL5-INF-0091", "capability_id": "partial_recovery", "arguments": {"header_hex": "4c554e41", "payload_hex": "5245434f5645524544", "expected_magic_hex": "4c554e41"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: valid four-byte fixture magic, known body, and explicitly absent trailer"},
    {"case_id": "MGL5-INF-0092", "capability_id": "timestamp_provenance", "arguments": {"metadata_timestamp": 1700000000, "filesystem_timestamp": 1700000100}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: distinct metadata and filesystem epoch values"},
    {"case_id": "MGL5-INF-0093", "capability_id": "dependency_graph", "arguments": {"root": "A", "nodes": ["A", "B", "C", "D"], "edges": [["A", "B"], ["B", "C"], ["C", "D"]]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: three-level directed dependency chain"},
    {"case_id": "MGL5-INF-0094", "capability_id": "protocol_version_diff", "arguments": {"old_fields": [{"name": "id", "width": 8, "offset": 0}, {"name": "count", "width": 16, "offset": 1}], "new_fields": [{"name": "id", "width": 8, "offset": 0}, {"name": "count", "width": 16, "offset": 1}, {"name": "flag", "width": 8, "offset": 3}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: two protocol field layouts; new version appends one field"},
    {"case_id": "MGL5-INF-0096", "capability_id": "section_overlaps", "arguments": {"sections": [{"name": ".text", "offset": 100, "size": 20}, {"name": ".data", "offset": 115, "size": 10}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: two section intervals overlap at byte 115"},
    {"case_id": "MGL5-INF-0098", "capability_id": "nested_zip_tar", "arguments": {"entries": [{"name": "one.txt", "data_hex": "6f6e65"}, {"name": "two.bin", "data_hex": "0001"}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: generated ZIP contains TAR containing two exact file members"},
    {"case_id": "MGL5-INF-0100", "capability_id": "forensic_report", "arguments": {"payload_hex": "41424344", "declared_size": 8, "stored_crc32": 0, "sections": [{"name": ".text", "offset": 0, "size": 3}, {"name": ".data", "offset": 2, "size": 2}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: controlled binary with size mismatch, CRC mismatch, and overlapping section offsets"},
    {"case_id": "MGL5-INF-0076", "capability_id": "seven_zip_list", "arguments": {"entries": [{"name": "one.txt", "data_hex": "6f6e65"}, {"name": "two.bin", "data_hex": "000102"}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: real 7z archive generated with deterministic timestamps and Copy method"},
    {"case_id": "MGL5-INF-0077", "capability_id": "seven_zip_missing_volume", "arguments": {"payload_hex": "00" * 8192, "volume_size": 1024, "missing_part": 2}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: real 7z multipart archive; second volume removed before archive test"},
    {"case_id": "MGL5-INF-0086", "capability_id": "wasm_sections", "arguments": {"sections": [{"section_id": 1, "payload_hex": "01600000"}, {"section_id": 3, "payload_hex": "0100"}], "truncate_index": -1}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: valid type and function sections with ULEB128 lengths"},
    {"case_id": "MGL5-INF-0087", "capability_id": "wasm_type_indices", "arguments": {"type_count": 2, "function_type_indices": [0, 1]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: two declared types referenced by two functions"},
    {"case_id": "MGL5-INF-0082", "capability_id": "pdf_objects", "arguments": {"references": [[1, 0], [2, 0]], "missing_object": 0}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: valid PDF 1.4 catalog/pages objects with exact references"},
    {"case_id": "MGL5-INF-0083", "capability_id": "pdf_xref", "arguments": {"corrupt_object": 2}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: PDF 1.4 cross-reference offset for object 2 displaced by one byte"},
    {"case_id": "MGL5-INF-0084", "capability_id": "pdf_encryption_boundary", "arguments": {"pdf_hex": _PDF_ENCRYPTED_HEX}, "fixture_provenance": "SOURCE_DERIVED_REAL_ENCRYPTION: PDF Standard Security Handler revision 2, generated by scripts/generate_c05_pdf_encryption_fixture.py; SHA-256=3ed2abadc29b409e6b7281acd5cda87b3992e198242f2569f1d1a8768dabf7ab; source test receives no password"},
    {"case_id": "MGL5-INF-0056", "capability_id": "elf_symbol_tables", "arguments": {"payload_hex": _ELF_SYMBOLS_HEX, "require_complete": True, "required_symbols": ["main", "fixture_marker", "exported_value"]}, "fixture_provenance": "SOURCE_DERIVED_ELF64: gcc specimen with exported symbols; SHA-256=73dfd15b920dbc069830e413dfe79bfcc24f9999ceffb3e4da4dec45cf7dbfca"},
    {"case_id": "MGL5-INF-0057", "capability_id": "elf_symbol_tables", "arguments": {"payload_hex": _ELF_STRIPPED_HEX, "require_complete": False}, "fixture_provenance": "SOURCE_DERIVED_STRIPPED_ELF: GNU strip --strip-all; SHA-256=facf8c3cd0a68549a94301f4c6d94f907a44cccb646f4f76b5f01db7bfb77f0f"},
    {"case_id": "MGL5-INF-0095", "capability_id": "elf_symbol_tables", "arguments": {"payload_hex": _ELF_SYMBOLS_HEX, "require_complete": True, "required_symbols": ["fixture_marker"]}, "fixture_provenance": "SOURCE_DERIVED_ELF64: complete .symtab and dynamic .dynsym from frozen ELF specimen; full-vs-dynamic differences retain table provenance"},
    {"case_id": "MGL5-INF-0060", "capability_id": "elf_host_compatibility", "arguments": {"payload_hex": _ELF_ARM_HEX, "native_machine": 62}, "fixture_provenance": "SOURCE_DERIVED_ARCHITECTURE_MISMATCH: valid ELF64 little-endian specimen with e_machine changed to ARM(40), host target x86-64(62)"},
    {"case_id": "MGL5-INF-0054", "capability_id": "elf_section_layout", "arguments": {"payload_hex": _ELF_SYMBOLS_HEX, "include_load_segments": False}, "fixture_provenance": "SOURCE_DERIVED_ELF64_SECTION_TABLE: readelf section inventory from frozen lab executable; offsets independently bounded against exact file length"},
    {"case_id": "MGL5-INF-0055", "capability_id": "elf_section_layout", "arguments": {"payload_hex": _ELF_SYMBOLS_HEX, "include_load_segments": True}, "fixture_provenance": "SOURCE_DERIVED_ELF64_LOAD_MAP: PT_LOAD file/memory extents and associated section names from frozen lab executable"},
    {"case_id": "MGL5-INF-0058", "capability_id": "elf_dynamic_dependencies", "arguments": {"payload_hex": _ELF_SYMBOLS_HEX}, "fixture_provenance": "SOURCE_DERIVED_ELF64_DYNAMIC: frozen compiler-produced specimen; readelf DT_NEEDED and ldd loader resolution only on SHA-256-pinned trusted fixture; program entry never run"},
    {"case_id": "MGL5-INF-0059", "capability_id": "elf_rpath_runpath", "arguments": {"payload_hex": _ELF_RPATH_RUNPATH_HEX}, "fixture_provenance": "SOURCE_DERIVED_ELF64_SEARCH_TAGS: genuine linker RUNPATH plus inert DT_DEBUG slot retyped as DT_RPATH; both dynamic strings validated by independent raw parser"},
    {"case_id": "MGL5-INF-0061", "capability_id": "pe_inspect", "arguments": {"payload_hex": _PE_HEX, "mode": "header"}, "fixture_provenance": "SOURCE_DERIVED_PE64: deterministic handcrafted PE32+ fixture with MZ, bounded e_lfanew and PE signature; structural inspection only"},
    {"case_id": "MGL5-INF-0062", "capability_id": "pe_inspect", "arguments": {"payload_hex": _PE_HEX, "mode": "sections"}, "fixture_provenance": "SOURCE_DERIVED_PE64: fixture contains .text, .data and .rdata with independently reconstructable raw offsets and sizes"},
    {"case_id": "MGL5-INF-0063", "capability_id": "pe_inspect", "arguments": {"payload_hex": _PE_HEX, "mode": "imports"}, "fixture_provenance": "SOURCE_DERIVED_PE64: static KERNEL32.dll ExitProcess import; no image loading or dynamic module observation"},
    {"case_id": "MGL5-INF-0065", "capability_id": "apk_inventory", "arguments": {"entries": [{"name": "AndroidManifest.xml", "data_hex": "3c6d616e69666573742f3e"}, {"name": "resources.arsc", "data_hex": "01020304"}, {"name": "classes.dex", "data_hex": "6465780a30333500"}]}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL: deterministic APK-like ZIP with manifest, resource table, and DEX member; inventory-only/no extraction"},
    {"case_id": "MGL5-INF-0064", "capability_id": "pe_inspect", "arguments": {"payload_hex": _PE_HEX[:0x188 * 2], "mode": "sections"}, "fixture_provenance": "SOURCE_DERIVED_TRUNCATED_PE64: exact cut at first byte of section table; required safe rejection"},


    {"case_id": "MGL5-INF-0066", "capability_id": "apk_signature_verify", "arguments": {"entries": [{"name": "AndroidManifest.xml", "data_hex": "3c6d616e69666573742f3e"}, {"name": "resources.arsc", "data_hex": "01020304"}, {"name": "classes.dex", "data_hex": "6465780a30333500"}], "signature_mode": "valid"}, "fixture_provenance": "SOURCE_DERIVED_MINIMAL_TEST_APK: fixture-only HMAC-SHA256 signature envelope; explicitly not Android APK signing schemes v1/v2/v3/v4; distinguishes valid/invalid/absent without external tools"},
    {"case_id": "MGL5-INF-0067", "capability_id": "dex_header", "arguments": {"payload_hex": _DEX_HEX}, "fixture_provenance": "SOURCE_DERIVED_DEX035: deterministic minimal DEX 035 fixture; header fields, SHA-1 signature and Adler-32 checksum generated and frozen by content hash"},
    {"case_id": "MGL5-INF-0068", "capability_id": "dex_tables", "arguments": {"payload_hex": _DEX_HEX}, "fixture_provenance": "SOURCE_DERIVED_DEX035: minimal string/type/proto/method tables with valid cross-indices; deterministic binary fixture"},

    {"case_id": "MGL5-INF-0101", "capability_id": "array_sum", "arguments": {"values": [-3, 0, 7, 11], "empty": []}},
    {"case_id": "MGL5-INF-0102", "capability_id": "array_minmax", "arguments": {"values": [-8, 4, 4, 19, 0]}},
    {"case_id": "MGL5-INF-0151", "capability_id": "tokenize", "arguments": {"text": "let x = 42 + 3;"}},
    {"case_id": "MGL5-INF-0251", "capability_id": "ipv4_check", "arguments": {"addresses": ["192.0.2.17", "192.0.2.256"]}},
    {"case_id": "MGL5-INF-0601", "capability_id": "binary_float_gap", "arguments": {"left": 0.1, "right": 0.2, "target": 0.3}},
]


def run_case(spec: dict) -> dict:
    runs = [execute(spec["capability_id"], spec["arguments"], spec["case_id"]) for _ in range(3)]
    observed = [run["observed"] for run in runs]
    ok = all(run["execution_status"] == "EXECUTED" for run in runs) and all(item == observed[0] for item in observed)
    return {
        "case_id": spec["case_id"],
        "capability_id": spec["capability_id"],
        "fixture_provenance": spec.get("fixture_provenance", "PROGRAM_LITERAL"),
        "repetitions": [run["run_id"] for run in runs],
        "observed": observed[0],
        "oracle_method": None if not runs[0]["oracle_result"] else runs[0]["oracle_result"].get("method"),
        "stderr": runs[0]["stderr"],
        "exit_code": [run["exit_code"] for run in runs],
        "execution_status": "CRITERION_MET" if ok else "FAIL",
        "protocol_gap": "separate negative and boundary runs were not executed for this case",
        "backend": "LOCAL_TEST_ONLY",
        "independent_review": "NOT_AVAILABLE",
        "teo_status": "NOT_APPLICABLE",
        "c05_gate": "NOT_PASSED",
    }


def run_all() -> list[dict]:
    return [run_case(spec) for spec in CASES]
