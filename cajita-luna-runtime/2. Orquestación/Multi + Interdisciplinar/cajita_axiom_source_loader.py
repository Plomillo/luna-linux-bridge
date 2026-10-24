#!/usr/bin/env python3
"""Verify the protected architecture prefix consumed by D02_MULTI_INTERDISCIPLINAR."""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def verify_binding(runtime_root: str | Path, companion: str | Path | None = None) -> dict:
    root = Path(runtime_root).resolve()
    binding_path = root / "2. Orquestación" / "Multi + Interdisciplinar" / "axiom_interdisciplinary_binding.json"
    if not root.is_dir() or binding_path.is_symlink() or not binding_path.is_file():
        raise RuntimeError("AXIOM_BINDING_OR_RUNTIME_MISSING")
    binding = json.loads(binding_path.read_text(encoding="utf-8"))
    doc = Path(companion).resolve() if companion else root.parent / "Louksna1.md"
    if doc.is_symlink() or not doc.is_file():
        raise RuntimeError("LOUKSNA1_COMPANION_MISSING")
    data = doc.read_bytes()
    if sha256(data) != binding["companion_artifact"]["sha256"]:
        raise RuntimeError("LOUKSNA1_COMPANION_HASH_MISMATCH")
    n = int(binding["protected_architecture_prefix"]["bytes"])
    if n <= 0 or len(data) < n:
        raise RuntimeError("PROTECTED_PREFIX_TRUNCATED")
    prefix = data[:n]
    if sha256(prefix) != binding["protected_architecture_prefix"]["sha256"]:
        raise RuntimeError("PROTECTED_PREFIX_HASH_MISMATCH")
    return {
        "status": "PASS_SOURCE_PREFIX_VERIFIED",
        "binding_path": str(binding_path),
        "companion_path": str(doc),
        "companion_sha256": sha256(data),
        "protected_prefix_sha256": sha256(prefix),
        "protected_prefix_bytes": n,
        "target": binding["target"],
        "axiom_inventory": binding["axiom_inventory"],
        "block_inventory": binding["block_inventory"],
        "framework_count": binding["framework_count"],
        "semantic_graph_execution": "NOT_PERFORMED_BY_SOURCE_LOADER",
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
