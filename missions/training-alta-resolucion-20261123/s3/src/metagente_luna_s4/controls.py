"""Source-bound negative and boundary inputs for authored executable cases."""
from __future__ import annotations

from metagente_luna_s4.batch2 import CASES as SECOND
from metagente_luna_s4.batch3 import CASES as THIRD
from metagente_luna_s4.batch4 import CASES as FOURTH
from metagente_luna_s4.batch5 import CASES as FIFTH
from metagente_luna_s4.batch6 import CASES as SIXTH
from metagente_luna_s4.d01_batch import CASES as FIRST
from metagente_luna_s4.runner import execute

CASES = FIRST + SECOND + THIRD + FOURTH + FIFTH + SIXTH


CONTROLS: dict[str, dict] = {}


def _add(case_id: str, kind: str, capability: str, arguments: dict, expect: str) -> None:
    CONTROLS.setdefault(case_id, {})[kind] = {"capability_id": capability, "arguments": arguments, "expect": expect}


def _build() -> None:
    if CONTROLS:
        return
    text = "utf8_roundtrip"
    _add("MGL5-INF-0001", "negative", text, {"text": "Luna-2025"}, "different-text")
    _add("MGL5-INF-0070", "negative", "zip_path_safety", {"entries": [{"name": "../../escape", "data_hex": "78"}]}, "zip-traversal-blocked")
    _add("MGL5-INF-0070", "boundary", "zip_path_safety", {"entries": [{"name": "inside.txt", "data_hex": ""}]}, "zip-safe-empty")
    _add("MGL5-INF-0071", "negative", "zip_crc", {"payload_hex": "0102"}, "zip-corrupt-crc-detected")
    _add("MGL5-INF-0071", "boundary", "zip_crc", {"payload_hex": "00"}, "zip-minimum-member-crc-detected")
    _add("MGL5-INF-0072", "negative", "zip_duplicates", {"names": ["x", "x"], "payloads_hex": ["61", "62"]}, "zip-duplicate-content-preserved")
    _add("MGL5-INF-0072", "boundary", "zip_duplicates", {"names": ["only"], "payloads_hex": [""]}, "zip-single-entry-preserved")
    _add("MGL5-INF-0073", "negative", "tar_offsets", {"entries": [{"name": "a", "data_hex": ""}, {"name": "b", "data_hex": "00"}, {"name": "c", "data_hex": ""}]}, "tar-empty-block-boundaries")
    _add("MGL5-INF-0073", "boundary", "tar_offsets", {"entries": [{"name": "a", "data_hex": "61"}, {"name": "b", "data_hex": "62"}, {"name": "c", "data_hex": "63"}]}, "tar-one-byte-block-boundaries")
    _add("MGL5-INF-0074", "negative", "tar_truncated", {"first_hex": "61", "second_hex": "626364", "cut_into_second": 0}, "tar-second-header-only-incomplete")
    _add("MGL5-INF-0074", "boundary", "tar_truncated", {"first_hex": "61", "second_hex": "62", "cut_into_second": 0}, "tar-second-empty-prefix-incomplete")
    _add("MGL5-INF-0075", "negative", "gzip_crc", {"payload_hex": "00"}, "gzip-crc-mismatch-detected")
    _add("MGL5-INF-0075", "boundary", "gzip_crc", {"payload_hex": ""}, "gzip-empty-crc-mismatch-detected")
    _add("MGL5-INF-0078", "negative", "sqlite_header", {"page_size": 512}, "sqlite-minimum-page-size")
    _add("MGL5-INF-0078", "boundary", "sqlite_header", {"page_size": 65536}, "sqlite-maximum-page-size")
    _add("MGL5-INF-0079", "negative", "sqlite_integrity", {"corrupt": True, "values": ["alpha", "beta"]}, "sqlite-corruption-reported")
    _add("MGL5-INF-0079", "boundary", "sqlite_integrity", {"corrupt": False, "values": []}, "sqlite-empty-integrity-ok")
    _add("MGL5-INF-0085", "negative", "wasm_header", {"magic_hex": "0161736d", "version": 1}, "wasm-invalid-magic-rejected")
    _add("MGL5-INF-0085", "boundary", "wasm_header", {"magic_hex": "0061736d", "version": 0}, "wasm-version-zero-rejected")
    _add("MGL5-INF-0080", "negative", "png_chunks", {"chunks": [{"type": "IHDR", "data_hex": "00000001000000010802000000"}, {"type": "IDAT", "data_hex": "00"}, {"type": "IEND", "data_hex": ""}], "tamper_index": 1}, "png-crc-mismatch-located")
    _add("MGL5-INF-0080", "boundary", "png_chunks", {"chunks": [{"type": "IHDR", "data_hex": "00000001000000010802000000"}, {"type": "IDAT", "data_hex": ""}, {"type": "IEND", "data_hex": ""}], "tamper_index": -1}, "png-empty-idat-crc-valid")
    _add("MGL5-INF-0088", "negative", "unknown_format", {"payload_hex": "89504e470d0a1a0a"}, "known-signature-is-not-unknown")
    _add("MGL5-INF-0088", "boundary", "unknown_format", {"payload_hex": "00"}, "unknown-single-byte")
    _add("MGL5-INF-0089", "negative", "block_entropy", {"payload_hex": "00000000", "block_size": 2}, "zero-entropy-blocks")
    _add("MGL5-INF-0089", "boundary", "block_entropy", {"payload_hex": "ff", "block_size": 1}, "single-byte-entropy-boundary")
    _add("MGL5-INF-0090", "negative", "binary_diff", {"left_hex": "aabb", "right_hex": "aabb"}, "identical-binaries-no-diff")
    _add("MGL5-INF-0090", "boundary", "binary_diff", {"left_hex": "00", "right_hex": "01"}, "single-byte-offset-zero-diff")
    _add("MGL5-INF-0097", "negative", "bounded_declared_size", {"declared_size": 3, "payload_hex": "00"}, "oversized-declaration-rejected")
    _add("MGL5-INF-0097", "boundary", "bounded_declared_size", {"declared_size": 0, "payload_hex": ""}, "zero-size-boundary")
    _add("MGL5-INF-0099", "negative", "reproducible_structure", {"payload_hex": "00ff"}, "reproducibility-with-different-input")
    _add("MGL5-INF-0099", "boundary", "reproducible_structure", {"payload_hex": ""}, "empty-input-reproducibility")
    _add("MGL5-INF-0081", "negative", "jpeg_markers", {"segments": [{"marker": "DQT", "payload_hex": "00" + "01" * 64}, {"marker": "SOF0", "payload_hex": "080001000101011100"}], "truncate_last": True}, "jpeg-truncated-marker-sequence-detected")
    _add("MGL5-INF-0081", "boundary", "jpeg_markers", {"segments": [{"marker": "DQT", "payload_hex": "00" + "ff" * 64}, {"marker": "SOF0", "payload_hex": "080002000201011100"}], "truncate_last": False}, "jpeg-alternate-valid-marker-sequence")
    _add("MGL5-INF-0091", "negative", "partial_recovery", {"header_hex": "00000000", "payload_hex": "4142", "expected_magic_hex": "4c554e41"}, "partial-invalid-header-rejected")
    _add("MGL5-INF-0091", "boundary", "partial_recovery", {"header_hex": "4c554e41", "payload_hex": "", "expected_magic_hex": "4c554e41"}, "partial-empty-body-recovered")
    _add("MGL5-INF-0092", "negative", "timestamp_provenance", {"metadata_timestamp": 100, "filesystem_timestamp": 50}, "timestamp-order-does-not-prove-creation")
    _add("MGL5-INF-0092", "boundary", "timestamp_provenance", {"metadata_timestamp": 100, "filesystem_timestamp": 100}, "timestamp-equality-source-preserved")
    _add("MGL5-INF-0093", "negative", "dependency_graph", {"root": "A", "nodes": ["A", "B"], "edges": [["A", "B"], ["B", "A"]]}, "dependency-cycle-detected")
    _add("MGL5-INF-0093", "boundary", "dependency_graph", {"root": "A", "nodes": ["A"], "edges": []}, "dependency-singleton-no-edges")
    _add("MGL5-INF-0094", "negative", "protocol_version_diff", {"old_fields": [{"name": "count", "width": 16, "offset": 1}], "new_fields": [{"name": "count", "width": 32, "offset": 1}]}, "protocol-width-change-incompatible")
    _add("MGL5-INF-0094", "boundary", "protocol_version_diff", {"old_fields": [{"name": "id", "width": 8, "offset": 0}], "new_fields": [{"name": "id", "width": 8, "offset": 0}]}, "protocol-identical-layout-boundary")
    _add("MGL5-INF-0096", "negative", "section_overlaps", {"sections": [{"name": "a", "offset": 0, "size": 4}, {"name": "b", "offset": 8, "size": 2}]}, "sections-nonoverlap-rejected-as-invalid-fixture")
    _add("MGL5-INF-0096", "boundary", "section_overlaps", {"sections": [{"name": "a", "offset": 0, "size": 4}, {"name": "b", "offset": 4, "size": 1}]}, "sections-adjacent-no-overlap")
    _add("MGL5-INF-0098", "negative", "nested_zip_tar", {"entries": [{"name": "../../outside", "data_hex": "78"}]}, "nested-archive-retains-literal-entry-name")
    _add("MGL5-INF-0098", "boundary", "nested_zip_tar", {"entries": [{"name": "empty", "data_hex": ""}]}, "nested-archive-empty-member")
    _add("MGL5-INF-0100", "negative", "forensic_report", {"payload_hex": "00", "declared_size": 1, "stored_crc32": 3523407757, "sections": [{"name": "a", "offset": 0, "size": 1}]}, "forensic-clean-single-byte")
    _add("MGL5-INF-0100", "boundary", "forensic_report", {"payload_hex": "", "declared_size": 0, "stored_crc32": 0, "sections": []}, "forensic-empty-clean-boundary")
    _add("MGL5-INF-0076", "negative", "seven_zip_list", {"entries": [{"name": "nested/item.txt", "data_hex": "78"}]}, "seven-zip-nested-name-listed")
    _add("MGL5-INF-0076", "boundary", "seven_zip_list", {"entries": [{"name": "empty.bin", "data_hex": ""}]}, "seven-zip-empty-file-listed")
    _add("MGL5-INF-0077", "negative", "seven_zip_missing_volume", {"payload_hex": "00" * 8192, "volume_size": 1024, "missing_part": 99}, "seven-zip-out-of-range-part-rejected")
    _add("MGL5-INF-0077", "boundary", "seven_zip_missing_volume", {"payload_hex": "00" * 8192, "volume_size": 2048, "missing_part": 1}, "seven-zip-first-volume-missing")
    _add("MGL5-INF-0001", "boundary", text, {"text": ""}, "empty-roundtrip")
    _add("MGL5-INF-0002", "negative", text, {"text": "computacion"}, "different-text")
    _add("MGL5-INF-0002", "boundary", text, {"text": "ñ"}, "single-multibyte")
    _add("MGL5-INF-0003", "negative", "utf8_reject_invalid", {"payload_hex": "61"}, "valid-byte-accepted")
    _add("MGL5-INF-0003", "boundary", "utf8_reject_invalid", {"payload_hex": "c280"}, "valid-pair-accepted")
    _add("MGL5-INF-0004", "negative", "utf16_encode", {"text": "LUNA", "byte_order": "BE"}, "opposite-endian")
    _add("MGL5-INF-0004", "boundary", "utf16_encode", {"text": "", "byte_order": "LE"}, "empty-roundtrip")
    _add("MGL5-INF-0005", "negative", "utf16_encode", {"text": "LUNA", "byte_order": "LE"}, "opposite-endian")
    _add("MGL5-INF-0005", "boundary", "utf16_encode", {"text": "", "byte_order": "BE"}, "empty-roundtrip")
    _add("MGL5-INF-0006", "boundary", "bom_policy", {"without_bom": "", "with_bom_visible": ""}, "empty-roundtrip")
    _add("MGL5-INF-0007", "boundary", "u32_endian", {"payload_hex": "00000000"}, "zero")
    _add("MGL5-INF-0007", "negative", "u32_endian", {"payload_hex": "ffffffff"}, "not-the-sample")
    _add("MGL5-INF-0008", "negative", "uint16_bounds", {"values": [-1]}, "rejected")
    _add("MGL5-INF-0008", "boundary", "uint16_bounds", {"values": [0, 65535]}, "both-kept")
    _add("MGL5-INF-0009", "negative", "int16_values", {"values": [-32769]}, "rejected")
    _add("MGL5-INF-0009", "boundary", "int16_values", {"values": [-32768, 32767]}, "both-kept")
    _add("MGL5-INF-0010", "boundary", "twos_complement_16", {"hex_value": "0x7FFF", "width": 16}, "max-positive")
    _add("MGL5-INF-0010", "negative", "twos_complement_16", {"hex_value": "0x0000", "width": 16}, "not-minus-one")
    _add("MGL5-INF-0011", "negative", "float_bits", {"value": 1.0, "kind": 32, "reference": "0x3f800000"}, "one")
    _add("MGL5-INF-0011", "boundary", "float_bits", {"value": 0.0, "kind": 32, "reference": "0x00000000"}, "zero")
    _add("MGL5-INF-0012", "negative", "float_bits", {"value": 1.0, "kind": 64, "reference": "0x3ff0000000000000"}, "one")
    _add("MGL5-INF-0012", "boundary", "float_bits", {"value": 0.0, "kind": 64, "reference": "0x0000000000000000"}, "zero")
    _add("MGL5-INF-0016", "boundary", "nfc_compare", {"decomposed": "a", "composed": "a"}, "already-composed")
    _add("MGL5-INF-0028", "boundary", "json_reject", {"texts": ["{,}"]}, "also-rejected")
    _add("MGL5-INF-0048", "negative", "sha256_text", {"text": "ab"}, "not-the-vector")
    _add("MGL5-INF-0101", "boundary", "array_sum", {"values": [11], "empty": []}, "one-element")
    _add("MGL5-INF-0101", "negative", "array_sum", {"values": [1, 2], "empty": []}, "not-fifteen")
    _add("MGL5-INF-0102", "boundary", "array_minmax", {"values": [4]}, "one-element")
    _add("MGL5-INF-0102", "negative", "array_minmax", {"values": [1, 2]}, "not-the-sample")
    _add("MGL5-INF-0251", "negative", "ipv4_check", {"addresses": ["192.0.2.256"]}, "rejected")
    _add("MGL5-INF-0251", "boundary", "ipv4_check", {"addresses": ["0.0.0.0", "255.255.255.255"]}, "both-kept")
    _add("MGL5-INF-0021", "negative", "crlf_roundtrip", {"text": "a\nb\n"}, "no-cr")
    _add("MGL5-INF-0022", "boundary", "crlf_to_lf", {"text": "a\nb"}, "already-lf")
    _add("MGL5-INF-0023", "negative", "csv_roundtrip", {"rows": [["plain"]]}, "one-column")
    _add("MGL5-INF-0026", "negative", "json_text", {"text": "abc"}, "ascii")
    _add("MGL5-INF-0027", "negative", "duplicate_keys", {"text": '{"a":1}'}, "no-duplicate")
    _add("MGL5-INF-0029", "negative", "canonical_json", {"left": {"a": 1}, "right": {"a": 2}}, "different")
    _add("MGL5-INF-0032", "negative", "xml_unbalanced", {"document": "<a></a>"}, "balanced-accepted")
    _add("MGL5-INF-0036", "boundary", "framed_record", {"payload_hex": ""}, "empty-payload")
    _add("MGL5-INF-0042", "negative", "decimal_text", {"text": "0.2"}, "other-decimal")
    _add("MGL5-INF-0046", "negative", "base64_bytes", {"payload_hex": "000000"}, "other-bytes")
    _add("MGL5-INF-0047", "negative", "base64_reject", {"text": "AAAA"}, "valid-accepted")
    _add("MGL5-INF-0151", "negative", "tokenize", {"text": "x"}, "one-token")
    _add("MGL5-INF-0025", "negative", "json_roundtrip", {"document": {"n": 1}}, "other-json")
    _add("MGL5-INF-0050", "negative", "manifest_hash", {"document": {"name": "luna"}, "altered": {"name": "luna"}}, "unchanged")
    _add("MGL5-INF-0013", "boundary", "nan_policy", {}, "nan-edge")
    _add("MGL5-INF-0014", "boundary", "inf_policy", {}, "inf-edge")
    _add("MGL5-INF-0015", "boundary", "subnormal_f32", {}, "subnormal-edge")
    _add("MGL5-INF-0017", "boundary", "nfd_decompose", {"composed": "a"}, "ascii-nfd")
    _add("MGL5-INF-0018", "boundary", "nfkc_compat", {"text": "A"}, "ascii-nfkc")
    _add("MGL5-INF-0019", "negative", "text_units", {"text": "a"}, "one-unit")
    _add("MGL5-INF-0020", "negative", "text_units", {"text": "ab"}, "two-units")
    _add("MGL5-INF-0024", "boundary", "csv_newline", {"text": '"x\ny",9\n'}, "other-newline")
    _add("MGL5-INF-0030", "boundary", "xml_expanded", {"document": "<x/>"}, "no-prefix")
    _add("MGL5-INF-0030", "negative", "xml_expanded", {"document": '<a xmlns:a="urn:x"><b xmlns:b="urn:y"/></a>'}, "different-names")
    _add("MGL5-INF-0031", "negative", "xml_entities", {"document": "<r>ok</r>"}, "plain-text")
    _add("MGL5-INF-0037", "boundary", "truncated_records", {"payload_hex": "ff"}, "other-cut")
    _add("MGL5-INF-0038", "boundary", "oversize_length", {"payload_hex": "ff"}, "other-oversize")
    _add("MGL5-INF-0041", "boundary", "float32_exactness", {"values": [16777219]}, "next-inexact")
    _add("MGL5-INF-0043", "boundary", "three_states", {"present": {"b": None, "c": "x"}, "absent_key": "a"}, "not-empty")
    _add("MGL5-INF-0044", "boundary", "zlib_roundtrip", {"payload_hex": "01"}, "other-payload")
    _add("MGL5-INF-0045", "boundary", "zlib_corrupt", {"payload_hex": "01"}, "other-damaged")
    _add("MGL5-INF-0051", "negative", "magic_bytes", {"name": "sample.png", "payload_hex": "89504e470d0a1a0a"}, "extension-agrees")
    _add("MGL5-INF-0052", "negative", "magic_bytes", {"name": "sample.elf", "payload_hex": "00000000"}, "unknown-signature")
    _add("MGL5-INF-0052", "boundary", "magic_bytes", {"name": "sample.elf", "payload_hex": "7f454c46020101000000000000000000"}, "elf-extension-match")
    _add("MGL5-INF-0053", "negative", "elf_header", {"payload_hex": "7f454c4602010100000000000000000002003e000100000000004000000000004000000000000000000000000000000000000000400038000000400000000000"[:-2]}, "elf-truncated-header")
    _add("MGL5-INF-0053", "boundary", "elf_header", {"payload_hex": "7f454c4602010100000000000000000001003e000100000000000000000000000000000000000000000000000000000000000000400038000000400000000000"}, "elf-rel-boundary")
    _add("MGL5-INF-0601", "boundary", "binary_float_gap", {}, "float-edge")
    _add("MGL5-INF-0107", "negative", "duplicates", {"values": [1, 2, 3]}, "no-duplicates")
    _add("MGL5-INF-0107", "boundary", "duplicates", {"values": [5, 5]}, "single-duplicate")
    _add("MGL5-INF-0108", "negative", "brackets", {"texts": ["([)]"]}, "mismatched-brackets")
    _add("MGL5-INF-0108", "boundary", "brackets", {"texts": [""]}, "empty-brackets")
    _add("MGL5-INF-0103", "negative", "first_match", {"needle": 8, "values": [2, 7, 9, 7]}, "first-match-absent")
    _add("MGL5-INF-0103", "boundary", "first_match", {"needle": 7, "values": [7]}, "first-match-singleton")
    _add("MGL5-INF-0104", "negative", "binary_find", {"needle": 32, "start": 1, "end": 31}, "binary-find-absent")
    _add("MGL5-INF-0104", "boundary", "binary_find", {"needle": 1, "start": 1, "end": 31}, "binary-find-first")
    _add("MGL5-INF-0105", "negative", "stable_ages", {"records": [{"id": "", "age": 30}]}, "rejected")
    _add("MGL5-INF-0105", "boundary", "stable_ages", {"records": []}, "empty-record-set")
    _add("MGL5-INF-0106", "negative", "descending_seed", {"seed": 106, "count": -1}, "rejected")
    _add("MGL5-INF-0106", "boundary", "descending_seed", {"seed": 106, "count": 1}, "descending-seed-singleton")
    _add("MGL5-INF-0024", "negative", "csv_newline", {"text": '"a",1\n"b",2\n'}, "two-records")
    _add("MGL5-INF-0031", "boundary", "xml_entities", {"document": "<r>&lt;&gt;&amp;</r><!-- boundary -->"}, "predefined-entity-set")
    _add("MGL5-INF-0032", "boundary", "xml_unbalanced", {"document": "<a/>"}, "self-closing-accepted")
    _add("MGL5-INF-0037", "negative", "truncated_records", {"payload_hex": ""}, "all-truncated")
    _add("MGL5-INF-0038", "negative", "oversize_length", {"payload_hex": ""}, "empty-oversize-rejected")
    _add("MGL5-INF-0043", "negative", "three_states", {"present": {"b": None, "c": ""}, "absent_key": "b"}, "field-present")
    _add("MGL5-INF-0044", "negative", "zlib_roundtrip", {"payload_hex": ""}, "empty-payload-roundtrip")
    _add("MGL5-INF-0045", "negative", "zlib_corrupt", {"payload_hex": ""}, "empty-stream-corrupt")
    _add("MGL5-INF-0051", "boundary", "magic_bytes", {"name": "sample.dat", "payload_hex": "00000000"}, "unknown-signature")
    _add("MGL5-INF-0006", "negative", "bom_policy", {"without_bom": "plain", "with_bom_visible": "marked"}, "distinct-bom-payloads")
    _add("MGL5-INF-0016", "negative", "nfc_compare", {"decomposed": "e\u0301", "composed": "e"}, "nfc-mismatch")
    _add("MGL5-INF-0017", "negative", "nfd_decompose", {"composed": "ñ"}, "n-tilde-decomposed")
    _add("MGL5-INF-0018", "negative", "nfkc_compat", {"text": "Ａ"}, "fullwidth-compat")
    _add("MGL5-INF-0019", "boundary", "text_units", {"text": "e\u0301"}, "combining-grapheme")
    _add("MGL5-INF-0020", "boundary", "text_units", {"text": "\U0001f468\u200d\U0001f680"}, "zwj-one-grapheme")
    _add("MGL5-INF-0021", "boundary", "crlf_roundtrip", {"text": "x\r\n"}, "single-crlf")
    _add("MGL5-INF-0022", "negative", "crlf_to_lf", {"text": "a\rb"}, "lone-cr-normalized")
    _add("MGL5-INF-0023", "boundary", "csv_roundtrip", {"rows": [["", "x"], ["y", "z"]]}, "empty-cell-preserved")
    _add("MGL5-INF-0025", "boundary", "json_roundtrip", {"document": {"items": [1, None, False], "child": {"ok": True}}}, "nested-types-preserved")
    _add("MGL5-INF-0026", "boundary", "json_text", {"text": "ñ"}, "single-nonascii")
    _add("MGL5-INF-0027", "boundary", "duplicate_keys", {"text": "{\"x\":0,\"x\":0}"}, "duplicate-equal-values")
    _add("MGL5-INF-0028", "negative", "json_reject", {"texts": ["{\"a\":1}"]}, "valid-json-accepted")
    _add("MGL5-INF-0029", "boundary", "canonical_json", {"left": {}, "right": {}}, "empty-object-canonical")
    _add("MGL5-INF-0036", "negative", "framed_record", {"payload_hex": "ff"}, "single-byte-frame")
    _add("MGL5-INF-0041", "negative", "float32_exactness", {"values": [16777217]}, "float32-inexact-identified")
    _add("MGL5-INF-0041", "boundary", "float32_exactness", {"values": [16777216]}, "float32-exact-transition")
    _add("MGL5-INF-0042", "negative", "decimal_text", {"text": "0.10x"}, "decimal-invalid-rejected")
    _add("MGL5-INF-0042", "boundary", "decimal_text", {"text": "0.00"}, "zero-decimal-preserved")
    _add("MGL5-INF-0043", "negative", "three_states", {"present": {"b": None, "c": ""}, "absent_key": "b"}, "known-key-not-absent")
    _add("MGL5-INF-0043", "boundary", "three_states", {"present": {"b": None, "c": "x"}, "absent_key": "a"}, "nonempty-field-not-empty")
    _add("MGL5-INF-0046", "negative", "base64_bytes", {"payload_hex": "0g"}, "base64-invalid-hex-rejected")
    _add("MGL5-INF-0046", "boundary", "base64_bytes", {"payload_hex": "010203"}, "other-three-bytes")
    _add("MGL5-INF-0047", "negative", "base64_reject", {"text": "AA=="}, "valid-base64-accepted")
    _add("MGL5-INF-0047", "boundary", "base64_reject", {"text": "A==="}, "invalid-padding-rejected")
    _add("MGL5-INF-0048", "boundary", "sha256_text", {"text": ""}, "empty-sha256")
    _add("MGL5-INF-0050", "negative", "manifest_hash", {"document": {"name": "luna"}, "altered": {"name": "luna"}}, "unchanged-manifest-stable")
    _add("MGL5-INF-0050", "boundary", "manifest_hash", {"document": {}, "altered": {"name": "luna"}}, "empty-manifest-change")
    _add("MGL5-INF-0608", "negative", "l2_norm", {"components": ["3"]}, "noninteger-components-rejected")
    _add("MGL5-INF-0608", "boundary", "l2_norm", {"components": []}, "zero-vector")
    _add("MGL5-INF-0626", "negative", "pearson", {"left": [1, 1, 1], "right": [1, 2, 3]}, "zero-variance-rejected")
    _add("MGL5-INF-0626", "boundary", "pearson", {"left": [1, 2], "right": [2, 4]}, "perfect-positive-correlation")
    _add("MGL5-INF-0627", "negative", "pearson", {"left": [1, 1, 1], "right": [3, 2, 1]}, "zero-variance-rejected")
    _add("MGL5-INF-0627", "boundary", "pearson", {"left": [1, 2], "right": [2, 1]}, "perfect-negative-correlation")
    _add("MGL5-INF-0110", "negative", "dequeue_named", {"values": ["C", "B", "A"]}, "fifo-reversed-order")
    _add("MGL5-INF-0110", "boundary", "dequeue_named", {"values": ["A"]}, "fifo-singleton")
    _add("MGL5-INF-0120", "negative", "factorials", {"values": [-1]}, "factorial-negative-rejected")
    _add("MGL5-INF-0120", "boundary", "factorials", {"values": [0]}, "factorial-zero-boundary")
    _add("MGL5-INF-0142", "negative", "confined", {"requested": "escape"}, "symlink-escape-blocked")
    _add("MGL5-INF-0142", "boundary", "confined", {"requested": "inside-link"}, "internal-symlink-allowed")
    _add("MGL5-INF-0253", "negative", "ipv6_reject", {"address": "not-an-ipv6-address"}, "malformed-ipv6-rejected")
    _add("MGL5-INF-0253", "boundary", "ipv6_reject", {"address": "::"}, "ipv6-unspecified-accepted")
    _add("MGL5-INF-0254", "negative", "cidr_bounds", {"cidr": "192.0.2.130/33"}, "invalid-prefix-rejected")
    _add("MGL5-INF-0254", "boundary", "cidr_bounds", {"cidr": "192.0.2.130/32"}, "host-prefix-boundary")
    _add("MGL5-INF-0255", "negative", "ipv6_prefix", {"cidr": "2001:db8::1/129"}, "ipv6-prefix-rejected")
    _add("MGL5-INF-0255", "boundary", "ipv6_prefix", {"cidr": "2001:db8::1/128"}, "ipv6-host-prefix")
    _add("MGL5-INF-0616", "negative", "newton_root", {"initial": 1.0, "target": -1.0}, "newton-negative-target-rejected")
    _add("MGL5-INF-0616", "boundary", "newton_root", {"initial": 1.0, "target": 1.0}, "newton-unit-root-boundary")
    _add("MGL5-INF-0620", "negative", "linear_integral", {"panels": 0}, "trapezoid-zero-panels-rejected")
    _add("MGL5-INF-0620", "boundary", "linear_integral", {"panels": 1}, "trapezoid-single-panel-boundary")
    _add("MGL5-INF-0621", "negative", "square_integral", {"panels": 3}, "simpson-odd-panels-rejected")
    _add("MGL5-INF-0621", "boundary", "square_integral", {"panels": 2}, "simpson-minimum-even-boundary")
    _add("MGL5-INF-0618", "negative", "bracket_cube", {"low": 2.0, "high": 3.0}, "cube-no-sign-change-rejected")
    _add("MGL5-INF-0618", "boundary", "bracket_cube", {"low": 1.0, "high": 1.5}, "cube-tight-boundary")
    _add("MGL5-INF-0623", "negative", "two_variances", {"values": []}, "variance-empty-rejected")
    _add("MGL5-INF-0623", "boundary", "two_variances", {"values": [5]}, "variance-singleton-boundary")
    _add("MGL5-INF-0763", "negative", "ratio", {"numerator": 80, "denominator": 0}, "ratio-zero-denominator-rejected")
    _add("MGL5-INF-0763", "boundary", "ratio", {"numerator": 0, "denominator": 1}, "ratio-zero-numerator-boundary")
    _add("MGL5-INF-0764", "negative", "precision_recall", {"true_positive": 0, "false_positive": 0, "false_negative": 1}, "precision-zero-denominator-rejected")
    _add("MGL5-INF-0764", "boundary", "precision_recall", {"true_positive": 1, "false_positive": 0, "false_negative": 0}, "precision-perfect-boundary")
    _add("MGL5-INF-0765", "negative", "f1_score", {"precision": 0.0, "recall": 0.0}, "f1-zero-denominator-rejected")
    _add("MGL5-INF-0765", "boundary", "f1_score", {"precision": 1.0, "recall": 1.0}, "f1-perfect-boundary")
    _add("MGL5-INF-0171", "negative", "index_limit", {"length": -1}, "negative-length-no-read")
    _add("MGL5-INF-0171", "boundary", "index_limit", {"length": 0}, "zero-length-no-read")
    _add("MGL5-INF-0252", "negative", "expand_v6", {"address": "not-an-ipv6-address"}, "expanded-invalid-ipv6-rejected")
    _add("MGL5-INF-0252", "boundary", "expand_v6", {"address": "::"}, "ipv6-zero-boundary")
    _add("MGL5-INF-0256", "negative", "mask_bits", {"mask": "255.0.0.255"}, "invalid-mask-rejected")
    _add("MGL5-INF-0256", "boundary", "mask_bits", {"mask": "255.255.255.255"}, "all-ones-mask-valid")
    _add("MGL5-INF-0435", "negative", "threshold", {"low": 38, "high": 38, "limit": 38}, "threshold-equality-no-fire")
    _add("MGL5-INF-0435", "boundary", "threshold", {"low": 38.1, "high": 38.1, "limit": 38}, "threshold-above-fires")
    _add("MGL5-INF-0151", "boundary", "tokenize", {"text": ""}, "empty-token-stream")
    _add("MGL5-INF-0555", "negative", "increment", {"times": -1}, "increment-negative-rejected")
    _add("MGL5-INF-0555", "boundary", "increment", {"times": 0}, "increment-zero-boundary")
    _add("MGL5-INF-0561", "negative", "request_log", {"successes": 99, "failures": -1}, "request-negative-count-rejected")
    _add("MGL5-INF-0561", "boundary", "request_log", {"successes": 1, "failures": 0}, "request-single-success-boundary")
    _add("MGL5-INF-0602", "negative", "sqrt_two", {"value": -1.0}, "sqrt-negative-rejected")
    _add("MGL5-INF-0602", "boundary", "sqrt_two", {"value": 0.0}, "sqrt-zero-boundary")
    _add("MGL5-INF-0607", "negative", "compensated_sum", {"start": 1.0, "increment": 1e-8, "count": -1}, "sum-negative-count-rejected")
    _add("MGL5-INF-0607", "boundary", "compensated_sum", {"start": 1.0, "increment": 1e-8, "count": 0}, "sum-zero-boundary")
    _add("MGL5-INF-0109", "negative", "stack_sequence", {"steps": ["pop"]}, "single-underflow")
    _add("MGL5-INF-0109", "boundary", "stack_sequence", {"steps": []}, "empty-stack-sequence")
    _add("MGL5-INF-0112", "negative", "binary_insert", {"values": [5, 2, 9]}, "binary-insert-variant")
    _add("MGL5-INF-0112", "boundary", "binary_insert", {"values": [7]}, "binary-insert-singleton")
    _add("MGL5-INF-0125", "negative", "arithmetic", {"expression": "2+3*5"}, "arithmetic-variant-17")
    _add("MGL5-INF-0125", "boundary", "arithmetic", {"expression": "0+0"}, "arithmetic-zero-boundary")
    _add("MGL5-INF-0155", "negative", "arithmetic", {"expression": "2*(1+2)"}, "arithmetic-variant-6")
    _add("MGL5-INF-0155", "boundary", "arithmetic", {"expression": "(0+0)*1"}, "arithmetic-zero-boundary")
    _add("MGL5-INF-0168", "negative", "arithmetic", {"expression": "3*4+5"}, "arithmetic-variant-17")
    _add("MGL5-INF-0168", "boundary", "arithmetic", {"expression": "0*1+0"}, "arithmetic-zero-boundary")
    _add("MGL5-INF-0202", "negative", "child_status", {"exit_code": 1}, "child-exit-one")
    _add("MGL5-INF-0202", "boundary", "child_status", {"exit_code": 0}, "child-exit-zero")
    _add("MGL5-INF-0411", "negative", "cosine_set", {"pairs": [[[0, 0], [1, 0]]]}, "cosine-zero-vector-rejected")
    _add("MGL5-INF-0411", "boundary", "cosine_set", {"pairs": [[[3, 4], [3, 4]]]}, "cosine-identical-boundary")
    _add("MGL5-INF-0633", "negative", "acf_lag0", {"values": [5, 5, 5]}, "acf-zero-variance-rejected")
    _add("MGL5-INF-0633", "boundary", "acf_lag0", {"values": [1, 2]}, "acf-two-point-boundary")
    _add("MGL5-INF-0013", "negative", "nan_policy", {"value_kind": "finite"}, "nan-finite-control")
    _add("MGL5-INF-0013", "boundary", "nan_policy", {"value_kind": "negative-nan"}, "nan-negative-payload-boundary")
    _add("MGL5-INF-0014", "negative", "inf_policy", {"value_kind": "finite"}, "inf-finite-control")
    _add("MGL5-INF-0014", "boundary", "inf_policy", {"value_kind": "negative"}, "inf-negative-boundary")
    _add("MGL5-INF-0015", "negative", "subnormal_f32", {"value_kind": "smallest-normal"}, "subnormal-normal-control")
    _add("MGL5-INF-0015", "boundary", "subnormal_f32", {"value_kind": "zero"}, "subnormal-zero-boundary")
    _add("MGL5-INF-0601", "negative", "binary_float_gap", {"left": 0.5, "right": 0.25, "target": 0.75}, "float-exact-control")
    _add("MGL5-INF-0601", "boundary", "binary_float_gap", {"left": 0.1, "right": 0.2, "target": 0.30000000000000004}, "float-rounding-boundary")
    _add("MGL5-INF-0629", "negative", "exact_line", {"xs": [0, 1, 2], "slope": -1, "intercept": 0}, "line-negative-slope")
    _add("MGL5-INF-0629", "boundary", "exact_line", {"xs": [0, 1], "slope": 0, "intercept": 0}, "line-zero-slope-boundary")
    _add("MGL5-INF-0638", "negative", "euler_decay", {"coarse_step": 0.05, "fine_step": 0.1}, "euler-step-order-reversed")
    _add("MGL5-INF-0638", "boundary", "euler_decay", {"coarse_step": 0.1, "fine_step": 0.1}, "euler-equal-step-boundary")
    _add("MGL5-INF-0639", "negative", "rk4_decay", {"step": 2.0}, "rk4-step-out-of-range-rejected")
    _add("MGL5-INF-0639", "boundary", "rk4_decay", {"step": 1.0}, "rk4-single-step-boundary")

    _add("MGL5-INF-0033", "negative", "yaml_types", {"text": "name: Luna\n  broken: true\n"}, "yaml-rejected")
    _add("MGL5-INF-0033", "boundary", "yaml_types", {"text": "name: ''\nenabled: false\ncount: 0\nitems: []\n"}, "yaml-empty-boundary")
    _add("MGL5-INF-0034", "negative", "yaml_ambiguous", {"text": "flag: yes\n  broken: x\n", "schema_version": "1.1"}, "yaml-invalid-rejected")
    _add("MGL5-INF-0034", "boundary", "yaml_ambiguous", {"text": "flag: yes\ndate: 2026-01-02\n", "schema_version": "1.2"}, "yaml12-ambiguous-strings")
    _add("MGL5-INF-0035", "negative", "protobuf_old_reader", {"wire_hex": "08071205"}, "protobuf-malformed-rejected")
    _add("MGL5-INF-0035", "boundary", "protobuf_old_reader", {"wire_hex": "0807"}, "protobuf-no-unknown-fields")
    _add("MGL5-INF-0039", "negative", "schema_migrate", {"document": {"version": 0, "name": "Luna", "count": 3}}, "schema-v0-rejected")
    _add("MGL5-INF-0039", "boundary", "schema_migrate", {"document": {"version": 1, "name": "", "count": 0}}, "schema-v1-empty-migrates")
    _add("MGL5-INF-0040", "negative", "schema_unknown_field", {"record": {"name": 7, "version": 2, "extra": "future"}, "known_fields": ["name", "version"]}, "known-field-type-rejected")
    _add("MGL5-INF-0040", "boundary", "schema_unknown_field", {"record": {"name": "Luna", "version": 2}, "known_fields": ["name", "version"]}, "no-unknown-fields")
    _add("MGL5-INF-0049", "negative", "cbor_roundtrip", {"document": {"name": 1.5}}, "cbor-unsupported-value-rejected")
    _add("MGL5-INF-0049", "boundary", "cbor_roundtrip", {"document": {}}, "cbor-empty-map-roundtrip")

    # C05: distinct negative and boundary fixtures for the ten previously
    # source-defined but control-incomplete batch-5 operations.
    _add("MGL5-INF-0113", "negative", "balanced_range", {"count": 0}, "range-count-rejected")
    _add("MGL5-INF-0113", "boundary", "balanced_range", {"start": 0, "count": 1}, "range-singleton")
    _add("MGL5-INF-0119", "negative", "linear_scans", {"sizes": [0]}, "scan-size-rejected")
    _add("MGL5-INF-0119", "boundary", "linear_scans", {"sizes": [1, 2, 4], "needle": 0}, "scan-first-element")
    _add("MGL5-INF-0141", "negative", "parameterized_name", {"name": "' OR 1=1 --"}, "query-injection-not-matched")
    _add("MGL5-INF-0141", "boundary", "parameterized_name", {"name": "ada"}, "query-exact-match")
    _add("MGL5-INF-0154", "negative", "precedence_tree", {"text": "1+*2"}, "expression-rejected")
    _add("MGL5-INF-0154", "boundary", "precedence_tree", {"text": "0+0"}, "expression-zero")
    _add("MGL5-INF-0186", "negative", "divide_zero", {"numerator": 1, "denominator": 1}, "division-finite")
    _add("MGL5-INF-0186", "boundary", "divide_zero", {"numerator": 0, "denominator": 1}, "division-zero-numerator")
    _add("MGL5-INF-0208", "negative", "mode_0640", {"mode": 0o600}, "mode-owner-only")
    _add("MGL5-INF-0208", "boundary", "mode_0640", {"mode": 0o644}, "mode-world-readable")
    _add("MGL5-INF-0209", "negative", "umask_0027", {"mask": 0o077, "requested_mode": 0o666}, "umask-private")
    _add("MGL5-INF-0209", "boundary", "umask_0027", {"mask": 0, "requested_mode": 0o600}, "umask-zero")
    _add("MGL5-INF-0233", "negative", "child_env", {"key": "LUNA_C05_NEG", "value": "isolated-negative"}, "child-env-negative-value")
    _add("MGL5-INF-0233", "boundary", "child_env", {"key": "LUNA_C05_EDGE", "value": ""}, "child-env-empty-value")
    _add("MGL5-INF-0308", "negative", "reject_age", {"age": -1}, "age-negative-rejected")
    _add("MGL5-INF-0308", "boundary", "reject_age", {"age": 0}, "age-zero-accepted")
    _add("MGL5-INF-0503", "negative", "exit_codes", {"commands": []}, "command-list-rejected")
    _add("MGL5-INF-0503", "boundary", "exit_codes", {"commands": ["true"]}, "single-zero-exit")

def accepts(expect: str, observed: dict, status: str) -> bool:
    # A control is adjudicated against its own expected behavior, not the
    # NORMAL-case oracle verdict. FAIL means the executor ran and the normal
    # oracle rejected this control input; the observed control may still pass.
    control_completed = status in {"EXECUTED", "FAIL"}
    if expect == "zip-traversal-blocked": return control_completed and observed.get("blocked") == ["../../escape"] and observed.get("outside_write") is False
    if expect == "zip-safe-empty": return control_completed and observed.get("safe") == ["inside.txt"] and observed.get("blocked") == []
    if expect in {"zip-corrupt-crc-detected", "zip-minimum-member-crc-detected"}: return control_completed and observed.get("crc_error_detected") is True and observed.get("damaged_member_crc32") != observed.get("central_crc32")
    if expect == "zip-duplicate-content-preserved": return control_completed and observed.get("collisions") == ["x"] and observed.get("contents") == ["61", "62"] and observed.get("silent_overwrite") is False
    if expect == "zip-single-entry-preserved": return control_completed and observed.get("collisions") == [] and observed.get("contents") == [""]
    if expect == "tar-empty-block-boundaries": return control_completed and [row["header_offset"] for row in observed.get("members", [])] == [0, 512, 1536] and [row["size"] for row in observed.get("members", [])] == [0, 1, 0]
    if expect == "tar-one-byte-block-boundaries": return control_completed and [row["header_offset"] for row in observed.get("members", [])] == [0, 1024, 2048] and all(row["size"] == 1 for row in observed.get("members", []))
    if expect in {"tar-second-header-only-incomplete", "tar-second-empty-prefix-incomplete"}: return control_completed and observed.get("first_preserved") is True and observed.get("second_incomplete") is True
    if expect in {"sqlite-minimum-page-size", "sqlite-maximum-page-size"}: return control_completed and observed.get("page_size") in {512, 65536} and observed.get("encoding") == "UTF-8"
    if expect == "sqlite-corruption-reported": return control_completed and observed.get("integrity") is False and observed.get("corrupt_input") is True and bool(observed.get("messages"))
    if expect == "sqlite-empty-integrity-ok": return control_completed and observed.get("integrity") is True and observed.get("messages") == ["ok"]
    if expect == "wasm-invalid-magic-rejected": return control_completed and observed.get("accepted") is False and observed.get("magic_valid") is False
    if expect == "wasm-version-zero-rejected": return control_completed and observed.get("accepted") is False and observed.get("magic_valid") is True and observed.get("version") == 0
    if expect == "png-crc-mismatch-located": return control_completed and [row["type"] for row in observed.get("chunks", []) if not row["crc_valid"]] == ["IDAT"]
    if expect == "png-empty-idat-crc-valid": return control_completed and all(row["crc_valid"] for row in observed.get("chunks", [])) and observed.get("chunks", [])[1]["length"] == 0
    if expect == "known-signature-is-not-unknown": return control_completed and observed.get("format") == "png" and observed.get("invented_details") is False
    if expect == "unknown-single-byte": return control_completed and observed.get("format") == "unknown" and observed.get("length") == 1
    if expect == "zero-entropy-blocks": return control_completed and all(row["bits_per_byte"] == 0 for row in observed.get("blocks", []))
    if expect == "single-byte-entropy-boundary": return control_completed and observed.get("blocks") == [{"offset": 0, "length": 1, "bits_per_byte": 0.0}]
    if expect == "identical-binaries-no-diff": return control_completed and observed.get("differences") == []
    if expect == "single-byte-offset-zero-diff": return control_completed and observed.get("differences") == [{"offset": 0, "before": 0, "after": 1}]
    if expect == "oversized-declaration-rejected": return control_completed and observed.get("rejected") is True and observed.get("allocated_from_declaration") is False
    if expect == "zero-size-boundary": return control_completed and observed.get("rejected") is False and observed.get("actual_size") == 0 and observed.get("allocated_from_declaration") is False
    if expect in {"reproducibility-with-different-input", "empty-input-reproducibility"}: return control_completed and observed.get("identical") is True and observed.get("first") == observed.get("second")
    if expect == "jpeg-truncated-marker-sequence-detected": return control_completed and observed.get("valid") is False and observed.get("truncated") is True
    if expect == "jpeg-alternate-valid-marker-sequence": return control_completed and observed.get("valid") is True and [row["name"] for row in observed.get("markers", [])] == ["SOI", "DQT", "SOF0", "EOI"]
    if expect == "partial-invalid-header-rejected": return control_completed and observed.get("header_valid") is False and observed.get("recovered_hex") == "" and observed.get("integrity_complete") is False
    if expect == "partial-empty-body-recovered": return control_completed and observed.get("header_valid") is True and observed.get("recovered_hex") == "" and observed.get("unknown_trailer") is True
    if expect in {"timestamp-order-does-not-prove-creation", "timestamp-equality-source-preserved"}: return control_completed and [row["source"] for row in observed.get("timestamps", [])] == ["embedded_metadata", "filesystem"] and observed.get("creation_time_proven") is False and bool(observed.get("warning"))
    if expect == "dependency-cycle-detected": return control_completed and observed.get("rejected") is False and observed.get("cycle") is True and observed.get("reachable") == ["A", "B"]
    if expect == "dependency-singleton-no-edges": return control_completed and observed.get("rejected") is False and observed.get("cycle") is False and observed.get("reachable") == []
    if expect == "protocol-width-change-incompatible": return control_completed and observed.get("changes", [{}])[0].get("change") == "modified" and observed.get("backward_compatible") is False
    if expect == "protocol-identical-layout-boundary": return control_completed and observed.get("changes") == [] and observed.get("backward_compatible") is True
    if expect in {"sections-nonoverlap-rejected-as-invalid-fixture", "sections-adjacent-no-overlap"}: return control_completed and observed.get("overlaps") == [] and observed.get("valid") is True
    if expect == "nested-archive-retains-literal-entry-name": return control_completed and observed.get("tree", {}).get("children", [{}])[0].get("children", [{}])[0].get("name") == "../../outside"
    if expect == "nested-archive-empty-member": return control_completed and observed.get("tree", {}).get("children", [{}])[0].get("children") == [{"name": "empty", "size": 0, "data_hex": ""}]
    if expect in {"forensic-clean-single-byte", "forensic-empty-clean-boundary"}: return control_completed and observed.get("observations") == [] and observed.get("inferences") == [] and observed.get("conclusion", {}).get("anomaly_count") == 0
    if expect == "seven-zip-nested-name-listed": return control_completed and observed.get("members") == [{"name": "nested/item.txt", "size": 1, "method": "Copy"}]
    if expect == "seven-zip-empty-file-listed": return control_completed and observed.get("members") == [{"name": "empty.bin", "size": 0, "method": "not_applicable_empty"}]
    if expect == "seven-zip-out-of-range-part-rejected": return control_completed and observed.get("rejected") is True and observed.get("reason") == "missing_part_index_out_of_range"
    if expect == "seven-zip-first-volume-missing": return control_completed and observed.get("rejected") is False and observed.get("missing_volume") == "parts.7z.001" and observed.get("reconstruction_complete") is False and observed.get("seven_zip_test_exit_code") != 0
    if expect in {"gzip-crc-mismatch-detected", "gzip-empty-crc-mismatch-detected"}: return control_completed and observed.get("crc_error_detected") is True
    # A schema-level rejection is a valid negative control even though the
    # operation never ran and therefore produced no observed payload.
    if expect == "yaml-invalid-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "yaml-parse-error"
    if expect == "yaml12-ambiguous-strings":
        return control_completed and observed.get("rejected") is False and observed.get("schema_version") == "1.2" and observed.get("parsed") == {"flag": "yes", "date": "2026-01-02"} and observed.get("types") == {"flag": "str", "date": "str"}
    if expect == "protobuf-malformed-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "truncated-length-delimited"
    if expect == "protobuf-no-unknown-fields":
        return control_completed and observed.get("accepted") is True and observed.get("unknown_fields") == [] and observed.get("known_fields") == {"1": 7}
    if expect == "schema-v0-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "unsupported-version"
    if expect == "schema-v1-empty-migrates":
        return control_completed and observed.get("rejected") is False and observed.get("document") == {"version": 2, "name": "", "count": 0}
    if expect == "known-field-type-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "known-field-type"
    if expect == "no-unknown-fields":
        return control_completed and observed.get("accepted") is True and observed.get("known") == {"name": "Luna", "version": 2} and observed.get("unknown") == {}
    if expect == "cbor-unsupported-value-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "unsupported-value-type"
    if expect == "cbor-empty-map-roundtrip":
        return control_completed and observed.get("accepted") is True and observed.get("wire_hex") == "a0" and observed.get("decoded") == {} and observed.get("same_types") is True
    if expect == "yaml-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "yaml-parse-error"
    if expect == "yaml-empty-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("parsed") == {"name": "", "enabled": False, "count": 0, "items": []} and observed.get("types") == {"name": "str", "enabled": "bool", "count": "int", "items": "list"}
    if expect == "float32-inexact-identified":
        return control_completed and observed.get("rows") == [{"value": 16777217, "exact": False}]
    if expect == "float32-exact-transition":
        return control_completed and observed.get("rows") == [{"value": 16777216, "exact": True}]
    if expect == "decimal-invalid-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "invalid-decimal"
    if expect == "known-key-not-absent":
        return control_completed and observed == {"absent": False, "null": True, "empty": True}
    if expect == "nonempty-field-not-empty":
        return control_completed and observed == {"absent": True, "null": True, "empty": False}
    if expect == "base64-invalid-hex-rejected":
        return control_completed and observed == {"rejected": True, "reason": "invalid-hex-input"}
    if expect == "valid-base64-accepted":
        return control_completed and observed.get("rejected") is False and observed.get("error_recorded") is False
    if expect == "unchanged-manifest-stable":
        return control_completed and observed.get("reproduced") is True and observed.get("altered_changes") is False
    if expect == "trapezoid-zero-panels-rejected":
        return status == "REJECTED" and observed is None
    if observed is None:
        return False
    if expect == "preflight-blocked":
        return (
            status == "BLOCKED"
            and observed.get("blocked") is True
            and observed.get("operation_invoked") is False
            and observed.get("phase") in {"NEGATIVE_CONTROL", "BOUNDARY_CONTROL"}
            and isinstance(observed.get("blocker_code"), str)
            and bool(observed["blocker_code"])
        )
    if expect == "different-text":
        return control_completed and observed["recovered"] not in {"Luna-2026", "computación, información, ñandú"}
    if expect == "empty-roundtrip":
        return control_completed and (
            observed.get("recovered", observed.get("visible", observed.get("plain_text", ""))) in {"", "LUNA"}
            or observed.get("bytes_hex") == ""
            or observed.get("visible") == ""
        )
    if expect == "single-multibyte":
        return control_completed and observed["bytes_hex"] == "c3b1"
    if expect == "valid-byte-accepted":
        return control_completed and observed["accepted_as_valid_utf8"] is True
    if expect == "valid-pair-accepted":
        return control_completed and observed["accepted_as_valid_utf8"] is True
    if expect == "opposite-endian":
        return control_completed and observed["bytes_hex"] in {"004c0055004e0041", "4c0055004e004100"}
    if expect == "zero":
        return control_completed and ("0x00000000" in observed.values() or observed.get("bits_hex") in {"0x00000000", "0x0000000000000000"})
    if expect == "not-the-sample":
        return control_completed and observed.get("little_endian_hex") != "0x04030201" and observed.get("minimum") != -8
    if expect == "rejected":
        rejected = observed.get("rejected")
        return control_completed and (
            rejected is True or (isinstance(rejected, list) and bool(rejected))
        )
    if expect == "both-kept":
        return control_completed and bool(observed.get("kept", observed.get("accepted")))
    if expect == "max-positive":
        return control_completed and observed["signed"] == 32767
    if expect == "not-minus-one":
        return control_completed and observed["signed"] == 0
    if expect == "one":
        return control_completed and observed["bits_hex"] in {"0x3f800000", "0x3ff0000000000000"}
    if expect == "also-rejected":
        return control_completed and observed["rejected_count"] == 1
    if expect == "not-the-vector":
        return status == "FAIL"
    if expect == "one-element":
        return control_completed and (observed.get("sum") == 11 or observed.get("minimum") == 4)
    if expect == "not-fifteen":
        return control_completed and observed["sum"] != 15
    if expect == "empty-token-stream":
        return control_completed and observed.get("tokens") == []
    if expect == "increment-negative-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "increment-zero-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("completed") == 0 and observed.get("failed") == 0 and observed.get("ids") == []
    if expect == "request-negative-count-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "request-single-success-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("availability") == 1.0 and observed.get("successes") == 1 and observed.get("failures") == 0 and observed.get("total") == 1
    if expect == "sqrt-negative-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "sqrt-zero-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("estimate") == 0 and observed.get("residual") == 0
    if expect == "sum-negative-count-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "sum-zero-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("naive") == 1.0 and observed.get("kahan") == 1.0
    if expect == "newton-negative-target-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "newton-unit-root-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("root") == 1.0 and observed.get("residual") == 0.0
    if expect == "trapezoid-zero-panels-rejected":
        return status == "REJECTED" and observed is None
    if expect == "trapezoid-single-panel-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("value") == 0.5 and observed.get("panels") == 1
    if expect == "simpson-odd-panels-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "simpson-minimum-even-boundary":
        return control_completed and observed.get("rejected") is False and abs(observed.get("value", 0) - (1 / 3)) < 1e-12 and observed.get("panels") == 2
    if expect == "cube-no-sign-change-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "cube-tight-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("high", 2) - observed.get("low", 0) < 1e-9
    if expect == "variance-empty-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "variance-singleton-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("population") == 0 and observed.get("sample") is None
    if expect == "ratio-zero-denominator-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "ratio-zero-numerator-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("value") == 0 and observed.get("denominator") == 1
    if expect == "precision-zero-denominator-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "precision-perfect-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("precision") == 1 and observed.get("recall") == 1
    if expect == "f1-zero-denominator-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "f1-perfect-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("f1") == 1
    if expect == "negative-length-no-read":
        return control_completed and observed.get("out_of_range") is True and observed.get("reads") == 0 and observed.get("length") == 0
    if expect == "zero-length-no-read":
        return control_completed and observed.get("out_of_range") is True and observed.get("reads") == 0 and observed.get("length") == 0
    if expect == "expanded-invalid-ipv6-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "ipv6-zero-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("expanded") == "0000:0000:0000:0000:0000:0000:0000:0000" and observed.get("integer") == 0
    if expect == "invalid-mask-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("contiguous") is False
    if expect == "all-ones-mask-valid":
        return control_completed and observed.get("rejected") is False and observed.get("contiguous") is True and observed.get("bits") == "1" * 32
    if expect == "threshold-equality-no-fire":
        return control_completed and observed.get("at_or_below") is True and observed.get("above") is False
    if expect == "threshold-above-fires":
        return control_completed and observed.get("at_or_below") is False and observed.get("above") is True
    if expect == "fifo-reversed-order":
        return control_completed and observed.get("order") == ["C", "B", "A"] and observed.get("remaining") == 0
    if expect == "fifo-singleton":
        return control_completed and observed.get("order") == ["A"] and observed.get("remaining") == 0
    if expect == "factorial-negative-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("negative_rejected") is True
    if expect == "factorial-zero-boundary":
        return control_completed and observed.get("rejected") is False and observed.get("values") == [1]
    if expect == "symlink-escape-blocked":
        return control_completed and observed.get("blocked") is True and observed.get("bytes_read") == 0 and observed.get("reason") == "symlink-escapes"
    if expect == "internal-symlink-allowed":
        return control_completed and observed.get("blocked") is False and observed.get("bytes_read") == 7 and observed.get("reason") == "internal-link"
    if expect == "malformed-ipv6-rejected":
        return control_completed and observed.get("accepted") is False
    if expect == "ipv6-unspecified-accepted":
        return control_completed and observed.get("accepted") is True
    if expect == "invalid-prefix-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "host-prefix-boundary":
        return control_completed and observed.get("network") == "192.0.2.130" and observed.get("broadcast") == "192.0.2.130"
    if expect == "ipv6-prefix-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "ipv6-host-prefix":
        return control_completed and observed.get("rejected") is False and observed.get("prefix") == "2001:db8::1/128"
    if expect == "noninteger-components-rejected":
        return control_completed and observed.get("rejected") is True
    if expect == "zero-vector":
        return control_completed and observed.get("norm") == 0 and observed.get("square") == 0
    if expect == "zero-variance-rejected":
        return control_completed and observed.get("value") is None and observed.get("error") == "zero-variance"
    if expect == "perfect-positive-correlation":
        return control_completed and observed.get("error") is None and abs(observed.get("value", 0) - 1.0) < 1e-9
    if expect == "perfect-negative-correlation":
        return control_completed and observed.get("error") is None and abs(observed.get("value", 0) + 1.0) < 1e-9
    if expect == "nfc-mismatch":
        return control_completed and observed.get("same_nfc") is False and observed.get("nfc") == "é"
    if expect == "n-tilde-decomposed":
        return control_completed and observed.get("codepoints") == ["U+006E", "U+0303"]
    if expect == "fullwidth-compat":
        return control_completed and observed.get("compatibility") == "A" and observed.get("preserves_original_form") is False
    if expect == "distinct-bom-payloads":
        return control_completed and observed.get("visible") == "marked" and observed.get("plain_text") == "plain" and observed.get("contains_bom_character") is False
    if expect == "combining-grapheme":
        return control_completed and observed.get("bytes") == 3 and observed.get("codepoints") == 2 and observed.get("graphemes") == 1
    if expect == "zwj-one-grapheme":
        return control_completed and observed.get("preserved") == "👨‍🚀" and observed.get("codepoints") == 3 and observed.get("graphemes") == 1
    if expect == "single-crlf":
        return control_completed and observed.get("lines") == ["x"] and observed.get("written") == "x\r\n" and observed.get("doubled_cr") is False
    if expect == "lone-cr-normalized":
        return control_completed and observed.get("converted") == "a\nb" and observed.get("cr_remaining") is False
    if expect == "empty-cell-preserved":
        return control_completed and observed.get("parsed") == [["", "x"], ["y", "z"]]
    if expect == "nested-types-preserved":
        return control_completed and observed.get("parsed") == {"items": [1, None, False], "child": {"ok": True}}
    if expect == "single-nonascii":
        return control_completed and observed.get("parsed") == "ñ" and "\\u00" not in observed.get("raw", "")
    if expect == "duplicate-equal-values":
        return control_completed and observed.get("duplicate_detected") is True and observed.get("deterministic") is True
    if expect == "valid-json-accepted":
        return control_completed and observed.get("rejected_count") == 0 and observed.get("rejected") == []
    if expect == "empty-object-canonical":
        return control_completed and observed.get("same") is True and observed.get("canonical") == "{}"
    if expect == "single-byte-frame":
        return control_completed and observed.get("length") == 1 and observed.get("checksum") == 255
    if expect == "exact-power-boundary":
        return control_completed and observed.get("rows") == [{"value": 16777216, "exact": True}]
    if expect == "zero-decimal-preserved":
        return control_completed and observed.get("text") == "0.00" and observed.get("used_binary_float") is False
    if expect == "other-three-bytes":
        return control_completed and observed.get("decoded_hex") == "010203"
    if expect == "invalid-padding-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("error_recorded") is True
    if expect == "empty-sha256":
        return control_completed and observed.get("digest_hex") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    if expect == "empty-manifest-change":
        return control_completed and observed.get("reproduced") is True and observed.get("altered_changes") is True and observed.get("digest") == "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"
    if expect == "two-records":
        return control_completed and observed.get("records") == 2 and observed.get("fields", [None])[0] == "a"
    if expect == "predefined-entity-set":
        return control_completed and observed.get("text") == "<>&" and observed.get("external_expanded") is False
    if expect == "self-closing-accepted":
        return control_completed and observed.get("rejected") is False
    if expect == "all-truncated":
        return control_completed and observed.get("all_rejected") is True and len(observed.get("rejected_lengths", [])) == 4
    if expect == "empty-oversize-rejected":
        return control_completed and observed.get("rejected") is True and observed.get("allocated_declared_length") is False
    if expect == "field-present":
        return control_completed and observed.get("absent") is False and observed.get("null") is True and observed.get("empty") is True
    if expect == "empty-payload-roundtrip":
        return control_completed and observed.get("match") is True and observed.get("compressed_differs") is True
    if expect == "empty-stream-corrupt":
        return control_completed and observed.get("corruption_detected") is True and observed.get("integrity_claimed") is False
    if expect == "unknown-signature":
        return control_completed and observed.get("detected") == "unknown" and observed.get("extension_matches_content") is False
    if expect == "elf-truncated-header":
        return control_completed and observed.get("rejected") is True and observed.get("reason") == "truncated-header"
    if expect == "elf-rel-boundary":
        return control_completed and observed == {"rejected": False, "class": "ELF64", "endianness": "little", "architecture": "x86-64", "object_type": "REL", "header_size": 64}
    if expect == "no-cr":
        return control_completed and observed["written"] == "a\r\nb\r\n"
    if expect == "already-lf":
        return control_completed and observed["converted"] == "a\nb" and observed["cr_remaining"] is False
    if expect == "one-column":
        return control_completed and observed["parsed"] == [["plain"]]
    if expect == "ascii":
        return control_completed and observed["parsed"] == "abc"
    if expect == "no-duplicate":
        return observed["duplicate_detected"] is False
    if expect == "different":
        return observed["same"] is False
    if expect == "balanced-accepted":
        return observed is not None and observed["rejected"] is False
    if expect == "empty-payload":
        return control_completed and observed["length"] == 0 and observed["checksum"] == 0
    if expect == "other-decimal":
        return control_completed and observed.get("text") == "0.2" and observed.get("used_binary_float") is False
    if expect == "other-bytes":
        return control_completed and observed["decoded_hex"] == "000000"
    if expect == "valid-accepted":
        return observed is not None and observed["rejected"] is False
    if expect == "one-token":
        return control_completed and observed.get("tokens") == [{"kind": "word", "lexeme": "x", "start": 0, "end": 1}]
    if expect == "other-json":
        return control_completed and observed["parsed"] == {"n": 1}
    if expect == "unchanged":
        return observed is not None and observed["altered_changes"] is False
    if expect == "nan-edge":
        return control_completed and observed["equals_itself"] is False
    if expect == "inf-edge":
        return control_completed and observed["positive_sign"] is True and observed["negative_sign"] is True
    if expect == "subnormal-edge":
        return control_completed and observed["is_subnormal"] is True
    if expect == "ascii-nfd":
        return control_completed and observed["codepoints"] == ["U+0061"]
    if expect == "ascii-nfkc":
        return control_completed and observed["compatibility"] == "A" and observed["preserves_original_form"] is True
    if expect == "one-unit":
        return control_completed and observed["graphemes"] == 1 and observed["codepoints"] == 1
    if expect == "two-units":
        return control_completed and observed["graphemes"] == observed["codepoints"] == 2
    if expect == "other-newline":
        return control_completed and observed["records"] == 1 and observed["fields"][0] == "x\ny"
    if expect == "no-prefix":
        return control_completed and observed["expanded_names"] == ["x"]
    if expect == "different-names":
        return control_completed and observed["same_expanded_name"] is False
    if expect == "plain-text":
        return control_completed and observed["text"] == "ok" and observed["external_expanded"] is False
    if expect == "other-cut":
        return control_completed and observed["all_rejected"] is True
    if expect == "other-oversize":
        return control_completed and observed["rejected"] is True and observed["allocated_declared_length"] is False
    if expect == "next-inexact":
        return control_completed and observed["rows"] == [{"value": 16777219, "exact": False}]
    if expect == "not-empty":
        return control_completed and observed["empty"] is False and observed["null"] is True
    if expect == "other-payload":
        return control_completed and observed["match"] is True and observed["compressed_differs"] is True
    if expect == "other-damaged":
        return control_completed and observed["corruption_detected"] is True and observed["integrity_claimed"] is False
    if expect == "extension-agrees":
        return control_completed and observed["detected"] == "png" and observed["extension_matches_content"] is True
    if expect == "elf-extension-match":
        return control_completed and observed.get("detected") == "elf" and observed.get("extension_matches_content") is True
    if expect == "float-edge":
        return control_completed and observed["equal"] is False and observed["difference"] != 0
    if expect == "already-composed":
        return control_completed and observed["same_nfc"] is True and observed["nfc"] == "a"
    if expect == "no-duplicates":
        return control_completed and observed.get("duplicates") == []
    if expect == "single-duplicate":
        return control_completed and observed.get("duplicates") == [5]
    if expect == "mismatched-brackets":
        return control_completed and observed.get("results") == [{"text": "([)]", "accepted": False}]
    if expect == "empty-brackets":
        return control_completed and observed.get("results") == [{"text": "", "accepted": True}]
    if expect == "first-match-absent":
        return control_completed and observed.get("index") is None and observed.get("duplicates") == []
    if expect == "first-match-singleton":
        return control_completed and observed.get("index") == 0 and observed.get("duplicates") == [0]
    if expect == "binary-find-absent":
        return control_completed and observed.get("index") is None and observed.get("comparisons", 0) > 0
    if expect == "binary-find-first":
        return control_completed and observed.get("index") == 0 and 1 <= observed.get("comparisons", 0) <= 5
    if expect == "empty-record-set":
        return control_completed and observed.get("records") == [] and observed.get("rejected") is False
    if expect == "descending-seed-singleton":
        ordered = observed.get("ordered")
        return (
            control_completed and observed.get("rejected") is False
            and observed.get("length") == 1 and isinstance(ordered, list)
            and len(ordered) == 1 and observed.get("first") == observed.get("last") == ordered[0]
            and observed.get("checksum") == ordered[0]
        )
    if expect == "single-underflow":
        return (
            control_completed
            and observed.get("underflow_count") == 1
            and observed.get("events") == [{"operation": "underflow", "source": "pop"}]
        )
    if expect == "empty-stack-sequence":
        return (
            control_completed
            and observed.get("events") == []
            and observed.get("stack") == []
            and observed.get("underflow_count") == 0
        )

    if expect == "range-count-rejected": return control_completed and observed.get("rejected") is True
    if expect == "range-singleton": return control_completed and observed.get("rejected") is False and observed.get("count") == observed.get("nodes") == observed.get("found") == 1
    if expect == "scan-size-rejected": return control_completed and observed.get("rejected") is True
    if expect == "scan-first-element": return control_completed and observed.get("rejected") is False and observed.get("comparisons") == [1, 1, 1]
    if expect == "query-injection-not-matched": return control_completed and observed.get("matched") == 0 and observed.get("status") == 200
    if expect == "query-exact-match": return control_completed and observed.get("matched") == 1 and observed.get("status") == 200
    if expect == "expression-rejected": return control_completed and observed.get("rejected") is True
    if expect == "expression-zero": return control_completed and observed.get("rejected") is False and observed.get("value") == 0
    if expect == "division-finite": return control_completed and observed.get("raised") is False and observed.get("value") == 1
    if expect == "division-zero-numerator": return control_completed and observed.get("raised") is False and observed.get("value") == 0
    if expect == "mode-owner-only": return control_completed and observed.get("mode") == 0o600
    if expect == "mode-world-readable": return control_completed and observed.get("mode") == 0o644
    if expect == "umask-private": return control_completed and observed.get("mode") == 0o600
    if expect == "umask-zero": return control_completed and observed.get("mode") == 0o600
    if expect == "child-env-negative-value": return control_completed and observed.get("value") == "isolated-negative" and observed.get("code") == 0
    if expect == "child-env-empty-value": return control_completed and observed.get("value") == "" and observed.get("code") == 0
    if expect == "age-negative-rejected": return control_completed and observed.get("rejected") is True and observed.get("rows") == 0
    if expect == "age-zero-accepted": return control_completed and observed.get("rejected") is False and observed.get("rows") == 1
    if expect == "command-list-rejected": return control_completed and observed.get("rejected") is True
    if expect == "single-zero-exit": return control_completed and observed.get("rejected") is not True and observed.get("commands") == ["true"] and observed.get("codes") == [0]

    if expect == "binary-insert-variant": return control_completed and observed.get("inorder") == [2, 5, 9]
    if expect == "binary-insert-singleton": return control_completed and observed.get("inorder") == [7]
    if expect == "arithmetic-variant-17": return control_completed and observed.get("value") == 17
    if expect == "arithmetic-variant-6": return control_completed and observed.get("value") == 6
    if expect == "arithmetic-zero-boundary": return control_completed and observed.get("value") == 0
    if expect == "child-exit-one": return control_completed and observed.get("exit_code") == 1
    if expect == "child-exit-zero": return control_completed and observed.get("exit_code") == 0
    if expect == "cosine-zero-vector-rejected": return control_completed and observed.get("rejected") is True
    if expect == "cosine-identical-boundary": return control_completed and observed.get("rejected") is False and observed.get("values") == [1.0]
    if expect == "acf-zero-variance-rejected": return control_completed and observed.get("lags") is None and observed.get("error") == "zero-variance"
    if expect == "acf-two-point-boundary":
        values = observed.get("lags")
        return control_completed and observed.get("error") is None and isinstance(values, list) and len(values) == 2 and abs(values[0] - 1.0) < 1e-9 and abs(values[1] + 0.5) < 1e-9
    if expect == "nan-finite-control": return control_completed and observed.get("is_nan") is False and observed.get("equals_itself") is True and observed.get("ordinary") is True
    if expect == "nan-negative-payload-boundary": return control_completed and observed.get("is_nan") is True and observed.get("equals_itself") is False and observed.get("negative_sign") is True
    if expect == "inf-finite-control": return control_completed and observed.get("positive_sign") is False and observed.get("negative_sign") is False
    if expect == "inf-negative-boundary": return control_completed and observed.get("positive_sign") is False and observed.get("negative_sign") is True
    if expect == "subnormal-normal-control": return control_completed and observed.get("is_subnormal") is False and observed.get("float32_bits_hex") == "00800000"
    if expect == "subnormal-zero-boundary": return control_completed and observed.get("is_subnormal") is False and observed.get("float32_bits_hex") == "00000000"
    if expect == "float-exact-control": return control_completed and observed.get("equal") is True and observed.get("difference") == 0 and observed.get("decimal_exact") is True
    if expect == "float-rounding-boundary": return control_completed and observed.get("equal") is True and observed.get("difference") == 0 and observed.get("decimal_exact") is False
    if expect == "line-negative-slope": return control_completed and observed.get("slope") == -1 and observed.get("intercept") == 0
    if expect == "line-zero-slope-boundary": return control_completed and observed.get("slope") == 0 and observed.get("intercept") == 0
    if expect == "euler-step-order-reversed": return control_completed and observed.get("fine_error", 0) > observed.get("coarse_error", 0)
    if expect == "euler-equal-step-boundary": return control_completed and abs(observed.get("fine_error", 0) - observed.get("coarse_error", 0)) < 1e-12
    if expect == "rk4-step-out-of-range-rejected": return control_completed and observed.get("rejected") is True
    if expect == "rk4-single-step-boundary": return control_completed and observed.get("rejected") is not True and observed.get("step") == 1.0
    return False





def run_controls() -> list[dict]:
    _build()
    rows = []
    for spec in CASES:
        controls = CONTROLS.get(spec["case_id"], {})
        record = {"case_id": spec["case_id"], "controls": {}}
        for kind, item in controls.items():
            metadata = {
                "definition": f"{kind.upper()} control {item['expect']}",
                "expected_behavior": f"accepts({item['expect']!r}, observed, lifecycle_status) is true",
                "source": f"{__file__}:{spec['case_id']}:{kind}",
            }
            result = execute(
                item["capability_id"], item["arguments"], spec["case_id"],
                run_kind=kind.upper(), control_metadata=metadata,
            )
            record["controls"][kind] = {
                "execution_status": result["execution_status"],
                "run_kind": result["run_kind"],
                "control_metadata": result["control_metadata"],
                "observed": result["observed"],
                "accepted": accepts(item["expect"], result["observed"], result["lifecycle_status"]),
            }
        record["control_status"] = "PRESENT" if controls and all(item["accepted"] for item in record["controls"].values()) else "MISSING"
        rows.append(record)
    return rows
