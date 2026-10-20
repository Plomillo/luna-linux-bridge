import json
import pathlib
import sys
import tempfile
import unittest

HERE = pathlib.Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import custoszv9_continuous_governor_v2 as governor


class FailClosedClassificationTests(unittest.TestCase):
    def test_blocked_status_without_explicit_flag_is_blocked(self):
        for status in (
            "BLOCKED_TEST",
            "SOURCE_MISSING_BLOCKED",
            "CANDIDATE_PLAN_IDENTITY_MISMATCH_BLOCKED",
            "BETA_BLOCKED_INDEPENDENT_VALIDATION",
            "BLOCKED_NOT_RUN",
        ):
            with self.subTest(status=status):
                self.assertTrue(governor.result_blocks_step({"status": status}))

    def test_explicit_false_blocks_even_when_status_sounds_successful(self):
        self.assertTrue(governor.result_blocks_step({
            "status": "PASS_FOR_SUBTASK_ONLY",
            "step_completion": False,
        }))

    def test_valid_subtask_does_not_block(self):
        self.assertFalse(governor.result_blocks_step({
            "status": "PASS_FOR_SUBTASK_ONLY",
            "step_completion": True,
        }))
        self.assertFalse(governor.result_blocks_step({
            "status": "PASS_RUNTIME_TESTS",
            "step_completion": True,
        }))

    def test_missing_or_non_object_result_fails_closed(self):
        self.assertTrue(governor.result_blocks_step({}))
        self.assertTrue(governor.result_blocks_step(None))


class QwenModelInventoryTests(unittest.TestCase):
    def test_exact_qwen_bf16_inventory_passes_without_mutating_weights(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            shard_name = "model-00001-of-00001.safetensors"
            shard = root / shard_name
            shard.write_bytes(b"fixture-weights")
            config = root / "config.json"
            config.write_text(json.dumps({
                "architectures": ["Qwen3ForCausalLM"],
                "torch_dtype": "bfloat16",
                "model_type": "qwen3",
            }), encoding="utf-8")
            index = root / "model.safetensors.index.json"
            index.write_text(json.dumps({
                "metadata": {"total_size": 1024},
                "weight_map": {"layer.fixture": shard_name},
            }), encoding="utf-8")
            before_hash = governor._sha256(shard)
            before_stat = shard.stat()
            result = governor._model_inventory(root)
            self.assertEqual(result["status"], "PASS_MODEL_INVENTORY")
            self.assertEqual(result["shard_count"], 1)
            self.assertEqual(result["missing_shards"], [])
            self.assertFalse(result["model_weights_modified"])
            self.assertEqual(governor._sha256(shard), before_hash)
            after_stat = shard.stat()
            self.assertEqual(before_stat.st_size, after_stat.st_size)
            self.assertEqual(before_stat.st_mtime_ns, after_stat.st_mtime_ns)

    def test_missing_shard_is_blocking(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = pathlib.Path(tmp)
            (root / "config.json").write_text(json.dumps({
                "architectures": ["Qwen3ForCausalLM"], "torch_dtype": "bfloat16"
            }), encoding="utf-8")
            (root / "model.safetensors.index.json").write_text(json.dumps({
                "metadata": {"total_size": 1024},
                "weight_map": {"layer.fixture": "missing.safetensors"},
            }), encoding="utf-8")
            result = governor._model_inventory(root)
            self.assertEqual(result["status"], "BLOCKED_MODEL_IDENTITY_OR_SHARDS")
            self.assertEqual(result["missing_shards"], ["missing.safetensors"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
