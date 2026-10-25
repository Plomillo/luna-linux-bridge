from __future__ import annotations
import ast
import hashlib
import json
import shutil
from pathlib import Path, PurePosixPath


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _safe_rel(value: str) -> PurePosixPath:
    p = PurePosixPath(value.replace("\\", "/"))
    if not value or p.is_absolute() or any(part in {"..", ""} for part in p.parts):
        raise RuntimeError("TARGET_MODULE_PATH_INVALID:" + value[:200])
    return p


def _rows(root: Path, runtime_root: Path) -> list[dict]:
    rows = []
    for base, dirs, files in __import__("os").walk(root, topdown=True, followlinks=False):
        bp = Path(base)
        dirs[:] = sorted(d for d in dirs if not (bp / d).is_symlink())
        for name in sorted(files):
            path = bp / name
            if path.is_symlink() or not path.is_file():
                raise RuntimeError("TARGET_MODULE_NON_REGULAR_ENTRY:" + str(path))
            if name == "CAJITA_MODULE.json":
                continue
            rows.append({"path": path.relative_to(root).as_posix(), "bytes": path.stat().st_size, "sha256": _sha(path.read_bytes())})
    rows = sorted(rows, key=lambda row: row["path"].encode("utf-8"))

    # Target descriptors and G23 must hash the same logical tree. A packed
    # tokenizer.json.gz is storage, not the logical module file; replace it in
    # the canonical row set with the byte-exact source tokenizer.json identity
    # registered in CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json.
    runtime = Path(runtime_root).resolve()
    tokenizer_manifest = runtime / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
    if tokenizer_manifest.is_symlink():
        raise RuntimeError("TARGET_MODULE_TOKENIZER_MANIFEST_SYMLINK")
    if tokenizer_manifest.is_file():
        try:
            from cajita_tokenizer_materializer import tokenizer_tree_rows, TokenizerMaterializationError
            rows = tokenizer_tree_rows(root, runtime, rows)
        except TokenizerMaterializationError as exc:
            raise RuntimeError("TARGET_MODULE_TOKENIZER_LOGICAL_TREE_INVALID:" + str(exc)) from exc
    return rows


def _registered_consumer_adapters(runtime_root: Path, targets: list[dict]) -> dict[str, dict]:
    """Read actual adapter declarations and bind only verifiable target adapters.

    Registration here is not certification: the scope remains synthetic-only
    until native execution and reference-quality equivalence have separate evidence.
    """
    runtime = Path(runtime_root).resolve()
    adapter_path = runtime / "cajita_task_adapters.py"
    weights_path = runtime / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    for path, code in ((adapter_path, "TASK_ADAPTER_SOURCE"), (weights_path, "TASK_ADAPTER_WEIGHT_MANIFEST")):
        if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(runtime):
            raise RuntimeError(code + "_MISSING_OR_UNSAFE")
    try:
        adapter_source = adapter_path.read_bytes()
        parsed = ast.parse(adapter_source.decode("utf-8"), filename=str(adapter_path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise RuntimeError("TASK_ADAPTER_SOURCE_PARSE_FAILED:" + type(exc).__name__) from exc

    literals = {}
    for node in parsed.body:
        if isinstance(node, ast.Assign):
            names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            if any(name in {"ADAPTERS", "MANIFEST_SHA", "CANDIDATE_ID"} for name in names):
                try:
                    value = ast.literal_eval(node.value)
                except (ValueError, TypeError) as exc:
                    raise RuntimeError("TASK_ADAPTER_REGISTRY_MUST_BE_LITERAL") from exc
                for name in names:
                    if name in {"ADAPTERS", "MANIFEST_SHA", "CANDIDATE_ID"}:
                        if name in literals:
                            raise RuntimeError("TASK_ADAPTER_LITERAL_DUPLICATE:" + name)
                        literals[name] = value
    adapter_rows = literals.get("ADAPTERS")
    manifest_sha = literals.get("MANIFEST_SHA")
    candidate_id = literals.get("CANDIDATE_ID")
    if not isinstance(adapter_rows, dict) or not adapter_rows:
        raise RuntimeError("TASK_ADAPTER_REGISTRY_MISSING_OR_INVALID")
    if not isinstance(manifest_sha, str) or len(manifest_sha) != 64 or any(ch not in "0123456789abcdef" for ch in manifest_sha):
        raise RuntimeError("TASK_ADAPTER_WEIGHT_MANIFEST_PIN_INVALID")
    if not isinstance(candidate_id, str) or not candidate_id:
        raise RuntimeError("TASK_ADAPTER_CANDIDATE_ID_MISSING")
    weight_manifest_raw = weights_path.read_bytes()
    if _sha(weight_manifest_raw) != manifest_sha:
        raise RuntimeError("TASK_ADAPTER_WEIGHT_MANIFEST_HASH_MISMATCH")
    try:
        weight_manifest = json.loads(weight_manifest_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("TASK_ADAPTER_WEIGHT_MANIFEST_INVALID_JSON") from exc
    if weight_manifest.get("candidate_id") != candidate_id or not isinstance(weight_manifest.get("artifacts"), list):
        raise RuntimeError("TASK_ADAPTER_WEIGHT_MANIFEST_CANDIDATE_MISMATCH")

    targets_by_id = {}
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RuntimeError("CANONICAL_TARGET_ID_INVALID_DURING_ADAPTER_BINDING")
        if target["id"] in targets_by_id:
            raise RuntimeError("CANONICAL_TARGET_ID_COLLISION_DURING_ADAPTER_BINDING:" + target["id"])
        targets_by_id[target["id"]] = target

    output = {}
    seen_adapter_ids = set()
    seen_target_ids = set()
    artifacts = weight_manifest["artifacts"]
    for domain_id, spec in adapter_rows.items():
        if not isinstance(domain_id, str) or not isinstance(spec, dict):
            raise RuntimeError("TASK_ADAPTER_SPEC_INVALID")
        required = ("target", "id", "op", "entry", "module", "weight", "sha", "bytes")
        if any(key not in spec for key in required):
            raise RuntimeError("TASK_ADAPTER_SPEC_INCOMPLETE:" + domain_id)
        if any(not isinstance(spec[key], str) or not spec[key] for key in required if key != "bytes"):
            raise RuntimeError("TASK_ADAPTER_SPEC_STRING_INVALID:" + domain_id)
        if isinstance(spec["bytes"], bool) or not isinstance(spec["bytes"], int) or spec["bytes"] < 1:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_SIZE_INVALID:" + domain_id)
        target_id = spec["target"]
        adapter_id = spec["id"]
        if target_id in seen_target_ids or adapter_id in seen_adapter_ids:
            raise RuntimeError("TASK_ADAPTER_TARGET_OR_ID_COLLISION:" + domain_id)
        seen_target_ids.add(target_id)
        seen_adapter_ids.add(adapter_id)
        target = targets_by_id.get(target_id)
        if target is None or target.get("domain_id") != domain_id:
            raise RuntimeError("TASK_ADAPTER_CANONICAL_TARGET_MISMATCH:" + domain_id + ":" + target_id)
        module_rel = _safe_rel(spec["module"]).as_posix()
        target_rel = _safe_rel(target.get("path", "")).as_posix()
        if module_rel != target_rel:
            raise RuntimeError("TASK_ADAPTER_MODULE_PATH_MISMATCH:" + domain_id)
        entry_rel = _safe_rel(spec["entry"]).as_posix()
        entry_path = runtime.joinpath(*PurePosixPath(entry_rel).parts)
        if entry_path.is_symlink() or not entry_path.is_file() or not entry_path.resolve().is_relative_to(runtime):
            raise RuntimeError("TASK_ADAPTER_ENTRYPOINT_MISSING_OR_UNSAFE:" + adapter_id)
        weight_rel = _safe_rel(spec["weight"]).as_posix()
        weight_rows = [row for row in artifacts if isinstance(row, dict) and row.get("path") == weight_rel]
        if len(weight_rows) != 1:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_MANIFEST_ENTRY_COUNT:" + domain_id)
        weight_row = weight_rows[0]
        if weight_row.get("sha256") != spec["sha"] or weight_row.get("bytes") != spec["bytes"]:
            raise RuntimeError("TASK_ADAPTER_WEIGHT_PIN_MISMATCH:" + domain_id)

        output[target_id] = {
            "status": "REGISTERED_SYNTHETIC_SCOPE_ONLY",
            "domain_id": domain_id,
            "adapter_id": adapter_id,
            "operation": spec["op"],
            "entrypoint": entry_rel,
            "adapter_source_sha256": _sha(adapter_source),
            "weight_manifest_sha256": manifest_sha,
            "weight_path": weight_rel,
            "weight_sha256": spec["sha"],
            "weight_bytes": spec["bytes"],
            "test_scope": "SYNTHETIC_FIXTURES_ONLY",
            "native_smoke": "REQUIRED",
            "reference_quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        }
    return output


def register_architecture_binding(repo_root: str | Path, runtime_root: str | Path, document_path: str | Path) -> dict:
    repo = Path(repo_root).resolve()
    runtime = Path(runtime_root).resolve()
    source = repo / "LOUKSNAMEJORADA.md"
    doc = Path(document_path).resolve()
    if source.is_symlink() or not source.is_file() or doc.is_symlink() or not doc.is_file():
        raise RuntimeError("PROTECTED_ARCHITECTURE_OR_LOUKSNA1_MISSING")
    source_bytes = source.read_bytes()
    doc_bytes = doc.read_bytes()
    source_sha = _sha(source_bytes)
    doc_sha = _sha(doc_bytes)
    routing_path = runtime / "command_subdomain_routing.json"
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    targets = routing.get("targets", [])
    multi = next((target for target in targets if target.get("id") == "D02_MULTI_INTERDISCIPLINAR"), None)
    if not multi:
        raise RuntimeError("MULTI_INTERDISCIPLINAR_TARGET_MISSING")
    multi_dir = runtime.joinpath(*_safe_rel(multi["path"]).parts)
    if not multi_dir.is_dir() or multi_dir.is_symlink():
        raise RuntimeError("MULTI_INTERDISCIPLINAR_DIRECTORY_MISSING")
    loader_source = repo / "tools" / "cajita_axiom_source_loader.py"
    if loader_source.is_symlink() or not loader_source.is_file():
        raise RuntimeError("AXIOM_SOURCE_LOADER_SOURCE_MISSING")
    loader_dest = multi_dir / "cajita_axiom_source_loader.py"
    binding_path = multi_dir / "axiom_interdisciplinary_binding.json"
    loader_source_bytes = loader_source.read_bytes()
    binding = {
        "schema": "LOUKSNA_AXIOM_MULTI_INTERDISCIPLINAR_BINDING/1.0",
        "status": "SOURCE_BOUND_GRAPH_EXECUTION_PENDING",
        "companion_artifact": {"path_from_runtime_root": "../Louksna1.md", "bytes": len(doc_bytes), "sha256": doc_sha},
        "protected_architecture_prefix": {"source_path": "LOUKSNAMEJORADA.md", "bytes": len(source_bytes), "sha256": source_sha, "mutation_allowed": False},
        "axiom_inventory": {
            "range": "AX0001-AX12414",
            "declared_materialized_count": 11757,
            "declared_historical_gap_count": 657,
            "gap_range": "AX0001-AX2414",
            "contiguous_range": "AX2415-AX12414",
            "state": "PRESERVED_DECLARATION_NOT_INDEPENDENTLY_REPARSED",
            "mutation_allowed": False
        },
        "block_inventory": {"range": "B1-B134", "count": 134, "state": "PRESERVED_CANONICAL_RANGE", "mutation_allowed": False},
        "framework_count": 18,
        "target": {"id": multi["id"], "domain_id": multi["domain_id"], "path": multi["path"], "engine_ids": multi.get("engine_ids", []), "support_assets": multi.get("support_assets", [])},
        "reader": {"relative_path": loader_dest.relative_to(runtime).as_posix(), "operation": "VERIFY_DOCUMENT_SHA256_AND_BYTE_EXACT_PROTECTED_PREFIX"},
        "graph_execution": "NOT_PROVEN_BY_SOURCE_BINDING",
        "certification": "NOT_GRANTED"
    }
    binding_bytes = (json.dumps(binding, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    if loader_dest.exists():
        if loader_dest.is_symlink() or loader_dest.read_bytes() != loader_source_bytes:
            raise RuntimeError("AXIOM_SOURCE_LOADER_CONTENT_COLLISION")
    else:
        shutil.copy2(loader_source, loader_dest)
    if binding_path.exists():
        if binding_path.is_symlink():
            raise RuntimeError("AXIOM_BINDING_SYMLINK")
        prior = json.loads(binding_path.read_text(encoding="utf-8"))
        prior_prefix = prior.get("protected_architecture_prefix", {})
        prior_target = prior.get("target", {})
        if (prior.get("schema") != "LOUKSNA_AXIOM_MULTI_INTERDISCIPLINAR_BINDING/1.0"
            or prior_prefix.get("sha256") != source_sha
            or prior_prefix.get("bytes") != len(source_bytes)
            or prior_prefix.get("mutation_allowed") is not False
            or prior_target.get("id") != multi.get("id")
            or prior_target.get("domain_id") != multi.get("domain_id")
            or prior_target.get("path") != multi.get("path")):
            raise RuntimeError("AXIOM_BINDING_CANONICAL_IDENTITY_COLLISION")
        # Rebuild the derived companion-document digest only after re-verifying
        # the immutable architecture bytes and canonical target identity above.
        binding_path.write_bytes(binding_bytes)
    else:
        binding_path.write_bytes(binding_bytes)
    consumer_adapters = _registered_consumer_adapters(runtime, targets)
    target_modules = []
    for target in targets:
        relative = _safe_rel(target["path"])
        directory = runtime.joinpath(*relative.parts)
        if not directory.is_dir() or directory.is_symlink():
            raise RuntimeError("CANONICAL_TARGET_DIRECTORY_MISSING:" + target["id"])
        manifest_path = directory / "CAJITA_MODULE.json"
        rows = _rows(directory, runtime)
        manifest = {
            "schema": "CAJITA_CANONICAL_TARGET_MODULE/1.0",
            "target_id": target["id"],
            "domain_id": target["domain_id"],
            "target_kind": target.get("kind"),
            "target_name": target.get("name"),
            "relative_path": target["path"],
            "engine_ids": target.get("engine_ids", []),
            "source_identity": {"path": "Louksna1.md", "protected_prefix_sha256": source_sha, "protected_prefix_bytes": len(source_bytes), "companion_sha256": doc_sha},
            "tree_integrity": {"file_count_excluding_module_descriptors": len(rows), "bytes_excluding_module_descriptors": sum(row["bytes"] for row in rows), "sha256": _sha(_canonical(rows))},
            "consumer_adapter": consumer_adapters[target["id"]]["adapter_id"] if target["id"] in consumer_adapters else "NOT_REGISTERED_FOR_ALL_TASKS",
            "consumer_adapter_registration": consumer_adapters.get(target["id"], {
                "status": "NOT_REGISTERED",
                "native_smoke": "REQUIRED",
                "reference_quality_equivalence": "NOT_ESTABLISHED",
                "certification": "NOT_GRANTED"
            }),
            "functional_state": "SYNTHETIC_ADAPTER_REGISTERED_NATIVE_SMOKE_AND_QUALITY_BASELINE_REQUIRED" if target["id"] in consumer_adapters else "MODULE_REGISTERED_ADAPTER_AND_NATIVE_SMOKE_REQUIRED",
            "lifecycle_state": "MATERIALIZED_OR_SOURCE_DIRECTORY_REGISTERED",
            "certification": "NOT_GRANTED"
        }
        manifest_bytes = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
        if manifest_path.exists():
            if manifest_path.is_symlink():
                raise RuntimeError("CANONICAL_TARGET_MODULE_MANIFEST_SYMLINK:" + target["id"])
            prior = json.loads(manifest_path.read_text(encoding="utf-8"))
            prior_source = prior.get("source_identity", {})
            if (prior.get("schema") != "CAJITA_CANONICAL_TARGET_MODULE/1.0"
                or prior.get("target_id") != target["id"]
                or prior_source.get("path") != "Louksna1.md"
                or prior_source.get("protected_prefix_sha256") != source_sha
                or prior_source.get("protected_prefix_bytes") != len(source_bytes)
                or not isinstance(prior_source.get("companion_sha256"), str)
                or len(prior_source.get("companion_sha256", "")) != 64):
                raise RuntimeError("CANONICAL_TARGET_MODULE_IDENTITY_COLLISION:" + target["id"])
            manifest_path.write_bytes(manifest_bytes)
        else:
            manifest_path.write_bytes(manifest_bytes)
        target_modules.append({
            "target_id": target["id"], "domain_id": target["domain_id"], "path": target["path"],
            "manifest": manifest_path.relative_to(runtime).as_posix(), "manifest_sha256": _sha(manifest_path.read_bytes()),
            "tree_sha256": manifest["tree_integrity"]["sha256"], "engine_ids": target.get("engine_ids", []),
            "consumer_adapter": consumer_adapters[target["id"]]["adapter_id"] if target["id"] in consumer_adapters else "NOT_REGISTERED_FOR_ALL_TASKS",
            "consumer_adapter_registration": manifest["consumer_adapter_registration"],
            "certification": "NOT_GRANTED"
        })
    registry_path = runtime / "module_registry.json"
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    registry["canonical_target_module_count"] = len(target_modules)
    registry["target_modules"] = target_modules
    registry["consumer_adapter_registration_summary"] = {
        "canonical_target_count": len(target_modules),
        "synthetic_scope_registered_target_count": len(consumer_adapters),
        "unregistered_target_count": len(target_modules) - len(consumer_adapters),
        "all_21_target_task_adapters": "NOT_ESTABLISHED",
        "synthetic_execution_only": True,
        "native_smoke": "REQUIRED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED"
    }
    registry["axiom_interdisciplinary_binding"] = {
        "path": binding_path.relative_to(runtime).as_posix(), "sha256": _sha(binding_path.read_bytes()),
        "target_id": multi["id"], "protected_architecture_sha256": source_sha,
        "declared_materialized_axiom_count": 11757, "declared_historical_gap_count": 657,
        "block_count": 134, "framework_count": 18, "state": "SOURCE_BOUND_GRAPH_EXECUTION_PENDING"
    }
    registry["certification"] = "NOT_GRANTED"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    routing.setdefault("materialization", {})["canonical_target_module_count"] = len(target_modules)
    routing["materialization"]["axiom_interdisciplinary_binding"] = binding_path.relative_to(runtime).as_posix()
    routing["materialization"]["axiom_interdisciplinary_binding_sha256"] = _sha(binding_path.read_bytes())
    routing["materialization"]["axiom_source_state"] = "SOURCE_BOUND_GRAPH_EXECUTION_PENDING"
    routing["materialization"]["consumer_adapter_registration"] = {
        "synthetic_scope_registered_target_count": len(consumer_adapters),
        "unregistered_target_count": len(target_modules) - len(consumer_adapters),
        "all_21_target_task_adapters": "NOT_ESTABLISHED",
        "native_smoke": "REQUIRED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED"
    }
    routing_path.write_text(json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "target_module_count": len(target_modules), "target_modules": target_modules,
        "binding_path": binding_path.relative_to(runtime).as_posix(),
        "binding_sha256": _sha(binding_path.read_bytes()), "protected_source_sha256": source_sha,
        "companion_document_sha256": doc_sha, "declared_materialized_axioms": 11757,
        "declared_historical_gaps": 657, "block_count": 134, "framework_count": 18,
        "state": "SOURCE_BOUND_GRAPH_EXECUTION_PENDING",
        "synthetic_scope_registered_target_count": len(consumer_adapters),
        "unregistered_target_count": len(target_modules) - len(consumer_adapters),
        "global_certification": "NOT_GRANTED"
    }
