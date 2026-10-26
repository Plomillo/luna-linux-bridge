import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
import louksnapg_worker_mission as worker


class CustoszWorkerMissionTests(unittest.TestCase):
    def test_worker_bundle_and_runtime_caps_are_separate_and_exact(self):
        with tempfile.TemporaryDirectory(prefix="louksnapg-worker-contract-") as tmp:
            root = Path(tmp)
            paths = {}
            for name in ("document", "runtime", "source_architecture", "cajita_doc", "architecture_contract"):
                path = root / (name + ".txt")
                path.write_text(name + "\n", encoding="utf-8")
                paths[name] = path

            task = worker.build_task("a" * 40, paths)
            acceptance = set(task["acceptance_criteria"])
            self.assertIn("output_within_479000000_bytes", acceptance)
            self.assertIn("runtime_archive_within_470000000_bytes", acceptance)
            self.assertNotIn("output_within_470000000_bytes", acceptance)
            self.assertEqual(task["authorized_scope"], "VERIFY_REPAIR_PRIMITIVES_AND_BUILD_LOUKSNAPG_CANDIDATE")
            self.assertEqual(task["permitted_effects"], ["WRITE_EVIDENCE"])
            self.assertIn("NO_SELF_CERTIFICATION", task["preconditions"])
            self.assertIn("FAIL_CLOSED", task["preconditions"])
            self.assertIn("REPAIR_SOURCE_HASHES_PINNED", task["preconditions"])
            self.assertIn("REAL_CANDIDATE_PRIMITIVE_TESTS_REQUIRED", task["preconditions"])
            self.assertEqual(set(task["required_capabilities"]), {"verify_repair_primitives", "build_single_file_distribution"})
            self.assertIn("three_repaired_non_model_primitives_executed_on_exact_candidate_and_outcomes_bound", acceptance)

    def test_repair_preflight_matches_the_real_packaged_trealla_driver(self):
        source = (ROOT / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        tests = (ROOT / "tests" / "test_cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        self.assertEqual(worker.repair_source_contract_failures(source, tests), [])

        # The old, impossible requirement put use_module() inside the query;
        # the correct implementation imports DCGs before loading the shipped grammar.
        self.assertNotIn(
            'query="use_module(library(dcgs)),phrase(sentence,[the,man,shoots]),write(true),halt"',
            source,
        )

    def test_repair_preflight_rejects_a_missing_real_runtime_fix(self):
        source = (ROOT / "tools" / "cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        tests = (ROOT / "tests" / "test_cajita_extended_target_e2e.py").read_text(encoding="utf-8")
        source = source.replace('trealla_env["TPL_LIBRARY_PATH"]=str(packaged_library)', "")
        failures = worker.repair_source_contract_failures(source, tests)
        self.assertIn('trealla_env["TPL_LIBRARY_PATH"]=str(packaged_library)', failures)

    def _bound_worker_result_with_a_primitive_blocker(self):
        source_commit = "a" * 40
        bundle_sha = "b" * 64
        contract_sha = "c" * 64
        report_sha = "d" * 64
        primitive = {
            "schema": "LOUKSNAPG_CUSTOSZ_PRIMITIVE_REPAIR_EVIDENCE/1.0",
            "status": "PASS_EVIDENCE_BOUND",
            "report_completed": True,
            "source_commit": source_commit,
            "bundle_sha256": bundle_sha,
            "contract_sha256": contract_sha,
            "report_sha256": report_sha,
            "all_target_outcomes_recorded": True,
            "targeted_repairs_all_pass": False,
            "target_status": {
                "D04_HERMENEUTICA_HG": "PASS_PRIMITIVE_SMOKE",
                "D04_TRADUCCION_LENGUAS_ANTIGUAS": "BLOCKED",
                "D06_MIGRACION_PERSISTENCIA": "PASS_PRIMITIVE_SMOKE",
            },
            "heavy_model_weight_download_count": 0,
            "remote_commander_used": False,
            "synthetic_evidence_used_as_product_proof": False,
        }
        action = {
            "exit_code": 0,
            "architecture_contract_sha256": contract_sha,
            "repair_preflight": {"status": "PASS"},
            "candidate_independent_validation": {
                "exit_code": 0,
                "container_integrity": "PASS",
                "runtime_member_integrity": "PASS",
                "source_commit": source_commit,
                "bundle_sha256": bundle_sha,
            },
            "primitive_repair_evidence": primitive,
            "primitive_report_sha256": report_sha,
            "repair_status": "HOLD_REPAIR_BLOCKERS_RECORDED",
        }
        build = {
            "bundle_bytes": 1234,
            "bundle_sha256": bundle_sha,
            "source_commit": source_commit,
            "identity_preservation_status": "PASS_SOURCE_IDENTITY_PRESERVED",
            "engine_replacement": "FORBIDDEN",
        }
        return source_commit, bundle_sha, contract_sha, action, build

    def test_complete_primitive_failures_are_recorded_without_suppressing_g23_g24(self):
        source_commit, bundle_sha, contract_sha, action, build = self._bound_worker_result_with_a_primitive_blocker()
        completed = worker.bounded_mission_completion_is_valid(
            coordinator_status="COMPLETED",
            action_result=action,
            output_exists=True,
            output_size=1234,
            max_bytes=479000000,
            output_hash=bundle_sha,
            expected_source_commit=source_commit,
            expected_contract_sha256=contract_sha,
            build_report=build,
        )
        self.assertTrue(completed)
        self.assertEqual(action["repair_status"], "HOLD_REPAIR_BLOCKERS_RECORDED")
        self.assertFalse(action["primitive_repair_evidence"]["targeted_repairs_all_pass"])
        self.assertEqual(action["primitive_repair_evidence"]["target_status"]["D04_TRADUCCION_LENGUAS_ANTIGUAS"], "BLOCKED")

    def test_incomplete_or_unbound_primitive_failure_report_still_blocks_worker_completion(self):
        source_commit, bundle_sha, contract_sha, action, build = self._bound_worker_result_with_a_primitive_blocker()
        del action["primitive_repair_evidence"]["target_status"]["D06_MIGRACION_PERSISTENCIA"]
        completed = worker.bounded_mission_completion_is_valid(
            coordinator_status="COMPLETED",
            action_result=action,
            output_exists=True,
            output_size=1234,
            max_bytes=479000000,
            output_hash=bundle_sha,
            expected_source_commit=source_commit,
            expected_contract_sha256=contract_sha,
            build_report=build,
        )
        self.assertFalse(completed)

    def test_worker_cannot_self_certify_or_expand_scope_silently(self):
        with tempfile.TemporaryDirectory(prefix="louksnapg-worker-contract-") as tmp:
            root = Path(tmp)
            paths = {}
            for name in ("document", "runtime", "source_architecture", "cajita_doc", "architecture_contract"):
                path = root / (name + ".txt")
                path.write_text(name + "\n", encoding="utf-8")
                paths[name] = path
            task = worker.build_task("b" * 40, paths)
            self.assertEqual(worker.authorize(task)["status"], "PASS")
            task["authorized_scope"] = "REPAIR_OR_PROMOTE_GLOBAL_PRODUCT"
            self.assertEqual(worker.authorize(task)["status"], "FAIL")
            task["authorized_scope"] = worker.SCOPE
            task["preconditions"] = ["FAIL_CLOSED"]
            self.assertEqual(worker.authorize(task)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()
