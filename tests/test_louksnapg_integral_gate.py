import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

MODULE = Path(__file__).resolve().parents[1] / "tools" / "louksnapg_integral_gate.py"
SPEC = importlib.util.spec_from_file_location("louksnapg_integral_gate", MODULE)
gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(gate)


class IntegralGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bundle = self.root / "LOUKSNAPG.md"
        self.bundle.write_bytes(b"candidate subject bytes for gate contract tests")
        self.sha = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.commit = "a" * 40
        self.private_key = Ed25519PrivateKey.generate()
        self.public_pem = self.private_key.public_key().public_bytes(
            serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode("ascii")
        self.evidence = self.valid_evidence()

    def sign_evidence(self, evidence):
        evidence.pop("g23", None)
        payload = {
            "schema": "LOUKSNAPG_G23_ATTESTATION_PAYLOAD/1.0",
            "status": "PASS",
            "scope": "LOUKSNAPG_INTEGRAL_FUNCTIONAL_VALIDATION",
            "candidate_commit": self.commit,
            "subject_bundle_sha256": self.sha,
            "evidence_manifest_sha256": hashlib.sha256(gate._canonical_json(evidence)).hexdigest(),
            "producer_id": "factory-worker",
            "validator_id": "independent-g23-validator",
        }
        payload_bytes = gate._canonical_json(payload)
        public_raw = self.private_key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )
        evidence["g23"] = {
            "schema": "LOUKSNAPG_G23_SIGNED/1.0",
            "status": "SIGNED",
            "signer_id": "independent-g23-validator",
            "signer_public_key_sha256": hashlib.sha256(public_raw).hexdigest(),
            "payload_sha256": hashlib.sha256(payload_bytes).hexdigest(),
            "signature_b64": base64.b64encode(self.private_key.sign(payload_bytes)).decode("ascii"),
            "payload": payload,
        }
        return evidence

    def valid_evidence(self):
        rows = []
        for target_id in gate.EXPECTED_TARGET_IDS:
            row = {
                "target_id": target_id,
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "exit_code": 0,
                "test_case_count": 3,
                "test_cases_passed": 3,
                "output_char_count": 8,
                "input_sha256": "1" * 64,
                "output_sha256": "2" * 64,
                "runtime_sha256": "3" * 64,
                "module_tree_sha256": "4" * 64,
                "synthetic_only": False,
            }
            if target_id in gate.MODEL_TARGETS:
                upstream_ids = dict(gate.OFFICIAL_MODEL_IDS)
                upstream_ids["D06_ANALISIS_AVANZADO"] = "Qwen/Qwen3-8B"
                row.update({
                    "model_load_status": "PASS",
                    "model_inference_observed": True,
                    "weight_sha256": "5" * 64,
                    "upstream_model_id": upstream_ids[target_id],
                    "upstream_source_url": gate.OFFICIAL_SOURCE_URLS[target_id],
                    "upstream_revision_sha256": "6" * 40,
                })
            rows.append(row)
        evidence = {
            "schema": gate.SCHEMA,
            "source_commit": self.commit,
            "bundle_sha256": self.sha,
            "execution_mode": "REAL_RUNTIME_EXECUTION",
            "synthetic_only": False,
            "functional_status": "PASS_ALL_21_REQUIRED_TARGETS",
            "semantic_quality_status": "PASS",
            "host_matrix_status": "PASS",
            "rollback_status": "PASS",
            "axiom_binding_status": "PASS",
            "block_binding_status": "PASS",
            "target_results": rows,
        }
        return self.sign_evidence(evidence)

    def evaluate(self, evidence=None, public_key=None):
        return gate.evaluate_evidence(
            self.evidence if evidence is None else evidence,
            self.sha,
            self.commit,
            self.public_pem if public_key is None else public_key,
        )

    def test_complete_subject_bound_signed_evidence_is_eligible(self):
        result = self.evaluate()
        self.assertEqual(result["decision"], "PASS")
        self.assertTrue(result["eligible_for_g24"])
        self.assertEqual(result["observed_target_count"], 21)

    def test_existing_synthetic_harness_report_is_not_eligible(self):
        report = {
            "schema": "LOUKSNA1_TASK_ADAPTER_EVIDENCE/1.0",
            "status": "PASS_SYNTHETIC_END_TO_END_EXECUTION_ONLY",
            "synthetic_quality_acceptance": "PASS",
            "semantic_quality_equivalence": "NOT_ESTABLISHED",
            "global_certification": "NOT_GRANTED",
        }
        result = self.evaluate(report)
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("FUNCTIONAL_EVIDENCE_SCHEMA_MISMATCH", result["failures"])
        self.assertIn("SYNTHETIC_ONLY_OR_UNPROVEN_EVIDENCE", result["failures"])

    def test_candidate_hash_mismatch_is_blocked(self):
        self.evidence["bundle_sha256"] = "0" * 64
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("FUNCTIONAL_EVIDENCE_BUNDLE_SHA256_MISMATCH", result["failures"])

    def test_missing_target_and_duplicate_are_blocked(self):
        self.evidence["target_results"].pop()
        self.evidence["target_results"].append(dict(self.evidence["target_results"][0]))
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(any(x.startswith("TARGET_EVIDENCE_MISSING:") for x in result["failures"]))
        self.assertTrue(any(x.startswith("DUPLICATE_TARGET_ID:") for x in result["failures"]))

    def test_model_without_pinned_upstream_revision_is_blocked(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] in gate.MODEL_TARGETS)
        row.pop("upstream_revision_sha256")
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(any(x.endswith("UPSTREAM_REVISION_NOT_PINNED_TO_COMMIT") for x in result["failures"]))

    def test_g23_bad_signature_or_wrong_subject_is_blocked(self):
        self.evidence["g23"]["payload"]["subject_bundle_sha256"] = "0" * 64
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("G23_SUBJECT_BUNDLE_MISMATCH", result["failures"])
        self.assertIn("G23_PAYLOAD_SHA256_MISMATCH", result["failures"])
        self.assertIn("G23_ED25519_SIGNATURE_INVALID", result["failures"])

    def test_missing_trust_root_fails_closed(self):
        result = self.evaluate(public_key="")
        self.assertEqual(result["decision"], "HOLD")
        self.assertIn("G23_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED", result["failures"])


if __name__ == "__main__":
    unittest.main()
