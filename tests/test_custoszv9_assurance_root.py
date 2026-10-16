from __future__ import annotations
import hashlib
import importlib.util
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, PublicFormat, NoEncryption

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "custoszv9_gate_trust_root.py"
SPEC = importlib.util.spec_from_file_location("custoszv9_trusted_gate_test", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(gate)

def key_pair():
    key = Ed25519PrivateKey.generate()
    private = key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption()).decode("ascii")
    public = key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo).decode("ascii")
    return private, public

class TrustedGateTests(unittest.TestCase):
    def test_ed25519_signature_verifies_exact_canonical_payload(self):
        private, public = key_pair()
        payload = {"schema": "TEST/1.0", "candidate_commit_sha": "a" * 40, "decision": "HOLD"}
        record = gate.sign_record(payload, private, "trusted-validator")
        verified, errors = gate.verify_signed_record(record, public, "trusted-validator")
        self.assertEqual(errors, [])
        self.assertEqual(verified, payload)
        self.assertEqual(record["payload_sha256"], hashlib.sha256(gate.canonical_bytes(payload)).hexdigest())

    def test_signature_tampering_wrong_identity_and_wrong_key_fail(self):
        private, public = key_pair()
        _, other_public = key_pair()
        payload = {"schema": "TEST/1.0", "candidate_commit_sha": "b" * 40}
        record = gate.sign_record(payload, private, "G23")
        tampered = dict(record, payload=dict(payload, candidate_commit_sha="c" * 40))
        result, errors = gate.verify_signed_record(tampered, public, "G23")
        self.assertIsNone(result)
        self.assertIn("SIGNED_ATTESTATION_PAYLOAD_HASH_MISMATCH", errors)
        self.assertIn("ED25519_SIGNATURE_INVALID", errors)
        result, errors = gate.verify_signed_record(record, public, "G24")
        self.assertIsNone(result)
        self.assertIn("SIGNED_ATTESTATION_SIGNER_IDENTITY_MISMATCH", errors)
        result, errors = gate.verify_signed_record(record, other_public, "G23")
        self.assertIsNone(result)
        self.assertIn("SIGNED_ATTESTATION_PUBLIC_KEY_FINGERPRINT_MISMATCH", errors)
        self.assertIn("ED25519_SIGNATURE_INVALID", errors)

    def test_g23_g24_keys_and_identity_are_distinct(self):
        g23_private, g23_public = key_pair()
        g24_private, g24_public = key_pair()
        self.assertTrue(gate.public_keys_match(g23_private, g23_public))
        self.assertTrue(gate.public_keys_match(g24_private, g24_public))
        self.assertFalse(gate.public_keys_match(g23_private, g24_public))
        self.assertNotEqual(gate.public_key_sha256(g23_public), gate.public_key_sha256(g24_public))
        g23 = gate.sign_record({"candidate": "candidate-1"}, g23_private, "G23")
        _, errors = gate.verify_signed_record(g23, g24_public, "G23")
        self.assertTrue(errors)

    def test_g23_result_is_derived_from_complete_five_command_evidence(self):
        results = [
            {"name": name, "returncode": 0, "status": "PASS",
             "stdout_sha256": "d" * 64, "stderr_sha256": "e" * 64}
            for name in sorted(gate.EXPECTED_G23_COMMANDS)
        ]
        report = {"independent_execution_results": results, "failures": [],
                  "tested_scope_result": "PASS", "scoped_decision_admissible": True}
        passed, errors = gate.g23_report_consistency(report)
        self.assertTrue(passed)
        self.assertEqual(errors, [])
        report["independent_execution_results"] = results[:-1]
        passed, errors = gate.g23_report_consistency(report)
        self.assertFalse(passed)
        self.assertIn("G23_REQUIRED_COMMAND_SET_MISMATCH", errors)

    def test_a_green_tested_subscope_is_not_a_full_release(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn('"decision":"HOLD"', text)
        self.assertIn('"full_release_eligible":False', text)
        self.assertIn('"canonical_G23_status":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN"', text)

if __name__ == "__main__":
    unittest.main()
