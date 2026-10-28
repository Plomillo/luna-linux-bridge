#!/usr/bin/env python3
"""Phase-2 functional runner for the exact repository commit; never certifies globally.

Runs the currently registered task-level model adapters (Cerebro, Qwen, general
translation, Whisper), records the ancient-language adapter gap explicitly, and
preserves per-task checkpoints. Model inference only runs on the hosted runner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

from cajita_task_e2e import MODEL_CASES, make_audio, run_case

DOMAIN_ORDER = [
    ("D01_CEREBRO", "CEREBRO"),
    ("D06_SISTEMA_INTELIGENTE", "QWEN_ADVANCED_REASONING"),
    ("D04_TRADUCTOR_INTELIGENTE", "GENERAL_TRANSLATION"),
    ("D04_TRADUCCION_LENGUAS_ANTIGUAS", "ANCIENT_LANGUAGE_TRANSLATION"),
    ("D03_TRANSCRIPCION", "WHISPER_TRANSCRIPTION"),
]
REGISTERED_CASES = {
    "D01_CEREBRO": "CEREBRO",
    "D06_SISTEMA_INTELIGENTE": "QWEN_ADVANCED_REASONING",
    "D04_TRADUCTOR_INTELIGENTE": "GENERAL_TRANSLATION",
    "D03_TRANSCRIPCION": "WHISPER_TRANSCRIPTION",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_checkpoint(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def event(name: str, **fields) -> None:
    print(json.dumps({"event": name, "timestamp_utc": utc_now(), **fields}, ensure_ascii=False), flush=True)


def require_hosted_runner(environ: dict[str, str] | None = None) -> None:
    """Block accidental local model inference; the 1 GiB limit applies only to PC inspection."""
    env = os.environ if environ is None else environ
    if env.get("GITHUB_ACTIONS", "").strip().lower() != "true":
        raise RuntimeError("HEAVY_MODEL_INFERENCE_REQUIRES_GITHUB_HOSTED_RUNNER")


def parse_mem_total_bytes(meminfo_text: str) -> int:
    match = re.search(r"^MemTotal:\\s+(\\d+)\\s+kB\\s*$", meminfo_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("HOSTED_RUNNER_MEMTOTAL_UNAVAILABLE")
    value = int(match.group(1)) * 1024
    if value <= 0:
        raise ValueError("HOSTED_RUNNER_MEMTOTAL_INVALID")
    return value


def parse_cgroup_memory_limit_bytes(text: str) -> int | None:
    value = text.strip()
    if not value or value.lower() == "max":
        return None
    if not value.isdigit():
        return None
    limit = int(value)
    # cgroup v1 and some containers expose a huge sentinel instead of a real cap.
    if limit <= 0 or limit >= (1 << 60):
        return None
    return limit


def calculate_hosted_runner_rss_budget_bytes(
    mem_total_bytes: int,
    cgroup_limit_bytes: int | None = None,
    override_bytes: int | None = None,
) -> dict:
    """Calculate an independent hosted-runner budget; never reuse the local 1 GiB cap."""
    if override_bytes is not None:
        if isinstance(override_bytes, bool) or not isinstance(override_bytes, int) or override_bytes <= 0:
            raise ValueError("HOSTED_RUNNER_RSS_OVERRIDE_INVALID")
        return {
            "rss_budget_bytes": override_bytes,
            "effective_memory_limit_bytes": None,
            "budget_source": "LOUKSNAPG_HOSTED_RUNNER_RSS_CAP_BYTES",
            "budget_fraction": None,
            "local_inspection_budget_applied": False,
        }
    limits = [x for x in (mem_total_bytes, cgroup_limit_bytes) if isinstance(x, int) and not isinstance(x, bool) and x > 0]
    if not limits:
        raise ValueError("HOSTED_RUNNER_MEMORY_LIMIT_UNAVAILABLE")
    effective_limit = min(limits)
    # Keep a 25% headroom for the OS, runner agent, and concurrent CI services.
    budget = int(effective_limit * 0.75)
    if budget <= 0:
        raise ValueError("HOSTED_RUNNER_RSS_BUDGET_INVALID")
    return {
        "rss_budget_bytes": budget,
        "effective_memory_limit_bytes": effective_limit,
        "budget_source": "75_PERCENT_OF_MIN_MEMTOTAL_AND_CGROUP_LIMIT",
        "budget_fraction": 0.75,
        "local_inspection_budget_applied": False,
    }


def read_hosted_runner_rss_budget(
    environ: dict[str, str] | None = None,
    meminfo_path: Path = Path("/proc/meminfo"),
    cgroup_paths: tuple[Path, ...] = (
        Path("/sys/fs/cgroup/memory.max"),
        Path("/sys/fs/cgroup/memory/memory.limit_in_bytes"),
    ),
) -> dict:
    env = os.environ if environ is None else environ
    require_hosted_runner(env)
    override_text = env.get("LOUKSNAPG_HOSTED_RUNNER_RSS_CAP_BYTES", "").strip()
    override = None
    if override_text:
        if not override_text.isdigit():
            raise ValueError("HOSTED_RUNNER_RSS_OVERRIDE_INVALID")
        override = int(override_text)
    if override is not None:
        return calculate_hosted_runner_rss_budget_bytes(0, override_bytes=override)
    mem_total = parse_mem_total_bytes(meminfo_path.read_text(encoding="ascii"))
    cgroup_limit = None
    for candidate in cgroup_paths:
        try:
            value = parse_cgroup_memory_limit_bytes(candidate.read_text(encoding="ascii"))
        except OSError:
            continue
        if value is not None:
            cgroup_limit = value
            break
    return calculate_hosted_runner_rss_budget_bytes(mem_total, cgroup_limit)


def main() -> int:
    try:
        require_hosted_runner()
        runner_rss_budget = read_hosted_runner_rss_budget()
    except (OSError, RuntimeError, ValueError) as exc:
        print(json.dumps({
            "event": "PHASE_2_ADMISSION_DENIED",
            "reason": str(exc)[:240],
            "heavy_model_inference": "NOT_STARTED",
            "global_certification": "NOT_GRANTED",
        }, sort_keys=True), file=sys.stderr, flush=True)
        return 90

    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True, type=Path)
    ap.add_argument("--output-dir", required=True, type=Path)
    ap.add_argument("--report", required=True, type=Path)
    ap.add_argument("--timeout", type=int, default=900)
    ap.add_argument("--candidate-commit", required=True)
    args = ap.parse_args()

    root = args.root.resolve(strict=True)
    out = args.output_dir.resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = args.report.resolve()
    if not (root / "cajita_runtime.py").is_file():
        raise SystemExit("PHASE2_RUNTIME_ROOT_MISSING")
    if not (root / "cajita_task_adapters.py").is_file():
        raise SystemExit("PHASE2_TASK_ADAPTER_REGISTRY_MISSING")

    manifest_path = root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
    if not manifest_path.is_file():
        raise SystemExit("PHASE2_WEIGHT_MANIFEST_MISSING")
    manifest_hash = sha256(manifest_path)

    ancient_path = root / "4. Traductor Inteligente" / "Traducción de lenguas antiguas" / "CAJITA_MODULE.json"
    if not ancient_path.is_file():
        ancient = {
            "status": "BLOCKED_EVIDENCE_MISSING",
            "reason": "ANCIENT_TRANSLATION_MANIFEST_MISSING",
            "next_action": "Locate the exact module manifest and adapter registration without substituting the general translator.",
        }
    else:
        ancient_manifest = json.loads(ancient_path.read_text(encoding="utf-8"))
        registration = ancient_manifest.get("consumer_adapter_registration", {})
        adapter_source = (root / "cajita_task_adapters.py").read_text(encoding="utf-8")
        registered = (
            registration.get("status") not in {"NOT_REGISTERED", None}
            and '"D04_TRADUCCION_LENGUAS_ANTIGUAS"' in adapter_source
        )
        ancient = {
            "status": "ADAPTER_REGISTERED_REQUIRES_NATIVE_TEST" if registered else "BLOCKED_ADAPTER_NOT_REGISTERED",
            "target_id": ancient_manifest.get("target_id"),
            "manifest_sha256": sha256(ancient_path),
            "declared_consumer_adapter": ancient_manifest.get("consumer_adapter"),
            "registration_status": registration.get("status", "NOT_REGISTERED"),
            "functional_state": ancient_manifest.get("functional_state"),
            "defect": "No native task-level consumer adapter is registered for ancient-language translation.",
            "functional_consequence": "The assigned ancient-language route cannot yet be demonstrated end-to-end through its engine.",
            "next_action": "Register an adapter against the existing ancient-language implementation, then run a known-answer native translation test. Do not substitute the general translator.",
        }

    event(
        "PHASE_2_STARTED",
        candidate_commit=args.candidate_commit,
        weight_manifest_sha256=manifest_hash,
        domain_order=[label for _, label in DOMAIN_ORDER],
        execution_environment="GitHub-hosted ubuntu-24.04",
        local_pc_heavy_inference="PROHIBITED_NOT_USED",
    )

    cases_by_domain = {record["domain_id"]: record for record in MODEL_CASES}
    audio = out / "synthetic-test-audio.wav"
    checkpoint_path = out / "LOUKSNAPG_PHASE2_CHECKPOINT.json"
    state = {
        "schema": "LOUKSNAPG_PHASE2_FUNCTIONAL_CHECKPOINT/1.0",
        "candidate_commit": args.candidate_commit,
        "weight_manifest_sha256": manifest_hash,
        "started_at_utc": utc_now(),
        "phase": "PHASE_2_DOMAIN_FUNCTIONAL_TESTS",
        "domain_order": [label for _, label in DOMAIN_ORDER],
        "completed_domains": [],
        "domain_results": [],
        "known_blockers": [],
        "execution_environment_resources": runner_rss_budget,
        "local_pc_inspection_budget_applied": False,
        "global_certification": "NOT_GRANTED",
    }
    write_checkpoint(checkpoint_path, state)
    if ancient["status"] != "ADAPTER_REGISTERED_REQUIRES_NATIVE_TEST":
        state["known_blockers"].append({"domain": "ANCIENT_LANGUAGE_TRANSLATION", **ancient})
        event(
            "MOTOR_BLOCKER_CONFIRMED",
            domain="ANCIENT_LANGUAGE_TRANSLATION",
            status=ancient["status"],
            registration_status=ancient.get("registration_status"),
            next_action=ancient.get("next_action"),
        )

    ok_all = True
    for domain, label in DOMAIN_ORDER:
        if domain == "D04_TRADUCCION_LENGUAS_ANTIGUAS":
            state["domain_results"].append({"domain_id": domain, "label": label, **ancient, "passed": False})
            state["completed_domains"].append(domain)
            state["updated_at_utc"] = utc_now()
            write_checkpoint(checkpoint_path, state)
            event("MOTOR_TEST_SKIPPED_FAIL_CLOSED", domain=domain, label=label,
                  reason=ancient["status"], next_action=ancient.get("next_action"))
            continue

        source = cases_by_domain.get(domain)
        if source is None:
            result = {"domain_id": domain, "label": label, "status": "BLOCKED_TEST_CASE_NOT_FOUND", "passed": False}
            ok_all = False
        else:
            event("MOTOR_TEST_STARTED", domain=domain, label=label, test_id=source.get("task_id"),
                  test_scope="SYNTHETIC_TASK_LEVEL_FUNCTIONAL_EXECUTION", certification="NOT_GRANTED")
            request = json.loads(json.dumps(source))
            request["schema"] = "CAJITA_TASK_REQUEST/1.0"
            request["input"] = dict(request.get("input", {}))
            if request["input"].get("audio_path") == "@AUDIO@":
                if not audio.is_file():
                    make_audio(audio)
                request["input"]["audio_path"] = str(audio)
            started = time.monotonic()
            result = run_case(root, out, request, args.timeout)
            execution_pass = result.get("status") == "PASS_FUNCTIONAL_EXECUTION" and result.get("exit_code") == 0
            quality_pass = result.get("quality_acceptance", {}).get("status") == "PASS"
            required_hashes = ("input_sha256", "output_sha256", "weight_sha256", "module_tree_sha256")
            hashes_pass = all(isinstance(result.get(key), str) and len(result[key]) == 64 for key in required_hashes)
            peak_rss = result.get("peak_rss_bytes")
            resource_pass = (
                isinstance(peak_rss, int) and not isinstance(peak_rss, bool)
                and 0 < peak_rss <= runner_rss_budget["rss_budget_bytes"]
            )
            passed = execution_pass and quality_pass and hashes_pass and resource_pass
            result.update({
                "domain_id": domain,
                "label": label,
                "phase": "PHASE_2",
                "task_level_functional_test": True,
                "quality_check_scope": "FIXED_SYNTHETIC_EXPECTATION",
                "execution_pass": execution_pass,
                "quality_pass": quality_pass,
                "resource_pass": resource_pass,
                "resource_gate": "PEAK_RSS_WITHIN_HOSTED_RUNNER_BUDGET",
                "peak_rss_budget_bytes": runner_rss_budget["rss_budget_bytes"],
                "peak_rss_budget_source": runner_rss_budget["budget_source"],
                "local_inspection_budget_applied": False,
                "required_hashes_pass": hashes_pass,
                "passed": passed,
                "elapsed_wall_seconds": round(time.monotonic() - started, 3),
                "candidate_commit": args.candidate_commit,
            })
            if not passed:
                ok_all = False
            event(
                "MOTOR_TEST_FINISHED",
                domain=domain,
                label=label,
                status=result.get("status"),
                quality_acceptance=result.get("quality_acceptance", {}).get("status"),
                passed=passed,
                elapsed_seconds=result.get("elapsed_seconds"),
                execution_pass=result.get("execution_pass", result.get("status") == "PASS_FUNCTIONAL_EXECUTION" and result.get("exit_code") == 0),
                quality_pass=result.get("quality_pass", result.get("quality_acceptance", {}).get("status") == "PASS"),
                resource_pass=result.get("resource_pass", False),
                peak_rss_bytes=result.get("peak_rss_bytes"),
                peak_rss_budget_bytes=runner_rss_budget["rss_budget_bytes"],
                peak_rss_budget_source=runner_rss_budget["budget_source"],
                local_inspection_budget_applied=False,
                output_sha256=result.get("output_sha256"),
                failure_reason=result.get("failure_reason"),
            )

        state["domain_results"].append(result)
        state["completed_domains"].append(domain)
        state["updated_at_utc"] = utc_now()
        write_checkpoint(checkpoint_path, state)

    registered_results = [r for r in state["domain_results"] if r["domain_id"] in REGISTERED_CASES]
    passed_count = sum(r.get("passed") is True for r in registered_results)
    all_registered_pass = ok_all and len(registered_results) == len(REGISTERED_CASES) and passed_count == len(REGISTERED_CASES)
    phase2_status = (
        "PARTIAL_BLOCKED_ANCIENT_ADAPTER"
        if all_registered_pass and ancient["status"] != "ADAPTER_REGISTERED_REQUIRES_NATIVE_TEST"
        else "REGISTERED_DOMAIN_TEST_FAILURE" if not all_registered_pass
        else "PASS_REGISTERED_DOMAINS"
    )

    result = {
        **state,
        "schema": "LOUKSNAPG_PHASE2_FUNCTIONAL_EVIDENCE/1.0",
        "finished_at_utc": utc_now(),
        "phase_2_status": phase2_status,
        "registered_domain_tests_passed": passed_count,
        "registered_domain_tests_expected": len(REGISTERED_CASES),
        "ancient_translation": ancient,
        "next_action": "RUN_PHASE_3_ROUTE_AND_WIRING_TESTS; RESOLVE_ANCIENT_TRANSLATION_ADAPTER_GAP",
        "functional_status": "PARTIAL" if all_registered_pass and phase2_status.startswith("PARTIAL") else (
            "PASS_FOR_REGISTERED_SCOPE" if all_registered_pass else "FAIL"
        ),
        "semantic_quality_equivalence": "NOT_ESTABLISHED",
        "global_certification": "NOT_GRANTED",
        "certification_reason": "Fixed synthetic expectations are bounded evidence only; the ancient adapter, full route/integration and independent gates remain pending.",
        "evidence": {
            "weight_manifest_sha256": manifest_hash,
            "ancient_manifest_sha256": ancient.get("manifest_sha256"),
            "checkpoint_file": checkpoint_path.name,
            "candidate_commit": args.candidate_commit,
        },
    }
    write_checkpoint(report_path, result)
    write_checkpoint(checkpoint_path, result)
    event(
        "PHASE_2_CHECKPOINT_WRITTEN",
        candidate_commit=args.candidate_commit,
        phase_2_status=phase2_status,
        registered_domain_tests_passed=passed_count,
        registered_domain_tests_expected=len(REGISTERED_CASES),
        ancient_translation=ancient["status"],
        global_certification="NOT_GRANTED",
        next_action=result["next_action"],
    )
    print(json.dumps({
        "schema": result["schema"],
        "phase_2_status": phase2_status,
        "registered_domain_tests_passed": passed_count,
        "registered_domain_tests_expected": len(REGISTERED_CASES),
        "ancient_translation": ancient["status"],
        "global_certification": "NOT_GRANTED",
        "report": str(report_path),
    }, ensure_ascii=False, indent=2), flush=True)
    return 0 if all_registered_pass else 3


if __name__ == "__main__":
    raise SystemExit(main())
