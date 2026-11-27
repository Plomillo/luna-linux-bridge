import os

from metagente_luna_s4.controls import CONTROLS, accepts, run_controls
from metagente_luna_s4.isolated import execute_isolated, run_bounded


def test_process_separation_hides_secrets_and_times_out(monkeypatch):
    monkeypatch.setenv("LUNA_SECRET", "do-not-leak")
    outcome = run_bounded("import os; print(os.environ.get('LUNA_SECRET'))", "", 2)
    assert outcome["status"] == "FINISHED"
    assert "do-not-leak" not in outcome["stdout"]
    timed = run_bounded("import time; time.sleep(5)", "", 0.2)
    assert timed["status"] == "TIMEOUT"
    assert os.environ["LUNA_SECRET"] == "do-not-leak"


def test_child_file_stays_in_the_child_workspace():
    from pathlib import Path

    parent = Path.cwd()
    outcome = run_bounded("from pathlib import Path; Path('marker.txt').write_text('x')", "", 2)
    assert outcome["status"] == "FINISHED"
    assert (Path(outcome["cwd"]) / "marker.txt").read_text() == "x"
    assert not (parent / "marker.txt").exists()
    record = execute_isolated("array_sum", {"values": [-3, 0, 7, 11], "empty": []}, "MGL5-INF-0101")
    assert record["backend"] == "PROCESS_SEPARATION"
    assert record["sandbox"] is False
    assert record["observed"] == {"sum": 15, "empty_sum": 0}
    assert record["execution_status"] == "EXECUTED"


def test_controls_that_were_defined_are_accepted():
    rows = run_controls()
    defined = [row for row in rows if row["controls"]]
    assert defined
    failures = [(row["case_id"], {kind: {"accepted": result["accepted"], "status": result["execution_status"], "observed": result["observed"]} for kind, result in row["controls"].items() if not result["accepted"]}) for row in defined if row["control_status"] != "PRESENT"]
    assert not failures, __import__("json").dumps(failures, ensure_ascii=False, sort_keys=True)
    # The runner must execute every currently authored control case; the
    # registry is the authoritative count, not a stale historical constant.
    assert {row["case_id"] for row in defined} == set(CONTROLS)
    assert len(defined) == len(CONTROLS) == 120

def test_yaml_type_plan_and_independent_oracle_cover_negative_and_boundary_inputs():
    from metagente_luna_s3.d01_exec import yaml_types
    from metagente_luna_s3.d01_oracle import yaml_types_oracle

    normal = {"text": "name: Luna\nenabled: true\ncount: 3\nitems:\n  - uno\n  - dos\n"}
    negative = {"text": "name: Luna\n  broken: true\n"}
    boundary = {"text": "name: ''\nenabled: false\ncount: 0\nitems: []\n"}
    normal_result = yaml_types(**normal)
    assert yaml_types_oracle(normal, normal_result)["ok"] is True
    negative_result = yaml_types(**negative)
    assert yaml_types_oracle(negative, negative_result)["ok"] is True
    boundary_result = yaml_types(**boundary)
    assert yaml_types_oracle(boundary, boundary_result)["ok"] is True
    assert accepts("yaml-rejected", negative_result, "EXECUTED") is True
    assert accepts("yaml-empty-boundary", boundary_result, "EXECUTED") is True


def test_yaml_ambiguous_scalars_follow_the_declared_schema_version():
    from metagente_luna_s3.d01_exec import yaml_ambiguous
    from metagente_luna_s3.d01_oracle import yaml_ambiguous_oracle

    arguments_11 = {"text": "flag: yes\ndate: 2026-01-02\n", "schema_version": "1.1"}
    result_11 = yaml_ambiguous(**arguments_11)
    assert yaml_ambiguous_oracle(arguments_11, result_11)["ok"] is True
    assert result_11["types"] == {"flag": "bool", "date": "date"}

    arguments_12 = {"text": "flag: yes\ndate: 2026-01-02\n", "schema_version": "1.2"}
    result_12 = yaml_ambiguous(**arguments_12)
    assert yaml_ambiguous_oracle(arguments_12, result_12)["ok"] is True
    assert result_12["types"] == {"flag": "str", "date": "str"}

    negative = {"text": "flag: yes\n  broken: x\n", "schema_version": "1.1"}
    rejected = yaml_ambiguous(**negative)
    assert yaml_ambiguous_oracle(negative, rejected)["ok"] is True
    assert accepts("yaml-invalid-rejected", rejected, "EXECUTED") is True
    assert accepts("yaml12-ambiguous-strings", result_12, "EXECUTED") is True


def test_both_kept_control_returns_a_boolean_not_a_collection():
    result = accepts("both-kept", {"kept": [0, 65535]}, "EXECUTED")
    assert result is True
    assert isinstance(result, bool)


def test_negative_controls_accept_explicit_rejected_collections():
    assert accepts("rejected", {"kept": [], "rejected": [-1]}, "EXECUTED") is True
    assert accepts("rejected", {"accepted": [], "rejected": ["192.0.2.256"]}, "EXECUTED") is True
    assert accepts("rejected", {"kept": [], "rejected": []}, "EXECUTED") is False


def test_d01_complementary_controls_cover_text_serialization_and_hash_boundaries():
    assert accepts("distinct-bom-payloads", {"visible": "marked", "plain_text": "plain", "contains_bom_character": False}, "EXECUTED") is True
    assert accepts("combining-grapheme", {"bytes": 3, "codepoints": 2, "graphemes": 1}, "EXECUTED") is True
    assert accepts("zwj-one-grapheme", {"preserved": "👨‍🚀", "codepoints": 3, "graphemes": 1}, "EXECUTED") is True
    assert accepts("single-crlf", {"lines": ["x"], "written": "x\r\n", "doubled_cr": False}, "EXECUTED") is True
    assert accepts("lone-cr-normalized", {"converted": "a\nb", "cr_remaining": False}, "EXECUTED") is True
    assert accepts("empty-cell-preserved", {"parsed": [["", "x"], ["y", "z"]]}, "EXECUTED") is True
    assert accepts("nested-types-preserved", {"parsed": {"items": [1, None, False], "child": {"ok": True}}}, "EXECUTED") is True
    assert accepts("single-nonascii", {"parsed": "ñ", "raw": '"ñ"'}, "EXECUTED") is True
    assert accepts("duplicate-equal-values", {"duplicate_detected": True, "deterministic": True}, "EXECUTED") is True
    assert accepts("valid-json-accepted", {"rejected_count": 0, "rejected": []}, "EXECUTED") is True
    assert accepts("empty-object-canonical", {"same": True, "canonical": "{}"}, "EXECUTED") is True
    assert accepts("single-byte-frame", {"length": 1, "checksum": 255}, "EXECUTED") is True
    assert accepts("exact-power-boundary", {"rows": [{"value": 16777216, "exact": True}]}, "EXECUTED") is True
    assert accepts("zero-decimal-preserved", {"text": "0.00", "used_binary_float": False}, "EXECUTED") is True
    assert accepts("other-three-bytes", {"decoded_hex": "010203"}, "EXECUTED") is True
    assert accepts("invalid-padding-rejected", {"rejected": True, "error_recorded": True}, "EXECUTED") is True
    assert accepts("empty-sha256", {"digest_hex": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"}, "EXECUTED") is True
    assert accepts("empty-manifest-change", {"reproduced": True, "altered_changes": True, "digest": "44136fa355b3678a1146ad16f7e8649e94fb4fc21fe77e8310c060f61caaff8a"}, "EXECUTED") is True


def test_fifo_factorial_path_and_ipv6_independent_oracles():
    from metagente_luna_s3.batch3_oracle import stated_prefix, two_compressions
    from metagente_luna_s3.batch4_oracle import escapes
    from metagente_luna_s3.batch5_oracle import named_order, reference_factorials

    assert named_order({"values": ["C", "B", "A"]}, {"order": ["C", "B", "A"], "remaining": 0})["ok"] is True
    assert reference_factorials({"values": [-1]}, {"rejected": True, "negative_rejected": True})["ok"] is True
    assert reference_factorials({"values": [0]}, {"rejected": False, "values": [1], "negative_rejected": True})["ok"] is True
    assert escapes({"requested": "escape"}, {"blocked": True, "bytes_read": 0, "opened_outside": False, "operation": "simulated-download", "reason": "symlink-escapes"})["ok"] is True
    assert escapes({"requested": "inside-link"}, {"blocked": False, "bytes_read": 7, "opened_outside": False, "operation": "simulated-download", "reason": "internal-link"})["ok"] is True
    assert two_compressions({"address": "not-an-ipv6-address"}, {"accepted": False})["ok"] is True
    assert two_compressions({"address": "::"}, {"accepted": True})["ok"] is True
    assert stated_prefix({"cidr": "2001:db8::1/129"}, {"rejected": True})["ok"] is True
    assert stated_prefix({"cidr": "2001:db8::1/128"}, {"rejected": False, "prefix": "2001:db8::1/128"})["ok"] is True


def test_scientific_and_evaluation_independent_oracles():
    from metagente_luna_s3.batch3_oracle import harmonic, rates, stated_ratio
    from metagente_luna_s3.batch5_oracle import sign_change, statistics_variance

    assert stated_ratio({"numerator": 80, "denominator": 0}, {"rejected": True})["ok"] is True
    assert stated_ratio({"numerator": 0, "denominator": 1}, {"rejected": False, "value": 0.0, "denominator": 1})["ok"] is True
    assert rates({"true_positive": 0, "false_positive": 0, "false_negative": 1}, {"rejected": True})["ok"] is True
    assert rates({"true_positive": 1, "false_positive": 0, "false_negative": 0}, {"rejected": False, "precision": 1.0, "recall": 1.0})["ok"] is True
    assert harmonic({"precision": 0.0, "recall": 0.0}, {"rejected": True})["ok"] is True
    assert harmonic({"precision": 1.0, "recall": 1.0}, {"rejected": False, "f1": 1.0})["ok"] is True
    assert sign_change({"low": 2.0, "high": 3.0}, {"rejected": True})["ok"] is True
    assert statistics_variance({"values": []}, {"rejected": True})["ok"] is True
    assert statistics_variance({"values": [5]}, {"rejected": False, "population": 0.0, "sample": None})["ok"] is True


def test_newton_and_quadrature_oracles_are_independent():
    from metagente_luna_s3.batch4_oracle import half, one_third
    from metagente_luna_s3.batch5_oracle import library_root

    assert library_root({"initial": 1.0, "target": -1.0}, {"rejected": True})["ok"] is True
    assert library_root({"initial": 1.0, "target": 1.0}, {"rejected": False, "root": 1.0, "residual": 0.0})["ok"] is True
    assert half({"panels": 1}, {"rejected": False, "value": 0.5, "method": "trapezoidal", "panels": 1, "weights": [1, 1], "points": [0.0, 1.0]})["ok"] is True
    assert one_third({"panels": 2}, {"rejected": False, "value": 1 / 3, "method": "simpson", "panels": 2, "weights": [1, 4, 1], "points": [0.0, 0.25, 1.0]})["ok"] is True


def test_newton_and_quadrature_controls_are_adjudicated():
    assert accepts("newton-negative-target-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("newton-unit-root-boundary", {"rejected": False, "root": 1.0, "residual": 0.0}, "EXECUTED") is True
    # Zero panels violate the input schema, so rejection occurs before an
    # operation result exists. It must not be represented as EXECUTED.
    assert accepts("trapezoid-zero-panels-rejected", None, "REJECTED") is True
    assert accepts("trapezoid-zero-panels-rejected", {"rejected": True}, "EXECUTED") is False
    assert accepts("trapezoid-single-panel-boundary", {"rejected": False, "value": 0.5, "panels": 1}, "EXECUTED") is True
    assert accepts("simpson-odd-panels-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("simpson-minimum-even-boundary", {"rejected": False, "value": 1 / 3, "panels": 2}, "EXECUTED") is True


def test_scientific_and_evaluation_controls_are_adjudicated():
    assert accepts("cube-no-sign-change-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("cube-tight-boundary", {"rejected": False, "low": 1.2599210499, "high": 1.259921050}, "EXECUTED") is True
    assert accepts("variance-empty-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("variance-singleton-boundary", {"rejected": False, "population": 0, "sample": None}, "EXECUTED") is True
    assert accepts("ratio-zero-denominator-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("ratio-zero-numerator-boundary", {"rejected": False, "value": 0, "denominator": 1}, "EXECUTED") is True
    assert accepts("precision-zero-denominator-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("precision-perfect-boundary", {"rejected": False, "precision": 1, "recall": 1}, "EXECUTED") is True
    assert accepts("f1-zero-denominator-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("f1-perfect-boundary", {"rejected": False, "f1": 1}, "EXECUTED") is True


def test_lexer_telemetry_and_numeric_controls_are_accepted():
    assert accepts("empty-token-stream", {"tokens": []}, "EXECUTED") is True
    assert accepts("increment-negative-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("increment-zero-boundary", {"rejected": False, "completed": 0, "failed": 0, "ids": []}, "EXECUTED") is True
    assert accepts("request-negative-count-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("request-single-success-boundary", {"rejected": False, "availability": 1.0, "successes": 1, "failures": 0, "total": 1}, "EXECUTED") is True
    assert accepts("sqrt-negative-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("sqrt-zero-boundary", {"rejected": False, "estimate": 0.0, "residual": 0.0}, "EXECUTED") is True
    assert accepts("sum-negative-count-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("sum-zero-boundary", {"rejected": False, "naive": 1.0, "kahan": 1.0}, "EXECUTED") is True


def test_lexer_metrics_and_numerical_oracles_cover_new_boundaries():
    from metagente_luna_s3.batch4_oracle import counted, request_counts
    from metagente_luna_s3.batch5_oracle import decimal_total, library_sqrt
    from metagente_luna_s3.more_oracle import token_vector

    assert token_vector({"text": ""}, {"tokens": []})["ok"] is True
    assert counted({"times": -1}, {"rejected": True})["ok"] is True
    assert counted({"times": 0}, {"rejected": False, "ids": [], "completed": 0, "failed": 0})["ok"] is True
    assert request_counts({"successes": 99, "failures": -1}, {"rejected": True})["ok"] is True
    assert request_counts({"successes": 1, "failures": 0}, {"rejected": False, "statuses": [200], "availability": 1.0})["ok"] is True
    assert library_sqrt({"value": -1.0}, {"rejected": True})["ok"] is True
    assert library_sqrt({"value": 0.0}, {"rejected": False, "estimate": 0.0, "residual": 0.0})["ok"] is True
    assert decimal_total({"start": 1.0, "increment": 1e-8, "count": -1}, {"rejected": True})["ok"] is True
    assert decimal_total({"start": 1.0, "increment": 1e-8, "count": 0}, {"rejected": False, "naive": 1.0, "kahan": 1.0})["ok"] is True


def test_index_ipv6_mask_and_threshold_independent_oracles():
    from metagente_luna_s3.batch3_oracle import fever_rule, stated_prefix
    from metagente_luna_s3.batch5_oracle import library_v6, one_run, refused_index

    assert refused_index({"length": -1}, {"out_of_range": True, "reads": 0, "length": 0})["ok"] is True
    assert library_v6({"address": "not-an-ipv6-address"}, {"rejected": True})["ok"] is True
    assert library_v6({"address": "::"}, {"rejected": False, "expanded": "0000:0000:0000:0000:0000:0000:0000:0000", "integer": 0})["ok"] is True
    assert one_run({"mask": "255.0.0.255"}, {"rejected": True, "contiguous": False, "bits": "11111111000000000000000011111111"})["ok"] is True
    assert one_run({"mask": "255.255.255.255"}, {"rejected": False, "contiguous": True, "bits": "1" * 32})["ok"] is True
    assert stated_prefix({"cidr": "2001:db8::1/129"}, {"rejected": True})["ok"] is True
    assert fever_rule({"low": 38, "high": 38, "limit": 38}, {"at_or_below": True, "above": False})["ok"] is True
    assert fever_rule({"low": 38.1, "high": 38.1, "limit": 38}, {"at_or_below": False, "above": True})["ok"] is True


def test_index_ipv6_mask_and_threshold_control_expectations():
    assert accepts("negative-length-no-read", {"out_of_range": True, "reads": 0, "length": 0}, "EXECUTED") is True
    assert accepts("zero-length-no-read", {"out_of_range": True, "reads": 0, "length": 0}, "EXECUTED") is True
    assert accepts("expanded-invalid-ipv6-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("ipv6-zero-boundary", {"rejected": False, "expanded": "0000:0000:0000:0000:0000:0000:0000:0000", "integer": 0}, "EXECUTED") is True
    assert accepts("invalid-mask-rejected", {"rejected": True, "contiguous": False}, "EXECUTED") is True
    assert accepts("all-ones-mask-valid", {"rejected": False, "contiguous": True, "bits": "1" * 32}, "EXECUTED") is True
    assert accepts("threshold-equality-no-fire", {"at_or_below": True, "above": False}, "EXECUTED") is True
    assert accepts("threshold-above-fires", {"at_or_below": False, "above": True}, "EXECUTED") is True


def test_fifo_factorial_path_and_ipv6_controls_are_adjudicated():
    assert accepts("fifo-reversed-order", {"order": ["C", "B", "A"], "remaining": 0}, "EXECUTED") is True
    assert accepts("fifo-singleton", {"order": ["A"], "remaining": 0}, "EXECUTED") is True
    assert accepts("factorial-negative-rejected", {"rejected": True, "negative_rejected": True}, "EXECUTED") is True
    assert accepts("factorial-zero-boundary", {"rejected": False, "values": [1]}, "EXECUTED") is True
    assert accepts("symlink-escape-blocked", {"blocked": True, "bytes_read": 0, "reason": "symlink-escapes"}, "EXECUTED") is True
    assert accepts("internal-symlink-allowed", {"blocked": False, "bytes_read": 7, "reason": "internal-link"}, "EXECUTED") is True
    assert accepts("malformed-ipv6-rejected", {"accepted": False}, "EXECUTED") is True
    assert accepts("ipv6-unspecified-accepted", {"accepted": True}, "EXECUTED") is True
    assert accepts("invalid-prefix-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("host-prefix-boundary", {"network": "192.0.2.130", "broadcast": "192.0.2.130"}, "EXECUTED") is True
    assert accepts("ipv6-prefix-rejected", {"rejected": True}, "EXECUTED") is True
    assert accepts("ipv6-host-prefix", {"rejected": False, "prefix": "2001:db8::1/128"}, "EXECUTED") is True


def test_numerical_oracles_cover_invalid_norm_and_pearson_zero_variance():
    from metagente_luna_s3.batch3_oracle import thirteen
    from metagente_luna_s3.batch4_oracle import correlation

    assert thirteen({"components": ["3"]}, {"rejected": True, "reason": "components must be integers"})["ok"] is True
    assert thirteen({"components": []}, {"norm": 0, "square": 0})["ok"] is True
    assert correlation({"left": [1, 1, 1], "right": [1, 2, 3]}, {"value": None, "error": "zero-variance"})["ok"] is True


def test_unicode_control_oracles_cover_distinct_normalization_edges():
    from metagente_luna_s3.d01_oracle import nfc_table, nfd_table, nfkc_table

    assert nfc_table({"decomposed": "e\u0301", "composed": "e"}, {"same_nfc": False, "nfc": "é"})["ok"] is True
    assert nfd_table({"composed": "ñ"}, {"codepoints": ["U+006E", "U+0303"]})["ok"] is True
    assert nfkc_table({"text": "Ａ"}, {"compatibility": "A", "preserves_original_form": False})["ok"] is True


def test_independent_oracles_cover_empty_decimal_and_empty_sha256_vectors():
    from metagente_luna_s3.d01_oracle import nist_abc
    from metagente_luna_s3.more_oracle import decimal_literal

    digest = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert nist_abc({"text": ""}, {"digest_hex": digest})["ok"] is True
    assert decimal_literal({"text": "0.00"}, {"text": "0.00", "used_binary_float": False})["ok"] is True


def test_serialization_controls_cover_csv_xml_binary_compression_and_manifest_edges():
    assert accepts("two-records", {"records": 2, "fields": ["a", "1"]}, "EXECUTED") is True
    assert accepts("predefined-entity-set", {"text": "<>&", "external_expanded": False}, "EXECUTED") is True
    assert accepts("self-closing-accepted", {"rejected": False}, "EXECUTED") is True
    assert accepts("all-truncated", {"all_rejected": True, "rejected_lengths": [0, 1, 2, 3]}, "EXECUTED") is True
    assert accepts("empty-oversize-rejected", {"rejected": True, "allocated_declared_length": False}, "EXECUTED") is True
    assert accepts("field-present", {"absent": False, "null": True, "empty": True}, "EXECUTED") is True
    assert accepts("empty-payload-roundtrip", {"match": True, "compressed_differs": True}, "EXECUTED") is True
    assert accepts("empty-stream-corrupt", {"corruption_detected": True, "integrity_claimed": False}, "EXECUTED") is True
    assert accepts("unknown-signature", {"detected": "unknown", "extension_matches_content": False}, "EXECUTED") is True
    assert accepts("empty-stream-corrupt", {"corruption_detected": True, "integrity_claimed": False}, "BLOCKED") is False


def test_duplicate_and_bracket_controls_cover_negative_and_empty_boundaries():
    assert accepts("no-duplicates", {"duplicates": []}, "EXECUTED") is True
    assert accepts("single-duplicate", {"duplicates": [5]}, "EXECUTED") is True
    assert accepts("mismatched-brackets", {"results": [{"text": "([)]", "accepted": False}]}, "EXECUTED") is True
    assert accepts("empty-brackets", {"results": [{"text": "", "accepted": True}]}, "EXECUTED") is True
    assert accepts("empty-brackets", {"results": [{"text": "", "accepted": True}]}, "BLOCKED") is False


def test_search_controls_distinguish_absence_and_first_boundary_position():
    assert accepts("first-match-absent", {"index": None, "duplicates": []}, "EXECUTED") is True
    assert accepts("first-match-absent", {"index": 1, "duplicates": [1]}, "EXECUTED") is False
    assert accepts("first-match-singleton", {"index": 0, "duplicates": [0]}, "EXECUTED") is True
    assert accepts("binary-find-absent", {"index": None, "comparisons": 5}, "EXECUTED") is True
    assert accepts("binary-find-first", {"index": 0, "comparisons": 5}, "EXECUTED") is True
    assert accepts("binary-find-first", {"index": 0, "comparisons": 6}, "EXECUTED") is False
    assert accepts("binary-find-absent", {"index": None, "comparisons": 5}, "BLOCKED") is False


def test_empty_roundtrip_control_cannot_pass_without_successful_execution():
    assert accepts("empty-roundtrip", {"bytes_hex": ""}, "EXECUTED") is True
    assert accepts("empty-roundtrip", {"bytes_hex": ""}, "BLOCKED") is False
    assert accepts("empty-roundtrip", {"visible": ""}, "INCONCLUSIVE") is False


def test_elf_magic_identification_ignores_a_misleading_jpg_extension():
    from metagente_luna_s4.runner import execute
    arguments = {"name": "sample.jpg", "payload_hex": "7f454c46020101000000000000000000"}
    result = execute("magic_bytes", arguments, "MGL5-INF-0052")
    assert result["execution_status"] == "EXECUTED"
    assert result["observed"] == {"extension": "jpg", "detected": "elf", "extension_matches_content": False}
    assert accepts("unknown-signature", {"detected": "unknown", "extension_matches_content": False}, "EXECUTED") is True
    assert accepts("elf-extension-match", {"detected": "elf", "extension_matches_content": True}, "EXECUTED") is True


def test_new_source_grounded_controls_match_their_contracts():
    from metagente_luna_s4.controls import accepts

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
        assert accepts(expect, observed, status) is True, expect
        assert accepts(expect, observed, "BLOCKED") is False, expect


def test_ieee754_and_float_gap_controls_are_checked_by_primary_adjudicator():
    from metagente_luna_s4.controls import accepts

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
        assert accepts(expect, observed, "EXECUTED") is True, expect
        assert accepts(expect, observed, "BLOCKED") is False, expect


def test_numerical_fit_and_integrator_controls():
    from metagente_luna_s3.batch5_exec import euler_decay, exact_line, rk4_decay
    from metagente_luna_s3.batch5_oracle import series_exp, smaller_step, two_points
    from metagente_luna_s4.controls import accepts

    line_args = {"xs": [0, 1, 2], "slope": -1, "intercept": 0}
    line = exact_line(**line_args)
    assert two_points(line_args, line)["ok"] is True
    assert accepts("line-negative-slope", line, "EXECUTED") is True

    euler_args = {"coarse_step": 0.05, "fine_step": 0.1}
    euler = euler_decay(**euler_args)
    assert smaller_step(euler_args, euler)["ok"] is False
    assert accepts("euler-step-order-reversed", euler, "FAIL") is True

    assert rk4_decay(2.0)["rejected"] is True
    assert series_exp({"step": 2.0}, rk4_decay(2.0))["ok"] is True



def test_d01_numeric_base64_null_and_manifest_controls_have_independent_adjudication():
    from metagente_luna_s3.more_exec import (
        base64_bytes,
        base64_reject,
        decimal_text,
        float32_exactness,
        manifest_hash,
        three_states,
    )
    from metagente_luna_s3.more_oracle import (
        b64_table,
        decimal_literal,
        f32_table,
        stable_digest,
        state_table,
    )
    from metagente_luna_s4.independent_validator import _independent_control_accepts

    cases = [
        ("float32-inexact-identified", float32_exactness(values=[16777217]), "EXECUTED"),
        ("float32-exact-transition", float32_exactness(values=[16777216]), "EXECUTED"),
        ("decimal-invalid-rejected", decimal_text("0.10x"), "EXECUTED"),
        ("known-key-not-absent", three_states({"b": None, "c": ""}, "b"), "EXECUTED"),
        ("nonempty-field-not-empty", three_states({"b": None, "c": "x"}, "a"), "EXECUTED"),
        ("base64-invalid-hex-rejected", base64_bytes("0g"), "EXECUTED"),
        ("valid-base64-accepted", base64_reject("AA=="), "FAIL"),
        ("unchanged-manifest-stable", manifest_hash({"name": "luna"}, {"name": "luna"}), "EXECUTED"),
    ]
    for expectation, observed, lifecycle in cases:
        assert accepts(expectation, observed, lifecycle) is True
        assert _independent_control_accepts(expectation, observed, lifecycle) is True

    normal_float = {"values": [16777216, 16777217, 16777219]}
    assert f32_table(normal_float, float32_exactness(**normal_float))["ok"] is True
    normal_decimal = {"text": "0.10"}
    assert decimal_literal(normal_decimal, decimal_text(**normal_decimal))["ok"] is True
    normal_states = {"present": {"b": None, "c": ""}, "absent_key": "a"}
    assert state_table(normal_states, three_states(**normal_states))["ok"] is True
    normal_base64 = {"payload_hex": "00ff01"}
    assert b64_table(normal_base64, base64_bytes(**normal_base64))["ok"] is True
    normal_hash = {"document": {"name": "luna", "version": 1}, "altered": {"name": "luna", "version": 2}}
    assert stable_digest(normal_hash, manifest_hash(**normal_hash))["ok"] is True
    invalid_decimal = {"text": "0.10x"}
    assert decimal_literal(invalid_decimal, decimal_text(**invalid_decimal))["ok"] is True
    invalid_hex = {"payload_hex": "0g"}
    assert b64_table(invalid_hex, base64_bytes(**invalid_hex))["ok"] is True



def test_d01_protobuf_schema_compatibility_and_cbor_roundtrip_cases():
    from metagente_luna_s3.more_exec import (
        cbor_roundtrip,
        protobuf_old_reader,
        schema_migrate,
        schema_unknown_field,
    )
    from metagente_luna_s3.more_oracle import (
        cbor_vector_oracle,
        protobuf_wire_oracle,
        schema_v2_oracle,
        unknown_field_oracle,
    )
    from metagente_luna_s4.controls import accepts
    from metagente_luna_s4.independent_validator import _independent_control_accepts

    protobuf = {"wire_hex": "080712036e6577"}
    observed_protobuf = protobuf_old_reader(**protobuf)
    assert protobuf_wire_oracle(protobuf, observed_protobuf)["ok"] is True
    assert observed_protobuf["unknown_fields"] == [2]
    protobuf_negative = protobuf_old_reader("08071205")
    assert accepts("protobuf-malformed-rejected", protobuf_negative, "EXECUTED") is True
    assert _independent_control_accepts("protobuf-malformed-rejected", protobuf_negative, "EXECUTED") is True

    migration = {"document": {"version": 1, "name": "Luna", "count": 3}}
    assert schema_v2_oracle(migration, schema_migrate(**migration))["ok"] is True
    schema_negative = schema_migrate({"version": 0, "name": "Luna", "count": 3})
    assert accepts("schema-v0-rejected", schema_negative, "EXECUTED") is True
    assert _independent_control_accepts("schema-v0-rejected", schema_negative, "EXECUTED") is True

    unknown = {"record": {"name": "Luna", "version": 2, "extra": "future"}, "known_fields": ["name", "version"]}
    assert unknown_field_oracle(unknown, schema_unknown_field(**unknown))["ok"] is True
    unknown_negative = schema_unknown_field({"name": 7, "version": 2, "extra": "future"}, ["name", "version"])
    assert accepts("known-field-type-rejected", unknown_negative, "EXECUTED") is True
    assert _independent_control_accepts("known-field-type-rejected", unknown_negative, "EXECUTED") is True

    document = {"name": "Luna", "count": 2, "enabled": True, "items": [1, None, False]}
    cbor_args = {"document": document}
    cbor_observed = cbor_roundtrip(**cbor_args)
    assert cbor_vector_oracle(cbor_args, cbor_observed)["ok"] is True
    cbor_negative = cbor_roundtrip({"name": 1.5})
    assert accepts("cbor-unsupported-value-rejected", cbor_negative, "EXECUTED") is True
    assert _independent_control_accepts("cbor-unsupported-value-rejected", cbor_negative, "EXECUTED") is True
    assert cbor_vector_oracle({"document": {}}, cbor_roundtrip({}))["ok"] is True


def test_elf_header_reports_class_endian_architecture_and_type_with_fixed_oracle():
    from metagente_luna_s3.more_exec import elf_header
    from metagente_luna_s3.more_oracle import elf_header_oracle
    from metagente_luna_s4.controls import accepts
    from metagente_luna_s4.independent_validator import _independent_control_accepts

    normal = {"payload_hex": "7f454c4602010100000000000000000002003e000100000000004000000000004000000000000000000000000000000000000000400038000000400000000000"}
    observed = elf_header(**normal)
    assert elf_header_oracle(normal, observed)["ok"] is True
    truncated = elf_header(normal["payload_hex"][:-2])
    assert accepts("elf-truncated-header", truncated, "EXECUTED") is True
    assert _independent_control_accepts("elf-truncated-header", truncated, "EXECUTED") is True
    boundary = {"payload_hex": "7f454c4602010100000000000000000001003e000100000000000000000000000000000000000000000000000000000000000000400038000000400000000000"}
    boundary_observed = elf_header(**boundary)
    assert elf_header_oracle(boundary, boundary_observed)["ok"] is True
    assert accepts("elf-rel-boundary", boundary_observed, "EXECUTED") is True
    assert _independent_control_accepts("elf-rel-boundary", boundary_observed, "EXECUTED") is True
