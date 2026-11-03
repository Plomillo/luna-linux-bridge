from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

RUNTIME = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "LOUKSNAPG2_RUNTIME"
sys.path.insert(0, str(RUNTIME))
import louksnapg2_auxiliary as auxiliary


class FormalReasoningTests(unittest.TestCase):
    def test_calculates_expression_without_evaluating_python(self):
        result = auxiliary.formal_reasoning("Compute (17 * 3) - 9. Return a single integer.")
        self.assertEqual(result["output_text"], "42")

    def test_solves_items_unit_price_minus_discount(self):
        result = auxiliary.formal_reasoning(
            "An invoice has 5 items at 7 dollars each and a 4 dollar discount. What is the final amount?"
        )
        self.assertEqual(result["output_text"], "31")

    def test_solves_capacity_minus_borrowed_books(self):
        result = auxiliary.formal_reasoning(
            "A library has 9 shelves with 8 books per shelf. 17 books are borrowed. How many remain?"
        )
        self.assertEqual(result["output_text"], "55")

    def test_rejects_invalid_existential_transfer(self):
        result = auxiliary.formal_reasoning(
            "All tulips are flowers. Some flowers fade quickly. Does it logically follow that some tulips fade quickly?"
        )
        self.assertEqual(result["output_text"], "No")
        self.assertIn("INVALID_EXISTENTIAL_TRANSFER", result["scope"])

    def test_unsupported_problem_is_not_fabricated(self):
        self.assertIsNone(auxiliary.formal_reasoning("Write a poem about winter."))

    def test_arithmetic_does_not_execute_python_or_allow_names(self):
        with self.assertRaisesRegex(auxiliary.AuxiliaryEngineError, "ARITHMETIC_SYNTAX_NOT_IN_ALLOWLIST"):
            auxiliary._safe_expression("__import__('os').system('id')")

    def test_arithmetic_division_by_zero_fails_closed(self):
        with self.assertRaisesRegex(auxiliary.AuxiliaryEngineError, "ARITHMETIC_DIVISION_BY_ZERO"):
            auxiliary._safe_expression("10 / 0")


class ApertiumRoutingTests(unittest.TestCase):
    def test_english_to_spanish_uses_one_registered_pair(self):
        with mock.patch.object(auxiliary, "_apertium_pair", return_value="La reunión empieza al mediodía.") as run, \
             mock.patch.object(auxiliary, "_apertium_runtime_evidence", return_value={"version": "fixture", "packages": {}}):
            result = auxiliary.translate_apertium("The meeting starts at noon.", "eng", "spa")
        run.assert_called_once_with("eng", "spa", "The meeting starts at noon.")
        self.assertEqual(result["translation_route"], ["eng-spa"])

    def test_english_to_french_uses_spanish_pivot(self):
        with mock.patch.object(auxiliary, "_apertium_pair", side_effect=["El libro está sobre la mesa.", "Le livre est sur la table."]) as run, \
             mock.patch.object(auxiliary, "_apertium_runtime_evidence", return_value={"version": "fixture", "packages": {}}):
            result = auxiliary.translate_apertium("The book is on the table.", "eng", "fra")
        self.assertEqual(run.call_args_list[0].args, ("eng", "spa", "The book is on the table."))
        self.assertEqual(run.call_args_list[1].args, ("spa", "fra", "El libro está sobre la mesa."))
        self.assertEqual(result["translation_route"], ["eng-spa", "spa-fra"])

    def test_french_to_english_uses_spanish_pivot(self):
        with mock.patch.object(auxiliary, "_apertium_pair", side_effect=["El libro está sobre la mesa.", "The book is on the table."]) as run, \
             mock.patch.object(auxiliary, "_apertium_runtime_evidence", return_value={"version": "fixture", "packages": {}}):
            result = auxiliary.translate_apertium("Le livre est sur la table.", "fra", "eng")
        self.assertEqual(run.call_count, 2)
        self.assertEqual(result["translation_route"], ["fra-spa", "spa-eng"])

    def test_unsupported_language_direction_fails_closed(self):
        with self.assertRaisesRegex(auxiliary.AuxiliaryEngineError, "APERTIUM_LANGUAGE_DIRECTION_NOT_REGISTERED"):
            auxiliary.translate_apertium("Bonjour", "fra", "deu")


class ImageAndAudioBackendTests(unittest.TestCase):
    def test_tesseract_backend_returns_text_and_input_provenance(self):
        with tempfile.TemporaryDirectory() as tmp:
            image = Path(tmp) / "invoice.png"
            image.write_bytes(b"image-bytes")
            completed = mock.Mock(returncode=0, stdout="INVOICE 4821\nTOTAL 37.50\n\x0c", stderr="")
            with mock.patch.object(auxiliary, "_run_checked", return_value=completed) as run:
                result = auxiliary.extract_document_tesseract(image)
        self.assertEqual(result["output_text"], "INVOICE 4821\nTOTAL 37.50")
        self.assertEqual(result["engine_id"], "TESSERACT_OCR/5.x")
        self.assertEqual(run.call_args.args[0][0], "tesseract")

    def test_tesseract_rejects_missing_or_symlink_image(self):
        with tempfile.TemporaryDirectory() as tmp:
            missing = Path(tmp) / "missing.png"
            with self.assertRaisesRegex(auxiliary.AuxiliaryEngineError, "OCR_INPUT_IMAGE_MISSING_OR_UNSAFE"):
                auxiliary.extract_document_tesseract(missing)

    def test_whisper_requires_hash_bound_bundled_binary_and_never_uses_path_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Path(tmp) / "LOUKSNAPG2_RUNTIME"
            runtime.mkdir()
            audio = Path(tmp) / "sample.wav"
            audio.write_bytes(b"RIFF" + b"0" * 128)
            with mock.patch.object(auxiliary.shutil, "which", return_value="/usr/bin/whisper-cli"):
                with self.assertRaisesRegex(auxiliary.AuxiliaryEngineError, "WHISPER_AUXILIARY_ASSET_MISSING_OR_UNSAFE:binary"):
                    auxiliary.transcribe_whisper_cpp(runtime, audio)


if __name__ == "__main__":
    unittest.main(verbosity=2)
