"""Adversarial tests for the candidate's bounded metacognitive automation."""
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import elastic_automation as elastic
import lrb_core as base

CONTRACT = json.loads((ROOT / "CONTRACT.v0.json").read_text())
CLOCK = lambda: datetime(2030, 1, 1, tzinfo=timezone.utc)


def good_observation():
    return {"memory_bytes": {"MemTotal": 1000, "MemAvailable": 900},
            "root_fs_bytes": {"available": 2 * 1024 * 1024 * 1024},
            "load": [0.1, 0.1, 0.1], "host": "TEST_ONLY"}


def mission(steps=None):
    steps = steps or [{"kind": "OBSERVE_LOCAL"}]
    return {"mission_id": "safe-001",
            "user_objective": "Inspeccionar la máquina sin cambios",
            "model_proposal": "Revisar evidencia; no afirmar certificación",
            "model": {"declared_name": "SIMULATED_MODEL",
                      "declared_version": "UNVERIFIED_TEST_VERSION"},
            "deadline_utc": "2030-01-02T00:00:00Z",
            "max_auto_steps": 8,
            "steps": steps}


class ElasticNegativeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.agent = elastic.Automation(Path(self.tmp.name) / "state",
                                        CONTRACT, observer=good_observation, clock=CLOCK)

    def tearDown(self):
        self.tmp.cleanup()

    def test_admit_is_idempotent_and_never_certifies(self):
        first = self.agent.admit(mission())
        second = self.agent.admit(mission())
        self.assertEqual(second["operation"], "IDEMPOTENT_EXISTING")
        self.assertEqual(first["mission_sha256"], second["mission_sha256"])
        self.assertFalse(first["certified"])
        self.assertEqual(first["g24"], "NOT_EXECUTED")

    def test_same_id_different_scope_holds(self):
        self.agent.admit(mission())
        changed = mission()
        changed["user_objective"] = "Borrar archivos"
        with self.assertRaisesRegex(RuntimeError, "MISSION_SCOPE_COLLISION"):
            self.agent.admit(changed)

    def test_two_readonly_steps_resume_exactly_once(self):
        request = mission([{"kind": "OBSERVE_LOCAL"}, {"kind": "OBSERVE_LOCAL"}])
        self.agent.admit(request)
        one = self.agent.run_once("safe-001")
        two = self.agent.run_once("safe-001")
        three = self.agent.run_once("safe-001")
        self.assertEqual(one["next_step"], 1)
        self.assertEqual(two["next_step"], 2)
        self.assertEqual(three["operation"], "IDEMPOTENT_NOOP")
        self.assertEqual(len(three["evidence"]), 2)
        self.assertEqual(three["status"], "COMPLETE_READONLY_UNCERTIFIED")

    def test_gated_operation_stops_before_resource_probe(self):
        def no_probe():
            raise AssertionError("No observations or root operations at this gate")
        self.agent.observer = no_probe
        request = mission([{"kind": "GATED_OPERATION",
                            "requested_capability": "CAP_STORAGE_FSTAB_FIX"}])
        self.agent.admit(request)
        blocked = self.agent.run_once("safe-001")
        self.assertEqual(blocked["status"], "WAITING_FRESH_G23_G24")
        self.assertFalse(blocked["privileged_execution"])
        self.assertEqual(self.agent.run_once("safe-001")["operation"], "IDEMPOTENT_NOOP")

    def test_memory_pressure_holds_without_advancing(self):
        def pressured():
            result = good_observation()
            result["memory_bytes"]["MemAvailable"] = 25
            return result
        self.agent.observer = pressured
        self.agent.admit(mission())
        blocked = self.agent.run_once("safe-001")
        self.assertEqual(blocked["status"], "HOLD_RESOURCE_PRESSURE")
        self.assertEqual(blocked["next_step"], 0)
        self.agent.observer = good_observation
        self.assertEqual(self.agent.run_once("safe-001")["next_step"], 1)

    def test_unmeasured_resources_hold(self):
        self.agent.observer = lambda: {"memory_bytes": {}, "root_fs_bytes": {},
                                        "load": []}
        self.agent.admit(mission())
        self.assertEqual(self.agent.run_once("safe-001")["status"],
                         "HOLD_MISSING_RESOURCE_EVIDENCE")

    def test_expired_deadline_never_executes(self):
        request = mission()
        request["deadline_utc"] = "2029-12-31T00:00:00Z"
        with self.assertRaisesRegex(RuntimeError, "MISSION_CAPACITY_OR_DEADLINE"):
            self.agent.admit(request)

    def test_script_or_extra_field_injection_rejected(self):
        for step in ({"kind": "OBSERVE_LOCAL", "sudo": "bash"},
                     {"kind": "ROOT_SHELL"},
                     {"kind": "GATED_OPERATION", "requested_capability": "sudo",
                      "shell": "bash"}):
            with self.subTest(step=step):
                with self.assertRaises(RuntimeError):
                    elastic.validate(mission([step]), {"max_work_seconds": 1200})

    def test_unverified_model_version_rejected_if_missing(self):
        request = mission()
        request["model"]["declared_version"] = ""
        with self.assertRaisesRegex(RuntimeError, "DECLARED_MODEL"):
            self.agent.admit(request)

    def test_evidence_chain_tampering_blocks_resumption(self):
        self.agent.admit(mission())
        log = self.agent.ledger.path
        log.write_text(log.read_text().replace("ELASTIC_INTENT", "ELASTIC_FORGED", 1))
        with self.assertRaisesRegex(RuntimeError, "EVIDENCE_HASH_BROKEN"):
            self.agent.run_once("safe-001")

    def test_state_rollback_or_tamper_blocks_resumption(self):
        self.agent.admit(mission())
        file = self.agent.store
        data = json.loads(file.read_text())
        data["revision"] = 0
        file.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, "ELASTIC_STATE_ROLLBACK_OR_TAMPERING"):
            self.agent.run_once("safe-001")

    def test_incomplete_transaction_blocks_silent_retry(self):
        self.agent.admit(mission())
        self.agent.ledger.append("ELASTIC_INTENT", {"tx": "unclosed", "kind": "TEST"})
        with self.assertRaisesRegex(RuntimeError, "INCOMPLETE_TRANSACTION_HOLD"):
            self.agent.run_once("safe-001")

    def test_project_index_is_bounded_and_has_no_names_in_result(self):
        target = Path(self.tmp.name) / "priority"
        target.mkdir()
        (target / "allowed").mkdir()
        self.agent.admit(mission([{"kind": "INDEX_PRIORITY",
                                  "root": str(target), "limit": 1}]))
        result = self.agent.run_once("safe-001")
        self.assertEqual(result["status"], "COMPLETE_READONLY_UNCERTIFIED")
        self.assertNotIn("allowed", json.dumps(result))
        self.assertEqual(result["evidence"][0]["effect"], "READ_ONLY")


if __name__ == "__main__":
    unittest.main()
