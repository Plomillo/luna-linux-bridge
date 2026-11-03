#!/usr/bin/env python3
"""Build and evaluate a source-bound, groupwise INT4 Granite Docling candidate.

Build is constrained by the caller to 3 GiB RAM / 1 CPU. Evaluation uses an explicit
8-GiB / four-thread budget on the remote runner. Source weights are immutable; no
candidate is promoted unless invoice extraction passes the exact semantic predicate.
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
GROUP_SIZE = 256
WEIGHT_HARD_CAP_BYTES = 114_000_000
GLOBAL_RELEASE_MAX_BYTES = 490_000_000
BASELINE_RELEASE_BYTES = 371_986_537
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
    teacher_dir = args.output_dir / "teacher"
    teacher_dir.mkdir(parents=True, exist_ok=True)
    teacher_sidecar = teacher_dir / "model.safetensors"
    shutil.copy2(source_weight, teacher_sidecar)
    if teacher_sidecar.stat().st_size != SOURCE_WEIGHT_BYTES or sha256_file(teacher_sidecar) != SOURCE_WEIGHT_SHA256:
        raise RuntimeError("ORIGINAL_TEACHER_SIDECAR_IDENTITY_MISMATCH")
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
        "paired_evaluation_teacher_sidecar": {
            "path": "teacher/model.safetensors",
            "bytes": SOURCE_WEIGHT_BYTES,
            "sha256": SOURCE_WEIGHT_SHA256,
            "role": "EVALUATION_ONLY_NOT_PART_OF_CANDIDATE_PACKAGE",
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
        "evaluation_ram_limit_bytes": 3 * 1024**3,
        "promotion": "NOT_AUTHORIZED",
    }
    write_json(args.output_dir / "repair_build_report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


def _run_runtime_protocol(runtime_path: Path, candidate_dir: Path, image: Path,
                           max_new_tokens: int, prompt: str, teacher_weights: Path | None,
                           timeout_seconds: int) -> dict:
    import subprocess

    payload = json.dumps({
        "operation": "extract_document_image",
        "max_new_tokens": max_new_tokens,
        "image_path": str(image),
        "prompt": prompt,
    })
    command = [
        sys.executable, "-B", str(runtime_path),
        "--candidate-dir", str(candidate_dir),
        "--task-json-stdin",
    ]
    if teacher_weights is not None:
        command.extend(["--teacher-weights", str(teacher_weights)])
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PYTHONNOUSERSITE": "1",
        "LOUKSNAPG2_DOCLING_IMAGE_SIDE": os.environ.get("LOUKSNAPG2_DOCLING_IMAGE_SIDE", "512"),
        "LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES": os.environ.get("LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES", str(3 * 1024**3)),
        "LOUKSNAPG2_DOCLING_CPU_THREADS": os.environ.get("LOUKSNAPG2_DOCLING_CPU_THREADS", "1"),
    })
    try:
        completed = subprocess.run(
            command, input=payload, text=True, capture_output=True,
            timeout=timeout_seconds, check=False, env=env,
        )
    except subprocess.TimeoutExpired as exc:
        def partial_text(value) -> str:
            if value is None:
                return ""
            if isinstance(value, bytes):
                return value.decode("utf-8", errors="replace")
            return str(value)

        partial_stdout = partial_text(getattr(exc, "stdout", None) or getattr(exc, "output", None))
        partial_stderr = partial_text(getattr(exc, "stderr", None))
        stage_markers = [
            line for line in partial_stderr.splitlines()
            if line.startswith("LOUKSNAPG2_DOCLING_STAGE=")
        ]
        return {
            "status": "FAIL_TIMEOUT",
            "process_return_code": None,
            "timeout_seconds": timeout_seconds,
            "partial_stdout_tail": partial_stdout[-4000:],
            "partial_stderr_tail": partial_stderr[-12000:],
            "partial_stdout_sha256": hashlib.sha256(partial_stdout.encode("utf-8")).hexdigest(),
            "partial_stderr_sha256": hashlib.sha256(partial_stderr.encode("utf-8")).hexdigest(),
            "runtime_stage_markers": stage_markers[-20:],
            "stderr_sha256": hashlib.sha256(partial_stderr.encode("utf-8")).hexdigest(),
            "output_text": "",
        }
    stderr_text = completed.stderr or ""
    try:
        result = json.loads(completed.stdout)
    except json.JSONDecodeError:
        result = {
            "status": "FAIL_RUNTIME",
            "return_code": completed.returncode,
            "stdout_tail": completed.stdout[-4000:],
            "stderr_tail": stderr_text[-12000:],
            "stderr_sha256": hashlib.sha256(stderr_text.encode("utf-8", errors="replace")).hexdigest(),
            "output_text": "",
        }
    result["process_return_code"] = completed.returncode
    result["runtime_stderr_tail"] = stderr_text[-12000:]
    result["runtime_stderr_sha256"] = hashlib.sha256(stderr_text.encode("utf-8", errors="replace")).hexdigest()
    result["runtime_stage_markers"] = [
        line for line in stderr_text.splitlines()
        if line.startswith("LOUKSNAPG2_DOCLING_STAGE=")
    ][-20:]
    if completed.returncode != 0 and result.get("status") == "PASS":
        result["status"] = "FAIL_RUNTIME_EXIT"
    return result


def evaluate(args: argparse.Namespace) -> int:
    runtime_path = args.repo_root / RUNTIME_REL
    if not runtime_path.is_file():
        raise RuntimeError("DOCILING_RUNTIME_NOT_FOUND:" + str(runtime_path))
    teacher_raw = Path(args.teacher_weights)
    if teacher_raw.is_symlink() or not teacher_raw.is_file():
        raise RuntimeError("ORIGINAL_TEACHER_SIDECAR_MISSING_OR_SYMLINK")
    teacher_weights = teacher_raw.resolve(strict=True)
    teacher_bytes = teacher_weights.stat().st_size
    teacher_sha = sha256_file(teacher_weights)
    if teacher_bytes != SOURCE_WEIGHT_BYTES or teacher_sha != SOURCE_WEIGHT_SHA256:
        raise RuntimeError("ORIGINAL_TEACHER_SIDECAR_IDENTITY_MISMATCH:" + teacher_sha)

    # Sequential subprocesses ensure that the two model copies never coexist in RAM.
    # Both use the same local processor/config/generation files, image, prompt,
    # input geometry, token budget, CPU quota and 8-GiB cgroup.
    q4_result = _run_runtime_protocol(
        runtime_path, args.candidate_dir, args.image, args.max_new_tokens,
        PROMPT, None, args.timeout_seconds,
    )
    teacher_result = _run_runtime_protocol(
        runtime_path, args.candidate_dir, args.image, args.max_new_tokens,
        PROMPT, teacher_weights, args.timeout_seconds,
    )

    def predicate(result: dict) -> dict:
        words = set(re.findall(r"[a-z0-9]+", str(result.get("output_text", "")).casefold()))
        missing = [word for word in EXPECTED_FIELDS if word not in words]
        peak = int(result.get("peak_rss_bytes", 0))
        execution_pass = result.get("status") == "PASS" and result.get("generation") == "PASS" and result.get("process_return_code") == 0
        budget = int(result.get("ram_budget_bytes", 3 * 1024**3))
        resource_pass = 0 < peak <= budget
        return {
            "observed_words": sorted(words),
            "missing_fields": missing,
            "semantic_quality_pass": not missing,
            "execution_pass": execution_pass,
            "resource_pass": resource_pass,
            "peak_rss_bytes": peak,
            "output_text": result.get("output_text", ""),
            "output_sha256": result.get("output_sha256"),
            "candidate_id": result.get("candidate_id"),
            "model_source": result.get("model_source"),
            "model_dtype": result.get("model_dtype"),
            "execution_status": "PASS_EXECUTION" if execution_pass else str(result.get("status", "FAIL")),
            "timeout_seconds": result.get("timeout_seconds"),
            "runtime_stage_markers": result.get("runtime_stage_markers", []),
            "runtime_stderr_tail": result.get("runtime_stderr_tail", result.get("partial_stderr_tail", "")),
            "runtime_stderr_sha256": result.get("runtime_stderr_sha256", result.get("partial_stderr_sha256")),
        }

    q4 = predicate(q4_result)
    teacher = predicate(teacher_result)
    comparable = (
        q4_result.get("image_side_pixels") == teacher_result.get("image_side_pixels")
        == int(os.environ.get("LOUKSNAPG2_DOCLING_IMAGE_SIDE", "512"))
        and q4_result.get("image_sequence_length") == teacher_result.get("image_sequence_length")
        and q4_result.get("processor_load") == teacher_result.get("processor_load") == "PASS"
        and q4_result.get("image_preprocess") == teacher_result.get("image_preprocess") == "PASS"
        and q4_result.get("generation") == teacher_result.get("generation") == "PASS"
    )
    if teacher["semantic_quality_pass"] and not q4["semantic_quality_pass"]:
        diagnosis = "Q4_WEIGHT_RECONSTRUCTION_OR_QUANTIZATION_FAILURE_SUPPORTED"
    elif not teacher["semantic_quality_pass"] and not q4["semantic_quality_pass"] and comparable:
        diagnosis = "SHARED_RUNTIME_PROCESSOR_IMAGE_OR_PROMPT_PATH_REMAINS_SUSPECT"
    elif teacher["semantic_quality_pass"] and q4["semantic_quality_pass"]:
        diagnosis = "BOTH_SEMANTICALLY_PASS; Q4_QUALITY_REQUIRES_BROADER_HELD_OUT_VALIDATION"
    else:
        diagnosis = "INCONCLUSIVE_OR_PROTOCOL_MISMATCH"

    fixture_sha = sha256_file(args.image)
    status = "PASS" if (
        comparable and q4["semantic_quality_pass"] and teacher["semantic_quality_pass"]
        and q4["execution_pass"] and teacher["execution_pass"]
        and q4["resource_pass"] and teacher["resource_pass"]
    ) else "FAIL"
    evidence = {
        "schema": "LOUKSNAPG2_DOCLING_Q4_PAIRED_SOURCE_EVALUATION/2.0",
        "generated_at_utc": utc_now(),
        "source_model": {
            "id": MODEL_ID, "revision": MODEL_REVISION,
            "weights_bytes": SOURCE_WEIGHT_BYTES, "weights_sha256": SOURCE_WEIGHT_SHA256,
        },
        "candidate_id": CANDIDATE_ID,
        "paired_protocol": {
            "fixture_sha256": fixture_sha,
            "fixture_bytes": args.image.stat().st_size,
            "prompt": PROMPT,
            "max_new_tokens": args.max_new_tokens,
            "image_side_pixels": int(q4_result.get("image_side_pixels", 0)),
            "image_sequence_length": q4_result.get("image_sequence_length"),
            "model_dtype": q4_result.get("model_dtype"),
            "image_splitting": False,
            "processor_and_generation_config_root": str(args.candidate_dir),
            "cpu_limit": int(os.environ.get("LOUKSNAPG2_DOCLING_CPU_THREADS", "1")),
            "memory_limit_bytes": int(os.environ.get("LOUKSNAPG2_DOCLING_RAM_BUDGET_BYTES", str(3 * 1024**3))),
            "runs_are_sequential_separate_processes": True,
            "same_fixture_and_generation_protocol": True,
            "teacher_sidecar_bytes": teacher_bytes,
            "teacher_sidecar_sha256": teacher_sha,
        },
        "teacher_source_bfloat16": teacher,
        "q4_reconstructed": q4,
        "protocol_comparable": comparable,
        "diagnostic_hypothesis": diagnosis,
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
    eval_parser.add_argument("--teacher-weights", required=True, type=Path)
    eval_parser.add_argument("--timeout-seconds", type=int, default=900)
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
