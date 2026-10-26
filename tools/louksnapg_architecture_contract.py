#!/usr/bin/env python3
"""Validate the LOUKSNAPG architectural contract and (optionally) real release evidence.

Contract integrity is deliberately separate from product certification. A passing
static contract check always reports global_certification=NOT_GRANTED. Product
evidence is evaluated only against the explicit evidence schema and remains HOLD
unless every worker, target, telemetry, G23, G24, safety and rollback binding passes.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_CONTRACT = Path(__file__).resolve().parents[1] / "contracts" / "louksnapg" / "architecture-contract.v1.json"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
EXPECTED_OBLIGATIONS = [
    "C1_COORDINATED_WORKERS", "C2_OFFICIAL_SOURCE_REPAIR", "C3_PRIMITIVE_FUNCTIONS",
    "C4_TELEMETRY_AND_AUDIT", "C5_GOVERNED_RELEASE_CHAIN", "C6_PROHIBITIONS_AND_RECOVERY",
]
EXPECTED_MODEL_URLS = {
    "D01_CEREBRO_ROOT": ("https://github.com/openai/gpt-oss", "openai/gpt-oss-120b"),
    "D03_TRANSCRIPCION_ROOT": ("https://github.com/openai/whisper", "turbo"),
    "D04_TRADUCCION_GENERAL": ("https://github.com/facebookresearch/seamless_communication", "facebook/seamless-m4t-v2-large"),
    "D05_DOCLING": ("https://huggingface.co/ibm-granite/granite-docling-258M", "ibm-granite/granite-docling-258M"),
    "D06_ANALISIS_AVANZADO": ("https://github.com/QwenLM/Qwen3", "Qwen/Qwen3-0.6B"),
}
REQUIRED_TELEMETRY = {
    "SOURCE", "INPUT", "OPERATION", "OUTPUT", "TEST", "VALIDATION",
    "INDEPENDENT_VALIDATION_G23", "KESTRA_AUDIT", "CERTIFICATION_DECISION_G24",
    "NON_REGRESSION", "ROLLBACK",
}


def _sha(value: Any) -> bool:
    return isinstance(value, str) and bool(SHA256_RE.fullmatch(value))


def _commit(value: Any) -> bool:
    return isinstance(value, str) and bool(COMMIT_RE.fullmatch(value))


def _object(value: Any) -> bool:
    return isinstance(value, dict)


def _nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _load_json(path: Path) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("INPUT_NOT_REGULAR_FILE:" + str(path))
    return json.loads(path.read_text(encoding="utf-8"))


def canonical_target_ids_from_gate() -> list[str]:
    """Read the registered gate IDs without importing inference/crypto dependencies."""
    gate_path = Path(__file__).resolve().with_name("louksnapg_integral_gate.py")
    if gate_path.is_symlink() or not gate_path.is_file():
        raise ValueError("INTEGRAL_GATE_SOURCE_MISSING_OR_UNSAFE")
    module = ast.parse(gate_path.read_text(encoding="utf-8"), filename=str(gate_path))
    for node in module.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(target, ast.Name) and target.id == "EXPECTED_TARGET_IDS" for target in targets):
                value_node = node.value
                value = ast.literal_eval(value_node)
                if not isinstance(value, (tuple, list)) or not all(isinstance(item, str) for item in value):
                    raise ValueError("INTEGRAL_GATE_TARGET_ID_DECLARATION_INVALID")
                return list(value)
    raise ValueError("INTEGRAL_GATE_TARGET_ID_DECLARATION_NOT_FOUND")


def validate_contract(contract: Any, expected_target_ids: list[str] | tuple[str, ...] | None = None) -> list[str]:
    failures: list[str] = []
    if not _object(contract):
        return ["CONTRACT_ROOT_NOT_OBJECT"]
    if contract.get("schema") != "LOUKSNAPG_ARCHITECTURAL_CONTRACT/1.0":
        failures.append("CONTRACT_SCHEMA_MISMATCH")
    if contract.get("contract_id") != "LOUKSNAPG-AC-001":
        failures.append("CONTRACT_ID_MISMATCH")
    if contract.get("state") != "ACTIVE_ENFORCED":
        failures.append("CONTRACT_NOT_ACTIVE_ENFORCED")
    if contract.get("authority") != "Louksna.md" or contract.get("doctrine") != "EXTEND_DO_NOT_REPLACE":
        failures.append("CANONICAL_AUTHORITY_OR_DOCTRINE_MISMATCH")
    if contract.get("mutation_policy") != "APPEND_ONLY" or contract.get("failure_policy") != "FAIL_CLOSED":
        failures.append("MUTATION_OR_FAILURE_POLICY_MISMATCH")
    if contract.get("release_state_without_complete_evidence") != "HOLD_NOT_CERTIFIED":
        failures.append("DEFAULT_RELEASE_STATE_NOT_HOLD")
    workers = contract.get("workers")
    if not _object(workers):
        failures.append("WORKER_CONTRACT_MISSING")
    else:
        if workers.get("primary", {}).get("id") != "CUSTOSZ_V9":
            failures.append("PRIMARY_WORKER_MUST_BE_CUSTOSZ_V9")
        if workers.get("secondary", {}).get("id") != "KESTRA":
            failures.append("SECONDARY_WORKER_MUST_BE_KESTRA")
        if workers.get("primary", {}).get("may_self_certify") is not False:
            failures.append("CUSTOSZ_SELF_CERTIFICATION_MUST_BE_FORBIDDEN")
        if workers.get("secondary", {}).get("may_replace_g23_or_g24") is not False:
            failures.append("KESTRA_MUST_NOT_REPLACE_G23_OR_G24")
        if workers.get("missing_or_disconnected_worker") != "HOLD":
            failures.append("DISCONNECTED_WORKER_MUST_HOLD")
        if not isinstance(workers.get("correlation_fields"), list) or not {
            "source_commit", "bundle_sha256", "contract_sha256"
        }.issubset(set(workers.get("correlation_fields", []))):
            failures.append("WORKER_CORRELATION_BINDINGS_INCOMPLETE")

    obligations = contract.get("obligations")
    ids = [o.get("id") for o in obligations if _object(o)] if isinstance(obligations, list) else []
    if ids != EXPECTED_OBLIGATIONS:
        failures.append("SIX_OBLIGATIONS_MISSING_REORDERED_OR_REASSIGNED")
    if not isinstance(obligations, list) or any(not _object(o) or o.get("status") != "MANDATORY" or not _nonempty(o.get("rule")) for o in obligations):
        failures.append("OBLIGATION_RULE_OR_MANDATORY_STATUS_INVALID")

    source_catalog = contract.get("source_catalog")
    catalog = {row.get("target_id"): row for row in source_catalog if _object(row)} if isinstance(source_catalog, list) else {}
    if set(catalog) != set(EXPECTED_MODEL_URLS):
        failures.append("OFFICIAL_MODEL_SOURCE_CATALOG_INCOMPLETE_OR_DUPLICATE")
    for target, (url, model_id) in EXPECTED_MODEL_URLS.items():
        row = catalog.get(target, {})
        if row.get("official_url") != url or row.get("model_id") != model_id:
            failures.append("OFFICIAL_MODEL_IDENTITY_MISMATCH:" + target)
        if row.get("variant_must_be_pinned") is not True:
            failures.append("MODEL_VARIANT_PIN_REQUIRED:" + target)
    whisper = catalog.get("D03_TRANSCRIPCION_ROOT", {})
    if whisper.get("task") != "speech_transcription_only" or whisper.get("translation_use_prohibited") is not True:
        failures.append("WHISPER_TURBO_TRANSLATION_MISUSE_NOT_BLOCKED")
    qwen = catalog.get("D06_ANALISIS_AVANZADO", {})
    if not isinstance(qwen.get("allowed_variants"), list) or not qwen["allowed_variants"] or qwen.get("variant_must_be_pinned") is not True:
        failures.append("QWEN3_VARIANT_NOT_PINNED_BY_CONTRACT")
    if catalog.get("D01_CEREBRO_ROOT", {}).get("heavy_weight_download_prohibited") is not True:
        failures.append("GPT_OSS_HEAVY_DOWNLOAD_NOT_BLOCKED")
    if catalog.get("D04_TRADUCCION_GENERAL", {}).get("heavy_weight_download_prohibited") is not True:
        failures.append("SEAMLESS_HEAVY_DOWNLOAD_NOT_BLOCKED")

    actual_targets = contract.get("target_ids")
    if not isinstance(actual_targets, list) or len(actual_targets) != 21 or len(set(actual_targets)) != 21:
        failures.append("TARGET_ID_SET_MUST_CONTAIN_21_UNIQUE_IDS")
    if expected_target_ids is not None and list(actual_targets or []) != list(expected_target_ids):
        failures.append("TARGET_ID_SET_DIFFERS_FROM_INTEGRAL_GATE")

    telemetry = contract.get("telemetry")
    if not _object(telemetry) or not set(REQUIRED_TELEMETRY).issubset(set(telemetry.get("required_event_types", []))):
        failures.append("TELEMETRY_EVENT_CHAIN_INCOMPLETE")
    if not _object(telemetry) or telemetry.get("persistence_required") is not True or telemetry.get("candidate_and_source_commit_binding_required") is not True:
        failures.append("TELEMETRY_PERSISTENCE_OR_BINDING_DISABLED")
    required_fields = {"operation_id", "sequence_id", "timestamp_utc", "actor", "tool_name", "tool_version", "source", "input_sha256", "output_sha256", "input_bytes", "output_bytes", "validation_status", "rollback_reference", "status"}
    if not _object(telemetry) or not required_fields.issubset(set(telemetry.get("required_fields", []))):
        failures.append("TELEMETRY_REQUIRED_FIELDS_INCOMPLETE")

    gates = contract.get("gates")
    expected_chain = ["SPECIFICATION", "EVIDENCE", "VALIDATION", "INDEPENDENT_VALIDATION_G23", "KESTRA_AUDIT", "SEPARATE_CERTIFICATION_G24", "NON_REGRESSION", "ROLLBACK_VERIFICATION", "ACTIVE"]
    if not _object(gates) or gates.get("chain") != expected_chain:
        failures.append("GOVERNANCE_CERTIFICATION_CHAIN_INVALID")
    if not _object(gates) or gates.get("missing_evidence_action") != "HOLD_NOT_CERTIFIED" or gates.get("global_certification_before_g24") != "NOT_GRANTED" or gates.get("merge_or_promotion_before_all_gates") != "PROHIBITED":
        failures.append("FAIL_CLOSED_OR_NO_AUTO_CERTIFICATION_POLICY_INVALID")
    if not _object(gates) or not set(["all_21_targets_pass", "real_runtime_execution", "synthetic_only_false", "custosz_v9_real_receipt", "kestra_real_receipt", "g23_signature_verified", "separate_g24_signature_verified", "rollback_pass", "non_regression_pass"]).issubset(set(gates.get("hard_requirements", []))):
        failures.append("RELEASE_HARD_REQUIREMENTS_INCOMPLETE")

    prohibitions = contract.get("prohibitions")
    expected_prohibitions = {
        "heavy_model_weights_download": False, "remote_commander_use": False,
        "canonical_identity_mutation": False, "block_or_axiom_reassignment": False,
        "engine_substitution_without_explicit_authorization": False,
        "synthetic_evidence_as_product_proof": False, "self_certification": False,
        "automatic_g23_to_g24_propagation": False, "merge_or_promotion_without_complete_chain": False,
    }
    if prohibitions != expected_prohibitions:
        failures.append("PROHIBITED_ACTION_POLICY_CHANGED")
    evidence_schema = contract.get("evidence_schema")
    if evidence_schema != "LOUKSNAPG_ARCHITECTURE_EXECUTION_EVIDENCE/1.0":
        failures.append("EXECUTION_EVIDENCE_SCHEMA_UNDECLARED")
    return sorted(set(failures))


def evaluate_execution_evidence(contract: dict, contract_bytes: bytes, evidence: Any,
                                expected_target_ids: list[str] | tuple[str, ...] | None = None) -> dict:
    failures: list[str] = []
    contract_sha = hashlib.sha256(contract_bytes).hexdigest()
    if not _object(evidence):
        evidence = {}
        failures.append("EXECUTION_EVIDENCE_ROOT_NOT_OBJECT")
    if evidence.get("schema") != contract.get("evidence_schema"):
        failures.append("EXECUTION_EVIDENCE_SCHEMA_MISMATCH")
    if evidence.get("contract_sha256") != contract_sha:
        failures.append("CONTRACT_SHA256_MISMATCH")
    source_commit = evidence.get("source_commit")
    if not _commit(source_commit):
        failures.append("SOURCE_COMMIT_INVALID")
    bundle_sha = evidence.get("bundle_sha256")
    if not _sha(bundle_sha):
        failures.append("BUNDLE_SHA256_INVALID")
    target_ids = list(expected_target_ids or contract.get("target_ids", []))

    worker_runs = evidence.get("worker_runs")
    for worker_id in ("CUSTOSZ_V9", "KESTRA"):
        row = worker_runs.get(worker_id, {}) if _object(worker_runs) else {}
        if row.get("status") != "PASS" or row.get("source_commit") != source_commit:
            failures.append("WORKER_STATUS_OR_COMMIT_MISMATCH:" + worker_id)
        if not _nonempty(row.get("run_id")):
            failures.append("WORKER_REAL_RUN_ID_MISSING:" + worker_id)
        for field in ("input_sha256", "output_sha256", "telemetry_sha256"):
            if not _sha(row.get(field)):
                failures.append("WORKER_EVIDENCE_HASH_INVALID:" + worker_id + ":" + field)

    sources = evidence.get("official_source_review")
    if not _object(sources) or sources.get("status") != "PASS":
        failures.append("OFFICIAL_SOURCE_REVIEW_NOT_PASS")
    source_rows = sources.get("models", []) if _object(sources) else []
    by_target = {row.get("target_id"): row for row in source_rows if _object(row)}
    if set(by_target) != set(EXPECTED_MODEL_URLS):
        failures.append("OFFICIAL_MODEL_EVIDENCE_SET_INCOMPLETE")
    catalog = {row.get("target_id"): row for row in contract.get("source_catalog", [])}
    for target, (url, default_model) in EXPECTED_MODEL_URLS.items():
        row = by_target.get(target, {})
        if row.get("source_url") != url:
            failures.append("OFFICIAL_SOURCE_URL_MISMATCH:" + target)
        model_id = row.get("model_id")
        allowed = catalog.get(target, {}).get("allowed_variants", [default_model])
        if model_id != default_model and model_id not in allowed:
            failures.append("MODEL_VARIANT_NOT_ALLOWED:" + target)
        if not _commit(row.get("revision_commit")):
            failures.append("UPSTREAM_REVISION_NOT_PINNED:" + target)
        if not _sha(row.get("weights_sha256")):
            failures.append("MODEL_WEIGHTS_SHA256_MISSING:" + target)
        if not _sha(row.get("inference_code_sha256")) or not _sha(row.get("tokenizer_or_processor_sha256")):
            failures.append("MODEL_RUNTIME_OR_TOKENIZER_HASH_MISSING:" + target)

    repair = evidence.get("repair_result")
    if not _object(repair) or repair.get("status") != "PASS" or repair.get("model_targets_repaired") != 5 or not _sha(repair.get("report_sha256")):
        failures.append("MATERIAL_MODEL_REPAIR_NOT_VERIFIED")

    functional = evidence.get("functional_gate")
    if not _object(functional) or functional.get("decision") != "PASS" or functional.get("target_pass_count") != 21 or functional.get("synthetic_only") is not False:
        failures.append("REAL_21_TARGET_FUNCTIONAL_GATE_NOT_PASS")
    if not _object(functional) or functional.get("source_commit") != source_commit or functional.get("bundle_sha256") != bundle_sha or not _sha(functional.get("report_sha256")):
        failures.append("FUNCTIONAL_GATE_SUBJECT_BINDING_INVALID")
    target_results = functional.get("target_results", []) if _object(functional) else []
    by_id = {row.get("target_id"): row for row in target_results if _object(row)}
    if set(by_id) != set(target_ids) or len(target_results) != len(target_ids):
        failures.append("FUNCTIONAL_TARGET_SET_INCOMPLETE_OR_DUPLICATED")
    if any(row.get("status") != "PASS" or row.get("synthetic_only") is not False for row in by_id.values()):
        failures.append("ONE_OR_MORE_TARGETS_NOT_REAL_FUNCTIONAL_PASS")

    telemetry = evidence.get("telemetry")
    if not _object(telemetry) or telemetry.get("status") != "PASS" or not _sha(telemetry.get("evidence_sha256")):
        failures.append("PERSISTENT_TELEMETRY_NOT_PASS")
    events = telemetry.get("events", []) if _object(telemetry) else []
    event_names = {row.get("event_type") for row in events if _object(row) and isinstance(row.get("count"), int) and row.get("count", 0) > 0 and _sha(row.get("evidence_sha256"))}
    if not REQUIRED_TELEMETRY.issubset(event_names):
        failures.append("TELEMETRY_EVENT_EVIDENCE_INCOMPLETE")

    kestra = evidence.get("kestra_audit")
    if not _object(kestra) or kestra.get("status") != "PASS" or not _nonempty(kestra.get("execution_id")) or not _sha(kestra.get("report_sha256")):
        failures.append("KESTRA_REAL_AUDIT_NOT_PASS")
    for gate_name, wanted_status in (("g23", "PASS"), ("g24", "GRANTED")):
        row = evidence.get(gate_name)
        if not _object(row) or row.get("status") != wanted_status or row.get("signature_verified") is not True:
            failures.append(gate_name.upper() + "_SIGNED_DECISION_NOT_VERIFIED")
        if not _object(row) or row.get("source_commit") != source_commit or row.get("bundle_sha256") != bundle_sha or not _sha(row.get("attestation_sha256")):
            failures.append(gate_name.upper() + "_SUBJECT_BINDING_INVALID")
    g23 = evidence.get("g23", {})
    g24 = evidence.get("g24", {})
    if _object(g23) and _object(g24):
        if g24.get("signer_id") in {g23.get("producer_id"), g23.get("validator_id")}:
            failures.append("G24_SIGNER_NOT_INDEPENDENT_OF_G23")
    for field in ("host_matrix_status", "rollback_status", "non_regression_status", "axiom_binding_status", "block_binding_status"):
        if evidence.get(field) != "PASS":
            failures.append(field.upper() + "_NOT_PASS")
    safety = evidence.get("safety")
    expected_safety = {"heavy_model_download_count": 0, "remote_commander_used": False, "canonical_mutation": False, "synthetic_evidence_used": False}
    if safety != expected_safety:
        failures.append("SAFETY_CONSTRAINT_VIOLATION_OR_UNPROVEN")

    return {
        "schema": "LOUKSNAPG_ARCHITECTURE_CONTRACT_DECISION/1.0",
        "contract_id": contract.get("contract_id"),
        "contract_sha256": contract_sha,
        "source_commit": source_commit if _commit(source_commit) else None,
        "bundle_sha256": bundle_sha if _sha(bundle_sha) else None,
        "decision": "PASS_RELEASE_ELIGIBLE_FOR_AUTHORIZED_ACTIVATION" if not failures else "HOLD_NOT_CERTIFIED",
        "release_eligible": not failures,
        "global_certification": "NOT_GRANTED_BY_THIS_VALIDATOR",
        "failure_count": len(set(failures)),
        "failures": sorted(set(failures)),
        "note": "This contract evaluator checks that independent gate reports claim verified signatures; the cryptographic verification of G23 remains the responsibility of louksnapg_integral_gate.py and G24 remains a separately authorized decision."
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--execution-evidence", type=Path)
    parser.add_argument("--require-execution-evidence", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args(argv)
    report_path = args.report
    try:
        contract_bytes = args.contract.read_bytes()
        if args.contract.is_symlink() or not args.contract.is_file():
            raise ValueError("CONTRACT_NOT_REGULAR_FILE")
        contract = json.loads(contract_bytes.decode("utf-8"))
        expected_target_ids = canonical_target_ids_from_gate()
        failures = validate_contract(contract, expected_target_ids)
        if failures:
            report = {"schema":"LOUKSNAPG_ARCHITECTURE_CONTRACT_DECISION/1.0","decision":"HOLD_INVALID_CONTRACT","contract_status":"FAIL","release_eligible":False,"global_certification":"NOT_GRANTED","failures":failures}
        else:
            report = {"schema":"LOUKSNAPG_ARCHITECTURE_CONTRACT_DECISION/1.0","decision":"CONTRACT_VALID_EXECUTION_HOLD","contract_status":"PASS","contract_id":contract["contract_id"],"contract_sha256":hashlib.sha256(contract_bytes).hexdigest(),"release_eligible":False,"global_certification":"NOT_GRANTED","failures":[],"execution_status":"HOLD_NO_EXECUTION_EVIDENCE"}
        if args.execution_evidence:
            evidence = _load_json(args.execution_evidence)
            decision = evaluate_execution_evidence(contract, contract_bytes, evidence, EXPECTED_TARGET_IDS)
            report["execution_evidence_decision"] = decision
            report["execution_status"] = decision["decision"]
            report["release_eligible"] = decision["release_eligible"]
            report["failures"] = decision["failures"]
        elif args.require_execution_evidence:
            report["execution_status"] = "HOLD_EXECUTION_EVIDENCE_REQUIRED"
            report["failures"] = sorted(set(report.get("failures", []) + ["EXECUTION_EVIDENCE_REQUIRED_BUT_MISSING"]))
            report["release_eligible"] = False
    except Exception as exc:
        report = {"schema":"LOUKSNAPG_ARCHITECTURE_CONTRACT_DECISION/1.0","decision":"HOLD_VALIDATION_ERROR","contract_status":"FAIL","release_eligible":False,"global_certification":"NOT_GRANTED","failures":[type(exc).__name__ + ":" + str(exc)[:500]]}
    text = json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if report.get("contract_status") == "PASS" and (not args.require_execution_evidence or report.get("release_eligible") is True) else 2


if __name__ == "__main__":
    raise SystemExit(main())
