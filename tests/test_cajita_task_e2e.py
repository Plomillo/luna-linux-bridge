from __future__ import annotations

import unittest

from cajita_task_e2e import MODEL_CASES, quality_acceptance


class SyntheticQualityAcceptanceTests(unittest.TestCase):
    def test_all_five_model_tasks_have_declared_acceptance_checks(self):
        self.assertEqual(len(MODEL_CASES), 5)
        self.assertTrue(all(row.get("quality_check", {}).get("id") for row in MODEL_CASES))

    def test_repository_answer_requires_expected_concept(self):
        row = MODEL_CASES[0]
        self.assertEqual(quality_acceptance(row, "A repository stores source code and files.")["status"], "PASS")
        self.assertEqual(quality_acceptance(row, "This is an unrelated answer.")["status"], "FAIL")

    def test_speech_transcription_requires_known_words(self):
        row = MODEL_CASES[1]
        self.assertEqual(quality_acceptance(row, "Hello, world!")["status"], "PASS")
        self.assertEqual(quality_acceptance(row, "Turn left at the next street.")["status"], "FAIL")

    def test_translation_accepts_accent_normalization_but_rejects_english(self):
        row = MODEL_CASES[2]
        self.assertEqual(quality_acceptance(row, "Buenos días. ¿Cómo estás?")["status"], "PASS")
        self.assertEqual(quality_acceptance(row, "Good morning. How are you?")["status"], "FAIL")

    def test_docling_uses_official_page_conversion_instruction_and_full_output_budget(self):
        row = MODEL_CASES[3]
        self.assertEqual(row["input"]["prompt"], "Convert this page to docling.")
        self.assertGreaterEqual(row["limits"]["max_new_tokens"], 64)

    def test_document_extraction_requires_the_fixture_total(self):
        row = MODEL_CASES[3]
        self.assertEqual(quality_acceptance(row, "TOTAL 133.45")["status"], "PASS")
        self.assertEqual(quality_acceptance(row, "TOTAL 123.45")["status"], "FAIL")

    def test_arithmetic_answer_requires_the_correct_number(self):
        row = MODEL_CASES[4]
        self.assertEqual(quality_acceptance(row, "4")["status"], "PASS")
        self.assertEqual(quality_acceptance(row, "5")["status"], "FAIL")

    def test_failed_expectation_emits_only_bounded_normalized_diagnostics(self):
        row = MODEL_CASES[4]
        bad_output = "NOT THE ANSWER" + chr(10) + "with <control>" + chr(92) + ("x" * 500)
        result = quality_acceptance(row, bad_output)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["output_char_count"], 530)
        self.assertEqual(len(result["normalized_output_excerpt"]), 180)
        self.assertNotIn(chr(10), result["normalized_output_excerpt"])
        self.assertNotIn("<control>", result["normalized_output_excerpt"])
        self.assertEqual(len(result["output_text_sha256"]), 64)

    def test_report_does_not_claim_reference_model_equivalence(self):
        for row in MODEL_CASES:
            evidence = quality_acceptance(row, "synthetic output")
            self.assertIs(evidence.get("does_not_establish_reference_model_equivalence"), True)


if __name__ == "__main__":
    unittest.main(verbosity=2)
