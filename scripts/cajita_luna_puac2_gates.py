#!/usr/bin/env python3
"""Cajita-scoped PUAC2 G23/G24 signing and verification.

G23 and G24 are distinct signed roles. This utility never modifies payload files,
never generates a PASS from missing evidence, and never promotes Louksna canonically.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from scripts import cajita_luna_governed_preflight as ctl
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scripts import cajita_luna_governed_preflight as ctl

COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
G23_SCHEMA = "CAJITA_PUAC2_G23_PAYLOAD/1.0"
G24_SCHEMA = "CAJITA_PUAC2_G24_PAYLOAD/1.0"
G23_ENVELOPE_SCHEMA = "CAJITA_PUAC2_G23_SIGNED/1.0"
G24_ENVELOPE_SCHEMA = "CAJITA_PUAC2_G24_SIGNED/1.0"
INDEPENDENT_TESTS_REL = ".cajita-optimization-candidates/evidence/INDEPENDENT_FUNCTIONAL_TESTS.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_ROOT_NOT_OBJECT:{path}")
    return value


def crypto_types():
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
    except ImportError as exc:
        raise RuntimeError("CRYPTography_REQUIRED_FOR_G23_G24") from exc
    return serialization, Ed25519PrivateKey, Ed25519PublicKey


def public_pem_from_private(private_pem: str) -> str:
    serialization, private_type, _ = crypto_types()
    key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
    if not isinstance(key, private_type):
        raise ValueError("SIGNING_KEY_NOT_ED25519")
    public = key.public_key()
    return public.public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode("ascii")


def public_key_fingerprint(public_pem: str) -> str:
    serialization, _, public_type = crypto_types()
    key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
    if not isinstance(key, public_type):
        raise ValueError("VERIFY_KEY_NOT_ED25519")
    raw = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return digest_bytes(raw)


def sign_envelope(payload: dict[str, Any], private_pem: str, signer_id: str, schema: str) -> dict[str, Any]:
    serialization, private_type, _ = crypto_types()
    if not isinstance(signer_id, str) or not signer_id.strip():
        raise ValueError("SIGNER_ID_MISSING")
    key = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
    if not isinstance(key, private_type):
        raise ValueError("SIGNER_KEY_NOT_ED25519")
    identity_field = "validator_id" if schema == G23_ENVELOPE_SCHEMA else "certifier_id"
    if payload.get(identity_field) != signer_id:
        raise ValueError("SIGNER_IDENTITY_PAYLOAD_MISMATCH")
    canonical = canonical_json(payload)
    signature = base64.b64encode(key.sign(canonical)).decode("ascii")
    return {
        "schema": schema,
        "status": "SIGNED",
        "signer_id": signer_id,
        "payload_sha256": digest_bytes(canonical),
        "signer_public_key_sha256": digest_bytes(key.public_key().public_bytes(
            serialization.Encoding.Raw, serialization.PublicFormat.Raw
        )),
        "signature_b64": signature,
        "payload": payload,
    }


def verify_envelope(envelope: Any, public_pem: str, expected_schema: str, expected_signer: str | None = None) -> tuple[dict[str, Any] | None, list[str]]:
    errors: list[str] = []
    if not isinstance(envelope, dict):
        return None, ["SIGNED_ENVELOPE_NOT_OBJECT"]
    if envelope.get("schema") != expected_schema:
        errors.append("SIGNED_ENVELOPE_SCHEMA_MISMATCH")
    if envelope.get("status") != "SIGNED":
        errors.append("SIGNED_ENVELOPE_STATUS_INVALID")
    signer_id = envelope.get("signer_id")
    if not isinstance(signer_id, str) or not signer_id.strip():
        errors.append("SIGNED_ENVELOPE_SIGNER_MISSING")
    if expected_signer and signer_id != expected_signer:
        errors.append("SIGNED_ENVELOPE_SIGNER_MISMATCH")
    payload = envelope.get("payload")
    if not isinstance(payload, dict):
        return None, errors + ["SIGNED_ENVELOPE_PAYLOAD_MISSING"]
    raw = canonical_json(payload)
    expected_payload_hash = digest_bytes(raw)
    if envelope.get("payload_sha256") != expected_payload_hash:
        errors.append("SIGNED_PAYLOAD_HASH_MISMATCH")
    try:
        serialization, _, public_type = crypto_types()
        key = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        if not isinstance(key, public_type):
            errors.append("VERIFY_KEY_NOT_ED25519")
        else:
            raw_key = key.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
            if envelope.get("signer_public_key_sha256") != digest_bytes(raw_key):
                errors.append("SIGNER_PUBLIC_KEY_FINGERPRINT_MISMATCH")
            signature = envelope.get("signature_b64")
            if not isinstance(signature, str):
                errors.append("SIGNATURE_MISSING")
            else:
                try:
                    key.verify(base64.b64decode(signature, validate=True), raw)
                except Exception:
                    errors.append("ED25519_SIGNATURE_INVALID")
    except Exception as exc:
        errors.append("SIGNATURE_VERIFICATION_ERROR:" + type(exc).__name__)
    identity_field = "validator_id" if expected_schema == G23_ENVELOPE_SCHEMA else "certifier_id"
    if payload.get(identity_field) != signer_id:
        errors.append("PAYLOAD_SIGNER_IDENTITY_MISMATCH")
    return (payload if not errors else None), sorted(set(errors))


def final_evidence(root: Path) -> dict[str, Any]:
    blockers: list[str] = []
    if not root.exists() or not root.is_dir() or root.is_symlink():
        return {
            "schema": G23_SCHEMA,
            "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "subject_tree_sha256": None,
            "tree_bytes_at_validation": None,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": None,
            "gates_checked": [],
            "evidence_hashes": {},
            "blockers": ["CAJITA_ROOT_MISSING_OR_UNSAFE"],
            "decision_utc": utc_now(),
        }
    inventory = ctl.scan_tree(root)
    total = inventory["total_bytes"]
    projected = total + ctl.MIN_EVIDENCE_RESERVE_BYTES
    if total + ctl.MIN_EVIDENCE_RESERVE_BYTES > ctl.CAP_BYTES:
        blockers.append("FINAL_TREE_PLUS_CERTIFICATE_RESERVE_EXCEEDS_CAP")
    if inventory["symlinks"]:
        blockers.append("SYMLINKS_PRESENT_FAIL_CLOSED")
    if inventory["hardlink_groups"]:
        blockers.append("HARDLINKS_PRESENT_FAIL_CLOSED")
    if inventory["non_regular"] or inventory["scan_errors"]:
        blockers.append("TREE_CONTAINS_UNSAFE_OR_UNREADABLE_ENTRIES")
    for domain in ctl.EXPECTED_DOMAINS:
        path = root / domain
        if not path.is_dir() or path.is_symlink():
            blockers.append("MANDATORY_DOMAIN_MISSING:" + domain)
    # Avoid multi-gigabyte content hashing when the budget already proves that the
    # final candidate cannot pass. This still returns a signed, auditable HOLD.
    if total + ctl.MIN_EVIDENCE_RESERVE_BYTES > ctl.CAP_BYTES:
        for rel, blocker in (
            (ctl.FROZEN_MANIFEST_REL, "FROZEN_V9_OUTPUTS_MANIFEST_MISSING"),
            (ctl.RECONCILIATION_REL, "REGISTRY_RECONCILIATION_MANIFEST_MISSING"),
            (ctl.PLAN_REL, "OPTIMIZATION_PLAN_MISSING"),
            (ctl.FUNCTIONAL_REL, "FUNCTIONAL_VALIDATION_MANIFEST_MISSING"),
            (ctl.GATE_MATRIX_REL, "G01_G22_EVIDENCE_MATRIX_MISSING"),
            (".cajita-optimization-candidates/OPTIMIZATION_EXECUTION_V9.json", "OPTIMIZATION_EXECUTION_MANIFEST_MISSING"),
        ):
            if not (root / rel).is_file():
                blockers.append(blocker)
        return {
            "schema": G23_SCHEMA,
            "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "subject_tree_sha256": None,
            "tree_bytes_at_validation": total,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": projected,
            "gates_checked": [],
            "evidence_hashes": {},
            "blockers": sorted(set(blockers)),
            "decision_utc": utc_now(),
        }
    edge = ctl.edge_evidence(root)
    if edge.get("status") != "PASS":
        blockers.append("EDGE_ARCHIVE_INTEGRITY_BLOCKED")
    registry = ctl.registry_comparison(root)
    blockers.extend(ctl.validate_reconciliation(root, registry))
    blockers.extend(ctl.validate_frozen_manifest(root))
    blockers.extend(ctl.validate_functional_manifest(root))
    blockers.extend(ctl.validate_gate_matrix(root))
    blockers.extend(ctl.validate_execution_manifest(root))
    independent_path = root / INDEPENDENT_TESTS_REL
    independent: dict[str, Any] | None = None
    if not independent_path.is_file():
        blockers.append("INDEPENDENT_FUNCTIONAL_REEXECUTION_EVIDENCE_MISSING")
    else:
        try:
            independent = load_object(independent_path)
            if independent.get("schema") != "CAJITA_INDEPENDENT_FUNCTIONAL_TESTS/1.0":
                blockers.append("INDEPENDENT_FUNCTIONAL_TESTS_SCHEMA_MISMATCH")
            if independent.get("status") != "PASS":
                blockers.append("INDEPENDENT_FUNCTIONAL_TESTS_NOT_PASS")
            if independent.get("executor_id") in (None, "", "CUSTOSZ_V9"):
                blockers.append("INDEPENDENT_FUNCTIONAL_TESTER_ID_INVALID")
            for field in ("test_suite_sha256", "test_report_sha256", "execution_manifest_sha256"):
                if not ctl.is_sha256(independent.get(field)):
                    blockers.append("INDEPENDENT_FUNCTIONAL_EVIDENCE_HASH_MISSING:" + field)
            execution_path = root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json"
            if execution_path.is_file() and independent.get("execution_manifest_sha256") != ctl.sha256_file(execution_path):
                blockers.append("INDEPENDENT_TESTS_EXECUTION_MANIFEST_MISMATCH")
            expected_retested = set(ctl.EXPECTED_DOMAINS) | set(ctl.PENDING_COMPONENTS)
            retested = independent.get("retested_scopes")
            if not isinstance(retested, list) or not expected_retested.issubset(set(retested)):
                blockers.append("INDEPENDENT_TEST_SCOPE_COVERAGE_INCOMPLETE")
        except (OSError, ValueError, json.JSONDecodeError):
            blockers.append("INDEPENDENT_FUNCTIONAL_TESTS_INVALID_JSON")
    if blockers:
        return {
            "schema": G23_SCHEMA,
            "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "subject_tree_sha256": None,
            "tree_bytes_at_validation": total,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": projected,
            "gates_checked": [],
            "evidence_hashes": {},
            "blockers": sorted(set(blockers)),
            "decision_utc": utc_now(),
        }
    try:
        subject_sha, hashed_files, payload_bytes = ctl.candidate_tree_digest(root)
    except (OSError, ValueError) as exc:
        return {
            "schema": G23_SCHEMA,
            "status": "HOLD",
            "scope": "CAJITA_DE_LUNA_EXACT_TREE",
            "subject_tree_sha256": None,
            "tree_bytes_at_validation": total,
            "hard_cap_bytes": ctl.CAP_BYTES,
            "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
            "projected_tree_bytes_with_reserve": projected,
            "gates_checked": [],
            "evidence_hashes": {},
            "blockers": ["SUBJECT_DIGEST_FAILED:" + type(exc).__name__],
            "decision_utc": utc_now(),
        }
    hash_paths = {
        "registry_sha256": root / "RUNTIME_CANDIDATE_V1" / "registry.json",
        "reconciliation_sha256": root / ctl.RECONCILIATION_REL,
        "frozen_manifest_sha256": root / ctl.FROZEN_MANIFEST_REL,
        "optimization_plan_sha256": root / ctl.PLAN_REL,
        "execution_manifest_sha256": root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json",
        "functional_manifest_sha256": root / ctl.FUNCTIONAL_REL,
        "gate_matrix_sha256": root / ctl.GATE_MATRIX_REL,
        "independent_tests_sha256": independent_path,
    }
    evidence_hashes = {
        key: ctl.sha256_file(path) for key, path in hash_paths.items()
        if path.is_file() and not path.is_symlink()
    }
    if len(evidence_hashes) != len(hash_paths):
        blockers.append("REQUIRED_EVIDENCE_HASH_MISSING")
    return {
        "schema": G23_SCHEMA,
        "status": "PASS" if not blockers else "HOLD",
        "scope": "CAJITA_DE_LUNA_EXACT_TREE",
        "subject_tree_sha256": subject_sha,
        "tree_bytes_at_validation": total,
        "hard_cap_bytes": ctl.CAP_BYTES,
        "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
        "projected_tree_bytes_with_reserve": projected,
        "candidate_payload_bytes_hashed": payload_bytes,
        "candidate_file_count_hashed": hashed_files,
        "edge_sha256": edge.get("sha256_observed"),
        "evidence_hashes": evidence_hashes,
        "gates_checked": ctl.GATE_IDS_22 if not blockers else [],
        "blockers": sorted(set(blockers)),
        "decision_utc": utc_now(),
    }


def sign_g23(unsigned_path: Path, output_path: Path, private_pem: str, validator_id: str, producer_id: str) -> dict[str, Any]:
    payload = load_object(unsigned_path)
    blockers = list(payload.get("blockers", [])) if isinstance(payload.get("blockers"), list) else ["G23_BLOCKER_LIST_INVALID"]
    if payload.get("schema") != G23_SCHEMA:
        blockers.append("G23_UNSIGNED_SCHEMA_MISMATCH")
    if payload.get("validator_id") not in (None, "", validator_id):
        blockers.append("G23_VALIDATOR_ID_MISMATCH")
    payload["validator_id"] = validator_id
    payload["producer_id"] = producer_id
    if not validator_id or validator_id == producer_id:
        blockers.append("G23_IDENTITY_NOT_INDEPENDENT")
    if not COMMIT_RE.fullmatch(str(payload.get("candidate_commit", ""))):
        blockers.append("G23_CANDIDATE_COMMIT_INVALID")
    if payload.get("status") != "PASS" or blockers:
        payload["status"] = "HOLD"
        payload["blockers"] = sorted(set(blockers))
    if not private_pem:
        envelope = {
            "schema": G23_ENVELOPE_SCHEMA,
            "status": "HOLD_UNSIGNED",
            "signer_id": validator_id,
            "payload_sha256": digest_bytes(canonical_json(payload)),
            "signature_b64": None,
            "payload": payload,
            "signing_blocker": "G23_PRIVATE_KEY_NOT_CONFIGURED",
        }
    else:
        try:
            envelope = sign_envelope(payload, private_pem, validator_id, G23_ENVELOPE_SCHEMA)
            envelope["status"] = "SIGNED"
        except Exception as exc:
            envelope = {
                "schema": G23_ENVELOPE_SCHEMA, "status": "HOLD_UNSIGNED",
                "signer_id": validator_id, "payload": payload, "signature_b64": None,
                "payload_sha256": digest_bytes(canonical_json(payload)),
                "signing_blocker": "G23_SIGNING_FAILED:" + type(exc).__name__,
            }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return envelope


def issue_g24(g23_path: Path, output_path: Path, g23_public_pem: str, g24_private_pem: str,
              certifier_id: str, producer_id: str, candidate_commit: str,
              expected_subject_sha256: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        g23_envelope = load_object(g23_path)
    except (OSError, ValueError, json.JSONDecodeError):
        g23_envelope = None
        errors.append("G23_RECEIPT_MISSING_OR_INVALID")
    g23_payload = None
    if g23_envelope is not None and g23_public_pem:
        g23_payload, verify_errors = verify_envelope(g23_envelope, g23_public_pem, G23_ENVELOPE_SCHEMA)
        errors.extend(verify_errors)
    elif not g23_public_pem:
        errors.append("G23_PUBLIC_KEY_NOT_CONFIGURED")
    if g23_payload is None:
        errors.append("G23_SIGNATURE_NOT_VERIFIED")
    if not ctl.is_sha256(expected_subject_sha256):
        errors.append("G24_EXPECTED_SUBJECT_SHA256_INVALID")
    if not certifier_id or certifier_id in {producer_id, (g23_payload or {}).get("validator_id")}:
        errors.append("G24_CERTIFIER_ID_INVALID")
    if g23_public_pem and g24_private_pem:
        try:
            g23_fingerprint = public_key_fingerprint(g23_public_pem)
            g24_fingerprint = public_key_fingerprint(public_pem_from_private(g24_private_pem))
            if g23_fingerprint == g24_fingerprint:
                errors.append("G23_G24_SIGNING_KEYS_NOT_DISTINCT")
        except Exception as exc:
            errors.append("G23_G24_SIGNING_KEY_VALIDATION_FAILED:" + type(exc).__name__)
    if g23_payload is not None:
        if g23_payload.get("status") != "PASS":
            errors.extend(g23_payload.get("blockers", []) or ["G23_NOT_PASS"])
        if g23_payload.get("validator_id") in (None, "", producer_id, certifier_id):
            errors.append("G23_G24_IDENTITIES_NOT_DISTINCT")
        if g23_payload.get("producer_id") != producer_id:
            errors.append("G23_PRODUCER_ID_MISMATCH")
        if g23_payload.get("candidate_commit") != candidate_commit:
            errors.append("G23_CANDIDATE_COMMIT_MISMATCH")
        if g23_payload.get("scope") != "CAJITA_DE_LUNA_EXACT_TREE":
            errors.append("G23_SCOPE_MISMATCH")
        if g23_payload.get("gates_checked") != ctl.GATE_IDS_22:
            errors.append("G23_REQUIRED_GATES_INCOMPLETE")
        if not ctl.is_sha256(g23_payload.get("subject_tree_sha256")):
            errors.append("G23_SUBJECT_HASH_INVALID")
        if expected_subject_sha256 and g23_payload.get("subject_tree_sha256") != expected_subject_sha256:
            errors.append("G23_DISPATCHED_SUBJECT_MISMATCH")
        evidence_hashes = g23_payload.get("evidence_hashes")
        required_hashes = {
            "registry_sha256", "reconciliation_sha256", "frozen_manifest_sha256",
            "optimization_plan_sha256", "execution_manifest_sha256",
            "functional_manifest_sha256", "gate_matrix_sha256", "independent_tests_sha256",
        }
        if not isinstance(evidence_hashes, dict) or set(evidence_hashes) != required_hashes or any(not ctl.is_sha256(v) for v in evidence_hashes.values()):
            errors.append("G23_EVIDENCE_HASH_SET_INVALID")
        measured_bytes = g23_payload.get("tree_bytes_at_validation")
        reserve_bytes = g23_payload.get("evidence_reserve_bytes")
        projected_bytes = g23_payload.get("projected_tree_bytes_with_reserve")
        if (
            isinstance(measured_bytes, bool) or not isinstance(measured_bytes, int) or measured_bytes < 0
            or isinstance(reserve_bytes, bool) or not isinstance(reserve_bytes, int) or reserve_bytes < ctl.MIN_EVIDENCE_RESERVE_BYTES
            or g23_payload.get("hard_cap_bytes") != ctl.CAP_BYTES
            or projected_bytes != measured_bytes + reserve_bytes
            or measured_bytes > ctl.CAP_BYTES
            or projected_bytes > ctl.CAP_BYTES
        ):
            errors.append("G23_SIZE_OR_RESERVE_INVALID")
        if g23_payload.get("blockers"):
            errors.append("G23_REPORT_HAS_BLOCKERS")
    g23_payload_hash = g23_envelope.get("payload_sha256") if isinstance(g23_envelope, dict) else None
    status = "CERTIFIED" if not errors else "HOLD"
    payload = {
        "schema": G24_SCHEMA,
        "status": status,
        "certification_granted": status == "CERTIFIED",
        "scope": "CAJITA_DE_LUNA_EXACT_TREE",
        "certifier_id": certifier_id,
        "producer_id": producer_id,
        "validator_id": g23_payload.get("validator_id") if g23_payload else None,
        "candidate_commit": candidate_commit,
        "subject_tree_sha256": g23_payload.get("subject_tree_sha256") if g23_payload else None,
        "g23_payload_sha256": g23_payload_hash,
        "g23_envelope_sha256": digest_bytes(canonical_json(g23_envelope)) if isinstance(g23_envelope, dict) else None,
        "gates_checked": ctl.GATE_IDS_24 if status == "CERTIFIED" else [],
        "tree_bytes_at_g23": g23_payload.get("tree_bytes_at_validation") if g23_payload else None,
        "hard_cap_bytes": ctl.CAP_BYTES,
        "evidence_reserve_bytes": ctl.MIN_EVIDENCE_RESERVE_BYTES,
        "blockers": sorted(set(errors)),
        "decision_utc": utc_now(),
        "canonical_authority_transfer": False,
        "certification_propagation": False,
    }
    if g24_private_pem:
        try:
            envelope = sign_envelope(payload, g24_private_pem, certifier_id, G24_ENVELOPE_SCHEMA)
            envelope["status"] = "SIGNED"
        except Exception as exc:
            envelope = {
                "schema": G24_ENVELOPE_SCHEMA, "status": "HOLD_UNSIGNED", "signer_id": certifier_id,
                "payload_sha256": digest_bytes(canonical_json(payload)), "signature_b64": None,
                "payload": payload, "signing_blocker": "G24_SIGNING_FAILED:" + type(exc).__name__,
            }
            envelope["payload"]["status"] = "HOLD"
            envelope["payload"]["certification_granted"] = False
    else:
        payload["status"] = "HOLD"
        payload["certification_granted"] = False
        payload["blockers"] = sorted(set(errors + ["G24_PRIVATE_KEY_NOT_CONFIGURED"]))
        envelope = {
            "schema": G24_ENVELOPE_SCHEMA, "status": "HOLD_UNSIGNED", "signer_id": certifier_id,
            "payload_sha256": digest_bytes(canonical_json(payload)), "signature_b64": None,
            "payload": payload, "signing_blocker": "G24_PRIVATE_KEY_NOT_CONFIGURED",
        }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(envelope, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return envelope


def verify_release(root: Path, manifest_path: Path, g23_public_pem: str, g24_public_pem: str,
                   expected_candidate_commit: str | None = None) -> dict[str, Any]:
    errors: list[str] = []
    try:
        inventory = ctl.scan_tree(root)
    except (OSError, ValueError) as exc:
        return {"decision": "HOLD", "certification_status": "NOT_GRANTED",
                "blockers": ["CAJITA_INVENTORY_FAILED:" + type(exc).__name__]}
    if inventory["total_bytes"] > ctl.CAP_BYTES:
        return {
            "schema": "CAJITA_PUAC2_RELEASE_VERIFICATION/1.0",
            "decision": "HOLD",
            "certification_status": "NOT_GRANTED",
            "current_tree_bytes": inventory["total_bytes"],
            "hard_cap_bytes": ctl.CAP_BYTES,
            "overage_bytes": inventory["total_bytes"] - ctl.CAP_BYTES,
            "blockers": ["FINAL_TREE_EXCEEDS_CAP"],
            "measured_at_utc": utc_now(),
        }
    if inventory["symlinks"] or inventory["hardlink_groups"] or inventory["non_regular"] or inventory["scan_errors"]:
        errors.append("FINAL_TREE_HAS_UNSAFE_ENTRIES")
    for domain in ctl.EXPECTED_DOMAINS:
        if not (root / domain).is_dir() or (root / domain).is_symlink():
            errors.append("MANDATORY_DOMAIN_MISSING:" + domain)
    edge = ctl.edge_evidence(root)
    if edge.get("status") != "PASS":
        errors.append("EDGE_ARCHIVE_INTEGRITY_BLOCKED")
    registry = ctl.registry_comparison(root)
    errors.extend(ctl.validate_reconciliation(root, registry))
    errors.extend(ctl.validate_frozen_manifest(root))
    errors.extend(ctl.validate_functional_manifest(root))
    errors.extend(ctl.validate_gate_matrix(root))
    errors.extend(ctl.validate_execution_manifest(root))
    independent_path = root / INDEPENDENT_TESTS_REL
    if not independent_path.is_file():
        errors.append("INDEPENDENT_FUNCTIONAL_REEXECUTION_EVIDENCE_MISSING")
    try:
        manifest = load_object(manifest_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return {"decision": "HOLD", "certification_status": "NOT_GRANTED",
                "blockers": sorted(set(errors + ["PUAC2_CERTIFICATION_MANIFEST_INVALID"]))}
    if manifest.get("schema") != "CAJITA_PUAC2_CERTIFICATION_MANIFEST/1.0":
        errors.append("PUAC2_CERTIFICATION_MANIFEST_SCHEMA_MISMATCH")
    candidate_commit = manifest.get("candidate_commit")
    if not COMMIT_RE.fullmatch(str(candidate_commit or "")):
        errors.append("CERTIFICATION_CANDIDATE_COMMIT_INVALID")
    if expected_candidate_commit and candidate_commit != expected_candidate_commit:
        errors.append("CERTIFICATION_CANDIDATE_COMMIT_MISMATCH")
    execution_path = root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json"
    if not execution_path.is_file() or execution_path.is_symlink():
        errors.append("OPTIMIZATION_EXECUTION_MANIFEST_MISSING")
    else:
        try:
            execution_manifest = load_object(execution_path)
            if execution_manifest.get("candidate_commit") != candidate_commit:
                errors.append("CERTIFICATION_COMMIT_NOT_BOUND_TO_OPTIMIZATION_EXECUTION")
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("OPTIMIZATION_EXECUTION_MANIFEST_INVALID")

    run_id = manifest.get("run_id")
    if not isinstance(run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", run_id):
        errors.append("CERTIFICATION_RUN_ID_INVALID")
        run_id = "INVALID_RUN_ID"
    evidence_dir = ".cajita-optimization-candidates/evidence"
    expected_json_names = [
        f"CAJITA_G23_{run_id}.json",
        f"CAJITA_G24_{run_id}.json",
        f"cajita-certification-manifest-{run_id}.json",
        f"cajita-release-verification-{run_id}.json",
    ]
    expected_generated_paths = sorted(
        [f"{evidence_dir}/{name}" for name in expected_json_names]
        + [f"{evidence_dir}/{name}.sha256" for name in expected_json_names]
    )
    generated_paths = manifest.get("generated_evidence_paths")
    subject_exclusions = manifest.get("subject_excluded_paths")
    if generated_paths != expected_generated_paths or subject_exclusions != expected_generated_paths:
        errors.append("CERTIFICATION_SUBJECT_EXCLUSIONS_NOT_EXACT_RUN_SCOPE")
    # All receipt files and sidecars must exist and hash correctly. The decision
    # report is absent during the first verification pass but required on read-back.
    for rel in expected_generated_paths:
        target = root / rel
        if not target.exists():
            if rel.endswith(f"cajita-release-verification-{run_id}.json") or rel.endswith(f"cajita-release-verification-{run_id}.json.sha256"):
                continue
            errors.append("CERTIFICATION_EVIDENCE_FILE_MISSING:" + rel)
            continue
        if target.is_symlink() or not target.is_file():
            errors.append("CERTIFICATION_EVIDENCE_FILE_UNSAFE:" + rel)
            continue
        if rel.endswith(".sha256"):
            continue
        sidecar = target.with_suffix(target.suffix + ".sha256")
        if not sidecar.is_file() or sidecar.is_symlink():
            errors.append("CERTIFICATION_EVIDENCE_SIDECAR_MISSING:" + rel)
            continue
        match = re.match(r"^([0-9a-f]{64})\s+", sidecar.read_text(encoding="utf-8", errors="replace"))
        if not match or match.group(1) != ctl.sha256_file(target):
            errors.append("CERTIFICATION_EVIDENCE_SIDECAR_MISMATCH:" + rel)

    g23_envelope = manifest.get("g23")
    g24_envelope = manifest.get("g24")
    g23_payload = None
    g24_payload = None
    if not g23_public_pem:
        errors.append("G23_PUBLIC_KEY_NOT_CONFIGURED")
    elif g23_envelope is not None:
        g23_payload, verification_errors = verify_envelope(g23_envelope, g23_public_pem, G23_ENVELOPE_SCHEMA)
        errors.extend(["G23:" + item for item in verification_errors])
    else:
        errors.append("G23_RECEIPT_MISSING")
    if not g24_public_pem:
        errors.append("G24_PUBLIC_KEY_NOT_CONFIGURED")
    elif g24_envelope is not None:
        g24_payload, verification_errors = verify_envelope(g24_envelope, g24_public_pem, G24_ENVELOPE_SCHEMA)
        errors.extend(["G24:" + item for item in verification_errors])
    else:
        errors.append("G24_CERTIFICATE_MISSING")

    manifest_evidence = manifest.get("evidence")
    if not isinstance(manifest_evidence, dict):
        errors.append("CERTIFICATION_MANIFEST_EVIDENCE_MISSING")
    else:
        if not isinstance(g23_envelope, dict) or manifest_evidence.get("g23_receipt_sha256") != digest_bytes(canonical_json(g23_envelope)):
            errors.append("MANIFEST_G23_RECEIPT_HASH_MISMATCH")
        if not isinstance(g24_envelope, dict) or manifest_evidence.get("g24_receipt_sha256") != digest_bytes(canonical_json(g24_envelope)):
            errors.append("MANIFEST_G24_RECEIPT_HASH_MISMATCH")

    try:
        subject_sha, hashed_files, hashed_bytes = ctl.candidate_tree_digest(root, set(expected_generated_paths))
    except (OSError, ValueError) as exc:
        subject_sha, hashed_files, hashed_bytes = None, 0, 0
        errors.append("FINAL_SUBJECT_DIGEST_FAILED:" + type(exc).__name__)
    if isinstance(manifest_evidence, dict):
        if manifest_evidence.get("output_sha256") != subject_sha or manifest_evidence.get("subject_tree_sha256") != subject_sha:
            errors.append("MANIFEST_SUBJECT_DIGEST_MISMATCH")

    if g23_payload is not None:
        if g23_payload.get("status") != "PASS" or g23_payload.get("blockers"):
            errors.append("G23_NOT_PASS_OR_HAS_BLOCKERS")
        if g23_payload.get("candidate_commit") != candidate_commit:
            errors.append("G23_COMMIT_MISMATCH")
        if g23_payload.get("subject_tree_sha256") != subject_sha:
            errors.append("G23_SUBJECT_HASH_MISMATCH")
        if g23_payload.get("gates_checked") != ctl.GATE_IDS_22:
            errors.append("G23_REQUIRED_GATE_SET_MISMATCH")
        if g23_payload.get("scope") != "CAJITA_DE_LUNA_EXACT_TREE":
            errors.append("G23_SCOPE_MISMATCH")
        expected_evidence = {
            "registry_sha256": root / "RUNTIME_CANDIDATE_V1" / "registry.json",
            "reconciliation_sha256": root / ctl.RECONCILIATION_REL,
            "frozen_manifest_sha256": root / ctl.FROZEN_MANIFEST_REL,
            "optimization_plan_sha256": root / ctl.PLAN_REL,
            "execution_manifest_sha256": root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json",
            "functional_manifest_sha256": root / ctl.FUNCTIONAL_REL,
            "gate_matrix_sha256": root / ctl.GATE_MATRIX_REL,
            "independent_tests_sha256": root / INDEPENDENT_TESTS_REL,
        }
        actual_evidence = {
            key: ctl.sha256_file(path) for key, path in expected_evidence.items()
            if path.is_file() and not path.is_symlink()
        }
        if g23_payload.get("evidence_hashes") != actual_evidence:
            errors.append("G23_EVIDENCE_HASHES_NO_LONGER_MATCH_TREE")
    if g24_payload is not None:
        if g24_payload.get("status") != "CERTIFIED" or g24_payload.get("certification_granted") is not True:
            errors.append("G24_CERTIFICATION_NOT_GRANTED")
        if g24_payload.get("candidate_commit") != candidate_commit:
            errors.append("G24_COMMIT_MISMATCH")
        if g24_payload.get("subject_tree_sha256") != subject_sha:
            errors.append("G24_SUBJECT_HASH_MISMATCH")
        if g23_envelope and g24_payload.get("g23_payload_sha256") != g23_envelope.get("payload_sha256"):
            errors.append("G24_G23_CHAIN_MISMATCH")
        if g23_envelope and g24_payload.get("g23_envelope_sha256") != digest_bytes(canonical_json(g23_envelope)):
            errors.append("G24_G23_ENVELOPE_DIGEST_MISMATCH")
        if g24_payload.get("gates_checked") != ctl.GATE_IDS_24:
            errors.append("G24_REQUIRED_GATE_SET_MISMATCH")
        if g24_payload.get("validator_id") != (g23_payload or {}).get("validator_id"):
            errors.append("G24_VALIDATOR_BINDING_MISMATCH")
        if g24_payload.get("certifier_id") in (None, "", (g23_payload or {}).get("validator_id"), (g23_payload or {}).get("producer_id")):
            errors.append("G24_IDENTITY_NOT_DISTINCT")
        if g23_envelope and g24_envelope and g23_envelope.get("signer_public_key_sha256") == g24_envelope.get("signer_public_key_sha256"):
            errors.append("G23_G24_SIGNING_KEYS_NOT_DISTINCT")
        if g24_payload.get("canonical_authority_transfer") is not False or g24_payload.get("certification_propagation") is not False:
            errors.append("FORBIDDEN_CERTIFICATION_PROPAGATION")
    final_scan = ctl.scan_tree(root)
    if final_scan["total_bytes"] > ctl.CAP_BYTES:
        errors.append("FINAL_TREE_BYTES_OVER_CAP_AFTER_CERTIFICATES")
    return {
        "schema": "CAJITA_PUAC2_RELEASE_VERIFICATION/1.0",
        "decision": "PASS" if not errors else "HOLD",
        "certification_status": "CERTIFIED_FOR_EXACT_CAJA_SCOPE" if not errors else "NOT_GRANTED",
        "scope": "CAJITA_DE_LUNA_EXACT_TREE_NOT_LOUKSNA_CANONICAL_PROMOTION",
        "candidate_commit": candidate_commit,
        "candidate_tree_sha256": subject_sha,
        "final_tree_bytes": final_scan["total_bytes"],
        "hard_cap_bytes": ctl.CAP_BYTES,
        "hashed_file_count": hashed_files,
        "hashed_payload_bytes": hashed_bytes,
        "g23_independent_validation": "PASS_VERIFIED" if not errors else "NOT_VERIFIED",
        "g24_certification": "PASS_VERIFIED" if not errors else "NOT_ISSUED_OR_INVALID",
        "canonical_authority_transfer": False,
        "certification_propagation": False,
        "blockers": sorted(set(errors)),
        "measured_at_utc": utc_now(),
    }


def write_exclusive(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def write_json_exclusive(path: Path, value: dict[str, Any]) -> str:
    raw = (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    write_exclusive(path, raw)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    write_exclusive(sidecar, f"{digest_bytes(raw)}  {path.name}\n".encode("utf-8"))
    return digest_bytes(raw)


def persist_bundle(root: Path, g23_path: Path, g24_path: Path, run_id: str,
                   candidate_commit: str, producer_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,80}", run_id):
        raise ValueError("RUN_ID_INVALID")
    if not COMMIT_RE.fullmatch(candidate_commit):
        raise ValueError("CANDIDATE_COMMIT_INVALID")
    root = root.resolve(strict=True)
    inventory_before = ctl.scan_tree(root)
    if inventory_before["total_bytes"] + ctl.MIN_EVIDENCE_RESERVE_BYTES > ctl.CAP_BYTES:
        raise ValueError("PERSISTENCE_BLOCKED_TREE_PLUS_EVIDENCE_RESERVE_EXCEEDS_CAP")
    if inventory_before["symlinks"] or inventory_before["hardlink_groups"] or inventory_before["non_regular"] or inventory_before["scan_errors"]:
        raise ValueError("PERSISTENCE_BLOCKED_UNSAFE_TREE_ENTRIES")
    g23_envelope = load_object(g23_path)
    g24_envelope = load_object(g24_path)
    if g23_envelope.get("schema") != G23_ENVELOPE_SCHEMA or g24_envelope.get("schema") != G24_ENVELOPE_SCHEMA:
        raise ValueError("PERSISTENCE_BLOCKED_RECEIPT_SCHEMA_MISMATCH")
    g23_payload = g23_envelope.get("payload")
    g24_payload = g24_envelope.get("payload")
    if not isinstance(g23_payload, dict) or not isinstance(g24_payload, dict):
        raise ValueError("PERSISTENCE_BLOCKED_RECEIPT_PAYLOAD_MISSING")
    if g23_payload.get("candidate_commit") != candidate_commit or g24_payload.get("candidate_commit") != candidate_commit:
        raise ValueError("PERSISTENCE_BLOCKED_CANDIDATE_MISMATCH")
    if g23_payload.get("producer_id") != producer_id or g24_payload.get("producer_id") != producer_id:
        raise ValueError("PERSISTENCE_BLOCKED_PRODUCER_MISMATCH")
    if g24_payload.get("g23_payload_sha256") != g23_envelope.get("payload_sha256"):
        raise ValueError("PERSISTENCE_BLOCKED_G23_G24_CHAIN_MISMATCH")
    evidence_dir = root / ".cajita-optimization-candidates" / "evidence"
    if evidence_dir.is_symlink():
        raise ValueError("PERSISTENCE_BLOCKED_EVIDENCE_PATH_SYMLINK")
    stamp = re.sub(r"[^A-Za-z0-9._-]", "_", run_id)
    g23_dest = evidence_dir / f"CAJITA_G23_{stamp}.json"
    g24_dest = evidence_dir / f"CAJITA_G24_{stamp}.json"
    manifest_dest = evidence_dir / f"cajita-certification-manifest-{stamp}.json"
    report_dest = evidence_dir / f"cajita-release-verification-{stamp}.json"
    for target in (g23_dest, g24_dest, manifest_dest, report_dest):
        if target.exists() or target.is_symlink():
            raise ValueError("PERSISTENCE_APPEND_ONLY_TARGET_EXISTS:" + target.name)
    generated_paths = sorted(
        [path.relative_to(root).as_posix() for path in (g23_dest, g24_dest, manifest_dest, report_dest)]
        + [path.with_suffix(path.suffix + ".sha256").relative_to(root).as_posix()
           for path in (g23_dest, g24_dest, manifest_dest, report_dest)]
    )
    # The 1 MiB reserve must cover the entire set of signed receipts, manifests,
    # sidecars and decision reports. Precompute exact serialized sizes before writes.
    manifest = {
        "schema": "CAJITA_PUAC2_CERTIFICATION_MANIFEST/1.0",
        "candidate_commit": candidate_commit,
        "submitter_id": producer_id,
        "scope": "CAJITA_DE_LUNA_EXACT_TREE",
        "evidence": {
            "output_sha256": g23_payload.get("subject_tree_sha256"),
            "subject_tree_sha256": g23_payload.get("subject_tree_sha256"),
            "g23_receipt_sha256": digest_bytes(canonical_json(g23_envelope)),
            "g24_receipt_sha256": digest_bytes(canonical_json(g24_envelope)),
        },
        "g23": g23_envelope,
        "g24": g24_envelope,
        "run_id": stamp,
        "generated_evidence_paths": generated_paths,
        "subject_excluded_paths": generated_paths,
        "persisted_at_utc": utc_now(),
        "canonical_authority_transfer": False,
        "certification_propagation": False,
    }
    serialized = [
        (g23_dest, (json.dumps(g23_envelope, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
        (g24_dest, (json.dumps(g24_envelope, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
        (manifest_dest, (json.dumps(manifest, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")),
    ]
    sidecar_bytes = sum(len(f"{digest_bytes(raw)}  {path.name}\n".encode("utf-8")) for path, raw in serialized)
    planned_receipt_bytes = sum(len(raw) for _, raw in serialized) + sidecar_bytes
    if planned_receipt_bytes + 64 * 1024 > ctl.MIN_EVIDENCE_RESERVE_BYTES:
        raise ValueError("PERSISTENCE_BUNDLE_EXCEEDS_RESERVED_METADATA_BUDGET")
    # Append-only commits: every write is exclusive and fsynced. If any step fails,
    # the partial receipts remain as evidence and release stays blocked; nothing is overwritten.
    for path, raw in serialized:
        write_exclusive(path, raw)
        write_exclusive(path.with_suffix(path.suffix + ".sha256"),
                        f"{digest_bytes(raw)}  {path.name}\n".encode("utf-8"))
    # Verify stored bytes and cryptographic chain before writing the final decision record.
    report = verify_release(root, manifest_dest, os.environ.get("CAJITA_G23_PUBLIC_KEY_PEM", ""),
                            os.environ.get("CAJITA_G24_PUBLIC_KEY_PEM", ""), candidate_commit)
    after_receipts = ctl.scan_tree(root)
    report["run_id"] = stamp
    report["manifest_path"] = manifest_dest.relative_to(root).as_posix()
    report["g23_receipt_path"] = g23_dest.relative_to(root).as_posix()
    report["g24_receipt_path"] = g24_dest.relative_to(root).as_posix()
    report["tree_bytes_before_decision_report"] = after_receipts["total_bytes"]
    report["decision_report_path"] = report_dest.relative_to(root).as_posix()
    report["decision_report_sidecar_path"] = report_dest.with_suffix(".json.sha256").relative_to(root).as_posix()
    # Solve the finite size fixed point so the receipt accounts for itself and its sidecar.
    predicted_total = after_receipts["total_bytes"]
    sidecar_len = len(f"{'0' * 64}  {report_dest.name}\n".encode("utf-8"))
    for _ in range(12):
        report["final_tree_bytes_including_this_report_and_sidecar"] = predicted_total
        raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        new_total = after_receipts["total_bytes"] + len(raw) + sidecar_len
        if new_total == predicted_total:
            break
        predicted_total = new_total
    else:
        raise ValueError("FINAL_REPORT_SIZE_FIXED_POINT_DID_NOT_CONVERGE")
    if predicted_total > ctl.CAP_BYTES:
        report["decision"] = "HOLD"
        report["certification_status"] = "NOT_GRANTED"
        report["blockers"] = sorted(set(report.get("blockers", []) + ["FINAL_TREE_WITH_DECISION_REPORT_EXCEEDS_CAP"]))
        report["final_tree_bytes_including_this_report_and_sidecar"] = predicted_total
        raw = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    write_exclusive(report_dest, raw)
    write_exclusive(report_dest.with_suffix(".json.sha256"),
                    f"{digest_bytes(raw)}  {report_dest.name}\n".encode("utf-8"))
    observed_total = ctl.scan_tree(root)["total_bytes"]
    report["observed_final_tree_bytes_after_persistence"] = observed_total
    report["predicted_final_tree_bytes_match"] = observed_total == predicted_total
    # The signed certificate/receipts bind the payload tree (excluding the evidence
    # ledger); this post-write scan binds every receipt and sidecar to the exact cap.
    final_decision = verify_release(root, manifest_dest, os.environ.get("CAJITA_G23_PUBLIC_KEY_PEM", ""),
                                    os.environ.get("CAJITA_G24_PUBLIC_KEY_PEM", ""), candidate_commit)
    report["post_persistence_reverification"] = final_decision
    report["status"] = "PASS" if (
        report.get("decision") == "PASS" and
        final_decision.get("decision") == "PASS" and
        observed_total == predicted_total and observed_total <= ctl.CAP_BYTES
    ) else "HOLD"
    report["certification_status"] = "CERTIFIED_FOR_EXACT_CAJA_SCOPE" if report["status"] == "PASS" else "NOT_GRANTED"
    # The immutable decision report was written before the second check and therefore
    # records the pre-report check plus exact predicted bytes. Reverification is returned
    # to the caller and workflow artifact; any discrepancy makes the workflow fail.
    return {
        "schema": "CAJITA_PUAC2_PERSIST_BUNDLE/1.0",
        "decision": report["status"],
        "certification_status": report["certification_status"],
        "final_tree_bytes": observed_total,
        "hard_cap_bytes": ctl.CAP_BYTES,
        "predicted_final_tree_bytes": predicted_total,
        "predicted_exact_match": observed_total == predicted_total,
        "manifest_path": manifest_dest.relative_to(root).as_posix(),
        "decision_report_path": report_dest.relative_to(root).as_posix(),
        "post_persistence_reverification": final_decision,
        "blockers": report.get("blockers", []),
    }


def dispatch_g23_g24(root: Path, candidate_commit: str, expected_subject_sha256: str,
                     repo: str, workflow: str, ref: str) -> dict[str, Any]:
    if not COMMIT_RE.fullmatch(candidate_commit):
        return {"decision": "HOLD", "blockers": ["CANDIDATE_COMMIT_INVALID"], "dispatched": False}
    if not ctl.is_sha256(expected_subject_sha256):
        return {"decision": "HOLD", "blockers": ["EXPECTED_SUBJECT_SHA256_INVALID"], "dispatched": False}
    evidence = final_evidence(root.resolve(strict=True))
    if evidence.get("status") != "PASS" or evidence.get("blockers"):
        return {
            "decision": "HOLD", "dispatched": False,
            "subject_tree_sha256": evidence.get("subject_tree_sha256"),
            "tree_bytes": evidence.get("tree_bytes_at_validation"),
            "blockers": evidence.get("blockers", []) + ["CERTIFICATION_DISPATCH_DENIED_BY_G23_PREFLIGHT"],
        }
    subject, _, _ = ctl.candidate_tree_digest(root.resolve(strict=True))
    if subject != expected_subject_sha256 or evidence.get("subject_tree_sha256") != expected_subject_sha256:
        return {"decision": "HOLD", "dispatched": False, "blockers": ["DISPATCHED_SUBJECT_MISMATCH"]}
    gh = shutil.which("gh")
    if gh is None:
        return {"decision": "HOLD", "dispatched": False, "blockers": ["GITHUB_CLI_NOT_FOUND"]}
    auth = subprocess.run([gh, "auth", "status", "--hostname", "github.com"],
                          capture_output=True, text=True, timeout=20, check=False)
    if auth.returncode != 0:
        return {"decision": "HOLD", "dispatched": False, "blockers": ["GITHUB_CLI_AUTH_NOT_READY"]}
    command = [
        gh, "workflow", "run", workflow, "--repo", repo, "--ref", ref,
        "-f", f"candidate_commit={candidate_commit}",
        "-f", f"expected_subject_sha256={expected_subject_sha256}",
    ]
    proc = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    if proc.returncode != 0:
        return {"decision": "HOLD", "dispatched": False,
                "blockers": ["GITHUB_WORKFLOW_DISPATCH_FAILED"],
                "detail": (proc.stderr or proc.stdout)[-2000:]}
    return {
        "schema": "CAJITA_PUAC2_CERTIFICATION_DISPATCH/1.0",
        "decision": "DISPATCHED",
        "dispatched": True,
        "workflow": workflow,
        "repo": repo,
        "ref": ref,
        "candidate_commit": candidate_commit,
        "subject_tree_sha256": subject,
        "tree_bytes_at_dispatch": evidence.get("tree_bytes_at_validation"),
        "measured_at_utc": utc_now(),
    }

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare-g23", help="Independently inspect final Cajita evidence; emits PASS or HOLD without mutation.")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--candidate-commit", required=True)
    prep.add_argument("--expected-subject-sha256", required=True)
    prep.add_argument("--validator-id", default=os.environ.get("CAJITA_G23_VALIDATOR_ID", ""))
    prep.add_argument("--producer-id", default=os.environ.get("CAJITA_PRODUCER_ID", "CUSTOSZ_V9"))
    prep.add_argument("--output", type=Path, required=True)
    s23 = sub.add_parser("sign-g23", help="Sign an independently produced G23 report; never upgrades HOLD to PASS.")
    s23.add_argument("--input", type=Path, required=True)
    s23.add_argument("--output", type=Path, required=True)
    s23.add_argument("--validator-id", default=os.environ.get("CAJITA_G23_VALIDATOR_ID", ""))
    s23.add_argument("--producer-id", default=os.environ.get("CAJITA_PRODUCER_ID", "CUSTOSZ_V9"))
    s24 = sub.add_parser("issue-g24", help="Verify G23 and automatically issue a signed G24 decision or signed HOLD.")
    s24.add_argument("--g23", type=Path, required=True)
    s24.add_argument("--candidate-commit", required=True)
    s24.add_argument("--output", type=Path, required=True)
    s24.add_argument("--certifier-id", default=os.environ.get("CAJITA_G24_CERTIFIER_ID", ""))
    s24.add_argument("--producer-id", default=os.environ.get("CAJITA_PRODUCER_ID", "CUSTOSZ_V9"))
    s24.add_argument("--expected-subject-sha256", required=True)
    persist = sub.add_parser("persist-bundle", help="Persist signed G23/G24 receipts and verify the exact final tree.")
    persist.add_argument("--root", type=Path, required=True)
    persist.add_argument("--g23", type=Path, required=True)
    persist.add_argument("--g24", type=Path, required=True)
    persist.add_argument("--run-id", required=True)
    persist.add_argument("--candidate-commit", required=True)
    persist.add_argument("--producer-id", default=os.environ.get("CAJITA_PRODUCER_ID", "CUSTOSZ_V9"))
    dispatch = sub.add_parser("dispatch-g23-g24", help="Dispatch trusted G23/G24 only after a clean, size-feasible final preflight.")
    dispatch.add_argument("--root", type=Path, required=True)
    dispatch.add_argument("--candidate-commit", required=True)
    dispatch.add_argument("--expected-subject-sha256", required=True)
    dispatch.add_argument("--repo", default="Plomillo/luna-linux-bridge")
    dispatch.add_argument("--workflow", default=".github/workflows/cajita-luna-puac2-g23-g24.yml")
    dispatch.add_argument("--ref", default="main")
    verify = sub.add_parser("verify-release", help="Verify the final Cajita tree and signed G23/G24 receipts.")
    verify.add_argument("--root", type=Path, required=True)
    verify.add_argument("--manifest", type=Path, required=True)
    verify.add_argument("--candidate-commit", default=None)
    args = parser.parse_args(argv)
    try:
        if args.command == "prepare-g23":
            root = args.root.resolve(strict=False)
            payload = final_evidence(root)
            payload["candidate_commit"] = args.candidate_commit
            execution_path = root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json"
            if payload.get("status") == "PASS":
                try:
                    execution_manifest = load_object(execution_path)
                    if execution_manifest.get("candidate_commit") != args.candidate_commit:
                        payload["status"] = "HOLD"
                        payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_COMMIT_NOT_BOUND_TO_OPTIMIZATION_EXECUTION"]))
                except (OSError, ValueError, json.JSONDecodeError):
                    payload["status"] = "HOLD"
                    payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_OPTIMIZATION_EXECUTION_MANIFEST_INVALID"]))
            independent_path = root / INDEPENDENT_TESTS_REL
            if independent_path.is_file():
                    try:
                        independent_manifest = load_object(independent_path)
                        if independent_manifest.get("executor_id") == args.validator_id:
                            payload["status"] = "HOLD"
                            payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_IDENTITY_COLLIDES_WITH_INDEPENDENT_TESTER"]))
                    except (OSError, ValueError, json.JSONDecodeError):
                        payload["status"] = "HOLD"
                        payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_INDEPENDENT_TEST_MANIFEST_INVALID"]))
            if args.expected_subject_sha256 and payload.get("subject_tree_sha256") != args.expected_subject_sha256:
                payload["status"] = "HOLD"
                payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_DISPATCHED_SUBJECT_MISMATCH"]))
            if args.expected_subject_sha256 and not ctl.is_sha256(args.expected_subject_sha256):
                payload["status"] = "HOLD"
                payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_EXPECTED_SUBJECT_HASH_INVALID"]))
            payload["validator_id"] = args.validator_id
            payload["producer_id"] = args.producer_id
            if not COMMIT_RE.fullmatch(args.candidate_commit):
                payload["status"] = "HOLD"
                payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_CANDIDATE_COMMIT_INVALID"]))
            if not args.validator_id or args.validator_id == args.producer_id:
                payload["status"] = "HOLD"
                payload["blockers"] = sorted(set(payload.get("blockers", []) + ["G23_IDENTITY_NOT_INDEPENDENT"]))
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            print(json.dumps({"decision": payload["status"], "blockers": payload.get("blockers", [])}, sort_keys=True))
            return 0
        if args.command == "sign-g23":
            signed = sign_g23(
                args.input, args.output, os.environ.get("CAJITA_G23_SIGNING_PRIVATE_KEY_PEM", ""),
                args.validator_id, args.producer_id,
            )
            print(json.dumps({"decision": signed.get("payload", {}).get("status", "HOLD"),
                              "signed": signed.get("status") == "SIGNED"}, sort_keys=True))
            return 0
        if args.command == "issue-g24":
            envelope = issue_g24(
                args.g23, args.output, os.environ.get("CAJITA_G23_PUBLIC_KEY_PEM", ""),
                os.environ.get("CAJITA_G24_SIGNING_PRIVATE_KEY_PEM", ""),
                args.certifier_id, args.producer_id, args.candidate_commit,
                args.expected_subject_sha256,
            )
            print(json.dumps({"decision": envelope.get("payload", {}).get("status", "HOLD"),
                              "signed": envelope.get("status") == "SIGNED"}, sort_keys=True))
            return 0
        if args.command == "persist-bundle":
            report = persist_bundle(
                args.root, args.g23, args.g24, args.run_id, args.candidate_commit, args.producer_id
            )
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
            return 0 if report.get("decision") == "PASS" else 3
        if args.command == "dispatch-g23-g24":
            report = dispatch_g23_g24(
                args.root, args.candidate_commit, args.expected_subject_sha256,
                args.repo, args.workflow, args.ref
            )
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
            return 0 if report.get("decision") == "DISPATCHED" else 3
        if args.command == "verify-release":
            report = verify_release(
                args.root.resolve(strict=False), args.manifest.resolve(strict=False),
                os.environ.get("CAJITA_G23_PUBLIC_KEY_PEM", ""),
                os.environ.get("CAJITA_G24_PUBLIC_KEY_PEM", ""),
                args.candidate_commit,
            )
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
            return 0 if report.get("decision") == "PASS" else 3
    except (OSError, ValueError, RuntimeError, json.JSONDecodeError) as exc:
        print(json.dumps({"decision": "HOLD", "certification_status": "NOT_GRANTED",
                          "blockers": ["GATE_EXECUTION_ERROR:" + type(exc).__name__],
                          "detail": str(exc)}, sort_keys=True))
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
