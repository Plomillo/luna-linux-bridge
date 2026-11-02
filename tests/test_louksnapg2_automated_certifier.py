from __future__ import annotations

import hashlib
import json
import os
import sys
import zipfile
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import louksnapg2_automated_certifier as certifier


class AutomatedG23G24Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.bundle = self.root / "LOUKSNAPG2.md"
        self.bundle.write_bytes(b"candidate-fixture")
        self.commit = "a" * 40
        self.env = mock.patch.dict(os.environ, {"GITHUB_SHA": self.commit, "G23_ATTESTATION_VERIFIED": "true"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.temp.cleanup()

    def write_json(self, name, value):
        path = self.root / name
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_g23_holds_when_worker_evidence_is_not_bound_or_not_present(self):
        worker = self.write_json("worker.json", {"worker": "OTHER", "worker_status": "FAIL", "source_commit": self.commit})
        build = self.write_json("build.json", {"status": "PASS_CANDIDATE_BUILD_ONLY", "source_commit": self.commit, "candidate": {"sha256": certifier.sha256_file(self.bundle), "bytes": self.bundle.stat().st_size}, "global_certification": "NOT_GRANTED"})
        unit = self.write_json("unit.json", {"status": "PASS", "failures": 0, "errors": 0})
        identity = self.write_json("identity.json", {"status": "PASS", "required_domain_count": 5})
        args = type("Args", (), {"bundle": self.bundle, "build_report": build, "worker_evidence": worker, "unit_evidence": unit, "model_materialization": identity})()
        with mock.patch.object(certifier, "verify_bundle", return_value={
            "identity_preservation_status": "PASS_SOURCE_IDENTITY_PRESERVED",
            "budget_status": "PASS", "container_integrity": "PASS",
            "protected_prefix_integrity": "PASS", "cajita_document_copy_integrity": "PASS",
            "runtime_member_integrity": "PASS", "single_distribution_container": "PASS",
            "runtime_routing_registry": "PASS", "module_registry": "PASS", "source_commit": self.commit,
        }):
            report = certifier.g23(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("PRIMARY_CUSTOSZ_AUDIT_OR_BUILD_NOT_PASS", report["blockers"])

    def test_g24_holds_without_g23_attestation(self):
        os.environ["G23_ATTESTATION_VERIFIED"] = "false"
        args = self.g24_args()
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("G23_OIDC_ATTESTATION_NOT_VERIFIED", report["blockers"])

    def test_g24_holds_when_execution_mode_is_not_local_offline(self):
        args = self.g24_args()
        execution = json.loads(args.execution_mode_preflight.read_text())
        execution.update({
            "status": "PASS_REMOTE_MODE",
            "execution_mode": "REMOTE",
            "remote_inference_enabled": True,
            "model_network_fetch_performed": False,
        })
        args.execution_mode_preflight.write_text(json.dumps(execution))
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("ISOLATED_GPU_REPAIR_PREFLIGHT_NOT_PASS", report["blockers"])

    def test_g24_holds_if_any_model_repair_adapter_is_blocked(self):
        args = self.g24_args()
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("MODEL_REPAIR_ADAPTERS_NOT_ALL_PASS", report["blockers"])
        self.assertIn("FUNCTIONAL_SEMANTIC_SUITE_NOT_PASS", report["blockers"])
        self.assertIn("REPAIR_ADAPTER_DOMAIN_COVERAGE_INCOMPLETE", report["blockers"])

    def test_g24_certifies_only_complete_exact_sha_evidence(self):
        args = self.g24_args()
        adapters = []
        archive_members = {}
        evidence_root = args.repair_readiness.parent
        for index, domain in enumerate(certifier.REQUIRED_REPAIR_DOMAINS, 1):
            digest = f"{index:064x}"
            repaired_bytes = ("repaired-output:" + domain).encode("utf-8")
            rollback_bytes = ("rollback-checkpoint:" + domain).encode("utf-8")
            heldout_payload = {
                "schema": "LOUKSNAPG2_HELDOUT_VALIDATION/1.0",
                "status": "PASS", "source_commit": self.commit, "domain_id": domain,
                "model_inference_performed": True, "heldout_case_count": 2,
                "failed_cases": [], "semantic_quality_equivalence_status": "PASS"
            }
            heldout_bytes = (json.dumps(heldout_payload, sort_keys=True) + "\n").encode("utf-8")
            folder = Path("repair-adapters") / domain
            for name, payload in (("repaired.bin", repaired_bytes), ("rollback.bin", rollback_bytes), ("heldout.json", heldout_bytes)):
                target = evidence_root / folder / name
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
            member_path = "LOUKSNAPG2_REPAIRED_OUTPUTS/" + domain + "/repaired.bin"
            archive_members[member_path] = repaired_bytes
            adapters.append({
                "adapter_id": "adapter-" + domain,
                "domain_id": domain,
                "source_model_id": "source-model-" + domain,
                "source_commit": self.commit,
                "status": "PASS",
                "source_weight_sha256": digest,
                "adapter_sha256": f"{index + 10:064x}",
                "calibration_dataset_sha256": f"{index + 20:064x}",
                "heldout_dataset_sha256": f"{index + 30:064x}",
                "rollback_checkpoint_sha256": hashlib.sha256(rollback_bytes).hexdigest(),
                "calibration_example_count": 100,
                "heldout_example_count": 25,
                "heldout_validation_status": "PASS",
                "independent_validation_status": "PASS",
                "semantic_quality_equivalence_status": "PASS",
                "rollback_verified": True,
                "original_weights_mutated": False,
                "candidate_output_separate": True,
                "execution_backend": "ISOLATED_GPU_RUNNER",
                "repair_operation_id": "repair-op-" + domain,
                "artifacts": {
                    "repaired_output": {"path": (folder / "repaired.bin").as_posix(), "bytes": len(repaired_bytes), "sha256": hashlib.sha256(repaired_bytes).hexdigest()},
                    "heldout_report": {"path": (folder / "heldout.json").as_posix(), "bytes": len(heldout_bytes), "sha256": hashlib.sha256(heldout_bytes).hexdigest()},
                    "rollback_checkpoint": {"path": (folder / "rollback.bin").as_posix(), "bytes": len(rollback_bytes), "sha256": hashlib.sha256(rollback_bytes).hexdigest()},
                    "candidate_member_path": member_path,
                },
            })
        with zipfile.ZipFile(args.bundle, "w", compression=zipfile.ZIP_STORED) as archive:
            for name, payload in archive_members.items():
                archive.writestr(name, payload)
        candidate_sha = certifier.sha256_file(args.bundle)
        g23 = json.loads(args.g23_report.read_text())
        g23["candidate"]["sha256"] = candidate_sha
        args.g23_report.write_text(json.dumps(g23))
        build_evidence = json.loads(args.build_report.read_text())
        build_evidence["candidate"]["sha256"] = candidate_sha
        args.build_report.write_text(json.dumps(build_evidence))
        worker = json.loads(args.worker_evidence.read_text())
        worker.update({
            "worker_status": "PASS_REPAIR_EXECUTED",
            "repair_status": "PASS_ALL_REQUIRED_ADAPTERS",
            "repair_execution_performed": True,
            "repair_adapter_domains": sorted(certifier.REQUIRED_REPAIR_DOMAINS),
        })
        args.worker_evidence.write_text(json.dumps(worker))
        readiness = json.loads(args.repair_readiness.read_text())
        readiness.update({
            "source_commit": self.commit,
            "candidate_sha256": candidate_sha,
            "repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS",
            "adapter_results": adapters,
        })
        args.repair_readiness.write_text(json.dumps(readiness))
        execution = json.loads(args.execution_mode_preflight.read_text())
        execution.update({
            "status": "PASS_ISOLATED_GPU_REPAIR",
            "execution_mode": "ISOLATED_GPU_REPAIR",
            "execution_backend": "ISOLATED_GPU_RUNNER",
            "source_commit": self.commit,
            "gpu_device_count": 1,
            "runner_id": "test-gpu-runner",
            "repair_job_id": "test-repair-job",
            "runner_image_sha256": "f" * 64,
            "repair_execution_performed": True,
        })
        args.execution_mode_preflight.write_text(json.dumps(execution))
        functional = json.loads(args.functional_evidence.read_text())
        functional.update({
            "source_commit": self.commit,
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
                for case_id, domain in certifier.REQUIRED_CASES.items()
            ],
            "domain_results": {domain: {"status": "PASS"} for domain in certifier.REQUIRED_DOMAINS},
        })
        args.functional_evidence.write_text(json.dumps(functional))
        report = certifier.g24(args)
        self.assertEqual(report["status"], "CERTIFIED", report["blockers"])
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["canonical_promotion_authorized"])

    def test_g24_rejects_incomplete_adapter_domain_coverage(self):
        args = self.g24_args()
        readiness = json.loads(args.repair_readiness.read_text())
        readiness.update({
            "source_commit": self.commit,
            "candidate_sha256": certifier.sha256_file(args.bundle),
            "repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS",
            "adapter_results": [{"adapter_id": "single-adapter", "domain_id": "D01_CEREBRO", "status": "PASS"}],
        })
        args.repair_readiness.write_text(json.dumps(readiness))
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("REPAIR_ADAPTER_DOMAIN_COVERAGE_INCOMPLETE", report["blockers"])

    def test_g24_rejects_adapter_that_mutates_original_weights(self):
        args = self.g24_args()
        adapters = []
        for index, domain in enumerate(certifier.REQUIRED_REPAIR_DOMAINS, 1):
            adapters.append({
                "adapter_id": "adapter-" + domain,
                "domain_id": domain,
                "source_model_id": "source-model-" + domain,
                "source_commit": self.commit,
                "status": "PASS",
                "source_weight_sha256": f"{index:064x}",
                "adapter_sha256": f"{index + 10:064x}",
                "calibration_dataset_sha256": f"{index + 20:064x}",
                "heldout_dataset_sha256": f"{index + 30:064x}",
                "rollback_checkpoint_sha256": f"{index + 40:064x}",
                "calibration_example_count": 100,
                "heldout_example_count": 25,
                "heldout_validation_status": "PASS",
                "independent_validation_status": "PASS",
                "semantic_quality_equivalence_status": "PASS",
                "rollback_verified": True,
                "original_weights_mutated": domain == "D01_CEREBRO",
                "candidate_output_separate": True,
            })
        readiness = json.loads(args.repair_readiness.read_text())
        readiness.update({
            "source_commit": self.commit,
            "candidate_sha256": certifier.sha256_file(args.bundle),
            "repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS",
            "adapter_results": adapters,
        })
        args.repair_readiness.write_text(json.dumps(readiness))
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("REPAIR_ADAPTER_MUTATED_ORIGINAL_WEIGHTS:D01_CEREBRO", report["blockers"])

    def g24_args(self):
        g23 = self.write_json("g23.json", {"gate": "G23", "status": "PASS", "source_commit": self.commit, "candidate": {"sha256": certifier.sha256_file(self.bundle)}})
        build = self.write_json("build.json", {"status": "PASS_CANDIDATE_BUILD_ONLY", "source_commit": self.commit, "candidate": {"sha256": certifier.sha256_file(self.bundle)}, "global_certification": "NOT_GRANTED"})
        worker = self.write_json("worker.json", {"worker": "CUSTOSZ_V9", "worker_status": "PASS", "source_commit": self.commit, "repair_status": "BLOCKED", "repair_execution_performed": False, "global_certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED"})
        identity = self.write_json("identity.json", {"status": "PASS", "required_domain_count": 5})
        readiness = self.write_json("readiness.json", {"repair_adapter_status": "BLOCKED", "adapter_results": []})
        execution = self.write_json("execution.json", {
            "status": "BLOCKED_REMOTE_MODE",
            "execution_mode": "REMOTE",
            "remote_inference_enabled": True,
            "model_network_fetch_performed": False,
        })
        functional = self.write_json("functional.json", {"source_commit": self.commit, "functional_status": "FAIL_FUNCTIONAL_QUALITY", "tests": [], "domain_results": {}})
        return type("Args", (), {
            "bundle": self.bundle, "g23_report": g23, "build_report": build,
            "worker_evidence": worker, "model_materialization": identity,
            "repair_readiness": readiness, "execution_mode_preflight": execution,
            "functional_evidence": functional,
        })()


if __name__ == "__main__":
    unittest.main()
