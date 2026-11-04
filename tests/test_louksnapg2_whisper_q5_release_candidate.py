import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/louksnapg2_whisper_q5_release_candidate.py"
SPEC = importlib.util.spec_from_file_location("whisper_q5_release_candidate", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WhisperQ5ReleaseCandidateTests(unittest.TestCase):
    def test_release_candidate_remains_outside_runtime_cap(self):
        self.assertGreater(MODULE.EXPECTED_Q5_BYTES, MODULE.ACTIVE_RELEASE_CAP_BYTES)
        self.assertGreater(MODULE.PROJECTED_RELEASE_BYTES, MODULE.ACTIVE_RELEASE_CAP_BYTES)
        self.assertLess(MODULE.EXPECTED_Q5_BYTES, MODULE.MAX_RELEASE_ASSET_BYTES)

    def test_only_exact_whisper_q5_candidate_is_selected(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest = {
                "schema": "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0",
                "source_model": {"sha256": MODULE.EXPECTED_SOURCE_SHA256,
                                 "source_model_id": "openai/whisper-large-v3-turbo"},
                "conversion": {"whisper_cpp_revision": "482279b8a18855ba741d7b88c30fcb3874691f59",
                               "runtime_libraries": []},
                "quantization_candidates": [
                    {"quantization": "q4_0", "path": "quantized/q4.bin"},
                    {"quantization": "q5_0", "path": "quantized/q5.bin"},
                ],
            }
            (root / "fullrank_manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            (root / "quantized").mkdir()
            (root / "quantized/q4.bin").write_bytes(b"q4")
            (root / "quantized/q5.bin").write_bytes(b"q5")
            with self.assertRaises(ValueError):
                MODULE.validate_candidate(root, root / "missing-evaluation.json")

    def test_runtime_release_assets_limit_is_not_runtime_package_limit(self):
        self.assertEqual(MODULE.ACTIVE_RELEASE_CAP_BYTES, 490_000_000)
        self.assertEqual(MODULE.MAX_RELEASE_ASSET_BYTES, 2 * 1024**3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
