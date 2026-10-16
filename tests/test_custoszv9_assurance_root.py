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

    def test_scoped_certificate_never_promotes_canonical_authority(self):
        text = SCRIPT.read_text(encoding="utf-8")
        self.assertIn("CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE", text)
        self.assertIn('"canonical_G01_G24_status":"HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN"', text)
        self.assertIn('"canonical_promotion":"NOT_AUTHORIZED"', text)
        self.assertIn('"operational_authorization":"NOT_GRANTED"', text)
        self.assertIn("--g23-attestation-verification", text)

    def test_g24_certifies_only_when_exact_package_g22_g23_and_attestation_evidence_pass(self):
        import json
        import tempfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            candidate = root / "candidate"
            candidate.mkdir()
            package = candidate / "CUSTOSZV9.pyz"
            package.write_bytes(b"scope-candidate-exact-bytes")
            package_sha = hashlib.sha256(package.read_bytes()).hexdigest()
            commit = "a" * 40
            trusted_sha = "b" * 40
            g22_path = root / "G22.json"
            g22 = {
                "schema": gate.G22_SCHEMA, "candidate_commit_sha": commit,
                "candidate_package_sha256": package_sha, "tested_scope_result": "PASS",
                "failures": [], "trusted_workflow_sha": trusted_sha,
                "local_puac_controls_status": "EVALUATED_FOR_DECLARED_SCOPE_ONLY"
            }
            gate.write(g22_path, g22)
            g23_path = root / "G23_UNSIGNED.json"
            g23 = {
                "schema": gate.G23_UNSIGNED_SCHEMA, "candidate_commit_sha": commit,
                "candidate_package_sha256": package_sha, "tested_scope_result": "PASS",
                "scoped_decision_admissible": True, "failures": [],
                "trusted_workflow_sha": trusted_sha, "validator_identity": "trusted-g23",
                "g22_record_sha256": gate.sha(g22_path),
                "independent_execution_results": [
                    {"name": name, "returncode": 0, "status": "PASS",
                     "stdout_sha256": "c" * 64, "stderr_sha256": "d" * 64}
                    for name in sorted(gate.EXPECTED_G23_COMMANDS)
                ]
            }
            gate.write(g23_path, g23)
            verified = root / "G23_ATTESTATION_VERIFICATION.json"
            verified.write_text(json.dumps({"attestation_verified": True}), encoding="utf-8")
            out = root / "CUSTOSZV9_CERTIFICATE.json"
            args = SimpleNamespace(
                candidate_dir=str(candidate), candidate_sha=commit,
                trusted_workflow_sha=trusted_sha, g22=str(g22_path),
                g23=str(g23_path), g23_attestation_verification=str(verified),
                out=str(out)
            )
            self.assertEqual(gate.g24(args), 0)
            cert = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(cert["package_scope_certified"])
            self.assertEqual(cert["decision"], "CERTIFIED_FOR_DECLARED_STANDALONE_SOFTWARE_SCOPE")
            self.assertEqual(cert["candidate_package_sha256"], package_sha)
            self.assertFalse(cert["full_release_eligible"])
            self.assertEqual(cert["canonical_G01_G24_status"], "HOLD_FULL_CANONICAL_SCOPE_NOT_PROVEN")
            self.assertEqual(cert["canonical_promotion"], "NOT_AUTHORIZED")

            # Any exact-byte mismatch must prevent even the scoped certificate.
            g23["candidate_package_sha256"] = "e" * 64
            gate.write(g23_path, g23)
            self.assertEqual(gate.g24(args), 0)
            held = json.loads(out.read_text(encoding="utf-8"))
            self.assertFalse(held["package_scope_certified"])
            self.assertEqual(held["decision"], "HOLD")
            self.assertTrue(held["failures"])

if __name__ == "__main__":
    unittest.main()
