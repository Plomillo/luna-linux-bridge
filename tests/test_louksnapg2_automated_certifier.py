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
        self.assertIn("PRIMARY_CUSTOSZ_WORKER_NOT_PASS", report["blockers"])

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
        self.assertIn("LOCAL_OFFLINE_EXECUTION_POLICY_NOT_PASS", report["blockers"])

    def test_g24_holds_if_any_model_repair_adapter_is_blocked(self):
        args = self.g24_args()
        report = certifier.g24(args)
        self.assertEqual(report["status"], "HOLD")
        self.assertIn("MODEL_REPAIR_ADAPTERS_NOT_ALL_PASS", report["blockers"])
        self.assertIn("FUNCTIONAL_SEMANTIC_SUITE_NOT_PASS", report["blockers"])

    def test_g24_certifies_only_complete_exact_sha_evidence(self):
        args = self.g24_args()
        worker = json.loads(args.worker_evidence.read_text())
        worker.update({"repair_status": "PASS_ALL_REQUIRED_ADAPTERS", "repair_execution_performed": True})
        args.worker_evidence.write_text(json.dumps(worker))
        readiness = json.loads(args.repair_readiness.read_text())
        readiness.update({"repair_adapter_status": "PASS_ALL_REQUIRED_ADAPTERS", "adapter_results": [{"status": "PASS"}]})
        args.repair_readiness.write_text(json.dumps(readiness))
        execution = json.loads(args.execution_mode_preflight.read_text())
        execution.update({
            "status": "PASS_LOCAL_OFFLINE",
            "execution_mode": "LOCAL_OFFLINE",
            "remote_inference_enabled": False,
            "model_network_fetch_performed": False,
        })
        args.execution_mode_preflight.write_text(json.dumps(execution))
        functional = json.loads(args.functional_evidence.read_text())
        functional["functional_status"] = "PASS_ALL_DOMAIN_CASES"
        functional["tests"] = [{"case_id": case_id, "domain_id": domain, "status": "PASS"} for case_id, domain in certifier.REQUIRED_CASES.items()]
        functional["domain_results"] = {domain: {"status": "PASS"} for domain in certifier.REQUIRED_DOMAINS}
        args.functional_evidence.write_text(json.dumps(functional))
        report = certifier.g24(args)
        self.assertEqual(report["status"], "CERTIFIED")
        self.assertFalse(report["release_authorized"])
        self.assertFalse(report["canonical_promotion_authorized"])

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
