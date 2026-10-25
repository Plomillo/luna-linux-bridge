from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

REPOSITORY = Path(__file__).resolve().parents[1]
RUNTIME = REPOSITORY / "cajita-luna-runtime"
sys.path.insert(0, str(RUNTIME))

import cajita_target_adapters as target_adapters


class TargetEngineSmokeContractTests(unittest.TestCase):
    def test_registry_has_six_unique_targets_with_explicit_scope_only_contracts(self):
        specs = target_adapters.TARGET_ADAPTERS
        self.assertEqual(len(specs), 6)
        self.assertEqual(len(set(specs)), 6)
        self.assertEqual(tuple(specs), target_adapters.EXPECTED_TARGET_IDS)
        for target_id, spec in specs.items():
            with self.subTest(target_id=target_id):
                self.assertTrue(spec["adapter_id"])
                self.assertTrue(spec["operation"])
                self.assertTrue(spec["engine"])
                self.assertTrue(spec["scope"])
                self.assertIn(spec["entry"], spec["required_files"])
                self.assertNotIn("certification", spec)
                self.assertTrue(spec["required_files"])

    def test_unknown_target_fails_closed_before_any_source_execution(self):
        with tempfile.TemporaryDirectory() as temp_name:
            with self.assertRaisesRegex(target_adapters.TargetAdapterError, "TARGET_ADAPTER_NOT_REGISTERED"):
                target_adapters.execute_target_task(Path(temp_name), "D99_UNKNOWN")

    def test_relative_path_rejects_parent_traversal_and_absolute_paths(self):
        with self.assertRaisesRegex(target_adapters.TargetAdapterError, "TARGET_ADAPTER_PATH_UNSAFE"):
            target_adapters._safe_relative("../outside")
        with self.assertRaisesRegex(target_adapters.TargetAdapterError, "TARGET_ADAPTER_PATH_UNSAFE"):
            target_adapters._safe_relative("/tmp/outside")

    def test_selected_engine_scopes_are_not_claimed_as_full_task_adapters(self):
        report = target_adapters.run_target_smokes
        self.assertTrue(callable(report))
        self.assertEqual(
            len({spec["scope"] for spec in target_adapters.TARGET_ADAPTERS.values()}),
            6
        )
        self.assertTrue(all(spec["engine"] for spec in target_adapters.TARGET_ADAPTERS.values()))
        self.assertTrue(all("task_adapter" not in spec for spec in target_adapters.TARGET_ADAPTERS.values()))
        self.assertTrue(all(spec["scope"] not in {"FULL_TASK_ADAPTER", "ALL_TASKS", "CERTIFIED"}
                            for spec in target_adapters.TARGET_ADAPTERS.values()))


if __name__ == "__main__":
    unittest.main(verbosity=2)
