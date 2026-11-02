from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile
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
        with zipfile.ZipFile(self.bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("fixture/source.bin", b"original-source")
            archive.writestr("fixture/repaired.bin", b"repaired-candidate")
        self.materialized_models = []
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
            "model_materialization": self.write_json("materialization.json", {"status": "PASS", "models": self.materialized_models}),
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
        archive_members = {}
        adapters = []
        self.materialized_models = []
        evidence_root = self.root / "repair-evidence"
        for index, domain in enumerate(gate.REQUIRED_REPAIR_DOMAINS, 1):
            source_bytes = ("source-model:" + domain).encode("utf-8")
            repaired_bytes = ("repaired-model:" + domain).encode("utf-8")
            source_member = (
                "source/" + domain + "/compiled.fst"
                if domain == "D04_TRADUCCION_LENGUAS_ANTIGUAS"
                else "source/" + domain + "/weights.bin"
            )
            repaired_member = "repaired/" + domain + "/weights.bin"
            archive_members[source_member] = source_bytes
            archive_members[repaired_member] = repaired_bytes
            source_sha = hashlib.sha256(source_bytes).hexdigest()
            if domain != "D04_TRADUCCION_LENGUAS_ANTIGUAS":
                self.materialized_models.append({"domain_id": domain, "sha256": source_sha, "status": "PASS_SOURCE_WEIGHT_AND_MODULE_IDENTITY"})

            folder = evidence_root / domain
            folder.mkdir(parents=True, exist_ok=True)
            payloads = {
                "adapter.py": ("adapter-source:" + domain).encode("utf-8"),
                "calibration.jsonl": ("calibration:" + domain).encode("utf-8"),
                "heldout.jsonl": ("heldout:" + domain).encode("utf-8"),
                "rollback.ckpt": ("rollback:" + domain).encode("utf-8"),
            }
            heldout_report = {
                "schema": "LOUKSNAPG2_HELDOUT_VALIDATION/1.0",
                "status": "PASS",
                "source_commit": self.commit,
                "domain_id": domain,
                "model_inference_performed": True,
                "heldout_case_count": 32,
                "failed_cases": [],
                "semantic_quality_equivalence_status": "PASS",
            }
            payloads["heldout-report.json"] = (json.dumps(heldout_report, sort_keys=True) + "\n").encode("utf-8")
            independent_report = {
                "schema": "LOUKSNAPG2_INDEPENDENT_REPAIR_VALIDATION/1.0",
                "status": "PASS", "source_commit": self.commit, "domain_id": domain,
                "validator_id": "independent-validator-" + domain,
                "candidate_sha256": None,
                "source_weight_sha256": source_sha,
                "repaired_output_sha256": hashlib.sha256(repaired_bytes).hexdigest(),
                "independent_inference_performed": True, "heldout_case_count": 32,
                "failed_cases": [], "semantic_quality_equivalence_status": "PASS",
            }
            payloads["independent-report.json"] = (json.dumps(independent_report, sort_keys=True) + "\n").encode("utf-8")
            rollback_report = {
                "schema": "LOUKSNAPG2_REPAIR_ROLLBACK/1.0",
                "status": "PASS", "source_commit": self.commit, "domain_id": domain,
                "source_weight_sha256": source_sha,
                "rollback_checkpoint_sha256": hashlib.sha256(payloads["rollback.ckpt"]).hexdigest(),
                "restore_test": "PASS", "original_weights_unchanged": True,
                "candidate_output_separate": True,
            }
            payloads["rollback-report.json"] = (json.dumps(rollback_report, sort_keys=True) + "\n").encode("utf-8")
            records = {}
            for name, data in payloads.items():
                target = folder / name
                target.write_bytes(data)
                records[name] = {
                    "path": (Path("repair-evidence") / domain / name).as_posix(),
                    "bytes": len(data),
                    "sha256": hashlib.sha256(data).hexdigest(),
                }

            adapters.append({
                "adapter_id": "adapter-" + domain,
                "domain_id": domain,
                "source_model_id": "source-model-" + domain,
                "source_commit": self.commit,
                "candidate_sha256": None,
                "status": "PASS",
                "source_weight_sha256": source_sha,
                "adapter_sha256": records["adapter.py"]["sha256"],
                "calibration_dataset_sha256": records["calibration.jsonl"]["sha256"],
                "heldout_dataset_sha256": records["heldout.jsonl"]["sha256"],
                "rollback_checkpoint_sha256": records["rollback.ckpt"]["sha256"],
                "calibration_example_count": 128,
                "heldout_example_count": 32,
                "heldout_validation_status": "PASS",
                "independent_validation_status": "PASS",
                "semantic_quality_equivalence_status": "PASS",
                "rollback_verified": True,
                "original_weights_mutated": False,
                "candidate_output_separate": True,
                "execution_backend": "ISOLATED_GPU_RUNNER",
                "repair_operation_id": "repair-op-" + domain,
                "source_resource_type": "COMPILED_FINITE_STATE_TRANSDUCER" if domain == "D04_TRADUCCION_LENGUAS_ANTIGUAS" else "SOURCE_MODEL_WEIGHT",
                "artifacts": {
                    "source_model": {
                        "candidate_member_path": source_member,
                        "bytes": len(source_bytes),
                        "sha256": source_sha,
                    },
                    "repaired_output": {
                        "candidate_member_path": repaired_member,
                        "bytes": len(repaired_bytes),
                        "sha256": hashlib.sha256(repaired_bytes).hexdigest(),
                    },
                    "adapter_source": records["adapter.py"],
                    "calibration_dataset": records["calibration.jsonl"],
                    "heldout_dataset": records["heldout.jsonl"],
                    "rollback_checkpoint": records["rollback.ckpt"],
                    "heldout_report": records["heldout-report.json"],
                    "independent_report": records["independent-report.json"],
                    "rollback_report": records["rollback-report.json"],
                },
            })

        with zipfile.ZipFile(self.bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, data in archive_members.items():
                archive.writestr(name, data)
        candidate_sha = gate.sha256_file(self.bundle)
        for adapter in adapters:
            adapter["candidate_sha256"] = candidate_sha
            independent_record = adapter["artifacts"]["independent_report"]
            independent_path = self.root / independent_record["path"]
            independent = json.loads(independent_path.read_text(encoding="utf-8"))
            independent["candidate_sha256"] = candidate_sha
            independent_path.write_text(json.dumps(independent, sort_keys=True) + "\n", encoding="utf-8")
            independent_record["bytes"] = independent_path.stat().st_size
            independent_record["sha256"] = hashlib.sha256(independent_path.read_bytes()).hexdigest()

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
            "repair_execution_evidence": {
                "status": "PASS_ISOLATED_GPU_REPAIR",
                "execution_mode": "ISOLATED_GPU_REPAIR",
                "execution_backend": "ISOLATED_GPU_RUNNER",
                "source_commit": self.commit,
                "gpu_device_count": 1,
                "runner_id": "fixture-gpu-runner",
                "repair_job_id": "fixture-repair-job",
                "runner_image_sha256": "f" * 64,
                "repair_execution_performed": True,
            },
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

    def test_g24_rejects_digest_only_adapter_claims_without_evidence_files(self):
        functional = self.valid_functional_evidence()
        row = functional["repair_adapter_evidence"][0]
        row["artifacts"]["rollback_checkpoint"]["path"] = "missing/rollback.ckpt"
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(any("REPAIR_EVIDENCE_FILE_MISSING_OR_UNSAFE:" in x for x in report["blockers"]))

    def test_g24_rejects_heldout_report_record_hash_mismatch(self):
        functional = self.valid_functional_evidence()
        functional["repair_adapter_evidence"][0]["artifacts"]["heldout_report"]["sha256"] = "0" * 64
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(any("REPAIR_EVIDENCE_RECORD_DIGEST_MISMATCH:" in x for x in report["blockers"]))

    def test_g24_rejects_independent_validator_collision(self):
        functional = self.valid_functional_evidence()
        row = functional["repair_adapter_evidence"][0]
        record = row["artifacts"]["independent_report"]
        path = self.root / record["path"]
        independent = json.loads(path.read_text())
        independent["validator_id"] = row["adapter_id"]
        path.write_text(json.dumps(independent, sort_keys=True) + "\n")
        record["bytes"] = path.stat().st_size
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(any("INDEPENDENT_VALIDATOR_NOT_DISTINCT:" in x for x in report["blockers"]))

    def test_g24_rejects_unverified_rollback_restore(self):
        functional = self.valid_functional_evidence()
        row = functional["repair_adapter_evidence"][0]
        record = row["artifacts"]["rollback_report"]
        path = self.root / record["path"]
        rollback = json.loads(path.read_text())
        rollback["restore_test"] = "FAIL"
        path.write_text(json.dumps(rollback, sort_keys=True) + "\n")
        record["bytes"] = path.stat().st_size
        record["sha256"] = hashlib.sha256(path.read_bytes()).hexdigest()
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertTrue(any("ROLLBACK_RESTORE_TEST_NOT_PASS:" in x for x in report["blockers"]))

    def test_g24_rejects_missing_gpu_execution_proof(self):
        functional = self.valid_functional_evidence()
        functional["repair_execution_evidence"]["gpu_device_count"] = 0
        report = self.call_g24(functional)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("GPU_DEVICE_NOT_PROVEN", report["blockers"])

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
