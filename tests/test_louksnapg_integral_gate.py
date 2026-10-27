import base64
import hashlib
import importlib.util
import json
import tempfile
import unittest
import zipfile
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
        qwen_config = {
            "hidden_size": 5120, "intermediate_size": 17408, "num_hidden_layers": 40,
            "num_attention_heads": 40, "num_key_value_heads": 8,
            "tie_word_embeddings": False, "vocab_size": 151936,
        }
        with zipfile.ZipFile(self.bundle, "w") as archive:
            archive.writestr(gate.QWEN_CONFIG_PATH, json.dumps(qwen_config))
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
                "evidence_kind": "MODEL_TASK",
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "quality_status": "PASS",
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
                upstream_ids["D06_ANALISIS_AVANZADO"] = "Qwen/Qwen3-14B"
                row.update({
                    "model_load_status": "PASS",
                    "model_inference_observed": True,
                    "weight_sha256": "5" * 64,
                    "upstream_model_id": upstream_ids[target_id],
                    "official_source_url": gate.OFFICIAL_SOURCE_URLS[target_id],
                    "upstream_revision_commit": gate.OFFICIAL_SOURCE_REVISIONS[target_id],
                    "model_repository_revision_commit": gate.OFFICIAL_MODEL_REVISIONS[target_id],
                    "upstream_weights_sha256": "9" * 64,
                    "candidate_before_weights_sha256": "6" * 64,
                    "candidate_after_weights_sha256": "5" * 64,
                    "repair_implementation_commit": "b" * 40,
                    "test_evidence_sha256": "7" * 64,
                    "quality_report_sha256": "8" * 64,
                    "expected_test_count": 3,
                    "passed_test_count": 3,
                    "semantic_quality_status": "PASS",
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
        candidate_model_identity = gate.inspect_qwen_model_identity(self.bundle)
        return gate.evaluate_evidence(
            self.evidence if evidence is None else evidence,
            self.sha,
            self.commit,
            self.public_pem if public_key is None else public_key,
            candidate_model_identity=candidate_model_identity,
        )

    def test_primitive_smoke_without_complete_scope_is_not_functional_certification(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D05_CALIBRE")
        row.update({
            "evidence_kind": "PRIMITIVE_SMOKE", "status": "PASS_PRIMITIVE_SMOKE",
            "scope_complete": False, "primitive_evidence_sha256": "6" * 64,
            "runtime_sha256": "7" * 64, "synthetic_only": False,
        })
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D05_CALIBRE")
        self.assertIn("PRIMITIVE_SCOPE_INCOMPLETE", check["failures"])
        self.assertNotIn("FUNCTIONAL_EXECUTION_NOT_PASS", check["failures"])

    def test_global_luna_byte_ceiling_is_enforced_by_integral_gate(self):
        from unittest.mock import patch
        with patch.object(gate, "GLOBAL_LUNA_HARD_MAX_BYTES", self.bundle.stat().st_size - 1):
            with self.assertRaisesRegex(ValueError, "BUNDLE_OVER_GLOBAL_LUNA_HARD_MAX_BYTES"):
                gate.validate_bundle_size(self.bundle)

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

    def test_candidate_config_matching_qwen14b_is_accepted_when_contract_pins_qwen14b(self):
        matching_config = {
            "hidden_size": 5120, "intermediate_size": 17408, "num_hidden_layers": 40,
            "num_attention_heads": 40, "num_key_value_heads": 8,
            "tie_word_embeddings": False, "vocab_size": 151936,
        }
        with zipfile.ZipFile(self.bundle, "w") as archive:
            archive.writestr(gate.QWEN_CONFIG_PATH, json.dumps(matching_config))
        self.sha = hashlib.sha256(self.bundle.read_bytes()).hexdigest()
        self.evidence["bundle_sha256"] = self.sha
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertNotIn("CANDIDATE_MODEL_IDENTITY_NOT_VERIFIED_OR_QWEN_VARIANT_MISMATCH", result["failures"])
        self.assertEqual(result["candidate_model_identity"]["status"], "PASS_CONFIG_MATCHES_PINNED_VARIANT")
        self.assertEqual(result["candidate_model_identity"]["expected_model_id"], "Qwen/Qwen3-14B")
        self.assertEqual(result["candidate_model_identity"]["reference"], "https://huggingface.co/Qwen/Qwen3-14B")


    def test_model_target_cannot_pass_as_primitive_smoke(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D03_TRANSCRIPCION_ROOT")
        row.update({
            "evidence_kind": "PRIMITIVE_SMOKE",
            "status": "PASS_PRIMITIVE_SMOKE",
            "scope_complete": True,
            "primitive_evidence_sha256": "6" * 64,
            "runtime_sha256": "7" * 64,
        })
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D03_TRANSCRIPCION_ROOT")
        self.assertIn("MODEL_TARGET_REQUIRES_MODEL_TASK_EVIDENCE", check["failures"])

    def test_model_quality_status_is_required_and_has_no_pass_default(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D01_CEREBRO_ROOT")
        row.pop("quality_status")
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D01_CEREBRO_ROOT")
        self.assertIn("MODEL_QUALITY_NOT_PASS", check["failures"])

    def test_candidate_weights_must_change_and_match_functional_gate_hash(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D04_TRADUCCION_GENERAL")
        row["candidate_before_weights_sha256"] = row["candidate_after_weights_sha256"]
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D04_TRADUCCION_GENERAL")
        self.assertIn("CANDIDATE_WEIGHTS_NOT_MATERIALLY_REPAIRED", check["failures"])

        row["candidate_before_weights_sha256"] = "4" * 64
        row["candidate_after_weights_sha256"] = "6" * 64
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D04_TRADUCCION_GENERAL")
        self.assertIn("CANDIDATE_AFTER_HASH_DIFFERS_FROM_FUNCTIONAL_GATE_WEIGHT_HASH", check["failures"])

    def test_model_repair_requires_quality_report_and_passed_case_counts(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D05_DOCLING")
        row.pop("quality_report_sha256")
        row["passed_test_count"] = 2
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        check = next(x for x in result["target_checks"] if x["target_id"] == "D05_DOCLING")
        self.assertIn("QUALITY_REPORT_SHA256_INVALID", check["failures"])
        self.assertIn("MODEL_REPAIR_TEST_CASES_NOT_ALL_PASS", check["failures"])

    def test_model_repository_revision_must_match_pinned_official_snapshot(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] == "D06_ANALISIS_AVANZADO")
        row["model_repository_revision_commit"] = "0" * 40
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(any("MODEL_REPOSITORY_REVISION_NOT_PINNED" in failure for failure in result["failures"]))

    def test_model_without_pinned_upstream_revision_is_blocked(self):
        row = next(x for x in self.evidence["target_results"] if x["target_id"] in gate.MODEL_TARGETS)
        row.pop("upstream_revision_commit")
        self.sign_evidence(self.evidence)
        result = self.evaluate()
        self.assertEqual(result["decision"], "HOLD")
        self.assertTrue(any(x.endswith("UPSTREAM_SOURCE_REVISION_MISMATCH") for x in result["failures"]))

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
