import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "louksna1_integral_mission.py"
SPEC = importlib.util.spec_from_file_location("louksna1_integral_mission", MODULE_PATH)
MISSION = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MISSION)


def passing_matrix():
    rows = []
    for target in MISSION.CANONICAL_TARGETS:
        detail = {}
        if target in MISSION.MODEL_TARGETS:
            detail["reference_kind"] = "AUTHORIZED_REFERENCE_MODEL"
        rows.append({
            "target_id": target,
            "status": "PASS",
            "exit_code": 0,
            "detail": detail,
            "worker_certification": "NOT_GRANTED",
        })
    return rows


class DecisionTests(unittest.TestCase):
    def test_partial_execution_is_not_granted(self):
        matrix = passing_matrix()
        matrix[0]["status"] = "FAIL"
        matrix[0]["exit_code"] = 4
        decision = MISSION.decide(
            matrix,
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Android"},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
        )
        self.assertEqual(decision["global_certification"], "NOT_GRANTED")
        self.assertEqual(decision["gates"]["coverage_21"]["status"], "FAIL")

    def test_worker_self_grant_is_rejected(self):
        decision = MISSION.decide(
            passing_matrix(),
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Android"},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="GRANTED",
        )
        self.assertEqual(decision["global_certification"], "NOT_GRANTED")
        self.assertEqual(decision["gates"]["independence"]["status"], "FAIL")

    def test_artifact_copy_rollback_does_not_grant(self):
        decision = MISSION.decide(
            passing_matrix(),
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Android"},
            {"status": "PASS", "scope": "EXECUTED_ARTIFACT_COPY_NOT_PRODUCT_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
        )
        self.assertEqual(decision["gates"]["rollback"]["status"], "FAIL")
        self.assertEqual(decision["global_certification"], "NOT_GRANTED")

    def test_all_mandatory_gates_can_grant(self):
        decision = MISSION.decide(
            passing_matrix(),
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Android"},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
            axiom_established=True,
        )
        self.assertEqual(decision["global_certification"], "GRANTED")
        self.assertEqual(decision["authority"], "INDEPENDENT_VALIDATOR_NOT_SELF_CERTIFICATION")
        self.assertNotEqual(decision["gates"]["independence"]["worker"], decision["gates"]["independence"]["evaluator"])


if __name__ == "__main__":
    unittest.main()
