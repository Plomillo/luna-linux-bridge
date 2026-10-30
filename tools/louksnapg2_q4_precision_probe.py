#!/usr/bin/env python3
"""Compare the active Q2 factors with repository-retained Q4-packed factors.

Every candidate is assembled in an isolated temporary directory. The Q4 source
commit and factor-source hashes are pinned; the active checkout and Git history
are read-only. This is a non-certifying semantic probe.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

import louksnapg2_historical_weight_probe as common

Q4_SOURCE_COMMIT = "fa8b64b1319605e050c2064f955f5fbf47951908"

def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def replace_adapter_registry(adapter_path: Path, domain: str, weight_path: str, sha: str, size: int, manifest_sha: str) -> str:
    source = adapter_path.read_text(encoding="utf-8")
    manifest_lines = [line for line in source.splitlines() if line.startswith("MANIFEST_SHA = ")]
    if len(manifest_lines) != 1:
        raise RuntimeError("Q4_MANIFEST_SHA_ANCHOR_NOT_UNIQUE")
    source = source.replace(manifest_lines[0], f'MANIFEST_SHA = "{manifest_sha}"', 1)

    marker = f'"{domain}": {{"weight":"{weight_path}","sha":"'
    start = source.find(marker)
    if start < 0 or source.find(marker, start + 1) >= 0:
        raise RuntimeError("Q4_ADAPTER_REGISTRY_ANCHOR_NOT_UNIQUE:" + domain)
    sha_start = start + len(marker)
    sha_end = sha_start + 64
    if sha_end > len(source) or any(c not in "0123456789abcdef" for c in source[sha_start:sha_end]):
        raise RuntimeError("Q4_ADAPTER_REGISTRY_SHA_FIELD_INVALID:" + domain)
    size_marker = ',"bytes":'
    size_start = source.find(size_marker, sha_end)
    if size_start < 0:
        raise RuntimeError("Q4_ADAPTER_REGISTRY_SIZE_FIELD_MISSING:" + domain)
    size_value_start = size_start + len(size_marker)
    size_end = source.find(",", size_value_start)
    if size_end < 0:
        raise RuntimeError("Q4_ADAPTER_REGISTRY_SIZE_FIELD_UNTERMINATED:" + domain)
    source = (
        source[:sha_start] + sha + source[sha_end:size_value_start]
        + str(size) + source[size_end:]
    )
    adapter_path.write_text(source, encoding="utf-8")
    return sha256_file(adapter_path)

def prepare_q4_runtime(current_root: Path, q4_root: Path, domain: str, temp_root: Path) -> dict:
    spec = common.DOMAINS[domain]
    q4_weight = q4_root / spec["weight"]
    q4_sidecar = q4_root / spec["sidecar"]
    current_sidecar = current_root / spec["sidecar"]
    for path, label in (
        (q4_weight, "Q4_WEIGHT"),
        (q4_sidecar, "Q4_SIDECAR"),
        (current_sidecar, "CURRENT_Q2_SIDECAR"),
    ):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError(label + "_MISSING_OR_UNSAFE")

    q4_meta = json.loads(q4_sidecar.read_text(encoding="utf-8"))
    q2_meta = json.loads(current_sidecar.read_text(encoding="utf-8"))
    q4_source_sha = q4_meta.get("source_sha256")
    q2_source_sha = q2_meta.get("source_sha256")
    if q4_meta.get("schema") != "CAJITA_Q4_BLOCK_PACKED/1.0":
        raise RuntimeError("Q4_SIDECAR_SCHEMA_MISMATCH")
    if not isinstance(q4_source_sha, str) or q4_source_sha != q2_source_sha:
        raise RuntimeError("Q4_SOURCE_FACTOR_IDENTITY_MISMATCH")
    if sha256_file(q4_weight) != q4_meta.get("candidate_sha256"):
        raise RuntimeError("Q4_CANDIDATE_WEIGHT_SHA256_MISMATCH")

    shutil.copytree(
        current_root,
        temp_root,
        ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        copy_function=shutil.copy2,
    )
    weight_dest = temp_root / spec["weight"]
    sidecar_dest = temp_root / spec["sidecar"]
    weight_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(q4_weight, weight_dest)
    shutil.copy2(q4_sidecar, sidecar_dest)
    weight_sha = sha256_file(weight_dest)
    weight_bytes = weight_dest.stat().st_size

    manifest_path = temp_root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [row for row in manifest.get("artifacts", []) if row.get("path") == spec["weight"]]
    if len(matches) != 1:
        raise RuntimeError("Q4_WEIGHT_MANIFEST_ENTRY_NOT_UNIQUE")
    matches[0]["sha256"] = weight_sha
    matches[0]["bytes"] = weight_bytes
    manifest["total_weight_bytes"] = sum(int(row.get("bytes", 0)) for row in manifest["artifacts"])
    manifest["total_weight_decimal_mb"] = round(manifest["total_weight_bytes"] / 1_000_000, 3)
    common.write_json(manifest_path, manifest)
    manifest_sha = sha256_file(manifest_path)

    adapter_path = temp_root / "cajita_task_adapters.py"
    adapter_sha = replace_adapter_registry(
        adapter_path, domain, spec["weight"], weight_sha, weight_bytes, manifest_sha
    )

    descriptor_path = temp_root / spec["module"] / "CAJITA_MODULE.json"
    if descriptor_path.is_symlink() or not descriptor_path.is_file():
        raise RuntimeError("Q4_MODULE_DESCRIPTOR_MISSING_OR_UNSAFE")
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    if descriptor.get("domain_id") != domain:
        raise RuntimeError("Q4_MODULE_DOMAIN_MISMATCH")
    registration = descriptor.get("consumer_adapter_registration", {})
    registration.update({
        "weight_sha256": weight_sha,
        "weight_bytes": weight_bytes,
        "weight_manifest_sha256": manifest_sha,
        "adapter_source_sha256": adapter_sha,
    })
    descriptor["consumer_adapter_registration"] = registration

    # Baseline preparation may have imported these modules from a temporary
    # directory that has since been removed. Drop those cached modules and load
    # the adapter/materializer directly from this Q4 runtime copy.
    sys.modules.pop("cajita_task_adapters", None)
    sys.modules.pop("cajita_tokenizer_materializer", None)
    sys.path.insert(0, str(temp_root))
    import cajita_task_adapters as adapters
    import cajita_tokenizer_materializer as tokenizer
    adapters.MANIFEST_SHA = manifest_sha
    adapters.ADAPTERS[domain]["sha"] = weight_sha
    adapters.ADAPTERS[domain]["bytes"] = weight_bytes

    module_root = temp_root / spec["module"]
    rows = adapters.tree_rows(module_root)
    tokenizer_manifest = temp_root / adapters.TOKENIZER_MANIFEST_NAME
    if tokenizer_manifest.is_file():
        rows = tokenizer.tokenizer_tree_rows(module_root, temp_root, rows)
    tree_hash = adapters.digest_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    )
    descriptor["tree_integrity"] = {
        "sha256": tree_hash,
        "file_count_excluding_module_descriptors": len(rows),
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
    }
    common.write_json(descriptor_path, descriptor)
    verified = adapters.verify_integrity(temp_root, domain)

    return {
        "domain_id": domain,
        "q4_source_commit": Q4_SOURCE_COMMIT,
        "source_representation": "HISTORICAL_Q4_BLOCK_PACKED_FACTORS_FROM_THIS_REPOSITORY",
        "weight_path": spec["weight"],
        "weight_sha256": weight_sha,
        "weight_bytes": weight_bytes,
        "q4_sidecar_sha256": sha256_file(sidecar_dest),
        "q4_source_factor_sha256": q4_source_sha,
        "current_q2_source_factor_sha256": q2_source_sha,
        "source_factor_identity_match": True,
        "manifest_sha256": manifest_sha,
        "module_integrity": verified,
        "active_checkout_mutated": False,
        "original_model_payload_mutated": False,
    }

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", required=True, type=Path)
    parser.add_argument("--q4-root", required=True, type=Path)
    parser.add_argument("--domain", required=True, choices=tuple(common.DOMAINS))
    parser.add_argument("--audio-one", type=Path)
    parser.add_argument("--audio-two", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)

    current_root = args.runtime_root.resolve(strict=True)
    q4_root = args.q4_root.resolve(strict=True)

    with tempfile.TemporaryDirectory(prefix="louksnapg2-q2-current-") as baseline_tmp:
        baseline_root = Path(baseline_tmp) / "runtime"
        baseline_source = common.prepare_current_runtime(current_root, baseline_root, args.domain)
        baseline = common.subprocess_evaluate(
            Path(common.__file__).resolve(), baseline_root, args.domain, args.audio_one, args.audio_two
        )

    with tempfile.TemporaryDirectory(prefix="louksnapg2-q4-historical-") as q4_tmp:
        q4_runtime_root = Path(q4_tmp) / "runtime"
        q4_source = prepare_q4_runtime(current_root, q4_root, args.domain, q4_runtime_root)
        q4 = common.subprocess_evaluate(
            Path(common.__file__).resolve(), q4_runtime_root, args.domain, args.audio_one, args.audio_two
        )

    report = {
        "schema": "LOUKSNAPG2_Q2_VS_HISTORICAL_Q4_PRECISION_PROBE/1.0",
        "experiment": "ACTIVE_Q2_FACTORS_VS_REPOSITORY_RETAINED_Q4_PACKED_FACTORS",
        "repository_only": True,
        "external_model_downloads": False,
        "domain_id": args.domain,
        "baseline_q2": baseline,
        "historical_q4": q4,
        "baseline_q2_source": baseline_source,
        "historical_q4_source": q4_source,
        "comparison": {
            "q2_passed": baseline.get("pass_count", 0),
            "q4_passed": q4.get("pass_count", 0),
            "total_cases": baseline.get("total_cases", 0),
            "q4_pass_delta": q4.get("pass_count", 0) - baseline.get("pass_count", 0),
            "same_factor_source_sha256": q4_source["source_factor_identity_match"],
            "quality_equivalence_to_full_size_upstream": "NOT_ESTABLISHED",
        },
        "certification": "NOT_GRANTED_BY_PRECISION_PROBE",
    }
    common.write_json(args.output, report)
    print(json.dumps({
        "domain_id": args.domain,
        "q2": f'{baseline.get("pass_count", 0)}/{baseline.get("total_cases", 0)}',
        "q4": f'{q4.get("pass_count", 0)}/{q4.get("total_cases", 0)}',
        "q2_status": baseline.get("status"),
        "q4_status": q4.get("status"),
        "q4_pass_delta": report["comparison"]["q4_pass_delta"],
        "same_factor_source": q4_source["source_factor_identity_match"],
        "certification": "NOT_GRANTED_BY_PRECISION_PROBE",
        "output": str(args.output),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if q4.get("total_cases", 0) and q4_source["source_factor_identity_match"] else 2

if __name__ == "__main__":
    raise SystemExit(main())
