from __future__ import annotations

import inspect

from metagente_luna_s4.controls import CONTROLS, _build
from metagente_luna_s4.independent_validator import _independent_control_accepts


def test_independent_validator_covers_every_authored_control_expectation():
    _build()
    expectations = {
        control["expect"]
        for pair in CONTROLS.values()
        for control in pair.values()
    }
    source = inspect.getsource(_independent_control_accepts)
    missing = sorted(expectation for expectation in expectations if f'"{expectation}"' not in source)
    assert not missing, f"independent adjudicator lacks authored expectations: {missing}"


def test_independent_negative_and_boundary_controls_accept_oracle_rejection_when_semantics_hold():
    cases = [
        ("valid-pair-accepted", {"accepted_as_valid_utf8": True}),
        ("already-composed", {"same_nfc": True, "nfc": "a"}),
        ("also-rejected", {"rejected_count": 1}),
        ("no-cr", {"written": "a\\r\\nb\\r\\n"}),
        ("already-lf", {"converted": "a\\nb", "cr_remaining": False}),
        ("one-column", {"parsed": [["plain"]]}),
        ("ascii", {"parsed": "abc"}),
        ("no-duplicate", {"duplicate_detected": False}),
        ("different", {"same": False}),
        ("balanced-accepted", {"rejected": False}),
        ("empty-payload", {"length": 0, "checksum": 0}),
        ("other-decimal", {"text": "0.2", "used_binary_float": False}),
        ("other-bytes", {"decoded_hex": "000000"}),
        ("valid-accepted", {"rejected": False}),
        ("one-token", {"tokens": [{"kind": "word", "lexeme": "x", "start": 0, "end": 1}]}),
        ("other-json", {"parsed": {"n": 1}}),
        ("unchanged", {"altered_changes": False}),
        ("nan-edge", {"equals_itself": False}),
        ("inf-edge", {"positive_sign": True, "negative_sign": True}),
        ("subnormal-edge", {"is_subnormal": True}),
        ("ascii-nfd", {"codepoints": ["U+0061"]}),
        ("ascii-nfkc", {"compatibility": "A", "preserves_original_form": True}),
        ("one-unit", {"graphemes": 1, "codepoints": 1}),
        ("two-units", {"graphemes": 2, "codepoints": 2}),
        ("other-newline", {"records": 1, "fields": ["x\\ny"]}),
        ("plain-text", {"text": "ok", "external_expanded": False}),
        ("other-cut", {"all_rejected": True}),
        ("other-oversize", {"rejected": True, "allocated_declared_length": False}),
        ("next-inexact", {"rows": [{"value": 16777219, "exact": False}]}),
        ("not-empty", {"empty": False, "null": True}),
        ("other-payload", {"match": True, "compressed_differs": True}),
        ("other-damaged", {"corruption_detected": True, "integrity_claimed": False}),
        ("extension-agrees", {"detected": "png", "extension_matches_content": True}),
        ("elf-extension-match", {"detected": "elf", "extension_matches_content": True}),
        ("float-edge", {"equal": False, "difference": 1}),
    ]
    for expectation, observed in cases:
        assert _independent_control_accepts(expectation, observed, "FAIL") is True, expectation
        assert _independent_control_accepts(expectation, observed, "BLOCKED") is False, expectation


def test_independent_adjudicator_preserves_special_failure_and_schema_rejection_contracts():
    assert _independent_control_accepts(
        "not-the-vector", {"digest_hex": "not-the-known-vector"}, "FAIL"
    ) is True
    assert _independent_control_accepts(
        "not-the-vector", {"digest_hex": "not-the-known-vector"}, "EXECUTED"
    ) is False
    assert _independent_control_accepts(
        "trapezoid-zero-panels-rejected", None, "REJECTED"
    ) is True
    assert _independent_control_accepts(
        "trapezoid-zero-panels-rejected", {"rejected": True}, "EXECUTED"
    ) is False
    assert _independent_control_accepts("unknown-control", {}, "EXECUTED") is False
    assert _independent_control_accepts(
        "rejected", {"rejected": [-1]}, "FAIL"
    ) is True
    assert _independent_control_accepts(
        "rejected", {"rejected": []}, "FAIL"
    ) is False
