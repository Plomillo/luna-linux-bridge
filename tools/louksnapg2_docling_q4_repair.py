#!/usr/bin/env python3
"""Build and evaluate a source-bound, groupwise INT4 Granite Docling candidate.

Build is constrained by the caller to 3 GiB RAM / 1 CPU. Evaluation is constrained
by the caller to 1 GiB RAM / 1 CPU. Source weights are immutable; no candidate is
promoted unless invoice extraction passes the exact semantic predicate.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import re
import shutil
import sys
import time
import zlib
from pathlib import Path

import numpy as np

MODEL_ID = "ibm-granite/granite-docling-258M"
MODEL_REVISION = "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe"
SOURCE_WEIGHT_BYTES = 515_093_104
SOURCE_WEIGHT_SHA256 = "1cdad234deb1cde18ee6a586f849057f19851daf1fedce2e40aff791dbe46f61"
SOURCE_CONFIG_SHA256 = "4fbb5d2a"  # Replaced below by a full pinned digest check if present.
GROUP_SIZE = 256
WEIGHT_HARD_CAP_BYTES = 114_000_000
GLOBAL_RELEASE_MAX_BYTES = 490_000_000
BASELINE_RELEASE_BYTES = 371_981_138
BASELINE_DOCLING_WEIGHT_BYTES = 13_483_380
CANDIDATE_ID = "GRANITE_DOCLING_258M_SOURCE_Q4_GROUP256_ZLIB_20261102"
DOMAIN_REL = Path("5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate")
RUNTIME_REL = Path("cajita-luna-runtime/5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/docling_30mb_runtime_v1.py")
EXPECTED_FIELDS = ("invoice", "4821", "37", "50")
PROMPT = "Convert this page to docling."


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def pack_int4(values: np.ndarray) -> np.ndarray:
    """Pack signed int4 values (-7..7) into low/high nibbles."""
    signed = np.asarray(values, dtype=np.int8).reshape(-1)
    if signed.size % 2:
        raise ValueError("INT4_PACK_REQUIRES_EVEN_ELEMENT_COUNT")
    codes = (signed.astype(np.int16) & 0x0F).astype(np.uint8).reshape(-1, 2)
    return (codes[:, 0] | (codes[:, 1] << 4)).astype(np.uint8)


def unpack_int4(packed: np.ndarray, count: int) -> np.ndarray:
    b = np.asarray(packed, dtype=np.uint8).reshape(-1)
    out = np.empty(b.size * 2, dtype=np.int8)
    low = b & 0x0F
    high = b >> 4
    out[0::2] = np.where(low >= 8, low.astype(np.int16) - 16, low).astype(np.int8)
    out[1::2] = np.where(high >= 8, high.astype(np.int16) - 16, high).astype(np.int8)
    return out[:count]


def self_test() -> None:
    rng = np.random.default_rng(17)
    values = rng.integers(-7, 8, size=32768, dtype=np.int8)
    packed = pack_int4(values)
    restored = unpack_int4(packed, values.size)
    if not np.array_equal(values, restored):
        raise RuntimeError("INT4_PACK_ROUNDTRIP_FAILED")
    payload = packed.tobytes() + np.arange(128, dtype="<f2").tobytes()
    if zlib.decompress(zlib.compress(payload, 9)) != payload:
        raise RuntimeError("ZLIB_PAYLOAD_ROUNDTRIP_FAILED")
    print(json.dumps({"status": "PASS", "int4_values": int(values.size), "packed_bytes": int(packed.size)}))


def build(args: argparse.Namespace) -> int:
    import torch
    from huggingface_hub import hf_hub_download
    from safetensors import safe_open

    if os.environ.get("GITHUB_ACTIONS", "").lower() != "true":
        raise RuntimeError("BUILD_REQUIRES_ISOLATED_GITHUB_3GIB_RUNNER")
    if torch.get_num_threads() != 1:
        torch.set_num_threads(1)
    torch.set_num_interop_threads(1)

    source_weight = Path(hf_hub_download(
        repo_id=MODEL_ID, filename="model.safetensors", revision=MODEL_REVISION
    ))
    source_config = Path(hf_hub_download(
        repo_id=MODEL_ID, filename="config.json", revision=MODEL_REVISION
    ))
    observed_weight_sha = sha256_file(source_weight)
    observed_config_sha = sha256_file(source_config)
    if source_weight.stat().st_size != SOURCE_WEIGHT_BYTES or observed_weight_sha != SOURCE_WEIGHT_SHA256:
        raise RuntimeError("UPSTREAM_SOURCE_WEIGHT_IDENTITY_MISMATCH:" + observed_weight_sha)
    # The model repository's config is checked against the exact source identity
    # recorded in the current Docling manifest; fail closed if that source differs.
    base_manifest_path = args.base_candidate / "quantized_manifest.json"
    if not base_manifest_path.is_file():
        raise RuntimeError("BASE_DOCLING_MANIFEST_MISSING")
    old_manifest = json.loads(base_manifest_path.read_text(encoding="utf-8"))
    expected_config_sha = old_manifest.get("source_hf_config_sha256")
    if expected_config_sha and observed_config_sha != expected_config_sha:
        raise RuntimeError("UPSTREAM_CONFIG_IDENTITY_MISMATCH:" + observed_config_sha)

    candidate = args.output_dir / "candidate"
    if candidate.exists():
        shutil.rmtree(candidate)
    shutil.copytree(args.base_candidate, candidate, symlinks=False)
    out_weights = candidate / "quantized_weights.bin"
    records: dict[str, dict] = {}
    total_norm_sq = 0.0
    total_error_sq = 0.0
    total_numel = 0
    tensor_count = 0
    started = time.monotonic()

    with safe_open(str(source_weight), framework="pt", device="cpu") as source, out_weights.open("wb") as output:
        keys = sorted(source.keys())
        for name in keys:
            tensor = source.get_tensor(name).detach().cpu()
            shape = [int(x) for x in tensor.shape]
            numel = int(tensor.numel())
            offset = output.tell()
            if tensor.ndim <= 1:
                arr = tensor.to(torch.float16).contiguous().numpy().astype("<f2", copy=False)
                raw = arr.tobytes(order="C")
                output.write(raw)
                records[name] = {
                    "name": name, "kind": "fp16", "shape": shape,
                    "offset": offset, "nbytes": len(raw), "numel": numel,
                }
                del arr, raw, tensor
                tensor_count += 1
                continue

            flat = tensor.to(torch.float32).contiguous().numpy().reshape(-1)
            group_count = (numel + GROUP_SIZE - 1) // GROUP_SIZE
            padded_numel = group_count * GROUP_SIZE
            packed = bytearray(padded_numel // 2)
            scales_all = np.empty(group_count, dtype="<f2")
            tensor_norm_sq = 0.0
            tensor_error_sq = 0.0
            chunk_groups = 4096
            for group_start in range(0, group_count, chunk_groups):
                group_end = min(group_count, group_start + chunk_groups)
                count = group_end - group_start
                start = group_start * GROUP_SIZE
                end = min(numel, group_end * GROUP_SIZE)
                block = np.zeros((count, GROUP_SIZE), dtype=np.float32)
                valid = end - start
                if valid > 0:
                    block.reshape(-1)[:valid] = flat[start:end]
                scale32 = np.maximum(np.max(np.abs(block), axis=1) / 7.0, 1e-6).astype(np.float32)
                scale16 = scale32.astype("<f2")
                scales_all[group_start:group_end] = scale16
                q = np.rint(block / scale32[:, None]).clip(-7, 7).astype(np.int8)
                packed_chunk = pack_int4(q)
                byte_start = group_start * (GROUP_SIZE // 2)
                packed[byte_start:byte_start + packed_chunk.size] = packed_chunk.tobytes()
                reconstructed = q.astype(np.float32) * scale16.astype(np.float32)[:, None]
                tensor_norm_sq += float(np.sum(block * block, dtype=np.float64))
                tensor_error_sq += float(np.sum((block - reconstructed) ** 2, dtype=np.float64))
                del block, scale32, scale16, q, packed_chunk, reconstructed

            raw_payload = bytes(packed) + scales_all.tobytes(order="C")
            compressed = zlib.compress(raw_payload, level=9)
            output.write(compressed)
            records[name] = {
                "name": name,
                "kind": "signed_int4_groupwise_zlib",
                "shape": shape,
                "numel": numel,
                "group_size": GROUP_SIZE,
                "group_count": group_count,
                "padded_numel": padded_numel,
                "offset": offset,
                "compressed_nbytes": len(compressed),
                "packed_nbytes": len(packed),
                "scales_nbytes": int(scales_all.nbytes),
                "scale_dtype": "<f2",
            }
            total_norm_sq += tensor_norm_sq
            total_error_sq += tensor_error_sq
            total_numel += numel
            tensor_count += 1
            del flat, packed, scales_all, raw_payload, compressed, tensor

    weights_bytes = out_weights.stat().st_size
    weights_sha = sha256_file(out_weights)
    if weights_bytes > WEIGHT_HARD_CAP_BYTES:
        raise RuntimeError(f"DOCLING_Q4_WEIGHT_HARD_CAP_EXCEEDED:{weights_bytes}:{WEIGHT_HARD_CAP_BYTES}")
    original_bytes = int((args.base_candidate / "quantized_weights.bin").stat().st_size)
    estimated_global_bytes = (
        BASELINE_RELEASE_BYTES - BASELINE_DOCLING_WEIGHT_BYTES + weights_bytes + 1_000_000
    )
    if estimated_global_bytes > GLOBAL_RELEASE_MAX_BYTES:
        raise RuntimeError(
            f"GLOBAL_RELEASE_HARD_CAP_EXCEEDED:{estimated_global_bytes}:{GLOBAL_RELEASE_MAX_BYTES}"
        )

    manifest = {
        "schema": "DOCLING_Q4_GROUPWISE_ZLIB_MANIFEST/1.0",
        "candidate_id": CANDIDATE_ID,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "source_hf_config_sha256": observed_config_sha,
        "source_hf_weight_hashes": {
            "model.safetensors": {"bytes": SOURCE_WEIGHT_BYTES, "sha256": SOURCE_WEIGHT_SHA256}
        },
        "weights_sha256": weights_sha,
        "weight_bytes": weights_bytes,
        "hard_cap_bytes": WEIGHT_HARD_CAP_BYTES,
        "quantization": {
            "method": "SYMMETRIC_GROUPWISE_INT4_PER_256_VALUES_ZLIB_PER_TENSOR",
            "signed_range": [-7, 7],
            "group_size": GROUP_SIZE,
            "scale_dtype": "FP16",
            "packing": "TWO_SIGNED_VALUES_PER_BYTE_LOW_NIBBLE_FIRST",
            "compression": "zlib level 9, independent frame per tensor",
        },
        "tensor_count": tensor_count,
        "tie_word_embeddings": bool(json.loads(source_config.read_text(encoding="utf-8")).get("tie_word_embeddings", False)),
        "tensors": records,
        "source_mutation": False,
        "candidate_promotion": "NOT_AUTHORIZED_PENDING_1G_SEMANTIC_EVALUATION",
    }
    write_json(candidate / "quantized_manifest.json", manifest)

    compression_path = candidate / "compression_metadata.json"
    previous = {}
    if compression_path.is_file():
        previous = json.loads(compression_path.read_text(encoding="utf-8"))
    previous.update({
        "candidate_id": CANDIDATE_ID,
        "model_id": MODEL_ID,
        "model_revision": MODEL_REVISION,
        "source_weight_sha256": observed_weight_sha,
        "source_config_sha256": observed_config_sha,
        "source_weights_written": False,
        "method": manifest["quantization"]["method"],
        "group_size": GROUP_SIZE,
        "quantized_weight_bytes": weights_bytes,
        "quantized_weight_sha256": weights_sha,
        "relative_frobenius_error": math.sqrt(total_error_sq / max(total_norm_sq, 1e-30)),
        "tensor_count": tensor_count,
        "numel_quantized": total_numel,
        "quality_equivalence": "PENDING_1G_SEMANTIC_EVALUATION",
        "certification": "NOT_GRANTED",
    })
    write_json(compression_path, previous)

    if sha256_file(source_weight) != SOURCE_WEIGHT_SHA256:
        raise RuntimeError("UPSTREAM_TEACHER_CHANGED_DURING_REPAIR")
    report = {
        "schema": "LOUKSNAPG2_DOCLING_Q4_REPAIR_BUILD/1.0",
        "status": "PASS_REPAIR_BUILD_AWAITING_SEMANTIC_EVALUATION",
        "candidate_id": CANDIDATE_ID,
        "source": {
            "model_id": MODEL_ID,
            "revision": MODEL_REVISION,
            "weights_bytes": SOURCE_WEIGHT_BYTES,
            "weights_sha256": observed_weight_sha,
            "config_sha256": observed_config_sha,
            "source_mutated": False,
        },
        "candidate": {
            "weights_bytes": weights_bytes,
            "weights_sha256": weights_sha,
            "weight_hard_cap_bytes": WEIGHT_HARD_CAP_BYTES,
            "bundle_directory_bytes": sum(p.stat().st_size for p in candidate.rglob("*") if p.is_file()),
            "replaced_previous_weight_bytes": original_bytes,
            "estimated_global_release_bytes": estimated_global_bytes,
            "global_release_hard_cap_bytes": GLOBAL_RELEASE_MAX_BYTES,
            "estimated_global_cap_pass": estimated_global_bytes <= GLOBAL_RELEASE_MAX_BYTES,
        },
        "quantization": manifest["quantization"],
        "tensor_count": tensor_count,
        "relative_frobenius_error": math.sqrt(total_error_sq / max(total_norm_sq, 1e-30)),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "repair_ram_limit_bytes": 3 * 1024**3,
        "evaluation_ram_limit_bytes": 1 * 1024**3,
        "promotion": "NOT_AUTHORIZED",
    }
    write_json(args.output_dir / "repair_build_report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def evaluate(args: argparse.Namespace) -> int:
    runtime_path = args.repo_root / RUNTIME_REL
    if not runtime_path.is_file():
        raise RuntimeError("DOCILING_RUNTIME_NOT_FOUND:" + str(runtime_path))
    spec = importlib.util.spec_from_file_location("docling_q4_runtime", runtime_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("DOCLING_RUNTIME_IMPORT_SPEC_FAILED")
    runtime = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runtime)
    result = runtime.smoke(
        args.candidate_dir,
        max_new_tokens=args.max_new_tokens,
        image_path=str(args.image),
        prompt=PROMPT,
    )
    words = set(re.findall(r"[a-z0-9]+", str(result.get("output_text", "")).casefold()))
    missing = [word for word in EXPECTED_FIELDS if word not in words]
    peak = int(result.get("peak_rss_bytes", 0))
    quality_pass = not missing
    resource_pass = 0 < peak <= 1 * 1024**3
    execution_pass = result.get("status") == "PASS" and result.get("generation") == "PASS"
    status = "PASS" if execution_pass and resource_pass and quality_pass else "FAIL"
    evidence = {
        "schema": "LOUKSNAPG2_DOCLING_Q4_FUNCTIONAL_EVIDENCE/1.0",
        "generated_at_utc": utc_now(),
        "source_model": {"id": MODEL_ID, "revision": MODEL_REVISION, "sha256": SOURCE_WEIGHT_SHA256},
        "candidate_id": result.get("candidate_id", CANDIDATE_ID),
        "test": {
            "fixture_sha256": sha256_file(args.image),
            "fixture_bytes": args.image.stat().st_size,
            "expected_fields": list(EXPECTED_FIELDS),
            "observed_words": sorted(words),
            "missing_fields": missing,
            "output_text": result.get("output_text", ""),
            "output_sha256": result.get("output_sha256"),
            "semantic_quality_pass": quality_pass,
        },
        "execution": result,
        "resource_budget": {
            "candidate_memory_limit_bytes": 1 * 1024**3,
            "candidate_cpu_limit": 1,
            "peak_rss_bytes": peak,
            "measured_process_peak_within_budget": resource_pass,
        },
        "status": status,
        "promotion": "NOT_AUTHORIZED",
        "global_certification": "NOT_GRANTED",
    }
    write_json(args.report, evidence)
    print(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if status == "PASS" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    sub = parser.add_subparsers(dest="mode")
    build_parser = sub.add_parser("build")
    build_parser.add_argument("--base-candidate", required=True, type=Path)
    build_parser.add_argument("--output-dir", required=True, type=Path)
    eval_parser = sub.add_parser("evaluate")
    eval_parser.add_argument("--repo-root", required=True, type=Path)
    eval_parser.add_argument("--candidate-dir", required=True, type=Path)
    eval_parser.add_argument("--image", required=True, type=Path)
    eval_parser.add_argument("--report", required=True, type=Path)
    eval_parser.add_argument("--max-new-tokens", type=int, default=256)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.mode == "build":
        return build(args)
    if args.mode == "evaluate":
        return evaluate(args)
    parser.error("select build or evaluate")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
