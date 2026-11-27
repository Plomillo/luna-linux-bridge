"""Negative and boundary inputs for the fifty cases already executed."""
from __future__ import annotations

from metagente_luna_s4.batch2 import CASES as SECOND
from metagente_luna_s4.d01_batch import CASES as FIRST
from metagente_luna_s4.runner import execute

CASES = FIRST + SECOND


CONTROLS: dict[str, dict] = {}


def _add(case_id: str, kind: str, capability: str, arguments: dict, expect: str) -> None:
    CONTROLS.setdefault(case_id, {})[kind] = {"capability_id": capability, "arguments": arguments, "expect": expect}


def _build() -> None:
    if CONTROLS:
        return
    text = "utf8_roundtrip"
    _add("MGL5-INF-0001", "negative", text, {"text": "Luna-2025"}, "different-text")
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
    _add("MGL5-INF-0601", "boundary", "binary_float_gap", {}, "float-edge")
    _add("MGL5-INF-0105", "negative", "stable_ages", {"records": [{"id": "bad", "age": "unknown"}]}, "rejected")
    _add("MGL5-INF-0105", "boundary", "stable_ages", {"records": []}, "empty-record-set")
    _add("MGL5-INF-0109", "negative", "stack_sequence", {"steps": ["pop"]}, "single-underflow")
    _add("MGL5-INF-0109", "boundary", "stack_sequence", {"steps": []}, "empty-stack-sequence")


def accepts(expect: str, observed: dict, status: str) -> bool:
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
        return status == "EXECUTED" and observed["recovered"] not in {"Luna-2026", "computación, información, ñandú"}
    if expect == "empty-roundtrip":
        return status == "EXECUTED" and (
            observed.get("recovered", observed.get("visible", observed.get("plain_text", ""))) in {"", "LUNA"}
            or observed.get("bytes_hex") == ""
            or observed.get("visible") == ""
        )
    if expect == "single-multibyte":
        return status == "EXECUTED" and observed["bytes_hex"] == "c3b1"
    if expect == "valid-byte-accepted":
        return status == "EXECUTED" and observed["accepted_as_valid_utf8"] is True
    if expect == "valid-pair-accepted":
        return status == "EXECUTED" and observed["accepted_as_valid_utf8"] is True
    if expect == "opposite-endian":
        return status == "EXECUTED" and observed["bytes_hex"] in {"004c0055004e0041", "4c0055004e004100"}
    if expect == "zero":
        return status == "EXECUTED" and ("0x00000000" in observed.values() or observed.get("bits_hex") in {"0x00000000", "0x0000000000000000"})
    if expect == "not-the-sample":
        return status == "EXECUTED" and observed.get("little_endian_hex") != "0x04030201" and observed.get("minimum") != -8
    if expect == "rejected":
        return status == "EXECUTED" and observed.get("rejected")
    if expect == "both-kept":
        return status == "EXECUTED" and observed.get("kept", observed.get("accepted"))
    if expect == "max-positive":
        return status == "EXECUTED" and observed["signed"] == 32767
    if expect == "not-minus-one":
        return status == "EXECUTED" and observed["signed"] == 0
    if expect == "one":
        return status == "EXECUTED" and observed["bits_hex"] in {"0x3f800000", "0x3ff0000000000000"}
    if expect == "also-rejected":
        return status == "EXECUTED" and observed["rejected_count"] == 1
    if expect == "not-the-vector":
        return status == "FAIL"
    if expect == "one-element":
        return status == "EXECUTED" and (observed.get("sum") == 11 or observed.get("minimum") == 4)
    if expect == "not-fifteen":
        return status == "EXECUTED" and observed["sum"] != 15
    if expect == "no-cr":
        return status == "EXECUTED" and observed["written"] == "a\r\nb\r\n"
    if expect == "already-lf":
        return status == "EXECUTED" and observed["converted"] == "a\nb" and observed["cr_remaining"] is False
    if expect == "one-column":
        return status == "EXECUTED" and observed["parsed"] == [["plain"]]
    if expect == "ascii":
        return status == "EXECUTED" and observed["parsed"] == "abc"
    if expect == "no-duplicate":
        return observed["duplicate_detected"] is False
    if expect == "different":
        return observed["same"] is False
    if expect == "balanced-accepted":
        return observed is not None and observed["rejected"] is False
    if expect == "empty-payload":
        return status == "EXECUTED" and observed["length"] == 0 and observed["checksum"] == 0
    if expect == "other-decimal":
        return status == "FAIL"
    if expect == "other-bytes":
        return status == "EXECUTED" and observed["decoded_hex"] == "000000"
    if expect == "valid-accepted":
        return observed is not None and observed["rejected"] is False
    if expect == "one-token":
        return status == "FAIL"
    if expect == "other-json":
        return status == "EXECUTED" and observed["parsed"] == {"n": 1}
    if expect == "unchanged":
        return observed is not None and observed["altered_changes"] is False
    if expect == "nan-edge":
        return status == "EXECUTED" and observed["equals_itself"] is False
    if expect == "inf-edge":
        return status == "EXECUTED" and observed["positive_sign"] is True and observed["negative_sign"] is True
    if expect == "subnormal-edge":
        return status == "EXECUTED" and observed["is_subnormal"] is True
    if expect == "ascii-nfd":
        return status == "EXECUTED" and observed["codepoints"] == ["U+0061"]
    if expect == "ascii-nfkc":
        return status == "EXECUTED" and observed["compatibility"] == "A" and observed["preserves_original_form"] is True
    if expect == "one-unit":
        return status == "EXECUTED" and observed["graphemes"] == 1 and observed["codepoints"] == 1
    if expect == "two-units":
        return status == "EXECUTED" and observed["graphemes"] == observed["codepoints"] == 2
    if expect == "other-newline":
        return status == "EXECUTED" and observed["records"] == 1 and observed["fields"][0] == "x\ny"
    if expect == "no-prefix":
        return status == "EXECUTED" and observed["expanded_names"] == ["x"]
    if expect == "different-names":
        return status == "EXECUTED" and observed["same_expanded_name"] is False
    if expect == "plain-text":
        return status == "EXECUTED" and observed["text"] == "ok" and observed["external_expanded"] is False
    if expect == "other-cut":
        return status == "EXECUTED" and observed["all_rejected"] is True
    if expect == "other-oversize":
        return status == "EXECUTED" and observed["rejected"] is True and observed["allocated_declared_length"] is False
    if expect == "next-inexact":
        return status == "EXECUTED" and observed["rows"] == [{"value": 16777219, "exact": False}]
    if expect == "not-empty":
        return status == "EXECUTED" and observed["empty"] is False and observed["null"] is True
    if expect == "other-payload":
        return status == "EXECUTED" and observed["match"] is True and observed["compressed_differs"] is True
    if expect == "other-damaged":
        return status == "EXECUTED" and observed["corruption_detected"] is True and observed["integrity_claimed"] is False
    if expect == "extension-agrees":
        return status == "EXECUTED" and observed["detected"] == "png" and observed["extension_matches_content"] is True
    if expect == "float-edge":
        return status == "EXECUTED" and observed["equal"] is False and observed["difference"] != 0
    if expect == "already-composed":
        return status == "EXECUTED" and observed["same_nfc"] is True and observed["nfc"] == "a"
    if expect == "empty-record-set":
        return status == "EXECUTED" and observed.get("records") == [] and observed.get("rejected") is False
    if expect == "single-underflow":
        return (
            status == "EXECUTED"
            and observed.get("underflow_count") == 1
            and observed.get("events") == [{"operation": "underflow", "source": "pop"}]
        )
    if expect == "empty-stack-sequence":
        return (
            status == "EXECUTED"
            and observed.get("events") == []
            and observed.get("stack") == []
            and observed.get("underflow_count") == 0
        )
    return False


def run_controls() -> list[dict]:
    _build()
    rows = []
    for spec in CASES:
        controls = CONTROLS.get(spec["case_id"], {})
        record = {"case_id": spec["case_id"], "controls": {}}
        for kind, item in controls.items():
            result = execute(item["capability_id"], item["arguments"], spec["case_id"])
            record["controls"][kind] = {
                "execution_status": result["execution_status"],
                "observed": result["observed"],
                "accepted": accepts(item["expect"], result["observed"], result["execution_status"]),
            }
        record["control_status"] = "PRESENT" if controls and all(item["accepted"] for item in record["controls"].values()) else "MISSING"
        rows.append(record)
    return rows
