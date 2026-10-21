[Reading 137 lines from start (total: 137 lines, 0 remaining)]

#!/usr/bin/env python3
"""Regression tests for bounded, fail-closed Cajita Qwen3 conversion progression."""
from __future__ import annotations
import hashlib
import importlib.util
import json
import pathlib
import tempfile
import unittest

GOVERNOR = pathlib.Path(__file__).resolve().parents[2] / "integrations" / "lunita-custoszv9" / "custoszv9_continuous_governor_v2.py"
spec = importlib.util.spec_from_file_location("cajita_governor_under_test", GOVERNOR)
assert spec and spec.loader
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

MISSION = """Cajita de Luna: máxima prioridad operativa por urgencia.
3.3. Cuantización, poda y optimización.
5. Segundo frente — cierre de Lunita.
La validación independiente y certificación son obligatorias.
"""

class CajitaQuantizationFlowTests(unittest.TestCase):
    def _layout(self, temp):
        operator = pathlib.Path(temp) / "0. CUSTOSZ - OPERADOR"
        root = operator / "CUSTOSZ_CONTINUITY_V1"
        state = root / "state"
        state.mkdir(parents=True)
        (operator / "MISION1.txt").write_text(MISSION, encoding="utf-8")
        mission_sha = hashlib.sha256((operator / "MISION1.txt").read_bytes()).hexdigest()
        return operator, root, state, mission_sha

    def _lane(self, state, mission_sha, log_path):
        lane = {
            "schema": "CUSTOSZ_CAJITA_PRIORITY_LANE_STATE/1.0", "mission_sha256": mission_sha,
            "stage": "DRY_RUN_RUNNING", "candidate_id": "QWEN3_TEST_CANDIDATE", "attempts": [],
            "job": {"pid": 999999, "receipt_path": str(state / "receipt.json"), "log_path": str(log_path)},
            "model_inventory": {"status": "PASS_MODEL_INVENTORY"},
            "toolchain": {"converter_source_commit": mod.EXPECTED_LLAMA_CPP_COMMIT,
                           "converter_source_status": "PASS", "quantizer_status": "PASS"},
            "certification": "NOT_GRANTED",
        }
        mod._atomic(state / "cajita_priority_lane.json", lane)
        return lane

    def test_interrupted_dryrun_advances_to_real_conversion_retry(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "dryrun.log"
            log.write_text("INFO Exporting model\\nKeyboardInterrupt\\n", encoding="utf-8")
            self._lane(state, mission_sha, log)
            original = mod._read_job
            mod._read_job = lambda lane: ({"returncode": 125, "error": "KeyboardInterrupt: "}, False)
            try:
                result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            finally:
                mod._read_job = original
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "CONVERT_RETRY")
            self.assertTrue(saved["dry_run_fallback_evidence"]["source_model_weights_modified"] is False)
            self.assertEqual(saved["certification"], "NOT_GRANTED")
            self.assertIn("BF16 conversion", result["next_action"])

    def test_dead_dryrun_without_receipt_at_tensor_boundary_advances(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "dryrun.log"
            log.write_text("INFO Exporting model\\ntoken_embd.weight, torch.bfloat16 --> BF16\\n", encoding="utf-8")
            self._lane(state, mission_sha, log)
            original = mod._read_job
            mod._read_job = lambda lane: (None, False)
            try:
                result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            finally:
                mod._read_job = original
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "CONVERT_RETRY")
            self.assertIn("LARGEST_TENSOR", saved["dry_run_fallback_evidence"]["reason"])

    def test_unrelated_dryrun_failure_does_not_bypass_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "dryrun.log"
            log.write_text("ImportError: unsupported architecture\\n", encoding="utf-8")
            self._lane(state, mission_sha, log)
            original = mod._read_job
            mod._read_job = lambda lane: ({"returncode": 1, "error": "ImportError: unsupported architecture"}, False)
            try:
                mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            finally:
                mod._read_job = original
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "DRY_RUN")
            self.assertNotIn("dry_run_fallback_evidence", saved)

    def test_converter_oom_at_largest_tensor_enters_resource_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "convert.log"
            log.write_text("INFO Exporting model\\ntoken_embd.weight, torch.bfloat16 --> BF16\\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane["stage"] = "CONVERSION_RUNNING"
            lane["conversion_attempts"] = 1
            mod._atomic(state / "cajita_priority_lane.json", lane)
            original = mod._read_job
            mod._read_job = lambda current: ({"returncode":125,"error":"KeyboardInterrupt: "}, False)
            try:
                result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            finally:
                mod._read_job = original
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIsNone(saved["resource_recovery_evidence"])
            self.assertIn("do not retry", result["next_action"].casefold())

    def test_resource_block_refuses_retry_without_hash_bound_receipt(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "convert.log"
            log.write_text("token_embd.weight\\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane.update({"stage":"CONVERT_RETRY","conversion_attempts":1,
                         "conversion_resource_failure":{"reason":"oom"},"resource_recovery_evidence":None})
            mod._atomic(state / "cajita_priority_lane.json", lane)
            result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertEqual(result["status"], "BLOCKED_CONVERSION_RESOURCE")

    def test_numerical_libraries_are_thread_bounded(self):
        env = mod._bounded_compute_env({"OMP_NUM_THREADS": "64", "OPENBLAS_NUM_THREADS": "32"})
        for name in ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(env[name], "1")
        self.assertEqual(env["TOKENIZERS_PARALLELISM"], "false")

if __name__ == "__main__":
    unittest.main(verbosity=2)

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]