from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import louksnapg2_puac2_gate as gate


class Puac2TerminalGateTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.commit = "a" * 40
        self.bundle = self.root / "LOUKSNAPG2.md"
        self.bundle.write_bytes(b"candidate-bundle-fixture")
        self.env = mock.patch.dict(os.environ, {
            "GITHUB_SHA": self.commit,
            "CAJITA_G23_PUBLIC_KEY_PEM": "test-public-key",
        })
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def args(self, functional):
        candidate_sha = gate.sha256_file(self.bundle)
        g23_payload = {
            "status": "PASS",
            "source_commit": self.commit,
            "candidate": {"sha256": candidate_sha, "bytes": self.bundle.stat().st_size},
        }
        return type("Args", (), {
            "bundle": self.bundle,
            "g23_signed": self.write_json("g23.json", {"payload_sha256": "c" * 64}),
            "functional_evidence": self.write_json("functional.json", functional),
            "unit_evidence": self.write_json("unit.json", {"status": "PASS", "failures": 0, "errors": 0}),
            "model_materialization": self.write_json("materialization.json", {"status": "PASS", "models": []}),
            "build_report": self.write_json("build.json", {
                "source_commit": self.commit,
                "candidate": {"sha256": candidate_sha, "bytes": self.bundle.stat().st_size},
            }),
            "g23_validator_id": "INDEPENDENT_G23",
            "g23_public_key_env": "CAJITA_G23_PUBLIC_KEY_PEM",
            "certifier_id": "INDEPENDENT_G24",
        })(), g23_payload

    def valid_functional_evidence(self):
        domains = gate.REQUIRED_DOMAINS
        adapters = []
        for index, domain in enumerate(gate.REQUIRED_REPAIR_DOMAINS, 1):
            adapters.append({
                "adapter_id": "adapter-" + domain,
                "domain_id": domain,
                "source_model_id": "source-model-" + domain,
                "source_commit": self.commit,
                "candidate_sha256": gate.sha256_file(self.bundle),
                "status": "PASS",
                "source_weight_sha256": f"{index:064x}",
                "adapter_sha256": f"{index + 10:064x}",
                "calibration_dataset_sha256": f"{index + 20:064x}",
                "heldout_dataset_sha256": f"{index + 30:064x}",
                "rollback_checkpoint_sha256": f"{index + 40:064x}",
                "calibration_example_count": 128,
                "heldout_example_count": 32,
                "heldout_validation_status": "PASS",
                "independent_validation_status": "PASS",
                "semantic_quality_equivalence_status": "PASS",
                "rollback_verified": True,
                "original_weights_mutated": False,
                "candidate_output_separate": True,
            })
        return {
            "source_commit": self.commit,
            "model_identity_status": "PASS_MODEL_SOURCE_IDENTITIES",
            "model_inference_performed": True,
            "functional_status": "PASS_ALL_DOMAIN_CASES",
            "tests": [
                {
                    "case_id": case_id,
                    "domain_id": domain,
                    "status": "PASS",
                    "execution_status": "PASS_EXECUTION",
                    "quality_criterion_passed": True,
                    "input_sha256": "a" * 64,
                    "output_sha256": "b" * 64,
                }
                for case_id, domain in gate.REQUIRED_CASES.items()
            ],
            "domain_results": {domain: {"status": "PASS"} for domain in domains},
            "summary": {"passed_cases": len(gate.REQUIRED_CASES), "total_cases": len(gate.REQUIRED_CASES)},
            "repair_execution_performed": True,
            "repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS",
            "repair_adapter_evidence": adapters,
        }

    def call_g24(self, functional):
        args, g23_payload = self.args(functional)
        with mock.patch.object(gate, "verify_envelope", return_value=(g23_payload, [])):
            return gate.g24_payload(args)

    def test_g24_passes_only_exact_all_domain_and_repair_evidence(self):
        report = self.call_g24(self.valid_functional_evidence())
        self.assertEqual(report["status"], "PASS", report["blockers"])
        self.assertEqual(report["terminal_decision"], "CERTIFIED_INTEGRAL_WITHIN_TESTED_SCOPE")
        self.assertEqual(report["functional_quality"]["total_cases"], 13)
        self.assertEqual(len(report["functional_quality"]["repair_adapter_domains"]), 6)

    def test_g24_rejects_missing_docling_case_even_when_domain_summary_claims_pass(self):
        functional = self.valid_functional_evidence()
        functional["tests"] = [
            row for row in functional["tests"] if row["case_id"] != "DOCLING_INVOICE_IMAGE_01"
        ]
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("REQUIRED_FUNCTIONAL_CASE_MISSING:DOCLING_INVOICE_IMAGE_01", report["blockers"])

    def test_g24_rejects_missing_adapter_domain_coverage(self):
        functional = self.valid_functional_evidence()
        functional["repair_adapter_evidence"] = functional["repair_adapter_evidence"][:1]
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("REPAIR_ADAPTER_DOMAIN_COVERAGE_INCOMPLETE", report["blockers"])

    def test_g24_rejects_changed_original_weights(self):
        functional = self.valid_functional_evidence()
        functional["repair_adapter_evidence"][0]["original_weights_mutated"] = True
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(any("REPAIR_ADAPTER_ORIGINAL_WEIGHTS_MUTATED:" in x for x in report["blockers"]))

    def test_g24_rejects_functional_evidence_from_another_commit(self):
        functional = self.valid_functional_evidence()
        functional["source_commit"] = "b" * 40
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("FUNCTIONAL_EVIDENCE_COMMIT_MISMATCH", report["blockers"])


if __name__ == "__main__":
    unittest.main()
