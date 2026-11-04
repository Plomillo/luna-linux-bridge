from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tempfile
import unittest

MODULE_PATH = Path(__file__).resolve().parents[1] / "tools/louksnapg_whisper_fullrank_quantization.py"
SPEC = importlib.util.spec_from_file_location("whisper_fullrank_quantization", MODULE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC is not None and SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class WhisperFullRankMemorySplitTests(unittest.TestCase):
    def test_official_checkpoint_source_is_sha256_pinned_and_not_hub_hosted(self):
        self.assertEqual(len(MODULE.SOURCE_MODEL_SHA256), 64)
        self.assertIn("openaipublic.azureedge.net", MODULE.SOURCE_MODEL_URL)
        self.assertNotIn("huggingface.co", MODULE.SOURCE_MODEL_URL)
        self.assertFalse(MODULE.SOURCE_MODEL_URL.startswith("https://huggingface.co"))

    def test_build_does_not_use_hub_download_api(self):
        source = inspect.getsource(MODULE.build)
        self.assertIn("download_official_whisper_checkpoint", source)
        self.assertNotIn("huggingface_hub", source)
        self.assertNotIn("snapshot_download", source)

    def test_pytorch_converter_uses_safe_mmap(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            converter = root / "convert-pt-to-ggml.py"
            converter.write_text(
                'import io, torch\\n'
                'model_bytes = open(fname_inp, "rb").read()\\n'
                'with io.BytesIO(model_bytes) as fp:\\n'
                '    checkpoint = torch.load(fp, map_location="cpu")\\n',
                encoding="utf-8",
            )
            patched = MODULE.create_mmap_pt_converter(converter, root)
            source = patched.read_text(encoding="utf-8")
            self.assertIn("mmap=True, weights_only=True", source)
            self.assertNotIn("model_bytes = open(fname_inp", source)

    def test_offline_fixture_is_source_pinned_and_does_not_load_hub_dataset(self):
        source = inspect.getsource(MODULE.prepare_fixtures)
        self.assertIn("PINNED_GIT_COMMIT_ASSET", source)
        self.assertNotIn("datasets", source)
        self.assertNotIn("load_helper", source)

    def test_memory_event_delta_tracks_new_oom_events_only(self):
        delta = MODULE.memory_event_delta({"oom": 0, "oom_kill": 0, "high": 10}, {"oom": 0, "oom_kill": 0, "high": 12})
        self.assertEqual(delta["oom"], 0)
        self.assertEqual(delta["oom_kill"], 0)
        self.assertEqual(delta["high"], 2)

    def test_report_uses_per_process_rss_not_cumulative_cgroup_peak(self):
        source = inspect.getsource(MODULE.report_evaluation)
        self.assertIn("CANDIDATE_NATIVE_PROCESS_PEAK_OVER_1GIB", source)
        self.assertNotIn("CANDIDATE_MEMORY_PEAK_OVER_1GIB", source)
    def test_normalization_matches_shared_whisper_evaluator(self):
        self.assertEqual(MODULE.normalized_words("Hello, WORLD! It's 2026."), ["hello", "world", "it", "s", "2026"])

    def test_wer_uses_word_level_edit_distance(self):
        self.assertEqual(MODULE.word_error_rate("hello world", "hello there"), 0.5)
        self.assertEqual(MODULE.word_error_rate("same text", "same text"), 0.0)

    def test_fixture_preparation_is_separate_from_model_evaluation(self):
        source = inspect.getsource(MODULE.evaluate)
        self.assertNotIn("load_helper", source)
        self.assertNotIn("datasets", source)
        self.assertIn("prepared_fixtures", source)

    def test_candidate_memory_gate_remains_one_gib(self):
        self.assertEqual(MODULE.CANDIDATE_RAM_BYTES, 1 * 1024**3)

    def test_native_decoder_uses_single_beam_within_one_gib(self):
        import inspect
        source = inspect.getsource(MODULE.evaluate)
        self.assertIn("-bs 1 -bo 1", source)

    def test_shared_library_staging_includes_nested_whisper_soname(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            build = root / "build"
            nested = build / "src"
            nested.mkdir(parents=True)
            real_library = nested / "libwhisper.so.1.0.0"
            real_library.write_bytes(b"pinned-whisper-library")
            (nested / "libwhisper.so.1").symlink_to(real_library.name)
            (build / "ggml" / "src").mkdir(parents=True)
            (build / "ggml" / "src" / "libggml-base.so.0").write_bytes(b"pinned-ggml-library")
            destination = root / "artifact" / "toolchain" / "lib"
            rows = MODULE.stage_shared_libraries(build, destination)
            names = {row["name"] for row in rows}
            self.assertIn("libwhisper.so.1", names)
            self.assertIn("libggml-base.so.0", names)
            self.assertFalse((destination / "libwhisper.so.1").is_symlink())
            self.assertEqual((destination / "libwhisper.so.1").read_bytes(), b"pinned-whisper-library")

    def test_runtime_env_prepends_bundled_libraries(self):
        with tempfile.TemporaryDirectory() as temporary:
            library_dir = Path(temporary)
            env = MODULE.whisper_runtime_env({"LD_LIBRARY_PATH": "/system/lib"}, library_dir)
            self.assertEqual(env["LD_LIBRARY_PATH"], str(library_dir.resolve()) + os.pathsep + "/system/lib")


if __name__ == "__main__":
    unittest.main(verbosity=2)
