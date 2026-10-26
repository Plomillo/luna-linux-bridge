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
from datetime import datetime
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
    "D03_TRANSCRIPCION_ROOT": ("https://github.com/openai/whisper", "openai/whisper-large-v3-turbo"),
    "D04_TRADUCCION_GENERAL": ("https://github.com/facebookresearch/seamless_communication", "facebook/seamless-m4t-v2-large"),
    "D05_DOCLING": ("https://huggingface.co/ibm-granite/granite-docling-258M", "ibm-granite/granite-docling-258M"),
    "D06_ANALISIS_AVANZADO": ("https://github.com/QwenLM/Qwen3", "Qwen/Qwen3-0.6B"),
}
EXPECTED_SOURCE_REVISIONS = {
    "D01_CEREBRO_ROOT": "5681a6b6552635e7b29cde94a61ca6a7aee90ebd",
    "D03_TRANSCRIPCION_ROOT": "86098128c0b4f24f0e2aa2994de830614b474227",
    "D04_TRADUCCION_GENERAL": "9a081e935c29c6b1e0e05bcbf3fcb623ad306524",
    "D05_DOCLING": "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe",
    "D06_ANALISIS_AVANZADO": "7a2f61ffc7a20d47efcd2bf97f6f2bf52729042e",
}
EXPECTED_MODEL_REVISIONS = {
    "D01_CEREBRO_ROOT": "b5c939de8f754692c1647ca79fbf85e8c1e70f8a",
    "D03_TRANSCRIPCION_ROOT": "41f01f3fe87f28c78e2fbf8b568835947dd65ed9",
    "D04_TRADUCCION_GENERAL": "b8d7691bcced0d24b2655f534b6148be78346b72",
    "D05_DOCLING": "982fe3b40f2fa73c365bdb1bcacf6c81b7184bfe",
    "D06_ANALISIS_AVANZADO": "c1899de289a04d12100db370d81485cdf75e47ca",
}

EXPECTED_CALIBRE_PIN = {
    "id": "CAJITA_CALIBRE_SLIM",
    "upstream_repository": "https://github.com/kovidgoyal/calibre",
    "official_release_url": "https://github.com/kovidgoyal/calibre/releases/tag/v9.17.0",
    "tag": "v9.17.0",
    "tag_object_sha": "58cfea71a2c2d893b853d73ca586ec9b28f7b2ba",
    "tag_signature_verified": True,
    "tag_signature_key_id": "06BC317B515ACE7C",
    "commit_sha": "e6b9e09472f6e63f8a12bf376eb54836042f0f5f",
    "runtime_version": "9.17.0",
    "source_lock_path": "cajita-luna-runtime/5. Inteligencia documental/Conversión documental/Calibre Slim/source-lock.json",
    "inventory_policy": "RECOMPUTE_ARCHIVE_AND_FULL_CACHE_FILE_SET_SIZE_SHA256_MODE_DIRECTORY_SET_ON_EVERY_INVOCATION",
    "runtime_policy": "DISCOVER_SYSTEM_EBOOK_CONVERT_AND_REQUIRE_EXACT_CALIBRE_VERSION_TOKEN",
}
EXPECTED_CALIBRE_RELEASE_ASSETS = [{"id":"CALIBRE_V9_17_0_LINUX_X86_64_BINARY","url":"https://github.com/kovidgoyal/calibre/releases/download/v9.17.0/calibre-9.17.0-x86_64.txz","filename":"calibre-9.17.0-x86_64.txz","size_bytes":201590724,"sha256":"953e4512a6482848cd803c88b6d942e6afca65dc3b67c7d1353ae048d616de53"}, {"id":"CALIBRE_V9_17_0_SOURCE","url":"https://github.com/kovidgoyal/calibre/releases/download/v9.17.0/calibre-9.17.0.tar.xz","filename":"calibre-9.17.0.tar.xz","size_bytes":50661596,"sha256":"07507ea8ace5f8a0f768c13afdb799ad685a636c1cdbd8b11162ddb419743be5"}]
EXPECTED_CALIBRE_OVERLAY = {"path":"cajita-luna-runtime/5. Inteligencia documental/Conversión documental/Calibre Slim/calibre-slim-overlay.tar.xz","filename":"calibre-slim-overlay.tar.xz","size_bytes":58180,"sha256":"dc1518eccd24d0bb6a294918381d9d42fa24df8b05026d1f173dadbd6e70977b"}
CALIBRE_SOURCE_LOCK_PATH = Path(__file__).resolve().parents[1] / "cajita-luna-runtime" / "5. Inteligencia documental" / "Conversión documental" / "Calibre Slim" / "source-lock.json"
CALIBRE_CONVERTER_PATH = CALIBRE_SOURCE_LOCK_PATH.with_name("calibre-slim-convert.py")
REQUIRED_REPAIR_TARGETS = {
    "D01_CEREBRO_ROOT", "D03_TRANSCRIPCION_ROOT", "D04_TRADUCCION_GENERAL",
    "D05_DOCLING", "D06_ANALISIS_AVANZADO",
}
REQUIRED_REPAIR_FIELDS = {
    "target_id", "status", "synthetic_only", "official_source_url", "upstream_model_id",
    "upstream_revision_commit", "upstream_weights_sha256", "candidate_before_weights_sha256",
    "candidate_after_weights_sha256", "repair_implementation_commit", "test_evidence_sha256",
    "quality_report_sha256", "expected_test_count", "passed_test_count", "semantic_quality_status",
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
    if contract.get("global_luna_hard_max_bytes") != 479000000:
        failures.append("GLOBAL_LUNA_HARD_MAX_BYTES_MISMATCH")
    if contract.get("candidate_distribution_max_bytes") != 479000000:
        failures.append("CANDIDATE_DISTRIBUTION_CAP_MISMATCH")
    if contract.get("cajita_runtime_archive_max_bytes") != 470000000:
        failures.append("CAJITA_RUNTIME_CAP_MISMATCH")
    if contract.get("byte_budget_policy") != "GLOBAL_LUNA_HARD_MAX_BYTES_APPLIES_TO_COMPLETE_SINGLE_FILE_DISTRIBUTION; NO_REWARD_FOR_APPROACHING_CAP; CAJITA_RUNTIME_CAP_IS_SEPARATE":
        failures.append("BYTE_BUDGET_POLICY_MISMATCH")
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

    toolchain_pins = contract.get("toolchain_pins")
    calibre_rows = [row for row in toolchain_pins if _object(row) and row.get("id") == EXPECTED_CALIBRE_PIN["id"]] if isinstance(toolchain_pins, list) else []
    if len(calibre_rows) != 1 or len(toolchain_pins) != 1:
        failures.append("CALIBRE_TOOLCHAIN_PIN_MISSING_DUPLICATED_OR_UNAUTHORIZED")
    else:
        calibre_pin = calibre_rows[0]
        for field, expected in EXPECTED_CALIBRE_PIN.items():
            if calibre_pin.get(field) != expected:
                failures.append("CALIBRE_TOOLCHAIN_PIN_MISMATCH:" + field)
        if calibre_pin.get("release_assets") != EXPECTED_CALIBRE_RELEASE_ASSETS:
            failures.append("CALIBRE_RELEASE_ASSET_PIN_MISMATCH")
        if calibre_pin.get("overlay_archive") != EXPECTED_CALIBRE_OVERLAY:
            failures.append("CALIBRE_OVERLAY_ARCHIVE_PIN_MISMATCH")
        if calibre_pin.get("inventory_policy") != "RECOMPUTE_ARCHIVE_AND_FULL_CACHE_FILE_SET_SIZE_SHA256_MODE_DIRECTORY_SET_ON_EVERY_INVOCATION":
            failures.append("CALIBRE_FULL_OVERLAY_INVENTORY_REVALIDATION_REQUIRED")

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
        if not _commit(row.get("official_source_revision_commit")):
            failures.append("OFFICIAL_SOURCE_REVISION_NOT_PINNED:" + target)
        if not _nonempty(row.get("official_source_revision_url")):
            failures.append("OFFICIAL_SOURCE_REVISION_URL_MISSING:" + target)
        if row.get("source_pin_type") not in {"official_source_code_commit", "official_model_repository_commit"}:
            failures.append("OFFICIAL_SOURCE_PIN_TYPE_INVALID:" + target)
        if not _nonempty(row.get("model_repository")):
            failures.append("OFFICIAL_MODEL_REPOSITORY_URL_MISSING:" + target)
        if row.get("official_source_revision_commit") != EXPECTED_SOURCE_REVISIONS[target]:
            failures.append("OFFICIAL_SOURCE_REVISION_COMMIT_MISMATCH:" + target)
        model_revision = row.get("model_repository_revision_commit")
        if model_revision != EXPECTED_MODEL_REVISIONS[target]:
            failures.append("MODEL_REPOSITORY_REVISION_NOT_PINNED_OR_MISMATCHED:" + target)
        if not _commit(model_revision):
            failures.append("MODEL_REPOSITORY_REVISION_NOT_PINNED:" + target)
        if row.get("allowed_variants") not in (None, [model_id]):
            failures.append("UNAUTHORIZED_MODEL_VARIANT_SUBSTITUTION_ALLOWED:" + target)
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
    repair_spec = contract.get("model_repair_evidence")
    if not _object(repair_spec):
        failures.append("MODEL_REPAIR_EVIDENCE_SPEC_MISSING")
    else:
        if repair_spec.get("required_model_target_count") != 5 or set(repair_spec.get("target_ids", [])) != REQUIRED_REPAIR_TARGETS:
            failures.append("MODEL_REPAIR_TARGET_REGISTRY_INVALID")
        if set(repair_spec.get("required_per_target_fields", [])) != REQUIRED_REPAIR_FIELDS:
            failures.append("MODEL_REPAIR_EVIDENCE_FIELDS_INVALID")
        if repair_spec.get("repair_must_change_candidate_weights") is not True or repair_spec.get("candidate_after_hash_must_match_functional_gate") is not True:
            failures.append("MATERIAL_REPAIR_AND_FUNCTIONAL_HASH_BINDING_REQUIRED")
        if repair_spec.get("synthetic_evidence_allowed") is not False or repair_spec.get("semantic_quality_pass_required") is not True or repair_spec.get("release_implication_if_missing") != "HOLD_NOT_CERTIFIED":
            failures.append("MODEL_REPAIR_FAIL_CLOSED_POLICY_INVALID")

    evidence_schema = contract.get("evidence_schema")
    if evidence_schema != "LOUKSNAPG_ARCHITECTURE_EXECUTION_EVIDENCE/1.0":
        failures.append("EXECUTION_EVIDENCE_SCHEMA_UNDECLARED")
    return sorted(set(failures))


def validate_calibre_source_lock(contract: dict, lock_path: Path | None = None,
                               converter_path: Path | None = None) -> list[str]:
    """Cross-check the canonical contract against the checked-in lock and overlay constants."""
    failures: list[str] = []
    pins = contract.get("toolchain_pins", [])
    rows = [row for row in pins if _object(row) and row.get("id") == EXPECTED_CALIBRE_PIN["id"]] if isinstance(pins, list) else []
    if len(rows) != 1:
        return ["CALIBRE_SOURCE_LOCK_CONTRACT_BINDING_MISSING"]
    pin = rows[0]
    lock_path = lock_path or CALIBRE_SOURCE_LOCK_PATH
    converter_path = converter_path or CALIBRE_CONVERTER_PATH
    try:
        lock = _load_json(lock_path)
    except Exception:
        return ["CALIBRE_SOURCE_LOCK_MISSING_OR_INVALID"]
    for field in ("upstream_repository", "tag", "tag_object_sha", "commit_sha"):
        if lock.get(field) != pin.get(field if field != "upstream_repository" else "upstream_repository"):
            failures.append("CALIBRE_SOURCE_LOCK_IDENTITY_MISMATCH:" + field)
    tag_signature = lock.get("tag_signature_status")
    if not isinstance(tag_signature, dict) or tag_signature.get("reported_by_github") != "verified":
        failures.append("CALIBRE_SOURCE_LOCK_TAG_SIGNATURE_NOT_VERIFIED")
    lock_assets = lock.get("artifacts")
    by_id = {row.get("id"): row for row in lock_assets if _object(row)} if isinstance(lock_assets, list) else {}
    expected = {row["id"]: row for row in pin.get("release_assets", []) if _object(row)}
    if not isinstance(lock_assets, list) or len(by_id) != len(lock_assets) or set(by_id) != set(expected):
        failures.append("CALIBRE_SOURCE_LOCK_ASSET_SET_MISMATCH")
    else:
        for asset_id, expect in expected.items():
            observed = by_id[asset_id]
            for field in ("url", "filename", "size_bytes", "sha256"):
                if observed.get(field) != expect.get(field):
                    failures.append("CALIBRE_SOURCE_LOCK_ASSET_MISMATCH:" + asset_id + ":" + field)
    try:
        source = converter_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        failures.append("CALIBRE_CONVERTER_SOURCE_MISSING_OR_INVALID")
        source = ""
    overlay = pin.get("overlay_archive", {})
    patterns = {
        "filename": (r'^ARCHIVE_NAME\s*=\s*"([^"]+)"                                expected_target_ids: list[str] | tuple[str, ...] | None = None) -> dict:
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
    bundle_bytes = evidence.get("bundle_bytes")
    if isinstance(bundle_bytes, bool) or not isinstance(bundle_bytes, int) or bundle_bytes <= 0:
        failures.append("BUNDLE_BYTES_INVALID")
    elif bundle_bytes > int(contract.get("global_luna_hard_max_bytes", 479000000)):
        failures.append("BUNDLE_EXCEEDS_GLOBAL_LUNA_HARD_MAX_BYTES")
    target_ids = list(expected_target_ids or contract.get("target_ids", []))

    worker_runs = evidence.get("worker_runs")
    for worker_id in ("CUSTOSZ_V9", "KESTRA"):
        row = worker_runs.get(worker_id, {}) if _object(worker_runs) else {}
        if row.get("status") != "PASS" or row.get("source_commit") != source_commit:
            failures.append("WORKER_STATUS_OR_COMMIT_MISMATCH:" + worker_id)
        if row.get("contract_sha256") != contract_sha:
            failures.append("WORKER_CONTRACT_SHA256_MISMATCH:" + worker_id)
        if row.get("bundle_sha256") != bundle_sha:
            failures.append("WORKER_BUNDLE_SHA256_MISMATCH:" + worker_id)
        if not _nonempty(row.get("run_id")):
            failures.append("WORKER_REAL_RUN_ID_MISSING:" + worker_id)
        if worker_id == "KESTRA" and not _nonempty(row.get("execution_id")):
            failures.append("KESTRA_EXECUTION_ID_MISSING")
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
        if row.get("source_revision_commit") != catalog.get(target, {}).get("official_source_revision_commit"):
            failures.append("OFFICIAL_SOURCE_REVISION_COMMIT_MISMATCH:" + target)
        if row.get("source_revision_url") != catalog.get(target, {}).get("official_source_revision_url"):
            failures.append("OFFICIAL_SOURCE_REVISION_URL_MISMATCH:" + target)
        model_id = row.get("model_id")
        allowed = catalog.get(target, {}).get("allowed_variants", [default_model])
        if model_id != default_model and model_id not in allowed:
            failures.append("MODEL_VARIANT_NOT_ALLOWED:" + target)
        if not _commit(row.get("revision_commit")):
            failures.append("UPSTREAM_REVISION_NOT_PINNED:" + target)
        if row.get("revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_MISMATCH:" + target)
        if row.get("model_repository_revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_FIELD_MISMATCH:" + target)
        if not _sha(row.get("weights_sha256")):
            failures.append("MODEL_WEIGHTS_SHA256_MISSING:" + target)
        if not _sha(row.get("inference_code_sha256")) or not _sha(row.get("tokenizer_or_processor_sha256")):
            failures.append("MODEL_RUNTIME_OR_TOKENIZER_HASH_MISSING:" + target)

    repair = evidence.get("repair_result")
    repair_rows = repair.get("model_repairs", []) if _object(repair) else []
    repair_by_id = {row.get("target_id"): row for row in repair_rows if _object(row)}
    if not _object(repair) or repair.get("status") != "PASS" or repair.get("model_targets_repaired") != 5 or not _sha(repair.get("report_sha256")):
        failures.append("MATERIAL_MODEL_REPAIR_NOT_VERIFIED")
    if set(repair_by_id) != REQUIRED_REPAIR_TARGETS or len(repair_rows) != 5:
        failures.append("MODEL_REPAIR_EVIDENCE_SET_INCOMPLETE_OR_DUPLICATED")
    repair_spec = contract.get("model_repair_evidence", {})
    if not _object(repair_spec) or repair_spec.get("required_per_target_fields") is None:
        failures.append("MODEL_REPAIR_EVIDENCE_CONTRACT_SCHEMA_MISSING")
    catalog = {row.get("target_id"): row for row in contract.get("source_catalog", []) if _object(row)}
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        row = repair_by_id.get(target_id, {})
        missing_fields = REQUIRED_REPAIR_FIELDS - set(row)
        if missing_fields:
            failures.append("MODEL_REPAIR_REQUIRED_FIELDS_MISSING:" + target_id + ":" + ",".join(sorted(missing_fields)))
        if row.get("status") != "PASS":
            failures.append("MODEL_REPAIR_NOT_PASS:" + target_id)
        if row.get("synthetic_only") is not False:
            failures.append("MODEL_REPAIR_SYNTHETIC_OR_UNPROVEN:" + target_id)
        if row.get("official_source_url") != catalog.get(target_id, {}).get("official_url"):
            failures.append("MODEL_REPAIR_OFFICIAL_SOURCE_MISMATCH:" + target_id)
        allowed_ids = catalog.get(target_id, {}).get("allowed_variants", [catalog.get(target_id, {}).get("model_id")])
        if row.get("upstream_model_id") not in allowed_ids:
            failures.append("MODEL_REPAIR_UPSTREAM_MODEL_ID_INVALID:" + target_id)
        if not _commit(row.get("upstream_revision_commit")):
            failures.append("MODEL_REPAIR_UPSTREAM_REVISION_NOT_PINNED:" + target_id)
        if not _commit(row.get("repair_implementation_commit")):
            failures.append("MODEL_REPAIR_IMPLEMENTATION_COMMIT_INVALID:" + target_id)
        for field in ("upstream_weights_sha256", "candidate_before_weights_sha256", "candidate_after_weights_sha256", "test_evidence_sha256", "quality_report_sha256"):
            if not _sha(row.get(field)):
                failures.append("MODEL_REPAIR_HASH_INVALID:" + target_id + ":" + field)
        if _sha(row.get("candidate_before_weights_sha256")) and row.get("candidate_before_weights_sha256") == row.get("candidate_after_weights_sha256"):
            failures.append("MODEL_REPAIR_DID_NOT_CHANGE_CANDIDATE_WEIGHTS:" + target_id)
        expected_cases = row.get("expected_test_count")
        passed_cases = row.get("passed_test_count")
        if isinstance(expected_cases, bool) or not isinstance(expected_cases, int) or expected_cases < 1:
            failures.append("MODEL_REPAIR_EXPECTED_TEST_COUNT_INVALID:" + target_id)
        if isinstance(passed_cases, bool) or not isinstance(passed_cases, int) or passed_cases != expected_cases:
            failures.append("MODEL_REPAIR_TEST_CASES_NOT_ALL_PASS:" + target_id)
        if row.get("semantic_quality_status") != "PASS":
            failures.append("MODEL_REPAIR_SEMANTIC_QUALITY_NOT_PASS:" + target_id)

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
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        repair_row = repair_by_id.get(target_id, {})
        functional_row = by_id.get(target_id, {})
        if _sha(repair_row.get("candidate_after_weights_sha256")) and repair_row.get("candidate_after_weights_sha256") != functional_row.get("weight_sha256"):
            failures.append("REPAIRED_WEIGHT_HASH_NOT_BOUND_TO_FUNCTIONAL_RUN:" + target_id)

    telemetry = evidence.get("telemetry")
    if not _object(telemetry) or telemetry.get("status") != "PASS" or not _sha(telemetry.get("evidence_sha256")):
        failures.append("PERSISTENT_TELEMETRY_NOT_PASS")
    events = telemetry.get("events", []) if _object(telemetry) else []
    event_names = [row.get("event_type") for row in events if _object(row)]
    if set(event_names) != REQUIRED_TELEMETRY or len(event_names) != len(REQUIRED_TELEMETRY) or len(events) != len(REQUIRED_TELEMETRY):
        failures.append("TELEMETRY_EVENT_SET_INCOMPLETE_OR_DUPLICATED")
    expected_sequence = list(range(1, len(events) + 1))
    observed_sequence = []
    for row in events:
        if not _object(row):
            failures.append("TELEMETRY_EVENT_ROW_INVALID")
            continue
        sequence = row.get("sequence_id")
        observed_sequence.append(sequence)
        if row.get("source_commit") != source_commit or row.get("bundle_sha256") != bundle_sha or row.get("contract_sha256") != contract_sha:
            failures.append("TELEMETRY_EVENT_SUBJECT_BINDING_MISMATCH")
        if not _sha(row.get("input_sha256")) or not _sha(row.get("output_sha256")) or row.get("evidence_sha256") != row.get("output_sha256"):
            failures.append("TELEMETRY_EVENT_HASH_INVALID")
        event_payload = dict(row)
        recorded_event_sha = event_payload.pop("evidence_sha256", None)
        event_payload.pop("output_sha256", None)
        event_output_bytes = event_payload.pop("output_bytes", None)
        event_canonical = json.dumps(event_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(event_canonical).hexdigest() != recorded_event_sha:
            failures.append("TELEMETRY_EVENT_PAYLOAD_HASH_MISMATCH")
        if event_output_bytes != len(event_canonical):
            failures.append("TELEMETRY_EVENT_OUTPUT_BYTE_COUNT_MISMATCH")
        if isinstance(row.get("count"), bool) or row.get("count") != 1:
            failures.append("TELEMETRY_EVENT_COUNT_INVALID")
        for field in ("input_bytes", "output_bytes"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                failures.append("TELEMETRY_EVENT_BYTE_COUNT_INVALID:" + field)
        if not _nonempty(row.get("rollback_reference")) or not _nonempty(row.get("status")) or not _nonempty(row.get("actor")) or not _nonempty(row.get("tool_name")) or not _nonempty(row.get("tool_version")):
            failures.append("TELEMETRY_EVENT_AUDIT_FIELDS_MISSING")
        try:
            stamp = datetime.fromisoformat(str(row.get("timestamp_utc", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                failures.append("TELEMETRY_TIMESTAMP_MISSING_TIMEZONE")
        except ValueError:
            failures.append("TELEMETRY_TIMESTAMP_INVALID")
    if observed_sequence != expected_sequence:
        failures.append("TELEMETRY_SEQUENCE_NOT_CONTIGUOUS")
    if _object(telemetry) and _sha(telemetry.get("evidence_sha256")):
        telem_payload = dict(telemetry)
        recorded_telem_sha = telem_payload.pop("evidence_sha256", None)
        canonical_telem = json.dumps(telem_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(canonical_telem).hexdigest() != recorded_telem_sha:
            failures.append("TELEMETRY_ENVELOPE_SHA256_MISMATCH")

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
        failures = sorted(set(validate_contract(contract, expected_target_ids) + validate_calibre_source_lock(contract)))
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
, str(overlay.get("filename"))),
        "size_bytes": (r"^ARCHIVE_BYTES\s*=\s*(\d+)$", str(overlay.get("size_bytes"))),
        "sha256": (r'^ARCHIVE_SHA256\s*=\s*"([0-9a-f]{64})"                                expected_target_ids: list[str] | tuple[str, ...] | None = None) -> dict:
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
    bundle_bytes = evidence.get("bundle_bytes")
    if isinstance(bundle_bytes, bool) or not isinstance(bundle_bytes, int) or bundle_bytes <= 0:
        failures.append("BUNDLE_BYTES_INVALID")
    elif bundle_bytes > int(contract.get("global_luna_hard_max_bytes", 479000000)):
        failures.append("BUNDLE_EXCEEDS_GLOBAL_LUNA_HARD_MAX_BYTES")
    target_ids = list(expected_target_ids or contract.get("target_ids", []))

    worker_runs = evidence.get("worker_runs")
    for worker_id in ("CUSTOSZ_V9", "KESTRA"):
        row = worker_runs.get(worker_id, {}) if _object(worker_runs) else {}
        if row.get("status") != "PASS" or row.get("source_commit") != source_commit:
            failures.append("WORKER_STATUS_OR_COMMIT_MISMATCH:" + worker_id)
        if row.get("contract_sha256") != contract_sha:
            failures.append("WORKER_CONTRACT_SHA256_MISMATCH:" + worker_id)
        if row.get("bundle_sha256") != bundle_sha:
            failures.append("WORKER_BUNDLE_SHA256_MISMATCH:" + worker_id)
        if not _nonempty(row.get("run_id")):
            failures.append("WORKER_REAL_RUN_ID_MISSING:" + worker_id)
        if worker_id == "KESTRA" and not _nonempty(row.get("execution_id")):
            failures.append("KESTRA_EXECUTION_ID_MISSING")
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
        if row.get("source_revision_commit") != catalog.get(target, {}).get("official_source_revision_commit"):
            failures.append("OFFICIAL_SOURCE_REVISION_COMMIT_MISMATCH:" + target)
        if row.get("source_revision_url") != catalog.get(target, {}).get("official_source_revision_url"):
            failures.append("OFFICIAL_SOURCE_REVISION_URL_MISMATCH:" + target)
        model_id = row.get("model_id")
        allowed = catalog.get(target, {}).get("allowed_variants", [default_model])
        if model_id != default_model and model_id not in allowed:
            failures.append("MODEL_VARIANT_NOT_ALLOWED:" + target)
        if not _commit(row.get("revision_commit")):
            failures.append("UPSTREAM_REVISION_NOT_PINNED:" + target)
        if row.get("revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_MISMATCH:" + target)
        if row.get("model_repository_revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_FIELD_MISMATCH:" + target)
        if not _sha(row.get("weights_sha256")):
            failures.append("MODEL_WEIGHTS_SHA256_MISSING:" + target)
        if not _sha(row.get("inference_code_sha256")) or not _sha(row.get("tokenizer_or_processor_sha256")):
            failures.append("MODEL_RUNTIME_OR_TOKENIZER_HASH_MISSING:" + target)

    repair = evidence.get("repair_result")
    repair_rows = repair.get("model_repairs", []) if _object(repair) else []
    repair_by_id = {row.get("target_id"): row for row in repair_rows if _object(row)}
    if not _object(repair) or repair.get("status") != "PASS" or repair.get("model_targets_repaired") != 5 or not _sha(repair.get("report_sha256")):
        failures.append("MATERIAL_MODEL_REPAIR_NOT_VERIFIED")
    if set(repair_by_id) != REQUIRED_REPAIR_TARGETS or len(repair_rows) != 5:
        failures.append("MODEL_REPAIR_EVIDENCE_SET_INCOMPLETE_OR_DUPLICATED")
    repair_spec = contract.get("model_repair_evidence", {})
    if not _object(repair_spec) or repair_spec.get("required_per_target_fields") is None:
        failures.append("MODEL_REPAIR_EVIDENCE_CONTRACT_SCHEMA_MISSING")
    catalog = {row.get("target_id"): row for row in contract.get("source_catalog", []) if _object(row)}
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        row = repair_by_id.get(target_id, {})
        missing_fields = REQUIRED_REPAIR_FIELDS - set(row)
        if missing_fields:
            failures.append("MODEL_REPAIR_REQUIRED_FIELDS_MISSING:" + target_id + ":" + ",".join(sorted(missing_fields)))
        if row.get("status") != "PASS":
            failures.append("MODEL_REPAIR_NOT_PASS:" + target_id)
        if row.get("synthetic_only") is not False:
            failures.append("MODEL_REPAIR_SYNTHETIC_OR_UNPROVEN:" + target_id)
        if row.get("official_source_url") != catalog.get(target_id, {}).get("official_url"):
            failures.append("MODEL_REPAIR_OFFICIAL_SOURCE_MISMATCH:" + target_id)
        allowed_ids = catalog.get(target_id, {}).get("allowed_variants", [catalog.get(target_id, {}).get("model_id")])
        if row.get("upstream_model_id") not in allowed_ids:
            failures.append("MODEL_REPAIR_UPSTREAM_MODEL_ID_INVALID:" + target_id)
        if not _commit(row.get("upstream_revision_commit")):
            failures.append("MODEL_REPAIR_UPSTREAM_REVISION_NOT_PINNED:" + target_id)
        if not _commit(row.get("repair_implementation_commit")):
            failures.append("MODEL_REPAIR_IMPLEMENTATION_COMMIT_INVALID:" + target_id)
        for field in ("upstream_weights_sha256", "candidate_before_weights_sha256", "candidate_after_weights_sha256", "test_evidence_sha256", "quality_report_sha256"):
            if not _sha(row.get(field)):
                failures.append("MODEL_REPAIR_HASH_INVALID:" + target_id + ":" + field)
        if _sha(row.get("candidate_before_weights_sha256")) and row.get("candidate_before_weights_sha256") == row.get("candidate_after_weights_sha256"):
            failures.append("MODEL_REPAIR_DID_NOT_CHANGE_CANDIDATE_WEIGHTS:" + target_id)
        expected_cases = row.get("expected_test_count")
        passed_cases = row.get("passed_test_count")
        if isinstance(expected_cases, bool) or not isinstance(expected_cases, int) or expected_cases < 1:
            failures.append("MODEL_REPAIR_EXPECTED_TEST_COUNT_INVALID:" + target_id)
        if isinstance(passed_cases, bool) or not isinstance(passed_cases, int) or passed_cases != expected_cases:
            failures.append("MODEL_REPAIR_TEST_CASES_NOT_ALL_PASS:" + target_id)
        if row.get("semantic_quality_status") != "PASS":
            failures.append("MODEL_REPAIR_SEMANTIC_QUALITY_NOT_PASS:" + target_id)

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
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        repair_row = repair_by_id.get(target_id, {})
        functional_row = by_id.get(target_id, {})
        if _sha(repair_row.get("candidate_after_weights_sha256")) and repair_row.get("candidate_after_weights_sha256") != functional_row.get("weight_sha256"):
            failures.append("REPAIRED_WEIGHT_HASH_NOT_BOUND_TO_FUNCTIONAL_RUN:" + target_id)

    telemetry = evidence.get("telemetry")
    if not _object(telemetry) or telemetry.get("status") != "PASS" or not _sha(telemetry.get("evidence_sha256")):
        failures.append("PERSISTENT_TELEMETRY_NOT_PASS")
    events = telemetry.get("events", []) if _object(telemetry) else []
    event_names = [row.get("event_type") for row in events if _object(row)]
    if set(event_names) != REQUIRED_TELEMETRY or len(event_names) != len(REQUIRED_TELEMETRY) or len(events) != len(REQUIRED_TELEMETRY):
        failures.append("TELEMETRY_EVENT_SET_INCOMPLETE_OR_DUPLICATED")
    expected_sequence = list(range(1, len(events) + 1))
    observed_sequence = []
    for row in events:
        if not _object(row):
            failures.append("TELEMETRY_EVENT_ROW_INVALID")
            continue
        sequence = row.get("sequence_id")
        observed_sequence.append(sequence)
        if row.get("source_commit") != source_commit or row.get("bundle_sha256") != bundle_sha or row.get("contract_sha256") != contract_sha:
            failures.append("TELEMETRY_EVENT_SUBJECT_BINDING_MISMATCH")
        if not _sha(row.get("input_sha256")) or not _sha(row.get("output_sha256")) or row.get("evidence_sha256") != row.get("output_sha256"):
            failures.append("TELEMETRY_EVENT_HASH_INVALID")
        event_payload = dict(row)
        recorded_event_sha = event_payload.pop("evidence_sha256", None)
        event_payload.pop("output_sha256", None)
        event_output_bytes = event_payload.pop("output_bytes", None)
        event_canonical = json.dumps(event_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(event_canonical).hexdigest() != recorded_event_sha:
            failures.append("TELEMETRY_EVENT_PAYLOAD_HASH_MISMATCH")
        if event_output_bytes != len(event_canonical):
            failures.append("TELEMETRY_EVENT_OUTPUT_BYTE_COUNT_MISMATCH")
        if isinstance(row.get("count"), bool) or row.get("count") != 1:
            failures.append("TELEMETRY_EVENT_COUNT_INVALID")
        for field in ("input_bytes", "output_bytes"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                failures.append("TELEMETRY_EVENT_BYTE_COUNT_INVALID:" + field)
        if not _nonempty(row.get("rollback_reference")) or not _nonempty(row.get("status")) or not _nonempty(row.get("actor")) or not _nonempty(row.get("tool_name")) or not _nonempty(row.get("tool_version")):
            failures.append("TELEMETRY_EVENT_AUDIT_FIELDS_MISSING")
        try:
            stamp = datetime.fromisoformat(str(row.get("timestamp_utc", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                failures.append("TELEMETRY_TIMESTAMP_MISSING_TIMEZONE")
        except ValueError:
            failures.append("TELEMETRY_TIMESTAMP_INVALID")
    if observed_sequence != expected_sequence:
        failures.append("TELEMETRY_SEQUENCE_NOT_CONTIGUOUS")
    if _object(telemetry) and _sha(telemetry.get("evidence_sha256")):
        telem_payload = dict(telemetry)
        recorded_telem_sha = telem_payload.pop("evidence_sha256", None)
        canonical_telem = json.dumps(telem_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(canonical_telem).hexdigest() != recorded_telem_sha:
            failures.append("TELEMETRY_ENVELOPE_SHA256_MISMATCH")

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
, str(overlay.get("sha256"))),
    }
    for field, (pattern, expected_value) in patterns.items():
        match = re.search(pattern, source, flags=re.MULTILINE)
        if not match or match.group(1) != expected_value:
            failures.append("CALIBRE_OVERLAY_CONSTANT_MISMATCH:" + field)
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
    bundle_bytes = evidence.get("bundle_bytes")
    if isinstance(bundle_bytes, bool) or not isinstance(bundle_bytes, int) or bundle_bytes <= 0:
        failures.append("BUNDLE_BYTES_INVALID")
    elif bundle_bytes > int(contract.get("global_luna_hard_max_bytes", 479000000)):
        failures.append("BUNDLE_EXCEEDS_GLOBAL_LUNA_HARD_MAX_BYTES")
    target_ids = list(expected_target_ids or contract.get("target_ids", []))

    worker_runs = evidence.get("worker_runs")
    for worker_id in ("CUSTOSZ_V9", "KESTRA"):
        row = worker_runs.get(worker_id, {}) if _object(worker_runs) else {}
        if row.get("status") != "PASS" or row.get("source_commit") != source_commit:
            failures.append("WORKER_STATUS_OR_COMMIT_MISMATCH:" + worker_id)
        if row.get("contract_sha256") != contract_sha:
            failures.append("WORKER_CONTRACT_SHA256_MISMATCH:" + worker_id)
        if row.get("bundle_sha256") != bundle_sha:
            failures.append("WORKER_BUNDLE_SHA256_MISMATCH:" + worker_id)
        if not _nonempty(row.get("run_id")):
            failures.append("WORKER_REAL_RUN_ID_MISSING:" + worker_id)
        if worker_id == "KESTRA" and not _nonempty(row.get("execution_id")):
            failures.append("KESTRA_EXECUTION_ID_MISSING")
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
        if row.get("source_revision_commit") != catalog.get(target, {}).get("official_source_revision_commit"):
            failures.append("OFFICIAL_SOURCE_REVISION_COMMIT_MISMATCH:" + target)
        if row.get("source_revision_url") != catalog.get(target, {}).get("official_source_revision_url"):
            failures.append("OFFICIAL_SOURCE_REVISION_URL_MISMATCH:" + target)
        model_id = row.get("model_id")
        allowed = catalog.get(target, {}).get("allowed_variants", [default_model])
        if model_id != default_model and model_id not in allowed:
            failures.append("MODEL_VARIANT_NOT_ALLOWED:" + target)
        if not _commit(row.get("revision_commit")):
            failures.append("UPSTREAM_REVISION_NOT_PINNED:" + target)
        if row.get("revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_MISMATCH:" + target)
        if row.get("model_repository_revision_commit") != catalog.get(target, {}).get("model_repository_revision_commit"):
            failures.append("UPSTREAM_MODEL_REPOSITORY_REVISION_FIELD_MISMATCH:" + target)
        if not _sha(row.get("weights_sha256")):
            failures.append("MODEL_WEIGHTS_SHA256_MISSING:" + target)
        if not _sha(row.get("inference_code_sha256")) or not _sha(row.get("tokenizer_or_processor_sha256")):
            failures.append("MODEL_RUNTIME_OR_TOKENIZER_HASH_MISSING:" + target)

    repair = evidence.get("repair_result")
    repair_rows = repair.get("model_repairs", []) if _object(repair) else []
    repair_by_id = {row.get("target_id"): row for row in repair_rows if _object(row)}
    if not _object(repair) or repair.get("status") != "PASS" or repair.get("model_targets_repaired") != 5 or not _sha(repair.get("report_sha256")):
        failures.append("MATERIAL_MODEL_REPAIR_NOT_VERIFIED")
    if set(repair_by_id) != REQUIRED_REPAIR_TARGETS or len(repair_rows) != 5:
        failures.append("MODEL_REPAIR_EVIDENCE_SET_INCOMPLETE_OR_DUPLICATED")
    repair_spec = contract.get("model_repair_evidence", {})
    if not _object(repair_spec) or repair_spec.get("required_per_target_fields") is None:
        failures.append("MODEL_REPAIR_EVIDENCE_CONTRACT_SCHEMA_MISSING")
    catalog = {row.get("target_id"): row for row in contract.get("source_catalog", []) if _object(row)}
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        row = repair_by_id.get(target_id, {})
        missing_fields = REQUIRED_REPAIR_FIELDS - set(row)
        if missing_fields:
            failures.append("MODEL_REPAIR_REQUIRED_FIELDS_MISSING:" + target_id + ":" + ",".join(sorted(missing_fields)))
        if row.get("status") != "PASS":
            failures.append("MODEL_REPAIR_NOT_PASS:" + target_id)
        if row.get("synthetic_only") is not False:
            failures.append("MODEL_REPAIR_SYNTHETIC_OR_UNPROVEN:" + target_id)
        if row.get("official_source_url") != catalog.get(target_id, {}).get("official_url"):
            failures.append("MODEL_REPAIR_OFFICIAL_SOURCE_MISMATCH:" + target_id)
        allowed_ids = catalog.get(target_id, {}).get("allowed_variants", [catalog.get(target_id, {}).get("model_id")])
        if row.get("upstream_model_id") not in allowed_ids:
            failures.append("MODEL_REPAIR_UPSTREAM_MODEL_ID_INVALID:" + target_id)
        if not _commit(row.get("upstream_revision_commit")):
            failures.append("MODEL_REPAIR_UPSTREAM_REVISION_NOT_PINNED:" + target_id)
        if not _commit(row.get("repair_implementation_commit")):
            failures.append("MODEL_REPAIR_IMPLEMENTATION_COMMIT_INVALID:" + target_id)
        for field in ("upstream_weights_sha256", "candidate_before_weights_sha256", "candidate_after_weights_sha256", "test_evidence_sha256", "quality_report_sha256"):
            if not _sha(row.get(field)):
                failures.append("MODEL_REPAIR_HASH_INVALID:" + target_id + ":" + field)
        if _sha(row.get("candidate_before_weights_sha256")) and row.get("candidate_before_weights_sha256") == row.get("candidate_after_weights_sha256"):
            failures.append("MODEL_REPAIR_DID_NOT_CHANGE_CANDIDATE_WEIGHTS:" + target_id)
        expected_cases = row.get("expected_test_count")
        passed_cases = row.get("passed_test_count")
        if isinstance(expected_cases, bool) or not isinstance(expected_cases, int) or expected_cases < 1:
            failures.append("MODEL_REPAIR_EXPECTED_TEST_COUNT_INVALID:" + target_id)
        if isinstance(passed_cases, bool) or not isinstance(passed_cases, int) or passed_cases != expected_cases:
            failures.append("MODEL_REPAIR_TEST_CASES_NOT_ALL_PASS:" + target_id)
        if row.get("semantic_quality_status") != "PASS":
            failures.append("MODEL_REPAIR_SEMANTIC_QUALITY_NOT_PASS:" + target_id)

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
    for target_id in sorted(REQUIRED_REPAIR_TARGETS):
        repair_row = repair_by_id.get(target_id, {})
        functional_row = by_id.get(target_id, {})
        if _sha(repair_row.get("candidate_after_weights_sha256")) and repair_row.get("candidate_after_weights_sha256") != functional_row.get("weight_sha256"):
            failures.append("REPAIRED_WEIGHT_HASH_NOT_BOUND_TO_FUNCTIONAL_RUN:" + target_id)

    telemetry = evidence.get("telemetry")
    if not _object(telemetry) or telemetry.get("status") != "PASS" or not _sha(telemetry.get("evidence_sha256")):
        failures.append("PERSISTENT_TELEMETRY_NOT_PASS")
    events = telemetry.get("events", []) if _object(telemetry) else []
    event_names = [row.get("event_type") for row in events if _object(row)]
    if set(event_names) != REQUIRED_TELEMETRY or len(event_names) != len(REQUIRED_TELEMETRY) or len(events) != len(REQUIRED_TELEMETRY):
        failures.append("TELEMETRY_EVENT_SET_INCOMPLETE_OR_DUPLICATED")
    expected_sequence = list(range(1, len(events) + 1))
    observed_sequence = []
    for row in events:
        if not _object(row):
            failures.append("TELEMETRY_EVENT_ROW_INVALID")
            continue
        sequence = row.get("sequence_id")
        observed_sequence.append(sequence)
        if row.get("source_commit") != source_commit or row.get("bundle_sha256") != bundle_sha or row.get("contract_sha256") != contract_sha:
            failures.append("TELEMETRY_EVENT_SUBJECT_BINDING_MISMATCH")
        if not _sha(row.get("input_sha256")) or not _sha(row.get("output_sha256")) or row.get("evidence_sha256") != row.get("output_sha256"):
            failures.append("TELEMETRY_EVENT_HASH_INVALID")
        event_payload = dict(row)
        recorded_event_sha = event_payload.pop("evidence_sha256", None)
        event_payload.pop("output_sha256", None)
        event_output_bytes = event_payload.pop("output_bytes", None)
        event_canonical = json.dumps(event_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(event_canonical).hexdigest() != recorded_event_sha:
            failures.append("TELEMETRY_EVENT_PAYLOAD_HASH_MISMATCH")
        if event_output_bytes != len(event_canonical):
            failures.append("TELEMETRY_EVENT_OUTPUT_BYTE_COUNT_MISMATCH")
        if isinstance(row.get("count"), bool) or row.get("count") != 1:
            failures.append("TELEMETRY_EVENT_COUNT_INVALID")
        for field in ("input_bytes", "output_bytes"):
            value = row.get(field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                failures.append("TELEMETRY_EVENT_BYTE_COUNT_INVALID:" + field)
        if not _nonempty(row.get("rollback_reference")) or not _nonempty(row.get("status")) or not _nonempty(row.get("actor")) or not _nonempty(row.get("tool_name")) or not _nonempty(row.get("tool_version")):
            failures.append("TELEMETRY_EVENT_AUDIT_FIELDS_MISSING")
        try:
            stamp = datetime.fromisoformat(str(row.get("timestamp_utc", "")).replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                failures.append("TELEMETRY_TIMESTAMP_MISSING_TIMEZONE")
        except ValueError:
            failures.append("TELEMETRY_TIMESTAMP_INVALID")
    if observed_sequence != expected_sequence:
        failures.append("TELEMETRY_SEQUENCE_NOT_CONTIGUOUS")
    if _object(telemetry) and _sha(telemetry.get("evidence_sha256")):
        telem_payload = dict(telemetry)
        recorded_telem_sha = telem_payload.pop("evidence_sha256", None)
        canonical_telem = json.dumps(telem_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        if hashlib.sha256(canonical_telem).hexdigest() != recorded_telem_sha:
            failures.append("TELEMETRY_ENVELOPE_SHA256_MISMATCH")

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
