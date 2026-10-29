from __future__ import annotations

import unittest

from cajita_task_e2e import (MODEL_CASES, quality_acceptance,
                             required_domain_coverage, task_execution_and_quality_pass)


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

    def test_required_ancient_translation_is_not_replaced_by_general_translation(self):
        rows = [
            {"domain_id": "D01_CEREBRO", "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_acceptance": {"status": "PASS"}},
            {"domain_id": "D03_TRANSCRIPCION", "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_acceptance": {"status": "PASS"}},
            {"domain_id": "D04_TRADUCTOR_INTELIGENTE", "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_acceptance": {"status": "PASS"}, "target_id": "D04_TRADUCCION_GENERAL"},
            {"domain_id": "D06_SISTEMA_INTELIGENTE", "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_acceptance": {"status": "PASS"}},
            {"domain_id": "D05_INTELIGENCIA_DOCUMENTAL", "status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_acceptance": {"status": "PASS"}},
        ]
        route = {"status": "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED",
                 "functional_translation_status": "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE"}
        coverage = required_domain_coverage(rows, route)
        by_name = {row["required_domain"]: row for row in coverage}
        self.assertEqual(len(coverage), 5)
        self.assertEqual(by_name["Traducción general"]["status"], "PASS_FIXED_SYNTHETIC_EXPECTATION_ONLY")
        self.assertEqual(by_name["Traducción de lenguas antiguas"]["status"],
                         "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE")
        self.assertEqual(by_name["Traducción de lenguas antiguas"]["route_diagnostic"],
                         "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED")
        self.assertFalse(all(row["status"] == "PASS_FIXED_SYNTHETIC_EXPECTATION_ONLY" for row in coverage))

    def test_required_domain_coverage_does_not_count_docling_as_ancient_translation(self):
        coverage = required_domain_coverage(
            [{"domain_id": "D05_INTELIGENCIA_DOCUMENTAL", "status": "PASS_FUNCTIONAL_EXECUTION",
              "exit_code": 0, "quality_acceptance": {"status": "PASS"}}],
            {"status": "PASS_ROUTE_IDENTIFIED_FAIL_CLOSED",
             "functional_translation_status": "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE"},
        )
        by_name = {row["required_domain"]: row for row in coverage}
        self.assertEqual(by_name["Traducción de lenguas antiguas"]["status"],
                         "BLOCKED_MISSING_CONSUMER_ADAPTER_AND_TRANSLATION_RESOURCE")
        self.assertEqual(by_name["Cerebro"]["status"], "NOT_TESTED")

    def test_process_rss_diagnostic_does_not_override_outer_cgroup_gate(self):
        row = {
            "status": "PASS_FUNCTIONAL_EXECUTION",
            "exit_code": 0,
            "quality_acceptance": {"status": "PASS"},
            "input_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "weight_sha256": "c" * 64,
            "module_tree_sha256": "d" * 64,
            "peak_rss_bytes": 1_146_601_472,
        }
        self.assertTrue(task_execution_and_quality_pass(row))

    def test_semantic_quality_failure_stays_failed_even_when_process_rss_is_below_cap(self):
        row = {
            "status": "PASS_FUNCTIONAL_EXECUTION",
            "exit_code": 0,
            "quality_acceptance": {"status": "FAIL"},
            "input_sha256": "a" * 64,
            "output_sha256": "b" * 64,
            "weight_sha256": "c" * 64,
            "module_tree_sha256": "d" * 64,
            "peak_rss_bytes": 500_000_000,
        }
        self.assertFalse(task_execution_and_quality_pass(row))


if __name__ == "__main__":
    unittest.main(verbosity=2)
