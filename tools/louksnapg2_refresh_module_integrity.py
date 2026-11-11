#!/usr/bin/env python3
"""Recompute source-bound module integrity descriptors after intentional runtime edits.

Only derived integrity metadata is rewritten in the isolated build workspace.
Original weights and canonical task/target identities are verified unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

DOCLING_DOMAIN = "D05_INTELIGENCIA_DOCUMENTAL"
MODEL_DOMAINS = (
    "D01_CEREBRO",
    "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE",
    "D05_INTELIGENCIA_DOCUMENTAL",
    "D06_SISTEMA_INTELIGENTE",
)


def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    os.replace(tmp, path)


def refresh_domain(runtime_root: Path, domain: str) -> dict:
    root = runtime_root.resolve(strict=True)
    sys.path.insert(0, str(root))
    from cajita_task_adapters import ADAPTERS, digest_bytes, digest_file, tree_rows, verify_integrity
    from cajita_tokenizer_materializer import tokenizer_tree_rows

    if domain not in MODEL_DOMAINS or domain not in ADAPTERS:
        raise RuntimeError("MODEL_DOMAIN_NOT_REGISTERED:" + str(domain))
    spec = ADAPTERS[domain]
    weight = root / spec["weight"]
    if weight.is_symlink() or not weight.is_file():
        raise RuntimeError("MODEL_WEIGHT_MISSING_OR_UNSAFE:" + domain)
    observed_bytes, observed_sha = weight.stat().st_size, digest_file(weight)
    if observed_bytes != int(spec["bytes"]) or observed_sha != spec["sha"]:
        raise RuntimeError("MODEL_WEIGHT_IDENTITY_CHANGED:" + domain + ":" + observed_sha)

    module = root / spec["module"]
    if module.is_symlink() or not module.is_dir():
        raise RuntimeError("MODEL_MODULE_MISSING_OR_UNSAFE:" + domain)
    descriptor_path = module / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise RuntimeError("MODEL_MODULE_DESCRIPTOR_MISSING_OR_UNSAFE:" + domain)
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("target_id") != spec["target"]:
        raise RuntimeError("MODEL_MODULE_TARGET_IDENTITY_MISMATCH:" + domain)

    rows = tree_rows(module)
    tokenizer_manifest = root / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
    if tokenizer_manifest.is_file():
        rows = tokenizer_tree_rows(module, root, rows)
    tree_sha = digest_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    old = descriptor.get("tree_integrity", {})
    descriptor["tree_integrity"] = {
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
        "file_count_excluding_module_descriptors": len(rows),
        "sha256": tree_sha,
    }
    descriptor["runtime_integrity_refresh"] = {
        "schema": "CAJITA_MODULE_TREE_REFRESH/1.0",
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNPINNED"),
        "domain_id": domain,
        "previous_tree_sha256": old.get("sha256"),
        "updated_tree_sha256": tree_sha,
        "weight_identity_preserved": True,
        "weight_sha256": observed_sha,
        "weight_bytes": observed_bytes,
        "source_weights_mutated": False,
        "certification": "NOT_GRANTED",
    }
    atomic_json(descriptor_path, descriptor)
    verified = verify_integrity(root, domain)
    if verified["module_tree_sha256"] != tree_sha:
        raise RuntimeError("MODEL_MODULE_REFRESH_POST_VALIDATION_MISMATCH:" + domain)
    return {
        "status": "PASS_DERIVED_DESCRIPTOR_REFRESH",
        "domain_id": domain,
        "previous_tree_sha256": old.get("sha256"),
        "updated_tree_sha256": tree_sha,
        "module_bytes": verified["module_bytes"],
        "module_file_count": verified["module_file_count"],
        "weight_sha256": verified["weight_sha256"],
        "weight_bytes": verified["weight_bytes"],
        "source_weights_mutated": False,
        "global_certification": "NOT_GRANTED",
    }


def refresh(runtime_root: Path) -> dict:
    """Compatibility API retained for callers expecting the historical D05 refresh."""
    return refresh_domain(runtime_root, DOCLING_DOMAIN)


def refresh_all(runtime_root: Path) -> dict:
    rows = [refresh_domain(runtime_root, domain) for domain in MODEL_DOMAINS]
    return {
        "schema": "LOUKSNAPG2_FIVE_MODEL_TREE_REFRESH/1.0",
        "status": "PASS_ALL_FIVE_MODULE_TREES_REFRESHED_AND_VALIDATED",
        "models": rows,
        "source_weights_mutated": False,
        "global_certification": "NOT_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--all-models", action="store_true")
    parser.add_argument("--domain", choices=MODEL_DOMAINS, default=DOCLING_DOMAIN)
    args = parser.parse_args()
    result = refresh_all(args.runtime_root) if args.all_models else refresh_domain(args.runtime_root, args.domain)
    print(json.dumps(result, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
