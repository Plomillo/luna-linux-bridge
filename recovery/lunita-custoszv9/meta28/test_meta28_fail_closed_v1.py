"""Tests of the META-28 gate. A passing test here is not T01-T80 and not certification."""

from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from certification_gate_v1 import OBSERVED_AT, write_reports
from consensus_v1 import evaluate as evaluate_consensus
from contracts_v1 import ContractError, new_id, validate_request, validate_response
from documents_v1 import compatibility
from epistemic_v1 import EpistemicError, promote
from mailbox_v1 import Mailbox
from rules_v1 import RuleError, evaluate as evaluate_rule
from size_budget_v1 import (
    GGUF_CONTENT_LENGTH_BYTES,
    HARD_MAX_BYTES,
    JAMOVI_CATALOG_DOWNLOAD_BYTES,
    evaluate,
    meta28_default_payloads,
)
from zero_trust_v1 import authorize

ROOT = Path(__file__).resolve().parent
EVIDENCE = ROOT / "evidence"


class Meta28FailClosedTests(unittest.TestCase):
    def test_size_lower_bound_blocks_build(self):
        result = evaluate(meta28_default_payloads())
        expected = GGUF_CONTENT_LENGTH_BYTES + JAMOVI_CATALOG_DOWNLOAD_BYTES
        self.assertEqual(result["accounted_required_lower_bound_bytes"], expected)
        self.assertGreater(expected, HARD_MAX_BYTES)
        self.assertEqual(result["over_by_bytes"], expected - HARD_MAX_BYTES)
        self.assertEqual(result["status"], "BUILD_BLOCKED_BY_SIZE_CONSTRAINT")
        self.assertIsNone(result["final_squashfs_bytes"])
        self.assertEqual(result["over_by_bytes"], 321_784_544)

    def test_compression_credit_requires_measured_delta(self):
        payloads = meta28_default_payloads()
        payloads[1]["compression_credit_bytes"] = payloads[1]["lower_bound_bytes"]
        with self.assertRaises(ValueError):
            evaluate(payloads)

    def test_declared_cannot_jump_to_certified(self):
        with self.assertRaises(EpistemicError):
            promote("DECLARED", "CERTIFIED", independent_validation=False)
        with self.assertRaises(EpistemicError):
            promote("VALIDATED", "CERTIFIED", independent_validation=False)
        self.assertEqual(
            promote("VALIDATED", "INDEPENDENTLY_VALIDATED", independent_validation=False),
            "INDEPENDENTLY_VALIDATED",
        )

    def test_same_model_is_not_consensus(self):
        same = {
            "vote": "ACCEPT",
            "evidence_digest": "d" * 64,
            "decision_logic_id": "qwen3-0.6b",
            "runtime_id": "llama.cpp",
        }
        result = evaluate_consensus([same, dict(same)], "d" * 64)
        self.assertEqual(result["status"], "CONSENSUS_UNAVAILABLE")
        self.assertEqual(result["reason"], "VALIDATORS_NOT_INDEPENDENT")

    def test_distinct_validators_can_agree(self):
        digest = "e" * 64
        result = evaluate_consensus(
            [
                {"vote": "ACCEPT", "evidence_digest": digest, "decision_logic_id": "lane-a", "runtime_id": "rt-a"},
                {"vote": "ACCEPT", "evidence_digest": digest, "decision_logic_id": "lane-b", "runtime_id": "rt-b"},
            ],
            digest,
        )
        self.assertEqual(result["status"], "CONSENSUS_UNANIMOUS")

    def test_zero_trust_denies_partial_checks(self):
        decision = authorize({"IDENTITY_CHECK": True, "AUTHORIZATION_CHECK": True})
        self.assertEqual(decision["decision"], "DENY_EXECUTION")
        self.assertIn("INTEGRITY_CHECK", decision["failed_controls"])

    def test_contract_rejects_foreign_caller_and_success_without_evidence(self):
        mission = new_id()
        request = {
            "request_id": new_id(),
            "mission_id": mission,
            "caller": "Qwen3",
            "component_id": "E01",
            "operation": "infer",
            "input": {},
            "constraints": {},
            "permissions": [],
            "provenance_required": True,
            "timeout_ms": 1000,
            "contract_version": "1.0",
        }
        with self.assertRaises(ContractError):
            validate_request(request)
        request["caller"] = "LUNITA"
        validate_request(request)
        response = {
            "request_id": request["request_id"],
            "mission_id": mission,
            "component_id": "E01",
            "status": "SUCCESS",
            "output": {},
            "evidence": [],
            "artifacts": [],
            "warnings": [],
            "errors": [],
            "provenance": {},
            "execution_metadata": {},
            "contract_version": "1.0",
        }
        with self.assertRaises(ContractError):
            validate_response(response)

    def test_rule_engine_refuses_calls(self):
        self.assertTrue(evaluate_rule("status == 'PASS' and n > 1", {"status": "PASS", "n": 2}))
        with self.assertRaises(RuleError):
            evaluate_rule("__import__('os')", {})

    def test_extension_is_not_compatibility(self):
        self.assertFalse(compatibility("DOCX", "DECLARED")["compatible"])
        self.assertTrue(compatibility("CSV", "EXPORT_TESTED")["compatible"])

    def test_mailbox_cannot_succeed_without_a_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            box = Mailbox(Path(tmp))
            mission = box.submit("CONSULTAS", "¿Qué diseño separa pregunta de hipótesis?")
            closed = box.close(mission["mission_id"], "SUCCESS")
            self.assertEqual(closed["state"], "VALIDATION_FAILED")
            artifact = Path(tmp) / "nota.txt"
            artifact.write_text("observación\n", encoding="utf-8")
            box.attach_artifact(mission["mission_id"], artifact)
            closed = box.close(mission["mission_id"], "SUCCESS")
            self.assertEqual(closed["state"], "SUCCESS")
            self.assertEqual(closed["artifacts"][0]["bytes"], len("observación\n".encode()))

    def test_committed_evidence_is_blocked_and_reproducible(self):
        report = json.loads((EVIDENCE / "LUNITA_CERTIFICATION_REPORT.json").read_text(encoding="utf-8"))
        self.assertEqual(report["status"], "CERTIFICATION_BLOCKED")
        self.assertEqual(report["certification"], "NOT_GRANTED")
        self.assertFalse(report["replaces_v18"])
        self.assertTrue(report["forbidden_jump_blocked"])
        self.assertEqual(report["consensus_status"], "CONSENSUS_UNAVAILABLE")
        inventory = json.loads((EVIDENCE / "LUNITA_COMPONENT_INVENTORY.json").read_text(encoding="utf-8"))
        self.assertFalse(inventory["qwen3_is_identity"])
        tests = json.loads((EVIDENCE / "LUNITA_TEST_RESULTS.json").read_text(encoding="utf-8"))
        self.assertTrue(all(value == "NOT_RUN_NO_IMAGE" for value in tests["results"].values()))
        self.assertEqual(len(tests["results"]), 80)
        with tempfile.TemporaryDirectory() as tmp:
            write_reports(Path(tmp), observed_at=OBSERVED_AT)
            for path in EVIDENCE.iterdir():
                if not path.is_file():
                    continue
                generated = Path(tmp) / path.name
                self.assertEqual(generated.read_bytes(), path.read_bytes(), path.name)
        sums = (EVIDENCE / "LUNITA_SHA256SUMS").read_text(encoding="utf-8").splitlines()
        for line in sums:
            digest, name = line.split("  ", 1)
            self.assertEqual(hashlib.sha256((EVIDENCE / name).read_bytes()).hexdigest(), digest)


if __name__ == "__main__":
    unittest.main()
