#!/usr/bin/env python3
"""Rebuild only stale CAJITA_MODULE tree-integrity metadata from exact local bytes.

Model payloads, tokenizer sources, compression metadata, manifests, and runtime code
are read-only. Only the selected module descriptor's derived tree_integrity object
may be replaced. Use this after exact Git/LFS materialization from an immutable commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

MODEL_DOMAINS = (
    "D01_CEREBRO",
    "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE",
    "D05_INTELIGENCIA_DOCUMENTAL",
    "D06_SISTEMA_INTELIGENTE",
)

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()

def canonical_tree_integrity(rows: list[dict]) -> dict:
    normalized = []
    seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("MODULE_TREE_ROW_NOT_OBJECT")
        rel = row.get("path")
        size = row.get("bytes")
        digest = row.get("sha256")
        if not isinstance(rel, str) or not rel or rel in seen:
            raise ValueError("MODULE_TREE_PATH_INVALID_OR_DUPLICATE")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0:
            raise ValueError("MODULE_TREE_SIZE_INVALID:" + rel)
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("MODULE_TREE_SHA256_INVALID:" + rel)
        seen.add(rel)
        normalized.append({"path": rel, "bytes": size, "sha256": digest})
    normalized.sort(key=lambda item: item["path"].encode("utf-8"))
    encoded = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return {
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "file_count_excluding_module_descriptors": len(normalized),
        "bytes_excluding_module_descriptors": sum(item["bytes"] for item in normalized),
    }

def write_json(path: Path, data: dict) -> None:
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    path.write_text(payload, encoding="utf-8")

def reconcile(runtime_root: Path, write: bool) -> dict:
    runtime_root = runtime_root.resolve(strict=True)
    if not runtime_root.is_dir() or runtime_root.is_symlink():
        raise RuntimeError("RUNTIME_ROOT_NOT_REGULAR_DIRECTORY")
    import sys
    sys.path.insert(0, str(runtime_root))
    from cajita_task_adapters import ADAPTERS, MANIFEST_SHA, verify_integrity, tree_rows
    from cajita_tokenizer_materializer import (
        MANIFEST_NAME as TOKENIZER_MANIFEST_NAME,
        tokenizer_tree_rows,
    )

    manifest_path = runtime_root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("WEIGHT_MANIFEST_MISSING_OR_UNSAFE")
    manifest_sha_before = sha256_file(manifest_path)
    if manifest_sha_before != MANIFEST_SHA:
        raise RuntimeError("WEIGHT_MANIFEST_SHA256_MISMATCH")
    manifest_bytes_before = manifest_path.stat().st_size
    model_rows = []
    updated_paths = []
    blockers = []

    for domain in MODEL_DOMAINS:
        spec = ADAPTERS.get(domain)
        if not isinstance(spec, dict):
            blockers.append("MODEL_DOMAIN_NOT_REGISTERED:" + domain)
            continue
        weight = runtime_root / spec["weight"]
        if weight.is_symlink() or not weight.is_file():
            blockers.append("MODEL_WEIGHT_MISSING_OR_UNSAFE:" + domain)
            continue
        observed_weight_bytes = weight.stat().st_size
        observed_weight_sha = sha256_file(weight)
        if observed_weight_bytes != spec["bytes"] or observed_weight_sha != spec["sha"]:
            blockers.append("MODEL_WEIGHT_IDENTITY_MISMATCH:" + domain)
            continue

        entries = [
            row for row in json.loads(manifest_path.read_text(encoding="utf-8")).get("artifacts", [])
            if row.get("path") == spec["weight"]
        ]
        if len(entries) != 1 or entries[0].get("bytes") != observed_weight_bytes or entries[0].get("sha256") != observed_weight_sha:
            blockers.append("WEIGHT_MANIFEST_ENTRY_MISMATCH:" + domain)
            continue

        module_root = runtime_root / spec["module"]
        descriptor_path = module_root / "CAJITA_MODULE.json"
        if module_root.is_symlink() or not module_root.is_dir() or descriptor_path.is_symlink() or not descriptor_path.is_file():
            blockers.append("MODULE_DESCRIPTOR_MISSING_OR_UNSAFE:" + domain)
            continue
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        if descriptor.get("domain_id") != domain or descriptor.get("target_id") != spec["target"]:
            blockers.append("MODULE_TARGET_IDENTITY_MISMATCH:" + domain)
            continue

        rows = tree_rows(module_root)
        tokenizer_manifest = runtime_root / TOKENIZER_MANIFEST_NAME
        if tokenizer_manifest.is_symlink() or not tokenizer_manifest.is_file():
            blockers.append("TOKENIZER_MANIFEST_MISSING_OR_UNSAFE")
            continue
        rows = tokenizer_tree_rows(module_root, runtime_root, rows)
        observed_tree = canonical_tree_integrity(rows)
        original_tree = descriptor.get("tree_integrity", {})
        changed = original_tree != observed_tree

        if write and changed:
            descriptor["tree_integrity"] = observed_tree
            write_json(descriptor_path, descriptor)
            updated_paths.append(descriptor_path.relative_to(runtime_root).as_posix())

        try:
            integrity = verify_integrity(runtime_root, domain) if (write or not changed) else None
        except Exception as exc:
            blockers.append("POST_RECONCILIATION_INTEGRITY_FAILED:" + domain + ":" + type(exc).__name__ + ":" + str(exc)[:250])
            integrity = None

        model_rows.append({
            "domain_id": domain,
            "module_path": spec["module"],
            "descriptor_path": descriptor_path.relative_to(runtime_root).as_posix(),
            "original_tree_integrity": original_tree,
            "observed_tree_integrity": observed_tree,
            "descriptor_changed": changed,
            "write_applied": bool(write and changed),
            "weight_path": spec["weight"],
            "weight_bytes": observed_weight_bytes,
            "weight_sha256": observed_weight_sha,
            "post_validation": "PASS" if integrity else ("PENDING_WRITE_REQUIRED" if changed and not write else "FAIL"),
        })

    manifest_sha_after = sha256_file(manifest_path)
    manifest_bytes_after = manifest_path.stat().st_size
    if manifest_sha_after != manifest_sha_before or manifest_bytes_after != manifest_bytes_before:
        blockers.append("WEIGHT_MANIFEST_MUTATED")
    report_status = "PASS_RECONCILED_MODULE_INTEGRITY" if not blockers else "HOLD_MODULE_INTEGRITY_RECONCILIATION"
    if not write and any(row["descriptor_changed"] for row in model_rows):
        report_status = "RECONCILIATION_REQUIRED"
    return {
        "schema": "CAJITA_MODULE_INTEGRITY_RECONCILIATION/1.0",
        "status": report_status,
        "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
        "runtime_root": str(runtime_root),
        "write_mode": write,
        "model_domain_count": len(model_rows),
        "updated_descriptor_paths": sorted(updated_paths),
        "models": model_rows,
        "weight_manifest": {
            "path": manifest_path.relative_to(runtime_root).as_posix(),
            "sha256_before": manifest_sha_before,
            "sha256_after": manifest_sha_after,
            "bytes_before": manifest_bytes_before,
            "bytes_after": manifest_bytes_after,
            "mutated": manifest_sha_before != manifest_sha_after or manifest_bytes_before != manifest_bytes_after,
        },
        "model_weights_mutated": False,
        "model_payload_downloaded": False,
        "tokenizer_source_mutated": False,
        "blockers": blockers,
        "certification": "NOT_GRANTED_BY_MODULE_INTEGRITY_RECONCILIATION",
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--write", action="store_true", help="replace only derived tree_integrity fields in module descriptors")
    args = parser.parse_args(argv)
    try:
        report = reconcile(args.runtime_root, args.write)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        write_json(args.output, report)
        print(json.dumps({
            "status": report["status"],
            "model_domain_count": report["model_domain_count"],
            "updated_descriptor_paths": report["updated_descriptor_paths"],
            "weight_manifest_mutated": report["weight_manifest"]["mutated"],
            "model_weights_mutated": report["model_weights_mutated"],
            "tokenizer_source_mutated": report["tokenizer_source_mutated"],
            "blockers": report["blockers"],
            "output": str(args.output),
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if report["status"] == "PASS_RECONCILED_MODULE_INTEGRITY" else 2
    except Exception as exc:
        print(json.dumps({
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc)[:1000],
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
