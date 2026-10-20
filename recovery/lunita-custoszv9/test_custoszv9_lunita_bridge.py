import hashlib
import importlib.util
import json
import pathlib
import sys
import tempfile
import unittest
from datetime import datetime, timezone

ROOT = pathlib.Path(__file__).resolve().parents[2]
SOURCE = ROOT / "recovery/lunita-custoszv9/custoszv9_lunita_bridge.py"
SPEC = importlib.util.spec_from_file_location("custoszv9_lunita_bridge", SOURCE)
BRIDGE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = BRIDGE
SPEC.loader.exec_module(BRIDGE)


class CustoszV9LunitaBridgeContractTests(unittest.TestCase):
    def test_sha256_helper_matches_known_digest(self):
        self.assertEqual(
            BRIDGE.sha256_bytes(b"abc"),
            "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad",
        )

    def test_task_is_bounded_and_scoped_to_existing_mission(self):
        task = BRIDGE.create_task("a" * 64, "bridge-selftest-task", "/tmp/authorization.json")
        self.assertEqual(task["mission_id"], "CUSTOSZ_MISION1_0a36c59d4baf")
        self.assertEqual(task["authorized_scope"], "MISION1_CAJITA_LUNITA")
        self.assertEqual(task["resource_budget"]["max_concurrency"], 1)
        self.assertEqual(task["maximum_planning_budget"], 2)
        self.assertEqual(task["maximum_retry_budget"], 0)
        self.assertEqual(task["authorization_evidence_reference"], "/tmp/authorization.json")
        self.assertIn("execution_deadline", task)

    def test_valid_local_authorization_is_scope_bound_and_not_certification(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            contract_path = directory / "contract.json"
            auth_path = directory / "authorization.json"
            contract_path.write_text(json.dumps({
                "mission_sha256": BRIDGE.MISSION_SHA256,
                "status": "ACTIVE_UNBOUNDED_CONTRACT",
                "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                "scope": "MISION1_CAJITA_LUNITA",
            }), encoding="utf-8")
            auth_path.write_text(json.dumps({
                "mission_sha256": BRIDGE.MISSION_SHA256,
                "authorization_mode": "UNBOUNDED_NO_EXPIRY",
                "scope": "MISION1_CAJITA_LUNITA",
                "allowed_effects": [
                    "read project artifacts",
                    "checkpointed changes inside scope",
                ],
            }), encoding="utf-8")
            original_contract, original_auth = BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH
            BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = contract_path, auth_path
            try:
                task = {
                    "task_id": "bounded-unit-test",
                    "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                    "authorized_scope": "MISION1_CAJITA_LUNITA",
                    "authorization_evidence_reference": str(auth_path),
                    "permitted_effects": ["READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT"],
                }
                result = BRIDGE.validate_local_authorization(task)
            finally:
                BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = original_contract, original_auth
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["canonical_promotion_authorized"])
            self.assertFalse(result["certification_authority"])
            self.assertEqual(result["authorization_scope"], "MISION1_CAJITA_LUNITA")

    def test_wrong_mission_hash_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            contract_path = directory / "contract.json"
            auth_path = directory / "authorization.json"
            contract_path.write_text(json.dumps({
                "mission_sha256": "0" * 64,
                "status": "ACTIVE_UNBOUNDED_CONTRACT",
                "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                "scope": "MISION1_CAJITA_LUNITA",
            }), encoding="utf-8")
            auth_path.write_text(json.dumps({
                "mission_sha256": BRIDGE.MISSION_SHA256,
                "authorization_mode": "UNBOUNDED_NO_EXPIRY",
                "scope": "MISION1_CAJITA_LUNITA",
                "allowed_effects": ["read project artifacts", "checkpointed changes inside scope"],
            }), encoding="utf-8")
            original_contract, original_auth = BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH
            BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = contract_path, auth_path
            try:
                result = BRIDGE.validate_local_authorization({
                    "task_id": "wrong-hash",
                    "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                    "authorized_scope": "MISION1_CAJITA_LUNITA",
                    "authorization_evidence_reference": str(auth_path),
                    "permitted_effects": ["READ_PROJECT_ARTIFACTS"],
                })
            finally:
                BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = original_contract, original_auth
            self.assertEqual(result["status"], "DENIED")
            self.assertEqual(result["reason"], "MISSION_IDENTITY_MISMATCH")

    def test_effect_outside_allowlist_is_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            directory = pathlib.Path(tmp)
            contract_path = directory / "contract.json"
            auth_path = directory / "authorization.json"
            contract_path.write_text(json.dumps({
                "mission_sha256": BRIDGE.MISSION_SHA256,
                "status": "ACTIVE_UNBOUNDED_CONTRACT",
                "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                "scope": "MISION1_CAJITA_LUNITA",
            }), encoding="utf-8")
            auth_path.write_text(json.dumps({
                "mission_sha256": BRIDGE.MISSION_SHA256,
                "authorization_mode": "UNBOUNDED_NO_EXPIRY",
                "scope": "MISION1_CAJITA_LUNITA",
                "allowed_effects": ["read project artifacts"],
            }), encoding="utf-8")
            original_contract, original_auth = BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH
            BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = contract_path, auth_path
            try:
                result = BRIDGE.validate_local_authorization({
                    "task_id": "effect-denial",
                    "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
                    "authorized_scope": "MISION1_CAJITA_LUNITA",
                    "authorization_evidence_reference": str(auth_path),
                    "permitted_effects": ["WRITE_LOCAL_AUDIT"],
                })
            finally:
                BRIDGE.CONTRACT_PATH, BRIDGE.AUTH_PATH = original_contract, original_auth
            self.assertEqual(result["status"], "DENIED")
            self.assertEqual(result["reason"], "EFFECT_NOT_AUTHORIZED")

    def test_missing_and_malformed_json_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = pathlib.Path(tmp) / "missing.json"
            with self.assertRaises(BRIDGE.BridgeError):
                BRIDGE.read_json(missing)
            malformed = pathlib.Path(tmp) / "malformed.json"
            malformed.write_text("[]", encoding="utf-8")
            with self.assertRaises(BRIDGE.BridgeError):
                BRIDGE.read_json(malformed)

    def test_version_and_model_identity_are_pinned(self):
        self.assertEqual(len(BRIDGE.V9_EXPECTED_SHA256), 64)
        self.assertEqual(BRIDGE.CANDIDATE_ID, "G06_REBUILD_CANDIDATE_R1")
        self.assertFalse(BRIDGE.sha256_bytes(b"candidate") == BRIDGE.V9_EXPECTED_SHA256)

    def test_task_deadline_is_timezone_aware(self):
        task = BRIDGE.create_task("b" * 64, "deadline-unit-test", "/tmp/auth.json")
        deadline = datetime.fromisoformat(task["execution_deadline"])
        self.assertIsNotNone(deadline.tzinfo)
        self.assertGreater(deadline, datetime.now(timezone.utc))


if __name__ == "__main__":
    unittest.main(verbosity=2)
