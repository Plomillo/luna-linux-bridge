import os

from metagente_luna_s4.controls import accepts, run_controls
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
    assert all(row["control_status"] == "PRESENT" for row in defined)
    assert len(defined) == 74

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
