#!/usr/bin/env python3
"""Terminal certifier: a certificate is emitted only after independently attested G23 PASS."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_ROOT_MUST_BE_OBJECT:" + str(path))
    return value


def g23_digest_is_valid(record: dict[str, Any]) -> bool:
    stated = record.get("report_sha256")
    payload = dict(record)
    payload.pop("report_sha256", None)
    return isinstance(stated, str) and SHA256_RE.fullmatch(stated) is not None and digest(canonical_bytes(payload)) == stated


def decide(g23: dict[str, Any], recheck: dict[str, Any], attestation_verification: Path, expected_g23_file_sha256: str) -> dict[str, Any]:
    failures: list[str] = []
    holds: list[str] = []
    candidate_sha = g23.get("candidate_sha")
    if not isinstance(candidate_sha, str) or not COMMIT_RE.fullmatch(candidate_sha):
        failures.append("G23_CANDIDATE_SHA_INVALID")
    if not g23_digest_is_valid(g23):
        failures.append("G23_REPORT_DIGEST_INVALID")
    if not g23_digest_is_valid(recheck):
        failures.append("G24_RECHECK_REPORT_DIGEST_INVALID")
    if g23.get("schema") != "LOUKSNA_GLOBAL_G23_RESULT/1.0":
        failures.append("G23_SCHEMA_MISMATCH")
    if recheck.get("schema") != "LOUKSNA_GLOBAL_G23_RESULT/1.0":
        failures.append("G24_RECHECK_SCHEMA_MISMATCH")
    if recheck.get("candidate_sha") != candidate_sha:
        failures.append("G23_G24_CANDIDATE_IDENTITY_MISMATCH")
    if g23.get("decision") != "PASS":
        holds.append("G23_GLOBAL_VALIDATION_NOT_PASS")
    if recheck.get("decision") != "PASS":
        holds.append("G24_INDEPENDENT_RECHECK_NOT_PASS")
    if g23.get("reason_codes") or recheck.get("reason_codes"):
        holds.append("GLOBAL_GATE_EVIDENCE_HAS_OPEN_REASONS")
    if g23.get("trusted_policy_sha256") != recheck.get("trusted_policy_sha256"):
        failures.append("TRUSTED_POLICY_DIGEST_DRIFT")
    if g23.get("trusted_matrix_sha256") != recheck.get("trusted_matrix_sha256"):
        failures.append("TRUSTED_MATRIX_DIGEST_DRIFT")
    if g23.get("protected_baseline_sha256") != recheck.get("protected_baseline_sha256"):
        failures.append("PROTECTED_BASELINE_DIGEST_DRIFT")
    if g23.get("authority_sha256") != recheck.get("authority_sha256"):
        failures.append("CANONICAL_AUTHORITY_DIGEST_DRIFT")
    if g23.get("gate_count") != 24 or recheck.get("gate_count") != 24:
        holds.append("GLOBAL_MATRIX_NOT_COMPLETE_24_GATES")
    required = [f"G{i:02d}" for i in range(1, 25)]
    for label, record in (("G23", g23), ("G24_RECHECK", recheck)):
        if record.get("required_gate_ids") != required:
            failures.append(label + "_GATE_IDENTITY_MISMATCH")
        checked = record.get("checked_evidence", [])
        checked_ids = {e.get("gate_id") for e in checked if isinstance(e, dict)}
        if checked_ids != set(required):
            holds.append(label + "_EVIDENCE_DOES_NOT_COVER_ALL_24_GATES")

    attestation_sha = None
    try:
        attestation_raw = attestation_verification.read_bytes()
        parsed = json.loads(attestation_raw.decode("utf-8"))
        if not SHA256_RE.fullmatch(expected_g23_file_sha256):
            failures.append("G23_ATTESTED_SUBJECT_SHA256_INVALID")
        verified_subject_found = False
        if isinstance(parsed, list):
            for envelope in parsed:
                if not isinstance(envelope, dict):
                    continue
                verified = envelope.get("verificationResult")
                if not isinstance(verified, dict):
                    continue
                statement = verified.get("statement")
                signature = verified.get("signature")
                certificate_data = signature.get("certificate") if isinstance(signature, dict) else None
                timestamps = verified.get("verifiedTimestamps")
                if not isinstance(statement, dict):
                    continue
                if statement.get("predicateType") != "https://slsa.dev/provenance/v1":
                    continue
                if not isinstance(certificate_data, dict) or not certificate_data:
                    continue
                if not isinstance(timestamps, list) or not timestamps:
                    continue
                subjects = statement.get("subject")
                if not isinstance(subjects, list):
                    continue
                for subject in subjects:
                    if not isinstance(subject, dict):
                        continue
                    subject_name = subject.get("name")
                    subject_digest = subject.get("digest")
                    if (
                        isinstance(subject_name, str)
                        and subject_name.rsplit("/", 1)[-1] == "G23_GLOBAL.json"
                        and isinstance(subject_digest, dict)
                        and subject_digest.get("sha256") == expected_g23_file_sha256
                    ):
                        verified_subject_found = True
                        break
                if verified_subject_found:
                    break
        if not verified_subject_found:
            holds.append("G23_ATTESTATION_VERIFICATION_INVALID_OR_SUBJECT_MISMATCH")
        else:
            attestation_sha = digest(attestation_raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        holds.append("G23_ATTESTATION_VERIFICATION_MISSING")

    status = "FAIL" if failures else ("HOLD" if holds else "PASS")
    issued_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    certificate: dict[str, Any] = {
        "schema": "LOUKSNA_GLOBAL_G24_TERMINAL_DECISION/1.0",
        "scope_id": "LOUKSNA_CANONICAL_G01_G24_TERMINAL_CERTIFICATION",
        "candidate_sha": candidate_sha,
        "decision": status,
        "certification": (
            "CERTIFIED_FOR_GLOBAL_CANONICAL_G01_G24"
            if status == "PASS"
            else "NOT_ISSUED"
        ),
        "certification_issued": status == "PASS",
        "g23_report_sha256": g23.get("report_sha256"),
        "g24_independent_recheck_sha256": recheck.get("report_sha256"),
        "g23_attestation_verification_sha256": attestation_sha,
        "trusted_policy_sha256": g23.get("trusted_policy_sha256"),
        "trusted_matrix_sha256": g23.get("trusted_matrix_sha256"),
        "protected_baseline_sha256": g23.get("protected_baseline_sha256"),
        "canonical_authority_sha256": g23.get("authority_sha256"),
        "gate_count": 24,
        "gate_ids": [f"G{i:02d}" for i in range(1, 25)],
        "reason_codes": sorted(set(failures + holds)),
        "activation_authorized": False,
        "canonical_authority_transfer": False,
        "certification_propagation": False,
        "issued_at_utc": issued_at,
    }
    certificate["decision_payload_sha256"] = digest(canonical_bytes(certificate))
    return certificate


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g23-report", required=True, type=Path)
    parser.add_argument("--recheck-report", required=True, type=Path)
    parser.add_argument("--attestation-verification", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    try:
        g23 = load_object(args.g23_report)
        recheck = load_object(args.recheck_report)
        expected_g23_file_sha256 = digest(args.g23_report.read_bytes())
        result = decide(g23, recheck, args.attestation_verification, expected_g23_file_sha256)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result = {
            "schema": "LOUKSNA_GLOBAL_G24_TERMINAL_DECISION/1.0",
            "scope_id": "LOUKSNA_CANONICAL_G01_G24_TERMINAL_CERTIFICATION",
            "decision": "FAIL",
            "certification": "NOT_ISSUED",
            "certification_issued": False,
            "reason_codes": ["CERTIFICATION_INPUT_INVALID:" + type(exc).__name__],
            "activation_authorized": False,
            "canonical_authority_transfer": False,
            "certification_propagation": False,
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": result.get("decision"),
        "certification_issued": result.get("certification_issued", False),
        "reason_codes": result.get("reason_codes", []),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
