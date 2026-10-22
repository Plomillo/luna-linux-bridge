import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from scripts import cajita_luna_governed_preflight as ctl
from scripts import cajita_luna_puac2_gates as gates


def keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode("ascii")
    public_pem = private.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("ascii")
    return private_pem, public_pem


def make_root(base: Path, with_oversized_sparse_file: bool = False) -> Path:
    root = base / "Cajita de Luna"
    root.mkdir()
    for domain in ctl.EXPECTED_DOMAINS:
        (root / domain).mkdir(parents=True)
    edge = root / ctl.EDGE_ARCHIVE_REL
    edge.parent.mkdir(parents=True, exist_ok=True)
    edge.write_bytes(b"edge-test-fixture-not-a-real-profile")
    edge.with_suffix(".sha256").write_text(
        f"{hashlib.sha256(edge.read_bytes()).hexdigest()}  {edge.name}\n",
        encoding="utf-8",
    )
    edge.with_suffix(".audit.jsonl").write_text('{"fixture":true}\n', encoding="utf-8")
    registry = root / "RUNTIME_CANDIDATE_V1" / "registry.json"
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(json.dumps({"artifacts": []}), encoding="utf-8")
    if with_oversized_sparse_file:
        sparse = root / "6. Sistema Inteligente" / "oversized-sparse-test.bin"
        with sparse.open("wb") as stream:
            stream.truncate(ctl.CAP_BYTES + 1)
    return root


class CajitaPUAC2GateTests(unittest.TestCase):
    def test_signed_envelope_verifies_exact_canonical_payload(self):
        private, public = keypair()
        payload = {"schema": gates.G23_SCHEMA, "status": "PASS",
                   "validator_id": "independent-g23", "scope": "CAJITA_DE_LUNA_EXACT_TREE"}
        envelope = gates.sign_envelope(payload, private, "independent-g23", gates.G23_ENVELOPE_SCHEMA)
        verified, errors = gates.verify_envelope(envelope, public, gates.G23_ENVELOPE_SCHEMA)
        self.assertEqual(errors, [])
        self.assertEqual(verified, payload)

    def test_mutated_signed_payload_is_rejected(self):
        private, public = keypair()
        payload = {"status": "PASS", "validator_id": "g23"}
        envelope = gates.sign_envelope(payload, private, "g23", gates.G23_ENVELOPE_SCHEMA)
        envelope["payload"]["status"] = "CERTIFIED"
        verified, errors = gates.verify_envelope(envelope, public, gates.G23_ENVELOPE_SCHEMA)
        self.assertIsNone(verified)
        self.assertTrue(any("HASH_MISMATCH" in item for item in errors) or "ED25519_SIGNATURE_INVALID" in errors)

    def test_hold_g23_never_becomes_certified_g24(self):
        g23_private, g23_public = keypair()
        g24_private, _ = keypair()
        commit = "a" * 40
        payload = {
            "schema": gates.G23_SCHEMA, "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "validator_id": "independent-g23", "producer_id": "CUSTOSZ_V9",
            "candidate_commit": commit, "subject_tree_sha256": None,
            "tree_bytes_at_validation": ctl.CAP_BYTES + 1,
            "projected_tree_bytes_with_reserve": ctl.CAP_BYTES + 100,
            "gates_checked": [], "blockers": ["FINAL_TREE_PLUS_CERTIFICATE_RESERVE_EXCEEDS_CAP"],
        }
        envelope = gates.sign_envelope(payload, g23_private, "independent-g23", gates.G23_ENVELOPE_SCHEMA)
        with tempfile.TemporaryDirectory() as temp:
            g23_path, g24_path = Path(temp) / "g23.json", Path(temp) / "g24.json"
            g23_path.write_text(json.dumps(envelope), encoding="utf-8")
            result = gates.issue_g24(g23_path, g24_path, g23_public, g24_private,
                                     "independent-g24", "CUSTOSZ_V9", commit, "b" * 64)
        self.assertEqual(result["payload"]["status"], "HOLD")
        self.assertFalse(result["payload"]["certification_granted"])
        self.assertTrue(result["payload"]["blockers"])

    def test_g23_and_g24_identity_collision_causes_hold(self):
        g23_private, g23_public = keypair()
        g24_private, _ = keypair()
        commit = "c" * 40
        payload = {
            "schema": gates.G23_SCHEMA, "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "validator_id": "same-identity", "producer_id": "CUSTOSZ_V9",
            "candidate_commit": commit, "subject_tree_sha256": "d" * 64,
            "tree_bytes_at_validation": 100, "projected_tree_bytes_with_reserve": 200,
            "gates_checked": [], "blockers": ["FIXTURE_HOLD"],
        }
        envelope = gates.sign_envelope(payload, g23_private, "same-identity", gates.G23_ENVELOPE_SCHEMA)
        with tempfile.TemporaryDirectory() as temp:
            path, output = Path(temp) / "g23.json", Path(temp) / "g24.json"
            path.write_text(json.dumps(envelope), encoding="utf-8")
            result = gates.issue_g24(path, output, g23_public, g24_private, "same-identity",
                                     "CUSTOSZ_V9", commit, "d" * 64)
        self.assertEqual(result["payload"]["status"], "HOLD")
        self.assertIn("G23_G24_IDENTITIES_NOT_DISTINCT", result["payload"]["blockers"])

    def test_known_size_violation_short_circuits_before_payload_hashing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp), with_oversized_sparse_file=True)
            report = gates.final_evidence(root)
            self.assertEqual(report["status"], "HOLD")
            self.assertGreater(report["tree_bytes_at_validation"], ctl.CAP_BYTES)
            self.assertIn("FINAL_TREE_PLUS_CERTIFICATE_RESERVE_EXCEEDS_CAP", report["blockers"])
            self.assertIsNone(report["subject_tree_sha256"])

    def test_dispatch_is_denied_before_gh_when_evidence_is_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp))
            report = gates.dispatch_g23_g24(
                root, "e" * 40, "f" * 64, "Plomillo/luna-linux-bridge",
                ".github/workflows/cajita-luna-puac2-g23-g24.yml", "main",
            )
            self.assertEqual(report["decision"], "HOLD")
            self.assertFalse(report["dispatched"])
            self.assertIn("CERTIFICATION_DISPATCH_DENIED_BY_G23_PREFLIGHT", report["blockers"])

    def test_persist_bundle_does_not_write_over_cap_tree(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp), with_oversized_sparse_file=True)
            with self.assertRaisesRegex(ValueError, "EXCEEDS_CAP"):
                gates.persist_bundle(root, Path(temp) / "absent-g23.json", Path(temp) / "absent-g24.json",
                                     "test-run", "a" * 40, "CUSTOSZ_V9")
            self.assertFalse((root / ".cajita-optimization-candidates" / "evidence").exists())

    def test_final_verifier_holds_overcap_without_claiming_certificate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = make_root(Path(temp), with_oversized_sparse_file=True)
            result = gates.verify_release(root, Path(temp) / "missing-manifest.json", "", "")
            self.assertEqual(result["decision"], "HOLD")
            self.assertEqual(result["certification_status"], "NOT_GRANTED")
            self.assertGreater(result["overage_bytes"], 0)

    def test_generated_evidence_is_excluded_from_subject_hash_but_not_size_accounting(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "payload.bin").write_bytes(b"payload")
            subject1, count1, bytes1 = ctl.candidate_tree_digest(root)
            evidence = root / ".cajita-optimization-candidates" / "evidence"
            evidence.mkdir(parents=True)
            (evidence / "signed-receipt.json").write_text('{"status":"PASS"}', encoding="utf-8")
            subject2, count2, bytes2 = ctl.candidate_tree_digest(root)
            self.assertEqual(subject1, subject2)
            self.assertEqual(count1, 1)
            self.assertEqual(bytes1, 7)
            self.assertEqual(count2, 1)
            self.assertEqual(bytes2, 7)
            self.assertGreater(ctl.scan_tree(root)["total_bytes"], bytes2)


    def test_valid_g23_and_distinct_g24_can_certify_the_same_subject(self):
        g23_private, g23_public = keypair()
        g24_private, g24_public = keypair()
        commit = "9" * 40
        subject = "8" * 64
        evidence_hashes = {
            "registry_sha256": "1" * 64,
            "reconciliation_sha256": "2" * 64,
            "frozen_manifest_sha256": "3" * 64,
            "optimization_plan_sha256": "4" * 64,
            "execution_manifest_sha256": "5" * 64,
            "functional_manifest_sha256": "6" * 64,
            "gate_matrix_sha256": "7" * 64,
            "independent_tests_sha256": "a" * 64,
        }
        payload = {
            "schema": gates.G23_SCHEMA,
            "status": "PASS",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "validator_id": "independent-g23",
            "producer_id": "CUSTOSZ_V9",
            "candidate_commit": commit,
            "subject_tree_sha256": subject,
            "tree_bytes_at_validation": 100_000_000,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": 100_000_000 + ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "gates_checked": ctl.GATE_IDS_22,
            "evidence_hashes": evidence_hashes,
            "blockers": [],
            "decision_utc": gates.utc_now(),
        }
        envelope = gates.sign_envelope(payload, g23_private, "independent-g23", gates.G23_ENVELOPE_SCHEMA)
        with tempfile.TemporaryDirectory() as temp:
            g23_path, g24_path = Path(temp) / "g23.json", Path(temp) / "g24.json"
            g23_path.write_text(json.dumps(envelope), encoding="utf-8")
            result = gates.issue_g24(g23_path, g24_path, g23_public, g24_private,
                                     "independent-g24", "CUSTOSZ_V9", commit, subject)
            verified, errors = gates.verify_envelope(result, g24_public, gates.G24_ENVELOPE_SCHEMA)
        self.assertEqual(errors, [])
        self.assertEqual(verified["status"], "CERTIFIED")
        self.assertTrue(verified["certification_granted"])
        self.assertEqual(verified["subject_tree_sha256"], subject)
        self.assertEqual(verified["g23_envelope_sha256"], gates.digest_bytes(gates.canonical_json(envelope)))
        self.assertEqual(verified["certifier_id"], "independent-g24")
        self.assertEqual(result["status"], "SIGNED")
        self.assertEqual(envelope["status"], "SIGNED")
        self.assertNotEqual(result["signer_public_key_sha256"], envelope["signer_public_key_sha256"])



    def test_same_cryptographic_key_cannot_certify_both_g23_and_g24(self):
        g23_private, g23_public = keypair()
        commit = "7" * 40
        subject = "6" * 64
        payload = {
            "schema": gates.G23_SCHEMA,
            "status": "PASS",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "validator_id": "independent-g23",
            "producer_id": "CUSTOSZ_V9",
            "candidate_commit": commit,
            "subject_tree_sha256": subject,
            "tree_bytes_at_validation": 100_000_000,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": 100_000_000 + ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "gates_checked": ctl.GATE_IDS_22,
            "evidence_hashes": {
                "registry_sha256": "1" * 64,
                "reconciliation_sha256": "2" * 64,
                "frozen_manifest_sha256": "3" * 64,
                "optimization_plan_sha256": "4" * 64,
                "execution_manifest_sha256": "5" * 64,
                "functional_manifest_sha256": "6" * 64,
                "gate_matrix_sha256": "7" * 64,
                "independent_tests_sha256": "8" * 64,
            },
            "blockers": [],
            "decision_utc": gates.utc_now(),
        }
        envelope = gates.sign_envelope(payload, g23_private, "independent-g23", gates.G23_ENVELOPE_SCHEMA)
        with tempfile.TemporaryDirectory() as temp:
            g23_path, g24_path = Path(temp) / "g23.json", Path(temp) / "g24.json"
            g23_path.write_text(json.dumps(envelope), encoding="utf-8")
            result = gates.issue_g24(
                g23_path, g24_path, g23_public, g23_private,
                "independent-g24", "CUSTOSZ_V9", commit, subject,
            )
        self.assertEqual(result["payload"]["status"], "HOLD")
        self.assertIn("G23_G24_SIGNING_KEYS_NOT_DISTINCT", result["payload"]["blockers"])
        self.assertFalse(result["payload"]["certification_granted"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
