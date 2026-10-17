#!/usr/bin/env python3
"""Fail-closed validator for the canonical Louksna G01-G24 evidence ledger.

This tool does not infer canonical gate meaning. It verifies a sourced matrix
against an exact protected baseline and exact evidence bytes. Missing canonical
inputs produce HOLD; mismatched identities or hashes produce FAIL.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

GATE_IDS = [f"G{i:02d}" for i in range(1, 25)]
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_ROOT_MUST_BE_OBJECT:" + str(path))
    return value


def safe_file(root: Path, relative: Any) -> Path | None:
    if not isinstance(relative, str) or not relative.strip():
        return None
    candidate = (root / relative).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError:
        return None
    return candidate if candidate.is_file() else None


def canonical_bytes(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate(
    candidate_root: Path,
    trusted_root: Path,
    policy_path: Path,
    matrix_path: Path,
    candidate_sha: str,
) -> dict[str, Any]:
    holds: list[str] = []
    failures: list[str] = []
    checked_evidence: list[dict[str, Any]] = []
    baseline_digest: str | None = None
    authority_digest: str | None = None

    if not COMMIT_RE.fullmatch(candidate_sha):
        failures.append("CANDIDATE_COMMIT_SHA_INVALID")

    try:
        policy = load_object(policy_path)
        matrix = load_object(matrix_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {
            "schema": "LOUKSNA_GLOBAL_G23_RESULT/1.0",
            "decision": "FAIL",
            "candidate_sha": candidate_sha,
            "reason_codes": ["POLICY_OR_MATRIX_UNREADABLE:" + type(exc).__name__],
            "checked_evidence": [],
            "issued_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }

    if policy.get("schema") != "LOUKSNA_GLOBAL_SCOPE_POLICY/1.0":
        failures.append("POLICY_SCHEMA_MISMATCH")
    if policy.get("scope_id") != "LOUKSNA_CANONICAL_G01_G24_TERMINAL_CERTIFICATION":
        failures.append("GLOBAL_SCOPE_IDENTITY_MISMATCH")
    if policy.get("canonical_gate_ids") != GATE_IDS:
        failures.append("POLICY_GATE_IDENTITY_OR_ORDER_MISMATCH")
    if matrix.get("schema") != "LOUKSNA_CANONICAL_GATE_MATRIX/1.0":
        failures.append("MATRIX_SCHEMA_MISMATCH")

    baseline_name = policy.get("protected_baseline_file")
    baseline = safe_file(candidate_root, baseline_name)
    expected_baseline_sha = policy.get("protected_baseline_sha256")
    if baseline is None:
        holds.append("PROTECTED_V25_BASELINE_ABSENT")
    else:
        baseline_digest = sha256_file(baseline)
    if not isinstance(expected_baseline_sha, str) or not SHA256_RE.fullmatch(expected_baseline_sha):
        holds.append("PROTECTED_V25_BASELINE_SHA256_NOT_PINNED")
    elif baseline_digest is not None and baseline_digest != expected_baseline_sha:
        failures.append("PROTECTED_V25_BASELINE_SHA256_MISMATCH")
    if baseline_digest is not None and matrix.get("source_sha256") != baseline_digest:
        if matrix.get("source_sha256") is None:
            holds.append("MATRIX_NOT_BOUND_TO_PROTECTED_BASELINE")
        else:
            failures.append("MATRIX_BASELINE_DIGEST_MISMATCH")

    authority_name = policy.get("authority_file")
    candidate_authority = safe_file(candidate_root, authority_name)
    trusted_authority = safe_file(trusted_root, authority_name)
    if candidate_authority is None or trusted_authority is None:
        holds.append("CANONICAL_AUTHORITY_FILE_MISSING")
    else:
        candidate_bytes = candidate_authority.read_bytes()
        trusted_bytes = trusted_authority.read_bytes()
        authority_digest = sha256_bytes(candidate_bytes)
        if candidate_bytes != trusted_bytes:
            failures.append("CANONICAL_AUTHORITY_BYTES_DIFFER_FROM_TRUSTED_MAIN")

    gates = matrix.get("gates")
    if not isinstance(gates, list):
        failures.append("MATRIX_GATES_NOT_LIST")
        gates = []
    ids = [gate.get("gate_id") if isinstance(gate, dict) else None for gate in gates]
    if ids != GATE_IDS:
        failures.append("MATRIX_MUST_CONTAIN_EXACTLY_ORDERED_G01_G24")

    for expected_id, gate in zip(GATE_IDS, gates):
        if not isinstance(gate, dict):
            holds.append(expected_id + ":GATE_ENTRY_MISSING_OR_INVALID")
            continue
        if gate.get("gate_id") != expected_id:
            failures.append(expected_id + ":GATE_IDENTITY_MISMATCH")
            continue
        criterion = gate.get("acceptance_predicate")
        source_path = gate.get("criterion_source_path")
        start = gate.get("criterion_start_line")
        end = gate.get("criterion_end_line")
        expected_criterion_sha = gate.get("criterion_sha256")
        source_file = safe_file(candidate_root, source_path)
        if (
            not isinstance(criterion, str) or not criterion.strip()
            or source_file is None
            or isinstance(start, bool) or not isinstance(start, int) or start < 1
            or isinstance(end, bool) or not isinstance(end, int) or end < start
            or not isinstance(expected_criterion_sha, str)
            or not SHA256_RE.fullmatch(expected_criterion_sha)
        ):
            holds.append(expected_id + ":CANONICAL_CRITERION_SOURCE_INCOMPLETE")
        else:
            lines = source_file.read_text(encoding="utf-8").splitlines()
            if end > len(lines):
                failures.append(expected_id + ":CRITERION_LINE_RANGE_OUT_OF_BOUNDS")
            else:
                excerpt = ("\n".join(lines[start - 1:end]) + "\n").encode("utf-8")
                actual_criterion_sha = sha256_bytes(excerpt)
                if actual_criterion_sha != expected_criterion_sha:
                    failures.append(expected_id + ":CRITERION_EXCERPT_HASH_MISMATCH")
                if source_path != baseline_name:
                    failures.append(expected_id + ":CRITERION_NOT_SOURCED_FROM_PROTECTED_BASELINE")

        if gate.get("status") != "PASS":
            holds.append(expected_id + ":GATE_STATUS_NOT_PASS")
        evidence = gate.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            holds.append(expected_id + ":REQUIRED_EVIDENCE_MISSING")
            continue
        for index, item in enumerate(evidence):
            if not isinstance(item, dict):
                holds.append(expected_id + f":EVIDENCE_{index}_INVALID")
                continue
            evidence_file = safe_file(candidate_root, item.get("path"))
            expected_evidence_sha = item.get("sha256")
            if evidence_file is None or not isinstance(expected_evidence_sha, str) or not SHA256_RE.fullmatch(expected_evidence_sha):
                holds.append(expected_id + f":EVIDENCE_{index}_UNBOUND")
                continue
            actual_evidence_sha = sha256_file(evidence_file)
            if actual_evidence_sha != expected_evidence_sha:
                failures.append(expected_id + f":EVIDENCE_{index}_HASH_MISMATCH")
                continue
            if item.get("result") != "PASS":
                holds.append(expected_id + f":EVIDENCE_{index}_NOT_PASS")
                continue
            checked_evidence.append({
                "gate_id": expected_id,
                "path": item["path"],
                "sha256": actual_evidence_sha,
                "result": "PASS",
            })

    decision = "FAIL" if failures else ("HOLD" if holds else "PASS")
    report: dict[str, Any] = {
        "schema": "LOUKSNA_GLOBAL_G23_RESULT/1.0",
        "scope_id": policy.get("scope_id"),
        "candidate_sha": candidate_sha,
        "trusted_policy_sha256": sha256_file(policy_path) if policy_path.is_file() else None,
        "trusted_matrix_sha256": sha256_file(matrix_path) if matrix_path.is_file() else None,
        "protected_baseline_file": baseline_name,
        "protected_baseline_sha256": baseline_digest,
        "authority_file": authority_name,
        "authority_sha256": authority_digest,
        "decision": decision,
        "certification_issued": False,
        "reason_codes": sorted(set(failures + holds)),
        "checked_evidence": checked_evidence,
        "gate_count": len(gates),
        "required_gate_ids": GATE_IDS,
        "issued_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
    }
    report["report_sha256"] = sha256_bytes(canonical_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", required=True, type=Path)
    parser.add_argument("--trusted-root", required=True, type=Path)
    parser.add_argument("--policy", required=True, type=Path)
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--candidate-sha", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    report = validate(
        args.candidate_root.resolve(),
        args.trusted_root.resolve(),
        args.policy.resolve(),
        args.matrix.resolve(),
        args.candidate_sha,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "decision": report["decision"],
        "candidate_sha": report["candidate_sha"],
        "reason_codes": report["reason_codes"],
        "report_sha256": report["report_sha256"],
    }, sort_keys=True))
    # HOLD/FAIL are valid, auditable outcomes; they must not become implicit PASS.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
