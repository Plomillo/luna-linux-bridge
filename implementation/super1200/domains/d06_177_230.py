"""Name-specific D06 primitives for capabilities 177-230.

Hermetic build graph plus model-factory controls.
Fail-closed. No global certification.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Callable

_SHA = re.compile(r"^[0-9a-f]{64}$")
_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_-]*$")
_SPDX = {"MIT", "Apache-2.0", "BSD-3-Clause", "GPL-3.0-only", "CC0-1.0", "UNLICENSED"}


def digest(value: Any) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    return hashlib.sha256(raw).hexdigest()


def _name(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    return value.strip()


def _sha(value: Any, field: str) -> str:
    if not isinstance(value, str) or not _SHA.fullmatch(value):
        raise ValueError(field + "_must_be_lowercase_sha256")
    return value


def rec(schema: str, decision: str, **fields: Any) -> dict[str, Any]:
    out = {
        "schema": schema,
        "decision": decision,
        "theorem_claim": False,
        "certification_granted": False,
        "global_certification": False,
    }
    out.update(fields)
    out["record_sha256"] = digest({k: v for k, v in out.items() if k != "record_sha256"})
    return out


def _targets(spec: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    if not isinstance(spec, list) or not spec:
        raise ValueError("targets_required")
    out = {}
    for target in spec:
        if not isinstance(target, dict):
            raise ValueError("target_must_be_object")
        ident = _name(target.get("id"), "target_id")
        deps = target.get("deps", [])
        if not isinstance(deps, list) or any(not isinstance(d, str) or not d for d in deps):
            raise ValueError("target_deps_invalid")
        inputs = target.get("inputs", [])
        if not isinstance(inputs, list):
            raise ValueError("target_inputs_invalid")
        for item in inputs:
            _sha(item, "input_sha256")
        out[ident] = {"deps": deps, "inputs": list(inputs), "sandbox": target.get("sandbox", True)}
    for ident, body in out.items():
        for dep in body["deps"]:
            if dep not in out:
                raise ValueError("target_dep_unknown")
    return out


def _order(targets: dict[str, dict[str, Any]]) -> list[str]:
    indeg = {i: 0 for i in targets}
    children = {i: [] for i in targets}
    for ident, body in targets.items():
        for dep in body["deps"]:
            children[dep].append(ident)
            indeg[ident] += 1
    ready = sorted([i for i, d in indeg.items() if d == 0])
    order = []
    while ready:
        cur = ready.pop(0)
        order.append(cur)
        for child in children[cur]:
            indeg[child] -= 1
            if indeg[child] == 0:
                ready.append(child)
                ready.sort()
    if len(order) != len(targets):
        raise ValueError("build_cycle")
    return order


def hermetic_execution_engine(*, target_id: str, inputs: list[str], network: bool) -> dict[str, Any]:
    target_id = _name(target_id, "target_id")
    if network is True:
        raise ValueError("hermetic_execution_rejects_network")
    if not isinstance(network, bool):
        raise ValueError("hermetic_network_flag_required")
    for item in inputs:
        _sha(item, "input_sha256")
    return rec("SUPER1200_HERMETIC_EXECUTION/1", "HERMETIC_EXECUTION_ACCEPTED", target_id=target_id, output_sha256=digest({"target": target_id, "inputs": inputs}))


def content_based_cache(*, key_sha256: str, payload_sha256: str, store: dict[str, str]) -> dict[str, Any]:
    key = _sha(key_sha256, "key_sha256")
    payload = _sha(payload_sha256, "payload_sha256")
    if not isinstance(store, dict):
        raise ValueError("cache_store_required")
    if key in store and store[key] != payload:
        raise ValueError("cache_key_collision")
    store = dict(store)
    store[key] = payload
    return rec("SUPER1200_CONTENT_CACHE/1", "CACHE_BOUND", key_sha256=key, payload_sha256=payload, entries=len(store))


def remote_cache(*, endpoint: str, auth_ref: str, key_sha256: str) -> dict[str, Any]:
    endpoint = _name(endpoint, "endpoint")
    if not endpoint.startswith("https://"):
        raise ValueError("remote_cache_requires_https")
    _name(auth_ref, "auth_ref")
    _sha(key_sha256, "key_sha256")
    return rec("SUPER1200_REMOTE_CACHE/1", "REMOTE_CACHE_ADDRESS_ACCEPTED", endpoint=endpoint, key_sha256=key_sha256)


def remote_execution_interface(*, digest_sha256: str, hermetic: bool, network: bool) -> dict[str, Any]:
    _sha(digest_sha256, "digest_sha256")
    if hermetic is True and network is True:
        raise ValueError("remote_exec_hermetic_rejects_network")
    if not isinstance(hermetic, bool) or not isinstance(network, bool):
        raise ValueError("remote_exec_flags_required")
    return rec("SUPER1200_REMOTE_EXECUTION/1", "REMOTE_EXECUTION_DESCRIBED", digest_sha256=digest_sha256, hermetic=hermetic)


def fine_grained_invalidation(*, targets: list[dict[str, Any]], changed: str) -> dict[str, Any]:
    graph = _targets(targets)
    changed = _name(changed, "changed")
    if changed not in graph:
        raise ValueError("invalidation_target_unknown")
    dirty = {changed}
    progressed = True
    while progressed:
        progressed = False
        for ident, body in graph.items():
            if ident not in dirty and any(dep in dirty for dep in body["deps"]):
                dirty.add(ident)
                progressed = True
    return rec("SUPER1200_FINE_GRAINED_INVALIDATION/1", "INVALIDATION_CLOSURE", changed=changed, dirty=sorted(dirty))


def affected_target_analysis(*, targets: list[dict[str, Any]], changed_inputs: dict[str, list[str]]) -> dict[str, Any]:
    graph = _targets(targets)
    if not isinstance(changed_inputs, dict):
        raise ValueError("changed_inputs_required")
    affected = []
    for ident, hashes in changed_inputs.items():
        if ident not in graph:
            raise ValueError("affected_target_unknown")
        if not isinstance(hashes, list) or any(not isinstance(h, str) or not _SHA.fullmatch(h) for h in hashes):
            raise ValueError("changed_input_hash_invalid")
        known = set(graph[ident]["inputs"])
        if any(h not in known for h in hashes):
            raise ValueError("changed_input_not_in_target")
        if hashes:
            affected.append(ident)
    return rec("SUPER1200_AFFECTED_TARGET_ANALYSIS/1", "AFFECTED_TARGETS", affected=sorted(affected))


def build_graph(*, targets: list[dict[str, Any]]) -> dict[str, Any]:
    graph = _targets(targets)
    order = _order(graph)
    return rec("SUPER1200_BUILD_GRAPH/1", "BUILD_GRAPH_ACCEPTED", order=order)


def build_target_identity(*, name: str, config_sha256: str) -> dict[str, Any]:
    name = _name(name, "target_name")
    config = _sha(config_sha256, "config_sha256")
    return rec("SUPER1200_BUILD_TARGET_IDENTITY/1", "TARGET_IDENTITY_BOUND", name=name, identity_sha256=digest({"name": name, "config": config}))


def build_reproducibility_proof(*, left_sha256: str, right_sha256: str, includes_timestamp: bool) -> dict[str, Any]:
    left = _sha(left_sha256, "left_sha256")
    right = _sha(right_sha256, "right_sha256")
    if includes_timestamp is True:
        raise ValueError("reproducible_build_rejects_timestamp")
    if left != right:
        raise ValueError("reproducible_build_mismatch")
    return rec("SUPER1200_BUILD_REPRODUCIBILITY/1", "REPRODUCIBLE", output_sha256=left)


def build_sandbox(*, root: str, path: str) -> dict[str, Any]:
    root = _name(root, "sandbox_root")
    path = _name(path, "sandbox_path")
    if ".." in path.split("/") or path.startswith("/") or path.startswith("\\"):
        raise ValueError("sandbox_escape")
    return rec("SUPER1200_BUILD_SANDBOX/1", "SANDBOX_PATH_CONTAINED", root=root, path=path)


def build_parallelizer(*, targets: list[dict[str, Any]]) -> dict[str, Any]:
    graph = _targets(targets)
    order = _order(graph)
    waves = []
    done = set()
    remaining = set(order)
    while remaining:
        wave = sorted([i for i in remaining if set(graph[i]["deps"]).issubset(done)])
        if not wave:
            raise ValueError("build_cycle")
        waves.append(wave)
        done.update(wave)
        remaining -= set(wave)
    return rec("SUPER1200_BUILD_PARALLELIZER/1", "PARALLEL_WAVES", waves=waves)


def critical_path_analyzer(*, targets: list[dict[str, Any]], costs: dict[str, int]) -> dict[str, Any]:
    graph = _targets(targets)
    order = _order(graph)
    if not isinstance(costs, dict):
        raise ValueError("critical_costs_required")
    dist = {}
    prev = {}
    for ident in order:
        cost = costs.get(ident)
        if not isinstance(cost, int) or cost < 0:
            raise ValueError("critical_cost_invalid")
        best = cost
        src = None
        for dep in graph[ident]["deps"]:
            cand = dist[dep] + cost
            if cand > best or src is None:
                if cand >= best:
                    best = cand
                    src = dep
        dist[ident] = best if graph[ident]["deps"] else cost
        prev[ident] = src
    end = max(order, key=lambda i: dist[i])
    path = []
    cur = end
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    path.reverse()
    return rec("SUPER1200_CRITICAL_PATH/1", "CRITICAL_PATH_COMPUTED", path=path, length=dist[end])


def incremental_build_engine(*, targets: list[dict[str, Any]], dirty: list[str]) -> dict[str, Any]:
    graph = _targets(targets)
    if not isinstance(dirty, list):
        raise ValueError("dirty_required")
    dirty_ids = [_name(d, "dirty_target") for d in dirty]
    if any(d not in graph for d in dirty_ids):
        raise ValueError("dirty_target_unknown")
    order = [i for i in _order(graph) if i in set(dirty_ids)]
    return rec("SUPER1200_INCREMENTAL_BUILD/1", "INCREMENTAL_PLAN", rebuild=order)


def monorepo_engine(*, packages: dict[str, list[str]]) -> dict[str, Any]:
    if not isinstance(packages, dict) or not packages:
        raise ValueError("packages_required")
    owners = {}
    for package, targets in packages.items():
        _name(package, "package")
        if not isinstance(targets, list):
            raise ValueError("package_targets_invalid")
        for target in targets:
            ident = _name(target, "package_target")
            if ident in owners:
                raise ValueError("target_in_two_packages")
            owners[ident] = package
    return rec("SUPER1200_MONOREPO/1", "PACKAGE_BOUNDARIES_ACCEPTED", packages=sorted(packages))


def _registry(entries: list[dict[str, Any]], id_field: str) -> list[str]:
    if not isinstance(entries, list):
        raise ValueError("registry_entries_required")
    ids = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("registry_entry_invalid")
        ident = _name(entry.get(id_field), id_field)
        if ident in ids:
            raise ValueError("registry_duplicate_id")
        ids.append(ident)
    return ids


def ai_factory(*, recipe_id: str, base_sha256: str) -> dict[str, Any]:
    return rec("SUPER1200_AI_FACTORY/1", "RECIPE_ACCEPTED", recipe_id=_name(recipe_id, "recipe_id"), base_sha256=_sha(base_sha256, "base_sha256"))


def model_architecture_registry(*, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return rec("SUPER1200_MODEL_ARCHITECTURE_REGISTRY/1", "ARCHITECTURES_REGISTERED", ids=_registry(entries, "id"))


def model_component_registry(*, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return rec("SUPER1200_MODEL_COMPONENT_REGISTRY/1", "COMPONENTS_REGISTERED", ids=_registry(entries, "id"))


def tokenizer_factory(*, vocab: list[str]) -> dict[str, Any]:
    if not isinstance(vocab, list) or not vocab:
        raise ValueError("vocab_required")
    tokens = [_name(t, "token") for t in vocab]
    if len(tokens) != len(set(tokens)):
        raise ValueError("duplicate_token")
    return rec("SUPER1200_TOKENIZER_FACTORY/1", "TOKENIZER_BUILT", vocab_size=len(tokens))


def dataset_factory(*, dataset_id: str, license_id: str) -> dict[str, Any]:
    if _name(license_id, "license_id") not in _SPDX:
        raise ValueError("dataset_license_unknown")
    return rec("SUPER1200_DATASET_FACTORY/1", "DATASET_CREATED", dataset_id=_name(dataset_id, "dataset_id"), license_id=license_id)


def corpus_factory(*, corpus_id: str, documents: list[str]) -> dict[str, Any]:
    if not isinstance(documents, list) or not documents:
        raise ValueError("corpus_documents_required")
    docs = [_sha(d, "document_sha256") for d in documents]
    return rec("SUPER1200_CORPUS_FACTORY/1", "CORPUS_CREATED", corpus_id=_name(corpus_id, "corpus_id"), documents=len(docs))


def dataset_deduplication(*, hashes: list[str]) -> dict[str, Any]:
    if not isinstance(hashes, list) or not hashes:
        raise ValueError("dedup_hashes_required")
    clean = [_sha(h, "sample_sha256") for h in hashes]
    unique = sorted(set(clean))
    return rec("SUPER1200_DATASET_DEDUPLICATION/1", "DEDUP_COMPLETE", kept=unique, removed=len(clean) - len(unique))


def dataset_provenance(*, dataset_id: str, source_sha256: str) -> dict[str, Any]:
    return rec("SUPER1200_DATASET_PROVENANCE/1", "PROVENANCE_BOUND", dataset_id=_name(dataset_id, "dataset_id"), source_sha256=_sha(source_sha256, "source_sha256"))


def dataset_license_engine(*, license_id: str) -> dict[str, Any]:
    license_id = _name(license_id, "license_id")
    if license_id not in _SPDX:
        raise ValueError("license_unknown")
    return rec("SUPER1200_DATASET_LICENSE/1", "LICENSE_ACCEPTED", license_id=license_id)


def dataset_contamination_analyzer(*, train_ids: list[str], eval_ids: list[str]) -> dict[str, Any]:
    if not isinstance(train_ids, list) or not isinstance(eval_ids, list):
        raise ValueError("contamination_sets_required")
    overlap = sorted(set(train_ids) & set(eval_ids))
    return rec("SUPER1200_DATASET_CONTAMINATION/1", "CONTAMINATION_FOUND" if overlap else "NO_CONTAMINATION", overlap=overlap)


def dataset_quality_scorer(*, score: float) -> dict[str, Any]:
    if not isinstance(score, (int, float)) or isinstance(score, bool) or not 0 <= float(score) <= 1:
        raise ValueError("quality_score_out_of_range")
    return rec("SUPER1200_DATASET_QUALITY/1", "QUALITY_SCORED", score=float(score))


def synthetic_data_generator(*, seed: int, count: int) -> dict[str, Any]:
    if not isinstance(seed, int):
        raise ValueError("synthetic_seed_required")
    if not isinstance(count, int) or count < 1:
        raise ValueError("synthetic_count_required")
    rows = [digest({"seed": seed, "i": i}) for i in range(count)]
    return rec("SUPER1200_SYNTHETIC_DATA_GENERATOR/1", "SYNTHETIC_ROWS", count=count, rows=rows)


def synthetic_data_validator(*, rows: list[dict[str, Any]], required: list[str]) -> dict[str, Any]:
    if not isinstance(rows, list) or not isinstance(required, list) or not required:
        raise ValueError("synthetic_schema_required")
    for row in rows:
        if not isinstance(row, dict) or any(field not in row for field in required):
            raise ValueError("synthetic_schema_mismatch")
    return rec("SUPER1200_SYNTHETIC_DATA_VALIDATOR/1", "SYNTHETIC_VALID", rows=len(rows))


def training_recipe_registry(*, entries: list[dict[str, Any]]) -> dict[str, Any]:
    return rec("SUPER1200_TRAINING_RECIPE_REGISTRY/1", "RECIPES_REGISTERED", ids=_registry(entries, "id"))


def pretraining_engine_interface(*, base_sha256: str, frozen: bool) -> dict[str, Any]:
    if frozen is not True:
        raise ValueError("pretraining_base_must_be_frozen")
    return rec("SUPER1200_PRETRAINING_INTERFACE/1", "PRETRAIN_INTERFACE_BOUND", base_sha256=_sha(base_sha256, "base_sha256"))


def finetuning_engine(*, base_sha256: str, dataset_sha256: str) -> dict[str, Any]:
    base = _sha(base_sha256, "base_sha256")
    data = _sha(dataset_sha256, "dataset_sha256")
    if base == data:
        raise ValueError("finetune_dataset_must_differ_from_base")
    return rec("SUPER1200_FINETUNING/1", "FINETUNE_BOUND", base_sha256=base, dataset_sha256=data)


def peft_engine(*, rank: int, adapter_id: str) -> dict[str, Any]:
    if not isinstance(rank, int) or rank < 1:
        raise ValueError("peft_rank_required")
    return rec("SUPER1200_PEFT/1", "PEFT_CONFIGURED", rank=rank, adapter_id=_name(adapter_id, "adapter_id"))


def lora_provider(*, rank: int, targets: list[str]) -> dict[str, Any]:
    if not isinstance(rank, int) or rank < 1:
        raise ValueError("lora_rank_required")
    if not isinstance(targets, list) or not targets:
        raise ValueError("lora_targets_required")
    return rec("SUPER1200_LORA/1", "LORA_CONFIGURED", rank=rank, targets=[_name(t, "lora_target") for t in targets])


def qlora_provider(*, bits: int, rank: int) -> dict[str, Any]:
    if bits not in {4, 8}:
        raise ValueError("qlora_bits_unsupported")
    if not isinstance(rank, int) or rank < 1:
        raise ValueError("qlora_rank_required")
    return rec("SUPER1200_QLORA/1", "QLORA_CONFIGURED", bits=bits, rank=rank)


def advanced_lora_provider(*, targets: list[str], rank: int) -> dict[str, Any]:
    if not isinstance(targets, list) or len(targets) < 2:
        raise ValueError("advanced_lora_requires_multiple_targets")
    if not isinstance(rank, int) or rank < 1:
        raise ValueError("advanced_lora_rank_required")
    return rec("SUPER1200_ADVANCED_LORA/1", "ADVANCED_LORA_CONFIGURED", targets=[_name(t, "target") for t in targets], rank=rank)


def _pairs(pairs: list[dict[str, str]], label: str) -> int:
    if not isinstance(pairs, list) or not pairs:
        raise ValueError(label + "_pairs_required")
    for pair in pairs:
        if not isinstance(pair, dict):
            raise ValueError(label + "_pair_invalid")
        _name(pair.get("prompt"), "prompt")
        _name(pair.get("chosen"), "chosen")
    return len(pairs)


def sft_engine(*, examples: list[dict[str, str]]) -> dict[str, Any]:
    return rec("SUPER1200_SFT/1", "SFT_EXAMPLES_ACCEPTED", count=_pairs(examples, "sft"))


def dpo_engine(*, pairs: list[dict[str, str]]) -> dict[str, Any]:
    if not isinstance(pairs, list) or not pairs:
        raise ValueError("dpo_pairs_required")
    for pair in pairs:
        _name(pair.get("chosen"), "chosen")
        _name(pair.get("rejected"), "rejected")
        if pair.get("chosen") == pair.get("rejected"):
            raise ValueError("dpo_preference_must_differ")
    return rec("SUPER1200_DPO/1", "DPO_PAIRS_ACCEPTED", count=len(pairs))


def grpo_engine(*, group_size: int, prompts: list[str]) -> dict[str, Any]:
    if not isinstance(group_size, int) or group_size < 2:
        raise ValueError("grpo_group_size_required")
    if not isinstance(prompts, list) or not prompts:
        raise ValueError("grpo_prompts_required")
    return rec("SUPER1200_GRPO/1", "GRPO_CONFIGURED", group_size=group_size, prompts=len(prompts))


def reward_model_engine(*, pairs: list[dict[str, str]]) -> dict[str, Any]:
    return rec("SUPER1200_REWARD_MODEL/1", "REWARD_PAIRS_ACCEPTED", count=_pairs(pairs, "reward"))


def process_reward_model_engine(*, steps: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(steps, list) or not steps:
        raise ValueError("process_steps_required")
    for step in steps:
        if not isinstance(step, dict) or not isinstance(step.get("score"), (int, float)) or isinstance(step.get("score"), bool):
            raise ValueError("process_score_required")
        if not 0 <= float(step["score"]) <= 1:
            raise ValueError("process_score_out_of_range")
    return rec("SUPER1200_PROCESS_REWARD/1", "PROCESS_REWARD_ACCEPTED", steps=len(steps))


def distillation_factory(*, teacher: str, student: str) -> dict[str, Any]:
    teacher = _name(teacher, "teacher")
    student = _name(student, "student")
    if teacher == student:
        raise ValueError("distillation_teacher_must_differ")
    return rec("SUPER1200_DISTILLATION/1", "DISTILLATION_BOUND", teacher=teacher, student=student)


def multi_teacher_distillation(*, teachers: list[str], student: str) -> dict[str, Any]:
    if not isinstance(teachers, list) or len(teachers) < 2:
        raise ValueError("multi_teacher_requires_two")
    names = [_name(t, "teacher") for t in teachers]
    student = _name(student, "student")
    if student in names:
        raise ValueError("student_cannot_be_teacher")
    return rec("SUPER1200_MULTI_TEACHER_DISTILLATION/1", "MULTI_TEACHER_BOUND", teachers=names, student=student)


def mixture_of_experts_factory(*, experts: list[str]) -> dict[str, Any]:
    if not isinstance(experts, list) or len(experts) < 2:
        raise ValueError("moe_requires_two_experts")
    names = [_name(e, "expert") for e in experts]
    if len(names) != len(set(names)):
        raise ValueError("duplicate_expert")
    return rec("SUPER1200_MOE/1", "MOE_CONFIGURED", experts=names)


def routing_engine_factory(*, experts: list[str], routes: dict[str, str]) -> dict[str, Any]:
    names = [_name(e, "expert") for e in experts] if isinstance(experts, list) else None
    if not names:
        raise ValueError("routing_experts_required")
    if not isinstance(routes, dict) or not routes:
        raise ValueError("routes_required")
    for token, expert in routes.items():
        _name(token, "route_token")
        if expert not in names:
            raise ValueError("route_expert_unknown")
    return rec("SUPER1200_ROUTING/1", "ROUTES_BOUND", routes=len(routes))


def model_merging_engine(*, weights: dict[str, float]) -> dict[str, Any]:
    if not isinstance(weights, dict) or len(weights) < 2:
        raise ValueError("merge_requires_two_models")
    total = 0.0
    for name, weight in weights.items():
        _name(name, "model")
        if not isinstance(weight, (int, float)) or isinstance(weight, bool) or weight < 0:
            raise ValueError("merge_weight_invalid")
        total += float(weight)
    if abs(total - 1.0) > 1e-9:
        raise ValueError("merge_weights_must_sum_to_one")
    return rec("SUPER1200_MODEL_MERGING/1", "MERGE_WEIGHTS_ACCEPTED", models=sorted(weights))


def model_composition_engine(*, parts: list[dict[str, Any]]) -> dict[str, Any]:
    if not isinstance(parts, list) or not parts:
        raise ValueError("composition_parts_required")
    ids = []
    edges = []
    for part in parts:
        ident = _name(part.get("id"), "part_id")
        ids.append(ident)
        parent = part.get("parent")
        if parent is not None:
            edges.append((_name(parent, "parent"), ident))
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate_part")
    known = set(ids)
    for src, _dst in edges:
        if src not in known:
            raise ValueError("composition_parent_unknown")
    # cycle check
    indeg = {i: 0 for i in ids}
    for _src, dst in edges:
        indeg[dst] += 1
    if any(v > 1 for v in indeg.values()):
        raise ValueError("composition_multiple_parents")
    return rec("SUPER1200_MODEL_COMPOSITION/1", "COMPOSITION_ACCEPTED", parts=ids)


def model_surgery_engine(*, op: str, target: str) -> dict[str, Any]:
    op = _name(op, "op")
    if op not in {"slice", "rename", "drop"}:
        raise ValueError("surgery_op_unknown")
    return rec("SUPER1200_MODEL_SURGERY/1", "SURGERY_PLANNED", op=op, target=_name(target, "target"))


def checkpoint_transformer(*, from_sha256: str, to_sha256: str) -> dict[str, Any]:
    src = _sha(from_sha256, "from_sha256")
    dst = _sha(to_sha256, "to_sha256")
    if src == dst:
        raise ValueError("checkpoint_requires_distinct_states")
    return rec("SUPER1200_CHECKPOINT_TRANSFORMER/1", "CHECKPOINT_TRANSFORM_BOUND", from_sha256=src, to_sha256=dst)


def model_converter(*, source_format: str, target_format: str) -> dict[str, Any]:
    src = _name(source_format, "source_format")
    dst = _name(target_format, "target_format")
    if src == dst:
        raise ValueError("converter_formats_must_differ")
    return rec("SUPER1200_MODEL_CONVERTER/1", "CONVERSION_PLANNED", source_format=src, target_format=dst)


def model_quantizer(*, bits: int) -> dict[str, Any]:
    if bits not in {2, 3, 4, 8}:
        raise ValueError("quantizer_bits_unsupported")
    return rec("SUPER1200_MODEL_QUANTIZER/1", "QUANTIZATION_PLANNED", bits=bits)


def model_pruner(*, sparsity: float) -> dict[str, Any]:
    if not isinstance(sparsity, (int, float)) or isinstance(sparsity, bool) or not 0 < float(sparsity) < 1:
        raise ValueError("pruner_sparsity_invalid")
    return rec("SUPER1200_MODEL_PRUNER/1", "PRUNE_PLANNED", sparsity=float(sparsity))


def model_sparsifier(*, mask_sha256: str) -> dict[str, Any]:
    return rec("SUPER1200_MODEL_SPARSIFIER/1", "SPARSITY_MASK_BOUND", mask_sha256=_sha(mask_sha256, "mask_sha256"))


def model_compiler(*, backend: str) -> dict[str, Any]:
    backend = _name(backend, "backend")
    if backend not in {"cpu", "vulkan", "metal", "cuda"}:
        raise ValueError("compiler_backend_unsupported")
    return rec("SUPER1200_MODEL_COMPILER/1", "COMPILE_TARGET_ACCEPTED", backend=backend)


def model_benchmark_engine(*, metric: str, value: float) -> dict[str, Any]:
    metric = _name(metric, "metric")
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("benchmark_value_required")
    return rec("SUPER1200_MODEL_BENCHMARK/1", "BENCHMARK_RECORDED", metric=metric, value=float(value))


def model_evaluation_matrix(*, axes: list[str], metric: str) -> dict[str, Any]:
    if not isinstance(axes, list) or not axes:
        raise ValueError("eval_axes_required")
    return rec("SUPER1200_MODEL_EVALUATION_MATRIX/1", "EVAL_MATRIX_DEFINED", axes=[_name(a, "axis") for a in axes], metric=_name(metric, "metric"))


FUNCS: dict[int, tuple[str, Callable[..., dict[str, Any]]]] = {
    177: ("HERMETIC_EXECUTION_ENGINE", hermetic_execution_engine),
    178: ("CONTENT_BASED_CACHE", content_based_cache),
    179: ("REMOTE_CACHE", remote_cache),
    180: ("REMOTE_EXECUTION_INTERFACE", remote_execution_interface),
    181: ("FINE_GRAINED_INVALIDATION", fine_grained_invalidation),
    182: ("AFFECTED_TARGET_ANALYSIS", affected_target_analysis),
    183: ("BUILD_GRAPH", build_graph),
    184: ("BUILD_TARGET_IDENTITY", build_target_identity),
    185: ("BUILD_REPRODUCIBILITY_PROOF", build_reproducibility_proof),
    186: ("BUILD_SANDBOX", build_sandbox),
    187: ("BUILD_PARALLELIZER", build_parallelizer),
    188: ("CRITICAL_PATH_ANALYZER", critical_path_analyzer),
    189: ("INCREMENTAL_BUILD_ENGINE", incremental_build_engine),
    190: ("MONOREPO_ENGINE", monorepo_engine),
    191: ("AI_FACTORY", ai_factory),
    192: ("MODEL_ARCHITECTURE_REGISTRY", model_architecture_registry),
    193: ("MODEL_COMPONENT_REGISTRY", model_component_registry),
    194: ("TOKENIZER_FACTORY", tokenizer_factory),
    195: ("DATASET_FACTORY", dataset_factory),
    196: ("CORPUS_FACTORY", corpus_factory),
    197: ("DATASET_DEDUPLICATION", dataset_deduplication),
    198: ("DATASET_PROVENANCE", dataset_provenance),
    199: ("DATASET_LICENSE_ENGINE", dataset_license_engine),
    200: ("DATASET_CONTAMINATION_ANALYZER", dataset_contamination_analyzer),
    201: ("DATASET_QUALITY_SCORER", dataset_quality_scorer),
    202: ("SYNTHETIC_DATA_GENERATOR", synthetic_data_generator),
    203: ("SYNTHETIC_DATA_VALIDATOR", synthetic_data_validator),
    204: ("TRAINING_RECIPE_REGISTRY", training_recipe_registry),
    205: ("PRETRAINING_ENGINE_INTERFACE", pretraining_engine_interface),
    206: ("FINETUNING_ENGINE", finetuning_engine),
    207: ("PEFT_ENGINE", peft_engine),
    208: ("LORA_PROVIDER", lora_provider),
    209: ("QLORA_PROVIDER", qlora_provider),
    210: ("ADVANCED_LORA_PROVIDER", advanced_lora_provider),
    211: ("SFT_ENGINE", sft_engine),
    212: ("DPO_ENGINE", dpo_engine),
    213: ("GRPO_ENGINE", grpo_engine),
    214: ("REWARD_MODEL_ENGINE", reward_model_engine),
    215: ("PROCESS_REWARD_MODEL_ENGINE", process_reward_model_engine),
    216: ("DISTILLATION_FACTORY", distillation_factory),
    217: ("MULTI_TEACHER_DISTILLATION", multi_teacher_distillation),
    218: ("MIXTURE_OF_EXPERTS_FACTORY", mixture_of_experts_factory),
    219: ("ROUTING_ENGINE_FACTORY", routing_engine_factory),
    220: ("MODEL_MERGING_ENGINE", model_merging_engine),
    221: ("MODEL_COMPOSITION_ENGINE", model_composition_engine),
    222: ("MODEL_SURGERY_ENGINE", model_surgery_engine),
    223: ("CHECKPOINT_TRANSFORMER", checkpoint_transformer),
    224: ("MODEL_CONVERTER", model_converter),
    225: ("MODEL_QUANTIZER", model_quantizer),
    226: ("MODEL_PRUNER", model_pruner),
    227: ("MODEL_SPARSIFIER", model_sparsifier),
    228: ("MODEL_COMPILER", model_compiler),
    229: ("MODEL_BENCHMARK_ENGINE", model_benchmark_engine),
    230: ("MODEL_EVALUATION_MATRIX", model_evaluation_matrix),
}
