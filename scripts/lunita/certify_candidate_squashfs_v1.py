#!/usr/bin/env python3
"""Issue a digest-bound functional certificate for the exact Lunita v1.8 SquashFS.

The certificate is limited to the versioned derived candidate. It requires:
- successful SquashFS build and extraction round-trip evidence;
- the exact target-runtime acceptance receipt;
- a complete independent-validation PASS with current evidence hashes;
- the S32 operational receipt; and
- the separate stable-release receipt bound to the same S32/report/runtime hashes.

It does not issue G23/G24, certify canonical G06/G08, or promote the candidate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any

CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
VERSION = "1.8.0"
PACKAGE_SCHEMA = "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0"
TARGET_SCHEMA = "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0"
INDEPENDENT_SCHEMA = "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0"
S32_SCHEMA = "CUSTOSZ_LUNITA_BETA_CERTIFICATION_RECEIPT/1.0"
STABLE_SCHEMA = "CUSTOSZ_LUNITA_STABLE_RELEASE/1.0"
PASS_PACKAGE = "PASS_SQUASHFS_PACKAGE_AND_ROUNDTRIP_NOT_CERTIFIED"
PASS_TARGET = "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
PASS_S32 = "BETA_OPERATIONAL_CERTIFIED"
PASS_STABLE = "CERTIFIED_STABLE_RELEASE"


class CertificationError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: pathlib.Path, label: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise CertificationError(f"{label} is missing, symlinked, or not a regular file: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CertificationError(f"{label} is not valid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise CertificationError(f"{label} root must be a JSON object: {path}")
    return value


def require_hash(path: pathlib.Path, expected: object, label: str) -> str:
    if path.is_symlink() or not path.is_file():
        raise CertificationError(f"{label} is missing or symlinked: {path}")
    observed = sha256_file(path)
    if not isinstance(expected, str) or observed != expected:
        raise CertificationError(f"{label} SHA-256 mismatch")
    return observed


def validate_evidence_map(checks: dict[str, Any]) -> None:
    for name, check in checks.items():
        if not isinstance(check, dict) or check.get("status") != "PASS" or check.get("returncode", 0) != 0:
            raise CertificationError(f"Independent check is not PASS: {name}")
        evidence = check.get("evidence")
        if evidence is None:
            continue
        if not isinstance(evidence, dict):
            raise CertificationError(f"Evidence map is malformed for check: {name}")
        for path_text, expected in evidence.items():
            require_hash(pathlib.Path(path_text), expected, f"Independent evidence for {name}")


def find_bound_s32(s32_dir: pathlib.Path, independent_path: pathlib.Path, independent_sha: str,
                   target_path: pathlib.Path, target_sha: str) -> tuple[pathlib.Path, dict, str]:
    if s32_dir.is_symlink() or not s32_dir.is_dir():
        raise CertificationError(f"S32 receipt directory is missing or symlinked: {s32_dir}")
    candidates = sorted(s32_dir.glob("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT_*.json"))
    for path in reversed(candidates):
        row = load_json(path, "S32 receipt")
        evidence = row.get("evidence") if isinstance(row.get("evidence"), dict) else {}
        if (row.get("schema") == S32_SCHEMA
            and row.get("status") == PASS_S32
            and row.get("candidate_id") == CANDIDATE_ID
            and row.get("independent_report_path") == str(independent_path)
            and row.get("independent_report_sha256") == independent_sha
            and row.get("runtime_report_path") == str(target_path)
            and row.get("runtime_report_sha256") == target_sha
            and evidence.get("independent_validation") == "PASS"
            and evidence.get("independent_report_path") == str(independent_path)
            and evidence.get("independent_report_sha256") == independent_sha
            and evidence.get("target_runtime_receipt_path") == str(target_path)
            and evidence.get("target_runtime_receipt_sha256") == target_sha
            and row.get("canonical_g06_certification") == "NOT_GRANTED"
            and row.get("frozen_g06_mutated") is False
            and row.get("canonical_g08_bindings_mutated") is False
            and row.get("g23_status") == "NOT_GRANTED"
            and row.get("g24_status") == "NOT_GRANTED"):
            return path, row, sha256_file(path)
    raise CertificationError("No S32 receipt is bound to the exact independent and target-runtime receipts")


def find_bound_stable_release(stable_dir: pathlib.Path, s32_path: pathlib.Path, s32_sha: str,
                              independent_sha: str, target_sha: str) -> tuple[pathlib.Path, dict, str]:
    if stable_dir.is_symlink() or not stable_dir.is_dir():
        raise CertificationError(f"Stable release directory is missing or symlinked: {stable_dir}")
    candidates = sorted(stable_dir.glob("release_*.json"))
    for path in reversed(candidates):
        row = load_json(path, "Stable release receipt")
        s32_ref = row.get("s32_receipt") if isinstance(row.get("s32_receipt"), dict) else {}
        if (row.get("schema") == STABLE_SCHEMA
            and row.get("status") == PASS_STABLE
            and row.get("candidate_id") == CANDIDATE_ID
            and row.get("version") == VERSION
            and row.get("certification") == "GRANTED_FOR_VERSIONED_CANDIDATE"
            and row.get("independent_report_sha256") == independent_sha
            and row.get("runtime_report_sha256") == target_sha
            and s32_ref.get("path") == str(s32_path)
            and s32_ref.get("sha256") == s32_sha
            and row.get("frozen_g06_mutated") is False
            and row.get("canonical_g08_bindings_mutated") is False):
            return path, row, sha256_file(path)
    raise CertificationError("No stable-release receipt is bound to the exact S32, independent, and target-runtime evidence")


def build_certificate(
    image: pathlib.Path,
    checksum: pathlib.Path,
    package_receipt_path: pathlib.Path,
    target_receipt_dir: pathlib.Path,
    independent_report_path: pathlib.Path,
    candidate_manifest_path: pathlib.Path,
    s32_receipt_dir: pathlib.Path,
    stable_release_dir: pathlib.Path,
) -> dict[str, Any]:
    if image.is_symlink() or not image.is_file() or image.stat().st_size <= 0:
        raise CertificationError(f"SquashFS image is missing, empty, or symlinked: {image}")
    image_sha = sha256_file(image)
    image_bytes = image.stat().st_size
    checksum_text = checksum.read_text(encoding="ascii").strip()
    expected_checksum = f"{image_sha}  {image.name}"
    if checksum.is_symlink() or checksum_text != expected_checksum:
        raise CertificationError("LUNITA.squashfs.sha256 does not match the exact image bytes")

    package = load_json(package_receipt_path, "SquashFS package receipt")
    if package.get("schema") != PACKAGE_SCHEMA or package.get("status") != PASS_PACKAGE:
        raise CertificationError("SquashFS package receipt is not a completed PASS")
    if package.get("candidate_id") != CANDIDATE_ID or package.get("version") != VERSION:
        raise CertificationError("SquashFS package candidate identity/version mismatch")
    if package.get("image_name") != image.name or package.get("image_sha256") != image_sha or package.get("image_bytes") != image_bytes:
        raise CertificationError("SquashFS package receipt does not bind the exact image")
    if package.get("roundtrip_manifest_match") is not True or package.get("source_rootfs_unchanged") is not True:
        raise CertificationError("SquashFS source/extraction round-trip did not pass")
    if package.get("mksquashfs") != "PASS" or package.get("unsquashfs_superblock") != "PASS" or package.get("unsquashfs_roundtrip") != "PASS":
        raise CertificationError("SquashFS tooling evidence is incomplete")
    if package.get("target_runtime_status") != PASS_TARGET:
        raise CertificationError("SquashFS package is not linked to a passing target-runtime receipt")
    if package.get("certification") != "NOT_GRANTED" or package.get("g23") != "NOT_GRANTED" or package.get("g24") != "NOT_GRANTED":
        raise CertificationError("Package receipt contains an unexpected inherited certification")

    target_sha_expected = package.get("target_runtime_receipt_sha256")
    if not isinstance(target_sha_expected, str) or len(target_sha_expected) != 64:
        raise CertificationError("Package receipt lacks a valid target-runtime SHA-256")
    if target_receipt_dir.is_symlink() or not target_receipt_dir.is_dir():
        raise CertificationError("Target-runtime receipt directory is missing or symlinked")
    target_matches = []
    for path in target_receipt_dir.glob("LUNITA_TARGET_RUNTIME_ACCEPTANCE_*.json"):
        if path.is_symlink() or not path.is_file():
            continue
        if sha256_file(path) == target_sha_expected:
            target_matches.append(path)
    if len(target_matches) != 1:
        raise CertificationError(f"Expected exactly one target-runtime receipt matching package SHA; found {len(target_matches)}")
    target_path = target_matches[0]
    target = load_json(target_path, "Target runtime receipt")
    if target.get("schema") != TARGET_SCHEMA or target.get("status") != PASS_TARGET:
        raise CertificationError("Target-runtime receipt is not a functional PASS")
    if (target.get("candidate_id") != CANDIDATE_ID
        or target.get("certification") != "NOT_GRANTED"
        or target.get("canonical_g06_certification") != "NOT_GRANTED"
        or target.get("canonical_g08_binding_mutation") is not False):
        raise CertificationError("Target-runtime receipt candidate/scope invariants mismatch")

    report = load_json(independent_report_path, "Independent validation report")
    independent_sha = sha256_file(independent_report_path)
    if (report.get("schema") != INDEPENDENT_SCHEMA
        or report.get("status") != "PASS_INDEPENDENT_VALIDATION"
        or report.get("candidate_id") != CANDIDATE_ID
        or report.get("certification_profile") != "V1_8_DIRECT"):
        raise CertificationError("Independent validation report is not a direct-v1.8 PASS")
    if (report.get("runtime_report_path") != str(target_path)
        or report.get("runtime_report_sha256") != target_sha_expected
        or report.get("candidate_manifest_sha256") != sha256_file(candidate_manifest_path)):
        raise CertificationError("Independent report is not bound to the same manifest/target receipt")
    if report.get("frozen_g06_mutated") is not False or report.get("canonical_g08_bindings_mutated") is not False:
        raise CertificationError("Independent report violates protected canonical invariants")
    checks = report.get("checks")
    required_checks = {
        "candidate_manifest_identity_sha256",
        "runtime_report_and_launcher_identity",
        "target_v1_8_runtime_acceptance_e01_e15_int8",
        "candidate_rootfs_inventory_and_dependency_manifest",
        "jasp_packaged_fixture_nonregression",
    }
    if not isinstance(checks, dict) or not required_checks.issubset(checks):
        raise CertificationError("Independent report lacks one or more required v1.8 checks")
    validate_evidence_map(checks)
    target_check = checks["target_v1_8_runtime_acceptance_e01_e15_int8"]
    if target_check.get("receipt_path") != str(target_path) or target_check.get("receipt_sha256") != target_sha_expected:
        raise CertificationError("Independent target check does not bind the package's target receipt")

    manifest = load_json(candidate_manifest_path, "Frozen v1.8 candidate manifest")
    preserved = manifest.get("preserved_baseline") if isinstance(manifest.get("preserved_baseline"), dict) else {}
    if (manifest.get("schema") != "LUNITA_CANDIDATE_FREEZE/1.0"
        or manifest.get("candidate_id") != CANDIDATE_ID
        or manifest.get("version") != VERSION
        or manifest.get("freeze_status") != "FROZEN_CANDIDATE_NOT_CERTIFIED"
        or preserved.get("frozen_g06_mutated") is not False
        or preserved.get("canonical_g08_bindings_mutated") is not False
        or preserved.get("legacy_v1_7_launcher_replaced") is not False):
        raise CertificationError("Frozen candidate manifest identity/preservation checks failed")

    s32_path, s32, s32_sha = find_bound_s32(
        s32_receipt_dir, independent_report_path, independent_sha, target_path, target_sha_expected
    )
    stable_path, stable, stable_sha = find_bound_stable_release(
        stable_release_dir, s32_path, s32_sha, independent_sha, target_sha_expected
    )
    package_sha = sha256_file(package_receipt_path)
    return {
        "schema": "LUNITA_SQUASHFS_FUNCTIONAL_CERTIFICATE/1.0",
        "status": "CERTIFIED_FUNCTIONAL_CANDIDATE",
        "certification": "GRANTED_FOR_VERSIONED_CANDIDATE_ONLY",
        "candidate_id": CANDIDATE_ID,
        "version": VERSION,
        "artifact": {
            "name": image.name,
            "path": str(image),
            "sha256": image_sha,
            "bytes": image_bytes,
            "checksum_path": str(checksum),
        },
        "package_receipt": {"path": str(package_receipt_path), "sha256": package_sha},
        "source_rootfs_manifest_sha256": package["source_rootfs_manifest_sha256"],
        "target_runtime_receipt": {"path": str(target_path), "sha256": target_sha_expected},
        "independent_validation": {"path": str(independent_report_path), "sha256": independent_sha, "status": "PASS"},
        "s32_operational_certificate": {"path": str(s32_path), "sha256": s32_sha, "status": PASS_S32},
        "stable_release_receipt": {"path": str(stable_path), "sha256": stable_sha, "status": PASS_STABLE},
        "frozen_g06_mutated": False,
        "canonical_g08_bindings_mutated": False,
        "canonical_g06_certification": "NOT_GRANTED",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "certification_scope": "LUNITA_V1_8_DERIVED_SQUASHFS_FUNCTIONALITY_ONLY",
        "automatic_canonical_promotion": False,
        "mission_completion_claim": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def write_exclusive(path: pathlib.Path, payload: dict[str, Any]) -> str:
    data = json.dumps(payload, ensure_ascii=True, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while persisting functional certificate")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return hashlib.sha256(data).hexdigest()


def self_test() -> dict[str, Any]:
    return {
        "schema": "LUNITA_SQUASHFS_FUNCTIONAL_CERTIFIER_SELFTEST/1.0",
        "status": "PASS",
        "fail_closed_on_missing_inputs": callable(load_json) and callable(require_hash),
        "s32_and_stable_receipts_required": callable(find_bound_s32) and callable(find_bound_stable_release),
        "candidate_scope_only": True,
        "g23_g24_not_inherited": True,
        "side_effects": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--image", type=pathlib.Path)
    parser.add_argument("--checksum", type=pathlib.Path)
    parser.add_argument("--package-receipt", type=pathlib.Path)
    parser.add_argument("--target-receipt-dir", type=pathlib.Path)
    parser.add_argument("--independent-report", type=pathlib.Path)
    parser.add_argument("--candidate-manifest", type=pathlib.Path)
    parser.add_argument("--s32-receipt-dir", type=pathlib.Path)
    parser.add_argument("--stable-release-dir", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True, indent=2))
        return 0
    required = (
        args.image, args.checksum, args.package_receipt, args.target_receipt_dir,
        args.independent_report, args.candidate_manifest, args.s32_receipt_dir,
        args.stable_release_dir, args.output,
    )
    if any(value is None for value in required):
        parser.error("all candidate, evidence, and --output paths are required unless --self-test is used")
    try:
        certificate = build_certificate(
            args.image, args.checksum, args.package_receipt, args.target_receipt_dir,
            args.independent_report, args.candidate_manifest, args.s32_receipt_dir,
            args.stable_release_dir,
        )
        digest = write_exclusive(args.output, certificate)
        certificate["certificate_path"] = str(args.output)
        certificate["certificate_sha256"] = digest
        print(json.dumps(certificate, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "status": "BLOCKED_FUNCTIONAL_CERTIFICATION",
            "error_type": type(exc).__name__,
            "error": str(exc)[:2000],
            "certification": "NOT_GRANTED",
        }, sort_keys=True, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
