#!/usr/bin/env python3
"""PUAC-2 fail-closed gate for mTLS evidence, G23 independent validation and G24 certification.

This program orchestrates evidence checks. It does not create credentials, run host
provisioning, impersonate an independent validator, or grant certification by itself.
"""
from __future__ import annotations
import argparse
import base64
import json
import hashlib
import os
import sys
from pathlib import Path

REQUIRED_EVIDENCE = (
    "source_ref", "candidate_commit", "input_sha256", "output_sha256",
    "test_report_ref", "test_report_sha256", "host_mtls_test_ref",
    "host_mtls_test_sha256", "rollback_ref", "rollback_test_sha256",
)
HEX = set("0123456789abcdef")


def sha256_hex(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in HEX for c in value)


def canonical_bytes(value: dict) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def verify_ed25519(public_pem: str, signed_payload: dict, signature_b64: str) -> bool:
    try:
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
        key = serialization.load_pem_public_key(public_pem.encode())
        if not isinstance(key, Ed25519PublicKey):
            return False
        key.verify(base64.b64decode(signature_b64, validate=True), canonical_bytes(signed_payload))
        return True
    except Exception:
        return False


def validate(m: dict, g23_pem: str, g24_pem: str) -> tuple[int, list[str]]:
    errors: list[str] = []
    if m.get("schema") != "PUAC2_MTLS_CERTIFICATION/1.0":
        errors.append("SCHEMA_INVALID")
    if m.get("candidate_commit") != os.environ.get("GITHUB_SHA", m.get("candidate_commit")):
        errors.append("CANDIDATE_COMMIT_MISMATCH")
    if not isinstance(m.get("candidate_commit"), str) or len(m["candidate_commit"]) != 40:
        errors.append("CANDIDATE_COMMIT_INVALID")

    evidence = m.get("evidence")
    if not isinstance(evidence, dict):
        errors.append("EVIDENCE_OBJECT_MISSING")
        evidence = {}
    for field in REQUIRED_EVIDENCE:
        if not isinstance(evidence.get(field), str) or not evidence[field].strip():
            errors.append("EVIDENCE_MISSING:" + field)
    if evidence.get("candidate_commit") != m.get("candidate_commit"):
        errors.append("EVIDENCE_CANDIDATE_MISMATCH")
    for field in ("input_sha256", "output_sha256", "test_report_sha256",
                  "host_mtls_test_sha256", "rollback_test_sha256"):
        if field in evidence and not sha256_hex(evidence[field]):
            errors.append("HASH_INVALID:" + field)

    tests = m.get("tests")
    if not isinstance(tests, dict) or tests.get("status") != "PASS" or tests.get("failed") != 0 or not isinstance(tests.get("passed"), int) or tests["passed"] < 1:
        errors.append("TESTS_NOT_PROVEN_PASS")

    g23 = m.get("g23")
    if not isinstance(g23, dict):
        errors.append("G23_ATTESTATION_MISSING")
        g23 = {}
    if not g23_pem:
        errors.append("G23_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED")
    if g23.get("status") != "PASS":
        errors.append("G23_NOT_PASS")
    if g23.get("validator_id") in (None, "", m.get("submitter_id")):
        errors.append("G23_VALIDATOR_NOT_INDEPENDENT")
    if g23.get("candidate_commit") != m.get("candidate_commit"):
        errors.append("G23_CANDIDATE_MISMATCH")
    g23_payload = {k: g23.get(k) for k in ("schema", "status", "validator_id", "candidate_commit", "evidence_bundle_sha256", "decision_utc")}
    if not sha256_hex(g23_payload.get("evidence_bundle_sha256")):
        errors.append("G23_EVIDENCE_BUNDLE_HASH_INVALID")
    expected_bundle_hash = hashlib.sha256(canonical_bytes({
        "candidate_commit": m.get("candidate_commit"),
        "evidence": evidence,
        "tests": tests,
    })).hexdigest()
    if g23_payload.get("evidence_bundle_sha256") != expected_bundle_hash:
        errors.append("G23_EVIDENCE_BUNDLE_BINDING_MISMATCH")
    expected_g23_attestation_hash = hashlib.sha256(canonical_bytes(g23_payload)).hexdigest()
    if g23.get("attestation_sha256") != expected_g23_attestation_hash:
        errors.append("G23_ATTESTATION_HASH_MISMATCH")
    if not g23_pem or not isinstance(g23.get("signature_b64"), str) or not verify_ed25519(g23_pem, g23_payload, g23["signature_b64"]):
        errors.append("G23_SIGNATURE_INVALID")

    g24 = m.get("g24")
    if not isinstance(g24, dict):
        errors.append("G24_ATTESTATION_MISSING")
        g24 = {}
    if not g24_pem:
        errors.append("G24_TRUSTED_PUBLIC_KEY_NOT_CONFIGURED")
    if g24.get("status") != "CERTIFIED":
        errors.append("G24_NOT_CERTIFIED")
    if g24.get("certifier_id") in (None, "", m.get("submitter_id"), g23.get("validator_id")):
        errors.append("G24_AUTHORITY_NOT_DISTINCT")
    if g24.get("candidate_commit") != m.get("candidate_commit"):
        errors.append("G24_CANDIDATE_MISMATCH")
    if g24.get("g23_attestation_sha256") != g23.get("attestation_sha256"):
        errors.append("G24_G23_CHAIN_MISMATCH")
    g24_payload = {k: g24.get(k) for k in ("schema", "status", "certifier_id", "candidate_commit", "g23_attestation_sha256", "decision_utc")}
    if not sha256_hex(g24_payload.get("g23_attestation_sha256")):
        errors.append("G24_G23_ATTESTATION_HASH_INVALID")
    if not g24_pem or not isinstance(g24.get("signature_b64"), str) or not verify_ed25519(g24_pem, g24_payload, g24["signature_b64"]):
        errors.append("G24_SIGNATURE_INVALID")

    if errors:
        return 3, sorted(set(errors))
    return 0, ["PUAC2_CHAIN_VERIFIED", "G23_INDEPENDENT_VALIDATION_VERIFIED", "G24_CERTIFICATION_SIGNATURE_VERIFIED"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", default="evidence/mtls-certification.json")
    args = parser.parse_args()
    try:
        manifest = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"decision": "HOLD", "reason": "MANIFEST_UNREADABLE", "detail": str(exc)}))
        return 3
    code, reasons = validate(
        manifest,
        os.environ.get("PUAC2_G23_PUBLIC_KEY_PEM", ""),
        os.environ.get("PUAC2_G24_PUBLIC_KEY_PEM", ""),
    )
    print(json.dumps({
        "decision": "CERTIFICATION_CHAIN_VERIFIED" if code == 0 else "HOLD",
        "exit_code": code,
        "candidate_commit": manifest.get("candidate_commit"),
        "reasons": reasons,
        "certification_created_by_script": False,
    }, sort_keys=True))
    return code


if __name__ == "__main__":
    sys.exit(main())
