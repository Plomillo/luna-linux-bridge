#!/usr/bin/env python3
"""Automated source-bound G23/G24 gates for LOUKSNAPG2.

G23 independently validates package structure and source identity.
G24 verifies the G23 decision's OIDC attestation and accepts only complete semantic,
model-repair and rollback evidence for the exact same commit and artifact digest.
No user-managed PEM signing keys and no worker self-certification are used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from louksnapg2_independent_validator import verify as verify_bundle

REQUIRED_CASES = {
    "CEREBRO_ARITHMETIC_01": "D01_CEREBRO",
    "CEREBRO_WORD_PROBLEM_02": "D01_CEREBRO",
    "ANALYSIS_MULTI_STEP_01": "D06_SISTEMA_INTELIGENTE",
    "ANALYSIS_LOGIC_02": "D06_SISTEMA_INTELIGENTE",
    "GENERAL_TRANSLATION_EN_ES_01": "D04_TRADUCTOR_INTELIGENTE",
    "GENERAL_TRANSLATION_ES_EN_02": "D04_TRADUCTOR_INTELIGENTE",
    "GENERAL_TRANSLATION_EN_FR_03": "D04_TRADUCTOR_INTELIGENTE",
    "GENERAL_TRANSLATION_FR_EN_04": "D04_TRADUCTOR_INTELIGENTE",
    "ANCIENT_LATIN_01": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "ANCIENT_GREEK_02": "D04_TRADUCCION_LENGUAS_ANTIGUAS",
    "WHISPER_AUDIO_01": "D03_TRANSCRIPCION",
    "WHISPER_AUDIO_02": "D03_TRANSCRIPCION",
    "DOCLING_INVOICE_IMAGE_01": "D05_INTELIGENCIA_DOCUMENTAL",
}
REQUIRED_DOMAINS = tuple(sorted(set(REQUIRED_CASES.values())))


def now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("EVIDENCE_FILE_MISSING_OR_UNSAFE:" + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_ROOT_NOT_OBJECT:" + str(path))
    return value


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def current_commit() -> str:
    value = os.environ.get("GITHUB_SHA", "")
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ValueError("GITHUB_SHA_INVALID")
    return value


def g23(args) -> dict:
    commit = current_commit()
    blockers: list[str] = []
    bundle = args.bundle
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError("CANDIDATE_BUNDLE_MISSING_OR_UNSAFE")
    candidate_sha = sha256_file(bundle)
    measured_bytes = bundle.stat().st_size
    independent = verify_bundle(bundle, 490_000_000, None, commit)
    if independent.get("identity_preservation_status") != "PASS_SOURCE_IDENTITY_PRESERVED":
        blockers.append("INDEPENDENT_SOURCE_IDENTITY_NOT_PASS")
    for field in (
        "budget_status",
        "container_integrity",
        "protected_prefix_integrity",
        "cajita_document_copy_integrity",
        "runtime_member_integrity",
        "single_distribution_container",
    ):
        if independent.get(field) != "PASS":
            blockers.append("INDEPENDENT_VALIDATION_NOT_PASS:" + field)
    if independent.get("source_commit") != commit:
        blockers.append("INDEPENDENT_VALIDATION_COMMIT_MISMATCH")

    build = read_json(args.build_report)
    worker = read_json(args.worker_evidence)
    unit = read_json(args.unit_evidence)
    materialization = read_json(args.model_materialization)
    if build.get("status") != "PASS_CANDIDATE_BUILD_ONLY":
        blockers.append("CANDIDATE_BUILD_NOT_PASS")
    if build.get("source_commit") != commit or worker.get("source_commit") != commit:
        blockers.append("BUILD_OR_WORKER_COMMIT_MISMATCH")
    if build.get("candidate", {}).get("sha256") != candidate_sha:
        blockers.append("BUILD_CANDIDATE_SHA256_MISMATCH")
    if build.get("candidate", {}).get("bytes") != measured_bytes:
        blockers.append("BUILD_CANDIDATE_SIZE_MISMATCH")
    if build.get("global_certification") != "NOT_GRANTED":
        blockers.append("BUILDER_ATTEMPTED_CERTIFICATION")
    if worker.get("worker") != "CUSTOSZ_V9" or worker.get("worker_status") != "PASS":
        blockers.append("PRIMARY_CUSTOSZ_WORKER_NOT_PASS")
    if worker.get("worker_sha256") != "667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3":
        blockers.append("CUSTOSZ_V9_IDENTITY_MISMATCH")
    if worker.get("global_certification") != "NOT_GRANTED":
        blockers.append("WORKER_ATTEMPTED_CERTIFICATION")
    if unit.get("status") != "PASS" or int(unit.get("failures", -1)) != 0 or int(unit.get("errors", -1)) != 0:
        blockers.append("SOURCE_UNIT_TESTS_NOT_PASS")
    if materialization.get("status") != "PASS" or int(materialization.get("required_domain_count", 0)) < 5:
        blockers.append("MODEL_SOURCE_MATERIALIZATION_NOT_PASS")

    return {
        "schema": "LOUKSNAPG2_G23_INDEPENDENT_VALIDATION/1.0",
        "generated_at_utc": now(),
        "gate": "G23",
        "status": "PASS" if not blockers else "HOLD",
        "source_commit": commit,
        "candidate": {"path": bundle.name, "bytes": measured_bytes, "sha256": candidate_sha},
        "independent_container_validation": independent,
        "evidence": {
            "build_report_sha256": sha256_file(args.build_report),
            "worker_evidence_sha256": sha256_file(args.worker_evidence),
            "unit_evidence_sha256": sha256_file(args.unit_evidence),
            "model_materialization_sha256": sha256_file(args.model_materialization),
        },
        "repair_status": worker.get("repair_status", "UNKNOWN"),
        "repair_execution_performed": bool(worker.get("repair_execution_performed", False)),
        "blockers": blockers,
        "global_certification": "NOT_GRANTED_BY_G23",
        "canonical_promotion": "NOT_AUTHORIZED",
        "self_certification": False,
        "validator_identity": "GITHUB_ACTIONS_G23_JOB_OIDC",
    }


def g24(args) -> dict:
    commit = current_commit()
    blockers: list[str] = []
    g23_report = read_json(args.g23_report)
    functional = read_json(args.functional_evidence)
    worker = read_json(args.worker_evidence)
    materialization = read_json(args.model_materialization)
    readiness = read_json(args.repair_readiness)
    endpoint = read_json(args.endpoint_preflight)
    build = read_json(args.build_report)
    bundle = args.bundle

    if os.environ.get("G23_ATTESTATION_VERIFIED") != "true":
        blockers.append("G23_OIDC_ATTESTATION_NOT_VERIFIED")
    if g23_report.get("status") != "PASS" or g23_report.get("gate") != "G23":
        blockers.append("G23_DECISION_NOT_PASS")
    if g23_report.get("source_commit") != commit:
        blockers.append("G23_COMMIT_MISMATCH")
    if bundle.is_symlink() or not bundle.is_file():
        blockers.append("CANDIDATE_BUNDLE_MISSING_OR_UNSAFE")
        candidate_sha = None
    else:
        candidate_sha = sha256_file(bundle)
    if candidate_sha is None or g23_report.get("candidate", {}).get("sha256") != candidate_sha:
        blockers.append("G23_CANDIDATE_DIGEST_MISMATCH")
    if build.get("source_commit") != commit or build.get("candidate", {}).get("sha256") != candidate_sha:
        blockers.append("BUILD_EVIDENCE_NOT_BOUND_TO_CANDIDATE")
    if materialization.get("status") != "PASS" or int(materialization.get("required_domain_count", 0)) < 5:
        blockers.append("MODEL_SOURCE_MATERIALIZATION_NOT_PASS")
    if endpoint.get("status") != "PASS_CONFIGURATION_PRESENT":
        blockers.append("REMOTE_ENDPOINT_CONFIGURATION_NOT_PASS")
    if functional.get("source_commit", commit) != commit:
        blockers.append("FUNCTIONAL_EVIDENCE_COMMIT_MISMATCH")
    if functional.get("functional_status") != "PASS_ALL_DOMAIN_CASES":
        blockers.append("FUNCTIONAL_SEMANTIC_SUITE_NOT_PASS")
    tests = functional.get("tests")
    if not isinstance(tests, list):
        tests = []
    by_id = {row.get("case_id"): row for row in tests if isinstance(row, dict)}
    for case_id, domain in REQUIRED_CASES.items():
        row = by_id.get(case_id)
        if row is None or row.get("status") != "PASS" or row.get("domain_id") != domain:
            blockers.append("REQUIRED_FUNCTIONAL_CASE_NOT_PASS:" + case_id)
    domain_results = functional.get("domain_results", {})
    for domain in REQUIRED_DOMAINS:
        if not isinstance(domain_results, dict) or domain_results.get(domain, {}).get("status") != "PASS":
            blockers.append("REQUIRED_DOMAIN_NOT_PASS:" + domain)
    if worker.get("repair_status") != "PASS_ALL_REQUIRED_ADAPTERS":
        blockers.append("MODEL_REPAIR_ADAPTERS_NOT_ALL_PASS")
    if readiness.get("repair_adapter_status") != "PASS_ALL_REQUIRED_ADAPTERS":
        blockers.append("REPAIR_READINESS_NOT_PASS")
    adapters = readiness.get("adapter_results", [])
    if not isinstance(adapters, list) or not adapters or any(x.get("status") != "PASS" for x in adapters if isinstance(x, dict)):
        blockers.append("REPAIR_ADAPTER_POSTVALIDATION_NOT_PASS")
    if worker.get("repair_execution_performed") is not True:
        blockers.append("MODEL_REPAIR_NOT_EXECUTED")
    if worker.get("global_certification") != "NOT_GRANTED":
        blockers.append("WORKER_CERTIFICATION_BOUNDARY_BROKEN")
    if worker.get("canonical_promotion") != "NOT_AUTHORIZED":
        blockers.append("WORKER_CANONICAL_PROMOTION_BOUNDARY_BROKEN")

    unique_blockers = sorted(set(blockers))
    certified = not unique_blockers
    return {
        "schema": "LOUKSNAPG2_G24_AUTOMATED_CERTIFICATE/1.0",
        "generated_at_utc": now(),
        "gate": "G24",
        "status": "CERTIFIED" if certified else "HOLD",
        "source_commit": commit,
        "candidate": {"path": bundle.name if bundle.exists() else None, "sha256": candidate_sha},
        "g23": {
            "status": g23_report.get("status"),
            "attestation_verified": os.environ.get("G23_ATTESTATION_VERIFIED") == "true",
            "evidence_sha256": sha256_file(args.g23_report),
        },
        "functional_status": functional.get("functional_status"),
        "model_repair_status": worker.get("repair_status"),
        "blockers": unique_blockers,
        "global_certification": "CERTIFIED" if certified else "NOT_GRANTED",
        "release_authorized": False,
        "canonical_promotion_authorized": False,
        "authority": "AUTOMATED_G24_INDEPENDENT_JOB_OIDC",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    p23 = sub.add_parser("g23")
    p23.add_argument("--bundle", required=True, type=Path)
    p23.add_argument("--build-report", required=True, type=Path)
    p23.add_argument("--worker-evidence", required=True, type=Path)
    p23.add_argument("--unit-evidence", required=True, type=Path)
    p23.add_argument("--model-materialization", required=True, type=Path)
    p23.add_argument("--report", required=True, type=Path)
    p24 = sub.add_parser("g24")
    for name in ("bundle", "build-report", "worker-evidence", "model-materialization", "repair-readiness", "endpoint-preflight", "functional-evidence", "g23-report", "report"):
        p24.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        report = g23(args) if args.command == "g23" else g24(args)
    except Exception as exc:
        report = {
            "schema": "LOUKSNAPG2_AUTOMATED_GATE_FAILURE/1.0",
            "generated_at_utc": now(),
            "gate": args.command.upper(),
            "status": "HOLD",
            "source_commit": os.environ.get("GITHUB_SHA", "UNKNOWN"),
            "blockers": [type(exc).__name__ + ":" + str(exc)[:600]],
            "global_certification": "NOT_GRANTED",
            "canonical_promotion_authorized": False,
        }
    write_json(args.report, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
    return 0 if report.get("status") in ({"PASS"} if args.command == "g23" else {"CERTIFIED"}) else 2


if __name__ == "__main__":
    raise SystemExit(main())
