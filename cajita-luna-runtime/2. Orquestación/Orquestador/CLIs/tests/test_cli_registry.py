import json
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(ROOT))
import common
import cli_registry
import cli_manager

class CLIModuleTests(unittest.TestCase):
    def test_missing_binary_is_absent_without_mutation(self):
        result = common.probe_version("definitely-not-installed-cajita-cli-test", ["--version"])
        self.assertEqual(result["status"], "ABSENT")
        self.assertFalse(result["shell"])
        self.assertFalse(result["mutations_performed"])

    def test_probe_invokes_direct_argv_without_shell(self):
        with tempfile.TemporaryDirectory() as temp:
            exe = pathlib.Path(temp) / "fixture-cli"
            exe.write_text("#!/usr/bin/env python3\nprint('fixture 1.0')\n", encoding="utf-8")
            exe.chmod(0o750)
            old_path = os.environ.get("PATH", "")
            with patch.dict(os.environ, {"PATH": temp + os.pathsep + old_path}, clear=False):
                with patch("common.subprocess.run", wraps=common.subprocess.run) as runner:
                    result = common.probe_version("fixture-cli", ["--version"])
            self.assertEqual(result["status"], "PASS")
            self.assertFalse(result["shell"])
            self.assertIn("fixture 1.0", result["stdout"])
            args, kwargs = runner.call_args
            self.assertEqual(args[0], [str(exe), "--version"])
            self.assertIs(kwargs["shell"], False)

    def test_contract_and_manifest_keep_the_eight_canonical_domains(self):
        manifest, contract = cli_registry.load_inputs()
        expected = ["CLI_MOJO", "CLI_CPP23_TOOLCHAIN", "CLI_CLAUDE_CODE", "CLI_PYTHON",
                    "CLI_GITHUB", "CLI_GEMINI", "CLI_GROK", "CLI_HUGGING_FACE"]
        self.assertEqual(manifest["domain_order"], expected)
        self.assertEqual(contract["domain_order"], expected)
        self.assertEqual([d["id"] for d in contract["domains"]], expected)

    def test_all_eight_modular_adapters_are_present(self):
        result = cli_registry.selftest()
        self.assertEqual(result["status"], "PASS", result)
        self.assertTrue(result["all_adapters_present"])
        self.assertEqual(result["domain_count"], 8)

    def test_git_does_not_substitute_for_github_cli(self):
        import cli_github
        with patch("common.probe_version", side_effect=[
            {"binary": "gh", "status": "ABSENT"},
            {"binary": "git", "status": "PASS"}
        ]):
            result = cli_github.probe()
        self.assertEqual(result["status"], "ABSENT")

    def test_grok_audit_does_not_execute_a_candidate_binary(self):
        import cli_grok
        with patch("shutil.which", return_value="/usr/local/bin/grok"), patch("subprocess.run") as run:
            result = cli_grok.probe()
        self.assertFalse(result["candidate_binary_executed"])
        run.assert_not_called()

    def test_read_only_registry_separates_infrastructure_from_provider_state(self):
        result = cli_registry.run_registry()
        self.assertEqual(result["infrastructure_status"], "PASS", result)
        self.assertEqual(result["domain_count"], 8)
        self.assertFalse(result["mutations_performed"])
        self.assertEqual(result["certification"], "NOT_GRANTED")

    def test_install_plan_does_not_mutate_without_version_pins(self):
        result = cli_manager.build_plan()
        self.assertEqual(result["schema"], "CAJITA_CLI_INSTALL_PLAN/1.0")
        self.assertEqual(result["status"], "BLOCKED_FAIL_CLOSED")
        self.assertEqual(result["commands"], [])
        self.assertTrue(result["no_mutations"])
        statuses = {x["domain_id"]: x["status"] for x in result["actions"]}
        self.assertEqual(statuses["CLI_MOJO"], "BLOCKED_VERSION_PIN_REQUIRED")
        self.assertEqual(statuses["CLI_PYTHON"], "AUDIT_ONLY_NO_INSTALL_MUTATION")

    def test_apply_plan_rejects_wrong_plan_sha_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as temp:
            plan_path = pathlib.Path(temp) / "plan.json"
            plan_path.write_text(json.dumps(cli_manager.build_plan()), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PLAN_SHA256_APPROVAL_MISMATCH"):
                cli_manager.apply_plan(plan_path, "0" * 64)

if __name__ == "__main__":
    unittest.main(verbosity=2)
