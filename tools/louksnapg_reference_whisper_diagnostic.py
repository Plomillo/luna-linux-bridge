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
DATASET_REPO = "hf-internal-testing/librispeech_asr_dummy"
DATASET_REVISION = "5be91486e11a2d616f4ec5db8d3fd248585ac07a"
DATASET_PARQUET = "clean/validation-00000-of-00001.parquet"
EXPECTED_PARQUET_SHA256 = "4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603"
REAL_AUDIO_ID = "1272-128104-0000"
REAL_WER_MAX = 0.25
MAX_NEW_TOKENS_SYNTHETIC = 12
MAX_NEW_TOKENS_REAL = 128
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


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalized_words(reference), normalized_words(hypothesis)
    if not ref:
        raise ValueError("WER_REFERENCE_EMPTY")
    previous = list(range(len(hyp) + 1))
    for i, rword in enumerate(ref, 1):
        current = [i]
        for j, hword in enumerate(hyp, 1):
            current.append(min(
                current[-1] + 1,
                previous[j] + 1,
                previous[j - 1] + (rword != hword),
            ))
        previous = current
    return previous[-1] / len(ref)


def load_librispeech_fixture(work_dir: Path) -> tuple[Path, str, dict]:
    import io
    from huggingface_hub import hf_hub_download
    from datasets import Audio, load_dataset
    import numpy as np
    import soundfile as sf

    parquet = Path(hf_hub_download(
        repo_id=DATASET_REPO,
        filename=DATASET_PARQUET,
        repo_type="dataset",
        revision=DATASET_REVISION,
    ))
    observed_parquet_sha = sha256_file(parquet)
    if observed_parquet_sha != EXPECTED_PARQUET_SHA256:
        raise RuntimeError("PINNED_LIBRISPEECH_PARQUET_SHA256_MISMATCH:" + observed_parquet_sha)
    dataset = load_dataset("parquet", data_files={"validation": str(parquet)}, split="validation")
    dataset = dataset.cast_column("audio", Audio(sampling_rate=TARGET_SAMPLE_RATE, decode=False))
    row = next((item for item in dataset if item.get("id") == REAL_AUDIO_ID), None)
    if row is None:
        raise RuntimeError("PINNED_LIBRISPEECH_SAMPLE_ID_NOT_FOUND")
    audio_metadata = row["audio"]
    raw_audio = audio_metadata.get("bytes")
    if raw_audio is None:
        audio_path = audio_metadata.get("path")
        if not audio_path:
            raise RuntimeError("LIBRISPEECH_AUDIO_BYTES_OR_PATH_MISSING")
        raw_audio = Path(audio_path).read_bytes()
    source_audio_sha = hashlib.sha256(raw_audio).hexdigest()
    audio, rate = sf.read(io.BytesIO(raw_audio), dtype="float32", always_2d=False)
    if audio.ndim == 2:
        audio = audio.mean(axis=1, dtype=np.float32)
    if int(rate) != TARGET_SAMPLE_RATE:
        raise RuntimeError("LIBRISPEECH_SAMPLE_RATE_MISMATCH:" + str(rate))
    if not len(audio) or not np.isfinite(audio).all():
        raise RuntimeError("LIBRISPEECH_AUDIO_INVALID")
    audio = np.clip(audio, -1.0, 0.999969).astype(np.float32, copy=False)
    pcm = (audio * 32768.0).round().astype("<i2")
    output = work_dir / "librispeech-1272-128104-0000.wav"
    with wave.open(str(output), "wb") as stream:
        stream.setnchannels(1)
        stream.setsampwidth(2)
        stream.setframerate(TARGET_SAMPLE_RATE)
        stream.writeframes(pcm.tobytes())
    transcript = str(row["text"])
    metadata = {
        "dataset_repo": DATASET_REPO,
        "dataset_revision": DATASET_REVISION,
        "parquet_path": DATASET_PARQUET,
        "expected_parquet_sha256": EXPECTED_PARQUET_SHA256,
        "observed_parquet_sha256": observed_parquet_sha,
        "audio_id": REAL_AUDIO_ID,
        "audio_asset_sha256": source_audio_sha,
        "audio_wav_sha256": sha256_file(output),
        "audio_wav_bytes": output.stat().st_size,
        "sample_rate_hz": TARGET_SAMPLE_RATE,
        "duration_seconds": round(len(audio) / TARGET_SAMPLE_RATE, 3),
        "transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "reference_word_count": len(normalized_words(transcript)),
    }
    return output, transcript, metadata


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
        "reference_scope": "SYNTHETIC_AND_PINNED_REAL_SPEECH_WITH_INTEGRATED_DECODER_SETTINGS",
        "decoder_policy": {
            "matches_integrated_runtime": True,
            "do_sample": False,
            "num_beams": 1,
            "repetition_penalty": 1.08,
            "no_repeat_ngram_size": 3,
            "renormalize_logits": True,
            "minimum_new_tokens": "min(3, max_new_tokens)",
        },
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
        report["synthetic_fixture"] = {
            "sample_rate_original_hz": wave.open(str(audio_path), "rb").getframerate(),
            "bytes": audio_path.stat().st_size,
            "sha256": sha256_file(audio_path),
            "expected_words": list(EXPECTED_WORDS),
        }
        real_audio_path, real_transcript, real_fixture_metadata = load_librispeech_fixture(work)
        report["real_audio_fixture"] = real_fixture_metadata

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

        def transcribe(path: Path, max_new_tokens: int) -> str:
            audio = load_reference_audio(path)
            features = processor(audio, sampling_rate=TARGET_SAMPLE_RATE, return_tensors="pt")
            inputs = features["input_features"].to(dtype=next(model.parameters()).dtype)
            with torch.inference_mode():
                # Match the integrated candidate's deterministic decoding controls exactly.
                # This isolates weight reconstruction from generation-policy effects.
                generated = model.generate(
                    input_features=inputs,
                    language="en",
                    task="transcribe",
                    max_new_tokens=max_new_tokens,
                    min_new_tokens=min(3, max_new_tokens),
                    do_sample=False,
                    repetition_penalty=1.08,
                    no_repeat_ngram_size=3,
                    renormalize_logits=True,
                    num_beams=1,
                )
            if not isinstance(generated, torch.Tensor) or generated.ndim != 2 or generated.shape[0] != 1:
                raise RuntimeError("REFERENCE_TRANSCRIPTION_OUTPUT_SHAPE_INVALID")
            return processor.batch_decode(generated, skip_special_tokens=True)[0].strip()

        synthetic_text = transcribe(audio_path, MAX_NEW_TOKENS_SYNTHETIC)
        synthetic_words = normalized_words(synthetic_text)
        synthetic_missing = [word for word in EXPECTED_WORDS if word not in synthetic_words]
        synthetic_pass = not synthetic_missing

        real_text = transcribe(real_audio_path, MAX_NEW_TOKENS_REAL)
        wer = word_error_rate(real_transcript, real_text)
        real_pass = wer <= REAL_WER_MAX
        overall_pass = synthetic_pass and real_pass
        report.update({
            "synthetic_check": {
                "id": "known-speech-hello-world",
                "status": "PASS" if synthetic_pass else "FAIL",
                "observed_words": synthetic_words,
                "missing_expected_words": synthetic_missing,
                "transcription_text": synthetic_text[:512],
                "transcription_sha256": hashlib.sha256(synthetic_text.encode("utf-8")).hexdigest(),
                "max_new_tokens": MAX_NEW_TOKENS_SYNTHETIC,
            },
            "real_speech_check": {
                "id": "librispeech-real-speech-transcript",
                "status": "PASS" if real_pass else "FAIL",
                "wer": round(wer, 6),
                "wer_limit": REAL_WER_MAX,
                "reference_word_count": len(normalized_words(real_transcript)),
                "transcription_word_count": len(normalized_words(real_text)),
                "reference_transcript_sha256": hashlib.sha256(real_transcript.encode("utf-8")).hexdigest(),
                "transcription_text": real_text[:1024],
                "transcription_sha256": hashlib.sha256(real_text.encode("utf-8")).hexdigest(),
                "max_new_tokens": MAX_NEW_TOKENS_REAL,
                "audio_id": REAL_AUDIO_ID,
                "dataset_repo": DATASET_REPO,
                "dataset_revision": DATASET_REVISION,
            },
            "reference_execution_status": "PASS_MODEL_INFERENCE",
            "reference_transcription_quality": "PASS_BOTH_REFERENCE_TASKS" if overall_pass else "FAIL_REFERENCE_TASKS",
            "peak_rss_bytes": peak_rss_bytes(),
            "torch_version": torch.__version__,
        })
        report["status"] = "PASS_REFERENCE_DIAGNOSTIC_ONLY" if overall_pass else "FAIL_REFERENCE_DIAGNOSTIC"
        report["conclusion"] = (
            "The source reference passed the synthetic known-answer and the pinned real-speech WER checks. The compressed model's failure is attributable to the candidate representation or its consumer path, not a changed fixture."
            if overall_pass else
            "The source reference did not pass every equivalent task check; inspect fixture, processor, decoding and task criteria before attributing the compact candidate failure solely to factorization."
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
