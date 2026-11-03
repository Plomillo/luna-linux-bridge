from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from unittest import mock

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

    def test_cpu_thread_budget_is_configurable_and_bounded(self):
        import importlib.util
        runtime = Path(__file__).resolve().parents[1] / "cajita-luna-runtime/5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py"
        spec = importlib.util.spec_from_file_location("louksnapg2_docling_runtime_policy_test", runtime)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)

        fake_torch = mock.Mock()
        with mock.patch.dict(os.environ, {"LOUKSNAPG2_DOCLING_CPU_THREADS": "4"}):
            self.assertEqual(module.configure_cpu_runtime(fake_torch), 4)
        fake_torch.set_num_threads.assert_called_once_with(4)
        fake_torch.set_num_interop_threads.assert_called_once_with(1)

        with mock.patch.dict(os.environ, {"LOUKSNAPG2_DOCLING_CPU_THREADS": "5"}):
            with self.assertRaisesRegex(RuntimeError, "DOCLING_CPU_THREAD_BUDGET_OUT_OF_RANGE"):
                module.requested_cpu_threads()

    def test_timeout_preserves_partial_runtime_stage_diagnostics(self):
        import louksnapg2_docling_q4_repair as repair
        marker = b"LOUKSNAPG2_DOCLING_STAGE=GENERATION_START"
        timeout = subprocess.TimeoutExpired(["python", "runtime.py"], 7, output=b"", stderr=marker)
        with mock.patch("subprocess.run", side_effect=timeout):
            result = repair._run_runtime_protocol(
                Path("runtime.py"), Path("candidate"), Path("invoice.png"),
                64, "Convert this page to docling.", None, 7,
            )
        self.assertEqual(result["status"], "FAIL_TIMEOUT")
        self.assertEqual(result["timeout_seconds"], 7)
        self.assertIn(marker.decode(), result["partial_stderr_tail"])
        self.assertIn(marker.decode(), result["runtime_stage_markers"][0])

    def test_paired_evaluation_requires_same_fixture_and_generation_protocol(self):
        import inspect
        import louksnapg2_docling_q4_repair as repair
        source = inspect.getsource(repair.evaluate)
        self.assertIn('"same_fixture_and_generation_protocol": True', source)
        self.assertIn('"runs_are_sequential_separate_processes": True', source)
        self.assertIn('"teacher_source_bfloat16": teacher', source)
        protocol_source = inspect.getsource(repair._run_runtime_protocol)
        self.assertIn('LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES', protocol_source)
        self.assertIn('LOUKSNAPG2_DOCLING_CPU_THREADS', protocol_source)
        self.assertIn('LOUKSNAPG2_DOCLING_STAGE=', runtime.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
