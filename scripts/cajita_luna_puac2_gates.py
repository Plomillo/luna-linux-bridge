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
    if payload.get("validator_id", payload.get("certifier_id")) != signer_id:
        raise ValueError("SIGNER_IDENTITY_PAYLOAD_MISMATCH")
    canonical = canonical_json(payload)
    signature = base64.b64encode(key.sign(canonical)).decode("ascii")
    return {
        "schema": schema,
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
    if payload.get("validator_id", payload.get("certifier_id")) != signer_id:
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
              certifier_id: str, producer_id: str, candidate_commit: str) -> dict[str, Any]:
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
    if not certifier_id or certifier_id == producer_id:
        errors.append("G24_CERTIFIER_ID_INVALID")
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
        if not isinstance(g23_payload.get("tree_bytes_at_validation"), int) or g23_payload.get("projected_tree_bytes_with_reserve", ctl.CAP_BYTES + 1) > ctl.CAP_BYTES:
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
        errors.append("FINAL_TREE_EXCEEDS_CAP")
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
    try:
        subject_sha, hashed_files, hashed_bytes = ctl.candidate_tree_digest(root)
    except (OSError, ValueError) as exc:
        subject_sha, hashed_files, hashed_bytes = None, 0, 0
        errors.append("FINAL_SUBJECT_DIGEST_FAILED:" + type(exc).__name__)
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
    if g24_payload is not None:
        if g24_payload.get("status") != "CERTIFIED" or g24_payload.get("certification_granted") is not True:
            errors.append("G24_CERTIFICATION_NOT_GRANTED")
        if g24_payload.get("candidate_commit") != candidate_commit:
            errors.append("G24_COMMIT_MISMATCH")
        if g24_payload.get("subject_tree_sha256") != subject_sha:
            errors.append("G24_SUBJECT_HASH_MISMATCH")
        if g23_envelope and g24_payload.get("g23_payload_sha256") != g23_envelope.get("payload_sha256"):
            errors.append("G24_G23_CHAIN_MISMATCH")
        if g24_payload.get("gates_checked") != ctl.GATE_IDS_24:
            errors.append("G24_REQUIRED_GATE_SET_MISMATCH")
        if g24_payload.get("validator_id") != (g23_payload or {}).get("validator_id"):
            errors.append("G24_VALIDATOR_BINDING_MISMATCH")
        if g24_payload.get("certifier_id") in (None, "", (g23_payload or {}).get("validator_id"), (g23_payload or {}).get("producer_id")):
            errors.append("G24_IDENTITY_NOT_DISTINCT")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    prep = sub.add_parser("prepare-g23", help="Independently inspect final Cajita evidence; emits PASS or HOLD without mutation.")
    prep.add_argument("--root", type=Path, required=True)
    prep.add_argument("--candidate-commit", required=True)
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
            )
            print(json.dumps({"decision": envelope.get("payload", {}).get("status", "HOLD"),
                              "signed": envelope.get("status") == "SIGNED"}, sort_keys=True))
            return 0
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
