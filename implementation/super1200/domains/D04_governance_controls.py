"""D04 governance controls for capability IDs 113-116.

Pure policy primitives only: no certification authority, no transitive
certification, and no implied cryptographic trust. All external signatures,
identity-independence proofs and revocation checks must be supplied by trusted
verifier callbacks. Durable production operation requires persisted storage;
these registries are deterministic, thread-safe in-process reference engines.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(field + "_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_timezone_required")
    return parsed.astimezone(timezone.utc)


def _text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


class SingleUseAuthorizationRegistry:
    """Atomic authorization-proof consumption with nonce replay rejection and chained receipts."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._proof_ids: set[str] = set()
        self._nonces: set[str] = set()
        self._operation_ids: set[str] = set()
        self._receipts: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    @property
    def receipts(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(json.loads(canonical_bytes(x)) for x in self._receipts)

    def consume(
        self,
        proof: Any,
        *,
        request: dict[str, Any],
        operation_id: str,
        now_utc: str,
        proof_verifier: Callable[[dict[str, Any], dict[str, Any], str], Any],
    ) -> dict[str, Any]:
        """Consume after trusted proof verification; checks replay again inside the atomic lock."""
        now = _utc(now_utc, "now_utc")
        if not isinstance(proof, dict):
            raise ValueError("single_use_proof_must_be_object")
        proof_id, nonce = proof.get("proof_id"), proof.get("nonce")
        if not _text(proof_id) or not _text(nonce) or not _text(operation_id):
            raise ValueError("single_use_identity_required")
        if not isinstance(request, dict):
            raise ValueError("single_use_request_required")
        if not callable(proof_verifier):
            raise ValueError("trusted_single_use_proof_verifier_required")
        try:
            verification = proof_verifier(proof, request, now.isoformat().replace("+00:00", "Z"))
        except Exception as exc:
            raise ValueError("single_use_proof_verifier_error:" + type(exc).__name__) from exc
        if verification is not True:
            raise ValueError("single_use_proof_not_authorized")
        if proof.get("nonce_consumption_status") == "CONSUMED":
            raise ValueError("single_use_proof_already_consumed")
        proof_unsigned = {k: v for k, v in proof.items() if k != "proof_integrity_sha256"}
        proof_integrity = _digest(proof_unsigned)
        if proof.get("proof_integrity_sha256") != proof_integrity:
            raise ValueError("single_use_proof_integrity_mismatch")
        with self._lock:
            if proof_id in self._proof_ids:
                raise ValueError("single_use_proof_replay")
            if nonce in self._nonces:
                raise ValueError("single_use_nonce_replay")
            if operation_id in self._operation_ids:
                raise ValueError("single_use_operation_replay")
            unsigned = {
                "schema": "SUPER1200_SINGLE_USE_RECEIPT/1",
                "sequence": len(self._receipts) + 1,
                "proof_id": proof_id,
                "nonce": nonce,
                "operation_id": operation_id,
                "request_sha256": _digest(request),
                "proof_integrity_sha256": proof_integrity,
                "consumed_at_utc": now.isoformat().replace("+00:00", "Z"),
                "previous_receipt_sha256": self._receipts[-1]["receipt_sha256"] if self._receipts else self.GENESIS,
            }
            receipt = dict(unsigned)
            receipt["receipt_sha256"] = _digest(unsigned)
            self._proof_ids.add(proof_id)
            self._nonces.add(nonce)
            self._operation_ids.add(operation_id)
            self._receipts.append(receipt)
            return json.loads(canonical_bytes(receipt))

    @classmethod
    def verify_receipts(cls, receipts: Any) -> bool:
        if not isinstance(receipts, (list, tuple)):
            return False
        proof_ids, nonces, operations = set(), set(), set()
        previous = cls.GENESIS
        for sequence, receipt in enumerate(receipts, start=1):
            if not isinstance(receipt, dict) or receipt.get("schema") != "SUPER1200_SINGLE_USE_RECEIPT/1":
                return False
            if receipt.get("sequence") != sequence or receipt.get("previous_receipt_sha256") != previous:
                return False
            proof_id, nonce, operation_id = receipt.get("proof_id"), receipt.get("nonce"), receipt.get("operation_id")
            if not all(_text(x) for x in (proof_id, nonce, operation_id)):
                return False
            if proof_id in proof_ids or nonce in nonces or operation_id in operations:
                return False
            try:
                for field in ("request_sha256", "proof_integrity_sha256", "receipt_sha256"):
                    value = receipt.get(field)
                    if not isinstance(value, str) or len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
                        return False
            except Exception:
                return False
            unsigned = dict(receipt)
            recorded = unsigned.pop("receipt_sha256", None)
            if _digest(unsigned) != recorded:
                return False
            proof_ids.add(proof_id); nonces.add(nonce); operations.add(operation_id); previous = recorded
        return True


class RevocationRegistry:
    """Append-only revocation ledger with issuer tracking and transitive dependent propagation."""

    GENESIS = "0" * 64

    def __init__(self) -> None:
        self._tracked: dict[tuple[str, str], dict[str, Any]] = {}
        self._dependencies: dict[tuple[str, str], set[tuple[str, str]]] = {}
        self._revocations: dict[tuple[str, str], dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        with self._lock:
            return tuple(json.loads(canonical_bytes(x)) for x in self._events)

    def track(self, *, subject_id: str, issuer: str, registry_checkpoint: str) -> dict[str, Any]:
        if not all(_text(x) for x in (subject_id, issuer, registry_checkpoint)):
            raise ValueError("revocation_tracking_identity_required")
        key = (issuer, subject_id)
        with self._lock:
            record = {"issuer": issuer, "subject_id": subject_id, "registry_checkpoint": registry_checkpoint}
            old = self._tracked.get(key)
            if old is not None and old != record:
                raise ValueError("revocation_tracking_identity_immutable")
            self._tracked[key] = record
            self._dependencies.setdefault(key, set())
            return dict(record)

    def add_dependent(self, *, issuer: str, source_subject_id: str, dependent_subject_id: str) -> None:
        source, target = (issuer, source_subject_id), (issuer, dependent_subject_id)
        with self._lock:
            if source not in self._tracked or target not in self._tracked:
                raise ValueError("revocation_dependency_subject_untracked")
            if source == target or self._reachable(target, source):
                raise ValueError("revocation_dependency_cycle")
            self._dependencies[source].add(target)

    def _reachable(self, start: tuple[str, str], target: tuple[str, str]) -> bool:
        pending, seen = [start], set()
        while pending:
            current = pending.pop()
            if current == target:
                return True
            if current in seen:
                continue
            seen.add(current)
            pending.extend(sorted(self._dependencies.get(current, set())))
        return False

    def _closure(self, source: tuple[str, str]) -> tuple[tuple[str, str], ...]:
        pending, seen = [source], set()
        while pending:
            current = pending.pop()
            if current in seen:
                continue
            seen.add(current)
            pending.extend(sorted(self._dependencies.get(current, set())))
        return tuple(sorted(seen))

    def revoke(
        self,
        *,
        subject_id: str,
        issuer: str,
        revocation_id: str,
        actor: str,
        reason: str,
        effective_at_utc: str,
    ) -> dict[str, Any]:
        if not all(_text(x) for x in (subject_id, issuer, revocation_id, actor, reason)):
            raise ValueError("revocation_identity_reason_required")
        effective = _utc(effective_at_utc, "effective_at_utc")
        source = (issuer, subject_id)
        with self._lock:
            if source not in self._tracked:
                raise ValueError("revocation_subject_untracked")
            old = self._revocations.get(source)
            candidate = {"issuer": issuer, "subject_id": subject_id, "revocation_id": revocation_id,
                         "actor": actor, "reason": reason,
                         "effective_at_utc": effective.isoformat().replace("+00:00", "Z")}
            if old is not None:
                if old != candidate:
                    raise ValueError("revocation_record_immutable")
                return json.loads(canonical_bytes(old))
            affected = self._closure(source)
            candidate["affected_subjects"] = [
                {"issuer": iss, "subject_id": sid} for iss, sid in affected
            ]
            candidate["propagation_count"] = len(affected)
            candidate["revocation_sha256"] = _digest(candidate)
            self._revocations[source] = candidate
            unsigned = {
                "schema": "SUPER1200_REVOCATION_EVENT/1",
                "sequence": len(self._events) + 1,
                "revocation_id": revocation_id,
                "issuer": issuer,
                "subject_id": subject_id,
                "reason_sha256": hashlib.sha256(reason.encode("utf-8")).hexdigest(),
                "effective_at_utc": candidate["effective_at_utc"],
                "propagation_count": len(affected),
                "previous_event_sha256": self._events[-1]["event_sha256"] if self._events else self.GENESIS,
            }
            event = dict(unsigned); event["event_sha256"] = _digest(unsigned)
            self._events.append(event)
            return json.loads(canonical_bytes(candidate))

    def check(self, *, subject_id: str, issuer: str, now_utc: str) -> dict[str, Any]:
        now = _utc(now_utc, "now_utc")
        key = (issuer, subject_id)
        with self._lock:
            if key not in self._tracked:
                return {"decision": "DENY", "status": "UNKNOWN", "reason": "revocation_subject_untracked"}
            affected_by = []
            for origin, record in self._revocations.items():
                if any(item["issuer"] == issuer and item["subject_id"] == subject_id
                       for item in record["affected_subjects"]):
                    if now >= _utc(record["effective_at_utc"], "effective_at_utc"):
                        affected_by.append(record)
            if affected_by:
                return {"decision": "DENY", "status": "REVOKED",
                        "revocation_ids": sorted(x["revocation_id"] for x in affected_by),
                        "reasons": sorted(set(x["reason"] for x in affected_by))}
            return {"decision": "ALLOW", "status": "NOT_REVOKED",
                    "registry_checkpoint": self._tracked[key]["registry_checkpoint"]}


def validate_separation_of_duties(policy: Any, assignments: Any) -> dict[str, Any]:
    """Require distinct role identities, control domains, credentials, paths and permissions."""
    if not isinstance(policy, dict) or policy.get("schema") != "SUPER1200_SEPARATION_OF_DUTIES/1":
        raise ValueError("separation_policy_schema_invalid")
    roles = policy.get("required_roles")
    if not isinstance(roles, list) or not roles or any(not _text(x) for x in roles) or len(set(roles)) != len(roles):
        raise ValueError("separation_required_roles_invalid")
    if not isinstance(assignments, dict):
        raise ValueError("separation_assignments_required")
    allowed = policy.get("allowed_permissions_by_role")
    if not isinstance(allowed, dict):
        raise ValueError("separation_permission_policy_required")
    reasons = []
    identities, domains, credentials, paths = {}, {}, {}, {}
    permissions: dict[str, set[str]] = {}
    critical_permissions: dict[str, set[str]] = {}
    for role in roles:
        assignment = assignments.get(role)
        if not isinstance(assignment, dict):
            reasons.append("role_assignment_missing:" + role); continue
        for field, bucket in (("actor_id", identities), ("control_domain", domains),
                              ("credential_id", credentials), ("execution_path", paths)):
            value = assignment.get(field)
            if not _text(value):
                reasons.append("role_" + field + "_missing:" + role); continue
            bucket.setdefault(value, []).append(role)
        given = assignment.get("permissions")
        critical = assignment.get("critical_permissions", [])
        if not isinstance(given, list) or not given or any(not _text(x) for x in given):
            reasons.append("role_permissions_invalid:" + role); given = []
        if not isinstance(critical, list) or any(not _text(x) for x in critical):
            reasons.append("role_critical_permissions_invalid:" + role); critical = []
        permitted = allowed.get(role)
        if not isinstance(permitted, list) or any(not _text(x) for x in permitted):
            reasons.append("policy_permissions_invalid:" + role); permitted = []
        excess = sorted(set(given) - set(permitted))
        if excess:
            reasons.append("role_excess_permissions:" + role + ":" + ",".join(excess))
        permissions[role] = set(given)
        critical_permissions[role] = set(critical)
        if not set(critical).issubset(set(given)):
            reasons.append("critical_permissions_not_granted:" + role)
    for label, bucket in (("actor_id", identities), ("control_domain", domains),
                          ("credential_id", credentials), ("execution_path", paths)):
        for value, assigned_roles in bucket.items():
            if len(assigned_roles) > 1:
                reasons.append("role_" + label + "_collision:" + value)
    for index, role in enumerate(roles):
        for other in roles[index+1:]:
            overlap = sorted(permissions.get(role, set()) & permissions.get(other, set()))
            if overlap:
                reasons.append("role_permission_overlap:" + role + ":" + other + ":" + ",".join(overlap))
            critical_overlap = sorted(critical_permissions.get(role, set()) & critical_permissions.get(other, set()))
            if critical_overlap:
                reasons.append("role_critical_permission_overlap:" + role + ":" + other + ":" + ",".join(critical_overlap))
    extra_roles = sorted(set(assignments) - set(roles))
    if extra_roles:
        reasons.append("unexpected_role_assignments:" + ",".join(extra_roles))
    return {
        "schema": "SUPER1200_SEPARATION_OF_DUTIES_DECISION/1",
        "decision": "ALLOW" if not reasons else "DENY",
        "reasons": reasons,
        "required_roles": roles,
        "role_count": len(roles),
        "distinct_actor_count": len(identities),
        "certification_granted": False,
    }


def evaluate_two_man_rule(
    policy: Any,
    *,
    risk: str,
    request: dict[str, Any],
    approvals: Any,
    now_utc: str,
    signature_verifier: Callable[[dict[str, Any], bytes], Any],
    independence_verifier: Callable[[dict[str, Any], dict[str, Any]], Any],
) -> dict[str, Any]:
    """Apply a risk-specific approval threshold with independent, signed, fresh approvals."""
    if not isinstance(policy, dict) or policy.get("schema") != "SUPER1200_TWO_MAN_RULE/1":
        raise ValueError("two_man_policy_schema_invalid")
    thresholds = policy.get("risk_thresholds")
    default_threshold = policy.get("default_threshold", 1)
    if not isinstance(thresholds, dict) or not isinstance(default_threshold, int) or isinstance(default_threshold, bool) or default_threshold < 1:
        raise ValueError("two_man_threshold_policy_invalid")
    if not _text(risk) or not isinstance(request, dict):
        raise ValueError("two_man_request_invalid")
    threshold = thresholds.get(risk, default_threshold)
    if not isinstance(threshold, int) or isinstance(threshold, bool) or threshold < 1:
        raise ValueError("two_man_risk_threshold_invalid")
    max_age = policy.get("max_approval_age_seconds", 300)
    if not isinstance(max_age, int) or isinstance(max_age, bool) or max_age < 1:
        raise ValueError("two_man_approval_freshness_invalid")
    now = _utc(now_utc, "now_utc")
    if not isinstance(approvals, list):
        raise ValueError("two_man_approvals_required")
    reasons = []
    valid: list[dict[str, Any]] = []
    seen_actor, seen_credential, seen_domain = set(), set(), set()
    for index, approval in enumerate(approvals):
        if not isinstance(approval, dict):
            reasons.append("approval_not_object:" + str(index)); continue
        actor, credential, domain = approval.get("actor_id"), approval.get("credential_id"), approval.get("control_domain")
        if not all(_text(x) for x in (actor, credential, domain)):
            reasons.append("approval_identity_missing:" + str(index)); continue
        if actor in seen_actor or credential in seen_credential or domain in seen_domain:
            reasons.append("approval_actor_not_independent:" + str(index)); continue
        if approval.get("request_sha256") != _digest(request) or approval.get("risk") != risk:
            reasons.append("approval_request_or_risk_mismatch:" + str(index)); continue
        try:
            issued = _utc(approval.get("issued_at_utc"), "approval_issued_at_utc")
            expires = _utc(approval.get("expires_at_utc"), "approval_expires_at_utc")
            if expires <= issued or issued > now or now >= expires or (now - issued).total_seconds() > max_age:
                reasons.append("approval_expired_or_stale:" + str(index)); continue
        except ValueError as exc:
            reasons.append(str(exc) + ":" + str(index)); continue
        signature = approval.get("signature")
        if not isinstance(signature, dict) or not _text(signature.get("algorithm")) or not _text(signature.get("value")):
            reasons.append("approval_signature_missing:" + str(index)); continue
        unsigned = {k: v for k, v in approval.items() if k not in {"signature", "approval_sha256"}}
        if approval.get("approval_sha256") != _digest(unsigned):
            reasons.append("approval_integrity_mismatch:" + str(index)); continue
        if not callable(signature_verifier):
            reasons.append("trusted_approval_signature_verifier_required"); continue
        try:
            if signature_verifier(approval, canonical_bytes(unsigned)) is not True:
                reasons.append("approval_signature_invalid:" + str(index)); continue
        except Exception:
            reasons.append("approval_signature_verifier_error:" + str(index)); continue
        if not callable(independence_verifier):
            reasons.append("trusted_approval_independence_verifier_required"); continue
        try:
            if independence_verifier(approval, request) is not True:
                reasons.append("approval_independence_verification_failed:" + str(index)); continue
        except Exception:
            reasons.append("approval_independence_verifier_error:" + str(index)); continue
        seen_actor.add(actor); seen_credential.add(credential); seen_domain.add(domain); valid.append(approval)
    if len(valid) < threshold:
        reasons.append("two_man_threshold_not_met")
    decision = "ALLOW" if not reasons and len(valid) >= threshold else "DENY"
    return {
        "schema": "SUPER1200_TWO_MAN_DECISION/1",
        "decision": decision,
        "risk": risk,
        "required_threshold": threshold,
        "valid_approval_count": len(valid),
        "approval_ids": sorted(x.get("approval_id", "") for x in valid),
        "request_sha256": _digest(request),
        "reasons": reasons,
        "two_man_rule_applied": risk in thresholds and threshold > 1,
        "certification_granted": False,
    }
