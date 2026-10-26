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

    def test_official_revisions_and_no_model_substitution_are_contract_invariants(self):
        bad_source = deepcopy(self.contract)
        row = next(x for x in bad_source["source_catalog"] if x["target_id"] == "D04_TRADUCCION_GENERAL")
        row["official_source_revision_commit"] = "0" * 40
        failures = contract_gate.validate_contract(bad_source)
        self.assertIn("OFFICIAL_SOURCE_REVISION_COMMIT_MISMATCH:D04_TRADUCCION_GENERAL", failures)

        bad_variant = deepcopy(self.contract)
        row = next(x for x in bad_variant["source_catalog"] if x["target_id"] == "D06_ANALISIS_AVANZADO")
        row["allowed_variants"] = ["Qwen/Qwen3-8B"]
        failures = contract_gate.validate_contract(bad_variant)
        self.assertIn("UNAUTHORIZED_MODEL_VARIANT_SUBSTITUTION_ALLOWED:D06_ANALISIS_AVANZADO", failures)

    def test_calibre_official_source_lock_and_overlay_match_contract(self):
        self.assertEqual(contract_gate.validate_calibre_source_lock(self.contract), [])

        changed = deepcopy(self.contract)
        changed["toolchain_pins"][0]["commit_sha"] = "0" * 40
        failures = contract_gate.validate_contract(changed)
        self.assertIn("CALIBRE_TOOLCHAIN_PIN_MISMATCH:commit_sha", failures)

        changed = deepcopy(self.contract)
        changed["toolchain_pins"][0]["overlay_archive"]["sha256"] = "0" * 64
        failures = contract_gate.validate_contract(changed)
        self.assertIn("CALIBRE_OVERLAY_ARCHIVE_PIN_MISMATCH", failures)

    def test_global_distribution_and_runtime_caps_are_immutable(self):
        bad = deepcopy(self.contract)
        bad["candidate_distribution_max_bytes"] = 490000000
        failures = contract_gate.validate_contract(bad)
        self.assertIn("CANDIDATE_DISTRIBUTION_CAP_MISMATCH", failures)

        bad = deepcopy(self.contract)
        bad["cajita_runtime_archive_max_bytes"] = 479000000
        failures = contract_gate.validate_contract(bad)
        self.assertIn("CAJITA_RUNTIME_CAP_MISMATCH", failures)

    def test_custosz_repair_mission_scope_targets_and_safety_are_contract_invariants(self):
        bad = deepcopy(self.contract)
        bad["worker_mission"]["authorized_scope"] = "BUILD_ONLY"
        self.assertIn("CUSTOSZ_REPAIR_MISSION_SCOPE_MISMATCH", contract_gate.validate_contract(bad))

        bad = deepcopy(self.contract)
        bad["worker_mission"]["repair_target_ids"].remove("D06_MIGRACION_PERSISTENCIA")
        self.assertIn("CUSTOSZ_REPAIR_TARGET_REGISTRY_INVALID", contract_gate.validate_contract(bad))

        bad = deepcopy(self.contract)
        bad["worker_mission"]["remote_commander_used"] = True
        self.assertIn("CUSTOSZ_REPAIR_SAFETY_POLICY_INVALID", contract_gate.validate_contract(bad))

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
        self.assertIn("CUSTOSZ_REPAIR_MISSION_RECEIPT_MISSING", result["failures"])
        self.assertIn("REAL_21_TARGET_FUNCTIONAL_GATE_NOT_PASS", result["failures"])
        self.assertEqual(result["global_certification"], "NOT_GRANTED_BY_THIS_VALIDATOR")

    def test_missing_execution_evidence_cannot_be_treated_as_certification(self):
        # Static contract integrity is not product evidence or certification.
        result = contract_gate.main(["--contract", str(CONTRACT_PATH), "--require-execution-evidence"])
        self.assertEqual(result, 2)


if __name__ == "__main__":
    unittest.main()
