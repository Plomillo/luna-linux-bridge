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
