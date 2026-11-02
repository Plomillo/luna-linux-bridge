from __future__ import annotations

import sys
import unittest
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

from louksnapg2_docling_q4_repair import GLOBAL_RELEASE_MAX_BYTES


class DoclingGlobalDistributionCapTests(unittest.TestCase):
    def test_docling_reconstruction_uses_authorized_louksnapg2_cap(self):
        self.assertEqual(GLOBAL_RELEASE_MAX_BYTES, 490_000_000)

    def test_teacher_sidecar_is_evaluation_only(self):
        import inspect
        import louksnapg2_docling_q4_repair as repair
        source = inspect.getsource(repair.build)
        self.assertIn('"role": "EVALUATION_ONLY_NOT_PART_OF_CANDIDATE_PACKAGE"', source)

    def test_paired_evaluation_requires_same_fixture_and_generation_protocol(self):
        import inspect
        import louksnapg2_docling_q4_repair as repair
        source = inspect.getsource(repair.evaluate)
        self.assertIn('"same_fixture_and_generation_protocol": True', source)
        self.assertIn('"runs_are_sequential_separate_processes": True', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
