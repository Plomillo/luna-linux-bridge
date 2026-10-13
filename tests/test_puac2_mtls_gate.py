import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "puac2_mtls_gate", Path(__file__).parents[1] / "scripts" / "puac2_mtls_gate.py"
)
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)


def minimal_manifest():
    return {
        "schema": "PUAC2_MTLS_CERTIFICATION/1.0",
        "candidate_commit": "a" * 40,
        "submitter_id": "submitter",
        "evidence": {},
        "tests": {"status": "HOLD", "passed": 0, "failed": 0},
        "g23": {},
        "g24": {},
    }


def test_empty_manifest_fails_closed():
    code, reasons = gate.validate(minimal_manifest(), "", "")
    assert code == 3
    assert "G23_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED" in reasons
    assert "G24_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED" in reasons
    assert "TESTS_NOT_PROVEN_PASS" in reasons


def test_wrong_schema_is_rejected():
    manifest = minimal_manifest()
    manifest["schema"] = "anything"
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "SCHEMA_INVALID" in reasons


def test_malformed_hashes_are_rejected():
    manifest = minimal_manifest()
    manifest["evidence"] = {
        "input_sha256": "not-a-hash",
        "output_sha256": "0" * 64,
        "test_report_sha256": "0" * 64,
        "host_mtls_test_sha256": "0" * 64,
        "rollback_test_sha256": "0" * 64,
    }
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "HASH_INVALID:input_sha256" in reasons


def test_missing_g23_and_g24_never_certifies():
    manifest = minimal_manifest()
    manifest["tests"] = {"status": "PASS", "passed": 1, "failed": 0}
    code, reasons = gate.validate(manifest, "", "")
    assert code == 3
    assert "G23_ATTESTATION_MISSING" in reasons
    assert "G24_ATTESTATION_MISSING" in reasons
