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
        ("no-cr", {"written": "a\r\nb\r\n"}),
        ("already-lf", {"converted": "a\nb", "cr_remaining": False}),
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
        ("other-newline", {"records": 1, "fields": ["x\ny"]}),
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


def test_new_source_grounded_controls_are_independently_adjudicated():
    cases = [
        ("binary-insert-variant", {"inorder": [2, 5, 9]}, "EXECUTED"),
        ("binary-insert-singleton", {"inorder": [7]}, "EXECUTED"),
        ("arithmetic-variant-17", {"value": 17}, "EXECUTED"),
        ("arithmetic-variant-6", {"value": 6}, "EXECUTED"),
        ("arithmetic-zero-boundary", {"value": 0}, "EXECUTED"),
        ("child-exit-one", {"exit_code": 1}, "EXECUTED"),
        ("child-exit-zero", {"exit_code": 0}, "EXECUTED"),
        ("cosine-zero-vector-rejected", {"rejected": True}, "EXECUTED"),
        ("cosine-identical-boundary", {"rejected": False, "values": [1.0]}, "EXECUTED"),
        ("acf-zero-variance-rejected", {"lags": None, "error": "zero-variance"}, "EXECUTED"),
        ("acf-two-point-boundary", {"lags": [1.0, -0.5], "error": None}, "EXECUTED"),
    ]
    for expect, observed, status in cases:
        assert _independent_control_accepts(expect, observed, status) is True, expect
        assert _independent_control_accepts(expect, observed, "BLOCKED") is False, expect


def test_ieee754_and_float_gap_controls_have_independent_adjudication():
    cases = [
        ("nan-finite-control", {"is_nan": False, "equals_itself": True, "ordinary": True}),
        ("nan-negative-payload-boundary", {"is_nan": True, "equals_itself": False, "negative_sign": True}),
        ("inf-finite-control", {"positive_sign": False, "negative_sign": False}),
        ("inf-negative-boundary", {"positive_sign": False, "negative_sign": True}),
        ("subnormal-normal-control", {"is_subnormal": False, "float32_bits_hex": "00800000"}),
        ("subnormal-zero-boundary", {"is_subnormal": False, "float32_bits_hex": "00000000"}),
        ("float-exact-control", {"equal": True, "difference": 0, "decimal_exact": True}),
        ("float-rounding-boundary", {"equal": True, "difference": 0, "decimal_exact": False}),
    ]
    for expect, observed in cases:
        assert _independent_control_accepts(expect, observed, "EXECUTED") is True, expect
        assert _independent_control_accepts(expect, observed, "BLOCKED") is False, expect


def test_numerical_fit_and_integrator_controls_are_independently_adjudicated():
    cases = [
        ("line-negative-slope", {"slope": -1, "intercept": 0}),
        ("line-zero-slope-boundary", {"slope": 0, "intercept": 0}),
        ("euler-step-order-reversed", {"coarse_error": 0.1, "fine_error": 0.2}),
        ("euler-equal-step-boundary", {"coarse_error": 0.1, "fine_error": 0.1}),
        ("rk4-step-out-of-range-rejected", {"rejected": True}),
        ("rk4-single-step-boundary", {"rejected": False, "step": 1.0}),
    ]
    for expect, observed in cases:
        assert _independent_control_accepts(expect, observed, "EXECUTED") is True, expect
        assert _independent_control_accepts(expect, observed, "BLOCKED") is False, expect
