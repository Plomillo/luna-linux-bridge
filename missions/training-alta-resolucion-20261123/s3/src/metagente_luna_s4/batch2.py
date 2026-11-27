"""Second execution batch. A matched criterion is not a closed C05 gate."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

_ENTITIES = "<r>" + "".join(chr(code) for code in (38, 108, 116, 59, 38, 103, 116, 59, 38, 97, 109, 112, 59)) + "</r>"
_ZWJ = "\U0001f468\u200d\U0001f680"
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
