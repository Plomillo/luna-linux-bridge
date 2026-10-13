"""SUPER1200 D04 authority primitives for capabilities 109-112.

This module is additive and intentionally separate from D04_runtime.py so that
previous scope certificates bound to D04_runtime.py remain source-stable.
No function in this module grants global SUPER1200 certification.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import datetime, timezone
from typing import Any


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _nonempty(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    return value.strip()


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError(field + "_invalid_iso8601")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(field + "_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_timezone_required")
    return parsed.astimezone(timezone.utc)


def _stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _sha(value: Any) -> str:
    return hashlib.sha256(canonical_json(value)).hexdigest()


def _key(value: Any) -> bytes:
    if not isinstance(value, (bytes, bytearray)) or len(value) < 32:
        raise ValueError("signing_key_minimum_32_bytes_required")
    return bytes(value)


def _signature(payload: dict[str, Any], key: bytes) -> str:
    unsigned = dict(payload)
    unsigned.pop("signature_hmac_sha256", None)
    unsigned.pop("proof_sha256", None)
    unsigned.pop("lease_sha256", None)
    return hmac.new(key, canonical_json(unsigned), hashlib.sha256).hexdigest()


def _verify_signature(payload: dict[str, Any], key: bytes) -> bool:
    supplied = payload.get("signature_hmac_sha256")
    return isinstance(supplied, str) and hmac.compare_digest(supplied, _signature(payload, key))


def _scope(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
        raise ValueError(field + "_nonempty_string_list_required")
    normalized = sorted(set(x.strip() for x in value))
    if len(normalized) != len(value):
        raise ValueError(field + "_duplicates_not_allowed")
    return normalized


def make_authorization_proof(
    *, subject: str, action: str, object_id: str, scope: list[str],
    not_before_utc: str, not_after_utc: str, issuer: str,
    delegation_chain: list[dict[str, Any]], revocation_id: str,
    provenance: dict[str, Any], key_id: str, signing_key: bytes,
) -> dict[str, Any]:
    """Create a signed proof binding identity, operation, object, scope, time and provenance."""
    key = _key(signing_key)
    subject = _nonempty(subject, "subject")
    action = _nonempty(action, "action")
    object_id = _nonempty(object_id, "object_id")
    issuer = _nonempty(issuer, "issuer")
    revocation_id = _nonempty(revocation_id, "revocation_id")
    key_id = _nonempty(key_id, "key_id")
    start, end = _utc(not_before_utc, "not_before_utc"), _utc(not_after_utc, "not_after_utc")
    if end <= start:
        raise ValueError("authority_interval_invalid")
    if not isinstance(delegation_chain, list) or any(not isinstance(x, dict) for x in delegation_chain):
        raise ValueError("delegation_chain_invalid")
    requested_scope = _scope(scope, "scope")
    if not isinstance(provenance, dict) or not all(isinstance(provenance.get(k), str) and provenance[k].strip()
            for k in ("source", "evidence_sha256", "recorded_at_utc")):
        raise ValueError("provenance_required")
    if not re.fullmatch(r"[0-9a-f]{64}", provenance["evidence_sha256"]):
        raise ValueError("provenance_evidence_sha256_invalid")
    _utc(provenance["recorded_at_utc"], "provenance_recorded_at_utc")
    actor = issuer
    allowed_scope = set(requested_scope)
    normalized_chain = []
    for index, step in enumerate(delegation_chain):
        from_actor = _nonempty(step.get("from"), f"delegation_{index}_from")
        to_actor = _nonempty(step.get("to"), f"delegation_{index}_to")
        if from_actor != actor:
            raise ValueError("delegation_chain_discontinuous")
        step_scope = set(_scope(step.get("scope"), f"delegation_{index}_scope"))
        allowed_scope &= step_scope
        step_start, step_end = _utc(step.get("not_before_utc"), f"delegation_{index}_not_before_utc"), _utc(step.get("not_after_utc"), f"delegation_{index}_not_after_utc")
        if step_end <= step_start:
            raise ValueError("delegation_interval_invalid")
        normalized_chain.append({"from": from_actor, "to": to_actor, "scope": sorted(step_scope),
            "not_before_utc": _stamp(step_start), "not_after_utc": _stamp(step_end),
            "revocation_id": _nonempty(step.get("revocation_id"), f"delegation_{index}_revocation_id"),
            "provenance_sha256": _nonempty(step.get("provenance_sha256"), f"delegation_{index}_provenance_sha256")})
        actor = to_actor
    if delegation_chain and actor != subject:
        raise ValueError("delegation_chain_subject_mismatch")
    if not delegation_chain and issuer != subject:
        raise ValueError("delegation_chain_required_for_distinct_subject")
    if set(requested_scope) - allowed_scope:
        raise ValueError("delegation_scope_exceeds_authority")
    proof = {"schema": "SUPER1200_AUTHORIZATION_PROOF/1", "subject": subject, "action": action,
        "object_id": object_id, "scope": requested_scope, "not_before_utc": _stamp(start),
        "not_after_utc": _stamp(end), "issuer": issuer, "delegation_chain": normalized_chain,
        "revocation_id": revocation_id, "provenance": dict(provenance), "key_id": key_id}
    proof["signature_hmac_sha256"] = _signature(proof, key)
    proof["proof_sha256"] = _sha(proof)
    return proof


def verify_authorization_proof(
    proof: Any, *, signing_key: bytes, trusted_now_utc: str,
    expected_subject: str, expected_action: str, expected_object_id: str,
    required_scope: list[str], trusted_issuers: list[str], revoked_ids: list[str],
) -> dict[str, Any]:
    """Fail-closed proof verification; trusted time and expected operation are explicit inputs."""
    reasons = []
    try:
        key = _key(signing_key)
        now = _utc(trusted_now_utc, "trusted_now_utc")
    except ValueError as exc:
        return {"decision": "DENY", "reasons": [str(exc)], "proof_sha256": None}
    if not isinstance(proof, dict) or proof.get("schema") != "SUPER1200_AUTHORIZATION_PROOF/1":
        return {"decision": "DENY", "reasons": ["authorization_proof_schema_invalid"], "proof_sha256": None}
    if not _verify_signature(proof, key):
        reasons.append("authorization_proof_signature_invalid")
    unsigned = dict(proof); recorded_hash = unsigned.pop("proof_sha256", None)
    if recorded_hash != _sha(unsigned):
        reasons.append("authorization_proof_hash_invalid")
    try:
        start, end = _utc(proof.get("not_before_utc"), "not_before_utc"), _utc(proof.get("not_after_utc"), "not_after_utc")
        if end <= start: reasons.append("authority_interval_invalid")
        elif now < start: reasons.append("authority_not_yet_valid")
        elif now >= end: reasons.append("authority_expired")
        requested_scope = set(_scope(required_scope, "required_scope"))
        proof_scope = set(_scope(proof.get("scope"), "proof_scope"))
        if requested_scope - proof_scope: reasons.append("authority_scope_insufficient")
    except ValueError as exc:
        reasons.append(str(exc))
    if proof.get("subject") != expected_subject: reasons.append("authority_subject_mismatch")
    if proof.get("action") != expected_action: reasons.append("authority_action_mismatch")
    if proof.get("object_id") != expected_object_id: reasons.append("authority_object_mismatch")
    if proof.get("issuer") not in trusted_issuers: reasons.append("authority_issuer_untrusted")
    if proof.get("revocation_id") in revoked_ids: reasons.append("authority_revoked")
    provenance = proof.get("provenance")
    if not isinstance(provenance, dict) or not isinstance(provenance.get("source"), str) or not re.fullmatch(
            r"[0-9a-f]{64}", str(provenance.get("evidence_sha256", ""))):
        reasons.append("authority_provenance_invalid")
    chain = proof.get("delegation_chain")
    if not isinstance(chain, list) or any(not isinstance(item, dict) for item in chain) or (chain and chain[-1].get("to") != proof.get("subject")):
        reasons.append("authority_delegation_chain_invalid")
    return {"schema": "SUPER1200_AUTHORIZATION_PROOF_VERIFICATION/1",
        "decision": "ALLOW" if not reasons else "DENY", "reasons": sorted(set(reasons)),
        "proof_sha256": _sha(proof), "checked_at_utc": _stamp(now),
        "operation": {"subject": expected_subject, "action": expected_action, "object_id": expected_object_id,
            "required_scope": sorted(set(required_scope))}}


def issue_capability_lease(
    *, subject: str, actions: list[str], resources: list[str], not_before_utc: str,
    not_after_utc: str, nonce: str, issuer: str, lease_id: str, signing_key: bytes,
) -> dict[str, Any]:
    """Issue a one-consumption, time-bounded lease with explicit nonce and revocation identity."""
    key = _key(signing_key)
    start, end = _utc(not_before_utc, "not_before_utc"), _utc(not_after_utc, "not_after_utc")
    if end <= start: raise ValueError("lease_interval_invalid")
    lease = {"schema": "SUPER1200_CAPABILITY_LEASE/1", "lease_id": _nonempty(lease_id, "lease_id"),
        "subject": _nonempty(subject, "subject"), "actions": _scope(actions, "actions"),
        "resources": _scope(resources, "resources"), "not_before_utc": _stamp(start),
        "not_after_utc": _stamp(end), "nonce": _nonempty(nonce, "nonce"),
        "issuer": _nonempty(issuer, "issuer"), "status": "ISSUED"}
    lease["signature_hmac_sha256"] = _signature(lease, key)
    lease["lease_sha256"] = _sha(lease)
    return lease


def consume_capability_lease(
    lease: Any, *, signing_key: bytes, subject: str, action: str, resource: str,
    trusted_now_utc: str, revoked_lease_ids: list[str], consumption_ledger: dict[str, Any],
) -> dict[str, Any]:
    """Consume a valid lease exactly once; denied attempts never mutate the supplied ledger."""
    reasons = []
    try:
        key = _key(signing_key); now = _utc(trusted_now_utc, "trusted_now_utc")
    except ValueError as exc:
        return {"decision": "DENY", "reasons": [str(exc)], "ledger": dict(consumption_ledger)}
    if not isinstance(lease, dict) or lease.get("schema") != "SUPER1200_CAPABILITY_LEASE/1":
        return {"decision": "DENY", "reasons": ["lease_schema_invalid"], "ledger": dict(consumption_ledger)}
    if not _verify_signature(lease, key): reasons.append("lease_signature_invalid")
    unsigned = dict(lease); recorded = unsigned.pop("lease_sha256", None)
    if recorded != _sha(unsigned): reasons.append("lease_hash_invalid")
    if lease.get("status") != "ISSUED": reasons.append("lease_not_issued")
    if lease.get("lease_id") in revoked_lease_ids: reasons.append("lease_revoked")
    if lease.get("subject") != subject: reasons.append("lease_subject_mismatch")
    if action not in lease.get("actions", []): reasons.append("lease_action_not_granted")
    if resource not in lease.get("resources", []): reasons.append("lease_resource_not_granted")
    try:
        start, end = _utc(lease.get("not_before_utc"), "not_before_utc"), _utc(lease.get("not_after_utc"), "not_after_utc")
        if end <= start: reasons.append("lease_interval_invalid")
        elif now < start: reasons.append("lease_not_yet_valid")
        elif now >= end: reasons.append("lease_expired")
    except ValueError as exc: reasons.append(str(exc))
    ledger = dict(consumption_ledger) if isinstance(consumption_ledger, dict) else {}
    if lease.get("lease_id") in ledger or lease.get("nonce") in ledger.values():
        reasons.append("lease_already_consumed_or_nonce_replayed")
    if reasons:
        return {"schema": "SUPER1200_CAPABILITY_LEASE_CONSUMPTION/1", "decision": "DENY",
            "reasons": sorted(set(reasons)), "ledger": dict(consumption_ledger)}
    ledger[lease["lease_id"]] = lease["nonce"]
    receipt = {"schema": "SUPER1200_CAPABILITY_LEASE_CONSUMED/1", "lease_id": lease["lease_id"],
        "nonce": lease["nonce"], "subject": subject, "action": action, "resource": resource,
        "consumed_at_utc": _stamp(now), "lease_sha256": _sha(lease), "status": "CONSUMED"}
    receipt["receipt_sha256"] = _sha(receipt)
    return {"schema": "SUPER1200_CAPABILITY_LEASE_CONSUMPTION/1", "decision": "ALLOW",
        "reasons": [], "ledger": ledger, "receipt": receipt}


def derive_least_privilege(mission_dag: Any, target_task_ids: list[str]) -> dict[str, Any]:
    """Derive only the action/resource union required by target tasks and their dependency closure."""
    if not isinstance(mission_dag, dict) or not isinstance(mission_dag.get("tasks"), list):
        raise ValueError("mission_dag_tasks_required")
    if not isinstance(target_task_ids, list) or not target_task_ids or any(not isinstance(x, str) or not x for x in target_task_ids):
        raise ValueError("target_task_ids_required")
    tasks = {}
    for task in mission_dag["tasks"]:
        if not isinstance(task, dict) or not isinstance(task.get("task_id"), str) or not task["task_id"]:
            raise ValueError("mission_task_identity_invalid")
        tid = task["task_id"]
        if tid in tasks: raise ValueError("mission_task_id_duplicate")
        deps = task.get("depends_on", [])
        if not isinstance(deps, list) or any(not isinstance(x, str) or not x for x in deps):
            raise ValueError("mission_dependencies_invalid")
        tasks[tid] = task
    if set(target_task_ids) - set(tasks): raise ValueError("mission_target_unknown")
    closure = set(); visiting = set()
    def visit(tid):
        if tid in visiting: raise ValueError("mission_dependency_cycle")
        if tid in closure: return
        if tid not in tasks: raise ValueError("mission_dependency_unknown")
        visiting.add(tid)
        for dep in tasks[tid].get("depends_on", []): visit(dep)
        visiting.remove(tid); closure.add(tid)
    for tid in target_task_ids: visit(tid)
    actions, resources = set(), set()
    for tid in closure:
        task = tasks[tid]
        actions.update(_scope(task.get("required_actions", []), f"{tid}_required_actions"))
        resources.update(_scope(task.get("required_resources", []), f"{tid}_required_resources"))
    result = {"schema": "SUPER1200_LEAST_PRIVILEGE_PLAN/1", "status": "PASS",
        "target_task_ids": sorted(set(target_task_ids)), "dependency_closure": sorted(closure),
        "minimum_actions": sorted(actions), "minimum_resources": sorted(resources),
        "mission_dag_sha256": _sha(mission_dag)}
    result["plan_sha256"] = _sha(result)
    return result


def evaluate_time_bound_authority(
    authority: Any, *, trusted_time: dict[str, Any], trusted_sources: list[str],
    max_time_age_seconds: int = 30, max_uncertainty_seconds: int = 2,
) -> dict[str, Any]:
    """Validate an authority interval against an explicit, fresh, allowlisted trusted-time observation."""
    reasons = []
    if not isinstance(authority, dict) or authority.get("schema") != "SUPER1200_TIME_BOUND_AUTHORITY/1":
        return {"decision": "DENY", "reasons": ["time_authority_schema_invalid"]}
    if not isinstance(trusted_time, dict) or trusted_time.get("schema") != "SUPER1200_TRUSTED_TIME/1":
        return {"decision": "DENY", "reasons": ["trusted_time_schema_invalid"]}
    unsigned_authority = dict(authority)
    recorded_authority_hash = unsigned_authority.pop("authority_sha256", None)
    if recorded_authority_hash != _sha(unsigned_authority):
        reasons.append("time_authority_hash_invalid")
    try:
        now = _utc(trusted_time.get("timestamp_utc"), "trusted_timestamp_utc")
        observed = _utc(trusted_time.get("observed_at_utc"), "trusted_observed_at_utc")
        start = _utc(authority.get("not_before_utc"), "not_before_utc")
        end = _utc(authority.get("not_after_utc"), "not_after_utc")
        age = abs((observed - now).total_seconds())
        uncertainty = trusted_time.get("uncertainty_seconds")
        if not isinstance(uncertainty, (int, float)) or isinstance(uncertainty, bool) or uncertainty < 0:
            reasons.append("trusted_time_uncertainty_invalid")
        elif uncertainty > max_uncertainty_seconds: reasons.append("trusted_time_uncertainty_excessive")
        if age > max_time_age_seconds: reasons.append("trusted_time_observation_stale")
        if trusted_time.get("source") not in trusted_sources: reasons.append("trusted_time_source_untrusted")
        if end <= start: reasons.append("time_authority_interval_invalid")
        elif now < start: reasons.append("time_authority_not_yet_valid")
        elif now >= end: reasons.append("time_authority_expired")
    except ValueError as exc:
        reasons.append(str(exc))
        now = None
    return {"schema": "SUPER1200_TIME_BOUND_AUTHORITY_DECISION/1",
        "decision": "ALLOW" if not reasons else "DENY", "reasons": sorted(set(reasons)),
        "authority_id": authority.get("authority_id"), "trusted_time_source": trusted_time.get("source"),
        "trusted_timestamp_utc": _stamp(now) if now else None,
        "authority_sha256": recorded_authority_hash}


def make_time_bound_authority(*, authority_id: str, subject: str, actions: list[str],
                              resources: list[str], not_before_utc: str, not_after_utc: str,
                              issuer: str, provenance_sha256: str) -> dict[str, Any]:
    start, end = _utc(not_before_utc, "not_before_utc"), _utc(not_after_utc, "not_after_utc")
    if end <= start: raise ValueError("time_authority_interval_invalid")
    if not re.fullmatch(r"[0-9a-f]{64}", provenance_sha256):
        raise ValueError("time_authority_provenance_sha256_invalid")
    authority = {"schema": "SUPER1200_TIME_BOUND_AUTHORITY/1", "authority_id": _nonempty(authority_id, "authority_id"),
        "subject": _nonempty(subject, "subject"), "actions": _scope(actions, "actions"),
        "resources": _scope(resources, "resources"), "not_before_utc": _stamp(start),
        "not_after_utc": _stamp(end), "issuer": _nonempty(issuer, "issuer"),
        "provenance_sha256": provenance_sha256}
    authority["authority_sha256"] = _sha(authority)
    return authority
