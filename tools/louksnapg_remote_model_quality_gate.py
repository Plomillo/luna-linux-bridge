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
from cajita_task_e2e import probe_ancient_translation_route

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


def integral_domain_gate_status(domain_rows: list[dict]) -> str:
    """Only established domain passes satisfy the required-domain gate."""
    if not domain_rows or any(
        not isinstance(row, dict) or not str(row.get("status", "")).startswith("PASS_")
        for row in domain_rows
    ):
        return "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED"
    return "PASS_KNOWN_ANSWER_SCOPE_ONLY"


def artifact_execution_scope() -> dict:
    """Separate execution of source files from proof of running the exact packaged product."""
    return {
        "runtime_under_test": "CHECKED_OUT_CAJITA_RUNTIME_SOURCE_TREE",
        "exact_louksnapg_distribution_bundle_sha256": None,
        "exact_candidate_artifact_functional_execution": "NOT_ESTABLISHED",
        "artifact_level_execution_required_for_integral_certification": True,
        "artifact_integrity_evidence_does_not_imply_functional_execution": True,
        "scope_limit": "DOES_NOT_ESTABLISH_EXECUTION_OF_THE_EXACT_PACKAGED_LOUKSNAPG_MD_BUNDLE",
    }

def quality_gate_exit_code(status: str) -> int:
    """A route-only preflight may pass, but an integral-domain blocker never exits green."""
    return 0 if status in {"PASS_ROUTE_PREFLIGHT_ONLY", "PASS_REMOTE_SEMANTIC_TASKS"} else 2


def required_domain_statuses(task_rows: list[dict], ancient_route: dict) -> list[dict]:
    """Report all five required domains; route identification is not translation proof."""
    by_domain: dict[str, list[dict]] = {}
    for row in task_rows:
        if isinstance(row, dict):
            by_domain.setdefault(str(row.get("domain_id", "")), []).append(row)

    def task_status(domain: str, expected_count: int = 1) -> str:
        rows = by_domain.get(domain, [])
        if len(rows) < expected_count:
            return "NOT_TESTED_REQUIRED_TASK_COUNT_INCOMPLETE"
        all_pass = all(
            row.get("status") == "PASS_REMOTE_EXECUTION"
            and row.get("execution_authorized") is True
            and row.get("quality_status") == "PASS"
            for row in rows
        )
        if all_pass:
            return "PASS_KNOWN_ANSWER_TASKS_ONLY"
        if any(row.get("status") == "PASS_REMOTE_EXECUTION" for row in rows):
            return "EXECUTED_QUALITY_FAILED"
        if rows:
            return "REMOTE_EXECUTION_FAILED"
        return "NOT_TESTED"

    route_status = str(ancient_route.get("status", "NOT_TESTED"))
    ancient_function = str(ancient_route.get("functional_translation_status", "NOT_TESTED"))
    fallback_selected = ancient_route.get("general_translation_fallback_selected")
    execution_authorized = ancient_route.get("execution_authorized")
    if route_status.startswith("PASS_ROUTE_IDENTIFIED") and fallback_selected is False and execution_authorized is False and ancient_function.startswith("BLOCKED_"):
        ancient_status = ancient_function
    elif route_status.startswith("PASS_ROUTE_IDENTIFIED") and fallback_selected is False and execution_authorized is False:
        ancient_status = "NOT_TESTED_NATIVE_TRANSLATION_TASK_REQUIRED"
    else:
        ancient_status = "FAIL_ANCIENT_ROUTE_DIAGNOSTIC"

    return [
        {"required_domain": "Cerebro / GPT-OSS-120B", "domain_id": "D01_CEREBRO",
         "status": task_status("D01_CEREBRO")},
        {"required_domain": "Razonamiento avanzado / Qwen", "domain_id": "D06_SISTEMA_INTELIGENTE",
         "status": task_status("D06_SISTEMA_INTELIGENTE")},
        {"required_domain": "Traducción general", "domain_id": "D04_TRADUCTOR_INTELIGENTE",
         "status": task_status("D04_TRADUCTOR_INTELIGENTE")},
        {"required_domain": "Traducción de lenguas antiguas", "domain_id": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
         "status": ancient_status, "route_diagnostic": route_status,
         "general_translation_fallback_selected": ancient_route.get("general_translation_fallback_selected")},
        {"required_domain": "Transcripción / Whisper", "domain_id": "D03_TRANSCRIPCION",
         "status": task_status("D03_TRANSCRIPCION", expected_count=2)},
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, default=Path(__file__).resolve().parents[1] / "cajita-luna-runtime")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument(
        "--preflight-only",
        action="store_true",
        help="Check source policy and the ancient-language fail-closed route only; execute no models or remote endpoints.",
    )
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
        "candidate_source_commit": os.environ.get("GITHUB_SHA"),
        "workflow_ref": os.environ.get("GITHUB_REF"),
        **artifact_execution_scope(),
        "workflow_run_id": os.environ.get("GITHUB_RUN_ID"),
        "workflow_run_attempt": os.environ.get("GITHUB_RUN_ATTEMPT"),
        "workflow_event": os.environ.get("GITHUB_EVENT_NAME"),
        "remote_execution_mode": "required" if not args.preflight_only else "NOT_USED_PREFLIGHT_ONLY",
        "local_model_inference": False,
        "local_model_weights_downloaded": False,
        "remote_endpoint_contacted": False,
        "model_task_execution_performed": False,
        "domain_task_results": [],
        "certification": "NOT_GRANTED",
        "global_certification": "NOT_GRANTED",
        "scope": "SEMANTIC_KNOWN_ANSWER_TASKS_THROUGH_CHECKED_OUT_CAJITA_RUNTIME_SOURCE_AND_SOURCE_PINNED_REMOTE_GATEWAYS",
    }
    try:
        policy_path = runtime / "CAJITA_REMOTE_MODEL_POLICY.json"
        if policy_path.is_symlink() or not policy_path.is_file():
            raise RuntimeError("REMOTE_MODEL_POLICY_MISSING_OR_UNSAFE")
        policy = json.loads(policy_path.read_text(encoding="utf-8"))
        if policy.get("schema") != "LOUKSNAPG_REMOTE_MODEL_POLICY/1.0":
            raise RuntimeError("REMOTE_MODEL_POLICY_SCHEMA_MISMATCH")
        if policy.get("certification") != "NOT_GRANTED":
            raise RuntimeError("REMOTE_MODEL_POLICY_CERTIFICATION_MUST_REMAIN_NOT_GRANTED")
        report["policy_sha256"] = sha_bytes(policy_path.read_bytes())
        report["quality_gate_sha256"] = sha256_file(Path(__file__).resolve())
        report["remote_client_sha256"] = sha256_file(runtime / "cajita_remote_execution.py")
        report["task_adapter_sha256"] = sha256_file(runtime / "cajita_task_adapters.py")
        report["router_sha256"] = sha256_file(runtime / "cajita_router.py")
        report["remote_source_revisions"] = {
            domain: row["source_revision"] for domain, row in policy.get("domains", {}).items()
        }
        report["remote_gateway_trust"] = policy.get("gateway_trust")

        # This diagnostic is independent of remote endpoints and model loading.
        # It verifies that ancient Greek reaches the ancient target and remains blocked
        # instead of silently using the general-language translation model.
        ancient_route = probe_ancient_translation_route(runtime, work, 60)
        report["ancient_translation_route"] = ancient_route
        report["required_domain_statuses"] = required_domain_statuses([], ancient_route)
        report["required_domain_gate_status"] = "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED"
        report["integral_certification"] = "NOT_GRANTED"

        if args.preflight_only:
            route_ok = (
                str(ancient_route.get("status", "")).startswith("PASS_ROUTE_IDENTIFIED")
                and ancient_route.get("general_translation_fallback_selected") is False
                and ancient_route.get("execution_authorized") is False
            )
            report["mode"] = "PREFLIGHT_ONLY_NO_MODEL_INFERENCE_NO_REMOTE_ENDPOINT"
            report["status"] = "PASS_ROUTE_PREFLIGHT_ONLY" if route_ok else "FAIL_ROUTE_PREFLIGHT"
            report["preflight"] = {
                "ancient_target_identified": route_ok,
                "general_translation_fallback_selected": ancient_route.get("general_translation_fallback_selected"),
                "execution_authorized": ancient_route.get("execution_authorized"),
                "functional_ancient_translation": ancient_route.get("functional_translation_status"),
                "model_inference_executed": False,
                "remote_endpoint_contacted": False,
            }
        else:
            # Configuration is checked before fixtures are generated or endpoints are contacted.
            assert_endpoints_configured()
            report["mode"] = "LIVE_REMOTE_SEMANTIC_TASKS"
            report["remote_endpoint_contacted"] = True

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
                    # SeamlessM4T expects ISO 639-3 codes (e.g. eng, spa), not two-letter ISO 639-1 aliases.
                "inputs": {"text": "The book is on the table.", "src_lang": "eng", "tgt_lang": "spa"},
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
            report["model_task_execution_performed"] = True

            failures = [
                {"task_id": item["task_id"], "domain_id": item["domain_id"], "status": item["quality_status"]}
                for item in report["domain_task_results"] if item.get("quality_status") != "PASS"
            ]
            report["task_count"] = len(report["domain_task_results"])
            report["task_quality_pass_count"] = report["task_count"] - len(failures)
            report["task_quality_failures"] = failures
            report["semantic_task_status"] = "PASS_REMOTE_SEMANTIC_TASKS" if not failures else "FAIL_REMOTE_SEMANTIC_TASKS"
            report["required_domain_statuses"] = required_domain_statuses(report["domain_task_results"], ancient_route)
            domain_failures = [row for row in report["required_domain_statuses"] if not row["status"].startswith("PASS_")]
            report["required_domain_gate_status"] = integral_domain_gate_status(report["required_domain_statuses"])
            report["integral_certification"] = "NOT_GRANTED"
            # The semantic harness may pass its declared five tasks; that never certifies
            # the integral product while the dedicated ancient-language domain is blocked.
            report["status"] = (
                "PASS_REMOTE_SEMANTIC_TASKS_INTEGRAL_GATE_BLOCKED"
                if not failures and domain_failures
                else ("PASS_REMOTE_SEMANTIC_TASKS" if not failures else "FAIL_REMOTE_SEMANTIC_TASKS")
            )
        report["finished_at_utc"] = utc_now()
    except Exception as exc:
        message = type(exc).__name__ + ":" + str(exc)[:1000]
        report["status"] = (
            "BLOCKED_REMOTE_ENDPOINT_CONFIGURATION"
            if message.startswith("RuntimeError:REMOTE_QUALITY_ENDPOINT_OR_SECRET_MISSING:")
            else "FAIL_CLOSED"
        )
        report["error"] = message
        report["finished_at_utc"] = utc_now()
        report["required_domain_statuses"] = required_domain_statuses(report.get("domain_task_results", []), report.get("ancient_translation_route", {}))
        report["required_domain_gate_status"] = "BLOCKED_REQUIRED_DOMAIN_NOT_ESTABLISHED"
        report["integral_certification"] = "NOT_GRANTED"
    serialized = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    temp_report = report_path.with_suffix(report_path.suffix + ".tmp")
    temp_report.write_text(serialized, encoding="utf-8")
    os.replace(temp_report, report_path)
    print(serialized, end="")
    if work_temp:
        work_temp.cleanup()
    return quality_gate_exit_code(str(report.get("status", "FAIL_CLOSED")))


if __name__ == "__main__":
    raise SystemExit(main())
