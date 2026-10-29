import unittest

from louksnapg_task_evidence_summary import summarize_task_results


class TaskEvidenceSummaryTests(unittest.TestCase):
    def test_execution_success_is_not_semantic_quality_pass(self):
        rows = [
            {
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "exit_code": 0,
                "quality_acceptance": {"status": "FAIL"},
            }
        ]
        summary = summarize_task_results(rows)
        self.assertEqual(summary["execution_success_count"], 1)
        self.assertEqual(summary["quality_pass_count"], 0)
        self.assertEqual(summary["pass_count"], 0)

    def test_semantic_quality_pass_requires_execution_and_quality_pass(self):
        rows = [
            {
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "exit_code": 0,
                "quality_acceptance": {"status": "PASS"},
            },
            {
                "status": "FAIL_FUNCTIONAL_EXECUTION",
                "exit_code": 1,
                "quality_acceptance": {"status": "PASS"},
            },
            {
                "status": "PASS_FUNCTIONAL_EXECUTION",
                "exit_code": 0,
                "quality_acceptance": {"status": "FAIL"},
            },
        ]
        summary = summarize_task_results(rows)
        self.assertEqual(summary["execution_success_count"], 2)
        self.assertEqual(summary["quality_pass_count"], 1)
        self.assertEqual(summary["pass_count"], 1)

    def test_missing_quality_field_fails_closed(self):
        rows = [
            {"status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0},
            {"status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": True,
             "quality_check": {"status": "PASS"}},
            None,
        ]
        summary = summarize_task_results(rows)
        self.assertEqual(summary["execution_success_count"], 1)
        self.assertEqual(summary["quality_pass_count"], 0)

    def test_legacy_quality_check_shape_is_supported(self):
        rows = [
            {"status": "PASS_FUNCTIONAL_EXECUTION", "exit_code": 0,
             "quality_check": {"status": "PASS"}}
        ]
        self.assertEqual(summarize_task_results(rows)["quality_pass_count"], 1)


if __name__ == "__main__":
    unittest.main()
