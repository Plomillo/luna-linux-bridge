import json
import pathlib
import sys
import tempfile
import unittest
from unittest import mock

BRIDGE = pathlib.Path(__file__).resolve().parents[1]
REASONING = BRIDGE / "reasoning"
sys.path.insert(0, str(REASONING))
sys.path.insert(0, str(BRIDGE))

import interface
import bridge_adapter
import qwen_provider


def request():
    return {
        "schema": "LOUKSNA_REASONING_REQUEST/1.0",
        "request_id": "test-001",
        "objective": "Diagnose from evidence and propose only; do not execute.",
        "evidence_refs": ["sha256:abc"],
        "context": {"host": "LOUKSNA", "state": "OBSERVED"},
        "constraints": {"fail_closed": True},
    }


def wire_payload():
    return {
        "observations": "Observed bounded evidence only.",
        "assumptions": "",
        "inferences": "No execution authorization is present.",
        "alternatives": "Remain HOLD.",
        "proposal_summary": "Remain advisory.",
        "proposal_operation_class": "NONE",
        "risks": "Unverified state must not be promoted.",
        "expected_result": "No host mutation.",
        "failure_conditions": "Evidence drift.",
        "recovery_proposal": "Remain HOLD.",
        "limitations": "No independent terminal certification in this unit test.",
        "confidence": "HIGH",
    }


def model_payload():
    return {
        "observations": ["Observed bounded evidence only."],
        "assumptions": [],
        "inferences": ["No execution authorization is present."],
        "alternatives": [{"id": "A", "summary": "Remain HOLD.", "requires_authorization": False}],
        "proposal": {"summary": "Remain advisory.", "operation_class": "NONE"},
        "risks": ["Unverified state must not be promoted."],
        "expected_result": "No host mutation.",
        "failure_conditions": ["Evidence drift."],
        "recovery_proposal": "Remain HOLD.",
        "limitations": ["No independent terminal certification in this unit test."],
        "confidence": 0.8,
    }


class ReasoningInterfaceTests(unittest.TestCase):
    def test_request_is_bounded(self):
        self.assertEqual(interface.validate_request(request())["request_id"], "test-001")
        bad = request(); bad["objective"] = ""
        with self.assertRaises(interface.ReasoningContractError):
            interface.validate_request(bad)

    def test_result_hard_binds_all_authority_false(self):
        out = interface.validate_result(model_payload(), "test-001", "QWEN35_4B_S")
        self.assertFalse(out["execution_allowed"])
        self.assertEqual(out["certification_state"], "NOT_CERTIFIED")
        self.assertTrue(all(v is False for v in out["authority"].values()))

    def test_model_cannot_add_authority_fields(self):
        bad = model_payload()
        bad["authority"] = {"execution": True}
        with self.assertRaises(interface.ReasoningContractError):
            interface.validate_result(bad, "test-001", "QWEN35_4B_S")

    def test_schema_forbids_extra_model_properties(self):
        schema = interface.model_wire_schema()
        self.assertIs(schema["additionalProperties"], False)
        self.assertNotIn("authority", schema["properties"])
        self.assertNotIn("command", schema["properties"])

    def test_wire_normalizes_to_canonical_contract(self):
        canonical = interface.normalize_model_wire(wire_payload())
        self.assertEqual(canonical["proposal"]["operation_class"], "NONE")
        self.assertEqual(canonical["alternatives"][0]["id"], "A1")
        self.assertEqual(canonical["confidence"], 0.85)

    def test_wire_extractor_ignores_foreign_json_prefix(self):
        mixed = json.dumps(request()) + "\n" + json.dumps(wire_payload())
        self.assertEqual(qwen_provider._extract_wire_json(mixed), wire_payload())

    def test_bridge_adapter_remains_proposed_uncertified(self):
        result = interface.validate_result(model_payload(), "test-001", "QWEN35_4B_S")
        result["material_binding"] = {"model_sha256": "a" * 64}
        plan = bridge_adapter.bind_to_bridge(request(), result)
        self.assertFalse(plan["execution_allowed"])
        self.assertEqual(plan["status"], "PROPOSED_UNCERTIFIED")
        self.assertEqual(plan["g23"], "NOT_EXECUTED")
        self.assertEqual(plan["g24"], "NOT_EXECUTED")

    def test_bridge_adapter_rejects_authority_drift(self):
        result = interface.validate_result(model_payload(), "test-001", "QWEN35_4B_S")
        result["authority"]["execution"] = True
        with self.assertRaises(bridge_adapter.AdapterHold):
            bridge_adapter.bind_to_bridge(request(), result)

    def test_provider_uses_shell_false_and_wraps_advisory_result(self):
        manifest = {
            "interface": "REASONING_INTERFACE/1.0",
            "model": {"provider_id": "QWEN35_4B_S", "expected_sha256": "m"},
            "runtime": {"revision": "r"},
        }
        binding = {
            "f1_run_id": 1,
            "model": {"sha256": "m", "bytes": 1},
            "runtime": {"source_revision": "r", "binary_sha256": "b"},
        }
        completed = mock.Mock(returncode=0, stdout=json.dumps(wire_payload()), stderr="")
        fake = mock.Mock(return_value=completed)
        with mock.patch.object(qwen_provider, "verify_material", return_value=(manifest, binding, pathlib.Path("/m"), pathlib.Path("/r"))),              mock.patch.object(qwen_provider.subprocess, "run", fake):
            out = qwen_provider.invoke(request(), timeout_sec=1)
        self.assertFalse(out["execution_allowed"])
        kwargs = fake.call_args.kwargs
        self.assertIs(kwargs["shell"], False)
        cmd = fake.call_args.args[0]
        self.assertEqual(cmd[0], "/r")
        self.assertIn("--skip-chat-parsing", cmd)
        self.assertIn("--log-disable", cmd)
        self.assertIn("--reasoning", cmd)
        self.assertEqual(cmd[cmd.index("--reasoning") + 1], "on")
        self.assertEqual(cmd[cmd.index("-n") + 1], "1024")
        self.assertNotIn("bash", cmd)
        self.assertNotIn("sh", cmd)

    def test_provider_fail_closed_on_bad_json(self):
        manifest = {
            "interface": "REASONING_INTERFACE/1.0",
            "model": {"provider_id": "QWEN35_4B_S", "expected_sha256": "m"},
            "runtime": {"revision": "r"},
        }
        binding = {
            "f1_run_id": 1,
            "model": {"sha256": "m", "bytes": 1},
            "runtime": {"source_revision": "r", "binary_sha256": "b"},
        }
        completed = mock.Mock(returncode=0, stdout="not-json", stderr="")
        fake = mock.Mock(return_value=completed)
        with mock.patch.object(qwen_provider, "verify_material", return_value=(manifest, binding, pathlib.Path("/m"), pathlib.Path("/r"))),              mock.patch.object(qwen_provider.subprocess, "run", fake):
            with self.assertRaises(qwen_provider.ProviderHold):
                qwen_provider.invoke(request(), timeout_sec=1)


if __name__ == "__main__":
    unittest.main()
