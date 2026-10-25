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


def _externalized_runtime_file_identity(
    runtime: Path, logical_runtime_path: str, repo_root: Path | None, target_id: str
) -> dict:
    """Resolve a missing runtime file only through its exact hash-pinned externalized record."""
    if repo_root is None:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_ROOT_REQUIRED:" + target_id)
    repo = Path(repo_root).resolve()
    placement_path = runtime / "EXTERNALIZED_ASSET_PLACEMENT.json"
    if placement_path.is_symlink() or not placement_path.is_file() or not placement_path.resolve().is_relative_to(runtime):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_PLACEMENT_MISSING_OR_UNSAFE:" + target_id)
    try:
        placement = json.loads(placement_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_PLACEMENT_INVALID:" + target_id) from exc
    assets = placement.get("assets")
    if not isinstance(assets, list):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_ASSET_LIST_INVALID:" + target_id)

    canonical_path = "cajita-luna-runtime/" + _safe_rel(logical_runtime_path).as_posix()
    matches = []
    for asset in assets:
        if not isinstance(asset, dict):
            continue
        meta = asset.get("compact_runtime_container")
        if not isinstance(meta, dict):
            continue
        if meta.get("path") == canonical_path or asset.get("placed_path") == canonical_path:
            matches.append((asset, meta))
    if len(matches) != 1:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_ASSET_BINDING_COUNT:" + target_id + ":" + str(len(matches)))
    asset, meta = matches[0]
    if asset.get("exact_externalized_candidate") is not True:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_ASSET_NOT_REGISTERED:" + target_id)
    if asset.get("placed_path") != canonical_path or meta.get("path") != canonical_path:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_CANONICAL_PATH_MISMATCH:" + target_id)

    expected_sha = meta.get("sha256")
    expected_bytes = meta.get("size_bytes")
    if (not isinstance(expected_sha, str) or len(expected_sha) != 64
        or any(ch not in "0123456789abcdef" for ch in expected_sha)
        or isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or expected_bytes <= 0):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_IDENTITY_INVALID:" + target_id)

    factory_record = asset.get("factory_reconciliation", {})
    optimization = asset.get("optimization", {})
    if not isinstance(factory_record, dict) or not isinstance(optimization, dict):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_PROVENANCE_INVALID:" + target_id)
    declared_paths = [
        asset.get("container_path_outside_runtime"),
        factory_record.get("container_source"),
        optimization.get("optimized_path"),
    ]
    declared_paths = [item for item in declared_paths if item not in (None, "")]
    if not declared_paths or any(not isinstance(item, str) for item in declared_paths):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_PATH_MISSING:" + target_id)
    normalized_paths = {_safe_rel(item).as_posix() for item in declared_paths}
    if len(normalized_paths) != 1:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_PATH_COLLISION:" + target_id)
    source_rel = next(iter(normalized_paths))
    source = repo.joinpath(*PurePosixPath(source_rel).parts)
    if not source.resolve(strict=False).is_relative_to(repo):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_PATH_ESCAPE:" + target_id)
    cursor = repo
    for part in PurePosixPath(source_rel).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_SYMLINK:" + target_id)
    if not source.is_file():
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_MISSING:" + target_id)
    actual_bytes = source.stat().st_size
    actual_sha = _sha(source.read_bytes())
    if actual_bytes != expected_bytes or actual_sha != expected_sha:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_SOURCE_IDENTITY_MISMATCH:" + target_id)
    for label, value in (
        ("container_sha256_verified", factory_record.get("container_sha256_verified")),
        ("optimized_sha256", optimization.get("optimized_sha256")),
    ):
        if value is not None and value != expected_sha:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_DUPLICATE_HASH_MISMATCH:" + target_id + ":" + label)
    for label, value in (
        ("container_bytes_verified", factory_record.get("container_bytes_verified")),
        ("optimized_size_bytes", optimization.get("optimized_size_bytes")),
    ):
        if value is not None and value != expected_bytes:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_EXTERNALIZED_DUPLICATE_SIZE_MISMATCH:" + target_id + ":" + label)
    return {"path": logical_runtime_path, "bytes": actual_bytes, "sha256": actual_sha}


def _registered_runtime_engine_scopes(
    runtime_root: Path, targets: list[dict], repo_root: Path | None = None
) -> dict[str, dict]:
    """Bind target-specific engine smoke adapters without promoting them to full task adapters."""
    runtime = Path(runtime_root).resolve()
    adapter_path = runtime / "cajita_target_adapters.py"
    if adapter_path.is_symlink() or not adapter_path.is_file() or not adapter_path.resolve().is_relative_to(runtime):
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_SOURCE_MISSING_OR_UNSAFE")
    try:
        adapter_source = adapter_path.read_bytes()
        parsed = ast.parse(adapter_source.decode("utf-8"), filename=str(adapter_path))
    except (OSError, UnicodeError, SyntaxError) as exc:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_SOURCE_PARSE_FAILED:" + type(exc).__name__) from exc

    specs = None
    for node in parsed.body:
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "TARGET_ADAPTERS"
            for target in node.targets
        ):
            try:
                specs = ast.literal_eval(node.value)
            except (ValueError, TypeError) as exc:
                raise RuntimeError("RUNTIME_TARGET_ADAPTER_REGISTRY_MUST_BE_LITERAL") from exc
            break
    if not isinstance(specs, dict) or not specs:
        raise RuntimeError("RUNTIME_TARGET_ADAPTER_REGISTRY_MISSING_OR_INVALID")

    targets_by_id = {}
    for target in targets:
        if not isinstance(target, dict) or not isinstance(target.get("id"), str):
            raise RuntimeError("CANONICAL_TARGET_ID_INVALID_DURING_RUNTIME_SCOPE_BINDING")
        if target["id"] in targets_by_id:
            raise RuntimeError("CANONICAL_TARGET_ID_COLLISION_DURING_RUNTIME_SCOPE_BINDING:" + target["id"])
        targets_by_id[target["id"]] = target

    output = {}
    seen_adapter_ids = set()
    required_keys = ("domain_id", "adapter_id", "operation", "module", "entry", "required_files", "engine", "scope")
    for target_id, spec in specs.items():
        if not isinstance(target_id, str) or not isinstance(spec, dict):
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_SPEC_INVALID")
        if any(key not in spec for key in required_keys):
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_SPEC_INCOMPLETE:" + str(target_id))
        for key in ("domain_id", "adapter_id", "operation", "module", "entry", "engine", "scope"):
            if not isinstance(spec[key], str) or not spec[key]:
                raise RuntimeError("RUNTIME_TARGET_ADAPTER_SPEC_FIELD_INVALID:" + target_id + ":" + key)
        if not isinstance(spec["required_files"], list) or not spec["required_files"]:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILES_MISSING:" + target_id)
        adapter_id = spec["adapter_id"]
        if adapter_id in seen_adapter_ids:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_ID_COLLISION:" + adapter_id)
        seen_adapter_ids.add(adapter_id)

        target = targets_by_id.get(target_id)
        if target is None or target.get("domain_id") != spec["domain_id"]:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_CANONICAL_TARGET_MISMATCH:" + target_id)
        module_rel = _safe_rel(spec["module"]).as_posix()
        target_rel = _safe_rel(target.get("path", "")).as_posix()
        if module_rel != target_rel:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_MODULE_PATH_MISMATCH:" + target_id)

        module_root = runtime.joinpath(*PurePosixPath(module_rel).parts)
        if module_root.is_symlink() or not module_root.is_dir() or not module_root.resolve().is_relative_to(runtime):
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_MODULE_ROOT_MISSING_OR_UNSAFE:" + target_id)
        entry_rel = _safe_rel(spec["entry"]).as_posix()
        if entry_rel not in { _safe_rel(item).as_posix() for item in spec["required_files"] }:
            raise RuntimeError("RUNTIME_TARGET_ADAPTER_ENTRY_NOT_HASH_BOUND:" + target_id)

        source_files = []
        seen_paths = set()
        for item in spec["required_files"]:
            file_rel = _safe_rel(item).as_posix()
            if file_rel in seen_paths:
                raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_DUPLICATE:" + target_id)
            seen_paths.add(file_rel)
            file_path = module_root.joinpath(*PurePosixPath(file_rel).parts)
            logical_file = (PurePosixPath(module_rel) / PurePosixPath(file_rel)).as_posix()
            if file_path.is_symlink():
                raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_MISSING_OR_UNSAFE:" + target_id + ":" + file_rel)
            if file_path.is_file():
                if not file_path.resolve().is_relative_to(module_root.resolve()):
                    raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_PATH_ESCAPE:" + target_id + ":" + file_rel)
                data = file_path.read_bytes()
                source_files.append({"path": logical_file, "bytes": len(data), "sha256": _sha(data)})
            elif file_path.exists():
                raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_NOT_REGULAR:" + target_id + ":" + file_rel)
            else:
                # Without a repository staging root, or without an exact
                # externalized identity, missing files retain the original
                # fail-closed required-file result.
                if repo_root is None:
                    raise RuntimeError("RUNTIME_TARGET_ADAPTER_REQUIRED_FILE_MISSING_OR_UNSAFE:" + target_id + ":" + file_rel)
                source_files.append(_externalized_runtime_file_identity(
                    runtime, logical_file, repo_root, target_id
                ))
        output[target_id] = {
            "status": "REGISTERED_RUNTIME_SMOKE_SCOPE_ONLY",
            "target_id": target_id,
            "domain_id": spec["domain_id"],
            "adapter_id": adapter_id,
            "operation": spec["operation"],
            "engine": spec["engine"],
            "module_path": module_rel,
            "entrypoint": (PurePosixPath(module_rel) / PurePosixPath(entry_rel)).as_posix(),
            "adapter_source_path": adapter_path.relative_to(runtime).as_posix(),
            "adapter_source_sha256": _sha(adapter_source),
            "source_files": source_files,
            "execution_scope": spec["scope"],
            "consumer_task_adapter_completion": "NOT_ESTABLISHED",
            "reference_quality_equivalence": "NOT_ESTABLISHED",
            "native_hardware_validation": "REQUIRED",
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
    block_graph_path = multi_dir / "block_engine_binding.json"
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
    expected_multi_engines = ["E03", "E04", "E05", "E06", "E07", "E08", "E09", "E12", "E13", "E14", "E15"]
    multi_engine_ids = list(multi.get("engine_ids", []))
    if multi_engine_ids != expected_multi_engines:
        raise RuntimeError("MULTI_INTERDISCIPLINAR_ENGINE_BINDING_MISMATCH")
    canonical_block_ids = [f"B{i}" for i in range(1, 135)]
    block_graph = {
        "schema": "LOUKSNA_BLOCK_ENGINE_BINDING/1.0",
        "status": "DECLARED_STRUCTURAL_ROUTING_ONLY",
        "scope": "CANONICAL_IDENTIFIER_ROUTING_NOT_SEMANTIC_PROOF",
        "source": {
            "document_path": "Louksna1.md", "document_sha256": doc_sha,
            "protected_architecture_path": "LOUKSNAMEJORADA.md",
            "protected_architecture_sha256": source_sha,
            "protected_architecture_bytes": len(source_bytes),
            "provenance_mode": "EXACT_DOCUMENT_AND_PROTECTED_PREFIX_HASHES"
        },
        "block_inventory": {
            "range": "B1-B134", "count": 134, "ids": canonical_block_ids,
            "mutation_allowed": False
        },
        "target": {
            "id": multi["id"], "domain_id": multi["domain_id"],
            "path": multi["path"], "engine_ids": multi_engine_ids
        },
        "block_routes": [
            {
                "from_block_id": block_id,
                "relation": "routes_to_interdisciplinary_target",
                "to_target_id": multi["id"],
                "source_scope": "CANONICAL_BLOCK_RANGE_DECLARATION_ONLY",
                "provenance_sha256": doc_sha
            } for block_id in canonical_block_ids
        ],
        "engine_routes": [
            {"from_target_id": multi["id"], "relation": "uses_canonical_engine", "to_engine_id": engine_id}
            for engine_id in multi_engine_ids
        ],
        "invariants": {
            "canonical_block_identity_mutation": False,
            "canonical_engine_reassignment": False,
            "synthetic_block_ids": False,
            "semantic_content_reconstructed": False
        },
        "certification": "NOT_GRANTED"
    }
    block_graph_bytes = (json.dumps(block_graph, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    block_graph_sha = _sha(block_graph_bytes)
    binding["block_engine_graph"] = {
        "path_from_runtime_root": block_graph_path.relative_to(runtime).as_posix(),
        "sha256": block_graph_sha, "block_count": 134,
        "state": "DECLARED_STRUCTURAL_ROUTING_ONLY"
    }
    binding["graph_execution"] = "STRUCTURAL_BLOCK_ROUTING_DECLARED_RUNTIME_VERIFICATION_REQUIRED"
    binding["status"] = "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND"
    binding["reader"]["operation"] = "VERIFY_DOCUMENT_SHA256_PREFIX_AND_B1_B134_BLOCK_ENGINE_ROUTES"
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
    if block_graph_path.exists():
        if block_graph_path.is_symlink() or not block_graph_path.is_file():
            raise RuntimeError("BLOCK_ENGINE_GRAPH_PATH_UNSAFE")
        prior_graph = json.loads(block_graph_path.read_text(encoding="utf-8"))
        prior_target = prior_graph.get("target", {})
        prior_inventory = prior_graph.get("block_inventory", {})
        if (
            prior_graph.get("schema") != "LOUKSNA_BLOCK_ENGINE_BINDING/1.0"
            or prior_target.get("id") != multi.get("id")
            or prior_target.get("domain_id") != multi.get("domain_id")
            or prior_target.get("path") != multi.get("path")
            or prior_target.get("engine_ids") != expected_multi_engines
            or prior_inventory.get("range") != "B1-B134"
            or prior_inventory.get("count") != 134
            or prior_inventory.get("ids") != canonical_block_ids
            or prior_inventory.get("mutation_allowed") is not False
        ):
            raise RuntimeError("BLOCK_ENGINE_GRAPH_CANONICAL_IDENTITY_COLLISION")
        block_graph_path.write_bytes(block_graph_bytes)
    else:
        block_graph_path.write_bytes(block_graph_bytes)
    consumer_adapters = _registered_consumer_adapters(runtime, targets)
    runtime_engine_scopes = _registered_runtime_engine_scopes(runtime, targets, repo_root=repo)
    if set(consumer_adapters).intersection(runtime_engine_scopes):
        raise RuntimeError("MODEL_ADAPTER_AND_RUNTIME_SCOPE_TARGET_COLLISION")
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
            "runtime_engine_scope_registration": runtime_engine_scopes.get(target["id"], {
                "status": "NOT_REGISTERED",
                "consumer_task_adapter_completion": "NOT_ESTABLISHED",
                "certification": "NOT_GRANTED"
            }),
            "functional_state": (
                "SYNTHETIC_ADAPTER_REGISTERED_NATIVE_SMOKE_AND_QUALITY_BASELINE_REQUIRED"
                if target["id"] in consumer_adapters
                else ("RUNTIME_ENGINE_SMOKE_SCOPE_ONLY_FULL_TASK_ADAPTER_NOT_ESTABLISHED"
                      if target["id"] in runtime_engine_scopes
                      else "MODULE_REGISTERED_ADAPTER_AND_NATIVE_SMOKE_REQUIRED")
            ),
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
            "runtime_engine_scope_registration": manifest["runtime_engine_scope_registration"],
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
    registry["runtime_engine_scope_registration_summary"] = {
        "canonical_target_count": len(target_modules),
        "runtime_engine_smoke_scope_registered_target_count": len(runtime_engine_scopes),
        "runtime_engine_smoke_scope_target_ids": sorted(runtime_engine_scopes),
        "runtime_engine_smoke_scope_only": True,
        "consumer_task_adapter_completion": "NOT_ESTABLISHED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "native_hardware_validation": "REQUIRED",
        "certification": "NOT_GRANTED"
    }
    registry["axiom_interdisciplinary_binding"] = {
        "path": binding_path.relative_to(runtime).as_posix(), "sha256": _sha(binding_path.read_bytes()),
        "target_id": multi["id"], "protected_architecture_sha256": source_sha,
        "declared_materialized_axiom_count": 11757, "declared_historical_gap_count": 657,
        "block_count": 134, "framework_count": 18, "state": "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND"
    }
    registry["block_engine_graph"] = {
        "path": block_graph_path.relative_to(runtime).as_posix(),
        "sha256": _sha(block_graph_path.read_bytes()), "block_count": 134,
        "target_id": multi["id"], "engine_ids": expected_multi_engines,
        "state": "DECLARED_STRUCTURAL_ROUTING_ONLY", "certification": "NOT_GRANTED"
    }
    registry["certification"] = "NOT_GRANTED"
    registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    routing.setdefault("materialization", {})["canonical_target_module_count"] = len(target_modules)
    routing["materialization"]["axiom_interdisciplinary_binding"] = binding_path.relative_to(runtime).as_posix()
    routing["materialization"]["axiom_interdisciplinary_binding_sha256"] = _sha(binding_path.read_bytes())
    routing["materialization"]["axiom_source_state"] = "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND"
    routing["materialization"]["block_engine_graph"] = {
        "path": block_graph_path.relative_to(runtime).as_posix(),
        "sha256": _sha(block_graph_path.read_bytes()), "block_count": 134,
        "target_id": multi["id"], "engine_ids": expected_multi_engines,
        "state": "DECLARED_STRUCTURAL_ROUTING_ONLY", "certification": "NOT_GRANTED"
    }
    routing["materialization"]["consumer_adapter_registration"] = {
        "synthetic_scope_registered_target_count": len(consumer_adapters),
        "unregistered_target_count": len(target_modules) - len(consumer_adapters),
        "all_21_target_task_adapters": "NOT_ESTABLISHED",
        "native_smoke": "REQUIRED",
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED"
    }
    routing["materialization"]["runtime_engine_scope_registration"] = {
        "runtime_engine_smoke_scope_registered_target_count": len(runtime_engine_scopes),
        "runtime_engine_smoke_scope_target_ids": sorted(runtime_engine_scopes),
        "scope_only_not_consumer_task_adapter": True,
        "reference_quality_equivalence": "NOT_ESTABLISHED",
        "native_hardware_validation": "REQUIRED",
        "certification": "NOT_GRANTED"
    }
    routing_path.write_text(json.dumps(routing, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "target_module_count": len(target_modules), "target_modules": target_modules,
        "binding_path": binding_path.relative_to(runtime).as_posix(),
        "binding_sha256": _sha(binding_path.read_bytes()), "protected_source_sha256": source_sha,
        "companion_document_sha256": doc_sha, "declared_materialized_axioms": 11757,
        "declared_historical_gaps": 657, "block_count": 134, "framework_count": 18,
        "state": "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND",
        "synthetic_scope_registered_target_count": len(consumer_adapters),
        "runtime_engine_smoke_scope_registered_target_count": len(runtime_engine_scopes),
        "runtime_engine_smoke_scope_target_ids": sorted(runtime_engine_scopes),
        "unregistered_target_count": len(target_modules) - len(consumer_adapters),
        "global_certification": "NOT_GRANTED"
    }
