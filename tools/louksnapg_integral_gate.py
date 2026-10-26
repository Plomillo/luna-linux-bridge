#!/usr/bin/env python3
"""Fail-closed eligibility gate for integral LOUKSNAPG functional evidence.

This checks evidence shape and subject binding only. It is not G23, G24, or a
model-quality oracle; cryptographic attestation and independent re-execution remain
separate release gates. Synthetic harness reports can never pass this gate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

SCHEMA = "LOUKSNAPG_FUNCTIONAL_EVIDENCE/1.0"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_TARGET_IDS = (
    "D01_CEREBRO_ROOT",
    "D02_CONFESION_ECLESIAL_REFORMADA",
    "D02_MULTI_INTERDISCIPLINAR",
    "D02_ORQUESTADOR",
    "D03_TRANSCRIPCION_ROOT",
    "D04_HERMENEUTICA_HG",
    "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "D04_TRADUCCION_GENERAL",
    "D05_CALIBRE",
    "D05_DOCLING",
    "D06_ANTI_ALUCINACIONES",
    "D06_ANALISIS_AVANZADO",
    "D06_ARCHIVADO_DETECCION",
    "D06_COGNITIVE_CI_CD",
    "D06_CONSOLA",
    "D06_MEMORIA_GOBERNADA",
    "D06_MIGRACION_PERSISTENCIA",
    "D06_MOTOR_PROTOCOLAR",
    "D06_PORTABILIDAD_BASE",
    "D06_RUNTIME_ANDROID_WINDOWS",
    "D06_TESTING",
)
MODEL_TARGETS = {
    "D01_CEREBRO_ROOT",
    "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCCION_GENERAL",
    "D05_DOCLING",
    "D06_ANALISIS_AVANZADO",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def evaluate_evidence(evidence: object, bundle_sha256: str, expected_source_commit: str) -> dict:
    """Return a deterministic PASS/HOLD decision for a source- and artifact-bound envelope."""
    failures: list[str] = []
    if not isinstance(evidence, dict):
        evidence = {}
        failures.append("EVIDENCE_ROOT_NOT_OBJECT")

    if evidence.get("schema") != SCHEMA:
        failures.append("FUNCTIONAL_EVIDENCE_SCHEMA_MISMATCH")
    source_commit = evidence.get("source_commit")
    if not isinstance(source_commit, str) or not COMMIT_RE.fullmatch(source_commit):
        failures.append("FUNCTIONAL_EVIDENCE_SOURCE_COMMIT_INVALID")
    elif source_commit != expected_source_commit:
        failures.append("FUNCTIONAL_EVIDENCE_SOURCE_COMMIT_MISMATCH")

    reported_bundle_sha = evidence.get("bundle_sha256")
    if not _is_sha(reported_bundle_sha):
        failures.append("FUNCTIONAL_EVIDENCE_BUNDLE_SHA256_INVALID")
    elif reported_bundle_sha != bundle_sha256:
        failures.append("FUNCTIONAL_EVIDENCE_BUNDLE_SHA256_MISMATCH")

    if evidence.get("execution_mode") != "REAL_RUNTIME_EXECUTION":
        failures.append("REAL_RUNTIME_EXECUTION_NOT_ESTABLISHED")
    if evidence.get("synthetic_only") is not False:
        failures.append("SYNTHETIC_ONLY_OR_UNPROVEN_EVIDENCE")
    if evidence.get("functional_status") != "PASS_ALL_21_REQUIRED_TARGETS":
        failures.append("ALL_21_TARGET_FUNCTIONS_NOT_PASSED")
    for field in ("semantic_quality_status", "host_matrix_status", "rollback_status",
                  "axiom_binding_status", "block_binding_status"):
        if evidence.get(field) != "PASS":
            failures.append(field.upper() + "_NOT_PASS")

    rows = evidence.get("target_results")
    if not isinstance(rows, list):
        rows = []
        failures.append("TARGET_RESULTS_NOT_A_LIST")
    by_id: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("target_id"), str):
            failures.append("TARGET_RESULT_ROW_INVALID")
            continue
        target_id = row["target_id"]
        if target_id in by_id:
            failures.append("DUPLICATE_TARGET_ID:" + target_id)
        else:
            by_id[target_id] = row
    expected, actual = set(EXPECTED_TARGET_IDS), set(by_id)
    for missing in sorted(expected - actual):
        failures.append("TARGET_EVIDENCE_MISSING:" + missing)
    for extra in sorted(actual - expected):
        failures.append("UNREGISTERED_TARGET_EVIDENCE:" + extra)

    target_checks = []
    for target_id in EXPECTED_TARGET_IDS:
        row = by_id.get(target_id)
        if row is None:
            continue
        target_failures = []
        if row.get("status") != "PASS_FUNCTIONAL_EXECUTION":
            target_failures.append("FUNCTIONAL_EXECUTION_NOT_PASS")
        if row.get("exit_code") != 0:
            target_failures.append("EXIT_CODE_NOT_ZERO")
        cases = row.get("test_case_count")
        passed_cases = row.get("test_cases_passed")
        if isinstance(cases, bool) or not isinstance(cases, int) or cases < 1:
            target_failures.append("TEST_CASE_COUNT_INVALID")
        if isinstance(passed_cases, bool) or not isinstance(passed_cases, int) or passed_cases != cases:
            target_failures.append("NOT_ALL_BEHAVIOR_CASES_PASSED")
        if isinstance(row.get("output_char_count"), bool) or not isinstance(row.get("output_char_count"), int) or row.get("output_char_count") <= 0:
            target_failures.append("NONEMPTY_OUTPUT_NOT_ESTABLISHED")
        for field in ("input_sha256", "output_sha256", "runtime_sha256", "module_tree_sha256"):
            if not _is_sha(row.get(field)):
                target_failures.append(field.upper() + "_INVALID")
        if row.get("synthetic_only") is not False:
            target_failures.append("TARGET_EVIDENCE_SYNTHETIC_OR_UNPROVEN")

        if target_id in MODEL_TARGETS:
            if row.get("model_load_status") != "PASS" or row.get("model_inference_observed") is not True:
                target_failures.append("REAL_MODEL_LOAD_OR_INFERENCE_NOT_ESTABLISHED")
            if not _is_sha(row.get("weight_sha256")):
                target_failures.append("WEIGHT_SHA256_INVALID")
            if not isinstance(row.get("upstream_model_id"), str) or not row["upstream_model_id"].strip():
                target_failures.append("UPSTREAM_MODEL_ID_MISSING")
            if not isinstance(row.get("upstream_source_url"), str) or not row["upstream_source_url"].startswith("https://"):
                target_failures.append("UPSTREAM_SOURCE_URL_MISSING")
            if not COMMIT_RE.fullmatch(str(row.get("upstream_revision_sha256", ""))):
                target_failures.append("UPSTREAM_REVISION_NOT_PINNED_TO_COMMIT")
        target_checks.append({"target_id": target_id, "status": "PASS" if not target_failures else "HOLD",
                              "failures": target_failures})
        failures.extend("TARGET:" + target_id + ":" + item for item in target_failures)

    g23 = evidence.get("g23")
    if not isinstance(g23, dict):
        failures.append("G23_EVIDENCE_MISSING")
        g23 = {}
    if g23.get("status") != "PASS":
        failures.append("G23_NOT_PASS")
    if g23.get("source_commit") != expected_source_commit:
        failures.append("G23_SOURCE_COMMIT_MISMATCH")
    if g23.get("subject_bundle_sha256") != bundle_sha256:
        failures.append("G23_SUBJECT_BUNDLE_MISMATCH")
    if g23.get("attestation_verified") is not True:
        failures.append("G23_ATTESTATION_NOT_VERIFIED")

    return {
        "schema": "LOUKSNAPG_INTEGRAL_FUNCTIONAL_GATE/1.0",
        "decision": "PASS" if not failures else "HOLD",
        "eligible_for_g24": not failures,
        "source_commit": expected_source_commit,
        "bundle_sha256": bundle_sha256,
        "expected_target_count": len(EXPECTED_TARGET_IDS),
        "observed_target_count": len(actual),
        "model_backed_target_count": len(MODEL_TARGETS),
        "target_checks": target_checks,
        "failure_count": len(failures),
        "failures": sorted(set(failures)),
        "global_certification": "NOT_GRANTED",
        "note": "Passing this envelope check does not replace independent re-execution, cryptographic G23 verification, or G24 authorization."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if not COMMIT_RE.fullmatch(args.expected_source_commit):
            raise ValueError("EXPECTED_SOURCE_COMMIT_INVALID")
        if args.evidence.is_symlink() or not args.evidence.is_file():
            raise ValueError("FUNCTIONAL_EVIDENCE_NOT_REGULAR_FILE")
        if args.bundle.is_symlink() or not args.bundle.is_file():
            raise ValueError("BUNDLE_NOT_REGULAR_FILE")
        evidence = json.loads(args.evidence.read_text(encoding="utf-8"))
        report = evaluate_evidence(evidence, sha256_file(args.bundle), args.expected_source_commit)
    except Exception as exc:
        report = {
            "schema": "LOUKSNAPG_INTEGRAL_FUNCTIONAL_GATE/1.0",
            "decision": "HOLD",
            "eligible_for_g24": False,
            "failure_count": 1,
            "failures": [f"{type(exc).__name__}:{str(exc)[:500]}"],
            "global_certification": "NOT_GRANTED",
        }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report.get("eligible_for_g24") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
