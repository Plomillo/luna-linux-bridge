#!/usr/bin/env python3
"""LOUKSNAPG required-domain functional probe; diagnostics only, never certification.

Runs only the four registered model tasks in scope (Cerebro, Whisper, general
translation, Qwen) and evaluates whether ancient-language translation has a
dedicated task adapter. Heavy execution belongs to a hosted repository runner.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

REQUIRED_DOMAINS = {
    "D01_CEREBRO": "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION": "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCTOR_INTELIGENTE": "D04_TRADUCCION_GENERAL",
    "D06_SISTEMA_INTELIGENTE": "D06_ANALISIS_AVANZADO",
}
ANCIENT_TARGET = "D04_TRADUCCION_LENGUAS_ANTIGUAS"
SCHEMA = "LOUKSNAPG_REQUIRED_DOMAIN_EVIDENCE/1.0"


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git_value(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def load_e2e_support(root: Path):
    helper_path = root / "tools" / "cajita_task_e2e.py"
    spec = importlib.util.spec_from_file_location("_louksnapg_cajita_e2e_support", helper_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CANNOT_LOAD_EXISTING_TASK_E2E_HELPERS")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def find_id(value, wanted):
    if isinstance(value, dict):
        if value.get("id") == wanted:
            return value
        for child in value.values():
            found = find_id(child, wanted)
            if found is not None:
                return found
    elif isinstance(value, list):
        for child in value:
            found = find_id(child, wanted)
            if found is not None:
                return found
    return None


def check_ancient_route(root: Path) -> dict:
    sys.path.insert(0, str(root))
    try:
        import cajita_task_adapters as task_adapters
        route_registry = json.loads((root / "command_subdomain_routing.json").read_text(encoding="utf-8"))
        descriptor_path = root / "4. Traductor Inteligente" / "Traducción de lenguas antiguas" / "CAJITA_MODULE.json"
        descriptor = json.loads(descriptor_path.read_text(encoding="utf-8"))
        target_id = descriptor.get("target_id")
        registered_targets = {row.get("target") for row in task_adapters.ADAPTERS.values()}
        route_entry = find_id(route_registry, target_id)
        target_has_adapter = target_id in registered_targets
        language_code_registered = "grc" in task_adapters.LANGS

        request = {
            "schema": task_adapters.REQUEST_SCHEMA,
            "task_id": "louksnapg-ancient-greek-adapter-gate",
            "domain_id": "D04_TRADUCTOR_INTELIGENTE",
            "target_id": target_id,
            "operation": "translate_text",
            "input": {"text": "Χαῖρε κόσμε", "src_lang": "grc", "tgt_lang": "spa"},
            "limits": {"timeout_seconds": 30, "max_new_tokens": 16},
        }
        try:
            normalized = task_adapters.normalize(request, root, timeout_cap=30)
            normalization = {
                "status": "PASS" if normalized.get("target_id") == target_id else "FAIL_GENERAL_TRANSLATOR_FALLTHROUGH",
                "selected_target_id": normalized.get("target_id"),
                "selected_adapter_id": normalized.get("adapter_id"),
            }
        except task_adapters.AdapterError as exc:
            normalization = {"status": "BLOCKED_BEFORE_MODEL_EXECUTION", "reason": str(exc)}

        ancient_root = root / "4. Traductor Inteligente" / "Traducción de lenguas antiguas"
        candidate_assets = []
        for suffix in (".fst", ".lexc", ".xfst", ".safetensors", ".gguf", ".onnx"):
            candidate_assets.extend(p.relative_to(ancient_root).as_posix() for p in ancient_root.rglob("*" + suffix))
        passed = target_has_adapter and language_code_registered and normalization["status"] == "PASS"
        return {
            "target_id": target_id,
            "manifest_sha256": sha256_file(descriptor_path),
            "route_registry_entry_present": route_entry is not None,
            "route_registry_support_assets": (route_entry or {}).get("support_assets"),
            "dedicated_task_adapter_registered": target_has_adapter,
            "ancient_greek_code_registered_in_current_translation_adapter": language_code_registered,
            "task_normalization_probe": normalization,
            "candidate_engine_or_lexicon_assets_found": sorted(candidate_assets),
            "status": "PASS" if passed else "BLOCKED_REQUIRED_FUNCTION_NOT_REGISTERED",
            "certification": "NOT_GRANTED",
            "inference_attempted": False,
        }
    finally:
        try:
            sys.path.remove(str(root))
        except ValueError:
            pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="cajita-luna-runtime")
    parser.add_argument("--output-dir", default="evidence/required-domain")
    parser.add_argument("--output", default="evidence/required-domain/report.json")
    parser.add_argument("--timeout", type=int, default=300)
    args = parser.parse_args()

    root = Path(args.root).resolve(strict=True)
    outdir = Path(args.output_dir).resolve()
    outdir.mkdir(parents=True, exist_ok=True)
    output = Path(args.output).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {
        "schema": SCHEMA,
        "generated_at_utc": utc_now(),
        "source_commit": "UNAVAILABLE",
        "source_tree": "UNAVAILABLE",
        "functional_status": "NOT_ESTABLISHED",
        "global_certification": "NOT_GRANTED",
        "independent_validation_G23": "NOT_PERFORMED",
        "certification_G24": "NOT_GRANTED",
        "phases": {},
        "required_model_tasks": [],
        "ancient_language_translation": {},
        "limitations": [
            "Fixed synthetic prompts are an initial functional probe, not broad semantic-quality certification.",
            "Reference-model equivalence is not established by these tests.",
            "A successful test run never propagates global certification.",
        ],
    }

    try:
        report["source_commit"] = git_value(root.parent, "rev-parse", "HEAD")
        report["source_tree"] = git_value(root.parent, "rev-parse", "HEAD^{tree}")
        report["phases"]["1"] = {
            "status": "PASS_CANDIDATE_PINNED",
            "candidate_commit": report["source_commit"],
            "candidate_tree": report["source_tree"],
            "workflow_run_commit": os.environ.get("GITHUB_SHA", "NOT_IN_GITHUB_ACTIONS"),
        }

        helper = load_e2e_support(root.parent)
        import sys as _sys
        _sys.path.insert(0, str(root))
        try:
            import cajita_task_adapters as task_adapters
            weights_manifest = root / "CAJITA_RUNTIME_V1" / "weights_manifest.json"
            report["task_adapter_sha256"] = sha256_file(root / "cajita_task_adapters.py")
            report["router_sha256"] = sha256_file(root / "cajita_router.py")
            report["routing_registry_sha256"] = sha256_file(root / "command_subdomain_routing.json")
            report["weights_manifest_sha256"] = sha256_file(weights_manifest)
            report["registered_task_adapter_targets"] = sorted({row.get("target") for row in task_adapters.ADAPTERS.values()})
        finally:
            try:
                _sys.path.remove(str(root))
            except ValueError:
                pass

        cases = [row for row in helper.MODEL_CASES if row["domain_id"] in REQUIRED_DOMAINS]
        observed_domains = {row["domain_id"] for row in cases}
        if observed_domains != set(REQUIRED_DOMAINS):
            raise RuntimeError("REQUIRED_DOMAIN_E2E_CASES_MISSING:" + ",".join(sorted(set(REQUIRED_DOMAINS) - observed_domains)))

        audio = outdir / "known-speech-hello-world.wav"
        helper.make_audio(audio)
        rows = []
        for source in cases:
            request = json.loads(json.dumps(source))
            request["schema"] = "CAJITA_TASK_REQUEST/1.0"
            request["limits"]["timeout_seconds"] = min(int(request.get("limits", {}).get("timeout_seconds", args.timeout)), args.timeout)
            request["input"] = dict(request["input"])
            if request["input"].get("audio_path") == "@AUDIO@":
                request["input"]["audio_path"] = str(audio)
            rows.append(helper.run_case(root, outdir, request, args.timeout))
        for row in rows:
            domain = row.get("domain_id", "UNKNOWN")
            expected_target = REQUIRED_DOMAINS.get(domain)
            hashes_valid = all(isinstance(row.get(key), str) and len(row[key]) == 64 for key in ("input_sha256", "output_sha256", "weight_sha256", "module_tree_sha256"))
            row["expected_target_id"] = expected_target
            row["identity_and_resource_gate"] = "PASS" if row.get("target_id") == expected_target and hashes_valid and isinstance(row.get("peak_rss_bytes"), int) and 0 < row["peak_rss_bytes"] <= 1_073_741_824 else "FAIL"
        report["required_model_tasks"] = rows
        report["phases"]["2"] = {
            "status": "EVIDENCE_CAPTURED",
            "required_model_domains": list(REQUIRED_DOMAINS),
            "synthetic_functional_acceptance": {row["domain_id"]: row.get("quality_acceptance", {}).get("status", row.get("status")) for row in rows},
            "scope": "CEREBRO_QWEN_GENERAL_TRANSLATION_WHISPER_PLUS_ANCIENT_TRANSLATION_ADAPTER_GATE",
        }
        report["phases"]["3"] = {
            "status": "ROUTE_TESTS_AND_TASK_DISPATCH_EXECUTED",
            "router_regression": "RUN_BY_WORKFLOW",
            "task_adapter_regression": "RUN_BY_WORKFLOW",
            "model_tasks_execute_through_registered_task_adapters": True,
        }
        report["ancient_language_translation"] = check_ancient_route(root)
        required_pass = all(
            row.get("status") == "PASS_FUNCTIONAL_EXECUTION"
            and row.get("exit_code") == 0
            and row.get("quality_acceptance", {}).get("status") == "PASS"
            and row.get("identity_and_resource_gate") == "PASS"
            for row in rows
        )
        report["phases"]["4"] = {
            "status": "NO_UNJUSTIFIED_REPAIR_APPLIED",
            "ancient_translation_defect": report["ancient_language_translation"]["status"],
            "repair_policy": "No substitute engine or fabricated lexicon; continue independent domains and preserve exact failure evidence.",
        }
        report["phases"]["5"] = {
            "status": "PASS_FOCUSED_RESULTS_RECORDED" if all(row.get("exit_code") is not None for row in rows) else "INCOMPLETE",
            "required_model_task_statuses": {row["domain_id"]: row.get("status") for row in rows},
        }
        report["phases"]["6"] = {
            "status": "PARTIAL_INTEGRATION_EVIDENCE",
            "registered_model_routes": "TASK_ADAPTER_EXECUTION_PROBED",
            "ancient_language_route": report["ancient_language_translation"]["status"],
        }
        report["phases"]["7"] = {
            "status": "NOT_GRANTED",
            "reason": "Required ancient-language consumer adapter/engine path is not registered; G23 independent validation and G24 certification have not been performed.",
        }
        report["functional_status"] = "PASS_REQUIRED_REGISTERED_MODEL_TASKS_WITH_ANCIENT_BLOCKER" if required_pass else "FUNCTIONAL_DEFECTS_OR_MISSING_EVIDENCE"
        report["required_registered_model_tasks_passed"] = required_pass
        report["global_certification"] = "NOT_GRANTED"
    except Exception as exc:
        report["functional_status"] = "FAIL_EVIDENCE_HARNESS"
        report["harness_error"] = type(exc).__name__ + ":" + str(exc)[:900]
        report["global_certification"] = "NOT_GRANTED"
        report["phases"].setdefault("7", {"status": "NOT_GRANTED", "reason": "Evidence harness incomplete."})

    output.write_text(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": SCHEMA,
        "source_commit": report.get("source_commit"),
        "functional_status": report.get("functional_status"),
        "required_model_tasks": {
            row.get("domain_id", "UNKNOWN"): {
                "status": row.get("status"),
                "target_id": row.get("target_id"),
                "quality": row.get("quality_acceptance", {}).get("status"),
                "rss_bytes": row.get("peak_rss_bytes"),
            } for row in report.get("required_model_tasks", [])
        },
        "ancient_language_translation": {
            "status": report.get("ancient_language_translation", {}).get("status"),
            "dedicated_task_adapter_registered": report.get("ancient_language_translation", {}).get("dedicated_task_adapter_registered"),
            "normalization_probe": report.get("ancient_language_translation", {}).get("task_normalization_probe"),
        },
        "global_certification": "NOT_GRANTED",
        "evidence_file": str(output),
    }, sort_keys=True, ensure_ascii=False, indent=2))
    # Evidence collection itself completes; the workflow's final gate evaluates outcomes.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
