from __future__ import annotations
import unittest
from pathlib import Path
from louksnapg2_primary_five_e2e import bounded_case_timeout

class PrimaryFiveModelRunnerTests(unittest.TestCase):
    def test_case_timeout_is_a_cap_not_a_floor(self):
        record = {"limits": {"timeout_seconds": 30}}
        self.assertEqual(bounded_case_timeout(1800, record), 30)
        self.assertEqual(bounded_case_timeout(10, record), 10)

    def test_runner_uses_five_registered_model_cases_and_excludes_alternates(self):
        root = Path(__file__).resolve().parents[1]
        source = (root / "tools" / "louksnapg2_primary_five_e2e.py").read_text(encoding="utf-8")
        self.assertIn("from cajita_task_e2e import MODEL_CASES, make_audio, run_case", source)
        self.assertIn("DIRECT_REGISTERED_LOCAL_MODEL_ADAPTERS_ONLY", source)
        self.assertIn('"auxiliary_engine_execution_performed": False', source)
        self.assertIn('"fallback_engine_execution_performed": False', source)
        self.assertIn('"required_model_count": 5', source)
        self.assertNotIn("LouksnapG2Runtime", source)
        self.assertNotIn("whisper-cli", source)
        self.assertNotIn("apertium", source)

    def test_exact_five_model_domains_have_fixed_quality_predicates(self):
        import sys
        root = Path(__file__).resolve().parents[1]
        sys.path.insert(0, str(root / "tools"))
        from cajita_task_e2e import MODEL_CASES
        self.assertEqual(
            [row["domain_id"] for row in MODEL_CASES],
            [
                "D01_CEREBRO",
                "D03_TRANSCRIPCION",
                "D04_TRADUCTOR_INTELIGENTE",
                "D05_INTELIGENCIA_DOCUMENTAL",
                "D06_SISTEMA_INTELIGENTE",
            ],
        )
        self.assertEqual(len({row["task_id"] for row in MODEL_CASES}), 5)
        for row in MODEL_CASES:
            self.assertTrue(row.get("quality_check", {}).get("id"))
            self.assertGreater(row.get("limits", {}).get("timeout_seconds", 0), 0)
            self.assertGreater(row.get("limits", {}).get("max_new_tokens", 0), 0)

    def test_gpt_oss_media_download_remeasures_shell_variables_after_python(self):
        root = Path(__file__).resolve().parents[1]
        workflow = (root / ".github" / "workflows" / "louksnapg2-primary-five-model-e2e.yml").read_text(encoding="utf-8")
        moved = workflow.index('mv "$temporary" "$GITHUB_WORKSPACE/$file"')
        measured = workflow.index('actual_bytes="$(stat -c %s "$GITHUB_WORKSPACE/$file")"')
        verified = workflow.index('actual_sha256="$(sha256sum "$GITHUB_WORKSPACE/$file" | cut -d " " -f1)"')
        reported = workflow.index('echo "GPT_OSS_LFS_OBJECT_VERIFIED bytes=$actual_bytes sha256=$actual_sha256"')
        self.assertLess(moved, measured)
        self.assertLess(measured, verified)
        self.assertLess(verified, reported)
        self.assertIn('test "$actual_bytes" -eq "$expected_bytes"', workflow)
        self.assertIn('test "$actual_sha256" = "$expected_sha256"', workflow)
        self.assertIn("/tools/louksnapg2_refresh_module_integrity.py", workflow)

if __name__ == "__main__":
    unittest.main(verbosity=2)
