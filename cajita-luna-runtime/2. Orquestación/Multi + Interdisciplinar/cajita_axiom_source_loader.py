#!/usr/bin/env python3
"""Verify the protected Louksna prefix and the additive B1-B134 routing graph."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path

MULTI_PATH = "2. Orquestación/Multi + Interdisciplinar"
EXPECTED_ENGINES = ["E03", "E04", "E05", "E06", "E07", "E08", "E09", "E12", "E13", "E14", "E15"]
EXPECTED_BLOCK_IDS = [f"B{i}" for i in range(1, 135)]
GRAPH_SCHEMA = "LOUKSNA_BLOCK_ENGINE_BINDING/1.0"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def verify_binding(runtime_root: str | Path, companion: str | Path | None = None) -> dict:
    root = Path(runtime_root).resolve()
    binding_path = root / MULTI_PATH / "axiom_interdisciplinary_binding.json"
    if not root.is_dir() or binding_path.is_symlink() or not binding_path.is_file():
        raise RuntimeError("AXIOM_BINDING_OR_RUNTIME_MISSING")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    doc = Path(companion).resolve() if companion else root.parent / "Louksna1.md"
    if doc.is_symlink() or not doc.is_file():
        raise RuntimeError("LOUKSNA1_COMPANION_MISSING")
    data = doc.read_bytes()
    companion_sha = sha256(data)
    if companion_sha != binding["companion_artifact"]["sha256"]:
        raise RuntimeError("LOUKSNA1_COMPANION_HASH_MISMATCH")
    n = int(binding["protected_architecture_prefix"]["bytes"])
    if n <= 0 or len(data) < n:
        raise RuntimeError("PROTECTED_PREFIX_TRUNCATED")
    prefix = data[:n]
    prefix_sha = sha256(prefix)
    if prefix_sha != binding["protected_architecture_prefix"]["sha256"]:
        raise RuntimeError("PROTECTED_PREFIX_HASH_MISMATCH")
    target = binding.get("target", {})
    if (target.get("id") != "D02_MULTI_INTERDISCIPLINAR"
        or target.get("domain_id") != "D02_ORQUESTACION"
        or target.get("path") != MULTI_PATH
        or target.get("engine_ids") != EXPECTED_ENGINES):
        raise RuntimeError("MULTI_INTERDISCIPLINAR_CANONICAL_ENGINE_BINDING_MISMATCH")
    graph_record = binding.get("block_engine_graph", {})
    expected_graph_rel = MULTI_PATH + "/block_engine_binding.json"
    if graph_record.get("path_from_runtime_root") != expected_graph_rel:
        raise RuntimeError("BLOCK_ENGINE_GRAPH_PATH_BINDING_MISMATCH")
    graph_path = root / expected_graph_rel
    if graph_path.is_symlink() or not graph_path.is_file() or not graph_path.resolve().is_relative_to(root):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_MISSING_OR_UNSAFE")
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
        or source.get("protected_architecture_bytes") != n):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_SOURCE_BINDING_MISMATCH")
    inventory = graph.get("block_inventory", {})
    if (inventory.get("range") != "B1-B134"
        or inventory.get("count") != 134
        or inventory.get("ids") != EXPECTED_BLOCK_IDS
        or inventory.get("mutation_allowed") is not False):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_CANONICAL_RANGE_MISMATCH")
    if graph_record.get("block_count") != 134:
        raise RuntimeError("BLOCK_ENGINE_GRAPH_DECLARED_COUNT_MISMATCH")
    graph_target = graph.get("target", {})
    if (graph_target.get("id") != target["id"]
        or graph_target.get("domain_id") != target["domain_id"]
        or graph_target.get("path") != target["path"]
        or graph_target.get("engine_ids") != EXPECTED_ENGINES):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_TARGET_BINDING_MISMATCH")
    expected_routes = [
        {"from_block_id": block_id, "relation": "routes_to_interdisciplinary_target",
         "to_target_id": target["id"], "source_scope": "CANONICAL_BLOCK_RANGE_DECLARATION_ONLY",
         "provenance_sha256": companion_sha}
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
    if (invariants.get("canonical_block_identity_mutation") is not False
        or invariants.get("canonical_engine_reassignment") is not False
        or invariants.get("synthetic_block_ids") is not False
        or invariants.get("semantic_content_reconstructed") is not False):
        raise RuntimeError("BLOCK_ENGINE_GRAPH_INVARIANT_FAILURE")
    block_graph = {
        "status": "PASS_CANONICAL_B1_B134_ROUTING",
        "path": graph_path.relative_to(root).as_posix(),
        "sha256": graph_sha, "block_count": 134,
        "first_block_id": "B1", "last_block_id": "B134",
        "route_edge_count": 134, "target_id": target["id"],
        "engine_ids": EXPECTED_ENGINES, "engine_route_count": len(expected_engine_routes),
        "scope": "STRUCTURAL_ROUTING_ONLY_NOT_SEMANTIC_PROOF"
    }
    return {
        "status": "PASS_SOURCE_PREFIX_VERIFIED",
        "binding_path": str(binding_path), "companion_path": str(doc),
        "companion_sha256": companion_sha, "protected_prefix_sha256": prefix_sha,
        "protected_prefix_bytes": n, "target": target,
        "axiom_inventory": binding["axiom_inventory"],
        "block_inventory": binding["block_inventory"],
        "block_engine_graph": block_graph, "framework_count": binding["framework_count"],
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
