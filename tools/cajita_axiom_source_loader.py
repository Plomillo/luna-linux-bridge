#!/usr/bin/env python3
"""Verify the protected Louksna prefix and additive canonical B1-B134 routing graph."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MULTI_PATH = "2. Orquestación/Multi + Interdisciplinar"
EXPECTED_ENGINES = ["E03", "E04", "E05", "E06", "E07", "E08", "E09", "E12", "E13", "E14", "E15"]
EXPECTED_BLOCK_IDS = [f"B{i}" for i in range(1, 135)]
GRAPH_SCHEMA = "LOUKSNA_BLOCK_ENGINE_BINDING/1.0"
BINDING_SCHEMA = "LOUKSNA_AXIOM_MULTI_INTERDISCIPLINAR_BINDING/1.0"
ROUTING_SCHEMA = "CAJITA_COMMAND_SUBDOMAIN_ROUTING/1.0"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def _regular_inside(root: Path, path: Path, reason: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(reason)
    resolved = path.resolve()
    if not resolved.is_relative_to(root):
        raise RuntimeError(reason + "_PATH_ESCAPE")
    return resolved

def _companion_candidates(root: Path, companion: str | Path | None) -> list[Path]:
    if companion is not None:
        return [Path(companion).expanduser().resolve()]
    # The distribution can be in the source tree, staged factory tree, or an
    # extracted LOUKSNAPG candidate. Match the declared digest across locations.
    candidates = [
        root / "Louksna1.md",
        root.parent / "Louksna1.md",
        root.parent.parent / "Louksna1.md",
        root.parent.parent.parent / "Louksna1.md",
    ]
    unique = []
    seen = set()
    for candidate in candidates:
        marker = str(candidate.resolve())
        if marker not in seen:
            seen.add(marker)
            unique.append(candidate)
    return unique

def verify_binding(runtime_root: str | Path, companion: str | Path | None = None) -> dict:
    root = Path(runtime_root).resolve()
    if not root.is_dir():
        raise RuntimeError("AXIOM_BINDING_OR_RUNTIME_MISSING")
    multi_dir = root.joinpath(*Path(MULTI_PATH).parts)
    if multi_dir.is_symlink() or not multi_dir.is_dir() or not multi_dir.resolve().is_relative_to(root):
        raise RuntimeError("MULTI_INTERDISCIPLINAR_DIRECTORY_MISSING_OR_UNSAFE")

    binding_path = multi_dir / "axiom_interdisciplinary_binding.json"
    _regular_inside(root, binding_path, "AXIOM_BINDING_OR_RUNTIME_MISSING")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    if binding.get("schema") != BINDING_SCHEMA:
        raise RuntimeError("AXIOM_BINDING_SCHEMA_MISMATCH")
    if binding.get("status") != "SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND":
        raise RuntimeError("AXIOM_BINDING_GRAPH_STATUS_NOT_BOUND")
    if binding.get("graph_execution") != "STRUCTURAL_BLOCK_ROUTING_DECLARED_RUNTIME_VERIFICATION_REQUIRED":
        raise RuntimeError("AXIOM_BINDING_GRAPH_SCOPE_MISMATCH")
    if binding.get("certification") != "NOT_GRANTED":
        raise RuntimeError("AXIOM_BINDING_CERTIFICATION_SCOPE_DRIFT")

    expected_axioms = {
        "range": "AX0001-AX12414",
        "declared_materialized_count": 11757,
        "declared_historical_gap_count": 657,
        "gap_range": "AX0001-AX2414",
        "contiguous_range": "AX2415-AX12414",
        "mutation_allowed": False,
    }
    axiom_inventory = binding.get("axiom_inventory", {})
    for key, value in expected_axioms.items():
        if axiom_inventory.get(key) != value:
            raise RuntimeError("AXIOM_INVENTORY_CANONICAL_DEBT_MISMATCH:" + key)
    if axiom_inventory.get("state") != "PRESERVED_DECLARATION_NOT_INDEPENDENTLY_REPARSED":
        raise RuntimeError("AXIOM_INVENTORY_STATE_MISMATCH")
    if binding.get("block_inventory") != {
        "range": "B1-B134",
        "count": 134,
        "state": "PRESERVED_CANONICAL_RANGE",
        "mutation_allowed": False,
    }:
        raise RuntimeError("AXIOM_BINDING_BLOCK_INVENTORY_MISMATCH")
    if binding.get("framework_count") != 18:
        raise RuntimeError("AXIOM_BINDING_FRAMEWORK_COUNT_MISMATCH")
    reader = binding.get("reader", {})
    if (reader.get("relative_path") != MULTI_PATH + "/cajita_axiom_source_loader.py"
        or reader.get("operation") != "VERIFY_DOCUMENT_SHA256_PREFIX_AND_B1_B134_BLOCK_ENGINE_ROUTES"):
        raise RuntimeError("AXIOM_BINDING_READER_CONTRACT_MISMATCH")

    target = binding.get("target", {})
    if (target.get("id") != "D02_MULTI_INTERDISCIPLINAR"
        or target.get("domain_id") != "D02_ORQUESTACION"
        or target.get("path") != MULTI_PATH
        or target.get("engine_ids") != EXPECTED_ENGINES):
        raise RuntimeError("MULTI_INTERDISCIPLINAR_CANONICAL_ENGINE_BINDING_MISMATCH")

    routing_path = root / "command_subdomain_routing.json"
    _regular_inside(root, routing_path, "CANONICAL_ROUTING_REGISTRY_MISSING_OR_UNSAFE")
    routing = json.loads(routing_path.read_text(encoding="utf-8"))
    if routing.get("schema") != ROUTING_SCHEMA:
        raise RuntimeError("CANONICAL_ROUTING_REGISTRY_SCHEMA_MISMATCH")
    catalog_matches = [
        row for row in routing.get("targets", [])
        if isinstance(row, dict) and row.get("id") == target["id"]
    ]
    if len(catalog_matches) != 1:
        raise RuntimeError("MULTI_INTERDISCIPLINAR_TARGET_CATALOG_MISSING_OR_DUPLICATE")
    catalog_target = catalog_matches[0]
    if (catalog_target.get("domain_id") != target["domain_id"]
        or catalog_target.get("path") != target["path"]
        or catalog_target.get("engine_ids") != EXPECTED_ENGINES
        or catalog_target.get("support_assets") != target.get("support_assets")):
        raise RuntimeError("MULTI_INTERDISCIPLINAR_ROUTING_CATALOG_IDENTITY_MISMATCH")

    companion_meta = binding.get("companion_artifact", {})
    expected_companion_sha = companion_meta.get("sha256")
    expected_companion_bytes = companion_meta.get("bytes")
    declared_companion_path = companion_meta.get("path_from_runtime_root")
    if (not isinstance(expected_companion_sha, str) or len(expected_companion_sha) != 64
        or not isinstance(expected_companion_bytes, int) or isinstance(expected_companion_bytes, bool)
        or expected_companion_bytes <= 0
        or not isinstance(declared_companion_path, str) or not declared_companion_path):
        raise RuntimeError("LOUKSNA1_COMPANION_IDENTITY_MISSING")
    doc = None
    existing_regular = False
    for candidate in _companion_candidates(root, companion):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        existing_regular = True
        data = candidate.read_bytes()
        if len(data) == expected_companion_bytes and sha256(data) == expected_companion_sha:
            doc = candidate.resolve()
            break
    if doc is None:
        if existing_regular:
            raise RuntimeError("LOUKSNA1_COMPANION_HASH_OR_SIZE_MISMATCH")
        raise RuntimeError("LOUKSNA1_COMPANION_MISSING")
    data = doc.read_bytes()
    companion_sha = sha256(data)

    prefix_meta = binding.get("protected_architecture_prefix", {})
    n = prefix_meta.get("bytes")
    if (prefix_meta.get("source_path") != "LOUKSNAMEJORADA.md"
        or prefix_meta.get("mutation_allowed") is not False
        or isinstance(n, bool) or not isinstance(n, int) or n <= 0
        or len(data) < n):
        raise RuntimeError("PROTECTED_PREFIX_DESCRIPTOR_INVALID_OR_TRUNCATED")
    prefix = data[:n]
    prefix_sha = sha256(prefix)
    if prefix_sha != prefix_meta.get("sha256"):
        raise RuntimeError("PROTECTED_PREFIX_HASH_MISMATCH")

    graph_record = binding.get("block_engine_graph", {})
    expected_graph_rel = MULTI_PATH + "/block_engine_binding.json"
    if (graph_record.get("path_from_runtime_root") != expected_graph_rel
        or graph_record.get("state") != "DECLARED_STRUCTURAL_ROUTING_ONLY"
        or graph_record.get("block_count") != 134):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_PATH_OR_DESCRIPTOR_MISMATCH")
    graph_path = root / expected_graph_rel
    _regular_inside(root, graph_path, "BLOCK_ENGINE_GRAPH_MISSING_OR_UNSAFE")
    graph_raw = graph_path.read_bytes()
    graph_sha = sha256(graph_raw)
    if graph_sha != graph_record.get("sha256"):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_SHA256_MISMATCH")
    graph = json.loads(graph_raw.decode("utf-8"))
    if graph.get("schema") != GRAPH_SCHEMA or graph.get("status") != "DECLARED_STRUCTURAL_ROUTING_ONLY":
        raise RuntimeError("BLOCK_ENGINE_GRAPH_SCHEMA_OR_STATUS_MISMATCH")
    if graph.get("scope") != "CANONICAL_IDENTIFIER_ROUTING_NOT_SEMANTIC_PROOF":
        raise RuntimeError("BLOCK_ENGINE_GRAPH_SCOPE_OVERCLAIM")
    source = graph.get("source", {})
    if (source.get("document_path") != "Louksna1.md"
        or source.get("document_sha256") != companion_sha
        or source.get("protected_architecture_path") != "LOUKSNAMEJORADA.md"
        or source.get("protected_architecture_sha256") != prefix_sha
        or source.get("protected_architecture_bytes") != n
        or source.get("provenance_mode") != "EXACT_DOCUMENT_AND_PROTECTED_PREFIX_HASHES"):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_SOURCE_BINDING_MISMATCH")
    inventory = graph.get("block_inventory", {})
    if (inventory.get("range") != "B1-B134"
        or inventory.get("count") != 134
        or inventory.get("ids") != EXPECTED_BLOCK_IDS
        or inventory.get("mutation_allowed") is not False):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_CANONICAL_RANGE_MISMATCH")
    graph_target = graph.get("target", {})
    if (graph_target.get("id") != target["id"]
        or graph_target.get("domain_id") != target["domain_id"]
        or graph_target.get("path") != target["path"]
        or graph_target.get("engine_ids") != EXPECTED_ENGINES):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_TARGET_BINDING_MISMATCH")
    expected_routes = [
        {
            "from_block_id": block_id,
            "relation": "routes_to_interdisciplinary_target",
            "to_target_id": target["id"],
            "source_scope": "CANONICAL_BLOCK_RANGE_DECLARATION_ONLY",
            "provenance_sha256": companion_sha,
        }
        for block_id in EXPECTED_BLOCK_IDS
    ]
    if graph.get("block_routes") != expected_routes:
        raise RuntimeError("BLOCK_ENGINE_GRAPH_ROUTE_SET_MISMATCH")
    expected_engine_routes = [
        {"from_target_id": target["id"], "relation": "uses_canonical_engine", "to_engine_id": engine_id}
        for engine_id in EXPECTED_ENGINES
    ]
    if graph.get("engine_routes") != expected_engine_routes:
        raise RuntimeError("BLOCK_ENGINE_GRAPH_ENGINE_ROUTE_SET_MISMATCH")
    invariants = graph.get("invariants", {})
    expected_invariants = {
        "canonical_block_identity_mutation": False,
        "canonical_engine_reassignment": False,
        "synthetic_block_ids": False,
        "semantic_content_reconstructed": False,
    }
    if any(invariants.get(key) is not value for key, value in expected_invariants.items()):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_INVARIANT_FAILURE")
    if graph.get("certification") != "NOT_GRANTED":
        raise RuntimeError("BLOCK_ENGINE_GRAPH_CERTIFICATION_SCOPE_DRIFT")

    block_graph = {
        "status": "PASS_CANONICAL_B1_B134_ROUTING",
        "path": graph_path.relative_to(root).as_posix(),
        "sha256": graph_sha,
        "block_count": 134,
        "first_block_id": "B1",
        "last_block_id": "B134",
        "route_edge_count": len(expected_routes),
        "target_id": target["id"],
        "engine_ids": EXPECTED_ENGINES,
        "engine_route_count": len(expected_engine_routes),
        "scope": "STRUCTURAL_ROUTING_ONLY_NOT_SEMANTIC_PROOF",
    }
    return {
        "status": "PASS_SOURCE_PREFIX_VERIFIED",
        "binding_path": str(binding_path),
        "companion_path": str(doc),
        "companion_sha256": companion_sha,
        "protected_prefix_sha256": prefix_sha,
        "protected_prefix_bytes": n,
        "target": target,
        "axiom_inventory": axiom_inventory,
        "block_inventory": binding["block_inventory"],
        "block_engine_graph": block_graph,
        "framework_count": binding["framework_count"],
        "semantic_graph_execution": "PASS_STRUCTURAL_BLOCK_ROUTING_ONLY",
        "certification": "NOT_GRANTED",
    }

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--runtime-root", required=True)
    p.add_argument("--companion")
    args = p.parse_args()
    try:
        print(json.dumps(verify_binding(args.runtime_root, args.companion), ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)[:300]}))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
