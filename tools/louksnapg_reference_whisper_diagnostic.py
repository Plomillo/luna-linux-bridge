#!/usr/bin/env python3
"""Bounded CPU-only reference diagnostic for the previously failing Whisper task.

This downloads only the official Whisper large-v3-turbo reference to a disposable
GitHub-hosted runner. It does not alter the LOUKSNAPG runtime or certify the product.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
import wave
from pathlib import Path

MODEL_ID = "openai/whisper-large-v3-turbo"
MODEL_REVISION = "7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7"
EXPECTED_MODEL_SHA256 = "542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1"
MAX_NEW_TOKENS = 12
TARGET_SAMPLE_RATE = 16_000
EXPECTED_WORDS = ("hello", "world")


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def peak_rss_bytes() -> int:
    # Linux getrusage reports ru_maxrss in KiB.
    return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024)


def ensure_hosted_runner() -> None:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise RuntimeError("REFERENCE_MODEL_INFERENCE_REQUIRES_GITHUB_HOSTED_RUNNER")
    if not os.environ.get("GITHUB_SHA") or not os.environ.get("GITHUB_RUN_ID"):
        raise RuntimeError("GITHUB_RUN_ID_AND_SHA_REQUIRED")
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        if os.environ.get(name) != "1":
            raise RuntimeError("SINGLE_THREAD_BUDGET_NOT_ENFORCED:" + name)


def make_known_audio(output: Path) -> None:
    executable = shutil_which("espeak-ng")
    if not executable:
        raise RuntimeError("ESPEAK_NG_NOT_INSTALLED_ON_HOSTED_RUNNER")
    subprocess.run(
        [executable, "-v", "en-us", "-s", "135", "-w", str(output), "hello world"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    with wave.open(str(output), "rb") as stream:
        if stream.getnframes() <= 0 or stream.getsampwidth() != 2 or stream.getnchannels() not in (1, 2):
            raise RuntimeError("KNOWN_AUDIO_FIXTURE_INVALID")


def shutil_which(executable: str) -> str | None:
    import shutil
    return shutil.which(executable)


def load_reference_audio(path: Path):
    import numpy as np
    import soundfile as sf
    from math import gcd
    from scipy.signal import resample_poly

    audio, rate = sf.read(str(path), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1, dtype=np.float32)
    if rate != TARGET_SAMPLE_RATE:
        divisor = gcd(int(rate), TARGET_SAMPLE_RATE)
        audio = resample_poly(audio, TARGET_SAMPLE_RATE // divisor, int(rate) // divisor).astype(np.float32, copy=False)
    if audio.ndim != 1 or not len(audio) or not np.isfinite(audio).all():
        raise RuntimeError("KNOWN_AUDIO_WAVEFORM_INVALID")
    return audio


def write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--work-dir", required=True, type=Path)
    args = parser.parse_args()

    started = time.monotonic()
    report = {
        "schema": "LOUKSNAPG_WHISPER_REFERENCE_DIAGNOSTIC/1.0",
        "started_at_utc": utc_now(),
        "candidate_commit": os.environ.get("GITHUB_SHA"),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "execution_environment": "GITHUB_HOSTED_UBUNTU_CPU",
        "thread_budget": 1,
        "local_pc_inference": False,
        "product_runtime_mutated": False,
        "reference_model_id": MODEL_ID,
        "reference_model_revision": MODEL_REVISION,
        "expected_model_safetensors_sha256": EXPECTED_MODEL_SHA256,
        "reference_scope": "KNOWN_SYNTHETIC_AUDIO_TASK_ONLY",
        "quality_check": {"id": "known-speech-hello-world", "expected_words": list(EXPECTED_WORDS)},
        "global_certification": "NOT_GRANTED",
        "product_candidate_promoted": False,
    }
    try:
        ensure_hosted_runner()

        import torch
        torch.set_num_threads(1)
        try:
            torch.set_num_interop_threads(1)
        except RuntimeError:
            pass

        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=True)
        model_dir = work / "reference-model"
        audio_path = work / "known-speech-hello-world.wav"
        make_known_audio(audio_path)
        report["fixture_sample_rate_original"] = wave.open(str(audio_path), "rb").getframerate()
        report["fixture_bytes"] = audio_path.stat().st_size
        report["fixture_sha256"] = sha256_file(audio_path)

        from huggingface_hub import snapshot_download
        snapshot_download(
            repo_id=MODEL_ID,
            revision=MODEL_REVISION,
            local_dir=str(model_dir),
            allow_patterns=[
                "config.json",
                "generation_config.json",
                "model.safetensors",
                "preprocessor_config.json",
                "special_tokens_map.json",
                "tokenizer.json",
                "tokenizer_config.json",
                "vocab.json",
                "merges.txt",
                "normalizer.json",
                "added_tokens.json",
            ],
            max_workers=1,
        )
        weight_path = model_dir / "model.safetensors"
        if not weight_path.is_file():
            raise RuntimeError("PINNED_REFERENCE_MODEL_WEIGHTS_MISSING")
        observed_weight_sha = sha256_file(weight_path)
        report["reference_model_bytes"] = weight_path.stat().st_size
        report["reference_model_observed_sha256"] = observed_weight_sha
        if observed_weight_sha != EXPECTED_MODEL_SHA256:
            raise RuntimeError("PINNED_REFERENCE_MODEL_SHA256_MISMATCH")

        from transformers import AutoProcessor, WhisperForConditionalGeneration
        import numpy as np

        processor = AutoProcessor.from_pretrained(str(model_dir), local_files_only=True)
        model = WhisperForConditionalGeneration.from_pretrained(
            str(model_dir),
            torch_dtype=torch.float32,
            use_safetensors=True,
            local_files_only=True,
        )
        model.eval()
        audio = load_reference_audio(audio_path)
        features = processor(audio, sampling_rate=TARGET_SAMPLE_RATE, return_tensors="pt")
        inputs = features["input_features"].to(dtype=next(model.parameters()).dtype)

        with torch.inference_mode():
            generated = model.generate(
                input_features=inputs,
                language="en",
                task="transcribe",
                max_new_tokens=MAX_NEW_TOKENS,
                num_beams=1,
                do_sample=False,
            )
        if not isinstance(generated, torch.Tensor) or generated.ndim != 2 or generated.shape[0] != 1:
            raise RuntimeError("REFERENCE_TRANSCRIPTION_OUTPUT_SHAPE_INVALID")
        text = processor.batch_decode(generated, skip_special_tokens=True)[0].strip()
        words = re.findall(r"[a-z]+", text.casefold())
        missing = [word for word in EXPECTED_WORDS if word not in words]
        passed = not missing
        report.update({
            "reference_execution_status": "PASS_MODEL_INFERENCE",
            "reference_transcription_quality": "PASS_KNOWN_ANSWER" if passed else "FAIL_KNOWN_ANSWER",
            "observed_words": words,
            "missing_expected_words": missing,
            "transcription_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "transcription_char_count": len(text),
            "peak_rss_bytes": peak_rss_bytes(),
            "max_new_tokens": MAX_NEW_TOKENS,
            "torch_version": torch.__version__,
        })
        report["status"] = "PASS_REFERENCE_DIAGNOSTIC_ONLY" if passed else "FAIL_REFERENCE_DIAGNOSTIC"
        report["conclusion"] = (
            "UPSTREAM_REFERENCE_PASSES_THE_SAME_KNOWN_ANSWER; investigate compressed-weight reconstruction or candidate wiring."
            if passed else
            "UPSTREAM_REFERENCE_DID_NOT_PASS_THE_KNOWN_ANSWER; inspect fixture, processor/runtime and decoding before blaming compressed weights."
        )
    except Exception as exc:
        report.update({
            "status": "FAIL_REFERENCE_DIAGNOSTIC",
            "error_type": type(exc).__name__,
            "error_code": str(exc)[:240],
            "conclusion": "Reference diagnostic did not establish task correctness; no model or product certification is inferred.",
        })
        print(json.dumps({"event": "REFERENCE_DIAGNOSTIC_ERROR", "error_type": type(exc).__name__, "error_code": str(exc)[:240]}, sort_keys=True), file=sys.stderr, flush=True)
    report["finished_at_utc"] = utc_now()
    report["elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["peak_rss_bytes"] = report.get("peak_rss_bytes", peak_rss_bytes())
    write_report(args.output.resolve(), report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["status"] == "PASS_REFERENCE_DIAGNOSTIC_ONLY" else 1


if __name__ == "__main__":
    raise SystemExit(main())
