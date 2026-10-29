from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from louksnapg2_engine import (
    ANCIENT_CONCORDANCE,
    EXPECTED_MODELS,
    EngineRuntimeError,
    LouksnapG2Runtime,
    normalize_ancient,
    verify_model_files,
)


class G2EngineContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.models = {
            "FIXTURE_LLM": {
                "path": "models/qwen-fixture.gguf",
                "repo": "example/fixture",
                "revision": "a" * 40,
                "file": "qwen-fixture.gguf",
                "bytes": 11,
                "sha256": hashlib.sha256(b"fixture-llm").hexdigest(),
            },
            "FIXTURE_WHISPER": {
                "path": "models/whisper-fixture.bin",
                "repo": "example/whisper-fixture",
                "revision": "b" * 40,
                "file": "whisper-fixture.bin",
                "bytes": 15,
                "sha256": hashlib.sha256(b"fixture-whisper").hexdigest(),
            },
        }
        for row in self.models.values():
            path = self.root / row["path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            payload = b"fixture-llm" if "qwen" in path.name else b"fixture-whisper"
            path.write_bytes(payload)
            self.assertEqual(path.stat().st_size, row["bytes"])

    def tearDown(self):
        self.temp.cleanup()

    def test_exact_source_file_size_and_sha256_are_required(self):
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", self.models, clear=True):
            result = verify_model_files(self.root)
        self.assertEqual(set(result), {"FIXTURE_LLM", "FIXTURE_WHISPER"})
        self.assertTrue(all(row["status"] == "PASS_SOURCE_IDENTITY" for row in result.values()))

    def test_size_mismatch_is_fail_closed(self):
        path = self.root / self.models["FIXTURE_LLM"]["path"]
        path.write_bytes(b"altered-size")
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", self.models, clear=True):
            with self.assertRaisesRegex(EngineRuntimeError, "MODEL_SIZE_MISMATCH"):
                verify_model_files(self.root)

    def test_hash_mismatch_is_fail_closed_even_when_size_matches(self):
        path = self.root / self.models["FIXTURE_LLM"]["path"]
        path.write_bytes(b"fixture-xyz")
        self.assertEqual(path.stat().st_size, 11)
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", self.models, clear=True):
            with self.assertRaisesRegex(EngineRuntimeError, "MODEL_SHA256_MISMATCH"):
                verify_model_files(self.root)

    def test_path_escape_is_rejected(self):
        data = {
            "BAD": {
                "path": "../model.gguf", "repo": "example/model", "revision": "a" * 40,
                "file": "model.gguf", "bytes": 1, "sha256": hashlib.sha256(b"x").hexdigest(),
            }
        }
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", data, clear=True):
            with self.assertRaisesRegex(EngineRuntimeError, "MODEL_PATH_INVALID"):
                verify_model_files(self.root)

    def test_known_ancient_phrase_uses_separate_route_without_general_fallback(self):
        runtime = LouksnapG2Runtime(self.root)
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", self.models, clear=True):
            with mock.patch.object(runtime, "_generate", side_effect=AssertionError("must use bounded reference")):
                result = runtime.translate_ancient("Carpe diem", src_lang="lat", tgt_lang="eng")
        self.assertEqual(result["output_text"], "Seize the day.")
        self.assertEqual(result["translation_strategy"], "BOUNDED_CONCORDANCE")
        self.assertEqual(result["domain_id"], "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertIs(result["general_translation_fallback_selected"], False)

    def test_unknown_ancient_phrase_uses_ancient_prompt_not_general_translation(self):
        runtime = LouksnapG2Runtime(self.root)
        seen = {}
        def fake_generate(*, system, user, max_tokens):
            seen["system"] = system
            seen["user"] = user
            return "All Gaul is divided into three parts."
        with mock.patch.dict("louksnapg2_engine.EXPECTED_MODELS", self.models, clear=True):
            with mock.patch.object(runtime, "_generate", side_effect=fake_generate):
                with mock.patch.object(runtime, "translate_general", side_effect=AssertionError("general adapter forbidden")):
                    result = runtime.translate_ancient(
                        "Gallia est omnis divisa in partes tres.", src_lang="lat", tgt_lang="eng"
                    )
        self.assertIn("dedicated ancient-language translation adapter", seen["system"].lower())
        self.assertNotIn("general-translation adapter", seen["system"].lower())
        self.assertEqual(result["domain_id"], "D04_TRADUCCION_LENGUAS_ANTIGUAS")
        self.assertIs(result["general_translation_fallback_selected"], False)
        self.assertEqual(result["translation_strategy"], "DEDICATED_ANCIENT_LANGUAGE_ADAPTER")

    def test_unknown_ancient_language_is_not_silently_routed(self):
        runtime = LouksnapG2Runtime(self.root)
        with self.assertRaisesRegex(EngineRuntimeError, "ANCIENT_SOURCE_LANGUAGE_NOT_REGISTERED"):
            runtime.translate_ancient("bonjour", src_lang="fra", tgt_lang="eng")

    def test_ancient_input_normalization_is_unicode_stable(self):
        self.assertEqual(normalize_ancient("CARPE DIEM"), "carpe diem")
        normalized = normalize_ancient("ἐν ἀρχῇ ἦν ὁ λόγος")
        self.assertEqual(normalize_ancient(normalized), normalized)
        self.assertEqual(normalize_ancient("λόγος"), normalize_ancient("λόγοσ"))

    def test_wrong_domain_operation_pair_is_fail_closed(self):
        runtime = LouksnapG2Runtime(self.root)
        with self.assertRaisesRegex(EngineRuntimeError, "DOMAIN_OPERATION_PAIR_NOT_REGISTERED"):
            runtime.route("D04_TRADUCCION_LENGUAS_ANTIGUAS", "translate_text", {"text": "Carpe diem"})


if __name__ == "__main__":
    unittest.main()
