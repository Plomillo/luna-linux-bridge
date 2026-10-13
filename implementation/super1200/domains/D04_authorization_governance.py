"""D04 authorization and lease primitives for capability IDs 109-112.

External signatures and trusted-time attestations are verified only through
injected trusted verifiers. This module never grants certification authority.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable


_DECISIONS = {"ALLOW", "DENY"}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _time(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(field + "_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_timezone_required")
    return parsed.astimezone(timezone.utc)


def _nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _scope_equal(left: Any, right: Any) -> bool:
    return isinstance(left, dict) and isinstance(right, dict) and canonical_bytes(left) == canonical_bytes(right)


def validate_authorization_proof(
    proof: Any,
    *,
    request: dict[str, Any],
    now_utc: str,
    signature_verifier: Callable[[dict[str, Any], bytes], Any],
    revocation_checker: Callable[[str, str], Any],
    delegation_verifier: Callable[[dict[str, Any]], Any] | None = None,
) -> dict[str, Any]:
    """Return an ALLOW/DENY decision only for an exact signed, unrevoked proof."""
    reasons: list[str] = []
    if not isinstance(request, dict):
        raise ValueError("authorization_request_must_be_object")
    now = _time(now_utc, "now_utc")
    if not isinstance(proof, dict) or proof.get("schema") != "SUPER1200_AUTHORIZATION_PROOF/1":
        return {"schema": "SUPER1200_AUTHORIZATION_DECISION/1", "decision": "DENY",
                "reasons": ["authorization_proof_schema_invalid"]}
    required = ("proof_id", "subject", "action", "object", "scope", "issuer",
                "issued_at_utc", "not_before_utc", "not_after_utc", "revocation_id", "provenance")
    if any(k not in proof for k in required):
        reasons.append("authorization_proof_field_missing")
    for field in ("proof_id", "subject", "action", "object", "issuer", "revocation_id"):
        if not _nonblank(proof.get(field)):
            reasons.append("authorization_proof_identity_invalid:" + field)
    if not isinstance(proof.get("scope"), dict) or not proof.get("scope"):
        reasons.append("authorization_scope_invalid")
    provenance = proof.get("provenance")
    if not isinstance(provenance, dict):
        reasons.append("authorization_provenance_missing")
    else:
        for field in ("operation_id", "source_uri", "input_sha256"):
            if not _nonblank(provenance.get(field)):
                reasons.append("authorization_provenance_invalid:" + field)
        input_hash = provenance.get("input_sha256")
        if not isinstance(input_hash, str) or len(input_hash) != 64 or any(ch not in "0123456789abcdef" for ch in input_hash):
            reasons.append("authorization_provenance_hash_invalid")

    expected_fields = ("subject", "action", "object")
    for field in expected_fields:
        if proof.get(field) != request.get(field):
            reasons.append("authorization_" + field + "_mismatch")
    if not _scope_equal(proof.get("scope"), request.get("scope")):
        reasons.append("authorization_scope_mismatch")
    try:
        issued = _time(proof.get("issued_at_utc"), "issued_at_utc")
        not_before = _time(proof.get("not_before_utc"), "not_before_utc")
        not_after = _time(proof.get("not_after_utc"), "not_after_utc")
        if not_before >= not_after:
            reasons.append("authorization_interval_invalid")
        if issued > now:
            reasons.append("authorization_issued_in_future")
        if now < not_before:
            reasons.append("authorization_not_yet_valid")
        if now >= not_after:
            reasons.append("authorization_expired")
        if issued > not_after:
            reasons.append("authorization_issue_after_expiry")
    except ValueError as exc:
        reasons.append(str(exc))

    signature = proof.get("signature")
    if not isinstance(signature, dict) or not _nonblank(signature.get("algorithm")) or not _nonblank(signature.get("value")):
        reasons.append("authorization_signature_missing")
    signed_payload = {k: v for k, v in proof.items() if k not in {"signature", "proof_sha256"}}
    if callable(signature_verifier) and isinstance(signature, dict) and not reasons:
        try:
            if signature_verifier(proof, canonical_bytes(signed_payload)) is not True:
                reasons.append("authorization_signature_verification_failed")
        except Exception:
            reasons.append("authorization_signature_verifier_error")
    elif not callable(signature_verifier):
        reasons.append("trusted_authorization_signature_verifier_required")
    if proof.get("delegation") is not None:
        delegation = proof.get("delegation")
        if not isinstance(delegation, dict) or not delegation:
            reasons.append("delegation_record_invalid")
        elif delegation.get("delegated") is True:
            if not callable(delegation_verifier):
                reasons.append("trusted_delegation_verifier_required")
            else:
                try:
                    if delegation_verifier(proof) is not True:
                        reasons.append("delegation_verification_failed")
                except Exception:
                    reasons.append("delegation_verifier_error")
    if not callable(revocation_checker):
        reasons.append("trusted_revocation_checker_required")
    elif _nonblank(proof.get("proof_id")) and _nonblank(proof.get("issuer")):
        try:
            revoked = revocation_checker(proof["proof_id"], proof["issuer"])
            if revoked is True:
                reasons.append("authorization_revoked")
            elif revoked is not False:
                reasons.append("revocation_status_unknown")
        except Exception:
            reasons.append("revocation_checker_error")
    unsigned_proof = {k: v for k, v in proof.items() if k != "proof_sha256"}
    calculated_hash = _digest(unsigned_proof)
    if proof.get("proof_sha256") != calculated_hash:
        reasons.append("authorization_proof_hash_mismatch")
    return {
        "schema": "SUPER1200_AUTHORIZATION_DECISION/1",
        "decision": "ALLOW" if not reasons else "DENY",
        "reasons": reasons,
        "proof_id": proof.get("proof_id"),
        "subject": proof.get("subject"),
        "action": proof.get("action"),
        "object": proof.get("object"),
        "scope": proof.get("scope"),
        "proof_sha256": calculated_hash,
        "revocation_status": "REVOKED" if "authorization_revoked" in reasons else
                             "UNKNOWN" if any(x.startswith("revocation_") or x == "revocation_status_unknown" for x in reasons) else "NOT_REVOKED",
    }


class CapabilityLeaseRegistry:
    """Thread-safe in-process lease ledger; durable deployment must persist events externally."""
    def __init__(self) -> None:
        self._events: list[dict[str, Any]] = []
        self._leases: dict[str, dict[str, Any]] = {}
        self._nonces: set[str] = set()
        self._operations: set[str] = set()
        self._lock = threading.RLock()

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(json.loads(canonical_bytes(event)) for event in self._events)

    def grant(
        self, *, lease_id: str, subject: str, capability: str,
        actions: list[str] | tuple[str, ...], resources: list[str] | tuple[str, ...],
        nonce: str, issuer: str, issued_at_utc: str, not_before_utc: str,
        not_after_utc: str, max_uses: int | None = None,
        revocation_id: str | None = None,
    ) -> dict[str, Any]:
        with self._lock:
            for field, value in (("lease_id", lease_id), ("subject", subject), ("capability", capability),
                                 ("nonce", nonce), ("issuer", issuer)):
                if not _nonblank(value):
                    raise ValueError(field + "_required")
            if lease_id in self._leases:
                raise ValueError("lease_id_immutable")
            if nonce in self._nonces:
                raise ValueError("lease_nonce_duplicate")
            if not isinstance(actions, (list, tuple)) or not actions or any(not _nonblank(x) for x in actions):
                raise ValueError("lease_actions_required")
            if not isinstance(resources, (list, tuple)) or not resources or any(not _nonblank(x) for x in resources):
                raise ValueError("lease_resources_required")
            if max_uses is not None and (not isinstance(max_uses, int) or isinstance(max_uses, bool) or max_uses < 1):
                raise ValueError("lease_max_uses_invalid")
            issued, start, end = (_time(issued_at_utc, "issued_at_utc"),
                                  _time(not_before_utc, "not_before_utc"),
                                  _time(not_after_utc, "not_after_utc"))
            if start >= end or issued > end:
                raise ValueError("lease_interval_invalid")
            lease = {
                "schema": "SUPER1200_CAPABILITY_LEASE/1", "lease_id": lease_id,
                "subject": subject, "capability": capability, "actions": sorted(set(actions)),
                "resources": sorted(set(resources)), "nonce": nonce, "issuer": issuer,
                "issued_at_utc": issued.isoformat().replace("+00:00", "Z"),
                "not_before_utc": start.isoformat().replace("+00:00", "Z"),
                "not_after_utc": end.isoformat().replace("+00:00", "Z"),
                "max_uses": max_uses, "revocation_id": revocation_id or ("revocation:" + lease_id),
            }
            lease["lease_sha256"] = _digest(lease)
            self._leases[lease_id] = {"lease": lease, "consumed_operations": [], "revoked": False}
            self._nonces.add(nonce)
            self._append_event("LEASE_GRANTED", lease_id, {"lease_sha256": lease["lease_sha256"], "nonce": nonce})
            return json.loads(canonical_bytes(lease))

    def _append_event(self, event_type: str, lease_id: str, payload: dict[str, Any]) -> dict[str, Any]:
        unsigned = {
            "schema": "SUPER1200_CAPABILITY_LEASE_EVENT/1",
            "sequence": len(self._events) + 1, "event_type": event_type,
            "lease_id": lease_id, "payload": payload,
            "previous_event_sha256": self._events[-1]["event_sha256"] if self._events else "0" * 64,
        }
        event = dict(unsigned)
        event["event_sha256"] = _digest(unsigned)
        self._events.append(event)
        return event

    def inspect(self, lease_id: str) -> dict[str, Any] | None:
        with self._lock:
            state = self._leases.get(lease_id)
            if state is None:
                return None
            lease = json.loads(canonical_bytes(state["lease"]))
            lease["usage_count"] = len(state["consumed_operations"])
            lease["consumed_operations"] = list(state["consumed_operations"])
            lease["revoked"] = state["revoked"]
            lease["consumption_status"] = "CONSUMED" if state["consumed_operations"] else "UNCONSUMED"
            return lease

    def authorize(self, lease_id: str, *, subject: str, action: str, resource: str, now_utc: str) -> dict[str, Any]:
        with self._lock:
            state = self._leases.get(lease_id)
            if state is None:
                return {"decision": "DENY", "reasons": ["lease_unknown"]}
            lease = state["lease"]
            reasons = []
            now = _time(now_utc, "now_utc")
            if state["revoked"]:
                reasons.append("lease_revoked")
            if subject != lease["subject"]:
                reasons.append("lease_subject_mismatch")
            if action not in lease["actions"]:
                reasons.append("lease_action_out_of_scope")
            if resource not in lease["resources"]:
                reasons.append("lease_resource_out_of_scope")
            if now < _time(lease["not_before_utc"], "not_before_utc"):
                reasons.append("lease_not_yet_valid")
            if now >= _time(lease["not_after_utc"], "not_after_utc"):
                reasons.append("lease_expired")
            if lease["max_uses"] is not None and len(state["consumed_operations"]) >= lease["max_uses"]:
                reasons.append("lease_usage_limit_reached")
            return {"schema": "SUPER1200_CAPABILITY_LEASE_DECISION/1",
                    "decision": "ALLOW" if not reasons else "DENY",
                    "reasons": reasons, "lease_id": lease_id,
                    "lease_sha256": lease["lease_sha256"]}

    def consume(self, lease_id: str, *, subject: str, action: str, resource: str,
                operation_id: str, now_utc: str) -> dict[str, Any]:
        with self._lock:
            if not _nonblank(operation_id):
                raise ValueError("operation_id_required")
            if operation_id in self._operations:
                raise ValueError("lease_operation_replay")
            decision = self.authorize(lease_id, subject=subject, action=action, resource=resource, now_utc=now_utc)
            if decision["decision"] != "ALLOW":
                raise ValueError("lease_consume_denied:" + ",".join(decision["reasons"]))
            self._leases[lease_id]["consumed_operations"].append(operation_id)
            self._operations.add(operation_id)
            self._append_event("LEASE_CONSUMED", lease_id, {
                "operation_id": operation_id, "usage_count": len(self._leases[lease_id]["consumed_operations"])})
            return {"status": "CONSUMED", "lease_id": lease_id,
                    "operation_id": operation_id,
                    "usage_count": len(self._leases[lease_id]["consumed_operations"])}

    def revoke(self, lease_id: str, *, actor: str, reason: str, effective_at_utc: str) -> dict[str, Any]:
        with self._lock:
            if not _nonblank(actor) or not _nonblank(reason):
                raise ValueError("revocation_actor_reason_required")
            _time(effective_at_utc, "effective_at_utc")
            state = self._leases.get(lease_id)
            if state is None:
                raise ValueError("lease_unknown")
            if state["revoked"]:
                raise ValueError("lease_revocation_immutable")
            state["revoked"] = True
            self._append_event("LEASE_REVOKED", lease_id, {
                "actor": actor, "reason": reason,
                "effective_at_utc": _time(effective_at_utc, "effective_at_utc").isoformat().replace("+00:00", "Z")})
            return {"status": "REVOKED", "lease_id": lease_id, "events": len(self._events)}


def derive_least_privilege(
    mission_dag: Any, *, goal_nodes: list[str] | tuple[str, ...]
) -> dict[str, Any]:
    """Derive the minimal action/resource union over goal nodes and their prerequisites."""
    if not isinstance(mission_dag, dict) or not mission_dag:
        raise ValueError("mission_dag_required")
    if not isinstance(goal_nodes, (list, tuple)) or not goal_nodes:
        raise ValueError("goal_nodes_required")
    nodes: dict[str, dict[str, Any]] = {}
    for node_id, spec in mission_dag.items():
        if not _nonblank(node_id) or not isinstance(spec, dict):
            raise ValueError("mission_dag_node_invalid")
        deps = spec.get("depends_on", [])
        actions = spec.get("actions", [])
        resources = spec.get("resources", [])
        if not isinstance(deps, list) or any(not _nonblank(x) for x in deps):
            raise ValueError("mission_dependencies_invalid:" + node_id)
        for field, values in (("actions", actions), ("resources", resources)):
            if not isinstance(values, list) or any(not _nonblank(x) for x in values):
                raise ValueError("mission_" + field + "_invalid:" + node_id)
        nodes[node_id] = {"depends_on": deps, "actions": sorted(set(actions)), "resources": sorted(set(resources))}
    unknown_goals = sorted(set(goal_nodes) - set(nodes))
    if unknown_goals:
        raise ValueError("mission_goal_unknown:" + ",".join(unknown_goals))
    closure: set[str] = set()
    active: set[str] = set()
    def visit(node_id: str) -> None:
        if node_id in active:
            raise ValueError("mission_dependency_cycle:" + node_id)
        if node_id in closure:
            return
        active.add(node_id)
        for dep in nodes[node_id]["depends_on"]:
            if dep not in nodes:
                raise ValueError("mission_dependency_unknown:" + node_id + ":" + dep)
            visit(dep)
        active.remove(node_id)
        closure.add(node_id)
    for goal in goal_nodes:
        visit(goal)
    actions = sorted({action for node_id in closure for action in nodes[node_id]["actions"]})
    resources = sorted({resource for node_id in closure for resource in nodes[node_id]["resources"]})
    result = {
        "schema": "SUPER1200_LEAST_PRIVILEGE_PLAN/1",
        "goal_nodes": sorted(set(goal_nodes)),
        "required_nodes": sorted(closure),
        "actions": actions,
        "resources": resources,
        "excluded_nodes": sorted(set(nodes) - closure),
        "authority": "NONE_REQUIRES_CAPABILITY_LEASE",
    }
    result["plan_sha256"] = _digest(result)
    return result


def validate_time_bound_authority(
    authority: Any,
    *,
    request: dict[str, Any],
    now_utc: str,
    clock_attestation: Any,
    authority_signature_verifier: Callable[[dict[str, Any], bytes], Any],
    clock_signature_verifier: Callable[[dict[str, Any]], Any],
) -> dict[str, Any]:
    """Validate exact scoped authority against cryptographically verified trusted time."""
    reasons: list[str] = []
    now = _time(now_utc, "now_utc")
    if not isinstance(request, dict):
        raise ValueError("authority_request_must_be_object")
    if not isinstance(authority, dict) or authority.get("schema") != "SUPER1200_TIME_BOUND_AUTHORITY/1":
        return {"schema": "SUPER1200_TIME_BOUND_AUTHORITY_DECISION/1", "decision": "DENY",
                "reasons": ["authority_schema_invalid"]}
    if not isinstance(clock_attestation, dict) or clock_attestation.get("schema") != "SUPER1200_TRUSTED_CLOCK_ATTESTATION/1":
        reasons.append("trusted_clock_attestation_invalid")
    else:
        if not _nonblank(clock_attestation.get("source_id")):
            reasons.append("trusted_clock_source_missing")
        if not callable(clock_signature_verifier):
            reasons.append("trusted_clock_verifier_required")
        else:
            try:
                if clock_signature_verifier(clock_attestation) is not True:
                    reasons.append("trusted_clock_signature_invalid")
            except Exception:
                reasons.append("trusted_clock_verifier_error")
    if not reasons and isinstance(clock_attestation, dict):
        try:
            observed = _time(clock_attestation.get("observed_at_utc"), "clock_observed_at_utc")
            expiry = _time(clock_attestation.get("expires_at_utc"), "clock_expires_at_utc")
            max_skew = clock_attestation.get("max_skew_seconds")
            if not isinstance(max_skew, int) or isinstance(max_skew, bool) or max_skew < 0:
                reasons.append("trusted_clock_max_skew_invalid")
            elif abs((now-observed).total_seconds()) > max_skew:
                reasons.append("trusted_clock_skew_exceeded")
            if now < observed or now >= expiry:
                reasons.append("trusted_clock_attestation_not_current")
        except ValueError as exc:
            reasons.append(str(exc))
    if not _nonblank(authority.get("authority_id")) or not _nonblank(authority.get("issuer")):
        reasons.append("authority_identity_invalid")
    for field in ("subject", "action", "object"):
        if authority.get(field) != request.get(field):
            reasons.append("authority_" + field + "_mismatch")
    if not _scope_equal(authority.get("scope"), request.get("scope")):
        reasons.append("authority_scope_mismatch")
    try:
        start = _time(authority.get("not_before_utc"), "authority_not_before_utc")
        end = _time(authority.get("not_after_utc"), "authority_not_after_utc")
        if start >= end:
            reasons.append("authority_interval_invalid")
        if now < start:
            reasons.append("authority_not_yet_valid")
        if now >= end:
            reasons.append("authority_expired")
        if isinstance(clock_attestation, dict) and _nonblank(clock_attestation.get("observed_at_utc")):
            clock_now = _time(clock_attestation["observed_at_utc"], "clock_observed_at_utc")
            if clock_now < start:
                reasons.append("trusted_time_before_authority_start")
            if clock_now >= end:
                reasons.append("trusted_time_after_authority_expiry")
    except ValueError as exc:
        reasons.append(str(exc))
    signature = authority.get("signature")
    if not isinstance(signature, dict) or not _nonblank(signature.get("algorithm")) or not _nonblank(signature.get("value")):
        reasons.append("authority_signature_missing")
    if not callable(authority_signature_verifier):
        reasons.append("trusted_authority_verifier_required")
    elif not reasons:
        payload = {k: v for k, v in authority.items() if k not in {"signature", "authority_sha256"}}
        try:
            if authority_signature_verifier(authority, canonical_bytes(payload)) is not True:
                reasons.append("authority_signature_invalid")
        except Exception:
            reasons.append("authority_signature_verifier_error")
    unsigned = {k: v for k, v in authority.items() if k != "authority_sha256"}
    observed_hash = _digest(unsigned)
    if authority.get("authority_sha256") != observed_hash:
        reasons.append("authority_hash_mismatch")
    return {
        "schema": "SUPER1200_TIME_BOUND_AUTHORITY_DECISION/1",
        "decision": "ALLOW" if not reasons else "DENY",
        "reasons": reasons,
        "authority_id": authority.get("authority_id"),
        "subject": authority.get("subject"),
        "action": authority.get("action"),
        "object": authority.get("object"),
        "scope": authority.get("scope"),
        "trusted_clock_source": clock_attestation.get("source_id") if isinstance(clock_attestation, dict) else None,
        "authority_sha256": observed_hash,
        "certification_granted": False,
    }
