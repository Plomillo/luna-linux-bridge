"""Behavioral tests for D06 capabilities 177-230."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "domains" / "d06_177_230.py"
spec = importlib.util.spec_from_file_location("d06_177_230", MODULE_PATH)
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
assert spec.loader is not None
spec.loader.exec_module(mod)

A = "a" * 64
B = "b" * 64
T = [{"id": "lib", "deps": [], "inputs": [A]}, {"id": "app", "deps": ["lib"], "inputs": [B]}]


def _ok():
    m = mod
    return {
        177: lambda: m.hermetic_execution_engine(target_id="app", inputs=[A], network=False),
        178: lambda: m.content_based_cache(key_sha256=A, payload_sha256=B, store={}),
        179: lambda: m.remote_cache(endpoint="https://cache.example", auth_ref="ref", key_sha256=A),
        180: lambda: m.remote_execution_interface(digest_sha256=A, hermetic=True, network=False),
        181: lambda: m.fine_grained_invalidation(targets=T, changed="lib"),
        182: lambda: m.affected_target_analysis(targets=T, changed_inputs={"lib": [A]}),
        183: lambda: m.build_graph(targets=T),
        184: lambda: m.build_target_identity(name="app", config_sha256=A),
        185: lambda: m.build_reproducibility_proof(left_sha256=A, right_sha256=A, includes_timestamp=False),
        186: lambda: m.build_sandbox(root="/work", path="src/main.rs"),
        187: lambda: m.build_parallelizer(targets=T),
        188: lambda: m.critical_path_analyzer(targets=T, costs={"lib": 2, "app": 3}),
        189: lambda: m.incremental_build_engine(targets=T, dirty=["app"]),
        190: lambda: m.monorepo_engine(packages={"core": ["lib"], "app": ["app"]}),
        191: lambda: m.ai_factory(recipe_id="r1", base_sha256=A),
        192: lambda: m.model_architecture_registry(entries=[{"id": "llama"}]),
        193: lambda: m.model_component_registry(entries=[{"id": "attn"}]),
        194: lambda: m.tokenizer_factory(vocab=["a", "b"]),
        195: lambda: m.dataset_factory(dataset_id="d", license_id="MIT"),
        196: lambda: m.corpus_factory(corpus_id="c", documents=[A]),
        197: lambda: m.dataset_deduplication(hashes=[A, A, B]),
        198: lambda: m.dataset_provenance(dataset_id="d", source_sha256=A),
        199: lambda: m.dataset_license_engine(license_id="Apache-2.0"),
        200: lambda: m.dataset_contamination_analyzer(train_ids=["1"], eval_ids=["2"]),
        201: lambda: m.dataset_quality_scorer(score=0.5),
        202: lambda: m.synthetic_data_generator(seed=1, count=2),
        203: lambda: m.synthetic_data_validator(rows=[{"text": "a"}], required=["text"]),
        204: lambda: m.training_recipe_registry(entries=[{"id": "sft"}]),
        205: lambda: m.pretraining_engine_interface(base_sha256=A, frozen=True),
        206: lambda: m.finetuning_engine(base_sha256=A, dataset_sha256=B),
        207: lambda: m.peft_engine(rank=8, adapter_id="a"),
        208: lambda: m.lora_provider(rank=4, targets=["q_proj"]),
        209: lambda: m.qlora_provider(bits=4, rank=8),
        210: lambda: m.advanced_lora_provider(targets=["q", "v"], rank=8),
        211: lambda: m.sft_engine(examples=[{"prompt": "p", "chosen": "c"}]),
        212: lambda: m.dpo_engine(pairs=[{"chosen": "a", "rejected": "b"}]),
        213: lambda: m.grpo_engine(group_size=4, prompts=["p"]),
        214: lambda: m.reward_model_engine(pairs=[{"prompt": "p", "chosen": "c"}]),
        215: lambda: m.process_reward_model_engine(steps=[{"score": 0.2}]),
        216: lambda: m.distillation_factory(teacher="big", student="small"),
        217: lambda: m.multi_teacher_distillation(teachers=["a", "b"], student="s"),
        218: lambda: m.mixture_of_experts_factory(experts=["e1", "e2"]),
        219: lambda: m.routing_engine_factory(experts=["e1"], routes={"tok": "e1"}),
        220: lambda: m.model_merging_engine(weights={"a": 0.25, "b": 0.75}),
        221: lambda: m.model_composition_engine(parts=[{"id": "root"}, {"id": "attn", "parent": "root"}]),
        222: lambda: m.model_surgery_engine(op="drop", target="lm_head"),
        223: lambda: m.checkpoint_transformer(from_sha256=A, to_sha256=B),
        224: lambda: m.model_converter(source_format="hf", target_format="gguf"),
        225: lambda: m.model_quantizer(bits=4),
        226: lambda: m.model_pruner(sparsity=0.4),
        227: lambda: m.model_sparsifier(mask_sha256=A),
        228: lambda: m.model_compiler(backend="cpu"),
        229: lambda: m.model_benchmark_engine(metric="loss", value=1.2),
        230: lambda: m.model_evaluation_matrix(axes=["lang"], metric="accuracy"),
    }


def _bad():
    m = mod
    return {
        177: ("hermetic_execution_rejects_network", lambda: m.hermetic_execution_engine(target_id="app", inputs=[A], network=True)),
        178: ("cache_key_collision", lambda: m.content_based_cache(key_sha256=A, payload_sha256=B, store={A: "c" * 64})),
        179: ("remote_cache_requires_https", lambda: m.remote_cache(endpoint="http://cache", auth_ref="r", key_sha256=A)),
        180: ("remote_exec_hermetic_rejects_network", lambda: m.remote_execution_interface(digest_sha256=A, hermetic=True, network=True)),
        181: ("invalidation_target_unknown", lambda: m.fine_grained_invalidation(targets=T, changed="missing")),
        182: ("changed_input_not_in_target", lambda: m.affected_target_analysis(targets=T, changed_inputs={"lib": [B]})),
        183: ("build_cycle", lambda: m.build_graph(targets=[{"id": "a", "deps": ["b"], "inputs": []}, {"id": "b", "deps": ["a"], "inputs": []}])),
        184: ("config_sha256_must_be_lowercase_sha256", lambda: m.build_target_identity(name="app", config_sha256="nope")),
        185: ("reproducible_build_rejects_timestamp", lambda: m.build_reproducibility_proof(left_sha256=A, right_sha256=A, includes_timestamp=True)),
        186: ("sandbox_escape", lambda: m.build_sandbox(root="/work", path="../etc/passwd")),
        187: ("build_cycle", lambda: m.build_parallelizer(targets=[{"id": "a", "deps": ["b"], "inputs": []}, {"id": "b", "deps": ["a"], "inputs": []}])),
        188: ("critical_cost_invalid", lambda: m.critical_path_analyzer(targets=T, costs={"lib": -1, "app": 1})),
        189: ("dirty_target_unknown", lambda: m.incremental_build_engine(targets=T, dirty=["missing"])),
        190: ("target_in_two_packages", lambda: m.monorepo_engine(packages={"a": ["lib"], "b": ["lib"]})),
        191: ("recipe_id_required", lambda: m.ai_factory(recipe_id="", base_sha256=A)),
        192: ("registry_duplicate_id", lambda: m.model_architecture_registry(entries=[{"id": "a"}, {"id": "a"}])),
        193: ("id_required", lambda: m.model_component_registry(entries=[{}])),
        194: ("duplicate_token", lambda: m.tokenizer_factory(vocab=["a", "a"])),
        195: ("dataset_license_unknown", lambda: m.dataset_factory(dataset_id="d", license_id="NOPE")),
        196: ("corpus_documents_required", lambda: m.corpus_factory(corpus_id="c", documents=[])),
        197: ("dedup_hashes_required", lambda: m.dataset_deduplication(hashes=[])),
        198: ("source_sha256_must_be_lowercase_sha256", lambda: m.dataset_provenance(dataset_id="d", source_sha256="x")),
        199: ("license_unknown", lambda: m.dataset_license_engine(license_id="custom")),
        200: ("contamination_sets_required", lambda: m.dataset_contamination_analyzer(train_ids="1", eval_ids=[])),
        201: ("quality_score_out_of_range", lambda: m.dataset_quality_scorer(score=2)),
        202: ("synthetic_seed_required", lambda: m.synthetic_data_generator(seed="s", count=1)),
        203: ("synthetic_schema_mismatch", lambda: m.synthetic_data_validator(rows=[{}], required=["text"])),
        204: ("registry_duplicate_id", lambda: m.training_recipe_registry(entries=[{"id": "a"}, {"id": "a"}])),
        205: ("pretraining_base_must_be_frozen", lambda: m.pretraining_engine_interface(base_sha256=A, frozen=False)),
        206: ("finetune_dataset_must_differ_from_base", lambda: m.finetuning_engine(base_sha256=A, dataset_sha256=A)),
        207: ("peft_rank_required", lambda: m.peft_engine(rank=0, adapter_id="a")),
        208: ("lora_targets_required", lambda: m.lora_provider(rank=4, targets=[])),
        209: ("qlora_bits_unsupported", lambda: m.qlora_provider(bits=16, rank=4)),
        210: ("advanced_lora_requires_multiple_targets", lambda: m.advanced_lora_provider(targets=["q"], rank=4)),
        211: ("sft_pairs_required", lambda: m.sft_engine(examples=[])),
        212: ("dpo_preference_must_differ", lambda: m.dpo_engine(pairs=[{"chosen": "a", "rejected": "a"}])),
        213: ("grpo_group_size_required", lambda: m.grpo_engine(group_size=1, prompts=["p"])),
        214: ("reward_pairs_required", lambda: m.reward_model_engine(pairs=[])),
        215: ("process_score_out_of_range", lambda: m.process_reward_model_engine(steps=[{"score": 2}])),
        216: ("distillation_teacher_must_differ", lambda: m.distillation_factory(teacher="m", student="m")),
        217: ("multi_teacher_requires_two", lambda: m.multi_teacher_distillation(teachers=["a"], student="s")),
        218: ("duplicate_expert", lambda: m.mixture_of_experts_factory(experts=["e", "e"])),
        219: ("route_expert_unknown", lambda: m.routing_engine_factory(experts=["e1"], routes={"t": "nope"})),
        220: ("merge_weights_must_sum_to_one", lambda: m.model_merging_engine(weights={"a": 0.2, "b": 0.2})),
        221: ("composition_parent_unknown", lambda: m.model_composition_engine(parts=[{"id": "a", "parent": "missing"}])),
        222: ("surgery_op_unknown", lambda: m.model_surgery_engine(op="destroy", target="x")),
        223: ("checkpoint_requires_distinct_states", lambda: m.checkpoint_transformer(from_sha256=A, to_sha256=A)),
        224: ("converter_formats_must_differ", lambda: m.model_converter(source_format="hf", target_format="hf")),
        225: ("quantizer_bits_unsupported", lambda: m.model_quantizer(bits=7)),
        226: ("pruner_sparsity_invalid", lambda: m.model_pruner(sparsity=1)),
        227: ("mask_sha256_must_be_lowercase_sha256", lambda: m.model_sparsifier(mask_sha256="zz")),
        228: ("compiler_backend_unsupported", lambda: m.model_compiler(backend="brain")),
        229: ("benchmark_value_required", lambda: m.model_benchmark_engine(metric="loss", value="high")),
        230: ("eval_axes_required", lambda: m.model_evaluation_matrix(axes=[], metric="acc")),
    }


class D06Tests(unittest.TestCase):
    def test_catalog_covers_177_through_230(self):
        self.assertEqual(set(mod.FUNCS), set(range(177, 231)))


def _bind(cid: int):
    def test(self):
        result = _ok()[cid]()
        self.assertFalse(result["certification_granted"])
        self.assertFalse(result["global_certification"])
        self.assertFalse(result["theorem_claim"])
        err, bad = _bad()[cid]
        with self.assertRaisesRegex(ValueError, err):
            bad()
    return test


for _cid in range(177, 231):
    setattr(D06Tests, f"test_cap_{_cid:04d}", _bind(_cid))


if __name__ == "__main__":
    unittest.main()
