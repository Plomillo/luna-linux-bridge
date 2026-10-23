import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
import common

class CLIModuleTests(unittest.TestCase):
    def test_missing_binary_is_reported_absent_without_mutation(self):
        result = common.probe_version("definitely-not-an-installed-cli-xyz", ["--version"])
        self.assertEqual(result["status"], "ABSENT")
        self.assertFalse(result.get("shell", True))

    def test_version_probe_uses_direct_argv(self):
        with tempfile.TemporaryDirectory() as temp:
            root = pathlib.Path(temp)
            fake = root / "fixture-cli"
            fake.write_text("#!/usr/bin/env python3\nprint('fixture 1.0')\n", encoding="utf-8")
            fake.chmod(0o750)
            original_path = os.environ.get("PATH", "")
            with patch.dict(os.environ, {"PATH": temp + os.pathsep + original_path}, clear=False):
                with patch("common.subprocess.run", wraps=common.subprocess.run) as run_mock:
                    result = common.probe_version("fixture-cli", ["--version"])
            self.assertEqual(result["status"], "PASS", result)
            self.assertFalse(result["shell"])
            self.assertIn("fixture 1.0", result["stdout"])
            run_mock.assert_called_once()
            args, kwargs = run_mock.call_args
            self.assertEqual(args[0], [str(fake), "--version"])
            self.assertIs(kwargs["shell"], False)

    def test_domain_order_is_eight_and_unique(self):
        order = ["CLI_MOJO", "CLI_CPP23_TOOLCHAIN", "CLI_CLAUDE_CODE", "CLI_PYTHON",
                 "CLI_GITHUB", "CLI_GEMINI", "CLI_GROK", "CLI_HUGGING_FACE"]
        self.assertEqual(len(order), 8)
        self.assertEqual(len(set(order)), 8)

if __name__ == "__main__":
    unittest.main(verbosity=2)
