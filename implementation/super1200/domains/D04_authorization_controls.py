"""SUPER1200 D04 authorization controls for capabilities 113-116.

Isolated from previously certified source files to preserve exact source bindings
for earlier D04 scopes. This module has no global certification authority.
"""
from __future__ import annotations

import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Callable


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_utc(value: Any, field: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(field + "_required")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(field + "_invalid_iso8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(field + "_timezone_required")
    return parsed.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return value.isoformat().replace("+00:00", "Z")


def nonblank(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


class SingleUseAuthorizationRegistry:
    """Thread-safe nonce/receipt registry; a nonce can be consumed at most once."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._consumed: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    def consume(self, *, nonce: str, authorization_id: str, subject: str, action: str,
                resource: str, now_utc: str, expires_at_utc: str, proof_sha256: str) -> dict[str, Any]:
        for name, value in (("nonce", nonce), ("authorization_id", authorization_id),
                            ("subject", subject), ("action", action), ("resource", resource)):
            if not nonblank(value):
                raise ValueError(name + "_required")
        if len(proof_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in proof_sha256):
            raise ValueError("authorization_proof_sha256_invalid")
        now, expiry = parse_utc(now_utc, "now_utc"), parse_utc(expires_at_utc, "expires_at_utc")
        if now >= expiry:
            return {"decision": "DENY", "reason": "authorization_expired", "receipt": None}
        with self._lock:
            if nonce in self._consumed:
                return {"decision": "DENY", "reason": "authorization_nonce_replay", "receipt": None}
            receipt = {"schema": "SUPER1200_SINGLE_USE_RECEIPT/1", "nonce": nonce,
                "authorization_id": authorization_id, "subject": subject, "action": action,
                "resource": resource, "consumed_at_utc": stamp(now), "proof_sha256": proof_sha256,
                "sequence": len(self._events) + 1,
                "previous_event_sha256": self._events[-1]["event_sha256"] if self._events else None}
            receipt["event_sha256"] = digest(receipt)
            self._consumed[nonce] = receipt
            self._events.append(receipt)
            return {"decision": "ALLOW", "reason": "consumed_once", "receipt": dict(receipt)}

    def inspect(self, nonce: str) -> dict[str, Any] | None:
        with self._lock:
            record = self._consumed.get(nonce)
            return dict(record) if record else None

    @property
    def events(self) -> list[dict[str, Any]]:
        with self._lock:
            return [dict(event) for event in self._events]


class RevocationRegistry:
    """Append-only hash-chained revocation events with effective-time evaluation."""
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: list[dict[str, Any]] = []
        self._by_id: dict[str, dict[str, Any]] = {}

    def revoke(self, *, revocation_id: str, target_id: str, issuer: str, reason: str,
               effective_at_utc: str, provenance_sha256: str) -> dict[str, Any]:
        for name, value in (("revocation_id", revocation_id), ("target_id", target_id),
                            ("issuer", issuer), ("reason", reason)):
            if not nonblank(value):
                raise ValueError(name + "_required")
        if len(provenance_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in provenance_sha256):
            raise ValueError("revocation_provenance_sha256_invalid")
        effective = parse_utc(effective_at_utc, "effective_at_utc")
        with self._lock:
            if revocation_id in self._by_id:
                existing = self._by_id[revocation_id]
                if existing["target_id"] == target_id and existing["reason"] == reason:
                    return {"status": "IDEMPOTENT", "event": dict(existing)}
                raise ValueError("revocation_id_collision")
            event = {"schema": "SUPER1200_REVOCATION_EVENT/1", "revocation_id": revocation_id,
                "target_id": target_id, "issuer": issuer, "reason": reason,
                "effective_at_utc": stamp(effective), "provenance_sha256": provenance_sha256,
                "sequence": len(self._events) + 1,
                "previous_event_sha256": self._events[-1]["event_sha256"] if self._events else None}
            event["event_sha256"] = digest(event)
            self._events.append(event); self._by_id[revocation_id] = event
            return {"status": "RECORDED", "event": dict(event)}

    def is_revoked(self, target_id: str, *, now_utc: str) -> dict[str, Any]:
        now = parse_utc(now_utc, "now_utc")
        with self._lock:
            active = [event for event in self._events
                      if event["target_id"] == target_id and parse_utc(event["effective_at_utc"], "effective_at_utc") <= now]
            active.sort(key=lambda event: (event["effective_at_utc"], event["sequence"]))
            return {"schema": "SUPER1200_REVOCATION_STATUS/1", "target_id": target_id,
                "revoked": bool(active), "effective_revocations": [dict(event) for event in active],
                "checked_at_utc": stamp(now)}

    def validate_chain(self) -> dict[str, Any]:
        with self._lock:
            previous = None
            for index, event in enumerate(self._events, start=1):
                unsigned = dict(event); recorded = unsigned.pop("event_sha256", None)
                if event.get("sequence") != index or event.get("previous_event_sha256") != previous:
                    return {"status": "FAIL", "reason": "revocation_chain_sequence_or_link_invalid", "index": index}
                if recorded != digest(unsigned):
                    return {"status": "FAIL", "reason": "revocation_event_hash_invalid", "index": index}
                previous = recorded
            return {"status": "PASS", "event_count": len(self._events), "head_sha256": previous}


def validate_separation_of_duties(assignments: Any) -> dict[str, Any]:
    """Require distinct executor/verifier/G23/G24 identities and prohibit conflicting privileged roles."""
    roles = ("executor", "verifier", "g23", "g24")
    forbidden = {
        "executor": {"verify", "validate_g23", "certify_g24"},
        "verifier": {"materialize", "write_material", "certify_g24"},
        "g23": {"materialize", "write_material", "certify_g24"},
        "g24": {"materialize", "write_material", "validate_g23"},
    }
    reasons = []
    if not isinstance(assignments, dict):
        return {"schema": "SUPER1200_SEPARATION_OF_DUTIES/1", "decision": "DENY",
                "reasons": ["assignments_must_be_object"]}
    actors = {}
    normalized = {}
    for role in roles:
        item = assignments.get(role)
        if not isinstance(item, dict) or not nonblank(item.get("actor")):
            reasons.append("role_assignment_missing:" + role); continue
        permissions = item.get("permissions")
        if not isinstance(permissions, list) or any(not nonblank(p) for p in permissions):
            reasons.append("role_permissions_invalid:" + role); continue
        perms = sorted(set(p.strip() for p in permissions))
        conflict = sorted(set(perms) & forbidden[role])
        if conflict: reasons.append("forbidden_privilege_for_role:" + role + ":" + ",".join(conflict))
        actors[role] = item["actor"].strip()
        normalized[role] = {"actor": actors[role], "permissions": perms}
    for i, left in enumerate(roles):
        for right in roles[i+1:]:
            if left in actors and right in actors and actors[left] == actors[right]:
                reasons.append("actor_reused_across_roles:" + left + ":" + right)
    decision = "ALLOW" if not reasons else "DENY"
    return {"schema": "SUPER1200_SEPARATION_OF_DUTIES/1", "decision": decision,
        "reasons": sorted(set(reasons)), "assignments": normalized,
        "assignment_sha256": digest(normalized), "certification_granted": False}


class TwoManRuleProvider:
    """Risk-scoped approval threshold with distinct actors, signing keys and unexpired approvals."""
    def __init__(self, *, thresholds: dict[str, int], default_threshold: int = 1) -> None:
        if not isinstance(thresholds, dict) or any(not nonblank(k) or not isinstance(v, int)
                or isinstance(v, bool) or v < 1 for k, v in thresholds.items()):
            raise ValueError("two_man_threshold_policy_invalid")
        if not isinstance(default_threshold, int) or isinstance(default_threshold, bool) or default_threshold < 1:
            raise ValueError("two_man_default_threshold_invalid")
        self.thresholds = dict(thresholds)
        self.default_threshold = default_threshold

    def evaluate(self, request: dict[str, Any], *, approvals: list[dict[str, Any]],
                 now_utc: str, signature_verifier: Callable[[dict[str, Any], bytes], Any]) -> dict[str, Any]:
        if not isinstance(request, dict) or not nonblank(request.get("request_id")) or not nonblank(request.get("risk")):
            raise ValueError("two_man_request_identity_required")
        if not isinstance(approvals, list):
            raise ValueError("two_man_approvals_required")
        now = parse_utc(now_utc, "now_utc")
        threshold = self.thresholds.get(request["risk"], self.default_threshold)
        request_hash = digest(request)
        valid = []; reasons = []; actors = set(); key_ids = set()
        for index, approval in enumerate(approvals):
            if not isinstance(approval, dict):
                reasons.append("approval_not_object:" + str(index)); continue
            actor, key_id = approval.get("actor"), approval.get("key_id")
            if not nonblank(actor) or not nonblank(key_id):
                reasons.append("approval_identity_invalid:" + str(index)); continue
            if actor in actors:
                reasons.append("approval_actor_duplicate:" + str(index)); continue
            if key_id in key_ids:
                reasons.append("approval_signing_key_duplicate:" + str(index)); continue
            actors.add(actor); key_ids.add(key_id)
            if approval.get("schema") != "SUPER1200_TWO_MAN_APPROVAL/1":
                reasons.append("approval_schema_invalid:" + str(index)); continue
            if approval.get("request_sha256") != request_hash:
                reasons.append("approval_request_binding_invalid:" + str(index)); continue
            try:
                issued, expires = parse_utc(approval.get("issued_at_utc"), "approval_issued_at_utc"), parse_utc(approval.get("expires_at_utc"), "approval_expires_at_utc")
                if expires <= issued or now < issued or now >= expires:
                    reasons.append("approval_not_current:" + str(index)); continue
            except ValueError as exc:
                reasons.append(str(exc) + ":" + str(index)); continue
            if not isinstance(approval.get("signature"), dict):
                reasons.append("approval_signature_missing:" + str(index)); continue
            if not callable(signature_verifier):
                reasons.append("approval_signature_verifier_required:" + str(index)); continue
            payload = {k: v for k, v in approval.items() if k != "signature"}
            try:
                verified = signature_verifier(approval, canonical_bytes(payload)) is True
            except Exception:
                verified = False
            if not verified:
                reasons.append("approval_signature_invalid:" + str(index)); continue
            valid.append({"actor": actor, "key_id": key_id, "approval_sha256": digest(approval)})
        decision = "ALLOW" if len(valid) >= threshold and not reasons else "DENY"
        if len(valid) < threshold:
            reasons.append("approval_threshold_not_met")
        return {"schema": "SUPER1200_TWO_MAN_RULE_DECISION/1", "decision": decision,
            "risk": request["risk"], "threshold": threshold, "valid_approval_count": len(valid),
            "valid_approvals": valid, "reasons": sorted(set(reasons)), "request_sha256": request_hash,
            "checked_at_utc": stamp(now), "certification_granted": False}
