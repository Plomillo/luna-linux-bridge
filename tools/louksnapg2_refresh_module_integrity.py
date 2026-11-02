#!/usr/bin/env python3
"""Recompute the Docling module tree descriptor after an intentional runtime-only edit."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
DOMAIN = "D05_INTELIGENCIA_DOCUMENTAL"
def atomic_json(path: Path, value: dict) -> None:
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
def refresh(runtime_root: Path) -> dict:
    root = runtime_root.resolve(strict=True)
    sys.path.insert(0, str(root))
    from cajita_task_adapters import ADAPTERS, digest_bytes, digest_file, tree_rows, verify_integrity
    from cajita_tokenizer_materializer import tokenizer_tree_rows
    spec = ADAPTERS[DOMAIN]
    weight = root / spec["weight"]
    if weight.is_symlink() or not weight.is_file():
        raise RuntimeError("DOCLING_WEIGHT_MISSING_OR_UNSAFE")
    observed_bytes, observed_sha = weight.stat().st_size, digest_file(weight)
    if observed_bytes != int(spec["bytes"]) or observed_sha != spec["sha"]:
        raise RuntimeError("DOCLING_WEIGHT_IDENTITY_CHANGED:" + observed_sha)
    module = root / spec["module"]
    if module.is_symlink() or not module.is_dir():
        raise RuntimeError("DOCLING_MODULE_MISSING_OR_UNSAFE")
    descriptor_path = module / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise RuntimeError("DOCLING_MODULE_DESCRIPTOR_MISSING_OR_UNSAFE")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("target_id") != spec["target"]:
        raise RuntimeError("DOCLING_MODULE_TARGET_IDENTITY_MISMATCH")
    rows = tree_rows(module)
    tokenizer_manifest = root / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
    if tokenizer_manifest.is_file():
        rows = tokenizer_tree_rows(module, root, rows)
    tree_sha = digest_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    old = descriptor.get("tree_integrity", {})
    descriptor["tree_integrity"] = {
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
        "file_count_excluding_module_descriptors": len(rows),
        "sha256": tree_sha,
    }
    descriptor["runtime_integrity_refresh"] = {
        "schema": "CAJITA_MODULE_TREE_REFRESH/1.0",
        "source_commit": os.environ.get("GITHUB_SHA", "LOCAL_UNPINNED"),
        "domain_id": DOMAIN,
        "expected_changed_runtime": "docling_30mb_runtime_v1.py",
        "previous_tree_sha256": old.get("sha256"),
        "updated_tree_sha256": tree_sha,
        "weight_identity_preserved": True,
        "weight_sha256": observed_sha,
        "weight_bytes": observed_bytes,
        "source_weights_mutated": False,
        "certification": "NOT_GRANTED",
    }
    atomic_json(descriptor_path, descriptor)
    verified = verify_integrity(root, DOMAIN)
    if verified["module_tree_sha256"] != tree_sha:
        raise RuntimeError("DOCLING_REFRESH_POST_VALIDATION_MISMATCH")
    return {"status":"PASS_DERIVED_DESCRIPTOR_REFRESH","domain_id":DOMAIN,
        "previous_tree_sha256":old.get("sha256"),"updated_tree_sha256":tree_sha,
        "module_bytes":verified["module_bytes"],"module_file_count":verified["module_file_count"],
        "weight_sha256":verified["weight_sha256"],"weight_bytes":verified["weight_bytes"],
        "source_weights_mutated":False,"global_certification":"NOT_GRANTED"}
def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root",type=Path,required=True)
    parser.add_argument("--domain",choices=(DOMAIN,),default=DOMAIN)
    args=parser.parse_args()
    result=refresh(args.runtime_root)
    print(json.dumps(result,sort_keys=True,indent=2))
    return 0
if __name__=="__main__":
    raise SystemExit(main())
