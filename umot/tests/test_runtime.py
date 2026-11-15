import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from runtime import AGENTS, LABS, PARENT_BYTES, PARENT_SHA256, Core


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.core = Core(Path(self.tmp.name) / "state")

    def tearDown(self):
        self.tmp.cleanup()

    def test_parent_constants_remain_the_protected_identity(self):
        self.assertEqual(PARENT_BYTES, 205679247)
        self.assertEqual(PARENT_SHA256, "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6")

    def test_commands_are_not_decorative(self):
        status = self.core.status()
        self.assertGreaterEqual(status["mem_available_kb"], 0)
        self.assertEqual(self.core.doctor()["core_import"], "PASS")
        names = {row["id"] for row in self.core.capabilities()["capabilities"]}
        self.assertTrue(all(f"agent:{name}" in names for name in AGENTS))
        self.assertTrue(all(f"lab:{name}" in names for name in LABS))

    def test_solver_rejects_unknown_work_and_governor_rejects_oversize(self):
        self.assertEqual(self.core.solve("teleport")["status"], "FAIL")
        self.assertEqual(self.core.govern(10**12)["status"], "FAIL")

    def test_memory_checkpoint_and_rollback(self):
        self.core.run("remember", key="k", value="v")
        point = self.core.checkpoint()
        self.core.run("remember", key="k", value="changed")
        self.assertEqual(self.core.recall("k")["value"], "changed")
        restored = self.core.rollback(point["checkpoint"])
        self.assertEqual(restored["status"], "PASS")
        self.assertEqual(self.core.recall("k")["value"], "v")

    def test_developer_cannot_certify_and_validator_is_independent(self):
        result = self.core.run("agent-change", body="payload")
        self.assertEqual(result["status"], "PASS")
        self.assertFalse(result["certified_by_developer"])
        self.assertTrue(result["validator"]["independent"])
        self.assertEqual(self.core.agent("validator", {"implementer": "validator", "path": "x", "expected_sha256": "0"})["reason"], "VALIDATOR_CANNOT_CERTIFY_ITSELF")

    def test_security_rejects_traversal_and_cpp_and_git_execute(self):
        self.assertEqual(self.core.agent("security", {"path": "../escape"})["status"], "FAIL")
        self.assertEqual(self.core.run("compile-cpp")["status"], "PASS")
        git = self.core.run("git-commit")
        self.assertEqual(git["status"], "PASS")
        self.assertEqual(git["forgejo"], "PRESENT")
        self.assertIn("17.0.1", git["forgejo_version"])

    def test_forgejo_gguf_browser_and_ocr_execute(self):
        forgejo = self.core.forgejo()
        self.assertEqual(forgejo["status"], "PASS", forgejo)
        self.assertEqual(forgejo["health_status"], "pass")
        self.assertEqual(forgejo["database_ping"], "pass")
        model = self.core.lab("model")
        self.assertEqual(model["status"], "PASS", model)
        self.assertEqual(model["model"], "stories260K.gguf")
        self.assertTrue(model["completion"])
        self.assertEqual(model["evidence"], "Generation:")
        browser = self.core.lab("browser")
        self.assertEqual(browser["status"], "PASS", browser)
        self.assertIn("UMOT-BROWSER-OK", browser["dom"])
        document = self.core.lab("document")
        self.assertEqual(document["status"], "PASS", document)
        self.assertIn("UMOT", document["text"])
        self.assertIn("OCR", document["text"])

    def test_adapter_does_not_block_core(self):
        result = self.core.run("adapter", name="claude")
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertFalse(result["core_blocked"])
        self.assertEqual(self.core.status()["network_required_for_core"], False)

    def test_cli_json_and_failure_exit(self):
        state = Path(self.tmp.name) / "cli"
        proc = subprocess.run([sys.executable, "-m", "cli", "--state", str(state), "status"], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("UMOT_STATUS/1.0", json.loads(proc.stdout)["schema"])
        bad = subprocess.run([sys.executable, "-m", "cli", "--state", str(state), "run", "teleport"], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True, check=False)
        self.assertEqual(bad.returncode, 2)


if __name__ == "__main__":
    unittest.main()
