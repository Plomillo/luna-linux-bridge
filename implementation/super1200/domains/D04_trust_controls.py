"""D04 trust controls for capabilities 117-120.

These deterministic reference implementations fail closed. They do not claim
cryptographic authenticity from hashes alone: attestation, signature and
identity proofs must be approved by injected trusted verifier callbacks.
Persistent deployment must store append-only state outside the process.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone, timedelta
from typing import Any, Callable


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(field + "_required")
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


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


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _verify(callback: Any, *args: Any, error_code: str) -> None:
    if not callable(callback):
        raise ValueError(error_code + "_verifier_required")
    try:
        result = callback(*args)
    except Exception as exc:
        raise ValueError(error_code + "_verifier_error") from exc
    if result is not True:
        raise ValueError(error_code + "_verification_failed")


def verify_actor_independence(policy: Any, assignments: Any, *,
                              independence_verifier: Any) -> dict[str, Any]:
    """Prove role separation across actors, control domains, credentials and paths."""
    if not isinstance(policy, dict) or policy.get("schema") != "SUPER1200_ACTOR_INDEPENDENCE/1":
        raise ValueError("actor_independence_policy_schema_invalid")
    roles = policy.get("required_roles")
    if (not isinstance(roles, list) or not roles
            or any(not text(role) for role in roles) or len(set(roles)) != len(roles)):
        raise ValueError("actor_independence_required_roles_invalid")
    if not isinstance(assignments, dict):
        raise ValueError("actor_independence_assignments_required")
    required_fields = ("actor_id", "control_domain", "credential_id", "execution_path")
    collisions: dict[str, dict[str, list[str]]] = {
        field: {} for field in required_fields
    }
    reasons: list[str] = []
    verifier_receipts = []
    critical_permissions: dict[str, set[str]] = {}
    required_permissions = policy.get("required_permissions_by_role", {})
    if not isinstance(required_permissions, dict):
        raise ValueError("actor_independence_permissions_policy_invalid")
    for role in roles:
        assignment = assignments.get(role)
        if not isinstance(assignment, dict):
            reasons.append("role_assignment_missing:" + role)
            continue
        for field in required_fields:
            value = assignment.get(field)
            if not text(value):
                reasons.append("role_" + field + "_missing:" + role)
            else:
                collisions[field].setdefault(value, []).append(role)
        permissions = assignment.get("permissions")
        if not isinstance(permissions, list) or not permissions or any(not text(x) for x in permissions):
            reasons.append("role_permissions_invalid:" + role)
            permissions = []
        required = required_permissions.get(role, [])
        if not isinstance(required, list) or any(not text(x) for x in required):
            reasons.append("role_required_permissions_invalid:" + role)
            required = []
        missing = sorted(set(required) - set(permissions))
        if missing:
            reasons.append("role_required_permissions_missing:" + role)
        critical = assignment.get("critical_permissions", [])
        if not isinstance(critical, list) or any(not text(x) for x in critical):
            reasons.append("role_critical_permissions_invalid:" + role)
            critical = []
        critical_permissions[role] = set(critical)
        try:
            _verify(independence_verifier, role, assignment, policy,
                    error_code="actor_independence")
            verifier_receipts.append({
                "role": role,
                "assignment_sha256": digest(assignment),
                "verification": "PASS",
            })
        except ValueError:
            reasons.append("trusted_independence_proof_failed:" + role)
    for field, values in collisions.items():
        for value, role_list in values.items():
            if len(role_list) > 1:
                reasons.append(field + "_collision:" + ",".join(sorted(role_list)))
    for role_a in roles:
        for role_b in roles:
            if role_a >= role_b:
                continue
            overlap = sorted(critical_permissions.get(role_a, set()) &
                             critical_permissions.get(role_b, set()))
            if overlap:
                reasons.append("critical_permission_collision:" + role_a + ":" + role_b)
    return {
        "schema": "SUPER1200_ACTOR_INDEPENDENCE_DECISION/1",
        "decision": "ALLOW" if not reasons else "DENY",
        "reasons": sorted(set(reasons)),
        "required_roles": list(roles),
        "verified_assignments": verifier_receipts,
        "independence_verifier_supplied": callable(independence_verifier),
    }


class TrustRootRegistry:
    """Append-only registry for verified roots; revocation is a separate immutable event."""
    def __init__(self) -> None:
        self._roots: dict[str, dict[str, Any]] = {}
        self._revocations: dict[str, dict[str, Any]] = {}
        self._events: list[dict[str, Any]] = []

    @property
    def roots(self) -> tuple[dict[str, Any], ...]:
        return tuple(json.loads(canonical_bytes(self._roots[key]))
                     for key in sorted(self._roots))

    @property
    def revocations(self) -> tuple[dict[str, Any], ...]:
        return tuple(json.loads(canonical_bytes(self._revocations[key]))
                     for key in sorted(self._revocations))

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(json.loads(canonical_bytes(x)) for x in self._events)

    def register(self, root: Any, *, attestation_verifier: Any) -> dict[str, Any]:
        if not isinstance(root, dict):
            raise ValueError("trust_root_must_be_object")
        required = ("root_id", "purpose", "public_key_material", "custody_actor",
                    "valid_from_utc", "valid_until_utc", "attestation")
        if any(not text(root.get(field)) for field in required):
            raise ValueError("trust_root_identity_or_material_missing")
        root_id = root["root_id"]
        start = parse_utc(root["valid_from_utc"], "valid_from_utc")
        end = parse_utc(root["valid_until_utc"], "valid_until_utc")
        if end <= start:
            raise ValueError("trust_root_validity_interval_invalid")
        key_hash = sha256_text(root["public_key_material"], "public_key_material")
        claimed_hash = root.get("public_key_sha256", key_hash)
        if claimed_hash != key_hash:
            raise ValueError("trust_root_public_key_digest_mismatch")
        stable = {
            "schema": "SUPER1200_TRUST_ROOT/1",
            "root_id": root_id,
            "purpose": root["purpose"],
            "public_key_material": root["public_key_material"],
            "public_key_sha256": key_hash,
            "custody_actor": root["custody_actor"],
            "valid_from_utc": start.isoformat().replace("+00:00", "Z"),
            "valid_until_utc": end.isoformat().replace("+00:00", "Z"),
            "attestation": root["attestation"],
        }
        _verify(attestation_verifier, stable, error_code="trust_root_attestation")
        stable["attestation_status"] = "VERIFIED_BY_TRUSTED_CALLBACK"
        old = self._roots.get(root_id)
        if old is not None:
            if old != stable:
                raise ValueError("trust_root_identity_immutable")
            return json.loads(canonical_bytes(old))
        self._roots[root_id] = stable
        self._append_event("ROOT_REGISTERED", {
            "root_id": root_id, "purpose": stable["purpose"],
            "public_key_sha256": key_hash, "custody_actor": stable["custody_actor"],
        })
        return json.loads(canonical_bytes(stable))

    def revoke(self, root_id: str, *, revocation_id: str, actor: str,
               reason: str, effective_at_utc: str,
               revocation_verifier: Any) -> dict[str, Any]:
        if not text(root_id) or not text(revocation_id) or not text(actor) or not text(reason):
            raise ValueError("trust_root_revocation_identity_required")
        if root_id not in self._roots:
            raise ValueError("trust_root_unknown")
        effective = parse_utc(effective_at_utc, "effective_at_utc")
        event = {
            "schema": "SUPER1200_TRUST_ROOT_REVOCATION/1",
            "root_id": root_id, "revocation_id": revocation_id,
            "actor": actor, "reason": reason,
            "effective_at_utc": effective.isoformat().replace("+00:00", "Z"),
        }
        _verify(revocation_verifier, self._roots[root_id], event,
                error_code="trust_root_revocation")
        old = self._revocations.get(root_id)
        if old is not None:
            if old != event:
                raise ValueError("trust_root_revocation_immutable")
            return json.loads(canonical_bytes(old))
        event["event_sha256"] = digest(event)
        self._revocations[root_id] = event
        self._append_event("ROOT_REVOKED", {
            "root_id": root_id, "revocation_id": revocation_id,
            "event_sha256": event["event_sha256"],
        })
        return json.loads(canonical_bytes(event))

    def resolve(self, root_id: str, *, purpose: str, now_utc: str) -> dict[str, Any]:
        root = self._roots.get(root_id)
        if root is None:
            raise ValueError("trust_root_unknown")
        if root["purpose"] != purpose:
            raise ValueError("trust_root_purpose_mismatch")
        now = parse_utc(now_utc, "now_utc")
        if now < parse_utc(root["valid_from_utc"], "valid_from_utc"):
            raise ValueError("trust_root_not_yet_valid")
        if now >= parse_utc(root["valid_until_utc"], "valid_until_utc"):
            raise ValueError("trust_root_expired")
        revoked = self._revocations.get(root_id)
        if revoked and now >= parse_utc(revoked["effective_at_utc"], "effective_at_utc"):
            raise ValueError("trust_root_revoked")
        return json.loads(canonical_bytes(root))

    def snapshot(self, *, now_utc: str | None = None) -> dict[str, Any]:
        roots = [json.loads(canonical_bytes(self._roots[key]))
                 for key in sorted(self._roots)]
        revocations = [json.loads(canonical_bytes(self._revocations[key]))
                       for key in sorted(self._revocations)]
        snapshot = {
            "schema": "SUPER1200_TRUST_ROOT_SNAPSHOT/1",
            "roots": roots, "revocations": revocations,
            "registry_sha256": digest({"roots": roots, "revocations": revocations}),
        }
        if now_utc is not None:
            _ = parse_utc(now_utc, "now_utc")
            snapshot["observed_at_utc"] = parse_utc(now_utc, "now_utc").isoformat().replace("+00:00", "Z")
        return snapshot

    def _append_event(self, event_type: str, payload: dict[str, Any]) -> None:
        unsigned = {
            "schema": "SUPER1200_TRUST_ROOT_REGISTRY_EVENT/1",
            "sequence": len(self._events) + 1,
            "event_type": event_type,
            "payload": payload,
            "previous_event_sha256": self._events[-1]["event_sha256"] if self._events else "0" * 64,
        }
        event = dict(unsigned)
        event["event_sha256"] = digest(unsigned)
        self._events.append(event)

    @classmethod
    def verify_events(cls, events: Any) -> bool:
        if not isinstance(events, (list, tuple)):
            return False
        previous = "0" * 64
        for sequence, event in enumerate(events, start=1):
            if not isinstance(event, dict) or event.get("schema") != "SUPER1200_TRUST_ROOT_REGISTRY_EVENT/1":
                return False
            if event.get("sequence") != sequence or event.get("previous_event_sha256") != previous:
                return False
            unsigned = dict(event)
            recorded = unsigned.pop("event_sha256", None)
            if not isinstance(recorded, str) or digest(unsigned) != recorded:
                return False
            previous = recorded
        return True


class TrustRootRotationLog:
    """Cross-signed, monotonic rotations with overlap windows and preserved history."""
    def __init__(self, roots: TrustRootRegistry) -> None:
        if not isinstance(roots, TrustRootRegistry):
            raise ValueError("trust_root_registry_required")
        self._roots = roots
        self._entries: list[dict[str, Any]] = []
        self._latest_by_purpose: dict[str, str] = {}

    @property
    def entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(json.loads(canonical_bytes(x)) for x in self._entries)

    def rotate(self, old_root_id: str, new_root_id: str, *, now_utc: str,
               overlap_seconds: int, sequence: int, expected_sequence: int,
               old_root_signature: str, new_root_signature: str,
               old_signature_verifier: Any, new_signature_verifier: Any) -> dict[str, Any]:
        if not isinstance(overlap_seconds, int) or isinstance(overlap_seconds, bool) or overlap_seconds <= 0:
            raise ValueError("trust_rotation_overlap_invalid")
        if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence != len(self._entries) + 1:
            raise ValueError("trust_rotation_sequence_rollback_or_gap")
        if expected_sequence != len(self._entries) + 1:
            raise ValueError("trust_rotation_expected_sequence_mismatch")
        if old_root_id == new_root_id:
            raise ValueError("trust_rotation_same_root")
        old = self._roots.resolve(old_root_id, purpose=self._root_purpose(old_root_id), now_utc=now_utc)
        new = self._roots.resolve(new_root_id, purpose=self._root_purpose(new_root_id), now_utc=now_utc)
        if old["purpose"] != new["purpose"]:
            raise ValueError("trust_rotation_purpose_mismatch")
        latest = self._latest_by_purpose.get(old["purpose"])
        if latest is not None and latest != old_root_id:
            raise ValueError("trust_rotation_old_root_not_latest")
        now = parse_utc(now_utc, "now_utc")
        overlap_end = now + timedelta(seconds=overlap_seconds)
        if parse_utc(old["valid_until_utc"], "old_root_valid_until_utc") < overlap_end:
            raise ValueError("trust_rotation_old_root_overlap_too_short")
        if parse_utc(new["valid_from_utc"], "new_root_valid_from_utc") > now:
            raise ValueError("trust_rotation_new_root_not_yet_valid")
        if parse_utc(new["valid_until_utc"], "new_root_valid_until_utc") <= overlap_end:
            raise ValueError("trust_rotation_new_root_overlap_too_short")
        unsigned = {
            "schema": "SUPER1200_TRUST_ROOT_ROTATION/1",
            "sequence": sequence, "purpose": old["purpose"],
            "old_root_id": old_root_id, "old_root_sha256": old["public_key_sha256"],
            "new_root_id": new_root_id, "new_root_sha256": new["public_key_sha256"],
            "requested_at_utc": now.isoformat().replace("+00:00", "Z"),
            "overlap_seconds": overlap_seconds,
            "overlap_end_utc": overlap_end.isoformat().replace("+00:00", "Z"),
            "previous_rotation_sha256": self._entries[-1]["rotation_sha256"] if self._entries else "0" * 64,
        }
        _verify(old_signature_verifier, old, new, unsigned, old_root_signature,
                error_code="trust_rotation_old_root_signature")
        _verify(new_signature_verifier, new, old, unsigned, new_root_signature,
                error_code="trust_rotation_new_root_signature")
        entry = dict(unsigned)
        entry["cross_signatures_verified"] = True
        entry["rotation_sha256"] = digest(entry)
        self._entries.append(entry)
        self._latest_by_purpose[old["purpose"]] = new_root_id
        return json.loads(canonical_bytes(entry))

    @staticmethod
    def _root_purpose_from_registry(roots: TrustRootRegistry, root_id: str) -> str:
        for root in roots.roots:
            if root.get("root_id") == root_id:
                return root["purpose"]
        raise ValueError("trust_root_unknown")

    def _root_purpose(self, root_id: str) -> str:
        return self._root_purpose_from_registry(self._roots, root_id)

    @classmethod
    def verify_history(cls, entries: Any) -> bool:
        if not isinstance(entries, (list, tuple)):
            return False
        previous = "0" * 64
        latest: dict[str, str] = {}
        for sequence, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict) or entry.get("schema") != "SUPER1200_TRUST_ROOT_ROTATION/1":
                return False
            if (entry.get("sequence") != sequence
                    or entry.get("previous_rotation_sha256") != previous
                    or entry.get("cross_signatures_verified") is not True):
                return False
            purpose, old_id, new_id = entry.get("purpose"), entry.get("old_root_id"), entry.get("new_root_id")
            if not all(text(x) for x in (purpose, old_id, new_id)) or old_id == new_id:
                return False
            if purpose in latest and latest[purpose] != old_id:
                return False
            if not isinstance(entry.get("overlap_seconds"), int) or entry["overlap_seconds"] <= 0:
                return False
            unsigned = dict(entry)
            recorded = unsigned.pop("rotation_sha256", None)
            if not isinstance(recorded, str) or digest(unsigned) != recorded:
                return False
            latest[purpose] = new_id
            previous = recorded
        return True


def build_offline_trust_bundle(*, version: int, roots: Any, intermediates: Any,
                               revocations: Any, checkpoints: Any, created_at_utc: str,
                               expires_at_utc: str, previous_bundle_sha256: str | None,
                               bundle_signature: str) -> dict[str, Any]:
    """Create a canonical versioned bundle; signatures still require external verification."""
    if not isinstance(version, int) or isinstance(version, bool) or version < 1:
        raise ValueError("offline_bundle_version_invalid")
    for name, value in (("roots", roots), ("intermediates", intermediates),
                        ("revocations", revocations), ("checkpoints", checkpoints)):
        if not isinstance(value, list):
            raise ValueError("offline_bundle_" + name + "_must_be_list")
    if not roots:
        raise ValueError("offline_bundle_roots_required")
    created = parse_utc(created_at_utc, "created_at_utc")
    expires = parse_utc(expires_at_utc, "expires_at_utc")
    if expires <= created:
        raise ValueError("offline_bundle_expiry_invalid")
    if version == 1 and previous_bundle_sha256 is not None:
        raise ValueError("offline_bundle_genesis_has_no_predecessor")
    if version > 1:
        if not isinstance(previous_bundle_sha256, str) or len(previous_bundle_sha256) != 64:
            raise ValueError("offline_bundle_predecessor_hash_required")
        if any(ch not in "0123456789abcdef" for ch in previous_bundle_sha256):
            raise ValueError("offline_bundle_predecessor_hash_invalid")
    root_ids = [root.get("root_id") for root in roots if isinstance(root, dict)]
    if len(root_ids) != len(roots) or any(not text(x) for x in root_ids) or len(set(root_ids)) != len(root_ids):
        raise ValueError("offline_bundle_root_identity_duplicate_or_invalid")
    unsigned = {
        "schema": "SUPER1200_OFFLINE_TRUST_BUNDLE/1",
        "version": version,
        "created_at_utc": created.isoformat().replace("+00:00", "Z"),
        "expires_at_utc": expires.isoformat().replace("+00:00", "Z"),
        "previous_bundle_sha256": previous_bundle_sha256,
        "roots": sorted(roots, key=lambda x: x["root_id"]),
        "intermediates": sorted(intermediates, key=canonical_bytes),
        "revocations": sorted(revocations, key=canonical_bytes),
        "checkpoints": sorted(checkpoints, key=canonical_bytes),
        "bundle_signature": bundle_signature,
    }
    if not text(bundle_signature):
        raise ValueError("offline_bundle_signature_required")
    bundle = dict(unsigned)
    bundle["bundle_sha256"] = digest(unsigned)
    return bundle


def verify_offline_trust_bundle(bundle: Any, *, now_utc: str,
                                minimum_version: int,
                                expected_previous_bundle_sha256: str | None,
                                bundle_signature_verifier: Any) -> dict[str, Any]:
    """Validate bundle content hash, expiry, anti-rollback chain and signature callback."""
    if not isinstance(bundle, dict) or bundle.get("schema") != "SUPER1200_OFFLINE_TRUST_BUNDLE/1":
        raise ValueError("offline_bundle_schema_invalid")
    version = bundle.get("version")
    if not isinstance(version, int) or isinstance(version, bool) or version < minimum_version:
        raise ValueError("offline_bundle_rollback_detected")
    if expected_previous_bundle_sha256 is not None and bundle.get("previous_bundle_sha256") != expected_previous_bundle_sha256:
        raise ValueError("offline_bundle_chain_mismatch")
    if version == 1 and bundle.get("previous_bundle_sha256") is not None:
        raise ValueError("offline_bundle_genesis_chain_mismatch")
    created = parse_utc(bundle.get("created_at_utc"), "created_at_utc")
    expires = parse_utc(bundle.get("expires_at_utc"), "expires_at_utc")
    now = parse_utc(now_utc, "now_utc")
    if expires <= created:
        raise ValueError("offline_bundle_expiry_invalid")
    if now < created:
        raise ValueError("offline_bundle_not_yet_valid")
    if now >= expires:
        raise ValueError("offline_bundle_expired")
    unsigned = dict(bundle)
    recorded_hash = unsigned.pop("bundle_sha256", None)
    if not isinstance(recorded_hash, str) or digest(unsigned) != recorded_hash:
        raise ValueError("offline_bundle_content_hash_mismatch")
    _verify(bundle_signature_verifier, bundle, error_code="offline_bundle_signature")
    return {
        "schema": "SUPER1200_OFFLINE_TRUST_BUNDLE_VALIDATION/1",
        "decision": "ALLOW",
        "version": version,
        "bundle_sha256": recorded_hash,
        "root_count": len(bundle.get("roots", [])),
        "intermediate_count": len(bundle.get("intermediates", [])),
        "revocation_count": len(bundle.get("revocations", [])),
        "checkpoint_count": len(bundle.get("checkpoints", [])),
        "signature": "VERIFIED_BY_TRUSTED_CALLBACK",
    }
