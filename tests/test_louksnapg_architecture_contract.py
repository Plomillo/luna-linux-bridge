import importlib.util
import json
import unittest
import sys
from copy import deepcopy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
MODULE = ROOT / "tools" / "louksnapg_architecture_contract.py"
SPEC = importlib.util.spec_from_file_location("louksnapg_architecture_contract", MODULE)
contract_gate = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(contract_gate)
CONTRACT_PATH = ROOT / "contracts" / "louksnapg" / "architecture-contract.v1.json"


class ArchitectureContractTests(unittest.TestCase):
    def setUp(self):
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))

    def test_canonical_contract_is_valid_and_has_six_obligations(self):
        from louksnapg_integral_gate import EXPECTED_TARGET_IDS
        self.assertEqual(contract_gate.validate_contract(self.contract, EXPECTED_TARGET_IDS), [])
        self.assertEqual(len(self.contract["obligations"]), 6)

    def test_custosz_must_remain_primary_and_kestra_secondary(self):
        bad = deepcopy(self.contract)
        bad["workers"]["primary"]["id"] = "KESTRA"
        bad["workers"]["secondary"]["id"] = "CUSTOSZ_V9"
        failures = contract_gate.validate_contract(bad)
        self.assertIn("PRIMARY_WORKER_MUST_BE_CUSTOSZ_V9", failures)
        self.assertIn("SECONDARY_WORKER_MUST_BE_KESTRA", failures)

    def test_remote_commander_and_heavy_downloads_cannot_be_enabled(self):
        for field in ("remote_commander_use", "heavy_model_weights_download"):
            with self.subTest(field=field):
                bad = deepcopy(self.contract)
                bad["prohibitions"][field] = True
                self.assertIn("PROHIBITED_ACTION_POLICY_CHANGED", contract_gate.validate_contract(bad))

    def test_synthetic_target_set_or_missing_workers_cannot_release(self):
        bad = {
            "schema": self.contract["evidence_schema"],
            "contract_sha256": "0" * 64,
            "source_commit": "a" * 40,
            "bundle_sha256": "b" * 64,
            "worker_runs": {},
            "official_source_review": {"status": "HOLD", "models": []},
            "repair_result": {"status": "HOLD"},
            "functional_gate": {"decision": "HOLD", "target_pass_count": 0, "synthetic_only": True},
            "telemetry": {"status": "HOLD", "events": []},
            "kestra_audit": {"status": "HOLD"},
            "g23": {"status": "NOT_PERFORMED"},
            "g24": {"status": "NOT_GRANTED"},
            "safety": {"heavy_model_download_count": 0, "remote_commander_used": False, "canonical_mutation": False, "synthetic_evidence_used": True}
        }
        result = contract_gate.evaluate_execution_evidence(self.contract, CONTRACT_PATH.read_bytes(), bad)
        self.assertFalse(result["release_eligible"])
        self.assertEqual(result["decision"], "HOLD_NOT_CERTIFIED")
        self.assertIn("WORKER_REAL_RUN_ID_MISSING:CUSTOSZ_V9", result["failures"])
        self.assertIn("REAL_21_TARGET_FUNCTIONAL_GATE_NOT_PASS", result["failures"])
        self.assertEqual(result["global_certification"], "NOT_GRANTED_BY_THIS_VALIDATOR")

    def test_missing_execution_evidence_cannot_be_treated_as_certification(self):
        # Static contract integrity is not product evidence or certification.
        result = contract_gate.main(["--contract", str(CONTRACT_PATH), "--require-execution-evidence"])
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
