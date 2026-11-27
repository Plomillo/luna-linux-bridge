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
    _add("MGL5-INF-0041", "negative", "float32_exactness", {"values": [16777216]}, "exact-power-boundary")
    _add("MGL5-INF-0042", "boundary", "decimal_text", {"text": "0.00"}, "zero-decimal-preserved")
    _add("MGL5-INF-0046", "boundary", "base64_bytes", {"payload_hex": "010203"}, "other-three-bytes")
    _add("MGL5-INF-0047", "boundary", "base64_reject", {"text": "A==="}, "invalid-padding-rejected")
    _add("MGL5-INF-0048", "boundary", "sha256_text", {"text": ""}, "empty-sha256")
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


def accepts(expect: str, observed: dict, status: str) -> bool:
    # A control is adjudicated against its own expected behavior, not the
    # NORMAL-case oracle verdict. FAIL means the executor ran and the normal
    # oracle rejected this control input; the observed control may still pass.
    control_completed = status in {"EXECUTED", "FAIL"}
    # A schema-level rejection is a valid negative control even though the
    # operation never ran and therefore produced no observed payload.
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
        return control_completed and observed.get("kept", observed.get("accepted"))
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
