[Reading 295 lines from start (total: 295 lines, 0 remaining)]

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

    def test_interrupted_dryrun_fails_closed_without_repeating_probe(self):
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
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertEqual(saved["conversion_resource_failure"]["returncode"], 125)
            self.assertEqual(saved["certification"], "NOT_GRANTED")
            self.assertIn("Do not retry", result["next_action"])

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
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIn("conversion_resource_failure", saved)

    def test_verified_swap_route_lowers_ram_floor_only_for_that_route(self):
        self.assertEqual(mod._minimum_conversion_ram_bytes(False), 2 * 1024**3)
        self.assertEqual(mod._minimum_conversion_ram_bytes(True), 1536 * 1024**2)

    def test_qwen3_retry_avoids_incompatible_tempfile_split_flags(self):
        lane={"venv_python":"/python", "model_inventory":{"tensor_total_size_bytes":29536614400}}
        cmd=mod._build_conversion_command(lane, pathlib.Path("convert_hf_to_gguf.py"),
            pathlib.Path("source-model"), pathlib.Path("candidate-R2.gguf"), 2)
        self.assertIn("--use-temp-file",cmd)
        self.assertNotIn("--split-max-size",cmd)
        self.assertIn("candidate-R2.gguf",cmd)

    def test_very_large_conversion_split_drops_tempfile_flag(self):
        lane={"venv_python":"/python", "model_inventory":{"tensor_total_size_bytes":65*1024**3}}
        cmd=mod._build_conversion_command(lane, pathlib.Path("convert_hf_to_gguf.py"),
            pathlib.Path("source-model"), pathlib.Path("candidate-R2.gguf"), 2)
        self.assertNotIn("--use-temp-file",cmd)
        self.assertIn("--split-max-size",cmd)

    def test_activation_guard_restores_preflight_to_one_real_conversion_step(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "dryrun.log"
            log.write_text("prior failed probe\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane["stage"] = "PROVISION_ENV"
            lane["candidate_id"] = "QWEN3_TEST_CANDIDATE"
            lane["candidate_dir"] = str(state / "cajita_candidates" / "QWEN3_TEST_CANDIDATE")
            lane["job"] = None
            mod._atomic(state / "cajita_priority_lane.json", lane)
            receipt=state / "recovery.json"
            receipt.write_text(json.dumps({"schema":"CUSTOSZ_CAJITA_RESOURCE_RECOVERY/1.0",
                "status":"RESOURCE_RECOVERY_VERIFIED","mission_sha256":mission_sha,
                "candidate_id":"QWEN3_TEST_CANDIDATE","swap_active":True,"swap_path":"/test/swap",
                "swap_bytes":4*1024**3,"memory_high_bytes":2560*1024**2,"memory_max_bytes":3*1024**3,
                "source_model_weights_modified":False,"no_competing_conversion":True}),encoding="utf-8")
            import hashlib
            evidence={"receipt_path":str(receipt),"receipt_sha256":hashlib.sha256(receipt.read_bytes()).hexdigest()}
            guard={"schema":"CUSTOSZ_CAJITA_QUANTIZATION_ACTIVATION_GUARD/1.0","status":"REAL_CONVERSION_ONLY",
                   "mission_sha256":mission_sha,"candidate_id":"QWEN3_TEST_CANDIDATE","lane_seed":lane,
                   "resource_recovery_evidence":evidence,"conversion_resource_failure":{"reason":"prior dryrun failed"}}
            mod._atomic(state / "cajita_quantization_activation_guard.json", guard)
            from unittest.mock import patch
            with patch.object(mod,"_guard_resource_receipt_valid",return_value=True), patch.object(mod,"_active_cajita_model_processes",return_value=[]):
                result=mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            saved=json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(result["status"],"CAJITA_REAL_CONVERSION_GUARD_RESTORED")
            self.assertEqual(saved["stage"],"CONVERT_RETRY")
            self.assertTrue(saved["quantization_guard_attempt_consumed"])
            self.assertEqual(saved["candidate_id"],"QWEN3_TEST_CANDIDATE")

    def test_activation_guard_defers_when_existing_model_tool_is_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log=state / "probe.log";log.write_text("existing probe\n",encoding="utf-8")
            lane=self._lane(state,mission_sha,log);lane["stage"]="PROVISION_ENV";lane["job"]=None
            mod._atomic(state / "cajita_priority_lane.json",lane)
            guard={"schema":"CUSTOSZ_CAJITA_QUANTIZATION_ACTIVATION_GUARD/1.0","status":"REAL_CONVERSION_ONLY",
                   "mission_sha256":mission_sha,"candidate_id":lane["candidate_id"],"lane_seed":lane,
                   "resource_recovery_evidence":{"receipt_path":"missing","receipt_sha256":"missing"},
                   "conversion_resource_failure":{"reason":"resource"}}
            mod._atomic(state / "cajita_quantization_activation_guard.json",guard)
            from unittest.mock import patch
            with patch.object(mod,"_active_cajita_model_processes",return_value=[{"pid":123,"kind":"CONVERTER"}]):
                result=mod.tick_cajita_priority_lane(state,root / "Cajita",mission_sha)
            saved=json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(result["status"],"CAJITA_ACTIVATION_GUARD_WAITING_FOR_EXISTING_PROCESS")
            self.assertEqual(saved["stage"],"PROVISION_ENV")

    def test_tensor_materializing_dryrun_space_failure_enters_resource_block(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "dryrun.log"
            log.write_text("OSError: Not enough free space to write 178257920 bytes\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane["stage"] = "DRY_RUN_RUNNING"
            mod._atomic(state / "cajita_priority_lane.json", lane)
            original = mod._read_job
            mod._read_job = lambda current: ({"returncode":1,"error":None}, False)
            try:
                mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            finally:
                mod._read_job = original
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIn("not enough free space to write", saved["conversion_resource_failure"]["failure_signatures"])
            self.assertEqual(saved["certification"], "NOT_GRANTED")

    def test_blocked_resource_stage_never_launches_another_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "failed.log"
            log.write_text("OSError\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane.update({"stage":"BLOCKED_CONVERSION_RESOURCE","conversion_resource_failure":{"reason":"resource"},"job":None})
            mod._atomic(state / "cajita_priority_lane.json", lane)
            result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(result["status"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIsNone(saved.get("job"))

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

    def test_resource_recovery_receipt_wrong_mission_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "convert.log"
            log.write_text("token_embd.weight\\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane.update({"stage":"CONVERT_RETRY","conversion_attempts":1,
                         "conversion_resource_failure":{"reason":"oom"}})
            receipt=state / "resource-recovery.json"
            receipt.write_text(json.dumps({"schema":"CUSTOSZ_CAJITA_RESOURCE_RECOVERY/1.0",
                "status":"RESOURCE_RECOVERY_VERIFIED","mission_sha256":"wrong-mission",
                "swap_active":True,"swap_bytes":4*1024**3,"memory_high_bytes":2560*1024**2,
                "memory_max_bytes":3*1024**3,"source_model_weights_modified":False,
                "no_competing_conversion":True}), encoding="utf-8")
            import hashlib
            lane["resource_recovery_evidence"]={"receipt_path":str(receipt),"receipt_sha256":hashlib.sha256(receipt.read_bytes()).hexdigest()}
            mod._atomic(state / "cajita_priority_lane.json", lane)
            result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertEqual(result["status"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIn("INVALID", saved["last_error"]["status"])

    def test_resource_recovery_receipt_requires_swap_currently_active(self):
        with tempfile.TemporaryDirectory() as tmp:
            operator, root, state, mission_sha = self._layout(tmp)
            log = state / "convert.log"
            log.write_text("token_embd.weight\\n", encoding="utf-8")
            lane = self._lane(state, mission_sha, log)
            lane.update({"stage":"CONVERT_RETRY","conversion_attempts":1,
                         "conversion_resource_failure":{"reason":"oom"}})
            receipt=state / "resource-recovery.json"
            receipt.write_text(json.dumps({"schema":"CUSTOSZ_CAJITA_RESOURCE_RECOVERY/1.0",
                "status":"RESOURCE_RECOVERY_VERIFIED","mission_sha256":mission_sha,
                "swap_active":True,"swap_path":"/tmp/custosz-swap-that-is-not-active.swap",
                "swap_bytes":4*1024**3,"memory_high_bytes":2560*1024**2,
                "memory_max_bytes":3*1024**3,"source_model_weights_modified":False,
                "no_competing_conversion":True}), encoding="utf-8")
            import hashlib
            lane["resource_recovery_evidence"]={"receipt_path":str(receipt),"receipt_sha256":hashlib.sha256(receipt.read_bytes()).hexdigest()}
            mod._atomic(state / "cajita_priority_lane.json", lane)
            result = mod.tick_cajita_priority_lane(state, root / "Cajita", mission_sha)
            saved = json.loads((state / "cajita_priority_lane.json").read_text())
            self.assertEqual(saved["stage"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertEqual(result["status"], "BLOCKED_CONVERSION_RESOURCE")
            self.assertIn("INVALID", saved["last_error"]["status"])

    def test_converter_tempdir_is_bound_to_candidate_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            temp_dir = pathlib.Path(tmp) / "candidate" / "converter_tmp"
            env = mod._bounded_compute_env({"TMPDIR": "/tmp"}, temp_dir=temp_dir)
            self.assertEqual(env["TMPDIR"], str(temp_dir))
            self.assertEqual(env["TEMP"], str(temp_dir))
            self.assertEqual(env["TMP"], str(temp_dir))
            self.assertTrue(temp_dir.is_dir())

    def test_numerical_libraries_are_thread_bounded(self):
        env = mod._bounded_compute_env({"OMP_NUM_THREADS": "64", "OPENBLAS_NUM_THREADS": "32"})
        for name in ("OMP_NUM_THREADS", "OMP_THREAD_LIMIT", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
            self.assertEqual(env[name], "1")
        self.assertEqual(env["TOKENIZERS_PARALLELISM"], "false")

if __name__ == "__main__":
    unittest.main(verbosity=2)

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]