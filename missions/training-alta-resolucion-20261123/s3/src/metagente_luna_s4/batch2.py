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
    {"case_id": "MGL5-INF-0036", "capability_id": "framed_record", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0037", "capability_id": "truncated_records", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0038", "capability_id": "oversize_length", "arguments": {"payload_hex": "0102"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0041", "capability_id": "float32_exactness", "arguments": {"values": [16777216, 16777217]}},
    {"case_id": "MGL5-INF-0042", "capability_id": "decimal_text", "arguments": {"text": "0.10"}},
    {"case_id": "MGL5-INF-0043", "capability_id": "three_states", "arguments": {"present": {"b": None, "c": ""}, "absent_key": "a"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0044", "capability_id": "zlib_roundtrip", "arguments": {"payload_hex": "00ff"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0045", "capability_id": "zlib_corrupt", "arguments": {"payload_hex": "00ff"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0046", "capability_id": "base64_bytes", "arguments": {"payload_hex": "0000ff"}},
    {"case_id": "MGL5-INF-0047", "capability_id": "base64_reject", "arguments": {"text": "****"}},
    {"case_id": "MGL5-INF-0050", "capability_id": "manifest_hash", "arguments": {"document": {"name": "luna"}, "altered": {"name": "luna-x"}}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0051", "capability_id": "magic_bytes", "arguments": {"name": "sample.dat", "payload_hex": "89504e470d0a1a0a"}, "fixture_provenance": "SIGNATURE_PREFIX_NOT_A_FULL_PNG"},
    {"case_id": "MGL5-INF-0052", "capability_id": "magic_bytes", "arguments": {"name": "sample.jpg", "payload_hex": "7f454c46020101000000000000000000"}, "fixture_provenance": "ELF64_LE_IDENT_HEADER_PREFIX"},
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
