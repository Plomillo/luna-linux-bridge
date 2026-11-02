from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from louksnapg2_docling_isolated_probe import acceptance_exit_code


class DoclingExitStatusTests(unittest.TestCase):
    def test_only_real_semantic_pass_returns_zero(self):
        self.assertEqual(acceptance_exit_code({
            "status": "PASS",
            "execution_status": "PASS_EXECUTION",
            "quality_criterion_passed": True,
        }), 0)

    def test_execution_timeout_is_nonzero(self):
        self.assertEqual(acceptance_exit_code({
            "status": "FAIL",
            "execution_status": "FAIL_TIMEOUT",
            "quality_criterion_passed": False,
        }), 2)

    def test_generation_without_quality_pass_is_nonzero(self):
        self.assertEqual(acceptance_exit_code({
            "status": "PASS_EXECUTION",
            "execution_status": "PASS_EXECUTION",
            "quality_criterion_passed": False,
        }), 2)

    def test_missing_or_invalid_case_is_nonzero(self):
        self.assertEqual(acceptance_exit_code(None), 2)
        self.assertEqual(acceptance_exit_code({}), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
