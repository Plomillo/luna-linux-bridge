#!/usr/bin/env python3
"""Run semantic tasks through the exact candidate adapter in remote-required mode.

No model weights are loaded locally. Every task is routed by cajita_task_adapters.py
with LOUKSNAPG_REMOTE_MODE=required, so a missing or invalid endpoint fails closed
without using the compact local weights. The report records task evidence but never
grants certification by itself.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from pathlib import Path
from typing import Any

from louksnapg_reference_whisper_diagnostic import (
    load_librispeech_fixture,
    make_known_audio,
    word_error_rate,
    normalized_words,
    sha256_file,
)

REPORT_SCHEMA = "LOUKSNAPG_REMOTE_SEMANTIC_QUALITY_GATE/1.0"
DOMAIN_ENDPOINTS = {
    "D01_CEREBRO": ("LOUKSNAPG_REMOTE_CEREBRO_URL", "LOUKSNAPG_REMOTE_CEREBRO_KEY_HEX"),
    "D03_TRANSCRIPCION": ("LOUKSNAPG_REMOTE_TRANSCRIPTION_URL", "LOUKSNAPG_REMOTE_TRANSCRIPTION_KEY_HEX"),
    "D04_TRADUCTOR_INTELIGENTE": ("LOUKSNAPG_REMOTE_TRANSLATION_URL", "LOUKSNAPG_REMOTE_TRANSLATION_KEY_HEX"),
    "D06_SISTEMA_INTELIGENTE": ("LOUKSNAPG_REMOTE_ANALYSIS_URL", "LOUKSNAPG_REMOTE_ANALYSIS_KEY_HEX"),
}
MAX_AUDIO_BYTES = 32 * 1024 * 1024


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def final_integer(value: str) -> int | None:
    matches = re.findall(r"(?<![A-Za-z0-9])[-+]?\d+(?![A-Za-z0-9])", value)
    if not matches:
        return None
    try:
        return int(matches[-1])
    except ValueError:
        return None


def whitelisted_remote_environment() -> dict[str, str]:
    allowed = {
        "PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "SYSTEMROOT", "WINDIR",
        "LOUKSNAPG_REMOTE_CEREBRO_URL", "LOUKSNAPG_REMOTE_CEREBRO_KEY_HEX",
        "LOUKSNAPG_REMOTE_TRANSCRIPTION_URL", "LOUKSNAPG_REMOTE_TRANSCRIPTION_KEY_HEX",
        "LOUKSNAPG_REMOTE_TRANSLATION_URL", "LOUKSNAPG_REMOTE_TRANSLATION_KEY_HEX",
        "LOUKSNAPG_REMOTE_ANALYSIS_URL", "LOUKSNAPG_REMOTE_ANALYSIS_KEY_HEX",
    }
    env = {key: os.environ[key] for key in allowed if key in os.environ}
    env.update({
        "LOUKSNAPG_REMOTE_MODE": "required",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
    })
    return env


def assert_endpoints_configured() -> None:
    missing = []
    for domain_id, (url_env, key_env) in DOMAIN_ENDPOINTS.items():
        if not os.environ.get(url_env, "").strip():
            missing.append(url_env)
        key = os.environ.get(key_env, "")
        if not re.fullmatch(r"[0-9a-fA-F]{64}", key):
            missing.append(key_env)
    if missing:
        raise RuntimeError("REMOTE_QUALITY_ENDPOINT_OR_SECRET_MISSING:" + ",".join(sorted(set(missing))))


def run_task(runtime_root: Path, work_dir: Path, *, task_id: str, domain_id: str,
             operation: str, inputs: dict, max_new_tokens: int = 64,
             timeout_seconds: int = 600) -> dict:
    request = {
        "schema": "CAJITA_TASK_REQUEST/1.0",
        "task_id": task_id,
        "domain_id": domain_id,
        "operation": operation,
        "input": inputs,
        "limits": {
            "timeout_seconds": timeout_seconds,
            "max_new_tokens": max_new_tokens,
        },
    }
    request_bytes = canonical(request)
    request_sha = sha_bytes(request_bytes)
    request_path = work_dir / (task_id + ".request.json")
    request_path.write_bytes(request_bytes + b"\n")
    command = [
        sys.executable, "-B", str(runtime_root / "cajita_task_adapters.py"),
        "execute", "--request-json", str(request_path),
        "--root", str(runtime_root), "--timeout", str(timeout_seconds),
    ]
    started = dt.datetime.now(dt.timezone.utc)
    try:
        proc = subprocess.run(
            command,
            cwd=str(runtime_root),
            env=whitelisted_remote_environment(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_seconds + 15,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return {
            "task_id": task_id, "domain_id": domain_id, "operation": operation,
            "input_sha256": request_sha, "status": "FAIL_TIMEOUT",
            "reason": "REMOTE_QUALITY_GATE_TASK_TIMEOUT", "return_code": 124,
            "remote_execution_mode": "required", "quality_equivalence": "NOT_ESTABLISHED",
        }
    try:
        result = json.loads(proc.stdout) if proc.stdout.strip() else {}
    except json.JSONDecodeError:
        result = {}
    if not isinstance(result, dict):
        result = {}
    return {
        "task_id": task_id,
        "domain_id": domain_id,
        "operation": operation,
        "input_sha256": result.get("input_sha256", request_sha),
        "output_sha256": result.get("output_sha256"),
        "remote_evidence": result.get("remote_evidence"),
        "status": result.get("status", "FAIL_MALFORMED_ADAPTER_RESULT"),
        "return_code": proc.returncode,
        "output_text": str(result.get("output_text", ""))[:1024],
        "generated_token_count": result.get("generated_token_count"),
        "reason": result.get("reason"),
        "elapsed_seconds": round((dt.datetime.now(dt.timezone.utc) - started).total_seconds(), 3),
        "remote_execution_mode": result.get("remote_execution_mode", "required"),
        "execution_authorized": result.get("execution_authorized") is True,
        "semantic_quality_equivalence": "NOT_ESTABLISHED_UNTIL_TASK_ASSERTION",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parents[1] / "cajita-luna-runtime")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args()

    runtime = args.runtime_root.resolve(strict=True)
    report_path = args.report
    work_temp = None
    if args.work_dir:
        work = args.work_dir.resolve()
        work.mkdir(parents=True, exist_ok=True)
    else:
        work_temp = tempfile.TemporaryDirectory(prefix="louksnapg-remote-quality-")
        work = Path(work_temp.name)
    report = {
        "schema": REPORT_SCHEMA,
        "started_at_utc": utc_now(),
        "runtime_root": str(runtime),
        "remote_execution_mode": "required",
        "local_model_inference": False,
        "local_model_weights_downloaded": False,
        "domain_task_results": [],
        "certification": "NOT_GRANTED",
        "global_certification": "NOT_GRANTED",
        "scope": "SEMANTIC_KNOWN_ANSWER_TASKS_THROUGH_THE_CANDIDATE_ADAPTER_AND_SOURCE_PINNED_REMOTE_GATEWAYS",
    }
    try:
        assert_endpoints_configured()
        policy_path = runtime / "CAJITA_REMOTE_MODEL_POLICY.json"
        if policy_path.is_symlink() or not policy_path.is_file():
            raise RuntimeError("REMOTE_MODEL_POLICY_MISSING_OR_UNSAFE")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        report["policy_sha256"] = sha_bytes(policy_path.read_bytes())
        report["remote_source_revisions"] = {
            domain: row["source_revision"] for domain, row in policy.get("domains", {}).items()
        }

        scenarios = [
            {
                "task_id": "remote-quality-cerebro-reasoning-01",
                "domain_id": "D01_CEREBRO",
                "operation": "generate_text",
                "inputs": {
                    "prompt": (
                        "Reason through this inventory problem and give only the final integer: "
                        "A shop has 4 boxes with 6 bottles in each. It sells 7 bottles and later receives 3. "
                        "How many bottles are left?"
                    )
                },
                "expected_integer": 20,
                "max_new_tokens": 64,
            },
            {
                "task_id": "remote-quality-qwen-analysis-01",
                "domain_id": "D06_SISTEMA_INTELIGENTE",
                "operation": "analyze_reasoning",
                "inputs": {
                    "prompt": (
                        "Compute this sequential calculation carefully and return only the final integer: "
                        "Start with 15, multiply by 2, subtract 8, then divide by 2."
                    )
                },
                "expected_integer": 11,
                "max_new_tokens": 64,
            },
            {
                "task_id": "remote-quality-general-translation-01",
                "domain_id": "D04_TRADUCTOR_INTELIGENTE",
                "operation": "translate_text",
                "inputs": {"text": "The book is on the table.", "src_lang": "en", "tgt_lang": "es"},
                "expected_translations": {
                    "el libro esta sobre la mesa",
                    "el libro esta en la mesa",
                    "el libro esta encima de la mesa",
                },
                "max_new_tokens": 48,
            },
        ]
        for scenario in scenarios:
            result = run_task(
                runtime, work,
                task_id=scenario["task_id"],
                domain_id=scenario["domain_id"],
                operation=scenario["operation"],
                inputs=scenario["inputs"],
                max_new_tokens=scenario["max_new_tokens"],
            )
            if result["status"] != "PASS_REMOTE_EXECUTION" or not result["execution_authorized"]:
                result["quality_status"] = "FAIL_REMOTE_EXECUTION"
                result["quality_reason"] = result.get("reason") or result["status"]
            elif "expected_integer" in scenario:
                observed = final_integer(result.get("output_text", ""))
                result["observed_integer"] = observed
                result["expected_integer"] = scenario["expected_integer"]
                result["quality_status"] = "PASS" if observed == scenario["expected_integer"] else "FAIL_SEMANTIC_ANSWER"
            else:
                observed = normalize_text(result.get("output_text", ""))
                result["normalized_translation"] = observed
                result["expected_translation_variants"] = sorted(scenario["expected_translations"])
                result["quality_status"] = "PASS" if observed in scenario["expected_translations"] else "FAIL_TRANSLATION_QUALITY"
            report["domain_task_results"].append(result)

        synthetic_audio = work / "known-speech-hello-world.wav"
        make_known_audio(synthetic_audio)
        synthetic_audio_meta = {
            "path": synthetic_audio.name,
            "bytes": synthetic_audio.stat().st_size,
            "sha256": sha256_file(synthetic_audio),
            "expected_text": "hello world",
            "fixture_kind": "ESPEAK_SYNTHETIC_KNOWN_ANSWER",
        }
        transcription = run_task(
            runtime, work,
            task_id="remote-quality-whisper-synthetic-01",
            domain_id="D03_TRANSCRIPCION",
            operation="transcribe_audio",
            inputs={"audio_path": str(synthetic_audio)},
            max_new_tokens=16,
        )
        transcript = " ".join(normalized_words(transcription.get("output_text", "")))
        transcription["fixture"] = synthetic_audio_meta
        transcription["normalized_transcript"] = transcript
        transcription["expected_transcript"] = "hello world"
        if transcription["status"] != "PASS_REMOTE_EXECUTION" or not transcription["execution_authorized"]:
            transcription["quality_status"] = "FAIL_REMOTE_EXECUTION"
        else:
            transcription["quality_status"] = "PASS" if transcript == "hello world" else "FAIL_TRANSCRIPTION_QUALITY"
        report["domain_task_results"].append(transcription)

        real_audio_path, reference_text, real_fixture = load_librispeech_fixture(work)
        if real_audio_path.stat().st_size > MAX_AUDIO_BYTES:
            raise RuntimeError("PINNED_REAL_AUDIO_FIXTURE_OVER_ADAPTER_LIMIT")
        real_result = run_task(
            runtime, work,
            task_id="remote-quality-whisper-librispeech-01",
            domain_id="D03_TRANSCRIPCION",
            operation="transcribe_audio",
            inputs={"audio_path": str(real_audio_path)},
            max_new_tokens=128,
            timeout_seconds=900,
        )
        hypothesis = real_result.get("output_text", "")
        wer = word_error_rate(reference_text, hypothesis) if hypothesis.strip() else 1.0
        real_result["fixture"] = {
            "fixture_kind": "PINNED_LIBRISPEECH_REAL_SPEECH",
            "dataset_repo": real_fixture.get("dataset_repo"),
            "dataset_revision": real_fixture.get("dataset_revision"),
            "audio_id": real_fixture.get("audio_id"),
            "audio_asset_sha256": real_fixture.get("audio_asset_sha256"),
            "audio_wav_sha256": real_fixture.get("audio_wav_sha256"),
            "reference_transcript_sha256": real_fixture.get("transcript_sha256"),
            "reference_word_count": real_fixture.get("reference_word_count"),
        }
        real_result["word_error_rate"] = round(wer, 6)
        real_result["max_word_error_rate"] = 0.25
        real_result["quality_status"] = (
            "PASS" if real_result["status"] == "PASS_REMOTE_EXECUTION"
            and real_result["execution_authorized"] and wer <= 0.25 else "FAIL_TRANSCRIPTION_WER"
        )
        report["domain_task_results"].append(real_result)

        failures = [
            {"task_id": item["task_id"], "domain_id": item["domain_id"], "status": item["quality_status"]}
            for item in report["domain_task_results"] if item.get("quality_status") != "PASS"
        ]
        report["task_count"] = len(report["domain_task_results"])
        report["task_quality_pass_count"] = report["task_count"] - len(failures)
        report["task_quality_failures"] = failures
        report["status"] = "PASS_REMOTE_SEMANTIC_TASKS" if not failures else "FAIL_REMOTE_SEMANTIC_TASKS"
        report["finished_at_utc"] = utc_now()
    except Exception as exc:
        report["status"] = "FAIL_CLOSED"
        report["error"] = type(exc).__name__ + ":" + str(exc)[:1000]
        report["finished_at_utc"] = utc_now()
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    if work_temp:
        work_temp.cleanup()
    return 0 if report.get("status") == "PASS_REMOTE_SEMANTIC_TASKS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
