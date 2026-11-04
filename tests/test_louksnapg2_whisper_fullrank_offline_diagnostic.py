import importlib.util
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/louksnapg2_whisper_fullrank_offline_diagnostic.py"
SPEC = importlib.util.spec_from_file_location("whisper_fullrank_offline_diagnostic", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WhisperFullRankOfflineDiagnosticTests(unittest.TestCase):
    def test_word_normalization_is_deterministic(self):
        self.assertEqual(MODULE.normalized_words("Hello, WORLD! It's 2026."),
                         ["hello", "world", "it", "s", "2026"])

    def test_word_error_rate_uses_word_level_edit_distance(self):
        self.assertEqual(MODULE.word_error_rate("hello world", "hello there"), 0.5)
        self.assertEqual(MODULE.word_error_rate("same text", "same text"), 0.0)

    def test_candidate_fits_only_as_an_external_asset(self):
        self.assertLess(MODULE.EXPECTED_Q4_BYTES, MODULE.GLOBAL_RELEASE_MAX_BYTES)
        self.assertGreater(MODULE.PROJECTED_COMPLETE_RELEASE_BYTES, MODULE.GLOBAL_RELEASE_MAX_BYTES)

    def test_diagnostic_cap_does_not_change_active_runtime_cap(self):
        self.assertEqual(MODULE.CANDIDATE_RAM_BYTES, 1_342_177_280)
        self.assertEqual(MODULE.ACTIVE_RUNTIME_RAM_BYTES, 1_073_741_824)
        self.assertGreater(MODULE.CANDIDATE_RAM_BYTES, MODULE.ACTIVE_RUNTIME_RAM_BYTES)

    def test_jfk_fixture_source_is_pinned(self):
        self.assertEqual(MODULE.OPENAI_WHISPER_FIXTURE_REVISION,
                         "86098128c0b4f24f0e2aa2994de830614b474227")


if __name__ == "__main__":
    unittest.main(verbosity=2)
