#!/usr/bin/env python3
"""Record identity evidence for existing compact Cajita weights without downloading models."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

DOMAIN_BINDINGS = {
    "D01_CEREBRO": "GPT-OSS compactado — rank-1 INT8 factors",
    "D03_TRANSCRIPCION": "Whisper compactado — low-rank INT8 factors",
    "D04_TRADUCTOR_INTELIGENTE": "SeamlessM4T v2 compactado — low-rank INT8 factors",
    "D05_INTELIGENCIA_DOCUMENTAL": "Granite Docling compactado — packed quantized weights",
    "D06_SISTEMA_INTELIGENTE": "Qwen3 compactado — low-rank INT8 factors",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    root = args.runtime_root.resolve(strict=True)
    if root.name == "LOUKSNAPG2_RUNTIME":
        root = root.parent
    sys.path.insert(0, str(root))
    evidence = {
        "schema": "LOUKSNAPG2_MODEL_MATERIALIZATION_EVIDENCE/1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "status": "FAIL",
        "source_repository": "Plomillo/luna-linux-bridge",
        "source_commit": __import__("os").environ.get("GITHUB_SHA", "UNKNOWN"),
        "source_manifest": "CAJITA_RUNTIME_V1/weights_manifest.json",
        "activation_policy": "USE_EXISTING_IN_ARTIFACT_CAJITA_WEIGHTS",
        "model_network_fetch_performed": False,
        "new_external_model_payloads": [],
        "models": [],
        "certification": "NOT_GRANTED_BY_MODEL_IDENTITY_EVIDENCE",
        "blockers": [],
    }
    try:
        from cajita_task_adapters import ADAPTERS, MANIFEST_SHA, verify_integrity

        manifest_path = root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
        if manifest_path.is_symlink() or not manifest_path.is_file():
            raise RuntimeError("ORIGINAL_WEIGHT_MANIFEST_MISSING_OR_UNSAFE")
        manifest_bytes = manifest_path.read_bytes()
        manifest_digest = hashlib.sha256(manifest_bytes).hexdigest()
        if manifest_digest != MANIFEST_SHA:
            raise RuntimeError("ORIGINAL_WEIGHT_MANIFEST_SHA256_MISMATCH")
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        if manifest.get("schema") != "CAJITA_SIX_DOMAIN_WEIGHT_MANIFEST/1.0":
            raise RuntimeError("ORIGINAL_WEIGHT_MANIFEST_SCHEMA_MISMATCH")

        rows = []
        for domain, model_label in DOMAIN_BINDINGS.items():
            binding = ADAPTERS[domain]
            integrity = verify_integrity(root, domain)
            weight = root / binding["weight"]
            if weight.is_symlink() or not weight.is_file():
                raise RuntimeError("ORIGINAL_MODEL_WEIGHT_MISSING_OR_UNSAFE:" + domain)
            size = weight.stat().st_size
            digest = sha256_file(weight)
            if size != binding["bytes"] or digest != binding["sha"]:
                raise RuntimeError("ORIGINAL_MODEL_WEIGHT_IDENTITY_MISMATCH:" + domain)
            matches = [
                item for item in manifest.get("artifacts", [])
                if item.get("path") == binding["weight"]
            ]
            if len(matches) != 1 or matches[0].get("sha256") != digest or int(matches[0].get("bytes", -1)) != size:
                raise RuntimeError("ORIGINAL_MANIFEST_ENTRY_MISMATCH:" + domain)
            if integrity.get("weight_sha256") != digest or integrity.get("weight_bytes") != size:
                raise RuntimeError("ORIGINAL_NATIVE_ADAPTER_INTEGRITY_BINDING_MISMATCH:" + domain)
            rows.append({
                "domain_id": domain,
                "model_label": model_label,
                "weight_path": binding["weight"],
                "bytes": size,
                "sha256": digest,
                "adapter_id": binding["id"],
                "native_module_tree_sha256": integrity.get("module_tree_sha256"),
                "status": "PASS_SOURCE_WEIGHT_AND_MODULE_IDENTITY",
            })
        evidence.update({
            "status": "PASS",
            "required_domain_count": 5,
            "manifest_bytes": len(manifest_bytes),
            "manifest_sha256": manifest_digest,
            "models": rows,
            "required_domain_count": 5,
            "unique_existing_model_weight_count": len(rows),
            "note": "Five model-backed domains bind to the existing compact Cajita weights. Ancient-language translation remains a specialist consumer over GPT-OSS and has no independent source-bound model payload."
        })
    except Exception as exc:
        evidence["blockers"].append(type(exc).__name__ + ":" + str(exc)[:500])

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "status": evidence["status"],
        "models": len(evidence["models"]),
        "model_network_fetch_performed": evidence["model_network_fetch_performed"],
        "blockers": evidence["blockers"],
        "certification": evidence["certification"],
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if evidence["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
