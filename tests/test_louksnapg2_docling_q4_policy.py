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

    def test_runtime_preserves_upstream_bfloat16_and_512px_vision_geometry(self):
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime/5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py"
        source = runtime.read_text(encoding="utf-8")
        self.assertIn('torch.bfloat16 if str(getattr(config, "dtype", "")).lower() == "bfloat16"', source)
        self.assertIn('LOUKSNAPG2_DOCLING_IMAGE_SIDE", "512"', source)
        self.assertIn('LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES', source)
        self.assertIn('image_seq_len=((image_side // patch_size) ** 2) // (scale_factor ** 2)', source)

    def test_paired_evaluation_requires_same_fixture_and_generation_protocol(self):
        import inspect
        import louksnapg2_docling_q4_repair as repair
        source = inspect.getsource(repair.evaluate)
        self.assertIn('"same_fixture_and_generation_protocol": True', source)
        self.assertIn('"runs_are_sequential_separate_processes": True', source)
        self.assertIn('"teacher_source_bfloat16": teacher', source)
        self.assertIn('LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES', source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
