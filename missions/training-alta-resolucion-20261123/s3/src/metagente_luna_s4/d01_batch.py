"""Runs the encoding cases whose inputs are in the program text. One match here is not C05."""
from __future__ import annotations

from metagente_luna_s4.runner import execute

LIGATURE = "\ufb01"
CASES = [
    {"case_id": "MGL5-INF-0001", "capability_id": "utf8_roundtrip", "arguments": {"text": "Luna-2026"}},
    {"case_id": "MGL5-INF-0002", "capability_id": "utf8_roundtrip", "arguments": {"text": "computación, información, ñandú"}},
    {"case_id": "MGL5-INF-0003", "capability_id": "utf8_reject_invalid", "arguments": {"payload_hex": "80"}},
    {"case_id": "MGL5-INF-0004", "capability_id": "utf16_encode", "arguments": {"text": "LUNA", "byte_order": "LE"}},
    {"case_id": "MGL5-INF-0005", "capability_id": "utf16_encode", "arguments": {"text": "LUNA", "byte_order": "BE"}},
    {"case_id": "MGL5-INF-0006", "capability_id": "bom_policy", "arguments": {"without_bom": "LUNA", "with_bom_visible": "LUNA"}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0007", "capability_id": "u32_endian", "arguments": {"payload_hex": "01020304"}},
    {"case_id": "MGL5-INF-0008", "capability_id": "uint16_bounds", "arguments": {"values": [0, 65535, 65536]}},
    {"case_id": "MGL5-INF-0009", "capability_id": "int16_values", "arguments": {"values": [-32768, -1, 0, 32767, 32768]}},
    {"case_id": "MGL5-INF-0010", "capability_id": "twos_complement_16", "arguments": {"hex_value": "0xFFFF", "width": 16}},
    {"case_id": "MGL5-INF-0011", "capability_id": "float_bits", "arguments": {"value": 1.5, "kind": 32, "reference": "0x3fc00000"}},
    {"case_id": "MGL5-INF-0012", "capability_id": "float_bits", "arguments": {"value": 1.5, "kind": 64, "reference": "0x3ff8000000000000"}},
    {"case_id": "MGL5-INF-0013", "capability_id": "nan_policy", "arguments": {"value_kind": "nan"}},
    {"case_id": "MGL5-INF-0014", "capability_id": "inf_policy", "arguments": {"value_kind": "both"}},
    {"case_id": "MGL5-INF-0015", "capability_id": "subnormal_f32", "arguments": {"value_kind": "smallest-subnormal"}},
    {"case_id": "MGL5-INF-0016", "capability_id": "nfc_compare", "arguments": {"decomposed": "e\u0301", "composed": "\u00e9"}},
    {"case_id": "MGL5-INF-0017", "capability_id": "nfd_decompose", "arguments": {"composed": "\u00e9"}},
    {"case_id": "MGL5-INF-0018", "capability_id": "nfkc_compat", "arguments": {"text": LIGATURE}},
    {"case_id": "MGL5-INF-0025", "capability_id": "json_roundtrip", "arguments": {"document": {"text": "ñ", "flag": True, "empty": None, "count": 1, "items": [1], "child": {"ok": False}}}, "fixture_provenance": "SYNTHETIC_MINIMAL"},
    {"case_id": "MGL5-INF-0028", "capability_id": "json_reject", "arguments": {"texts": ["{a:1}", "{\"a\":1,}"]}},
    {"case_id": "MGL5-INF-0048", "capability_id": "sha256_text", "arguments": {"text": "abc"}},
    {"case_id": "MGL5-INF-0041", "capability_id": "float32_exactness", "arguments": {"values": [16777216, 16777217, 16777219]}, "fixture_provenance": "SYNTHETIC_MINIMAL: IEEE-754 binary32 exact-integer boundary"},
    {"case_id": "MGL5-INF-0042", "capability_id": "decimal_text", "arguments": {"text": "0.10"}},
    {"case_id": "MGL5-INF-0043", "capability_id": "three_states", "arguments": {"present": {"b": None, "c": ""}, "absent_key": "a"}, "fixture_provenance": "SYNTHETIC_MINIMAL: absent/null/empty fields"},
    {"case_id": "MGL5-INF-0046", "capability_id": "base64_bytes", "arguments": {"payload_hex": "00ff01"}, "fixture_provenance": "SYNTHETIC_MINIMAL: byte sequence contains 0x00 and 0xFF"},
    {"case_id": "MGL5-INF-0047", "capability_id": "base64_reject", "arguments": {"text": "A==="}},
    {"case_id": "MGL5-INF-0050", "capability_id": "manifest_hash", "arguments": {"document": {"name": "luna", "version": 1}, "altered": {"name": "luna", "version": 2}}, "fixture_provenance": "SYNTHETIC_MINIMAL: deterministic manifest and alteration"},
]


def run_case(spec: dict) -> dict:
    runs = [execute(spec["capability_id"], spec["arguments"], spec["case_id"]) for _ in range(3)]
    observed = [run["observed"] for run in runs]
    same = all(item == observed[0] for item in observed)
    oracle_ok = all(run["oracle_result"] and run["oracle_result"].get("ok") is True for run in runs)
    primary_ok = all(run["execution_status"] == "EXECUTED" for run in runs) and same and oracle_ok
    return {
        "case_id": spec["case_id"],
        "capability_id": spec["capability_id"],
        "arguments": spec["arguments"],
        "fixture_provenance": spec.get("fixture_provenance", "PROGRAM_LITERAL"),
        "repetitions": [run["run_id"] for run in runs],
        "observed": observed[0],
        "oracle_method": None if not runs[0]["oracle_result"] else runs[0]["oracle_result"].get("method"),
        "stdout": [run["stdout"] for run in runs],
        "stderr": [run["stderr"] for run in runs],
        "exit_code": [run["exit_code"] for run in runs],
        "execution_status": "CRITERION_MET" if primary_ok else "FAIL",
        "protocol_gap": "separate negative and boundary runs were not executed for this case",
        "backend": "LOCAL_TEST_ONLY",
        "independent_review": "NOT_AVAILABLE",
        "teo_status": "NOT_APPLICABLE",
        "c05_gate": "NOT_PASSED",
        "c08_status": "NOT_ACCREDITED",
    }


def run_all() -> list[dict]:
    return [run_case(spec) for spec in CASES]


def assess_c05(executed: list[dict]) -> dict:
    met = [row["case_id"] for row in executed if row["execution_status"] == "CRITERION_MET"]
    return {
        "source": "mission/authority/PROTODEFINITIVO.txt",
        "source_lines": "589-643",
        "acceptance_text": "los 1.000 identificadores tienen expedientes individuales y resultados auténticos, sin ocultar fallos.",
        "operation_text": "Ejecutar cada caso individualmente",
        "identifiers": 1000,
        "executed_this_run": len(executed),
        "criterion_met_this_run": len(met),
        "not_run": 1000 - len(executed),
        "gate": "NOT_PASSED",
        "counter": "4/26",
        "reason": "979 cases were not executed. A matching criterion is not the common protocol PASS, because the separate negative and boundary runs are still missing.",
        "teo_engineering_board": "NOT_DEFINED_IN_PROTOCOL",
        "teo_cases": "MGL5-TEO-0001..0050 remain NOT_RUN",
    }
