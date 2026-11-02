from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/louksnapg_whisper_fullrank_quantization.py"
SPEC = importlib.util.spec_from_file_location("whisper_fullrank_quantization", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WhisperFullRankMemorySplitTests(unittest.TestCase):
    def test_normalization_matches_shared_whisper_evaluator(self):
        self.assertEqual(MODULE.normalized_words("Hello, WORLD! It's 2026."), ["hello", "world", "it", "s", "2026"])

    def test_wer_uses_word_level_edit_distance(self):
        self.assertEqual(MODULE.word_error_rate("hello world", "hello there"), 0.5)
        self.assertEqual(MODULE.word_error_rate("same text", "same text"), 0.0)

    def test_fixture_preparation_is_separate_from_model_evaluation(self):
        import inspect
        source = inspect.getsource(MODULE.evaluate)
        self.assertNotIn("load_helper", source)
        self.assertNotIn("datasets", source)
        self.assertIn("prepared_fixtures", source)

    def test_candidate_memory_gate_remains_one_gib(self):
        self.assertEqual(MODULE.CANDIDATE_RAM_BYTES, 1 * 1024**3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
