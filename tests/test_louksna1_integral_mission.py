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

    def test_product_candidate_rollback_restores_identity_without_touching_source(self):
        candidate = self.runtime / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
        before = candidate.read_bytes()
        result = MISSION.rollback_probe(self.runtime)
        self.assertEqual(candidate.read_bytes(), before)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["scope"], "PRODUCT_CANDIDATE_UPDATE")
        self.assertTrue(result["tampered_identity_rejected"])
        self.assertTrue(result["reexecuted_identity_match"])
        self.assertTrue(result["source_untouched"])
        self.assertEqual(result["restored_candidate_id"], MISSION.CANDIDATE_ID)

    def test_published_bytes_stay_bound_and_missing_distribution_does_not_pass(self):
        repo = Path(__file__).resolve().parents[1]
        report = MISSION.provenance_report(repo, MISSION.git_head(repo))
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("RUNTIME_DISTRIBUTION_MISSING", report["problems"])
        self.assertIn("PUBLISHED_MANIFEST_SOURCE_COMMIT_DIFFERS_FROM_EXECUTION_HEAD", report["problems"])
        self.assertNotIn("LOUKSNA1_HASH_MISMATCH", report["problems"])
        self.assertNotIn("PROTECTED_ARCHITECTURE_HASH_MISMATCH", report["problems"])
        self.assertNotIn("PROTECTED_ARCHITECTURE_MISSING", report["problems"])

    def test_linux_without_android_emulator_does_not_pass_host(self):
        decision = MISSION.decide(
            passing_matrix(),
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Linux-6.8", "android_emulator": {"verified": False}},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
            axiom_established=True,
        )
        self.assertEqual(decision["gates"]["host_resources"]["status"], "FAIL")
        self.assertEqual(decision["global_certification"], "NOT_GRANTED")

    def test_verified_android_emulator_witness_satisfies_host_gate(self):
        decision = MISSION.decide(
            passing_matrix(),
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Linux-6.8", "android_emulator": {"verified": True, "sdk": "34", "qemu": "1"}},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
            axiom_established=True,
        )
        self.assertEqual(decision["gates"]["host_resources"]["status"], "PASS")

    def test_open_engines_fail_closed_when_absent(self):
        missing = "/tmp/louksna1-missing-engine"
        for key in ("LOUKSNA1_LLAMA_CLI", "LOUKSNA1_WHISPER_CLI", "LOUKSNA1_MARIAN_DECODER", "LOUKSNA1_TESSERACT", "LOUKSNA1_Z3"):
            os.environ[key] = missing
        os.environ.pop("LOUKSNA1_ANDROID_WITNESS", None)
        runtime = self.runtime
        try:
            self.assertEqual(MISSION.op_cerebro(runtime)["reason"], "LLAMA_CPP_NOT_INSTALLED")
            self.assertEqual(MISSION.op_transcribe()["reason"], "WHISPER_CPP_NOT_INSTALLED")
            self.assertEqual(MISSION.op_translate()["reason"], "MARIAN_NOT_INSTALLED")
            self.assertEqual(MISSION.op_docling()["reason"], "TESSERACT_NOT_INSTALLED")
            self.assertEqual(MISSION.op_reasoning(runtime)["reason"], "LLAMA_CPP_NOT_INSTALLED")
            self.assertFalse(MISSION.z3_structural_check()["establishes_axiom_propositions"])
            witness = MISSION.read_android_witness()
            self.assertFalse(witness["verified"])
            self.assertEqual(witness["reason"], "ANDROID_EMULATOR_NOT_EXECUTED")
        finally:
            for key in ("LOUKSNA1_LLAMA_CLI", "LOUKSNA1_WHISPER_CLI", "LOUKSNA1_MARIAN_DECODER", "LOUKSNA1_TESSERACT", "LOUKSNA1_Z3"):
                os.environ.pop(key, None)

    def test_marian_without_pinned_model_does_not_authorize_the_rank4_candidate(self):
        with tempfile.TemporaryDirectory() as temp_name:
            binary = Path(temp_name) / "marian-decoder"
            binary.write_text("#!/bin/sh\nprintf 'marian 1.9.0\\n'\n", encoding="utf-8")
            binary.chmod(0o755)
            os.environ["LOUKSNA1_MARIAN_DECODER"] = str(binary)
            os.environ.pop("LOUKSNA1_MARIAN_MODEL", None)
            os.environ.pop("LOUKSNA1_MARIAN_VOCAB", None)
            os.environ.pop("LOUKSNA1_MARIAN_CONFIG", None)
            try:
                row = MISSION.op_translate()
            finally:
                os.environ.pop("LOUKSNA1_MARIAN_DECODER", None)
        self.assertEqual(row["status"], "FAIL")
        self.assertEqual(row["reason"], "MARIAN_REFERENCE_MODEL_MISSING")
        self.assertNotEqual(row["detail"].get("reference_kind"), "AUTHORIZED_REFERENCE_MODEL")

    def test_reference_known_answer_counts_toward_coverage_not_semantic_equivalence(self):
        matrix = passing_matrix()
        for row in matrix:
            if row["target_id"] in MISSION.MODEL_TARGETS:
                row["detail"] = {"reference_known_answer": "PASS", "low_rank_candidate_equivalent": False}
        decision = MISSION.decide(
            matrix,
            {"status": "PASS", "problems": []},
            {"confidence": "MEASURED", "platform": "Linux-6.8", "android_emulator": {"verified": True, "sdk": "34", "qemu": "1"}},
            {"status": "PASS", "scope": "PRODUCT_CANDIDATE_UPDATE"},
            {"status": "PASS", "problems": []},
            worker_claim="NOT_GRANTED",
        )
        self.assertEqual(decision["gates"]["coverage_21"]["status"], "PASS")
        self.assertEqual(len(decision["gates"]["coverage_21"]["passed"]), 21)
        self.assertEqual(decision["gates"]["semantic_quality"]["status"], "FAIL")
        self.assertEqual(decision["global_certification"], "NOT_GRANTED")


if __name__ == "__main__":
    unittest.main()
