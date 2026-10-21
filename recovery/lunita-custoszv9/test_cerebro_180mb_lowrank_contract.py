import ast
import json
import pathlib
import unittest

HERE = pathlib.Path(__file__).resolve().parent
WORKER = HERE / "cerebro_180mb_lowrank_v1.py"
RUNTIME = HERE / "cerebro_180mb_lowrank_runtime_v1.py"
DISPATCH = HERE / "custoszv9_cerebro_180mb_dispatch_v1.py"
if not DISPATCH.is_file():
    DISPATCH = HERE.parent / "custoszv9_cerebro_180mb_dispatch_v1.py"
MISSION = HERE / "CEREBRO_180MB_MISSION_20261021.json"


class Cerebro180MBContractTests(unittest.TestCase):
    def test_mission_is_pinned_and_uncertified(self):
        doc = json.loads(MISSION.read_text(encoding="utf-8"))
        self.assertEqual(doc["source_mission_sha256"], "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f")
        self.assertEqual(doc["target"]["candidate_directory_byte_cap"], 180_000_000)
        self.assertFalse(doc["target"]["padding_allowed"])
        self.assertEqual(doc["epistemic_status"]["certification"], "NOT_GRANTED")
        self.assertFalse(doc["immutability"]["canonical_promotion_authorized"])

    def test_sources_parse_without_executing_the_model(self):
        for path in (WORKER, RUNTIME, DISPATCH):
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())
                ast.parse(path.read_text(encoding="utf-8"), filename=str(path))

    def test_worker_serializes_processes_and_fails_closed_on_journal_corruption(self):
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("fcntl.flock", source)
        self.assertIn("WORKER_ALREADY_RUNNING", source)
        self.assertLess(source.index("_WORKER_LOCK_FD = os.open"), source.index("import torch"))
        self.assertIn("EVENT_SEQUENCE_INVALID", source)
        self.assertIn("UNJOURNALED_CHECKPOINT_REFUSED", source)
        self.assertIn("RECOVERY_CHECKPOINT_IMPORTED", source)

    def test_dispatcher_guards_duplicate_launches_and_uses_isolated_recovery_state(self):
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("cerebro_180mb_dispatch.lock", source)
        self.assertIn("cerebro_180mb_worker.lock", source)
        self.assertIn("DISPATCH_ALREADY_RUNNING", source)
        self.assertIn("WORKER_SINGLETON_LOCK_HELD", source)
        self.assertIn("dispatch_state.json", source)
        self.assertIn("verify_worker_journal", source)
        self.assertIn("CEREBRO_JOB_DIR", source)
        self.assertIn("DISPATCH_STATE_ALREADY_EXISTS_NO_OVERWRITE", source)
        self.assertIn("probe_resource_snapshot", source)
        self.assertIn("/proc/meminfo:MemAvailable", source)
        self.assertIn("replace(snapshot, ram_available_bytes=available", source)

    def test_worker_validates_mxfp4_block_scale_pairs_across_shards(self):
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("MXFP4_GATE_UP_BLOCK_SCALE_SHARDS_DIFFER", source)
        self.assertIn("MXFP4_DOWN_BLOCK_SCALE_SHARDS_DIFFER", source)
        self.assertNotIn("MXFP4_EXPERT_TENSORS_SPLIT_ACROSS_SHARDS", source)
        self.assertIn("decode_one_expert(paths[\"gu_blocks\"], paths[\"gu_scales\"]", source)
        self.assertIn("decode_one_expert(paths[\"down_blocks\"], paths[\"down_scales\"]", source)

    def test_worker_has_hard_size_gate_and_checkpoints(self):
        source = WORKER.read_text(encoding="utf-8")
        self.assertIn("TARGET_BYTES = 180_000_000", source)
        self.assertIn("HARD_SIZE_GATE", source)
        self.assertIn("expert_chunks", source)
        self.assertIn("SOURCE_NONMUTATION_POSTCHECK_PASS", source)
        self.assertIn("certification", source.lower())

    def test_runtime_keeps_original_gpt_oss_architecture_and_declares_lossy_mapping(self):
        source = RUNTIME.read_text(encoding="utf-8")
        self.assertIn("GptOssForCausalLM", source)
        self.assertIn("class LowRankExperts", source)
        self.assertIn("class LowRankRouter", source)
        self.assertIn("quality_equivalence", source)

    def test_dispatch_pins_v9_and_applies_resource_caps(self):
        source = DISPATCH.read_text(encoding="utf-8")
        self.assertIn("EXPECTED_V9_SHA", source)
        self.assertIn("MemoryMax=1G", source)
        self.assertIn("MemoryHigh=768M", source)
        self.assertIn("CPUQuota=50%", source)
        self.assertIn("run_bounded_mission", source)
        self.assertIn("WRITE_CAJITA_WITH_CHECKPOINTS", source)


if __name__ == "__main__":
    unittest.main()

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]