#!/usr/bin/env python3
"""PUAC2-style signed G23/G24 evidence gates for the LOUKSNAPG2 branch candidate.

G23 measures source identity and container integrity; G24 separately requires the
real-model functional evidence for all required domains. Neither gate mutates the
candidate, and the worker/build process cannot sign either decision.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
import zipfile

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "tools"))

from scripts.cajita_luna_puac2_gates import sign_envelope, verify_envelope
from louksnapg2_independent_validator import verify as verify_bundle

G23_SCHEMA = "CAJITA_PUAC2_G23_PAYLOAD/1.0"
G24_SCHEMA = "CAJITA_PUAC2_G24_PAYLOAD/1.0"
G23_SIGNED_SCHEMA = "CAJITA_PUAC2_G23_SIGNED/1.0"
G24_SIGNED_SCHEMA = "CAJITA_PUAC2_G24_SIGNED/1.0"
MAX_BYTES = 490_000_000
PRODUCER_ID = "CUSTOSZ_V9"
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
REQUIRED_REPAIR_DOMAINS = REQUIRED_DOMAINS
REPAIR_DIGEST_FIELDS = (
    "source_weight_sha256",
    "adapter_sha256",
    "calibration_dataset_sha256",
    "heldout_dataset_sha256",
    "rollback_checkpoint_sha256",
)
SHA256_RE = __import__("re").compile(r"^[0-9a-f]{64}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("EVIDENCE_NOT_REGULAR_FILE:" + path.name)
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("EVIDENCE_NOT_OBJECT:" + path.name)
    return value


def atomic_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def exact_source_bindings(bundle_path: Path, architecture_path: Path, cajita_path: Path) -> dict:
    architecture = architecture_path.read_bytes()
    cajita = cajita_path.read_bytes()
    with zipfile.ZipFile(bundle_path, "r") as archive:
        combined = archive.read("LOUKSNAMEJORADA.md")
    if not combined.startswith(architecture):
        raise ValueError("PROTECTED_ARCHITECTURE_PREFIX_NOT_BYTE_EXACT")
    if not combined.endswith(cajita):
        raise ValueError("ORIGINAL_CAJITA_DOCUMENT_SUFFIX_NOT_BYTE_EXACT")
    return {
        "architecture_bytes": len(architecture),
        "architecture_sha256": sha256_bytes(architecture),
        "prefix_byte_exact": True,
        "cajita_document_bytes": len(cajita),
        "cajita_document_sha256": sha256_bytes(cajita),
        "cajita_suffix_byte_exact": True,
        "combined_document_bytes": len(combined),
        "combined_document_sha256": sha256_bytes(combined),
    }


def g23_payload(args) -> dict:
    blockers = []
    bundle = args.bundle.resolve(strict=True)
    build_report = read_json(args.build_report)
    worker = read_json(args.worker_evidence)
    unit = read_json(args.unit_evidence)
    materialization = read_json(args.model_materialization)
    functional = read_json(args.functional_evidence)
    source_arch = args.source_architecture.resolve(strict=True)
    cajita_doc = args.cajita_doc.resolve(strict=True)
    head = os.environ.get("GITHUB_SHA", "")
    validator_id = args.validator_id.strip()
    if not validator_id or validator_id == PRODUCER_ID:
        blockers.append("G23_VALIDATOR_ID_MISSING_OR_EQUALS_PRODUCER")
    if build_report.get("status") != "PASS_CANDIDATE_BUILD_ONLY":
        blockers.append("CANDIDATE_BUILD_REPORT_NOT_PASS")
    measured = bundle.stat().st_size
    bundle_hash = sha256_file(bundle)
    if measured > MAX_BYTES:
        blockers.append("CANDIDATE_OVER_490000000_BYTES")
    if build_report.get("candidate", {}).get("bytes") != measured or build_report.get("candidate", {}).get("sha256") != bundle_hash:
        blockers.append("BUILDER_REPORT_CANDIDATE_BINDING_MISMATCH")
    if build_report.get("source_commit") != head:
        blockers.append("CANDIDATE_SOURCE_COMMIT_MISMATCH")
    if worker.get("worker") != PRODUCER_ID or worker.get("worker_status") != "PASS":
        blockers.append("CUSTOSZ_V9_WORKER_EVIDENCE_NOT_PASS")
    if worker.get("artifact", {}).get("sha256") != bundle_hash or worker.get("artifact", {}).get("bytes") != measured:
        blockers.append("WORKER_OUTPUT_BINDING_MISMATCH")
    if worker.get("source_commit") != head:
        blockers.append("WORKER_SOURCE_COMMIT_MISMATCH")
    if unit.get("status") != "PASS" or unit.get("failures", 0) or unit.get("errors", 0):
        blockers.append("LOUKSNAPG2_UNIT_TESTS_NOT_PASS")
    if materialization.get("status") != "PASS":
        blockers.append("EXTERNALIZED_MODEL_MATERIALIZATION_NOT_PASS")
    if functional.get("model_identity_status") != "PASS_MODEL_SOURCE_IDENTITIES":
        blockers.append("FUNCTIONAL_MODEL_SOURCE_IDENTITY_NOT_PASS")
    if not source_arch.is_file() or not cajita_doc.is_file():
        blockers.append("SOURCE_DOCUMENT_MISSING")
    try:
        identity = exact_source_bindings(bundle, source_arch, cajita_doc)
    except Exception as exc:
        identity = {"status": "FAIL", "reason": type(exc).__name__ + ":" + str(exc)[:300]}
        blockers.append("SOURCE_BINDING_CHECK_FAILED:" + identity["reason"])
    verification = verify_bundle(bundle, MAX_BYTES, None, head)
    if verification.get("identity_preservation_status") != "PASS_SOURCE_IDENTITY_PRESERVED":
        blockers.append("INDEPENDENT_CONTAINER_IDENTITY_NOT_PASS")
    if verification.get("runtime_routing_registry") == "FAIL" or verification.get("module_registry") == "FAIL":
        blockers.append("INDEPENDENT_RUNTIME_REGISTRY_NOT_PASS")
    return {
        "schema": G23_SCHEMA,
        "gate": "G23_INDEPENDENT_VALIDATION",
        "status": "PASS" if not blockers else "HOLD",
        "decision_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "validator_id": validator_id,
        "producer_id": PRODUCER_ID,
        "source_commit": head,
        "candidate": {"path": bundle.name, "bytes": measured, "sha256": bundle_hash, "cap_bytes": MAX_BYTES},
        "source_identity": identity,
        "independent_container_validation": {
            "status": verification.get("status"),
            "identity_preservation_status": verification.get("identity_preservation_status"),
            "runtime_routing_registry": verification.get("runtime_routing_registry"),
            "module_registry": verification.get("module_registry"),
            "axiom_registry": verification.get("axiom_registry"),
            "member_count": verification.get("member_count"),
        },
        "evidence_sha256": {
            "build_report": sha256_file(args.build_report),
            "worker_evidence": sha256_file(args.worker_evidence),
            "unit_tests": sha256_file(args.unit_evidence),
            "model_materialization": sha256_file(args.model_materialization),
            "functional_evidence": sha256_file(args.functional_evidence),
        },
        "functional_quality_observation": {
            "status": functional.get("functional_status"),
            "is_a_G23_pass_criterion": False,
            "G24_decides_functional_quality": True,
        },
        "blockers": blockers,
        "global_certification": "NOT_GRANTED_BY_G23",
    }


def sign_payload(input_path: Path, output_path: Path, signer_id: str, env_name: str, schema: str) -> dict:
    payload = read_json(input_path)
    key = os.environ.get(env_name, "")
    if not key.strip():
        raise ValueError("SIGNING_KEY_ENV_MISSING:" + env_name)
    if payload.get("status") not in ("PASS", "HOLD"):
        raise ValueError("GATE_PAYLOAD_STATUS_INVALID")
    if schema == G23_SIGNED_SCHEMA and payload.get("validator_id") != signer_id:
        raise ValueError("G23_SIGNER_IDENTITY_MISMATCH")
    if schema == G24_SIGNED_SCHEMA and payload.get("certifier_id") != signer_id:
        raise ValueError("G24_SIGNER_IDENTITY_MISMATCH")
    envelope = sign_envelope(payload, key, signer_id, schema)
    atomic_write(output_path, envelope)
    return {
        "status": "PASS_SIGNED" if payload.get("status") == "PASS" else "HOLD_SIGNED",
        "gate_payload_status": payload.get("status"),
        "signer_id": signer_id,
        "payload_sha256": envelope.get("payload_sha256"),
        "signature_emitted": True,
        "private_key_emitted": False,
        "global_certification": "NOT_GRANTED_BY_SIGNATURE_ALONE",
    }


def g24_payload(args) -> dict:
    blockers = []
    bundle = args.bundle.resolve(strict=True)
    g23_envelope = read_json(args.g23_signed)
    functional = read_json(args.functional_evidence)
    unit = read_json(args.unit_evidence)
    materialization = read_json(args.model_materialization)
    build_report = read_json(args.build_report)
    head = os.environ.get("GITHUB_SHA", "")
    validator_id = args.g23_validator_id.strip()
    certifier_id = args.certifier_id.strip()
    public_key = os.environ.get(args.g23_public_key_env, "")
    if not certifier_id or certifier_id == PRODUCER_ID or certifier_id == validator_id:
        blockers.append("G24_CERTIFIER_ID_MISSING_OR_ROLE_COLLISION")
    if not public_key.strip():
        blockers.append("G23_PUBLIC_KEY_ENV_MISSING")
        verified_g23 = None
        verify_errors = ["PUBLIC_KEY_MISSING"]
    else:
        verified_g23, verify_errors = verify_envelope(g23_envelope, public_key, G23_SIGNED_SCHEMA, validator_id)
    if verify_errors or verified_g23 is None:
        blockers.extend("G23_SIGNATURE_VERIFICATION_FAILED:" + error for error in verify_errors)
    if not verified_g23 or verified_g23.get("status") != "PASS":
        blockers.append("G23_NOT_PASS")
    bundle_hash = sha256_file(bundle)
    measured = bundle.stat().st_size
    if measured > MAX_BYTES:
        blockers.append("CANDIDATE_OVER_490000000_BYTES")
    if build_report.get("candidate", {}).get("sha256") != bundle_hash or build_report.get("candidate", {}).get("bytes") != measured:
        blockers.append("BUILD_REPORT_CANDIDATE_BINDING_MISMATCH")
    if build_report.get("source_commit") != head:
        blockers.append("BUILD_SOURCE_COMMIT_MISMATCH")
    if verified_g23 and (
        verified_g23.get("candidate", {}).get("sha256") != bundle_hash
        or verified_g23.get("candidate", {}).get("bytes") != measured
        or verified_g23.get("source_commit") != head
    ):
        blockers.append("G23_CANDIDATE_BINDING_MISMATCH")
    if unit.get("status") != "PASS" or unit.get("failures", 0) or unit.get("errors", 0):
        blockers.append("UNIT_TESTS_NOT_PASS")
    if materialization.get("status") != "PASS":
        blockers.append("PINNED_MODEL_MATERIALIZATION_NOT_PASS")
    required_results = functional.get("domain_results", {})
    failed_domains = []
    for domain in REQUIRED_DOMAINS:
        if required_results.get(domain, {}).get("status") != "PASS":
            failed_domains.append(domain)
    if functional.get("source_commit") != head:
        blockers.append("FUNCTIONAL_EVIDENCE_COMMIT_MISMATCH")
    if functional.get("model_inference_performed") is not True:
        blockers.append("REAL_MODEL_INFERENCE_NOT_PROVEN")
    if functional.get("model_identity_status") != "PASS_MODEL_SOURCE_IDENTITIES":
        blockers.append("FUNCTIONAL_MODEL_IDENTITY_NOT_PASS")
    if functional.get("functional_status") != "PASS_ALL_DOMAIN_CASES":
        blockers.append("REAL_MODEL_FUNCTIONAL_EVALUATION_NOT_PASS")
    tests = functional.get("tests")
    if not isinstance(tests, list):
        tests = []
        blockers.append("FUNCTIONAL_CASE_INVENTORY_MISSING_OR_INVALID")
    by_case = {}
    for row in tests:
        if not isinstance(row, dict) or not isinstance(row.get("case_id"), str):
            blockers.append("FUNCTIONAL_CASE_RECORD_INVALID")
            continue
        case_id = row["case_id"]
        if case_id in by_case:
            blockers.append("FUNCTIONAL_CASE_DUPLICATE:" + case_id)
        by_case[case_id] = row
    for case_id, domain in REQUIRED_CASES.items():
        row = by_case.get(case_id)
        if row is None:
            blockers.append("REQUIRED_FUNCTIONAL_CASE_MISSING:" + case_id)
            continue
        if row.get("domain_id") != domain or row.get("status") != "PASS":
            blockers.append("REQUIRED_FUNCTIONAL_CASE_NOT_PASS:" + case_id)
            continue
        if row.get("execution_status") != "PASS_EXECUTION":
            blockers.append("FUNCTIONAL_CASE_EXECUTION_NOT_PASS:" + case_id)
        if row.get("quality_criterion_passed") is not True:
            blockers.append("FUNCTIONAL_CASE_QUALITY_NOT_PASS:" + case_id)
        for field in ("input_sha256", "output_sha256"):
            value = row.get(field)
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                blockers.append("FUNCTIONAL_CASE_DIGEST_INVALID:" + case_id + ":" + field)
    summary = functional.get("summary", {})
    if summary.get("total_cases") != len(REQUIRED_CASES) or len(tests) != len(REQUIRED_CASES):
        blockers.append("FUNCTIONAL_CASE_COUNT_MISMATCH")
    if summary.get("passed_cases") != len(REQUIRED_CASES):
        blockers.append("FUNCTIONAL_PASSED_CASE_COUNT_MISMATCH")
    if not isinstance(required_results, dict):
        required_results = {}
        blockers.append("FUNCTIONAL_DOMAIN_RESULTS_INVALID")
    for domain in REQUIRED_DOMAINS:
        if required_results.get(domain, {}).get("status") != "PASS":
            blockers.append("REQUIRED_DOMAIN_FUNCTION_FAILURE:" + domain)

    # A semantic smoke test is not a repair. Require six domain-specific adapter
    # records bound to the exact source commit and candidate, with held-out and
    # independent post-validation plus a verified rollback checkpoint.
    repair_adapters = functional.get("repair_adapter_evidence")
    if functional.get("repair_execution_performed") is not True:
        blockers.append("MODEL_REPAIR_EXECUTION_NOT_PROVEN")
    if functional.get("repair_adapter_status") != "PASS_ALL_REQUIRED_ADAPTERS":
        blockers.append("REPAIR_ADAPTER_SET_NOT_PASS")
    if not isinstance(repair_adapters, list):
        repair_adapters = []
        blockers.append("REPAIR_ADAPTER_EVIDENCE_MISSING_OR_INVALID")
    adapters_by_domain = {}
    adapter_ids = []
    for adapter in repair_adapters:
        if not isinstance(adapter, dict):
            blockers.append("REPAIR_ADAPTER_RECORD_INVALID")
            continue
        domain = adapter.get("domain_id")
        if not isinstance(domain, str) or domain in adapters_by_domain:
            blockers.append("REPAIR_ADAPTER_DOMAIN_DUPLICATE_OR_INVALID")
            continue
        adapters_by_domain[domain] = adapter
        adapter_id = adapter.get("adapter_id")
        if isinstance(adapter_id, str) and adapter_id.strip():
            adapter_ids.append(adapter_id)
        else:
            blockers.append("REPAIR_ADAPTER_ID_MISSING:" + domain)
    if set(adapters_by_domain) != set(REQUIRED_REPAIR_DOMAINS) or len(adapters_by_domain) != len(repair_adapters):
        blockers.append("REPAIR_ADAPTER_DOMAIN_COVERAGE_INCOMPLETE")
    if len(adapter_ids) != len(set(adapter_ids)):
        blockers.append("REPAIR_ADAPTER_ID_COLLISION")
    for domain in REQUIRED_REPAIR_DOMAINS:
        adapter = adapters_by_domain.get(domain)
        if adapter is None:
            continue
        if adapter.get("status") != "PASS":
            blockers.append("REPAIR_ADAPTER_NOT_PASS:" + domain)
        if adapter.get("source_commit") != head:
            blockers.append("REPAIR_ADAPTER_COMMIT_MISMATCH:" + domain)
        if adapter.get("candidate_sha256") != bundle_hash:
            blockers.append("REPAIR_ADAPTER_CANDIDATE_DIGEST_MISMATCH:" + domain)
        if not isinstance(adapter.get("source_model_id"), str) or not adapter["source_model_id"].strip():
            blockers.append("REPAIR_ADAPTER_SOURCE_MODEL_MISSING:" + domain)
        for field in REPAIR_DIGEST_FIELDS:
            value = adapter.get(field)
            if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
                blockers.append("REPAIR_ADAPTER_DIGEST_INVALID:" + domain + ":" + field)
        for field in ("calibration_example_count", "heldout_example_count"):
            count = adapter.get(field)
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                blockers.append("REPAIR_ADAPTER_DATASET_COUNT_INVALID:" + domain + ":" + field)
        if adapter.get("heldout_validation_status") != "PASS":
            blockers.append("REPAIR_ADAPTER_HELDOUT_VALIDATION_NOT_PASS:" + domain)
        if adapter.get("independent_validation_status") != "PASS":
            blockers.append("REPAIR_ADAPTER_INDEPENDENT_VALIDATION_NOT_PASS:" + domain)
        if adapter.get("semantic_quality_equivalence_status") != "PASS":
            blockers.append("REPAIR_ADAPTER_QUALITY_EQUIVALENCE_NOT_PASS:" + domain)
        if adapter.get("rollback_verified") is not True:
            blockers.append("REPAIR_ADAPTER_ROLLBACK_NOT_VERIFIED:" + domain)
        if adapter.get("original_weights_mutated") is not False:
            blockers.append("REPAIR_ADAPTER_ORIGINAL_WEIGHTS_MUTATED:" + domain)
        if adapter.get("candidate_output_separate") is not True:
            blockers.append("REPAIR_ADAPTER_CANDIDATE_NOT_SEPARATE:" + domain)
    return {
        "schema": G24_SCHEMA,
        "gate": "G24_INDEPENDENT_TERMINAL_CERTIFICATION",
        "status": "PASS" if not blockers else "HOLD",
        "decision_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        "certifier_id": certifier_id,
        "validator_id": validator_id,
        "producer_id": PRODUCER_ID,
        "source_commit": head,
        "candidate": {"path": bundle.name, "bytes": measured, "sha256": bundle_hash, "cap_bytes": MAX_BYTES},
        "g23_verification": {
            "signature_status": "PASS" if verified_g23 is not None and not verify_errors else "FAIL",
            "g23_payload_status": verified_g23.get("status") if verified_g23 else "INVALID",
            "payload_sha256": g23_envelope.get("payload_sha256"),
            "verification_errors": verify_errors,
        },
        "functional_quality": {
            "status": functional.get("functional_status"),
            "domain_results": {domain: required_results.get(domain, {}) for domain in REQUIRED_DOMAINS},
            "passed_cases": functional.get("summary", {}).get("passed_cases"),
            "total_cases": functional.get("summary", {}).get("total_cases"),
            "model_inference_performed": functional.get("model_inference_performed"),
            "repair_adapter_status": functional.get("repair_adapter_status"),
            "repair_adapter_domains": sorted(adapters_by_domain),
            "full_size_original_equivalence": (
                "PASS" if functional.get("repair_adapter_status") == "PASS_ALL_REQUIRED_ADAPTERS"
                and all(adapters_by_domain.get(domain, {}).get("semantic_quality_equivalence_status") == "PASS" for domain in REQUIRED_REPAIR_DOMAINS)
                else "NOT_ESTABLISHED"
            ),
        },
        "externalized_model_integrity": {
            "status": materialization.get("status"),
            "models": materialization.get("models", []),
        },
        "evidence_sha256": {
            "build_report": sha256_file(args.build_report),
            "g23_signed": sha256_file(args.g23_signed),
            "unit_tests": sha256_file(args.unit_evidence),
            "model_materialization": sha256_file(args.model_materialization),
            "functional_evidence": sha256_file(args.functional_evidence),
        },
        "blockers": blockers,
        "terminal_decision": "CERTIFIED_INTEGRAL_WITHIN_TESTED_SCOPE" if not blockers else "NOT_CERTIFIED",
        "global_certification": "CERTIFIED" if not blockers else "NOT_GRANTED",
        "limitations": [
            "Real model tests establish only the declared test scope; they do not prove all capabilities of full-size source models.",
            "Externalized weights are fetched explicitly from pinned sources and are not embedded in the single-file artifact.",
        ],
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    g23 = sub.add_parser("prepare-g23")
    for option in ("bundle", "build-report", "worker-evidence", "unit-evidence", "model-materialization", "functional-evidence", "source-architecture", "cajita-doc", "output"):
        g23.add_argument("--" + option, required=True, type=Path)
    g23.add_argument("--validator-id", required=True)

    sign23 = sub.add_parser("sign-g23")
    sign23.add_argument("--input", required=True, type=Path)
    sign23.add_argument("--output", required=True, type=Path)
    sign23.add_argument("--signer-id", required=True)
    sign23.add_argument("--private-key-env", default="CAJITA_G23_SIGNING_PRIVATE_KEY_PEM")

    g24 = sub.add_parser("issue-g24")
    for option in ("bundle", "g23-signed", "functional-evidence", "unit-evidence", "model-materialization", "build-report", "output"):
        g24.add_argument("--" + option, required=True, type=Path)
    g24.add_argument("--g23-validator-id", required=True)
    g24.add_argument("--g23-public-key-env", default="CAJITA_G23_PUBLIC_KEY_PEM")
    g24.add_argument("--certifier-id", required=True)
    g24.add_argument("--private-key-env", default="CAJITA_G24_SIGNING_PRIVATE_KEY_PEM")
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-g23":
            result = g23_payload(args)
            atomic_write(args.output, result)
            print(json.dumps({key: result.get(key) for key in ("status", "candidate", "blockers", "global_certification")}, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        if args.command == "sign-g23":
            result = sign_payload(args.input, args.output, args.signer_id, args.private_key_env, G23_SIGNED_SCHEMA)
            print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
            return 0
        result = g24_payload(args)
        signed = sign_envelope(
            result,
            os.environ.get(args.private_key_env, ""),
            args.certifier_id,
            G24_SIGNED_SCHEMA,
        ) if os.environ.get(args.private_key_env, "").strip() else None
        if signed is not None:
            atomic_write(args.output, signed)
        else:
            atomic_write(args.output, result)
        print(json.dumps({
            "status": result["status"],
            "terminal_decision": result["terminal_decision"],
            "blockers": result["blockers"],
            "signed": signed is not None,
            "global_certification": result["global_certification"],
        }, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if result["status"] == "PASS" and signed is not None else 2
    except Exception as exc:
        failure = {
            "schema": "LOUKSNAPG2_GATE_FAILURE/1.0",
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc)[:500],
            "global_certification": "NOT_GRANTED",
        }
        target = getattr(args, "output", None)
        if isinstance(target, Path):
            atomic_write(target, failure)
        print(json.dumps(failure, ensure_ascii=False, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
