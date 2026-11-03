from __future__ import annotations
import unittest
from pathlib import Path

class PrimaryFiveModelRunnerTests(unittest.TestCase):
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

if __name__ == "__main__":
    unittest.main(verbosity=2)
