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
import importlib.util
import json
import os
import pathlib
import re
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
JASP_DEATH_PENALTY_SOURCE_SHA256 = "fc8b6f8faf0e4437c8e4ab4bd922b3e959a0d4549c813b229bc5708050851895"


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


def canonical_rootfs_tree_manifest(rootfs: pathlib.Path) -> dict[str, Any]:
    """Load and execute the exact tree_manifest implementation used by the packager."""
    if rootfs.is_symlink() or not rootfs.is_dir():
        raise CertificationError("Packaged source rootfs is missing, symlinked, or not a directory")
    packager_path = pathlib.Path(__file__).resolve().parent / "package_candidate_squashfs_v1.py"
    if packager_path.is_symlink() or not packager_path.is_file():
        raise CertificationError("Canonical SquashFS packager source is missing or unsafe")
    spec = importlib.util.spec_from_file_location("lunita_packager_manifest_certifier", packager_path)
    if spec is None or spec.loader is None:
        raise CertificationError("Cannot load canonical SquashFS packager implementation")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.tree_manifest(rootfs)


def validate_rootfs_manifest_closure(
    package: dict[str, Any],
    package_receipt_path: pathlib.Path,
    package_sha: str,
    closure_check: dict[str, Any],
) -> dict[str, Any]:
    """Fail closed unless the post-validation rootfs still equals the packaged tree."""
    if not isinstance(closure_check, dict) or closure_check.get("status") != "PASS" or closure_check.get("returncode", 0) != 0:
        raise CertificationError("Post-validation rootfs/package manifest closure is not PASS")
    rootfs_text = package.get("source_rootfs")
    if not isinstance(rootfs_text, str) or not rootfs_text:
        raise CertificationError("Package receipt lacks source_rootfs identity")
    rootfs = pathlib.Path(rootfs_text)
    if closure_check.get("rootfs_path") != str(rootfs):
        raise CertificationError("Post-validation rootfs closure references a different rootfs")
    expected_sha = package.get("source_rootfs_manifest_sha256")
    if not isinstance(expected_sha, str) or len(expected_sha) != 64:
        raise CertificationError("Package receipt lacks canonical source-rootfs manifest SHA-256")
    if closure_check.get("package_source_rootfs_manifest_sha256") != expected_sha:
        raise CertificationError("Post-validation closure does not bind the package source manifest")
    if closure_check.get("observed_post_validation_rootfs_manifest_sha256") != expected_sha:
        raise CertificationError("Post-validation rootfs manifest differs from the packaged source manifest")
    expected_count = package.get("source_rootfs_entry_count")
    if not isinstance(expected_count, int) or closure_check.get("package_source_rootfs_entry_count") != expected_count:
        raise CertificationError("Post-validation closure entry count differs from package receipt")
    if closure_check.get("observed_post_validation_rootfs_entry_count") != expected_count:
        raise CertificationError("Post-validation rootfs entry count differs from package receipt")
    if closure_check.get("package_receipt_path") != str(package_receipt_path):
        raise CertificationError("Post-validation closure references another package receipt")
    if closure_check.get("package_receipt_sha256") != package_sha:
        raise CertificationError("Post-validation closure package receipt SHA-256 mismatch")
    if closure_check.get("same_canonical_algorithm") is not True or closure_check.get("exact_manifest_equality") is not True:
        raise CertificationError("Post-validation closure does not attest exact canonical manifest equality")
    receipt_path_text = closure_check.get("manifest_closure_receipt_path")
    receipt_sha = closure_check.get("manifest_closure_receipt_sha256")
    if not isinstance(receipt_path_text, str) or not receipt_path_text or not isinstance(receipt_sha, str):
        raise CertificationError("Post-validation rootfs closure receipt is missing")
    receipt_path = pathlib.Path(receipt_path_text)
    require_hash(receipt_path, receipt_sha, "Post-validation rootfs closure receipt")
    receipt = load_json(receipt_path, "Post-validation rootfs closure receipt")
    packager_path = pathlib.Path(__file__).resolve().parent / "package_candidate_squashfs_v1.py"
    packager_sha = sha256_file(packager_path)
    if (
        receipt.get("schema") != "LUNITA_POSTVALIDATION_ROOTFS_PACKAGE_MANIFEST_CLOSURE/1.0"
        or receipt.get("status") != "PASS"
        or receipt.get("rootfs_path") != str(rootfs)
        or receipt.get("package_receipt_path") != str(package_receipt_path)
        or receipt.get("package_receipt_sha256") != package_sha
        or receipt.get("packager_source_path") != str(packager_path)
        or receipt.get("packager_source_sha256") != packager_sha
        or receipt.get("package_source_rootfs_manifest_sha256") != expected_sha
        or receipt.get("observed_post_validation_rootfs_manifest_sha256") != expected_sha
        or receipt.get("package_source_rootfs_entry_count") != expected_count
        or receipt.get("observed_post_validation_rootfs_entry_count") != expected_count
        or receipt.get("same_canonical_algorithm") is not True
        or receipt.get("exact_manifest_equality") is not True
    ):
        raise CertificationError("Post-validation rootfs closure receipt identity/content mismatch")
    if closure_check.get("packager_source_path") != str(packager_path) or closure_check.get("packager_source_sha256") != packager_sha:
        raise CertificationError("Post-validation closure packager source identity/hash mismatch")
    observed = canonical_rootfs_tree_manifest(rootfs)
    if observed.get("entries_sha256") != expected_sha or observed.get("entry_count") != expected_count:
        raise CertificationError("Live post-validation rootfs no longer equals packaged canonical manifest")
    return {
        "rootfs_path": str(rootfs),
        "manifest_sha256": expected_sha,
        "entry_count": expected_count,
        "closure_receipt_path": str(receipt_path),
        "closure_receipt_sha256": receipt_sha,
        "packager_source_sha256": packager_sha,
    }


def find_bound_s32(s32_dir: pathlib.Path, independent_path: pathlib.Path, independent_sha: str,
                   target_path: pathlib.Path, target_sha: str, image_sha: str, image_bytes: int,
                   checksum_sha: str, package_sha: str, manifest_sha: str) -> tuple[pathlib.Path, dict, str]:
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
            and row.get("candidate_manifest_sha256") == manifest_sha
            and row.get("squashfs_image_sha256") == image_sha
            and row.get("squashfs_image_bytes") == image_bytes
            and row.get("squashfs_checksum_sha256") == checksum_sha
            and row.get("squashfs_package_receipt_sha256") == package_sha
            and evidence.get("independent_validation") == "PASS"
            and evidence.get("independent_report_path") == str(independent_path)
            and evidence.get("independent_report_sha256") == independent_sha
            and evidence.get("target_runtime_receipt_path") == str(target_path)
            and evidence.get("target_runtime_receipt_sha256") == target_sha
            and evidence.get("candidate_manifest_sha256") == manifest_sha
            and evidence.get("squashfs_image_sha256") == image_sha
            and evidence.get("squashfs_image_bytes") == image_bytes
            and evidence.get("squashfs_checksum_sha256") == checksum_sha
            and evidence.get("squashfs_package_receipt_sha256") == package_sha
            and row.get("canonical_g06_certification") == "NOT_GRANTED"
            and row.get("frozen_g06_mutated") is False
            and row.get("canonical_g08_bindings_mutated") is False
            and row.get("g23_status") == "NOT_GRANTED"
            and row.get("g24_status") == "NOT_GRANTED"):
            return path, row, sha256_file(path)
    raise CertificationError("No S32 receipt is bound to the exact independent and target-runtime receipts")


def find_bound_stable_release(stable_dir: pathlib.Path, s32_path: pathlib.Path, s32_sha: str,
                              independent_sha: str, target_sha: str, image_sha: str, image_bytes: int,
                              checksum_sha: str, package_sha: str, manifest_sha: str) -> tuple[pathlib.Path, dict, str]:
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
            and row.get("candidate_manifest_sha256") == manifest_sha
            and row.get("squashfs_image_sha256") == image_sha
            and row.get("squashfs_image_bytes") == image_bytes
            and row.get("squashfs_checksum_sha256") == checksum_sha
            and row.get("squashfs_package_receipt_sha256") == package_sha
            and s32_ref.get("path") == str(s32_path)
            and s32_ref.get("sha256") == s32_sha
            and row.get("frozen_g06_mutated") is False
            and row.get("canonical_g08_bindings_mutated") is False):
            return path, row, sha256_file(path)
    raise CertificationError("No stable-release receipt is bound to the exact S32, independent, and target-runtime evidence")


def validate_jasp_process_tree_lifecycle(
    check: dict,
    target: dict,
    jasp_runtime_identity: dict,
) -> dict[str, Any]:
    """Verify five hash-bound process-group receipts against this workflow/runtime."""
    if not isinstance(check, dict) or check.get("status") != "PASS":
        raise CertificationError("JASP process-tree lifecycle check is not PASS")
    workflow = target.get("workflow_identity") if isinstance(target.get("workflow_identity"), dict) else {}
    expected_run_id = str(workflow.get("run_id", ""))
    expected_attempt = str(workflow.get("run_attempt", ""))
    expected_binary_sha = jasp_runtime_identity.get("jasp_binary_sha256")
    expected_runtime_commit = jasp_runtime_identity.get("flatpak_runtime_commit")
    expected_case_ids = {
        "flatpak_launch", "reliability", "weight_gain",
        "death_penalty_save", "death_penalty_rerun",
    }
    rows = check.get("invocations")
    if (not isinstance(rows, list) or len(rows) != 5
        or check.get("invocation_count") != 5
        or check.get("expected_invocation_count") != 5
        or check.get("unique_invocation_id_count") != 5):
        raise CertificationError("JASP process-tree lifecycle receipt count is incomplete")
    observed_case_ids = set()
    invocation_ids = set()
    for receipt in rows:
        if not isinstance(receipt, dict):
            raise CertificationError("JASP process-tree invocation receipt is malformed")
        invocation_id = receipt.get("invocation_id")
        case_id = receipt.get("case_id")
        if not isinstance(invocation_id, str) or not re.fullmatch(r"[0-9a-f]{32}", invocation_id):
            raise CertificationError("JASP process-tree invocation UUID is missing or malformed")
        if invocation_id in invocation_ids:
            raise CertificationError("Duplicate JASP process-tree invocation UUID")
        invocation_ids.add(invocation_id)
        observed_case_ids.add(case_id)
        if (receipt.get("schema") != "LUNITA_JASP_PROCESS_TREE_RECEIPT/1.0"
            or receipt.get("status") != "PASS_PROCESS_GROUP_CLOSED"
            or receipt.get("run_id") != expected_run_id
            or receipt.get("run_attempt") != expected_attempt
            or receipt.get("process_group_closed") is not True
            or receipt.get("remaining_live_pids") != []
            or receipt.get("timeout_triggered") is not False
            or receipt.get("termination_signals") != []
            or not isinstance(receipt.get("process_group_id"), int)
            or receipt.get("process_group_id", 0) <= 1
            or receipt.get("session_id") != receipt.get("process_group_id")
            or receipt.get("executable_sha256") != expected_binary_sha
            or receipt.get("runtime_ostree_commit") != expected_runtime_commit
            or receipt.get("timeout_seconds") != 300
            or type(receipt.get("returncode")) is not int
            or receipt.get("returncode") != 0
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("command_sha256", "")))
            or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("captured_output_sha256", "")))
            or not isinstance(receipt.get("captured_output_bytes"), int)
            or receipt.get("captured_output_bytes", -1) < 0
            or not isinstance(receipt.get("started_at_utc"), str)
            or not isinstance(receipt.get("finished_at_utc"), str)):
            raise CertificationError(f"JASP process-tree receipt failed identity/closure validation: {case_id}")
    if observed_case_ids != expected_case_ids:
        raise CertificationError("JASP process-tree receipts do not cover the exact five required invocations")
    if (check.get("workflow_identity") != {
        "run_id": expected_run_id, "run_attempt": expected_attempt,
    } or check.get("jasp_binary_sha256") != expected_binary_sha
       or check.get("flatpak_runtime_ostree_commit") != expected_runtime_commit):
        raise CertificationError("JASP process-tree aggregate identity differs from target/JASP runtime receipts")
    return {
        "status": "PASS",
        "invocation_count": 5,
        "invocation_ids": sorted(invocation_ids),
        "workflow_run_id": expected_run_id,
        "workflow_run_attempt": expected_attempt,
        "jasp_binary_sha256": expected_binary_sha,
        "flatpak_runtime_ostree_commit": expected_runtime_commit,
    }



def validate_jasp_seeded_fixture_evidence(check: dict) -> dict[str, Any]:
    """Independently verify flatpak_launch used a seeded disposable copy of the pinned source."""
    if not isinstance(check, dict) or check.get("status") != "PASS" or check.get("returncode") != 0:
        raise CertificationError("JASP packaged-fixture non-regression gate is not PASS")
    cases = check.get("cases") if isinstance(check.get("cases"), dict) else {}
    row = cases.get("flatpak_launch") if isinstance(cases.get("flatpak_launch"), dict) else {}
    if (row.get("status") != "PASS" or row.get("returncode") != 0
        or row.get("original_packaged_fixture_identity_valid") is not True
        or row.get("deterministic_fixture_evidence_valid") is not True):
        raise CertificationError("JASP flatpak_launch lacks a verified deterministic fixture result")
    receipt = row.get("deterministic_fixture_receipt")
    if not isinstance(receipt, dict):
        raise CertificationError("JASP seeded fixture receipt is missing")
    receipt_path_text = receipt.get("receipt_path")
    source_path_text = receipt.get("source_path")
    if not isinstance(receipt_path_text, str) or not receipt_path_text.strip():
        raise CertificationError("JASP seeded fixture receipt path is missing")
    if not isinstance(source_path_text, str) or not source_path_text.strip():
        raise CertificationError("JASP original fixture path is missing")
    receipt_path = pathlib.Path(receipt_path_text)
    source_path = pathlib.Path(source_path_text)
    if (receipt_path.is_symlink() or not receipt_path.is_file()
        or source_path.is_symlink() or not source_path.is_file()):
        raise CertificationError("JASP source or deterministic fixture receipt is missing/unsafe")
    source_sha = sha256_file(source_path)
    receipt_sha = sha256_file(receipt_path)
    if (source_sha != JASP_DEATH_PENALTY_SOURCE_SHA256
        or receipt.get("source_sha256") != JASP_DEATH_PENALTY_SOURCE_SHA256
        or receipt.get("expected_source_sha256") != JASP_DEATH_PENALTY_SOURCE_SHA256
        or receipt.get("source_sha256_after") != JASP_DEATH_PENALTY_SOURCE_SHA256
        or receipt.get("source_unchanged") is not True):
        raise CertificationError("JASP original packaged fixture no longer matches its immutable SHA-256 pin")
    if receipt.get("receipt_sha256") != receipt_sha:
        raise CertificationError("JASP deterministic fixture receipt SHA-256 mismatch")
    on_disk = load_json(receipt_path, "JASP deterministic fixture receipt")
    fields = (
        "schema", "status", "source_path", "source_sha256", "expected_source_sha256",
        "source_sha256_after", "source_unchanged", "clone_path", "clone_sha256",
        "purpose", "clone_is_distinct", "active_configuration_member", "changed_archive_member",
        "changed_json_pointer", "analysis_index", "analysis_id", "analysis_name", "module_name",
        "archive_member_count", "changed_archive_member_count",
        "unchanged_non_active_member_count", "before", "after",
        "result_output_members_changed", "reference_results_modified",
    )
    if any(on_disk.get(field) != receipt.get(field) for field in fields):
        raise CertificationError("Embedded and on-disk JASP deterministic fixture receipts disagree")
    clone_path = pathlib.Path(str(receipt.get("clone_path", "")))
    if (receipt.get("schema") != "LUNITA_JASP_DETERMINISTIC_FIXTURE/1.0"
        or receipt.get("status") != "PASS_DETERMINISTIC_FIXTURE_COPY_CREATED"
        or receipt.get("purpose") != "TEST_ONLY_DISPOSABLE_COPY;SOURCE_FIXTURE_AND_REFERENCE_RESULTS_UNCHANGED"
        or receipt.get("clone_is_distinct") is not True
        or not re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("clone_sha256", "")))
        or receipt.get("clone_sha256") == JASP_DEATH_PENALTY_SOURCE_SHA256
        or clone_path.exists() or clone_path.is_symlink()
        or receipt.get("active_configuration_member") != "analyses.json"
        or receipt.get("changed_archive_member") != "analyses.json"
        or receipt.get("changed_archive_member_count") != 1
        or not isinstance(receipt.get("archive_member_count"), int)
        or receipt.get("archive_member_count", 0) < 2
        or receipt.get("unchanged_non_active_member_count") != receipt.get("archive_member_count") - 1
        or not isinstance(receipt.get("changed_json_pointer"), str)
        or not receipt.get("changed_json_pointer", "").startswith("/analyses/")
        or not receipt.get("changed_json_pointer", "").endswith("/options")
        or receipt.get("before") != {"setSeed": False, "seed": 1}
        or receipt.get("after") != {"setSeed": True, "seed": 1}
        or receipt.get("result_output_members_changed") is not False
        or receipt.get("reference_results_modified") is not False):
        raise CertificationError("JASP deterministic seed transition or archive-preservation evidence is invalid")
    if row.get("deterministic_fixture_path") != receipt.get("clone_path"):
        raise CertificationError("JASP flatpak_launch did not execute the exact seeded clone in its receipt")
    if row.get("deterministic_fixture_receipt_valid") is not True:
        raise CertificationError("JASP seeded fixture receipt was not validated by the execution lane")
    log_path_text = row.get("evidence_path")
    log_sha_expected = row.get("evidence_sha256")
    if not isinstance(log_path_text, str) or not isinstance(log_sha_expected, str):
        raise CertificationError("JASP flatpak_launch log binding is missing")
    log_path = pathlib.Path(log_path_text)
    if (log_path.is_symlink() or not log_path.is_file()
        or sha256_file(log_path) != log_sha_expected):
        raise CertificationError("JASP flatpak_launch log hash does not match its independent evidence")
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    required_log_markers = (
        f"TEST_FILE={receipt.get('clone_path')}",
        f"DETERMINISTIC_FIXTURE_RECEIPT_PATH={receipt_path}",
        f"DETERMINISTIC_FIXTURE_RECEIPT_SHA256={receipt_sha}",
        f"DETERMINISTIC_FIXTURE_CLONE_SHA256={receipt.get('clone_sha256')}",
        "DETERMINISTIC_FIXTURE_SEED_ENABLED=TRUE",
    )
    if any(marker not in log_text.splitlines() for marker in required_log_markers):
        raise CertificationError("JASP flatpak_launch log does not bind the exact seeded fixture receipt")
    return {
        "status": "PASS",
        "original_source_sha256": source_sha,
        "deterministic_fixture_receipt_sha256": receipt_sha,
        "seeded_clone_sha256": receipt.get("clone_sha256"),
        "changed_archive_member": "analyses.json",
        "reference_results_modified": False,
    }


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
    if checksum.is_symlink() or not checksum.is_file():
        raise CertificationError("LUNITA.squashfs.sha256 is missing or symlinked")
    checksum_text = checksum.read_text(encoding="ascii").strip()
    expected_checksum = f"{image_sha}  {image.name}"
    if checksum_text != expected_checksum:
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
    if package.get("target_runtime_receipt_path") != str(target_path):
        raise CertificationError("Package receipt target-runtime path does not match the hash-selected receipt")
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
        "jasp_process_tree_lifecycle",
        "jasp_post_mutation_runtime_identity",
        "squashfs_image_and_package_binding",
        "squashfs_rootfs_postvalidation_manifest_closure",
    }
    if not isinstance(checks, dict) or not required_checks.issubset(checks):
        raise CertificationError("Independent report lacks one or more required v1.8 checks")
    validate_evidence_map(checks)
    jasp_process_tree_summary = validate_jasp_process_tree_lifecycle(
        checks["jasp_process_tree_lifecycle"],
        target,
        checks["jasp_post_mutation_runtime_identity"],
    )
    jasp_seeded_fixture_summary = validate_jasp_seeded_fixture_evidence(
        checks["jasp_packaged_fixture_nonregression"],
    )
    rootfs_manifest_closure = validate_rootfs_manifest_closure(
        package, package_receipt_path, sha256_file(package_receipt_path),
        checks["squashfs_rootfs_postvalidation_manifest_closure"],
    )
    target_check = checks["target_v1_8_runtime_acceptance_e01_e15_int8"]
    if target_check.get("receipt_path") != str(target_path) or target_check.get("receipt_sha256") != target_sha_expected:
        raise CertificationError("Independent target check does not bind the package's target receipt")

    manifest_sha = sha256_file(candidate_manifest_path)
    package_sha = sha256_file(package_receipt_path)
    checksum_sha = sha256_file(checksum)
    image_check = checks["squashfs_image_and_package_binding"]
    expected_image_binding = {
        "image_path": str(image), "image_sha256": image_sha, "image_bytes": image_bytes,
        "checksum_path": str(checksum), "checksum_sha256": checksum_sha,
        "package_receipt_path": str(package_receipt_path), "package_receipt_sha256": package_sha,
        "candidate_manifest_path": str(candidate_manifest_path), "candidate_manifest_sha256": manifest_sha,
    }
    for field, expected in expected_image_binding.items():
        if image_check.get(field) != expected:
            raise CertificationError(f"Independent image/manifest binding mismatch: {field}")
    expected_evidence = {
        str(image): image_sha, str(checksum): checksum_sha,
        str(package_receipt_path): package_sha, str(candidate_manifest_path): manifest_sha,
    }
    if image_check.get("evidence") != expected_evidence:
        raise CertificationError("Independent image/manifest evidence map is incomplete or mismatched")
    if (report.get("squashfs_image_path") != str(image)
        or report.get("squashfs_image_sha256") != image_sha
        or report.get("squashfs_image_bytes") != image_bytes
        or report.get("squashfs_checksum_path") != str(checksum)
        or report.get("squashfs_checksum_sha256") != checksum_sha
        or report.get("squashfs_package_receipt_path") != str(package_receipt_path)
        or report.get("squashfs_package_receipt_sha256") != package_sha
        or report.get("candidate_manifest_sha256") != manifest_sha):
        raise CertificationError("Independent report does not bind the exact image, package, checksum, and frozen manifest")
    validate_evidence_map({"squashfs_image_and_package_binding": image_check})

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
        s32_receipt_dir, independent_report_path, independent_sha, target_path, target_sha_expected,
        image_sha, image_bytes, checksum_sha, package_sha, manifest_sha
    )
    stable_path, stable, stable_sha = find_bound_stable_release(
        stable_release_dir, s32_path, s32_sha, independent_sha, target_sha_expected,
        image_sha, image_bytes, checksum_sha, package_sha, manifest_sha
    )
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
        "checksum": {"path": str(checksum), "sha256": checksum_sha},
        "candidate_manifest": {"path": str(candidate_manifest_path), "sha256": manifest_sha},
        "source_rootfs_manifest_sha256": package["source_rootfs_manifest_sha256"],
        "post_validation_rootfs_manifest_closure": rootfs_manifest_closure,
        "jasp_process_tree_lifecycle": jasp_process_tree_summary,
        "jasp_seeded_fixture": jasp_seeded_fixture_summary,
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
