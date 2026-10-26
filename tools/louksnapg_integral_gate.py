#!/usr/bin/env python3
"""Fail-closed eligibility gate for integral LOUKSNAPG functional evidence.

This checks evidence shape and subject binding only. It is not G23, G24, or a
model-quality oracle; cryptographic attestation and independent re-execution remain
separate release gates. Synthetic harness reports can never pass this gate.
"""
from __future__ import annotations

import argparse
import base64
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
OFFICIAL_MODEL_IDS = {
    "D01_CEREBRO_ROOT": "openai/gpt-oss-120b",
    "D03_TRANSCRIPCION_ROOT": "turbo",
    "D04_TRADUCCION_GENERAL": "facebook/seamless-m4t-v2-large",
    "D05_DOCLING": "ibm-granite/granite-docling-258M",
}
OFFICIAL_SOURCE_URLS = {
    "D01_CEREBRO_ROOT": "https://github.com/openai/gpt-oss",
    "D03_TRANSCRIPCION_ROOT": "https://github.com/openai/whisper",
    "D04_TRADUCCION_GENERAL": "https://github.com/facebookresearch/seamless_communication",
    "D05_DOCLING": "https://huggingface.co/ibm-granite/granite-docling-258M",
    "D06_ANALISIS_AVANZADO": "https://github.com/QwenLM/Qwen3",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_sha(value: object) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _canonical_json(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _verify_g23_envelope(envelope: object, public_key_pem: str | None,
                         expected_source_commit: str, bundle_sha256: str,
                         evidence_without_g23: dict) -> list[str]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return ["G23_SIGNED_ENVELOPE_MISSING"]
    if envelope.get("schema") != "LOUKSNAPG_G23_SIGNED/1.0" or envelope.get("status") != "SIGNED":
        errors.append("G23_SIGNED_ENVELOPE_SCHEMA_OR_STATUS_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return errors + ["G23_SIGNED_PAYLOAD_MISSING"]
    if payload.get("schema") != "LOUKSNAPG_G23_ATTESTATION_PAYLOAD/1.0":
        errors.append("G23_PAYLOAD_SCHEMA_INVALID")
    if payload.get("status") != "PASS":
        errors.append("G23_PAYLOAD_NOT_PASS")
    if payload.get("scope") != "LOUKSNAPG_INTEGRAL_FUNCTIONAL_VALIDATION":
        errors.append("G23_SCOPE_MISMATCH")
    if payload.get("candidate_commit") != expected_source_commit:
        errors.append("G23_SOURCE_COMMIT_MISMATCH")
    if payload.get("subject_bundle_sha256") != bundle_sha256:
        errors.append("G23_SUBJECT_BUNDLE_MISMATCH")
    expected_manifest_sha = hashlib.sha256(_canonical_json(evidence_without_g23)).hexdigest()
    if payload.get("evidence_manifest_sha256") != expected_manifest_sha:
        errors.append("G23_EVIDENCE_MANIFEST_SHA256_MISMATCH")
    producer_id = payload.get("producer_id")
    validator_id = payload.get("validator_id")
    if not isinstance(producer_id, str) or not producer_id.strip():
        errors.append("G23_PRODUCER_ID_MISSING")
    if not isinstance(validator_id, str) or not validator_id.strip() or validator_id == producer_id:
        errors.append("G23_VALIDATOR_ID_NOT_INDEPENDENT")
    if not public_key_pem:
        errors.append("G23_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED")
        return errors
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = serialization.load_pem_public_key(public_key_pem.encode("ascii"))
        if not isinstance(key, Ed25519PublicKey):
            return errors + ["G23_TRUSTED_KEY_NOT_ED25519"]
        raw_key = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        fingerprint = hashlib.sha256(raw_key).hexdigest()
        if envelope.get("signer_public_key_sha256") != fingerprint:
            errors.append("G23_TRUSTED_KEY_FINGERPRINT_MISMATCH")
        payload_bytes = _canonical_json(payload)
        if envelope.get("payload_sha256") != hashlib.sha256(payload_bytes).hexdigest():
            errors.append("G23_PAYLOAD_SHA256_MISMATCH")
        signature = base64.b64decode(envelope.get("signature_b64", ""), validate=True)
        key.verify(signature, payload_bytes)
    except ImportError:
        errors.append("G23_CRYPTOGRAPHY_DEPENDENCY_MISSING")
    except Exception:
        errors.append("G23_ED25519_SIGNATURE_INVALID")
    return errors


def evaluate_evidence(evidence: object, bundle_sha256: str, expected_source_commit: str,
                      g23_public_key_pem: str | None = None) -> dict:
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
            model_id = row.get("upstream_model_id")
            if not isinstance(model_id, str) or not model_id.strip():
                target_failures.append("UPSTREAM_MODEL_ID_MISSING")
            elif target_id in OFFICIAL_MODEL_IDS and model_id != OFFICIAL_MODEL_IDS[target_id]:
                target_failures.append("UPSTREAM_MODEL_ID_NOT_OFFICIAL_EXPECTED_VARIANT")
            elif target_id == "D06_ANALISIS_AVANZADO" and model_id not in {
                "Qwen/Qwen3-0.6B", "Qwen/Qwen3-1.7B", "Qwen/Qwen3-4B",
                "Qwen/Qwen3-8B", "Qwen/Qwen3-14B", "Qwen/Qwen3-32B",
                "Qwen/Qwen3-30B-A3B", "Qwen/Qwen3-235B-A22B",
            }:
                target_failures.append("QWEN3_UPSTREAM_VARIANT_NOT_PINNED")
            if row.get("upstream_source_url") != OFFICIAL_SOURCE_URLS[target_id]:
                target_failures.append("UPSTREAM_SOURCE_NOT_OFFICIAL_EXPECTED_URL")
            if not COMMIT_RE.fullmatch(str(row.get("upstream_revision_sha256", ""))):
                target_failures.append("UPSTREAM_REVISION_NOT_PINNED_TO_COMMIT")
        target_checks.append({"target_id": target_id, "status": "PASS" if not target_failures else "HOLD",
                              "failures": target_failures})
        failures.extend("TARGET:" + target_id + ":" + item for item in target_failures)

    evidence_without_g23 = dict(evidence)
    evidence_without_g23.pop("g23", None)
    failures.extend(_verify_g23_envelope(
        evidence.get("g23"), g23_public_key_pem, expected_source_commit,
        bundle_sha256, evidence_without_g23
    ))

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
        "note": "Ed25519 G23 signature is verified against an explicitly supplied trust key. This evidence gate still does not replace separate G24 authorization."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--expected-source-commit", required=True)
    parser.add_argument("--g23-public-key", type=Path, help="trusted G23 Ed25519 public key PEM; absent means HOLD")
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
        public_pem = None
        if args.g23_public_key:
            if args.g23_public_key.is_symlink() or not args.g23_public_key.is_file():
                raise ValueError("G23_TRUSTED_PUBLIC_KEY_NOT_REGULAR_FILE")
            public_pem = args.g23_public_key.read_text(encoding="ascii")
        report = evaluate_evidence(evidence, sha256_file(args.bundle), args.expected_source_commit, public_pem)
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
