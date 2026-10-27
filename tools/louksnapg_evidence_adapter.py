#!/usr/bin/env python3
"""Bind runtime task and primitive-probe outcomes into a single 21-target manifest.

This tool only normalizes evidence. It never certifies and never promotes smoke
results to full consumer-task coverage without explicit scope evidence.
"""
from __future__ import annotations
import argparse, hashlib, json, re
from pathlib import Path
from typing import Any
import louksnapg_integral_gate as gate

SCHEMA = "LOUKSNAPG_FUNCTIONAL_EVIDENCE/1.0"
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
MODEL_DOMAIN_TO_TARGET = {
    "D01_CEREBRO": "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION": "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCTOR_INTELIGENTE": "D04_TRADUCCION_GENERAL",
    "D05_INTELIGENCIA_DOCUMENTAL": "D05_DOCLING",
    "D06_SISTEMA_INTELIGENTE": "D06_ANALISIS_AVANZADO",
}
PRIMITIVE_SCOPE_COMPLETE = {
    "D05_CALIBRE": "PASS_FOR_TXT_TO_EPUB_PRIMITIVE_ONLY",
    "D06_ARCHIVADO_DETECCION": "PASS_FOR_ZIP_FILE_IDENTIFICATION_ONLY",
    "D06_MIGRACION_PERSISTENCIA": "PASS_FOR_DATABASE_MIGRATION_AND_LOCAL_PERSISTENCE_PRIMITIVES",
    "D06_TESTING": "PASS_FOR_TEST_RUNNER_PRIMITIVE_ONLY",
}

def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()

def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("EVIDENCE_INPUT_NOT_REGULAR_FILE:" + path.name)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_INPUT_ROOT_NOT_OBJECT:" + path.name)
    return value

def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA_RE.fullmatch(value))

def _primitive_scope_complete(target_id: str, row: dict[str, Any]) -> bool:
    if row.get("status") != "PASS_PRIMITIVE_SMOKE":
        return False
    details = row.get("details", {})
    result = details.get("result", {}) if isinstance(details, dict) else {}
    expected = PRIMITIVE_SCOPE_COMPLETE.get(target_id)
    return bool(expected and isinstance(result, dict) and result.get("consumer_task_equivalence") == expected)

def build_evidence(task_report: dict[str, Any], extended_report: dict[str, Any], bundle_sha256: str,
                   source_commit: str, runtime_root: Path) -> dict[str, Any]:
    if not COMMIT_RE.fullmatch(source_commit):
        raise ValueError("EXPECTED_SOURCE_COMMIT_INVALID")
    if not _is_sha(bundle_sha256):
        raise ValueError("BUNDLE_SHA256_INVALID")
    if extended_report.get("schema") != "CAJITA_EXTENDED_TARGET_E2E/1.0":
        raise ValueError("EXTENDED_REPORT_SCHEMA_MISMATCH")
    if extended_report.get("source_commit") != source_commit:
        raise ValueError("EXTENDED_REPORT_SOURCE_COMMIT_MISMATCH")
    if extended_report.get("bundle_sha256") != bundle_sha256:
        raise ValueError("EXTENDED_REPORT_BUNDLE_SHA256_MISMATCH")
    if task_report.get("schema") != "LOUKSNA1_TASK_ADAPTER_EVIDENCE/1.0":
        raise ValueError("TASK_REPORT_SCHEMA_MISMATCH")

    runtime_files = {
        "adapter_runtime_sha256": runtime_root / "cajita_task_adapters.py",
        "target_engine_adapter_runtime_sha256": runtime_root / "cajita_target_adapters.py",
        "weight_manifest_sha256": runtime_root / "CAJITA_RUNTIME_V1" / "weights_manifest.json",
    }
    binding_failures = []
    for field, path in runtime_files.items():
        if path.is_symlink() or not path.is_file():
            binding_failures.append("RUNTIME_BINDING_FILE_MISSING:" + field)
        elif task_report.get(field) != sha256_file(path):
            binding_failures.append("TASK_REPORT_RUNTIME_HASH_MISMATCH:" + field)

    task_rows = task_report.get("task_results", [])
    engine_rows = task_report.get("target_engine_results", [])
    extended_rows = extended_report.get("targets", [])
    if not isinstance(task_rows, list):
        task_rows = []
        binding_failures.append("TASK_RESULTS_NOT_A_LIST")
    if not isinstance(engine_rows, list):
        engine_rows = []
        binding_failures.append("TARGET_ENGINE_RESULTS_NOT_A_LIST")
    if not isinstance(extended_rows, list):
        extended_rows = []
        binding_failures.append("EXTENDED_TARGETS_NOT_A_LIST")

    results: dict[str, dict[str, Any]] = {}
    for raw in task_rows:
        if not isinstance(raw, dict):
            binding_failures.append("MODEL_TASK_ROW_INVALID")
            continue
        target_id = raw.get("target_id") or MODEL_DOMAIN_TO_TARGET.get(raw.get("domain_id"))
        if target_id not in gate.MODEL_TARGETS:
            binding_failures.append("MODEL_TASK_TARGET_UNREGISTERED:" + str(target_id))
            continue
        if target_id in results:
            binding_failures.append("DUPLICATE_TARGET_RESULT:" + target_id)
            continue
        quality = raw.get("quality_acceptance", {}) if isinstance(raw.get("quality_acceptance"), dict) else {}
        quality_status = quality.get("status", "NOT_ESTABLISHED")
        execution_pass = raw.get("status") == "PASS_FUNCTIONAL_EXECUTION" and raw.get("exit_code") == 0
        synthetic = quality.get("reference_kind") == "FIXED_SYNTHETIC_EXPECTATION" or "synthetic" in str(task_report.get("inputs", "")).casefold()
        results[target_id] = {
            "target_id": target_id, "evidence_kind": "MODEL_TASK",
            "status": "PASS_FUNCTIONAL_EXECUTION" if execution_pass else str(raw.get("status", "MISSING")),
            "exit_code": raw.get("exit_code"), "test_case_count": 1,
            "test_cases_passed": 1 if execution_pass and quality_status == "PASS" else 0,
            "output_char_count": int(raw.get("output_char_count", quality.get("output_char_count", 0)) or 0),
            "input_sha256": raw.get("input_sha256"), "output_sha256": raw.get("output_sha256"),
            "runtime_sha256": task_report.get("adapter_runtime_sha256"),
            "entrypoint_sha256": raw.get("entrypoint_sha256"),
            "module_tree_sha256": raw.get("module_tree_sha256"), "weight_sha256": raw.get("weight_sha256"),
            "model_load_status": "PASS" if execution_pass and _is_sha(raw.get("weight_sha256")) else "FAIL",
            "model_inference_observed": bool(isinstance(raw.get("generated_token_count"), int) and raw["generated_token_count"] > 0),
            "upstream_model_id": gate.OFFICIAL_MODEL_IDS[target_id],
            "upstream_source_url": gate.OFFICIAL_SOURCE_URLS[target_id],
            "upstream_revision_sha256": gate.OFFICIAL_SOURCE_REVISIONS[target_id],
            "model_repository_revision_commit": gate.OFFICIAL_MODEL_REVISIONS[target_id],
            "quality_status": quality_status, "quality_check_id": quality.get("check_id"),
            "quality_output_sha256": quality.get("output_text_sha256"),
            "generated_token_count": raw.get("generated_token_count"), "peak_rss_bytes": raw.get("peak_rss_bytes"),
            "synthetic_only": bool(synthetic),
            "scope_complete": bool(execution_pass and quality_status == "PASS" and not synthetic),
            "evidence_record_sha256": sha256_bytes(canonical_json(raw)),
        }

    for raw in engine_rows:
        if not isinstance(raw, dict):
            binding_failures.append("ENGINE_ROW_INVALID")
            continue
        target_id = raw.get("target_id")
        if target_id not in gate.EXPECTED_TARGET_IDS or target_id in gate.MODEL_TARGETS:
            binding_failures.append("ENGINE_TARGET_UNREGISTERED:" + str(target_id))
            continue
        if target_id in results:
            binding_failures.append("DUPLICATE_TARGET_RESULT:" + target_id)
            continue
        identities = raw.get("required_file_identities", [])
        results[target_id] = {
            "target_id": target_id, "evidence_kind": "PRIMITIVE_SMOKE",
            "status": str(raw.get("status", "MISSING")), "exit_code": raw.get("exit_code"),
            "test_case_count": 1,
            "test_cases_passed": 1 if raw.get("status") == "PASS_TARGET_ENGINE_EXECUTION" and raw.get("exit_code") == 0 else 0,
            "primitive_scope": raw.get("execution_scope"), "scope_complete": False,
            "consumer_task_adapter_completion": raw.get("consumer_task_adapter_completion", "NOT_ESTABLISHED"),
            "task_coverage": raw.get("task_coverage", "NOT_ESTABLISHED"),
            "primitive_evidence_sha256": sha256_bytes(canonical_json(raw)),
            "required_file_identity_count": len(identities) if isinstance(identities, list) else 0,
            "required_file_identity_manifest_sha256": sha256_bytes(canonical_json(identities)),
            "primitive_result_sha256": sha256_bytes(canonical_json(raw.get("result"))),
            "runtime_sha256": task_report.get("target_engine_adapter_runtime_sha256"),
            "synthetic_only": False, "certification": "NOT_GRANTED",
        }

    for raw in extended_rows:
        if not isinstance(raw, dict):
            binding_failures.append("EXTENDED_TARGET_ROW_INVALID")
            continue
        target_id = raw.get("target_id")
        if target_id not in gate.EXPECTED_TARGET_IDS or target_id in gate.MODEL_TARGETS:
            binding_failures.append("EXTENDED_TARGET_UNREGISTERED:" + str(target_id))
            continue
        if target_id in results:
            binding_failures.append("DUPLICATE_TARGET_RESULT:" + target_id)
            continue
        status = raw.get("status", "MISSING")
        details = raw.get("details", {})
        result = details.get("result", {}) if isinstance(details, dict) else {}
        runtime_sha = None
        for candidate in (
            result.get("runtime_identity", {}).get("executable_sha256") if isinstance(result.get("runtime_identity"), dict) else None,
            result.get("binary_sha256"), result.get("rqlite_server_binary_sha256"),
            result.get("wheel_sha256"), result.get("cmake_sha256"),
            result.get("source_descriptor_sha256"), result.get("module_descriptor_sha256"),
        ):
            if _is_sha(candidate):
                runtime_sha = candidate
                break
        primitive_pass = status == "PASS_PRIMITIVE_SMOKE"
        results[target_id] = {
            "target_id": target_id, "evidence_kind": "PRIMITIVE_SMOKE", "status": status,
            "exit_code": 0 if primitive_pass else (125 if status == "BLOCKED" else 1),
            "test_case_count": 1, "test_cases_passed": 1 if primitive_pass else 0,
            "primitive_scope": raw.get("purpose"), "scope_complete": _primitive_scope_complete(target_id, raw),
            "primitive_evidence_sha256": raw.get("evidence_sha256") if _is_sha(raw.get("evidence_sha256")) else sha256_bytes(canonical_json(raw)),
            "runtime_sha256": runtime_sha,
            "module_descriptor_sha256": result.get("module_descriptor_sha256") if isinstance(result, dict) else None,
            "source_descriptor_sha256": result.get("source_descriptor_sha256") if isinstance(result, dict) else None,
            "consumer_task_equivalence": result.get("consumer_task_equivalence") if isinstance(result, dict) else None,
            "reason": raw.get("reason") or (details.get("reason") if isinstance(details, dict) else None),
            "synthetic_only": False, "certification": "NOT_GRANTED",
        }

    for target_id in gate.EXPECTED_TARGET_IDS:
        if target_id not in results:
            results[target_id] = {
                "target_id": target_id, "evidence_kind": "MISSING", "status": "MISSING",
                "exit_code": None, "test_case_count": 0, "test_cases_passed": 0,
                "scope_complete": False, "synthetic_only": True,
            }
    rows = [results[target_id] for target_id in gate.EXPECTED_TARGET_IDS]
    model_rows = [row for row in rows if row.get("evidence_kind") == "MODEL_TASK"]
    all_model_quality_pass = len(model_rows) == len(gate.MODEL_TARGETS) and all(
        row.get("quality_status") == "PASS" and row.get("scope_complete") is True for row in model_rows
    )
    all_target_scope_complete = all(
        row.get("scope_complete") is True
        and row.get("status") in {"PASS_FUNCTIONAL_EXECUTION", "PASS_PRIMITIVE_SMOKE", "PASS_TARGET_ENGINE_EXECUTION"}
        for row in rows
    )
    synthetic_only = any(row.get("synthetic_only") is True for row in rows)
    failures = list(binding_failures)
    if len(task_rows) != 5: failures.append("MODEL_TASK_COUNT_NOT_FIVE")
    if len(engine_rows) != 6: failures.append("TARGET_ENGINE_COUNT_NOT_SIX")
    if len(extended_rows) != 10: failures.append("EXTENDED_TARGET_COUNT_NOT_TEN")
    return {
        "schema": SCHEMA, "source_commit": source_commit, "bundle_sha256": bundle_sha256,
        "execution_mode": "REAL_RUNTIME_EXECUTION" if task_rows else "NOT_ESTABLISHED",
        "synthetic_only": synthetic_only,
        "functional_status": "PASS_ALL_21_REQUIRED_TARGETS" if all_target_scope_complete and not synthetic_only and not failures else "HOLD_NOT_CERTIFIED",
        "semantic_quality_status": "PASS" if all_model_quality_pass and not synthetic_only else "FAIL",
        "host_matrix_status": "NOT_ESTABLISHED", "rollback_status": "NOT_ESTABLISHED",
        "axiom_binding_status": "NOT_ESTABLISHED", "block_binding_status": "NOT_ESTABLISHED",
        "target_results": rows,
        "evidence_sources": {
            "task_report_sha256": sha256_bytes(canonical_json(task_report)),
            "extended_report_sha256": sha256_bytes(canonical_json(extended_report)),
            "runtime_adapter_sha256": task_report.get("adapter_runtime_sha256"),
            "target_engine_adapter_sha256": task_report.get("target_engine_adapter_runtime_sha256"),
            "weight_manifest_sha256": task_report.get("weight_manifest_sha256"),
        },
        "binding_failures": sorted(set(failures)), "decision": "HOLD_NOT_CERTIFIED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--task-report", type=Path, required=True)
    parser.add_argument("--extended-report", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.bundle.is_symlink() or not args.bundle.is_file():
            raise ValueError("BUNDLE_NOT_REGULAR_FILE")
        if args.runtime_root.is_symlink() or not args.runtime_root.is_dir():
            raise ValueError("RUNTIME_ROOT_NOT_DIRECTORY")
        evidence = build_evidence(
            load_json(args.task_report), load_json(args.extended_report),
            sha256_file(args.bundle), args.expected_source_commit, args.runtime_root.resolve(),
        )
    except Exception as exc:
        evidence = {
            "schema": SCHEMA, "source_commit": args.expected_source_commit,
            "bundle_sha256": sha256_file(args.bundle) if args.bundle.is_file() and not args.bundle.is_symlink() else None,
            "execution_mode": "NOT_ESTABLISHED", "synthetic_only": True,
            "functional_status": "HOLD_NOT_CERTIFIED", "semantic_quality_status": "NOT_ESTABLISHED",
            "host_matrix_status": "NOT_ESTABLISHED", "rollback_status": "NOT_ESTABLISHED",
            "axiom_binding_status": "NOT_ESTABLISHED", "block_binding_status": "NOT_ESTABLISHED",
            "target_results": [], "binding_failures": [type(exc).__name__ + ":" + str(exc)[:500]],
            "decision": "HOLD_NOT_CERTIFIED",
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(evidence, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "schema": evidence.get("schema"), "source_commit": evidence.get("source_commit"),
        "bundle_sha256": evidence.get("bundle_sha256"),
        "observed_target_count": len(evidence.get("target_results", [])),
        "functional_status": evidence.get("functional_status"),
        "semantic_quality_status": evidence.get("semantic_quality_status"),
        "binding_failures": evidence.get("binding_failures", []), "decision": evidence.get("decision"),
    }, ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
