#!/usr/bin/env python3
"""Phase-4 bounded diagnosis of the pinned LOUKSNAPG candidate; no model inference or mutation."""
from __future__ import annotations

import argparse
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

BASELINE = "66f0f0d22f5e7f7d207b191b39e997d1253a3866"
MANIFEST_SHA = "703fb6b4c278b6111a354951bb7f9faf3721edb0c89b4dda843242e47634039d"
DOMAIN_SPECS = {
    "D01_CEREBRO": {
        "module": "1. Cerebro",
        "weight": "1. Cerebro/model.safetensors",
        "bytes": 40489120,
        "sha256": "e2516453d09285581bd6f3bf45a4c3a9fa6431bdc3dff56e7249d30e4e294ae0",
        "previous_quality": "FAIL",
        "previous_output_sha256": "9308bc822ed96f27b929493bd15837d4c54852d27ee851e6e004e57533ebfa7d",
    },
    "D03_TRANSCRIPCION": {
        "module": "3. Transcripción",
        "weight": "3. Transcripción/model.safetensors",
        "bytes": 10399882,
        "sha256": "67ee70beb2fb3529270a8169fbb6bd0f538912a064a6a303bec238647b4a5f5f",
        "previous_quality": "FAIL",
        "previous_output_sha256": "c2dcf834728a60f2b53b3f8668969b7b98c926d2b77a97905e5f8e3031720a6d",
    },
    "D04_TRADUCTOR_INTELIGENTE": {
        "module": "4. Traductor Inteligente/Traducción general",
        "weight": "4. Traductor Inteligente/Traducción general/model.safetensors",
        "bytes": 11720882,
        "sha256": "630aad9958f9c78603852c29c382b0fe9d63e64772e21dc6367875a91dc6a28f",
        "previous_quality": "FAIL",
        "previous_output_sha256": "10e494e1adfd2b16103009d2d5fe97aba97e7fb88f7447d3405e519d3159836a",
    },
    "D06_SISTEMA_INTELIGENTE": {
        "module": "6. Sistema Inteligente/Análisis Avanzado",
        "weight": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
        "bytes": 14956240,
        "sha256": "01eba827b9dd001a2352f0fd28a0bea229d3a5b3a78a41f3ea3e7c6c21995f56",
        "previous_quality": "FAIL",
        "previous_output_sha256": "b1a75ce6640d3d5f39e985ad1e0d4d54e76861b8294f6d997fba2f5e66743a67",
    },
}
TOKENIZER_MANIFEST_SHA = "89102653347a040787317dbc9f53ecda9ed40944"


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=20,
    ).stdout.strip()


def inspect_factor_shapes(weight_path: Path) -> dict:
    try:
        from safetensors import safe_open
    except Exception as exc:
        return {"status": "BLOCKED_SAFETENSORS_UNAVAILABLE", "error_type": type(exc).__name__}
    pairs = []
    with safe_open(str(weight_path), framework="pt", device="cpu") as handle:
        keys = list(handle.keys())
        keyset = set(keys)
        for key in keys:
            if key.endswith("_u") and "_scale_" not in key:
                partner = key[:-2] + "_v"
                if partner not in keyset:
                    continue
                ushape = list(handle.get_slice(key).get_shape())
                vshape = list(handle.get_slice(partner).get_shape())
                if len(ushape) < 2 or len(vshape) < 2:
                    continue
                urank = ushape[-1]
                vrank = vshape[-2] if len(vshape) >= 3 else vshape[0]
                pairs.append({
                    "u": key, "u_shape": ushape, "v": partner, "v_shape": vshape,
                    "rank_u": urank, "rank_v": vrank, "rank_matches": urank == vrank,
                })
    ranks = [int(row["rank_u"]) for row in pairs if row["rank_matches"]]
    return {
        "status": "PASS_METADATA_ONLY",
        "tensor_count": len(keys),
        "paired_factor_count": len(pairs),
        "factor_pairs": pairs[:24],
        "rank_counts": {str(r): ranks.count(r) for r in sorted(set(ranks))},
        "all_paired_ranks_equal_one": bool(ranks) and all(r == 1 for r in ranks),
        "factor_rank_mismatch_count": sum(1 for row in pairs if not row["rank_matches"]),
        "no_tensor_data_loaded": True,
    }


def inspect_tokenizers(root: Path) -> dict:
    manifest_path = root / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
    if not manifest_path.is_file():
        return {"status": "BLOCKED_MANIFEST_MISSING"}
    raw_manifest = manifest_path.read_bytes()
    manifest = json.loads(raw_manifest)
    rows = []
    all_ok = True
    for row in manifest.get("entries", []):
        record = {
            "source_path": row.get("source_path"),
            "compressed_path": row.get("compressed_path"),
            "packed": row.get("packed"),
            "source_bytes": row.get("source_bytes"),
            "source_sha256": row.get("source_sha256"),
            "compressed_bytes": row.get("compressed_bytes"),
            "compressed_sha256": row.get("compressed_sha256"),
        }
        if row.get("packed"):
            compressed = root / str(row.get("compressed_path", ""))
            try:
                packed = compressed.read_bytes()
                unpacked = gzip.decompress(packed)
                actual_packed_sha = hashlib.sha256(packed).hexdigest()
                actual_source_sha = hashlib.sha256(unpacked).hexdigest()
                record.update({
                    "actual_compressed_bytes": len(packed),
                    "actual_compressed_sha256": actual_packed_sha,
                    "actual_source_bytes": len(unpacked),
                    "actual_source_sha256": actual_source_sha,
                    "compressed_hash_matches": len(packed) == row.get("compressed_bytes") and actual_packed_sha == row.get("compressed_sha256"),
                    "source_hash_matches": len(unpacked) == row.get("source_bytes") and actual_source_sha == row.get("source_sha256"),
                })
                ok = record["compressed_hash_matches"] and record["source_hash_matches"]
            except Exception as exc:
                record.update({"verification_error_type": type(exc).__name__})
                ok = False
            all_ok = all_ok and ok
        rows.append(record)
    return {
        "status": "PASS_BYTE_EXACT" if all_ok and rows else "FAIL_OR_INCOMPLETE",
        "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "manifest_source_commit": manifest.get("source_commit"),
        "entries": rows,
        "tokenizer_byte_identity_verified": all_ok and bool(rows),
        "model_quality_equivalence_established": False,
    }


def inspect_ancient_assets(root: Path) -> dict:
    folder = root / "4. Traductor Inteligente/Traducción de lenguas antiguas"
    if not folder.is_dir():
        return {"status": "BLOCKED_DIRECTORY_MISSING"}
    suffixes = {".fst", ".hfst", ".lexc", ".twolc", ".foma", ".dict", ".tsv", ".csv", ".jsonl", ".yaml", ".yml"}
    rows = []
    counts = {}
    for p in folder.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        if p.suffix.lower() in suffixes:
            counts[p.suffix.lower()] = counts.get(p.suffix.lower(), 0) + 1
            if len(rows) < 120:
                rows.append({"path": p.relative_to(folder).as_posix(), "suffix": p.suffix.lower(), "bytes": p.stat().st_size})
    compiled = [r for r in rows if Path(r["path"]).suffix.lower() in {".fst", ".hfst"} and r["bytes"] > 0]
    transducers_present = bool(compiled)
    descriptor_path = folder / "CAJITA_MODULE.json"
    descriptor = {}
    if descriptor_path.is_file():
        try:
            descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        except Exception:
            descriptor = {"parse_status": "INVALID_JSON"}
    return {
        "status": "COMPILED_TRANSDUCER_CANDIDATE_FOUND" if transducers_present else "SOURCE_PRESENT_NO_COMPILED_TRANSDUCER_FOUND_IN_SCANNED_TREE",
        "file_counts_by_suffix": counts,
        "sample_files": rows,
        "compiled_transducer_sample": compiled[:20],
        "descriptor": {
            "consumer_adapter": descriptor.get("consumer_adapter"),
            "functional_state": descriptor.get("functional_state"),
            "target_id": descriptor.get("target_id"),
        },
        "translation_lexicon_or_transducer_ready": transducers_present,
        "scan_scope": "candidate module recursively; no network downloads; no source edits",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", required=True)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(strict=True)
    evidence_path = Path(args.evidence).resolve(strict=True)
    out_path = Path(args.out)
    current = git(root, "rev-parse", "HEAD")
    base_present = subprocess.run(
        ["git", "-C", str(root), "cat-file", "-e", BASELINE + "^{commit}"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=10,
    ).returncode == 0
    is_ancestor = base_present and subprocess.run(
        ["git", "-C", str(root), "merge-base", "--is-ancestor", BASELINE, "HEAD"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=10,
    ).returncode == 0
    runtime_unchanged = False
    if is_ancestor:
        runtime_unchanged = subprocess.run(
            ["git", "-C", str(root), "diff", "--quiet", BASELINE, "HEAD", "--", "cajita-luna-runtime"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False, timeout=20,
        ).returncode == 0
    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
    if evidence.get("candidate_commit") != BASELINE:
        raise SystemExit("PRIOR_CHECKPOINT_CANDIDATE_MISMATCH")
    if evidence.get("phase_2_status") != "REGISTERED_DOMAIN_TEST_FAILURE":
        raise SystemExit("PRIOR_PHASE2_STATUS_UNEXPECTED")
    weight_manifest_path = root / "cajita-luna-runtime/CAJITA_RUNTIME_V1/weights_manifest.json"
    if not weight_manifest_path.is_file():
        raise SystemExit("CANDIDATE_WEIGHT_MANIFEST_MISSING")
    weight_manifest_raw = weight_manifest_path.read_bytes()
    actual_manifest_sha = hashlib.sha256(weight_manifest_raw).hexdigest()
    if actual_manifest_sha != MANIFEST_SHA:
        raise SystemExit("CANDIDATE_WEIGHT_MANIFEST_SHA_MISMATCH:" + actual_manifest_sha)
    weight_manifest = json.loads(weight_manifest_raw)
    model_rows = []
    all_weights_ok = True
    for domain, spec in DOMAIN_SPECS.items():
        weight = root / "cajita-luna-runtime" / spec["weight"]
        module_path = root / "cajita-luna-runtime" / spec["module"] / "CAJITA_MODULE.json"
        if not weight.is_file() or not module_path.is_file():
            model_rows.append({"domain_id": domain, "status": "BLOCKED_REQUIRED_FILE_MISSING"})
            all_weights_ok = False
            continue
        expected_size = spec["bytes"]
        actual_size = weight.stat().st_size
        actual_sha = digest(weight)
        with weight.open("rb") as stream:
            lfs_pointer = stream.read(64).startswith(b"version https://git-lfs.github.com/spec/v1")
        identity_ok = actual_size == expected_size and actual_sha == spec["sha256"] and not lfs_pointer
        all_weights_ok = all_weights_ok and identity_ok
        descriptor = json.loads(module_path.read_text(encoding="utf-8"))
        factor_meta = inspect_factor_shapes(weight) if identity_ok else {"status": "SKIPPED_WEIGHT_IDENTITY_FAILURE"}
        model_rows.append({
            "domain_id": domain,
            "weight_path": spec["weight"],
            "actual_bytes": actual_size,
            "expected_bytes": expected_size,
            "actual_sha256": actual_sha,
            "expected_sha256": spec["sha256"],
            "weight_identity_pass": identity_ok,
            "lfs_pointer_not_materialized": lfs_pointer,
            "manifest_representation": next((x.get("representation") for x in weight_manifest.get("artifacts", []) if x.get("path") == spec["weight"]), None),
            "module_status": descriptor.get("consumer_adapter_registration", {}).get("status"),
            "reference_quality_equivalence": descriptor.get("consumer_adapter_registration", {}).get("reference_quality_equivalence"),
            "previous_phase2_quality_status": spec["previous_quality"],
            "previous_phase2_output_sha256": spec["previous_output_sha256"],
            "factor_metadata": factor_meta,
        })
    current_weight_paths = [str(row["weight_path"]) for row in model_rows if row.get("weight_path")]
    # Check for full upstream checkpoint shards inside each model module, not just the low-rank payload.
    full_source_rows = []
    model_root = root / "cajita-luna-runtime"
    for p in model_root.rglob("*"):
        if not p.is_file() or p.is_symlink():
            continue
        rel = p.relative_to(model_root).as_posix()
        size = p.stat().st_size
        if p.suffix.lower() in {".safetensors", ".bin", ".gguf", ".pth"} and size >= 1_000_000_000:
            full_source_rows.append({"path": rel, "bytes": size, "classification": "LARGE_WEIGHT_PAYLOAD_CANDIDATE"})
        elif re.fullmatch(r"(?:model|pytorch_model)-\d+-of-\d+\.(?:safetensors|bin)", p.name, flags=re.IGNORECASE):
            full_source_rows.append({"path": rel, "bytes": size, "classification": "SHARDED_WEIGHT_PAYLOAD_CANDIDATE"})
    tokenizer_result = inspect_tokenizers(model_root)
    ancient_result = inspect_ancient_assets(model_root)
    rank1_domains = [
        row["domain_id"] for row in model_rows
        if row.get("factor_metadata", {}).get("all_paired_ranks_equal_one") is True
    ]
    every_failed_domain_rank1 = len(rank1_domains) == 4
    if not all_weights_ok:
        phase4_status = "BLOCKED_WEIGHT_IDENTITY_FAILURE"
    elif every_failed_domain_rank1 and tokenizer_result.get("tokenizer_byte_identity_verified"):
        phase4_status = "DIAGNOSIS_COMPLETE_COMMON_RANK1_COMPRESSION_HYPOTHESIS_STRONGLY_CORROBORATED"
    else:
        phase4_status = "DIAGNOSIS_COMPLETE_ROOT_CAUSE_NOT_EXCLUSIVE"
    report = {
        "schema": "LOUKSNAPG_PHASE4_FORENSIC_DIAGNOSIS/1.0",
        "generated_at_utc": utc_now(),
        "repository": "Plomillo/luna-linux-bridge",
        "candidate_commit_under_test": BASELINE,
        "continuation_commit": current,
        "prior_evidence": {
            "artifact_run_id": 40614237594,
            "phase2_status": evidence.get("phase_2_status"),
            "expected_registered_domains": evidence.get("registered_domain_tests_expected"),
            "registered_domain_tests_passed": evidence.get("registered_domain_tests_passed"),
            "global_certification": evidence.get("global_certification"),
            "archive_sha256": evidence.get("evidence_archive_sha256"),
        },
        "continuation_identity": {
            "baseline_commit_present": base_present,
            "baseline_is_ancestor": is_ancestor,
            "runtime_tree_unchanged_from_baseline": runtime_unchanged,
            "phases_1_to_3_rerun": False,
            "model_inference_performed": False,
            "repository_mutated_by_diagnostic": False,
        },
        "weight_manifest": {
            "path": "cajita-luna-runtime/CAJITA_RUNTIME_V1/weights_manifest.json",
            "sha256": actual_manifest_sha,
            "expected_sha256": MANIFEST_SHA,
            "candidate_id": weight_manifest.get("candidate_id"),
            "functional_equivalence": weight_manifest.get("functional_equivalence"),
            "certification": weight_manifest.get("certification"),
        },
        "registered_model_domains": model_rows,
        "full_upstream_model_weight_payloads_in_candidate": full_source_rows,
        "full_source_model_weight_shards_found_in_candidate": bool(full_source_rows),
        "tokenizer_integrity": tokenizer_result,
        "ancient_translation_assets": ancient_result,
        "root_cause_assessment": {
            "rank1_factor_compression_across_all_four_failed_domains": every_failed_domain_rank1,
            "rank1_domains": rank1_domains,
            "status": phase4_status,
            "claim_limit": "This is a corroborated cause hypothesis, not proof that rank-1 compression is the only defect. No reference-model equivalence is declared.",
            "repair_decision": "DO_NOT_OVERWRITE_OR_REPLACE_V9_WEIGHTS. Create an isolated experimental candidate from verified upstream source weights, compare task acceptance, then register only after evidence.",
        },
        "phase_progress": {
            "phase_4": phase4_status,
            "phase_5_targeted_post_repair_tests": "BLOCKED_NO_JUSTIFIED_REPAIR_AVAILABLE_IN_PINNED_CANDIDATE",
            "phase_6_integrated_runtime": "PENDING",
            "phase_7_independent_certification": "PENDING_NOT_GRANTED",
            "phase_8_release": "BLOCKED",
            "phase_9_governance": "PASS_SCOPE_PRESERVED",
            "next_action": "Use the PC inventory in Kestra output to identify available V4 source variants; do not upload private/local model weights to the public repository. Select the smallest source variant whose shapes and hashes are valid, then test it in an isolated approved runner before promoting it.",
        },
        "global_certification": "NOT_GRANTED",
    }
    out_path.parent.mkdir(parents=True, exist_ok=True)
    temp = out_path.with_suffix(out_path.suffix + ".building")
    temp.write_text(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, out_path)
    print(json.dumps({
        "event": "PHASE4_DIAGNOSTIC_COMPLETE",
        "candidate_commit": BASELINE,
        "continuation_commit": current,
        "phase4_status": phase4_status,
        "rank1_domains": rank1_domains,
        "tokenizer_identity": tokenizer_result.get("status"),
        "ancient_asset_status": ancient_result.get("status"),
        "global_certification": "NOT_GRANTED",
        "report": str(out_path),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
