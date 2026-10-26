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
            self.assertEqual(task["authorized_scope"], "BUILD_LOUKSNAPG_SINGLE_FILE_CANDIDATE")
            self.assertEqual(task["permitted_effects"], ["WRITE_EVIDENCE"])
            self.assertIn("NO_SELF_CERTIFICATION", task["preconditions"])
            self.assertIn("FAIL_CLOSED", task["preconditions"])

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
