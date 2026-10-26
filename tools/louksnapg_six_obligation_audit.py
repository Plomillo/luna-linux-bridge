#!/usr/bin/env python3
"""Evaluate the six LOUKSNAPG architectural obligations against run-bound evidence.

This auditor never grants product certification. It distinguishes package integrity,
worker dispatch, model-quality proof, complete target coverage, telemetry traceability,
the G23/Kestra/G24 chain, and forbidden-action controls.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "LOUKSNAPG_SIX_OBLIGATION_AUDIT/1.0"
GLOBAL_LUNA_HARD_MAX_BYTES = 479_000_000
CAJITA_RUNTIME_MAX_BYTES = 470_000_000
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
REQUIRED_EVENT_TYPES = {
    "SOURCE", "INPUT", "OPERATION", "OUTPUT", "TEST", "VALIDATION",
    "INDEPENDENT_VALIDATION_G23", "KESTRA_AUDIT",
    "CERTIFICATION_DECISION_G24", "NON_REGRESSION", "ROLLBACK",
}
MODEL_TARGETS = {
    "D01_CEREBRO_ROOT", "D03_TRANSCRIPCION_ROOT",
    "D04_TRADUCCION_GENERAL", "D05_DOCLING", "D06_ANALISIS_AVANZADO",
}
OBLIGATIONS = [
    ("C1_COORDINATED_WORKERS", "CUSTOSZ_V9 primary receipt and real Kestra secondary execution receipt"),
    ("C2_OFFICIAL_SOURCE_REPAIR", "Exact official source pins and material, quality-validated repair for all five model targets"),
    ("C3_PRIMITIVE_FUNCTIONS", "Real behavior tests passing for all 21 registered consumer targets"),
    ("C4_TELEMETRY_AND_AUDIT", "Persisted, ordered, source/contract/candidate-bound trace with hashes and rollback references"),
    ("C5_GOVERNED_RELEASE_CHAIN", "Independent functional G23, separate authorized G24, non-regression and rollback verification"),
    ("C6_PROHIBITIONS_AND_RECOVERY", "No heavy-weight downloads, Remote Commander, canonical mutation or synthetic proof; fail closed"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_json_optional(path: Path | None) -> dict[str, Any]:
    if path is None or path.is_symlink() or not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        return value if isinstance(value, dict) else {}
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return {}


def file_binding(path: Path | None) -> dict[str, Any]:
    if path is None or path.is_symlink() or not path.is_file():
        return {"available": False, "sha256": None, "bytes": None}
    return {"available": True, "sha256": sha256_file(path), "bytes": path.stat().st_size}


def _result(status: str, reason_codes: list[str], details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "status": status,
        "reason_codes": sorted(set(reason_codes)),
        "details": details or {},
    }


def evaluate(
    *,
    contract: dict[str, Any],
    contract_sha256: str,
    source_commit: str,
    bundle: Path,
    worker: dict[str, Any],
    task_report: dict[str, Any],
    functional_gate: dict[str, Any],
    g24_evidence: dict[str, Any],
    telemetry: dict[str, Any],
    kestra_receipt: dict[str, Any],
    g23_integrity: dict[str, Any] | None = None,
) -> dict[str, Any]:
    failures: list[str] = []
    if not COMMIT_RE.fullmatch(source_commit):
        failures.append("SOURCE_COMMIT_INVALID")
    if not SHA256_RE.fullmatch(contract_sha256):
        failures.append("CONTRACT_SHA256_INVALID")
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError("BUNDLE_NOT_REGULAR_FILE")
    bundle_bytes = bundle.stat().st_size
    bundle_sha = sha256_file(bundle)
    if bundle_bytes <= 0 or bundle_bytes > GLOBAL_LUNA_HARD_MAX_BYTES:
        failures.append("BUNDLE_OUTSIDE_GLOBAL_479MB_CAP")
    if worker.get("source_commit") != source_commit:
        failures.append("CUSTOSZ_SOURCE_COMMIT_MISMATCH")
    if worker.get("contract_sha256") != contract_sha256:
        failures.append("CUSTOSZ_CONTRACT_SHA256_MISMATCH")
    if worker.get("bundle_sha256") != bundle_sha or worker.get("artifact", {}).get("sha256") != bundle_sha:
        failures.append("CUSTOSZ_BUNDLE_SHA256_MISMATCH")

    task_rows = task_report.get("task_results", [])
    if not isinstance(task_rows, list):
        task_rows = []
    target_ids = sorted({row.get("target_id") for row in task_rows if isinstance(row, dict) and isinstance(row.get("target_id"), str)})
    quality_passes = sum(
        1 for row in task_rows if isinstance(row, dict)
        and row.get("status") == "PASS_FUNCTIONAL_EXECUTION"
        and row.get("exit_code") == 0
        and (row.get("quality_acceptance") or {}).get("status") == "PASS"
    )
    quality_failures = sum(
        1 for row in task_rows if isinstance(row, dict)
        and (row.get("quality_acceptance") or {}).get("status") == "FAIL"
    )
    synthetic_diagnostics = bool(
        task_report and (
            "synthetic" in str(task_report.get("inputs", "")).casefold()
            or any(
                isinstance(row, dict)
                and (row.get("quality_acceptance") or {}).get("reference_kind") == "FIXED_SYNTHETIC_EXPECTATION"
                for row in task_rows
            )
        )
    )
    expected_targets = contract.get("target_ids", [])
    if not isinstance(expected_targets, list) or len(expected_targets) != 21 or len(set(expected_targets)) != 21:
        expected_targets = []
        failures.append("CONTRACT_21_TARGET_REGISTRY_INVALID")

    worker_run_id = worker.get("worker_run_id") or worker.get("run_id")
    worker_receipt_ok = (
        worker.get("worker_status") == "PASS"
        and bool(worker_run_id)
        and worker.get("source_commit") == source_commit
        and worker.get("contract_sha256") == contract_sha256
        and worker.get("bundle_sha256") == bundle_sha
    )
    kestra_status = kestra_receipt.get("status")
    kestra_executed = (
        bool(kestra_receipt.get("execution_id"))
        and kestra_status in {
            "AUDIT_FAILED_OR_FAIL_CLOSED_HOLD",
            "FLOW_EXECUTION_SUCCESS_RELEASE_STILL_HOLD",
        }
        and bool(kestra_receipt.get("kestra_terminal_state"))
    )
    c1 = _result(
        "PASS_EXECUTION_RECEIPTS_PRESENT" if worker_receipt_ok and kestra_executed else "HOLD",
        [] if worker_receipt_ok and kestra_executed else [
            *(["CUSTOSZ_V9_REAL_RUN_RECEIPT_MISSING_OR_UNBOUND"] if not worker_receipt_ok else []),
            *(["KESTRA_REAL_EXECUTION_RECEIPT_MISSING_OR_UNBOUND"] if not kestra_executed else []),
        ],
        {
            "primary_worker": "CUSTOSZ_V9",
            "primary_worker_status": worker.get("worker_status", "NOT_ESTABLISHED"),
            "primary_run_id_present": bool(worker_run_id),
            "primary_run_id": worker_run_id,
            "primary_scope": worker.get("authorized_scope"),
            "secondary_worker": "KESTRA",
            "secondary_receipt_status": kestra_status or "NOT_ESTABLISHED",
            "secondary_execution_id_present": bool(kestra_receipt.get("execution_id")),
            "secondary_terminal_state": kestra_receipt.get("kestra_terminal_state"),
        },
    )

    catalog = contract.get("source_catalog", [])
    catalog_ok = isinstance(catalog, list) and len(catalog) == 5 and all(
        isinstance(row, dict)
        and COMMIT_RE.fullmatch(str(row.get("official_source_revision_commit", "")))
        and COMMIT_RE.fullmatch(str(row.get("model_repository_revision_commit", "")))
        and isinstance(row.get("official_url"), str)
        and isinstance(row.get("model_repository"), str)
        for row in catalog
    )
    repair = worker.get("repair_result") if isinstance(worker.get("repair_result"), dict) else {}
    repairs = repair.get("model_repairs", []) if isinstance(repair.get("model_repairs", []), list) else []
    repair_map = {row.get("target_id"): row for row in repairs if isinstance(row, dict)}
    material_repair_ok = (
        repair.get("status") == "PASS"
        and repair.get("model_targets_repaired") == 5
        and set(repair_map) == MODEL_TARGETS
        and all(
            row.get("status") == "PASS"
            and row.get("synthetic_only") is False
            and SHA256_RE.fullmatch(str(row.get("candidate_before_weights_sha256", "")))
            and SHA256_RE.fullmatch(str(row.get("candidate_after_weights_sha256", "")))
            and row.get("candidate_before_weights_sha256") != row.get("candidate_after_weights_sha256")
            and row.get("semantic_quality_status") == "PASS"
            for row in repair_map.values()
        )
    )
    c2 = _result(
        "PASS_MATERIAL_REPAIR_EVIDENCED" if catalog_ok and material_repair_ok else "HOLD",
        [] if catalog_ok and material_repair_ok else [
            *(["OFFICIAL_SOURCE_REVISION_CATALOG_INCOMPLETE"] if not catalog_ok else []),
            *(["MATERIAL_WEIGHT_REPAIR_OR_SEMANTIC_QUALITY_NOT_EVIDENCED"] if not material_repair_ok else []),
        ],
        {
            "official_source_revision_catalog": "PASS_METADATA_PIN_CHECK" if catalog_ok else "HOLD",
            "model_targets_expected": 5,
            "model_repair_records_observed": len(repair_map),
            "model_repairs_verified": material_repair_ok,
            "diagnostic_quality_fail_count": quality_failures,
            "constraint": "No heavy model weights downloaded; compact factors cannot be claimed as reconstructing discarded source information.",
        },
    )

    functional_gate_subject_bound = (
        functional_gate.get("source_commit") == source_commit
        and functional_gate.get("bundle_sha256") == bundle_sha
    )
    task_pass = (
        len(target_ids) == 21
        and set(target_ids) == set(expected_targets)
        and quality_passes == len(task_rows)
        and len(task_rows) == 21
        and not synthetic_diagnostics
        and functional_gate_subject_bound
        and functional_gate.get("decision") == "PASS"
        and functional_gate.get("eligible_for_g24") is True
    )
    c3 = _result(
        "PASS_ALL_21_REAL_TARGETS" if task_pass else "HOLD",
        [] if task_pass else [
            *(["ALL_21_TARGETS_NOT_OBSERVED"] if len(target_ids) != 21 or set(target_ids) != set(expected_targets) else []),
            *(["ONE_OR_MORE_TASK_QUALITY_ASSERTIONS_FAILED"] if quality_failures else []),
            *(["SYNTHETIC_DIAGNOSTICS_ARE_NOT_PRODUCT_PROOF"] if synthetic_diagnostics else []),
            *(["INTEGRAL_FUNCTIONAL_GATE_SUBJECT_BINDING_MISMATCH"] if not functional_gate_subject_bound else []),
            *(["INTEGRAL_FUNCTIONAL_GATE_NOT_PASS"] if functional_gate.get("decision") != "PASS" or functional_gate.get("eligible_for_g24") is not True else []),
        ],
        {
            "expected_target_count": 21,
            "observed_target_count": len(target_ids),
            "observed_target_ids": target_ids,
            "task_execution_count": len(task_rows),
            "quality_pass_count": quality_passes,
            "quality_fail_count": quality_failures,
            "synthetic_diagnostics": synthetic_diagnostics,
            "functional_gate_decision": functional_gate.get("decision", "NOT_ESTABLISHED"),
        },
    )

    event_rows = telemetry.get("events", []) if isinstance(telemetry.get("events", []), list) else []
    event_names = [row.get("event_type") for row in event_rows if isinstance(row, dict)]
    event_payloads_valid = all(
        isinstance(row, dict)
        and row.get("output_bytes") == len(json.dumps(
            {key: value for key, value in row.items() if key not in {"evidence_sha256", "output_sha256", "output_bytes"}},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8"))
        and hashlib.sha256(json.dumps(
            {key: value for key, value in row.items() if key not in {"evidence_sha256", "output_sha256", "output_bytes"}},
            sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest() == row.get("evidence_sha256") == row.get("output_sha256")
        for row in event_rows
    )
    telemetry_payload = {key: value for key, value in telemetry.items() if key != "evidence_sha256"} if isinstance(telemetry, dict) else {}
    telemetry_envelope_valid = (
        bool(telemetry.get("evidence_sha256"))
        and hashlib.sha256(json.dumps(
            telemetry_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")).hexdigest() == telemetry.get("evidence_sha256")
    )
    telemetry_bound = (
        telemetry.get("source_commit") == source_commit
        and telemetry.get("bundle_sha256") == bundle_sha
        and telemetry.get("contract_sha256") == contract_sha256
        and set(event_names) == REQUIRED_EVENT_TYPES
        and len(event_names) == len(REQUIRED_EVENT_TYPES)
        and [row.get("sequence_id") for row in event_rows if isinstance(row, dict)] == list(range(1, len(REQUIRED_EVENT_TYPES) + 1))
        and event_payloads_valid
        and telemetry_envelope_valid
        and all(
            isinstance(row, dict)
            and row.get("source_commit") == source_commit
            and row.get("bundle_sha256") == bundle_sha
            and row.get("contract_sha256") == contract_sha256
            and SHA256_RE.fullmatch(str(row.get("input_sha256", "")))
            and SHA256_RE.fullmatch(str(row.get("output_sha256", "")))
            and row.get("evidence_sha256") == row.get("output_sha256")
            for row in event_rows
        )
    )
    c4 = _result(
        "PASS_TRACEABILITY_WITH_RELEASE_HOLD" if telemetry_bound else "HOLD",
        [] if telemetry_bound else ["PERSISTENT_TELEMETRY_MISSING_INCOMPLETE_OR_UNBOUND"],
        {
            "telemetry_file_status": telemetry.get("status", "NOT_ESTABLISHED"),
            "event_count": len(event_names),
            "expected_event_count": len(REQUIRED_EVENT_TYPES),
            "candidate_commit_contract_binding": telemetry_bound,
            "telemetry_sha256": telemetry.get("evidence_sha256"),
            "release_eligibility": "NOT_GRANTED_BY_TELEMETRY_ALONE",
        },
    )

    g24_evidence_subject_bound = (
        g24_evidence.get("source_commit") == source_commit
        and g24_evidence.get("package_sha256") == bundle_sha
    )
    g23_functional_pass = (
        functional_gate_subject_bound
        and g24_evidence_subject_bound
        and functional_gate.get("decision") == "PASS"
        and g24_evidence.get("integral_functional_evidence_decision") == "PASS"
        and bool(g24_evidence.get("g23_signed_functional_attestation_sha256"))
    )
    g24_granted = (
        g24_evidence_subject_bound
        and g24_evidence.get("decision") == "GRANTED"
        and g24_evidence.get("g24_signature_verification_status") == "PASS_VERIFIED"
    )
    c5_ok = (
        g23_functional_pass
        and kestra_executed
        and g24_granted
        and g24_evidence.get("host_matrix_status") == "PASS"
        and g24_evidence.get("rollback_status") == "PASS"
        and g24_evidence.get("non_regression_status") == "PASS"
    )
    c5 = _result(
        "PASS_COMPLETE_CERTIFICATION_CHAIN" if c5_ok else "HOLD",
        [] if c5_ok else [
            *(["FUNCTIONAL_G23_NOT_VERIFIED"] if not g23_functional_pass else []),
            *(["KESTRA_AUDIT_NOT_EXECUTED_OR_NOT_TERMINAL"] if not kestra_executed else []),
            *(["SEPARATE_G24_NOT_GRANTED_AND_VERIFIED"] if not g24_granted else []),
            *(["HOST_NON_REGRESSION_OR_ROLLBACK_EVIDENCE_MISSING"] if not (
                g24_evidence.get("host_matrix_status") == "PASS"
                and g24_evidence.get("rollback_status") == "PASS"
                and g24_evidence.get("non_regression_status") == "PASS"
            ) else []),
        ],
        {
            "package_integrity_g23_job": (g23_integrity or {}).get("conclusion", "NOT_ESTABLISHED"),
            "functional_g23": "PASS" if g23_functional_pass else "NOT_ESTABLISHED",
            "kestra_audit": kestra_status or "NOT_ESTABLISHED",
            "g24_decision": g24_evidence.get("decision", "NOT_GRANTED"),
            "global_certification": "NOT_GRANTED",
        },
    )

    safety = telemetry.get("safety", {}) if isinstance(telemetry.get("safety", {}), dict) else {}
    prohibitions = contract.get("prohibitions", {})
    safety_ok = (
        safety.get("heavy_model_download_count") == 0
        and safety.get("remote_commander_used") is False
        and safety.get("canonical_mutation") is False
        and safety.get("synthetic_evidence_used_as_product_proof") is False
        and isinstance(prohibitions, dict)
        and all(value is False for value in prohibitions.values())
        and g24_evidence.get("global_certification") in {"NOT_GRANTED", None}
    )
    c6 = _result(
        "PASS_PROHIBITIONS_OBSERVED" if safety_ok else "HOLD",
        [] if safety_ok else ["SAFETY_CONSTRAINTS_NOT_ALL_VERIFIABLY_ENFORCED"],
        {
            "heavy_model_download_count": safety.get("heavy_model_download_count", "NOT_ESTABLISHED"),
            "remote_commander_used": safety.get("remote_commander_used", "NOT_ESTABLISHED"),
            "canonical_mutation": safety.get("canonical_mutation", "NOT_ESTABLISHED"),
            "synthetic_evidence_used_as_product_proof": safety.get("synthetic_evidence_used_as_product_proof", "NOT_ESTABLISHED"),
            "fail_closed_release_state": "HOLD_NOT_CERTIFIED",
        },
    )

    obligations = {
        "C1_COORDINATED_WORKERS": c1,
        "C2_OFFICIAL_SOURCE_REPAIR": c2,
        "C3_PRIMITIVE_FUNCTIONS": c3,
        "C4_TELEMETRY_AND_AUDIT": c4,
        "C5_GOVERNED_RELEASE_CHAIN": c5,
        "C6_PROHIBITIONS_AND_RECOVERY": c6,
    }
    all_release_requirements_pass = all(row["status"].startswith("PASS") for row in obligations.values())
    return {
        "schema": SCHEMA,
        "audit_id": "LOUKSNAPG-SIX-OBLIGATION-" + source_commit[:12],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "source_commit": source_commit,
        "contract_sha256": contract_sha256,
        "bundle": {"path": bundle.name, "bytes": bundle_bytes, "sha256": bundle_sha, "max_bytes": GLOBAL_LUNA_HARD_MAX_BYTES},
        "separate_runtime_max_bytes": CAJITA_RUNTIME_MAX_BYTES,
        "obligations": obligations,
        "summary": {
            "obligations_expected": 6,
            "obligations_passed": sum(1 for row in obligations.values() if row["status"].startswith("PASS")),
            "obligations_held": sum(1 for row in obligations.values() if row["status"] == "HOLD"),
            "release_eligible": all_release_requirements_pass,
            "global_certification": "NOT_GRANTED" if not all_release_requirements_pass else "REQUIRES_SEPARATE_AUTHORIZED_G24",
            "decision": "HOLD_NOT_CERTIFIED" if not all_release_requirements_pass else "ELIGIBLE_FOR_SEPARATE_G24_REVIEW",
        },
        "evidence_bindings": {
            "worker": file_binding(None),
            "task_report": file_binding(None),
            "functional_gate": file_binding(None),
            "g24_evidence": file_binding(None),
            "telemetry": file_binding(None),
            "kestra_receipt": file_binding(None),
        },
        "note": "Package integrity and static contract validity are not model repair or product certification. Synthetic diagnostic fixtures are never accepted as functional product evidence.",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--worker-evidence", type=Path)
    parser.add_argument("--task-report", type=Path)
    parser.add_argument("--functional-gate", type=Path)
    parser.add_argument("--g24-evidence", type=Path)
    parser.add_argument("--telemetry", type=Path)
    parser.add_argument("--kestra-receipt", type=Path)
    parser.add_argument("--g23-integrity", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)

    try:
        contract_bytes = args.contract.read_bytes()
        contract = json.loads(contract_bytes.decode("utf-8"))
        bundle = args.bundle
        result = evaluate(
            contract=contract,
            contract_sha256=sha256_bytes(contract_bytes),
            source_commit=args.source_commit,
            bundle=bundle,
            worker=load_json_optional(args.worker_evidence),
            task_report=load_json_optional(args.task_report),
            functional_gate=load_json_optional(args.functional_gate),
            g24_evidence=load_json_optional(args.g24_evidence),
            telemetry=load_json_optional(args.telemetry),
            kestra_receipt=load_json_optional(args.kestra_receipt),
            g23_integrity=load_json_optional(args.g23_integrity),
        )
        for key, path in (
            ("worker", args.worker_evidence), ("task_report", args.task_report),
            ("functional_gate", args.functional_gate), ("g24_evidence", args.g24_evidence),
            ("telemetry", args.telemetry), ("kestra_receipt", args.kestra_receipt),
        ):
            result["evidence_bindings"][key] = file_binding(path)
    except Exception as exc:
        result = {
            "schema": SCHEMA, "source_commit": args.source_commit,
            "decision": "HOLD_NOT_CERTIFIED", "release_eligible": False,
            "global_certification": "NOT_GRANTED",
            "failures": [type(exc).__name__ + ":" + str(exc)[:800]],
        }
    text = json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if result.get("summary", {}).get("release_eligible") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
