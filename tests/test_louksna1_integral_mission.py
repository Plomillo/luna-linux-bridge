import importlib.util
import json
import os
import tempfile
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


class ExecutableGateTests(unittest.TestCase):
    def setUp(self):
        self.runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime"

    def test_calibre_lock_matches_pinned_binary(self):
        pin, problem = MISSION.calibre_pin(self.runtime)
        self.assertEqual(problem, "")
        self.assertEqual(pin["sha256"], MISSION.CALIBRE_SHA256)
        self.assertEqual(pin["size_bytes"], MISSION.CALIBRE_BYTES)

    def test_cmake_without_windows_witness_is_not_executed(self):
        os.environ.pop("LOUKSNA1_CMAKE_WITNESS", None)
        row = MISSION.op_cmake(self.runtime)
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["reason"], "WINDOWS_CMAKE_HOST_NOT_EXECUTED")

    def test_cmake_witness_must_match_extracted_exe_and_version(self):
        archive = self.runtime / "6. Sistema Inteligente" / "Portabilidad base" / "CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE.7z"
        with tempfile.TemporaryDirectory(prefix="louksna1-cmake-test-") as temp_name:
            temp = Path(temp_name)
            exe = MISSION.extract_cmake_exe(archive, temp / "extract")
            digest = MISSION.sha256_file(exe)
            witness = temp / "witness.json"
            witness.write_text(json.dumps({
                "status": "PASS",
                "archive_sha256": MISSION.CMAKE_ARCHIVE_SHA256,
                "cmake_exe_sha256": digest,
                "exit_code": 0,
                "echo_exit_code": 0,
                "version_stdout": "CMake Error: Could not find CMAKE_ROOT !!!\ncmake version 4.4.3\n",
                "echo_stdout": MISSION.CMAKE_ECHO + "\n",
                "platform": "Microsoft Windows NT 10.0.26100.0",
                "runner_os": "Windows",
            }), encoding="utf-8")
            os.environ["LOUKSNA1_CMAKE_WITNESS"] = str(witness)
            try:
                rejected = MISSION.op_cmake(self.runtime)
                witness.write_text(json.dumps({
                    "status": "FAIL",
                    "archive_sha256": MISSION.CMAKE_ARCHIVE_SHA256,
                    "cmake_exe_sha256": digest,
                    "exit_code": 0,
                    "echo_exit_code": 0,
                    "version_stdout": "cmake version 4.4.3\nCMake suite maintained and supported by Kitware (kitware.com/cmake).\n",
                    "echo_stdout": MISSION.CMAKE_ECHO + "\n",
                    "platform": "Microsoft Windows NT 10.0.26100.0",
                    "runner_os": "Windows",
                }), encoding="utf-8")
                accepted = MISSION.op_cmake(self.runtime)
            finally:
                os.environ.pop("LOUKSNA1_CMAKE_WITNESS", None)
        self.assertEqual(rejected["status"], "FAIL")
        self.assertEqual(rejected["reason"], "CMAKE_WINDOWS_OUTPUT_MISMATCH")
        self.assertEqual(accepted["status"], "PASS")
        self.assertEqual(accepted["detail"]["cmake_exe_sha256"], digest)
        self.assertTrue(accepted["detail"]["independent_exe_hash_checked"])
        self.assertNotIn("status", accepted["detail"])


if __name__ == "__main__":
    unittest.main()
