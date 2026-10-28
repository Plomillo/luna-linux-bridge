#!/usr/bin/env python3
"""Build/test a temporary raw-INT8 Whisper candidate, with no canonical mutation.

The build mode downloads only a hash-pinned public Whisper reference into the
GitHub-hosted runner, factorizes it under a measured 40,000,000-byte module cap,
then exercises the current task adapter against synthetic and real read speech.
Only if both task checks pass does it emit a promotion tarball. Verify mode reruns
the exact tests against an already committed candidate SHA.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import math
import os
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time
import wave
from pathlib import Path

SOURCE_REPO = "openai/whisper-large-v3-turbo"
SOURCE_REVISION = "7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7"
SOURCE_MODEL_SHA256 = "542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1"
DATASET_REPO = "hf-internal-testing/librispeech_asr_dummy"
DATASET_REVISION = "5be91486e11a2d616f4ec5db8d3fd248585ac07a"
DATASET_PARQUET_SHA256 = "4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603"
REAL_AUDIO_ID = "1272-128104-0000"
REAL_WER_MAX = 0.25
TARGET_BYTES = 40_000_000
RANK = 29
OVERSAMPLE = 8
BLOCK_ROWS = 64
CANDIDATE_ID = "CAJITA_LUNA_RUNTIME_V9_20261023_WHISPER_INT8_EXPERIMENT"
DOMAIN_PATH = "3. Transcripción"
WEIGHT_REL = f"{DOMAIN_PATH}/model.safetensors"
SIDECAR_REL = f"{WEIGHT_REL}.q4.json"
MANIFEST_REL = "CAJITA_RUNTIME_V1/weights_manifest.json"
ESSENTIAL_ROOT_FILES = (
    "cajita_runtime.py",
    "cajita_weight_materializer.py",
    "cajita_tokenizer_materializer.py",
    "cajita_task_adapters.py",
    "cajita_router.py",
    "cajita_target_adapters.py",
    "cajita_antiparalysis.py",
    "command_subdomain_routing.json",
    "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json",
    MANIFEST_REL,
)
PLACEHOLDER_DOMAINS = (
    "1. Cerebro",
    "2. Orquestación",
    "4. Traductor Inteligente",
    "5. Inteligencia documental",
    "6. Sistema Inteligente",
)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_json(path: Path, value: dict) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def ensure_hosted_runner() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise RuntimeError("WHISPER_FACTORISATION_REQUIRES_GITHUB_HOSTED_RUNNER")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise RuntimeError("SINGLE_THREAD_BUDGET_NOT_ENFORCED:" + name)


def peak_rss_bytes() -> int:
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def write_report(path: Path, report: dict) -> None:
    atomic_json(path, report)


def copy_runtime_skeleton(source: Path, destination: Path, *, include_whisper_weight: bool) -> None:
    source = Path(source).resolve(strict=True)
    destination = Path(destination)
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for relative in ESSENTIAL_ROOT_FILES:
        src = source / relative
        if not src.is_file() or src.is_symlink():
            raise RuntimeError("RUNTIME_SKELETON_FILE_MISSING_OR_UNSAFE:" + relative)
        dst = destination / relative
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        if digest_file(src) != digest_file(dst):
            raise RuntimeError("RUNTIME_SKELETON_COPY_HASH_MISMATCH:" + relative)

    module_source = source / DOMAIN_PATH
    if not module_source.is_dir() or module_source.is_symlink():
        raise RuntimeError("WHISPER_MODULE_DIRECTORY_MISSING")
    module_destination = destination / DOMAIN_PATH

    def ignore(directory: str, names: list[str]) -> set[str]:
        base = Path(directory)
        excluded = set()
        for name in names:
            candidate = base / name
            if name == "model.safetensors" and not (
                include_whisper_weight and base.resolve() == module_source.resolve()
            ):
                excluded.add(name)
            if name == "model.safetensors.q4.json" and not (
                include_whisper_weight and base.resolve() == module_source.resolve()
            ):
                excluded.add(name)
        return excluded

    shutil.copytree(module_source, module_destination, ignore=ignore, symlinks=False)

    # The tokenizer manifest is global and validates all registered gzip payloads,
    # even when executing only Whisper. Copy those small, hash-pinned assets without
    # copying or loading any of the other domain models.
    tokenizer_manifest_path = source / "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
    tokenizer_manifest = json.loads(tokenizer_manifest_path.read_text(encoding="utf-8"))
    for row in tokenizer_manifest.get("entries", []):
        if row.get("packed") is not True:
            continue
        rel = row.get("compressed_path")
        if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in Path(rel).parts:
            raise RuntimeError("TOKENIZER_COMPRESSED_PATH_UNSAFE")
        src = source / rel
        dst = destination / rel
        if src.is_symlink() or not src.is_file():
            raise RuntimeError("TOKENIZER_COMPRESSED_PAYLOAD_MISSING:" + rel)
        if src.stat().st_size != int(row.get("compressed_bytes", -1)) or digest_file(src) != row.get("compressed_sha256"):
            raise RuntimeError("TOKENIZER_COMPRESSED_PAYLOAD_IDENTITY_MISMATCH:" + rel)
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.is_file() or digest_file(dst) != row.get("compressed_sha256"):
            shutil.copy2(src, dst)
        if digest_file(dst) != row.get("compressed_sha256"):
            raise RuntimeError("TOKENIZER_COMPRESSED_COPY_HASH_MISMATCH:" + rel)

    if include_whisper_weight:
        weight = module_destination / "model.safetensors"
        if not weight.is_file() or weight.is_symlink():
            raise RuntimeError("COMMITTED_WHISPER_WEIGHT_MISSING")
    for relative in PLACEHOLDER_DOMAINS:
        (destination / relative).mkdir(parents=True, exist_ok=True)
    # Refuse any leftover Q2/Q4 sidecar in a build candidate.
    if not include_whisper_weight:
        (module_destination / "model.safetensors").unlink(missing_ok=True)
        (module_destination / "model.safetensors.q4.json").unlink(missing_ok=True)
    sys.path.insert(0, str(destination))


def make_synthetic_audio(path: Path) -> Path:
    executable = shutil.which("espeak-ng")
    if not executable:
        raise RuntimeError("ESPEAK_NG_REQUIRED_FOR_KNOWN_SPEECH_FIXTURE")
    subprocess.run(
        [executable, "-v", "en-us", "-s", "135", "-w", str(path), "hello world"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True, timeout=30,
    )
    with wave.open(str(path), "rb") as stream:
        if stream.getnframes() <= 0 or stream.getsampwidth() != 2 or stream.getnchannels() not in (1, 2):
            raise RuntimeError("ESPEAK_NG_FIXTURE_WAV_INVALID")
    return path


def make_int8_factors(source_model: Path, output_path: Path, rank: int) -> dict:
    import torch
    from safetensors import safe_open
    from safetensors.torch import save_file

    # Thread pools were already initialized by run_build; do not reconfigure
    # inter-op threading after model metadata or transfer libraries have run.
    if digest_file(source_model) != SOURCE_MODEL_SHA256:
        raise RuntimeError("SOURCE_WHISPER_SHA256_MISMATCH")
    with safe_open(str(source_model), framework="pt", device="cpu") as source:
        keys = sorted(source.keys())
        if len(keys) != 587:
            raise RuntimeError("WHISPER_SOURCE_TENSOR_COUNT_MISMATCH:" + str(len(keys)))
        records = []
        preserved_vectors = 0
        total_source_norm_sq = 0.0
        total_residual_sq = 0.0
        output = {}
        preserved = {"model.encoder.embed_positions.weight", "model.decoder.embed_positions.weight"}
        for index, key in enumerate(keys, 1):
            sl = source.get_slice(key)
            shape = tuple(sl.get_shape())
            if len(shape) in (2, 3) and not key.endswith(".weight"):
                raise RuntimeError("UNSUPPORTED_MATRIX_KEY:" + key)
            if len(shape) in (2, 3) and key not in preserved:
                m, n = shape[0], math.prod(shape[1:])
                qdim = min(rank + OVERSAMPLE, m, n)
                r = min(rank, m, n)
                seed = int.from_bytes(hashlib.sha256(key.encode()).digest()[:8], "little") & ((1 << 63) - 1)
                generator = torch.Generator(device="cpu")
                generator.manual_seed(seed)
                omega = torch.randn((n, qdim), generator=generator, dtype=torch.float32) / math.sqrt(qdim)
                y = torch.empty((m, qdim), dtype=torch.float32)
                norm_sq = 0.0
                for start in range(0, m, BLOCK_ROWS):
                    end = min(m, start + BLOCK_ROWS)
                    block = sl[start:end].to(torch.float32).reshape(end - start, n)
                    y[start:end] = block @ omega
                    norm_sq += float(torch.sum(block * block).item())
                qmat, _ = torch.linalg.qr(y, mode="reduced")
                bmat = torch.zeros((qdim, n), dtype=torch.float32)
                for start in range(0, m, BLOCK_ROWS):
                    end = min(m, start + BLOCK_ROWS)
                    block = sl[start:end].to(torch.float32).reshape(end - start, n)
                    bmat.add_(qmat[start:end].T @ block)
                ub, singular, vh = torch.linalg.svd(bmat, full_matrices=False)
                sigma = singular[:r].clamp_min(0)
                root_sigma = torch.sqrt(sigma)
                a = (qmat @ ub[:, :r]) * root_sigma.unsqueeze(0)
                b = root_sigma.unsqueeze(1) * vh[:r, :]
                scale_u = (a.abs().amax(dim=0) / 127.0).clamp_min(1e-12)
                scale_v = (b.abs().amax(dim=1) / 127.0).clamp_min(1e-12)
                uq = torch.round(a / scale_u.unsqueeze(0)).clamp(-127, 127).to(torch.int8).contiguous()
                vq = torch.round(b / scale_v.unsqueeze(1)).clamp(-127, 127).to(torch.int8).contiguous()
                uqf = uq.to(torch.float32) * scale_u.unsqueeze(0)
                vqf = vq.to(torch.float32) * scale_v.unsqueeze(1)
                residual_sq = 0.0
                for start in range(0, m, BLOCK_ROWS):
                    end = min(m, start + BLOCK_ROWS)
                    block = sl[start:end].to(torch.float32).reshape(end - start, n)
                    approx = uqf[start:end] @ vqf
                    residual = block - approx
                    residual_sq += float(torch.sum(residual * residual).item())
                relative_error = math.sqrt(max(residual_sq, 0.0) / max(norm_sq, 1e-30))
                lowrank_residual = math.sqrt(max(norm_sq - float(torch.sum(sigma * sigma).item()), 0.0) / max(norm_sq, 1e-30))
                base = key[:-len(".weight")]
                output[base + ".weight_u"] = uq.cpu().contiguous()
                output[base + ".weight_v"] = vq.cpu().contiguous()
                output[base + ".scale_u"] = scale_u.cpu().to(torch.float32).contiguous()
                output[base + ".scale_v"] = scale_v.cpu().to(torch.float32).contiguous()
                total_source_norm_sq += norm_sq
                total_residual_sq += residual_sq
                records.append({
                    "tensor": key,
                    "shape": list(shape),
                    "rank": r,
                    "relative_frobenius_error_after_int8": relative_error,
                    "relative_residual_before_factor_quantization": lowrank_residual,
                    "factor_bytes": sum(x.numel() * x.element_size() for x in (
                        output[base + ".weight_u"], output[base + ".weight_v"],
                        output[base + ".scale_u"], output[base + ".scale_v"],
                    )),
                })
            elif len(shape) == 1 or key in preserved:
                if len(shape) == 1:
                    preserved_vectors += 1
                output[key] = sl[:].contiguous()
            else:
                raise RuntimeError("UNSUPPORTED_SOURCE_TENSOR_SHAPE:" + key + ":" + str(shape))

    # Whisper's output projection ties the decoder embedding weights.
    for suffix in ("weight_u", "weight_v", "scale_u", "scale_v"):
        source_key = "model.decoder.embed_tokens." + suffix
        target_key = "proj_out." + suffix
        if source_key not in output:
            raise RuntimeError("WHISPER_TIED_EMBEDDING_FACTOR_MISSING:" + source_key)
        output[target_key] = output[source_key].clone().contiguous()

    output_path.parent.mkdir(parents=True, exist_ok=True)
    temp = output_path.with_suffix(output_path.suffix + ".building")
    save_file(output, str(temp), metadata={
        "format": "pt",
        "source_model_id": SOURCE_REPO,
        "source_revision": SOURCE_REVISION,
        "source_model_sha256": SOURCE_MODEL_SHA256,
        "method": "randomized_truncated_svd_rank29_symmetric_int8_factors",
        "rank": str(rank),
        "quantization": "signed_int8_per_factor_with_fp32_scales",
        "promotion_status": "EXPERIMENTAL_NOT_CERTIFIED",
    })
    os.replace(temp, output_path)
    if digest_file(source_model) != SOURCE_MODEL_SHA256:
        raise RuntimeError("SOURCE_WHISPER_CHANGED_DURING_FACTORIZATION")
    return {
        "source_tensor_count": len(keys),
        "source_matrix_count_factorized": len(records),
        "source_vector_count_preserved": preserved_vectors,
        "position_embedding_tensors_preserved": sorted(preserved),
        "rank": rank,
        "oversample": OVERSAMPLE,
        "factor_dtype": "INT8",
        "factorization_error_aggregate": math.sqrt(total_residual_sq / max(total_source_norm_sq, 1e-30)),
        "factorization_tensor_count": len(records),
        "factorization_error_worst_10": sorted(
            [{"tensor": x["tensor"], "relative_frobenius_error_after_int8": x["relative_frobenius_error_after_int8"]}
             for x in records],
            key=lambda x: x["relative_frobenius_error_after_int8"], reverse=True,
        )[:10],
        "raw_factor_safetensors_sha256": digest_file(output_path),
        "raw_factor_safetensors_bytes": output_path.stat().st_size,
    }


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalized_words(reference), normalized_words(hypothesis)
    if not ref:
        raise ValueError("WER_REFERENCE_EMPTY")
    prev = list(range(len(hyp) + 1))
    for i, rword in enumerate(ref, 1):
        curr = [i]
        for j, hword in enumerate(hyp, 1):
            curr.append(min(
                curr[-1] + 1,
                prev[j] + 1,
                prev[j - 1] + (rword != hword),
            ))
        prev = curr
    return prev[-1] / len(ref)


def run_runtime_task(runtime_root: Path, case_dir: Path, *, task_id: str, audio_path: Path,
                     max_new_tokens: int, expected_words: tuple[str, ...] | None = None,
                     reference_text: str | None = None) -> dict:
    runtime_root = Path(runtime_root).resolve()
    case_dir.mkdir(parents=True, exist_ok=True)
    request = {
        "schema": "CAJITA_TASK_REQUEST/1.0",
        "task_id": task_id,
        "domain_id": "D03_TRANSCRIPCION",
        "operation": "transcribe_audio",
        "input": {"audio_path": str(Path(audio_path).resolve())},
        "limits": {"timeout_seconds": 900, "max_new_tokens": max_new_tokens},
    }
    request_path = case_dir / (task_id + ".request.json")
    request_path.write_text(json.dumps(request, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    env = {k: os.environ[k] for k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "WINDIR") if k in os.environ}
    env.update({
        "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "PYTHONNOUSERSITE": "1",
        "CAJITA_E2E_DIAGNOSTICS": "1",
    })
    start = time.monotonic()
    command = [
        sys.executable, str(runtime_root / "cajita_runtime.py"), "execute-task",
        "--root", str(runtime_root), "--request-json", str(request_path), "--timeout", "900",
    ]
    proc = subprocess.run(command, cwd=str(runtime_root), env=env, text=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=930, check=False)
    try:
        response = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        response = {}
    text = response.get("output_text", "") if isinstance(response, dict) else ""
    words = normalized_words(text)
    result = {
        "task_id": task_id,
        "candidate_runtime_root": str(runtime_root),
        "exit_code": proc.returncode,
        "status": response.get("status", "NO_JSON_RESULT") if isinstance(response, dict) else "NO_JSON_RESULT",
        "target_id": response.get("target_id") if isinstance(response, dict) else None,
        "operation": response.get("operation") if isinstance(response, dict) else None,
        "output_text_sha256": digest_bytes(str(text).encode("utf-8", errors="replace")),
        "output_char_count": len(str(text)),
        "output_word_count": len(words),
        "peak_rss_bytes": response.get("peak_rss_bytes") if isinstance(response, dict) else None,
        "elapsed_seconds": round(time.monotonic() - start, 3),
        "stderr_sha256": digest_bytes(proc.stderr.encode("utf-8", errors="replace")),
        "semantic_equivalence": "NOT_ESTABLISHED",
    }
    if proc.returncode != 0:
        result["failure_code"] = response.get("reason", "TASK_RUNTIME_NONZERO_EXIT") if isinstance(response, dict) else "TASK_RUNTIME_NO_JSON"
        result["diagnostic_stderr_tail"] = proc.stderr[-2000:]
        return result
    if response.get("status") != "PASS_FUNCTIONAL_EXECUTION" or not isinstance(text, str) or not text.strip():
        result["failure_code"] = "TASK_RESULT_STATUS_OR_OUTPUT_INVALID"
        return result
    if expected_words is not None:
        missing = [phrase for phrase in expected_words if phrase not in words]
        result["quality_check"] = {
            "check_id": "synthetic-known-hello-world",
            "kind": "SYNTHETIC_KNOWN_ANSWER",
            "status": "PASS" if not missing else "FAIL",
            "expected_words": list(expected_words),
            "missing_words": missing,
        }
    if reference_text is not None:
        wer = word_error_rate(reference_text, text)
        result["quality_check"] = {
            "check_id": "librispeech-real-speech-transcript",
            "kind": "REAL_PUBLIC_RECORDED_SPEECH",
            "wer": round(wer, 6),
            "wer_limit": REAL_WER_MAX,
            "reference_word_count": len(normalized_words(reference_text)),
            "status": "PASS" if wer <= REAL_WER_MAX else "FAIL",
            "dataset_repo": DATASET_REPO,
            "dataset_revision": DATASET_REVISION,
            "audio_id": REAL_AUDIO_ID,
        }
    result["task_pass"] = result.get("quality_check", {}).get("status") == "PASS"
    return result


def get_librispeech_fixture(work_dir: Path) -> tuple[Path, str, dict]:
    from datasets import Audio, load_dataset
    from huggingface_hub import hf_hub_download
    import numpy as np
    import soundfile as sf

    parquet = Path(hf_hub_download(
        repo_id=DATASET_REPO,
        filename="clean/validation-00000-of-00001.parquet",
        repo_type="dataset",
        revision=DATASET_REVISION,
    ))
    observed_parquet_sha = digest_file(parquet)
    if observed_parquet_sha != DATASET_PARQUET_SHA256:
        raise RuntimeError("PINNED_LIBRISPEECH_PARQUET_SHA256_MISMATCH:" + observed_parquet_sha)
    dataset = load_dataset("parquet", data_files={"validation": str(parquet)}, split="validation")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=16000, decode=False))
    row = next((x for x in dataset if x.get("id") == REAL_AUDIO_ID), None)
    if row is None:
        raise RuntimeError("PINNED_LIBRISPEECH_SAMPLE_ID_NOT_FOUND")
    raw_audio = row["audio"]
    data = raw_audio.get("bytes")
    if data is None:
        audio_path = raw_audio.get("path")
        if not audio_path:
            raise RuntimeError("LIBRISPEECH_AUDIO_BYTES_OR_PATH_MISSING")
        with open(audio_path, "rb") as stream:
            data = stream.read()
    audio_sha = digest_bytes(data)
    audio, sample_rate = sf.read(io.BytesIO(data), dtype="float32", always_2d=False)
    if getattr(audio, "ndim", 0) == 2:
        audio = audio.mean(axis=1, dtype=np.float32)
    if int(sample_rate) != 16000:
        raise RuntimeError("LIBRISPEECH_SAMPLE_RATE_MISMATCH:" + str(sample_rate))
    if len(audio) < 16000 or not np.isfinite(audio).all():
        raise RuntimeError("LIBRISPEECH_AUDIO_INVALID")
    audio = np.clip(audio, -1.0, 0.999969).astype(np.float32, copy=False)
    pcm = (audio * 32768.0).round().astype("<i2")
    output = work_dir / "librispeech-known-transcript.wav"
    output.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(16000)
        stream.writeframes(pcm.tobytes())
    transcript = str(row["text"])
    info = {
        "repo": DATASET_REPO,
        "revision": DATASET_REVISION,
        "expected_parquet_sha256": DATASET_PARQUET_SHA256,
        "observed_parquet_sha256": observed_parquet_sha,
        "sample_id": REAL_AUDIO_ID,
        "audio_asset_sha256": audio_sha,
        "audio_wav_sha256": digest_file(output),
        "audio_wav_bytes": output.stat().st_size,
        "sample_rate_hz": 16000,
        "audio_duration_seconds": round(len(audio) / 16000, 3),
        "transcript_sha256": digest_bytes(transcript.encode("utf-8")),
        "transcript_word_count": len(normalized_words(transcript)),
    }
    return output, transcript, info


def prepare_metadata(runtime_root: Path, candidate_weight: Path, factor_metrics: dict) -> dict:
    root = Path(runtime_root)
    module = root / DOMAIN_PATH
    weight_in_module = module / "model.safetensors"
    if candidate_weight.resolve() != weight_in_module.resolve():
        shutil.copy2(candidate_weight, weight_in_module)
    (module / "model.safetensors.q4.json").unlink(missing_ok=True)
    weight_sha = digest_file(weight_in_module)
    weight_bytes = weight_in_module.stat().st_size

    compression_path = module / "compression_metadata.json"
    compression = json.loads(compression_path.read_text(encoding="utf-8"))
    compression.update({
        "method": "randomized_truncated_svd_low_rank_factorization_plus_symmetric_INT8_factor_quantization",
        "rank": RANK,
        "oversample": OVERSAMPLE,
        "target_bytes": TARGET_BYTES,
        "candidate_weight_sha256": weight_sha,
        "candidate_weight_bytes": weight_bytes,
        "actual_secondary_factor_packing": "NONE_RAW_INT8_FACTORS",
        "q2_sidecar_removed": True,
        "factorization_evidence": factor_metrics,
        "quality_equivalence": "PENDING_TWO_TASK_EXPERIMENT",
        "certification": "NOT_GRANTED",
    })
    atomic_json(compression_path, compression)

    manifest_path = root / MANIFEST_REL
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["candidate_id"] = CANDIDATE_ID
    for artifact in manifest.get("artifacts", []):
        if artifact.get("path") == WEIGHT_REL:
            artifact["bytes"] = weight_bytes
            artifact["sha256"] = weight_sha
            artifact["representation"] = "Whisper rank-29 raw signed INT8 low-rank factors; experimental"
            artifact["presence"] = "VERIFIED"
            break
    else:
        raise RuntimeError("WHISPER_WEIGHT_MANIFEST_ENTRY_MISSING")
    manifest["total_weight_bytes"] = sum(int(row["bytes"]) for row in manifest["artifacts"])
    manifest["total_weight_decimal_mb"] = round(manifest["total_weight_bytes"] / 1_000_000, 3)
    manifest["functional_equivalence"] = "PENDING_TWO_TASK_EXPERIMENT"
    manifest["certification"] = "NOT_GRANTED"
    atomic_json(manifest_path, manifest)
    manifest_sha = digest_file(manifest_path)

    runtime_path = root / "cajita_runtime.py"
    runtime_text = runtime_path.read_text(encoding="utf-8")
    runtime_text = re.sub(r'(?m)^CANDIDATE_ID = ".*"$', f'CANDIDATE_ID = "{CANDIDATE_ID}"', runtime_text)
    runtime_text = re.sub(r'(?m)^MANIFEST_SHA256 = ".*"$', f'MANIFEST_SHA256 = "{manifest_sha}"', runtime_text)
    runtime_path.write_text(runtime_text, encoding="utf-8")

    adapter_path = root / "cajita_task_adapters.py"
    adapter_text = adapter_path.read_text(encoding="utf-8")
    adapter_text = re.sub(r'(?m)^MANIFEST_SHA = ".*"$', f'MANIFEST_SHA = "{manifest_sha}"', adapter_text)
    adapter_text = re.sub(r'(?m)^CANDIDATE_ID = ".*"$', f'CANDIDATE_ID = "{CANDIDATE_ID}"', adapter_text)
    old_adapter_line = next((line for line in adapter_text.splitlines() if '"D03_TRANSCRIPCION": {' in line), None)
    if old_adapter_line is None:
        raise RuntimeError("WHISPER_TASK_ADAPTER_ROW_MISSING")
    new_adapter_line = (
        ' "D03_TRANSCRIPCION": {"weight":"3. Transcripción/model.safetensors",'
        f'"sha":"{weight_sha}","bytes":{weight_bytes},'
        '"module":"3. Transcripción","target":"D03_TRANSCRIPCION_ROOT",'
        '"entry":"3. Transcripción/lowrank_runtime.py","op":"transcribe_audio",'
        '"id":"CAJITA_WHISPER_TRANSCRIPTION/1.0","tokens":8},'
    )
    adapter_text = adapter_text.replace(old_adapter_line, new_adapter_line, 1)
    adapter_path.write_text(adapter_text, encoding="utf-8")
    adapter_sha = digest_file(adapter_path)

    descriptor_path = module / "CAJITA_MODULE.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    registration = descriptor.get("consumer_adapter_registration", {})
    registration.update({
        "adapter_source_sha256": adapter_sha,
        "certification": "NOT_GRANTED",
        "native_smoke": "PENDING",
        "reference_quality_equivalence": "PENDING_TWO_TASK_EXPERIMENT",
        "status": "REGISTERED_EXPERIMENTAL_INT8_CANDIDATE",
        "test_scope": "SYNTHETIC_AND_REAL_PUBLIC_SPEECH_EXPERIMENT",
        "weight_bytes": weight_bytes,
        "weight_manifest_sha256": manifest_sha,
        "weight_sha256": weight_sha,
    })
    descriptor["consumer_adapter_registration"] = registration
    descriptor["certification"] = "NOT_GRANTED"
    descriptor["functional_state"] = "EXPERIMENTAL_INT8_CANDIDATE_QUALITY_GATE_PENDING"
    atomic_json(descriptor_path, descriptor)

    # Compute the canonical module tree with lossless tokenizer reconstruction.
    sys.path.insert(0, str(root))
    import importlib
    import cajita_task_adapters
    importlib.reload(cajita_task_adapters)
    rows = cajita_task_adapters.tree_rows(module)
    rows = cajita_task_adapters.tokenizer_tree_rows(module, root, rows)
    descriptor["tree_integrity"] = {
        "bytes_excluding_module_descriptors": sum(int(row["bytes"]) for row in rows),
        "file_count_excluding_module_descriptors": len(rows),
        "sha256": digest_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")),
    }
    atomic_json(descriptor_path, descriptor)
    return {
        "candidate_id": CANDIDATE_ID,
        "weight_sha256": weight_sha,
        "weight_bytes": weight_bytes,
        "weight_manifest_sha256": manifest_sha,
        "module_tree_sha256": descriptor["tree_integrity"]["sha256"],
        "module_tree_bytes_excluding_descriptor": descriptor["tree_integrity"]["bytes_excluding_module_descriptors"],
        "module_tree_file_count_excluding_descriptor": descriptor["tree_integrity"]["file_count_excluding_module_descriptors"],
        "module_directory_bytes_including_descriptor": sum(p.stat().st_size for p in module.rglob("*") if p.is_file()),
        "adapter_source_sha256": adapter_sha,
    }


def assert_temp_runtime_integrity(runtime_root: Path) -> dict:
    root = Path(runtime_root)
    sys.path.insert(0, str(root))
    import importlib
    import cajita_task_adapters
    importlib.reload(cajita_task_adapters)
    result = cajita_task_adapters.verify_integrity(root, "D03_TRANSCRIPCION")
    expected = json.loads((root / DOMAIN_PATH / "compression_metadata.json").read_text(encoding="utf-8"))
    if result["weight_sha256"] != expected.get("candidate_weight_sha256"):
        raise RuntimeError("TEMP_CANDIDATE_METADATA_SHA_BINDING_MISMATCH")
    if result["weight_bytes"] != expected.get("candidate_weight_bytes"):
        raise RuntimeError("TEMP_CANDIDATE_METADATA_SIZE_BINDING_MISMATCH")
    return result


def build_promotion_tar(runtime_root: Path, repo_root: Path, report_path: Path, promotion_tar: Path) -> None:
    runtime_root = Path(runtime_root)
    repo_root = Path(repo_root)
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    evidence_rel = Path("evidence/louksnapg") / f"whisper-int8-prepromotion-{run_id}.json"
    tar_path = Path(promotion_tar)
    tar_path.parent.mkdir(parents=True, exist_ok=True)
    source_dest_pairs = [
        (runtime_root / "cajita_runtime.py", "cajita-luna-runtime/cajita_runtime.py"),
        (runtime_root / "cajita_task_adapters.py", "cajita-luna-runtime/cajita_task_adapters.py"),
        (runtime_root / MANIFEST_REL, f"cajita-luna-runtime/{MANIFEST_REL}"),
        (runtime_root / DOMAIN_PATH / "model.safetensors", f"cajita-luna-runtime/{WEIGHT_REL}"),
        (runtime_root / DOMAIN_PATH / "compression_metadata.json", f"cajita-luna-runtime/{DOMAIN_PATH}/compression_metadata.json"),
        (runtime_root / DOMAIN_PATH / "CAJITA_MODULE.json", f"cajita-luna-runtime/{DOMAIN_PATH}/CAJITA_MODULE.json"),
    ]
    payload = {
        "schema": "LOUKSNAPG_WHISPER_INT8_PROMOTION_PAYLOAD/1.0",
        "candidate_id": CANDIDATE_ID,
        "source_commit": subprocess.run(["git", "-C", str(repo_root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip(),
        "weight_sha256": digest_file(runtime_root / DOMAIN_PATH / "model.safetensors"),
        "weight_bytes": (runtime_root / DOMAIN_PATH / "model.safetensors").stat().st_size,
        "delete_paths": [f"cajita-luna-runtime/{SIDECAR_REL}"],
        "evidence_path": evidence_rel.as_posix(),
        "global_certification": "NOT_GRANTED",
    }
    payload["files"] = [
        {"path": rel, "bytes": src.stat().st_size, "sha256": digest_file(src)}
        for src, rel in source_dest_pairs
    ]
    atomic_json(Path(report_path), json.loads(Path(report_path).read_text(encoding="utf-8")) | {"promotion_payload": payload})
    evidence_src = Path(report_path)
    with tarfile.open(tar_path, "w:gz") as archive:
        for src, relative in source_dest_pairs:
            archive.add(src, arcname=relative, recursive=False)
        archive.add(evidence_src, arcname=evidence_rel.as_posix(), recursive=False)
        marker = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8") + b"\n"
        info = tarfile.TarInfo("LOUKSNAPG_WHISPER_INT8_PROMOTION_MANIFEST.json")
        info.size = len(marker)
        info.mode = 0o600
        import io as _io
        archive.addfile(info, _io.BytesIO(marker))


def run_tests(runtime_root: Path, work_dir: Path) -> tuple[list[dict], dict]:
    synthetic = work_dir / "synthetic-hello-world.wav"
    make_synthetic_audio(synthetic)
    real_audio, real_text, dataset_metadata = get_librispeech_fixture(work_dir)
    cases_dir = work_dir / "task-results"
    hello_result = run_runtime_task(
        runtime_root, cases_dir, task_id="whisper-int8-hello-world",
        audio_path=synthetic, max_new_tokens=12, expected_words=("hello", "world"),
    )
    real_result = run_runtime_task(
        runtime_root, cases_dir, task_id="whisper-int8-librispeech-1272-128104-0000",
        audio_path=real_audio, max_new_tokens=128, reference_text=real_text,
    )
    report = {
        "synthetic_audio_sha256": digest_file(synthetic),
        "synthetic_audio_bytes": synthetic.stat().st_size,
        "librispeech_fixture": dataset_metadata,
        "task_results": [hello_result, real_result],
    }
    return [hello_result, real_result], report


def run_build(args) -> int:
    import torch
    from huggingface_hub import snapshot_download

    ensure_hosted_runner()
    torch.set_num_threads(1)
    torch.set_num_interop_threads(1)
    source_checkout = Path(args.repo_runtime_root).resolve(strict=True)
    source_model_dir = Path(args.work_dir).resolve() / "upstream-whisper"
    source_model_dir.mkdir(parents=True, exist_ok=True)
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    source_dir = Path(snapshot_download(
        repo_id=SOURCE_REPO,
        revision=SOURCE_REVISION,
        repo_type="model",
        local_dir=str(source_model_dir),
        allow_patterns=["model.safetensors"],
        max_workers=1,
    ))
    source_weights = source_dir / "model.safetensors"
    if not source_weights.is_file():
        raise RuntimeError("PINNED_UPSTREAM_WHISPER_WEIGHTS_MISSING")
    if digest_file(source_weights) != SOURCE_MODEL_SHA256:
        raise RuntimeError("PINNED_UPSTREAM_WHISPER_SHA256_MISMATCH")

    runtime_root = work / "experimental-runtime"
    copy_runtime_skeleton(source_checkout, runtime_root, include_whisper_weight=False)
    t0 = time.monotonic()
    candidate_weight = runtime_root / DOMAIN_PATH / "model.safetensors"
    factor_metrics = make_int8_factors(source_weights, candidate_weight, RANK)
    metadata = prepare_metadata(runtime_root, candidate_weight, factor_metrics)
    actual_module_bytes = metadata["module_directory_bytes_including_descriptor"]
    report = {
        "schema": "LOUKSNAPG_WHISPER_INT8_REPAIR_EXPERIMENT/1.0",
        "status": "IN_PROGRESS",
        "started_at_utc": utc_now(),
        "source_commit": subprocess.run(["git", "-C", str(source_checkout.parent), "rev-parse", "HEAD"],
                                        check=False, capture_output=True, text=True).stdout.strip() or "UNKNOWN",
        "execution_environment": "GITHUB_HOSTED_UBUNTU_CPU",
        "threads": 1,
        "local_pc_inference": False,
        "canonical_runtime_mutated": False,
        "source_model": {
            "repo": SOURCE_REPO, "revision": SOURCE_REVISION,
            "expected_sha256": SOURCE_MODEL_SHA256, "observed_sha256": digest_file(source_weights),
            "bytes": source_weights.stat().st_size,
        },
        "compression_method_before": "INT8_FACTOR_METADATA_WITH_SECONDARY_UNSIGNED_INT2_PACKING",
        "compression_method_experiment": "RAW_SIGNED_INT8_FACTORS_WITH_FP32_SCALES_NO_SECONDARY_Q2_Q4_SIDECAR",
        "rank": RANK,
        "target_bytes": TARGET_BYTES,
        "candidate_weight_sha256": metadata["weight_sha256"],
        "candidate_weight_bytes": metadata["weight_bytes"],
        "candidate_module_bytes_including_descriptor": actual_module_bytes,
        "candidate_module_cap_pass": actual_module_bytes <= TARGET_BYTES,
        "module_integrity": assert_temp_runtime_integrity(runtime_root) if actual_module_bytes <= TARGET_BYTES else None,
        "factorization": factor_metrics,
        "metadata": metadata,
        "global_certification": "NOT_GRANTED",
        "promotion_performed": False,
    }
    if actual_module_bytes > TARGET_BYTES:
        report.update({
            "status": "FAIL_HARD_SIZE_CAP",
            "finished_at_utc": utc_now(),
            "elapsed_seconds": round(time.monotonic() - t0, 3),
            "peak_rss_bytes": peak_rss_bytes(),
            "conclusion": "Raw INT8 candidate exceeds the 40,000,000-byte module limit; no task execution or promotion.",
        })
        write_report(Path(args.report), report)
        return 2

    results, test_context = run_tests(runtime_root, work)
    report["task_results"] = results
    report["test_context"] = test_context
    all_pass = all(row.get("task_pass") is True for row in results)
    report.update({
        "status": "PASS_CANDIDATE_BUDGET_AND_TWO_TASKS" if all_pass else "FAIL_FUNCTIONAL_OR_QUALITY_GATE",
        "finished_at_utc": utc_now(),
        "elapsed_seconds": round(time.monotonic() - t0, 3),
        "peak_rss_bytes": peak_rss_bytes(),
        "global_certification": "NOT_GRANTED",
        "promotion_performed": False,
        "conclusion": (
            "Candidate satisfies the hard module cap and both task checks. It is eligible for branch promotion followed by exact-commit retest; this is not domain or global certification."
            if all_pass else
            "Candidate was not accepted. No promotion is authorized; inspect the failed test's exact status and WER."
        ),
    })
    report_path = Path(args.report)
    write_report(report_path, report)
    if not all_pass:
        return 2

    # The descriptor is still excluded from tree_integrity, so append status only
    # after the task run and keep the certification state denied.
    descriptor_path = runtime_root / DOMAIN_PATH / "CAJITA_MODULE.json"
    descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
    registration = descriptor["consumer_adapter_registration"]
    registration.update({
        "native_smoke": "PASS_HELLO_WORLD_AND_LIBRISPEECH_SAMPLE",
        "reference_quality_equivalence": "PARTIAL_KNOWN_ANSWER_TESTS_ONLY_NOT_FULL_EQUIVALENCE",
        "status": "PASS_TWO_TASK_EXPERIMENT_ONLY",
    })
    descriptor["consumer_adapter_registration"] = registration
    descriptor["functional_state"] = "EXPERIMENTAL_INT8_CANDIDATE_PASSES_TWO_TASKS_NOT_CERTIFIED"
    atomic_json(descriptor_path, descriptor)
    # Regenerate descriptor after status change; its own row is excluded from
    # tree_integrity, so this should remain exactly the same.
    if digest_bytes(json.dumps(
        (lambda rows: rows)(
            __import__("cajita_task_adapters").tokenizer_tree_rows(
                runtime_root / DOMAIN_PATH, runtime_root,
                __import__("cajita_task_adapters").tree_rows(runtime_root / DOMAIN_PATH),
            )
        ),
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")) != descriptor["tree_integrity"]["sha256"]:
        raise RuntimeError("MODULE_TREE_HASH_CHANGED_AFTER_EXPERIMENT_STATUS_UPDATE")

    write_report(report_path, report)
    build_promotion_tar(runtime_root, source_checkout, report_path, Path(args.promotion_tar))
    return 0


def run_verify(args) -> int:
    ensure_hosted_runner()
    repo_root = Path(args.repo_runtime_root).resolve(strict=True)
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    runtime_root = work / "verify-runtime"
    copy_runtime_skeleton(repo_root, runtime_root, include_whisper_weight=True)
    source_sha = subprocess.run(["git", "-C", str(repo_root.parent), "rev-parse", "HEAD"],
                                check=False, capture_output=True, text=True).stdout.strip() or "UNKNOWN"
    module = runtime_root / DOMAIN_PATH
    module_bytes = sum(p.stat().st_size for p in module.rglob("*") if p.is_file())
    metadata = json.loads((module / "compression_metadata.json").read_text(encoding="utf-8"))
    weight_sha = digest_file(module / "model.safetensors")
    if (module / "model.safetensors.q4.json").exists() or metadata.get("actual_secondary_factor_packing") != "NONE_RAW_INT8_FACTORS":
        raise RuntimeError("PROMOTED_WHISPER_CANDIDATE_IS_NOT_RAW_INT8")
    if module_bytes > TARGET_BYTES:
        raise RuntimeError("PROMOTED_WHISPER_CANDIDATE_EXCEEDS_HARD_CAP")
    integrity = assert_temp_runtime_integrity(runtime_root)
    t0 = time.monotonic()
    results, test_context = run_tests(runtime_root, work)
    passed = all(row.get("task_pass") is True for row in results)
    report = {
        "schema": "LOUKSNAPG_WHISPER_INT8_EXACT_COMMIT_VERIFICATION/1.0",
        "status": "PASS_EXACT_COMMIT_TWO_TASK_RETEST" if passed else "FAIL_EXACT_COMMIT_TWO_TASK_RETEST",
        "candidate_commit": source_sha,
        "verified_at_utc": utc_now(),
        "weight_sha256": weight_sha,
        "weight_bytes": (module / "model.safetensors").stat().st_size,
        "module_bytes_including_descriptor": module_bytes,
        "module_hard_cap_bytes": TARGET_BYTES,
        "module_cap_pass": module_bytes <= TARGET_BYTES,
        "module_integrity": integrity,
        "task_results": results,
        "test_context": test_context,
        "elapsed_seconds": round(time.monotonic() - t0, 3),
        "peak_rss_bytes": peak_rss_bytes(),
        "canonical_runtime_mutated_during_test": False,
        "global_certification": "NOT_GRANTED",
        "domain_certification": "PROVISIONAL_TWO_TASK_EVIDENCE_ONLY" if passed else "NOT_GRANTED",
        "conclusion": (
            "Exact checked-out commit passed two task checks. Evidence is scoped to one synthetic phrase and one public recorded-speech clip; broader transcription quality and all-domain certification remain pending."
            if passed else "Exact checked-out candidate failed retest; rollback is required."
        ),
    }
    write_report(Path(args.report), report)
    return 0 if passed else 3


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=("build-and-test", "verify-existing"))
    parser.add_argument("--repo-runtime-root", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--promotion-tar", type=Path)
    args = parser.parse_args()
    try:
        if args.mode == "build-and-test":
            if args.promotion_tar is None:
                parser.error("--promotion-tar required in build-and-test mode")
            return run_build(args)
        return run_verify(args)
    except Exception as exc:
        report = {
            "schema": "LOUKSNAPG_WHISPER_INT8_REPAIR_EXPERIMENT/1.0",
            "status": "ERROR_FAIL_CLOSED",
            "error_type": type(exc).__name__,
            "error_code": str(exc)[:500],
            "global_certification": "NOT_GRANTED",
            "promotion_performed": False,
            "timestamp_utc": utc_now(),
            "peak_rss_bytes": peak_rss_bytes(),
        }
        write_report(Path(args.report), report)
        print(json.dumps(report, sort_keys=True), file=sys.stderr, flush=True)
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
