#!/usr/bin/env python3
"""Cajita governed preflight and PUAC2 receipt verifier.

This controller does not quantize, prune, delete, move, or rewrite payload files.
CUSTOSZ V9 remains the authorized transformation executor. Decisions fail closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

CAP_BYTES = 470_000_000
MIN_EVIDENCE_RESERVE_BYTES = 1_048_576
BUFFER_BYTES = 1024 * 1024
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_DOMAINS = (
    "1. Cerebro",
    "2. Orquestación",
    "3. Transcripción",
    "4. Traductor Inteligente",
    "5. Inteligencia documental",
    "6. Sistema Inteligente",
)
EDGE_ARCHIVE_REL = (
    "2. Orquestación/Orquestador/EdgeBackup_20260907_170357_d18dac86743a/"
    "EdgeBackup_20260907_170357_d18dac86743a.7z"
)
FROZEN_MANIFEST_REL = ".cajita-optimization-candidates/FROZEN_OUTPUTS_V9.json"
RECONCILIATION_REL = "RUNTIME_CANDIDATE_V1/registry_reconciliation.json"
PLAN_REL = ".cajita-optimization-candidates/OPTIMIZATION_PLAN_V9.json"
FUNCTIONAL_REL = ".cajita-optimization-candidates/FUNCTIONAL_VALIDATION_V9.json"
GATE_MATRIX_REL = ".cajita-optimization-candidates/PUAC2_G01_G22_EVIDENCE.json"
RELEASE_MANIFEST_REL = ".cajita-optimization-candidates/evidence/puac2-certification-manifest.json"
GATE_IDS_22 = [f"G{i:02d}" for i in range(1, 23)]
GATE_IDS_24 = [f"G{i:02d}" for i in range(1, 25)]
FROZEN_SCOPES = {
    "CEREBRO": "1. Cerebro",
    "TRANSCRIPCION": "3. Transcripción",
    "TRADUCCION_GENERAL": "4. Traductor Inteligente",
    "INTELIGENCIA_DOCUMENTAL": "5. Inteligencia documental",
    "ANALISIS_AVANZADO": "6. Sistema Inteligente",
}
PENDING_COMPONENTS = {
    "orquestador": "2. Orquestación",
    "multi_interdisciplinar": "2. Orquestación",
    "confesion_eclesial_reformada": "2. Orquestación",
    "hermeneutica_hg": "4. Traductor Inteligente",
    "traduccion_lenguas_antiguas": "4. Traductor Inteligente",
    "testing": "6. Sistema Inteligente",
    "runtime_android_windows": "6. Sistema Inteligente",
    "portabilidad_base": "6. Sistema Inteligente",
    "motor_protocolar": "6. Sistema Inteligente",
    "migracion_persistencia": "6. Sistema Inteligente",
    "consola": "6. Sistema Inteligente",
    "cognitive_ci_cd": "6. Sistema Inteligente",
    "archivado_deteccion": "6. Sistema Inteligente",
    "anti_alucinaciones": "6. Sistema Inteligente",
}

HELPER_REPOSITORY = "Plomillo/luna-linux-bridge"
DOMAIN_MANIFEST_ROOT = "implementation/super1200/domains"
DOMAIN_TOOL_REPORT_REL = ".cajita-optimization-candidates/evidence/DOMAIN_TOOL_VALIDATION_V9.json"
DOMAIN_CAPABILITY_RANGES = {
    "D01": (1, 30), "D02": (31, 45), "D03": (46, 80), "D04": (81, 120),
    "D05": (121, 176), "D06": (177, 230), "D07": (231, 300), "D08": (301, 360),
    "D09": (361, 437), "D10": (438, 476), "D11": (477, 530), "D12": (531, 585),
    "D13": (586, 640), "D14": (641, 660), "D15": (661, 700), "D16": (701, 720),
    "D17": (721, 760), "D18": (761, 860), "D19": (861, 960), "D20": (961, 1000),
    "D21": (1001, 1080), "D22": (1081, 1200),
}



def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BUFFER_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: Any) -> bool:
    return isinstance(value, str) and SHA256_RE.fullmatch(value) is not None


def calculate_projected_final(total_bytes: int, current_scope_bytes: int,
                               output_upper_bytes: int, reserve_bytes: int) -> int:
    if min(total_bytes, current_scope_bytes, output_upper_bytes, reserve_bytes) < 0:
        raise ValueError("NEGATIVE_SIZE_IN_BUDGET")
    if current_scope_bytes > total_bytes:
        raise ValueError("TARGET_SCOPE_BYTES_EXCEED_TREE")
    return total_bytes - current_scope_bytes + output_upper_bytes + reserve_bytes


def read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON_ROOT_NOT_OBJECT:{path}")
    return value


def safe_relative(root: Path, value: Any) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("RELATIVE_PATH_MISSING")
    raw = Path(value)
    if raw.is_absolute() or ".." in raw.parts:
        raise ValueError(f"UNSAFE_RELATIVE_PATH:{value}")
    base = root.resolve()
    target = (root / raw).resolve(strict=False)
    if not target.is_relative_to(base):
        raise ValueError(f"PATH_ESCAPES_CAJITA:{value}")
    return root / raw


def path_bytes(path: Path) -> int:
    """Sum file and symlink-entry byte lengths under a path without following links."""
    if path.is_symlink():
        return path.lstat().st_size
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0
    total = 0
    for base, dirs, files in os.walk(path, topdown=True, followlinks=False):
        base_path = Path(base)
        for name in list(dirs):
            item = base_path / name
            if item.is_symlink():
                total += item.lstat().st_size
                dirs.remove(name)
        for name in files:
            item = base_path / name
            try:
                info = item.lstat()
            except OSError:
                continue
            if stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
                total += info.st_size
    return total


def scan_tree(root: Path) -> dict[str, Any]:
    """Deterministic path/size inventory; does not read large payload contents."""
    if not root.exists() or not root.is_dir() or root.is_symlink():
        raise ValueError("CAJITA_ROOT_MISSING_OR_NOT_A_REAL_DIRECTORY")
    entries: list[dict[str, Any]] = []
    symlinks: list[str] = []
    inode_paths: dict[tuple[int, int], list[str]] = {}
    total = 0
    regular_file_count = 0
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        for name in list(dirs):
            item = base_path / name
            rel = item.relative_to(root).as_posix()
            try:
                info = item.lstat()
            except OSError as exc:
                entries.append({"path": rel, "error": f"LSTAT:{type(exc).__name__}"})
                dirs.remove(name)
                continue
            if stat.S_ISLNK(info.st_mode):
                symlinks.append(rel)
                entries.append({"path": rel, "kind": "symlink_directory", "bytes": info.st_size})
                total += info.st_size
                dirs.remove(name)
        for name in files:
            item = base_path / name
            rel = item.relative_to(root).as_posix()
            try:
                info = item.lstat()
            except OSError as exc:
                entries.append({"path": rel, "error": f"LSTAT:{type(exc).__name__}"})
                continue
            if stat.S_ISLNK(info.st_mode):
                symlinks.append(rel)
                entries.append({"path": rel, "kind": "symlink", "bytes": info.st_size})
                total += info.st_size
                continue
            if not stat.S_ISREG(info.st_mode):
                entries.append({"path": rel, "kind": "non_regular", "mode": info.st_mode, "bytes": info.st_size})
                continue
            regular_file_count += 1
            total += info.st_size
            identity = (info.st_dev, info.st_ino)
            inode_paths.setdefault(identity, []).append(rel)
            entries.append({"path": rel, "kind": "file", "bytes": info.st_size})
    hardlinks = [paths for paths in inode_paths.values() if len(paths) > 1]
    entries.sort(key=lambda item: item["path"])
    return {
        "root": str(root.resolve()),
        "total_bytes": total,
        "regular_file_count": regular_file_count,
        "entry_count": len(entries),
        "symlinks": sorted(set(symlinks)),
        "hardlink_groups": hardlinks,
        "non_regular": [item["path"] for item in entries if item.get("kind") == "non_regular"],
        "scan_errors": [item for item in entries if "error" in item],
        "entries": entries,
    }


def available_ram_bytes() -> int | None:
    """Return currently available RAM on Linux; do not guess if unavailable."""
    meminfo = Path("/proc/meminfo")
    if meminfo.is_file():
        try:
            for line in meminfo.read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) * 1024
        except (OSError, ValueError, IndexError):
            return None
    try:
        return int(os.sysconf("SC_AVPHYS_PAGES")) * int(os.sysconf("SC_PAGE_SIZE"))
    except (ValueError, OSError, AttributeError):
        return None


def edge_evidence(root: Path) -> dict[str, Any]:
    archive = safe_relative(root, EDGE_ARCHIVE_REL)
    sidecar = archive.with_suffix(".sha256")
    audit_log = archive.with_suffix(".audit.jsonl")
    result: dict[str, Any] = {
        "archive_path": EDGE_ARCHIVE_REL,
        "archive_bytes": None,
        "sha256_observed": None,
        "sidecar_path": sidecar.relative_to(root).as_posix(),
        "sidecar_status": "MISSING",
        "audit_log_path": audit_log.relative_to(root).as_posix(),
        "audit_log_present": audit_log.is_file(),
        "profile_preservation_status": "NOT_FUNCTIONALLY_TESTED",
    }
    if not archive.is_file() or archive.is_symlink():
        result["status"] = "BLOCKED_ARCHIVE_MISSING_OR_UNSAFE"
        return result
    result["archive_bytes"] = archive.stat().st_size
    if not sidecar.is_file() or sidecar.is_symlink():
        result["status"] = "BLOCKED_SIDECAR_MISSING_OR_UNSAFE"
        return result
    try:
        sidecar_text = sidecar.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError):
        result["status"] = "BLOCKED_SIDECAR_UNREADABLE"
        return result
    match = re.search(r"\b([0-9a-fA-F]{64})\b", sidecar_text)
    if not match:
        result["status"] = "BLOCKED_SIDECAR_INVALID"
        return result
    sidecar_hash = match.group(1).lower()
    observed = sha256_file(archive)
    result["sha256_observed"] = observed
    result["sha256_sidecar"] = sidecar_hash
    result["sidecar_status"] = "PASS" if observed == sidecar_hash else "FAIL"
    result["status"] = "PASS" if observed == sidecar_hash and audit_log.is_file() else "BLOCKED"
    if observed != sidecar_hash:
        result["reason"] = "EDGE_SHA256_MISMATCH"
    elif not audit_log.is_file():
        result["reason"] = "EDGE_AUDIT_LOG_MISSING"
    return result


def registry_comparison(root: Path) -> dict[str, Any]:
    registry_path = root / "RUNTIME_CANDIDATE_V1" / "registry.json"
    result: dict[str, Any] = {
        "registry_path": "RUNTIME_CANDIDATE_V1/registry.json",
        "status": "BLOCKED",
        "artifact_count": 0,
        "declared_original_bytes": 0,
        "missing_paths": [],
        "size_mismatches": [],
        "registry_sha256": None,
    }
    if not registry_path.is_file() or registry_path.is_symlink():
        result["reason"] = "LEGACY_REGISTRY_MISSING"
        return result
    try:
        data = read_object(registry_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        result["reason"] = f"LEGACY_REGISTRY_UNREADABLE:{type(exc).__name__}"
        return result
    artifacts = data.get("artifacts")
    if not isinstance(artifacts, list):
        result["reason"] = "LEGACY_ARTIFACT_LIST_INVALID"
        return result
    result["registry_sha256"] = sha256_file(registry_path)
    result["artifact_count"] = len(artifacts)
    for item in artifacts:
        if not isinstance(item, dict):
            result["reason"] = "LEGACY_ARTIFACT_ENTRY_NOT_OBJECT"
            return result
        source_path = item.get("path")
        declared_size = item.get("size")
        if isinstance(declared_size, int) and not isinstance(declared_size, bool) and declared_size >= 0:
            result["declared_original_bytes"] += declared_size
        try:
            target = safe_relative(root, source_path)
        except ValueError:
            result["missing_paths"].append({"path": source_path, "reason": "UNSAFE_OR_MISSING_PATH"})
            continue
        if not target.exists() or target.is_symlink():
            result["missing_paths"].append({"path": source_path, "declared_size_bytes": declared_size})
            continue
        if not target.is_file():
            result["size_mismatches"].append({
                "path": source_path, "declared_size_bytes": declared_size,
                "actual_size_bytes": None, "reason": "EXPECTED_FILE_NOT_FILE",
            })
            continue
        actual_size = target.stat().st_size
        if isinstance(declared_size, int) and not isinstance(declared_size, bool) and declared_size != actual_size:
            result["size_mismatches"].append({
                "path": source_path, "declared_size_bytes": declared_size,
                "actual_size_bytes": actual_size,
            })
    result["missing_count"] = len(result["missing_paths"])
    result["size_mismatch_count"] = len(result["size_mismatches"])
    result["status"] = "PASS" if not result["missing_paths"] and not result["size_mismatches"] else "RECONCILIATION_REQUIRED"
    return result


def validate_reconciliation(root: Path, comparison: dict[str, Any]) -> list[str]:
    path = root / RECONCILIATION_REL
    if not path.is_file():
        return ["REGISTRY_RECONCILIATION_MANIFEST_MISSING"]
    try:
        manifest = read_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["REGISTRY_RECONCILIATION_MANIFEST_INVALID"]
    errors: list[str] = []
    if manifest.get("schema") != "CAJITA_V9_REGISTRY_RECONCILIATION/1.0":
        errors.append("REGISTRY_RECONCILIATION_SCHEMA_MISMATCH")
    if manifest.get("source_registry_sha256") != comparison.get("registry_sha256"):
        errors.append("REGISTRY_RECONCILIATION_SOURCE_DIGEST_MISMATCH")
    entries = manifest.get("entries")
    if not isinstance(entries, list):
        return errors + ["REGISTRY_RECONCILIATION_ENTRIES_INVALID"]
    by_source: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        if isinstance(entry, dict) and isinstance(entry.get("source_path"), str):
            by_source.setdefault(entry["source_path"], []).append(entry)
        else:
            errors.append("REGISTRY_RECONCILIATION_ENTRY_INVALID")
    issues = {
        item["path"] for item in comparison.get("missing_paths", []) if isinstance(item, dict)
    } | {
        item["path"] for item in comparison.get("size_mismatches", []) if isinstance(item, dict)
    }
    if set(by_source) != issues:
        errors.append("REGISTRY_RECONCILIATION_COVERAGE_MISMATCH")
    valid_dispositions = {"V9_REPLACED", "RESTORED", "REGENERABLE_CACHE", "NON_RESIDENT_PROVEN_UNNECESSARY"}
    for source in sorted(issues):
        rows = by_source.get(source, [])
        if len(rows) != 1:
            errors.append(f"REGISTRY_RECONCILIATION_DUPLICATE_OR_MISSING:{source}")
            continue
        row = rows[0]
        disposition = row.get("disposition")
        if disposition not in valid_dispositions:
            errors.append(f"REGISTRY_RECONCILIATION_DISPOSITION_INVALID:{source}")
        evidence_field = "v9_evidence_sha256" if disposition in {"V9_REPLACED", "RESTORED"} else "resolution_evidence_sha256"
        if not is_sha256(row.get(evidence_field)):
            errors.append(f"REGISTRY_RECONCILIATION_EVIDENCE_HASH_MISSING:{source}")
        if disposition in {"V9_REPLACED", "RESTORED"}:
            try:
                current = safe_relative(root, row.get("current_path"))
            except ValueError:
                errors.append(f"REGISTRY_RECONCILIATION_TARGET_INVALID:{source}")
                continue
            if not current.is_file() or current.is_symlink():
                errors.append(f"REGISTRY_RECONCILIATION_TARGET_MISSING:{source}")
                continue
            actual_size = current.stat().st_size
            if row.get("current_size_bytes") != actual_size:
                errors.append(f"REGISTRY_RECONCILIATION_SIZE_MISMATCH:{source}")
            if not is_sha256(row.get("current_sha256")) or sha256_file(current) != row.get("current_sha256"):
                errors.append(f"REGISTRY_RECONCILIATION_HASH_MISMATCH:{source}")
        elif disposition == "REGENERABLE_CACHE" and row.get("regeneration_test_sha256") is None:
            errors.append(f"REGISTRY_RECONCILIATION_REGENERATION_PROOF_MISSING:{source}")
        elif disposition == "NON_RESIDENT_PROVEN_UNNECESSARY" and row.get("dependency_closure_sha256") is None:
            errors.append(f"REGISTRY_RECONCILIATION_DEPENDENCY_PROOF_MISSING:{source}")
    return sorted(set(errors))


def validate_frozen_manifest(root: Path) -> list[str]:
    path = root / FROZEN_MANIFEST_REL
    if not path.is_file():
        return ["FROZEN_V9_OUTPUTS_MANIFEST_MISSING"]
    try:
        manifest = read_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["FROZEN_V9_OUTPUTS_MANIFEST_INVALID"]
    errors: list[str] = []
    if manifest.get("schema") != "CAJITA_V9_FROZEN_OUTPUTS/1.0":
        errors.append("FROZEN_V9_OUTPUTS_SCHEMA_MISMATCH")
    scope_roots = manifest.get("scope_roots")
    files = manifest.get("files")
    if not isinstance(scope_roots, dict) or not isinstance(files, list):
        return errors + ["FROZEN_V9_OUTPUTS_MANIFEST_SHAPE_INVALID"]
    if set(scope_roots) != set(FROZEN_SCOPES):
        errors.append("FROZEN_SCOPE_SET_MISMATCH")
    normalized_roots: dict[str, str] = {}
    for scope, relative in scope_roots.items():
        try:
            target = safe_relative(root, relative)
            normalized = target.relative_to(root).as_posix()
        except (ValueError, TypeError):
            errors.append(f"FROZEN_SCOPE_ROOT_INVALID:{scope}")
            continue
        parent_prefix = FROZEN_SCOPES.get(scope)
        whole_domain_scopes = {"CEREBRO", "TRANSCRIPCION", "INTELIGENCIA_DOCUMENTAL"}
        if scope in whole_domain_scopes:
            authorized = normalized == parent_prefix
        else:
            authorized = bool(parent_prefix and normalized.startswith(parent_prefix + "/"))
        if not parent_prefix or not authorized:
            errors.append(f"FROZEN_SCOPE_ROOT_OUTSIDE_AUTHORIZED_DOMAIN:{scope}")
        if not target.is_dir() or target.is_symlink():
            errors.append(f"FROZEN_SCOPE_ROOT_MISSING:{scope}")
        normalized_roots[scope] = normalized
    actual_scoped_files: dict[str, str] = {}
    for scope, rel_root in normalized_roots.items():
        folder = root / rel_root
        if not folder.is_dir():
            continue
        for base, dirs, names in os.walk(folder, followlinks=False):
            b = Path(base)
            for name in list(dirs):
                if (b / name).is_symlink():
                    errors.append(f"SYMLINK_IN_FROZEN_SCOPE:{(b / name).relative_to(root).as_posix()}")
                    dirs.remove(name)
            for name in names:
                p = b / name
                rel = p.relative_to(root).as_posix()
                if p.is_symlink() or not p.is_file():
                    errors.append(f"UNSAFE_FROZEN_FILE:{rel}")
                    continue
                if rel in actual_scoped_files:
                    errors.append(f"FROZEN_SCOPE_OVERLAP:{rel}")
                actual_scoped_files[rel] = scope
    manifested: dict[str, dict[str, Any]] = {}
    for row in files:
        if not isinstance(row, dict):
            errors.append("FROZEN_FILE_ENTRY_INVALID")
            continue
        rel = row.get("path")
        scope = row.get("scope")
        if not isinstance(rel, str) or scope not in FROZEN_SCOPES:
            errors.append("FROZEN_FILE_SCOPE_OR_PATH_INVALID")
            continue
        if rel in manifested:
            errors.append(f"FROZEN_FILE_DUPLICATED:{rel}")
        manifested[rel] = row
        if actual_scoped_files.get(rel) != scope:
            errors.append(f"FROZEN_FILE_SCOPE_COVERAGE_MISMATCH:{rel}")
        try:
            target = safe_relative(root, rel)
        except ValueError:
            errors.append(f"FROZEN_FILE_PATH_UNSAFE:{rel}")
            continue
        if not target.is_file() or target.is_symlink():
            errors.append(f"FROZEN_FILE_MISSING:{rel}")
            continue
        if row.get("size_bytes") != target.stat().st_size:
            errors.append(f"FROZEN_FILE_SIZE_MISMATCH:{rel}")
        if not is_sha256(row.get("sha256")) or sha256_file(target) != row.get("sha256"):
            errors.append(f"FROZEN_FILE_HASH_MISMATCH:{rel}")
        if not is_sha256(row.get("v9_execution_evidence_sha256")):
            errors.append(f"FROZEN_FILE_V9_EVIDENCE_MISSING:{rel}")
    if set(manifested) != set(actual_scoped_files):
        errors.append("FROZEN_FILE_INVENTORY_INCOMPLETE")
    return sorted(set(errors))



def git_show_bytes(repo_root: Path, commit_sha: str, source_path: str,
                   cache: dict[tuple[str, str], bytes]) -> bytes:
    """Read a source blob from the pinned helper-repository commit without checking it out."""
    key = (commit_sha, source_path)
    if key in cache:
        return cache[key]
    if not re.fullmatch(r"[0-9a-f]{40}", commit_sha):
        raise ValueError("HELPER_COMMIT_SHA_INVALID")
    if not isinstance(source_path, str) or not source_path or Path(source_path).is_absolute() or ".." in Path(source_path).parts:
        raise ValueError("HELPER_SOURCE_PATH_UNSAFE")
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "show", f"{commit_sha}:{source_path}"],
        capture_output=True, text=False, timeout=20, check=False,
    )
    if proc.returncode != 0:
        raise ValueError("HELPER_SOURCE_BLOB_UNAVAILABLE:" + source_path)
    cache[key] = proc.stdout
    return proc.stdout


def sha256_git_blob(repo_root: Path, commit_sha: str, source_path: str,
                    cache: dict[tuple[str, str], bytes]) -> str:
    return hashlib.sha256(git_show_bytes(repo_root, commit_sha, source_path, cache)).hexdigest()


def validate_domain_routing(root: Path, plan: dict[str, Any],
                            operations_by_component: dict[str, dict[str, Any]]) -> list[str]:
    """Require auditable routing across the 22 helper domains without packaging them into Cajita."""
    errors: list[str] = []
    routing = plan.get("domain_routing")
    if not isinstance(routing, dict):
        return ["DOMAIN_ROUTING_MANIFEST_MISSING"]
    if routing.get("schema") != "CAJITA_V9_DOMAIN_ROUTING/1.0":
        errors.append("DOMAIN_ROUTING_SCHEMA_MISMATCH")
    if routing.get("repository") != HELPER_REPOSITORY:
        errors.append("DOMAIN_ROUTING_REPOSITORY_MISMATCH")
    helper_commit = routing.get("repository_commit")
    if not isinstance(helper_commit, str) or re.fullmatch(r"[0-9a-f]{40}", helper_commit) is None:
        return sorted(set(errors + ["DOMAIN_ROUTING_HELPER_COMMIT_INVALID"]))
    report_rel = routing.get("validation_report_path")
    if report_rel != DOMAIN_TOOL_REPORT_REL:
        errors.append("DOMAIN_TOOL_VALIDATION_REPORT_PATH_MISMATCH")
    try:
        report_path = safe_relative(root, report_rel)
    except (ValueError, TypeError):
        return sorted(set(errors + ["DOMAIN_TOOL_VALIDATION_REPORT_PATH_UNSAFE"]))
    if not report_path.is_file() or report_path.is_symlink():
        return sorted(set(errors + ["DOMAIN_TOOL_VALIDATION_REPORT_MISSING"]))
    actual_report_sha = sha256_file(report_path)
    if not is_sha256(routing.get("validation_report_sha256")) or actual_report_sha != routing.get("validation_report_sha256"):
        errors.append("DOMAIN_TOOL_VALIDATION_REPORT_HASH_MISMATCH")
    try:
        validation_report = read_object(report_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return sorted(set(errors + ["DOMAIN_TOOL_VALIDATION_REPORT_INVALID_JSON"]))
    if validation_report.get("schema") != "CAJITA_DOMAIN_TOOL_VALIDATION_V9/1.0":
        errors.append("DOMAIN_TOOL_VALIDATION_SCHEMA_MISMATCH")
    if validation_report.get("repository") != HELPER_REPOSITORY or validation_report.get("repository_commit") != helper_commit:
        errors.append("DOMAIN_TOOL_VALIDATION_SOURCE_BINDING_MISMATCH")
    if validation_report.get("status") != "PASS":
        errors.append("DOMAIN_TOOL_VALIDATION_NOT_PASS")

    domain_rows = routing.get("domains")
    report_domains = validation_report.get("domains")
    expected_ids = set(DOMAIN_CAPABILITY_RANGES)
    if not isinstance(domain_rows, list) or {row.get("domain_id") for row in domain_rows if isinstance(row, dict)} != expected_ids or len(domain_rows) != len(expected_ids):
        errors.append("DOMAIN_ROUTING_MATRIX_MUST_COVER_D01_D22_EXACTLY")
        domain_rows = domain_rows if isinstance(domain_rows, list) else []
    if not isinstance(report_domains, list) or {row.get("domain_id") for row in report_domains if isinstance(row, dict)} != expected_ids or len(report_domains) != len(expected_ids):
        errors.append("DOMAIN_TOOL_VALIDATION_MUST_COVER_D01_D22_EXACTLY")
        report_domains = report_domains if isinstance(report_domains, list) else []
    by_domain = {row.get("domain_id"): row for row in domain_rows if isinstance(row, dict)}
    reports_by_domain = {row.get("domain_id"): row for row in report_domains if isinstance(row, dict)}
    route_components: dict[str, set[str]] = {domain_id: set() for domain_id in DOMAIN_CAPABILITY_RANGES}
    route_capabilities: dict[str, set[int]] = {domain_id: set() for domain_id in DOMAIN_CAPABILITY_RANGES}
    route_evidence_by_capability: dict[tuple[str, int], set[str]] = {}
    for component, op in operations_by_component.items():
        routes = op.get("domain_routes")
        if not isinstance(routes, list) or not routes:
            errors.append(f"OPTIMIZATION_DOMAIN_ROUTES_MISSING:{component}")
            continue
        seen_domains: set[str] = set()
        for route in routes:
            if not isinstance(route, dict):
                errors.append(f"OPTIMIZATION_DOMAIN_ROUTE_INVALID:{component}")
                continue
            domain_id = route.get("domain_id")
            if domain_id not in DOMAIN_CAPABILITY_RANGES:
                errors.append(f"OPTIMIZATION_DOMAIN_ID_INVALID:{component}:{domain_id}")
                continue
            if domain_id in seen_domains:
                errors.append(f"OPTIMIZATION_DOMAIN_ROUTE_DUPLICATED:{component}:{domain_id}")
            seen_domains.add(domain_id)
            cap_ids = route.get("capability_ids")
            if not isinstance(cap_ids, list) or not cap_ids:
                errors.append(f"OPTIMIZATION_DOMAIN_CAPABILITIES_MISSING:{component}:{domain_id}")
                continue
            low, high = DOMAIN_CAPABILITY_RANGES[domain_id]
            normalized: set[int] = set()
            for cap_id in cap_ids:
                if isinstance(cap_id, bool) or not isinstance(cap_id, int) or not (low <= cap_id <= high):
                    errors.append(f"OPTIMIZATION_DOMAIN_CAPABILITY_OUT_OF_RANGE:{component}:{domain_id}:{cap_id}")
                else:
                    normalized.add(cap_id)
            if len(normalized) != len(cap_ids):
                errors.append(f"OPTIMIZATION_DOMAIN_CAPABILITY_DUPLICATED:{component}:{domain_id}")
            if not isinstance(route.get("rationale"), str) or len(route["rationale"].strip()) < 12:
                errors.append(f"OPTIMIZATION_DOMAIN_ROUTE_RATIONALE_MISSING:{component}:{domain_id}")
            route_evidence = route.get("route_evidence_sha256")
            if not is_sha256(route_evidence):
                errors.append(f"OPTIMIZATION_DOMAIN_ROUTE_EVIDENCE_HASH_MISSING:{component}:{domain_id}")
            else:
                for cap_id in normalized:
                    route_evidence_by_capability.setdefault((domain_id, cap_id), set()).add(route_evidence)
            route_components[domain_id].add(component)
            route_capabilities[domain_id].update(normalized)

    repo_root = Path(__file__).resolve().parents[1]
    blob_cache: dict[tuple[str, str], bytes] = {}
    for domain_id in sorted(expected_ids):
        row = by_domain.get(domain_id)
        report_row = reports_by_domain.get(domain_id)
        low, high = DOMAIN_CAPABILITY_RANGES[domain_id]
        if not isinstance(row, dict) or not isinstance(report_row, dict):
            errors.append(f"DOMAIN_ROUTE_ROW_MISSING:{domain_id}")
            continue
        if row.get("decision") != "USED":
            errors.append(f"DOMAIN_NOT_USED_OR_NOT_JUSTIFIED:{domain_id}")
        components = row.get("routed_components")
        expected_components = sorted(route_components[domain_id])
        if not isinstance(components, list) or sorted(set(components)) != expected_components or not expected_components:
            errors.append(f"DOMAIN_ROUTED_COMPONENT_COVERAGE_MISMATCH:{domain_id}")
        cap_ids = row.get("capability_ids")
        expected_caps = sorted(route_capabilities[domain_id])
        if not isinstance(cap_ids, list) or sorted(set(cap_ids)) != expected_caps or not expected_caps:
            errors.append(f"DOMAIN_ROUTED_CAPABILITY_COVERAGE_MISMATCH:{domain_id}")
        if any(isinstance(cid, bool) or not isinstance(cid, int) or cid < low or cid > high for cid in expected_caps):
            errors.append(f"DOMAIN_CAPABILITY_RANGE_INVALID:{domain_id}")
        manifest_path = f"{DOMAIN_MANIFEST_ROOT}/{domain_id}.json"
        if row.get("domain_manifest_path") != manifest_path:
            errors.append(f"DOMAIN_MANIFEST_PATH_MISMATCH:{domain_id}")
        try:
            manifest_bytes = git_show_bytes(repo_root, helper_commit, manifest_path, blob_cache)
            manifest_sha = hashlib.sha256(manifest_bytes).hexdigest()
            if row.get("domain_manifest_sha256") != manifest_sha:
                errors.append(f"DOMAIN_MANIFEST_PINNED_HASH_MISMATCH:{domain_id}")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
        except (OSError, ValueError, UnicodeDecodeError, json.JSONDecodeError, subprocess.SubprocessError):
            errors.append(f"DOMAIN_MANIFEST_PINNED_SOURCE_UNAVAILABLE:{domain_id}")
            continue
        capabilities = manifest.get("capabilities")
        if not isinstance(capabilities, list):
            errors.append(f"DOMAIN_CAPABILITY_REGISTRY_INVALID:{domain_id}")
            continue
        cap_map = {
            item.get("capability_id"): item for item in capabilities if isinstance(item, dict)
        }
        if not set(expected_caps).issubset(set(cap_map)):
            errors.append(f"DOMAIN_CAPABILITY_NOT_IN_PINNED_MANIFEST:{domain_id}")
        test_report_rel = row.get("test_report_path")
        try:
            test_report_path = safe_relative(root, test_report_rel)
        except (ValueError, TypeError):
            errors.append(f"DOMAIN_TEST_REPORT_PATH_UNSAFE:{domain_id}")
            continue
        if not test_report_path.is_file() or test_report_path.is_symlink():
            errors.append(f"DOMAIN_TEST_REPORT_MISSING:{domain_id}")
            continue
        test_report_sha = sha256_file(test_report_path)
        if row.get("test_report_sha256") != test_report_sha or report_row.get("test_report_sha256") != test_report_sha:
            errors.append(f"DOMAIN_TEST_REPORT_HASH_MISMATCH:{domain_id}")
        if report_row.get("decision") != "USED" or report_row.get("status") != "PASS":
            errors.append(f"DOMAIN_TOOL_TEST_STATUS_NOT_PASS:{domain_id}")
        if report_row.get("test_report_path") != test_report_rel:
            errors.append(f"DOMAIN_TEST_REPORT_PATH_BINDING_MISMATCH:{domain_id}")
        try:
            test_report = read_object(test_report_path)
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append(f"DOMAIN_TEST_REPORT_INVALID_JSON:{domain_id}")
            continue
        if test_report.get("schema") != "CAJITA_DOMAIN_TEST_REPORT_V9/1.0":
            errors.append(f"DOMAIN_TEST_REPORT_SCHEMA_MISMATCH:{domain_id}")
        if test_report.get("domain_id") != domain_id or test_report.get("repository") != HELPER_REPOSITORY or test_report.get("repository_commit") != helper_commit:
            errors.append(f"DOMAIN_TEST_REPORT_SOURCE_BINDING_MISMATCH:{domain_id}")
        if test_report.get("status") != "PASS" or test_report.get("exit_code") != 0:
            errors.append(f"DOMAIN_TEST_REPORT_NOT_PASS:{domain_id}")
        report_caps = test_report.get("capabilities")
        if not isinstance(report_caps, list):
            errors.append(f"DOMAIN_TEST_REPORT_CAPABILITIES_INVALID:{domain_id}")
            continue
        report_cap_map = {
            item.get("capability_id"): item for item in report_caps if isinstance(item, dict)
        }
        if len(report_cap_map) != len(report_caps):
            errors.append(f"DOMAIN_TEST_REPORT_CAPABILITY_DUPLICATED_OR_INVALID:{domain_id}")
        if not expected_caps.issubset(set(report_cap_map)):
            errors.append(f"DOMAIN_TEST_REPORT_CAPABILITY_COVERAGE_MISMATCH:{domain_id}")
        if set(report_cap_map) != expected_caps:
            errors.append(f"DOMAIN_TEST_REPORT_CONTAINS_UNROUTED_CAPABILITIES:{domain_id}")
        for cap_id in sorted(expected_caps):
            item = cap_map.get(cap_id)
            result_row = report_cap_map.get(cap_id)
            if not isinstance(item, dict) or not isinstance(result_row, dict):
                continue
            if item.get("implementation_state") != "EVIDENCED":
                errors.append(f"DOMAIN_CAPABILITY_NOT_EVIDENCED:{domain_id}:{cap_id}")
            if result_row.get("canonical_name") != item.get("canonical_name"):
                errors.append(f"DOMAIN_CAPABILITY_NAME_MISMATCH:{domain_id}:{cap_id}")
            for key, manifest_key in (
                ("implementation_path", "implementation_artifact"),
                ("test_path", "test_artifact"),
            ):
                source_path = item.get(manifest_key)
                if not isinstance(source_path, str) or source_path.startswith("/") or ".." in Path(source_path).parts:
                    errors.append(f"DOMAIN_SOURCE_PATH_INVALID:{domain_id}:{cap_id}:{manifest_key}")
                    continue
                if result_row.get(key) != source_path:
                    errors.append(f"DOMAIN_TEST_REPORT_SOURCE_PATH_MISMATCH:{domain_id}:{cap_id}:{key}")
                    continue
                hash_key = "implementation_sha256" if key == "implementation_path" else "test_sha256"
                try:
                    observed_sha = sha256_git_blob(repo_root, helper_commit, source_path, blob_cache)
                    if result_row.get(hash_key) != observed_sha:
                        errors.append(f"DOMAIN_SOURCE_HASH_MISMATCH:{domain_id}:{cap_id}:{key}")
                except (OSError, ValueError, subprocess.SubprocessError):
                    errors.append(f"DOMAIN_SOURCE_BLOB_UNAVAILABLE:{domain_id}:{cap_id}:{key}")
            if result_row.get("test_status") != "PASS" or result_row.get("test_return_code") != 0:
                errors.append(f"DOMAIN_CAPABILITY_TEST_NOT_PASS:{domain_id}:{cap_id}")
            route_evidence_values = route_evidence_by_capability.get((domain_id, cap_id), set())
            if len(route_evidence_values) != 1:
                errors.append(f"DOMAIN_CAPABILITY_ROUTE_EVIDENCE_CONFLICT_OR_MISSING:{domain_id}:{cap_id}")
            elif result_row.get("route_evidence_sha256") != next(iter(route_evidence_values)):
                errors.append(f"DOMAIN_CAPABILITY_ROUTE_EVIDENCE_MISMATCH:{domain_id}:{cap_id}")
            if not is_sha256(result_row.get("test_output_sha256")):
                errors.append(f"DOMAIN_CAPABILITY_TEST_OUTPUT_HASH_MISSING:{domain_id}:{cap_id}")
            test_output_rel = result_row.get("test_output_path")
            try:
                test_output_path = safe_relative(root, test_output_rel)
            except (ValueError, TypeError):
                errors.append(f"DOMAIN_CAPABILITY_TEST_OUTPUT_PATH_UNSAFE:{domain_id}:{cap_id}")
                continue
            if not test_output_path.is_file() or test_output_path.is_symlink():
                errors.append(f"DOMAIN_CAPABILITY_TEST_OUTPUT_MISSING:{domain_id}:{cap_id}")
            elif sha256_file(test_output_path) != result_row.get("test_output_sha256"):
                errors.append(f"DOMAIN_CAPABILITY_TEST_OUTPUT_HASH_MISMATCH:{domain_id}:{cap_id}")
    return sorted(set(errors))

def validate_plan(root: Path, total_bytes: int, available_disk: int, available_ram: int | None) -> dict[str, Any]:
    plan_path = root / PLAN_REL
    result: dict[str, Any] = {
        "status": "BLOCKED",
        "plan_path": PLAN_REL,
        "projected_final_upper_bound_bytes": None,
        "minimum_evidence_reserve_bytes": MIN_EVIDENCE_RESERVE_BYTES,
        "peak_transient_bytes": None,
        "errors": [],
        "operations": [],
    }
    if not plan_path.is_file():
        result["errors"] = ["OPTIMIZATION_PLAN_MISSING"]
        return result
    try:
        plan = read_object(plan_path)
    except (OSError, ValueError, json.JSONDecodeError):
        result["errors"] = ["OPTIMIZATION_PLAN_INVALID_JSON"]
        return result
    errors: list[str] = []
    if plan.get("schema") != "CAJITA_OPTIMIZATION_PLAN_V9/1.0":
        errors.append("OPTIMIZATION_PLAN_SCHEMA_MISMATCH")
    if plan.get("authority") != "Louksna.md" or plan.get("executor") != "CUSTOSZ_V9":
        errors.append("OPTIMIZATION_PLAN_AUTHORITY_OR_EXECUTOR_MISMATCH")
    if plan.get("final_cap_bytes") != CAP_BYTES:
        errors.append("OPTIMIZATION_PLAN_CAP_MISMATCH")
    if plan.get("max_parallel_operations") != 1:
        errors.append("OPTIMIZATION_PLAN_PARALLELISM_NOT_ONE")
    reserve = plan.get("final_evidence_reserve_bytes")
    if not isinstance(reserve, int) or isinstance(reserve, bool) or reserve < MIN_EVIDENCE_RESERVE_BYTES:
        errors.append("OPTIMIZATION_PLAN_EVIDENCE_RESERVE_TOO_SMALL")
        reserve = MIN_EVIDENCE_RESERVE_BYTES
    operations = plan.get("operations")
    if not isinstance(operations, list):
        result["errors"] = sorted(set(errors + ["OPTIMIZATION_PLAN_OPERATIONS_INVALID"]))
        return result
    by_component: dict[str, dict[str, Any]] = {}
    assigned_files: dict[str, str] = {}
    covered_roots: list[tuple[str, str]] = []
    current_scope_total = 0
    output_upper_total = 0
    peak_transient = 0
    for op in operations:
        if not isinstance(op, dict):
            errors.append("OPTIMIZATION_OPERATION_NOT_OBJECT")
            continue
        component = op.get("component")
        if component not in PENDING_COMPONENTS:
            errors.append(f"OPTIMIZATION_COMPONENT_UNKNOWN:{component}")
            continue
        if component in by_component:
            errors.append(f"OPTIMIZATION_COMPONENT_DUPLICATED:{component}")
        by_component[component] = op
        if op.get("executor") != "CUSTOSZ_V9":
            errors.append(f"OPTIMIZATION_EXECUTOR_MISMATCH:{component}")
        if not isinstance(op.get("technique"), str) or not op["technique"].strip():
            errors.append(f"OPTIMIZATION_TECHNIQUE_MISSING:{component}")
        if not is_sha256(op.get("prediction_evidence_sha256")):
            errors.append(f"OPTIMIZATION_PREDICTION_EVIDENCE_MISSING:{component}")
        if not is_sha256(op.get("functional_test_plan_sha256")):
            errors.append(f"OPTIMIZATION_FUNCTIONAL_TEST_PLAN_MISSING:{component}")
        if not is_sha256(op.get("rollback_plan_sha256")):
            errors.append(f"OPTIMIZATION_ROLLBACK_PLAN_MISSING:{component}")
        roots = op.get("target_roots")
        exclusions = op.get("exclude_roots", [])
        if not isinstance(roots, list) or not roots or not isinstance(exclusions, list):
            errors.append(f"OPTIMIZATION_TARGET_ROOTS_INVALID:{component}")
            continue
        selected: set[str] = set()
        for value in roots:
            try:
                p = safe_relative(root, value)
                rel = p.relative_to(root).as_posix()
            except (ValueError, TypeError):
                errors.append(f"OPTIMIZATION_TARGET_UNSAFE:{component}")
                continue
            parent_prefix = PENDING_COMPONENTS[component]
            if not (rel == parent_prefix or rel.startswith(parent_prefix + "/")):
                errors.append(f"OPTIMIZATION_TARGET_OUTSIDE_DOMAIN:{component}:{rel}")
            if not p.exists() or p.is_symlink():
                errors.append(f"OPTIMIZATION_TARGET_MISSING_OR_LINK:{component}:{rel}")
                continue
            covered_roots.append((component, rel))
            for base, dirs, names in os.walk(p, topdown=True, followlinks=False) if p.is_dir() else [(str(p.parent), [], [p.name])]:
                b = Path(base)
                for name in list(dirs):
                    if (b / name).is_symlink():
                        errors.append(f"OPTIMIZATION_TARGET_CONTAINS_SYMLINK:{component}:{(b / name).relative_to(root).as_posix()}")
                        dirs.remove(name)
                for name in names:
                    item = b / name
                    if item.is_symlink() or not item.is_file():
                        errors.append(f"OPTIMIZATION_TARGET_UNSAFE_FILE:{component}:{item.relative_to(root).as_posix()}")
                        continue
                    selected.add(item.relative_to(root).as_posix())
        exclusion_set: set[str] = set()
        for value in exclusions:
            try:
                p = safe_relative(root, value)
                rel = p.relative_to(root).as_posix()
            except (ValueError, TypeError):
                errors.append(f"OPTIMIZATION_EXCLUSION_UNSAFE:{component}")
                continue
            if not p.exists() or p.is_symlink():
                errors.append(f"OPTIMIZATION_EXCLUSION_MISSING:{component}:{rel}")
                continue
            if p.is_dir():
                for base, _, names in os.walk(p, followlinks=False):
                    for name in names:
                        item = Path(base) / name
                        if item.is_file() and not item.is_symlink():
                            exclusion_set.add(item.relative_to(root).as_posix())
            else:
                exclusion_set.add(rel)
        selected -= exclusion_set
        for rel in selected:
            if rel in assigned_files:
                errors.append(f"OPTIMIZATION_TARGET_OVERLAP:{rel}")
            assigned_files[rel] = component
        current_bytes = sum((root / rel).stat().st_size for rel in selected)
        declared_current = op.get("current_scope_bytes")
        if declared_current != current_bytes:
            errors.append(f"OPTIMIZATION_CURRENT_SCOPE_BYTES_STALE:{component}")
        current_scope_total += current_bytes
        output_bound = op.get("expected_output_upper_bound_bytes")
        temp = op.get("peak_temp_bytes")
        rollback = op.get("rollback_bytes")
        ram = op.get("peak_ram_bytes")
        for label, value in (("output", output_bound), ("temp", temp), ("rollback", rollback), ("ram", ram)):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                errors.append(f"OPTIMIZATION_RESOURCE_VALUE_INVALID:{component}:{label}")
        if all(isinstance(value, int) and not isinstance(value, bool) and value >= 0
               for value in (output_bound, temp, rollback, ram)):
            output_upper_total += output_bound
            peak_transient = max(peak_transient, temp + rollback)
            if temp + rollback > available_disk:
                errors.append(f"DISK_PEAK_EXCEEDS_AVAILABLE:{component}")
            if available_ram is None:
                errors.append("AVAILABLE_RAM_UNKNOWN")
            elif ram > available_ram:
                errors.append(f"RAM_PEAK_EXCEEDS_AVAILABLE:{component}")
        result["operations"].append({
            "component": component,
            "target_file_count": len(selected),
            "current_scope_bytes": current_bytes,
            "expected_output_upper_bound_bytes": output_bound,
            "peak_temp_bytes": temp,
            "rollback_bytes": rollback,
            "peak_ram_bytes": ram,
        })
    if set(by_component) != set(PENDING_COMPONENTS):
        errors.append("OPTIMIZATION_COMPONENT_COVERAGE_INCOMPLETE")
    if EDGE_ARCHIVE_REL not in assigned_files:
        errors.append("EDGE_ARCHIVE_NOT_INCLUDED_IN_OPTIMIZATION_SCOPE")
    # Every helper domain must be pinned, routed, tested, and bound to the exact
    # implementation/test sources at the declared repository commit.
    errors.extend(validate_domain_routing(root, plan, by_component))
    # Overlapping declared roots are only acceptable when the enclosing operation
    # explicitly excludes all files assigned to the nested operation.
    for i, (left_component, left) in enumerate(covered_roots):
        for right_component, right in covered_roots[i + 1:]:
            if left_component == right_component:
                continue
            if left == right or left.startswith(right + "/") or right.startswith(left + "/"):
                parent_component = left_component if left.startswith(right + "/") else right_component
                parent_root = right if parent_component == left_component else left
                parent_op = by_component.get(parent_component, {})
                excluded = [str(x).rstrip("/") for x in parent_op.get("exclude_roots", []) if isinstance(x, str)]
                child_root = left if parent_component == left_component else right
                if not any(child_root == ex or child_root.startswith(ex + "/") for ex in excluded):
                    errors.append(f"OPTIMIZATION_NESTED_ROOT_NOT_EXCLUDED:{left}:{right}")
    edge = plan.get("edge_profile")
    if not isinstance(edge, dict):
        errors.append("EDGE_PROFILE_STRATEGY_MISSING")
    else:
        if edge.get("archive_path") != EDGE_ARCHIVE_REL:
            errors.append("EDGE_PROFILE_ARCHIVE_PATH_MISMATCH")
        if edge.get("source_archive_sha256") is None or not is_sha256(edge.get("source_archive_sha256")):
            errors.append("EDGE_PROFILE_SOURCE_HASH_MISSING")
        if edge.get("preservation_mode") not in {"LOSSLESS_REPACK", "FUNCTIONAL_PROFILE_PRESERVATION"}:
            errors.append("EDGE_PROFILE_STRATEGY_INVALID")
        if edge.get("authentication_state_preserved") is not True:
            errors.append("EDGE_AUTHENTICATION_PRESERVATION_NOT_ASSERTED")
        required_state = {
            "cookies_and_session_state", "local_storage_and_indexeddb",
            "history_and_extensions", "profile_preferences",
        }
        if not isinstance(edge.get("preserved_state_classes"), list) or not required_state.issubset(set(edge.get("preserved_state_classes", []))):
            errors.append("EDGE_PROFILE_STATE_CLASSES_INCOMPLETE")
        if not is_sha256(edge.get("smoke_test_plan_sha256")):
            errors.append("EDGE_PROFILE_SMOKE_TEST_PLAN_MISSING")
        if not is_sha256(edge.get("rollback_test_plan_sha256")):
            errors.append("EDGE_PROFILE_ROLLBACK_PLAN_MISSING")
        for item in edge.get("removed_paths", []) if isinstance(edge.get("removed_paths", []), list) else []:
            if not isinstance(item, dict) or item.get("classification") != "REGENERABLE_CACHE_ONLY" or not is_sha256(item.get("regeneration_evidence_sha256")):
                errors.append("EDGE_REMOVAL_NOT_PROVEN_REGENERABLE_CACHE")
    try:
        projected = calculate_projected_final(total_bytes, current_scope_total, output_upper_total, reserve)
    except ValueError as exc:
        errors.append(str(exc))
        projected = total_bytes + output_upper_total + reserve
    result["projected_final_upper_bound_bytes"] = projected
    result["current_target_scope_bytes"] = current_scope_total
    result["output_upper_bound_bytes"] = output_upper_total
    result["final_evidence_reserve_bytes"] = reserve
    result["peak_transient_bytes"] = peak_transient
    if projected > CAP_BYTES:
        errors.append("PROJECTED_FINAL_SIZE_EXCEEDS_CAP")
    if edge and isinstance(edge, dict):
        edge_current_hash = None
        try:
            edge_path = safe_relative(root, EDGE_ARCHIVE_REL)
            if edge_path.is_file() and not edge_path.is_symlink():
                edge_current_hash = sha256_file(edge_path)
        except ValueError:
            pass
        if edge.get("source_archive_sha256") != edge_current_hash:
            errors.append("EDGE_PROFILE_SOURCE_DIGEST_STALE")
        if edge.get("expected_output_upper_bound_bytes", CAP_BYTES + 1) > CAP_BYTES:
            errors.append("EDGE_PROFILE_OUTPUT_BOUND_EXCEEDS_GLOBAL_CAP")
        if not isinstance(edge.get("expected_output_upper_bound_bytes"), int):
            errors.append("EDGE_PROFILE_OUTPUT_BOUND_INVALID")
    result["errors"] = sorted(set(errors))
    result["status"] = "PASS" if not result["errors"] else "BLOCKED"
    result["measured_at_utc"] = utc_now()
    return result


def check_preflight(root: Path) -> dict[str, Any]:
    inventory = scan_tree(root)
    free = shutil.disk_usage(root).free
    ram = available_ram_bytes()
    blockers: list[str] = []
    for domain in EXPECTED_DOMAINS:
        path = root / domain
        if not path.is_dir() or path.is_symlink():
            blockers.append(f"MANDATORY_DOMAIN_MISSING:{domain}")
    if inventory["symlinks"]:
        blockers.append("SYMLINKS_PRESENT_FAIL_CLOSED")
    if inventory["hardlink_groups"]:
        blockers.append("HARDLINKS_PRESENT_FAIL_CLOSED")
    if inventory["non_regular"]:
        blockers.append("NON_REGULAR_FILES_PRESENT")
    if inventory["scan_errors"]:
        blockers.append("TREE_SCAN_ERRORS")
    edge = edge_evidence(root)
    if edge.get("status") != "PASS":
        blockers.append("EDGE_ARCHIVE_INTEGRITY_BLOCKED")
    registry = registry_comparison(root)
    reconciliation_errors = validate_reconciliation(root, registry)
    blockers.extend(reconciliation_errors)
    frozen_errors = validate_frozen_manifest(root)
    blockers.extend(frozen_errors)
    plan = validate_plan(root, inventory["total_bytes"], free, ram)
    blockers.extend(plan["errors"])
    if plan["status"] != "PASS":
        blockers.append("OPTIMIZATION_PLAN_NOT_READY")
    current_overage = max(0, inventory["total_bytes"] - CAP_BYTES)
    if inventory["total_bytes"] > CAP_BYTES:
        size_state = "CURRENT_TREE_OVER_CAP_OPTIMIZATION_REQUIRED"
    else:
        size_state = "CURRENT_TREE_WITHIN_CAP"
    result = {
        "schema": "CAJITA_GOVERNED_PREFLIGHT/1.0",
        "measured_at_utc": utc_now(),
        "authority": "Louksna.md",
        "governance": "PUAC2_G01_G24_FAIL_CLOSED",
        "root": str(root.resolve()),
        "hard_cap_bytes": CAP_BYTES,
        "inventory": {
            "total_bytes": inventory["total_bytes"],
            "regular_file_count": inventory["regular_file_count"],
            "entry_count": inventory["entry_count"],
            "symlink_count": len(inventory["symlinks"]),
            "hardlink_group_count": len(inventory["hardlink_groups"]),
            "size_state": size_state,
            "current_overage_bytes": current_overage,
        },
        "domain_bytes": {
            domain: path_bytes(root / domain)
            for domain in EXPECTED_DOMAINS if (root / domain).exists()
        },
        "storage_resources": {
            "partition_total_bytes": shutil.disk_usage(root).total,
            "partition_used_bytes": shutil.disk_usage(root).used,
            "partition_free_bytes": free,
            "available_ram_bytes": ram,
        },
        "edge": edge,
        "legacy_registry": registry,
        "registry_reconciliation_errors": reconciliation_errors,
        "frozen_output_manifest_errors": frozen_errors,
        "optimization_plan": plan,
        "functional_validation": "NOT_RUN_OR_NOT_BOUND_TO_FINAL_SUBJECT",
        "gates": {
            **{gate: "NOT_VALIDATED_BY_PREFLIGHT" for gate in GATE_IDS_22},
            "G23": "NOT_RUN_FOR_CAJITA",
            "G24": "NOT_ISSUED_FOR_CAJITA",
        },
        "certification_status": "NOT_GRANTED",
        "release_status": "READY_FOR_CONTROLLED_OPTIMIZATION" if not blockers else "BLOCKED",
        "blockers": sorted(set(blockers)),
        "invariants": {
            "payload_transformations_performed": False,
            "frozen_outputs_modified": False,
            "edge_removed_or_moved": False,
            "external_staging_created": False,
            "full_cajita_copy_created": False,
            "g23_self_certification": False,
            "g24_self_issuance": False,
            "canonical_authority_transfer": False,
            "certification_propagation": False,
        },
        "measurement_policy": "All files and sidecars inside root count; no directory or hidden-path exclusions.",
    }
    return result


def persist_report(root: Path, report: dict[str, Any]) -> Path:
    evidence_dir = root / ".cajita-optimization-candidates" / "evidence"
    if evidence_dir.is_symlink():
        raise ValueError("EVIDENCE_DIRECTORY_SYMLINK_FORBIDDEN")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    report_path = evidence_dir / f"cajita-preflight-{stamp}.json"
    sidecar_path = report_path.with_suffix(".json.sha256")
    report["evidence_record"] = {
        "report_path": report_path.relative_to(root).as_posix(),
        "sha256_sidecar_path": sidecar_path.relative_to(root).as_posix(),
        "append_only": True,
        "report_and_sidecar_count_toward_cap": True,
    }
    existing = scan_tree(root)["total_bytes"]
    report["inventory"]["bytes_before_this_evidence_record"] = existing
    sidecar_bytes = len(("0" * 64 + "  " + report_path.name + "\n").encode("utf-8"))
    for _ in range(12):
        data = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        report["evidence_record"]["report_bytes"] = len(data)
        report["evidence_record"]["sidecar_bytes"] = sidecar_bytes
        report["inventory"]["bytes_after_this_evidence_record"] = existing + len(data) + sidecar_bytes
        updated = (json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        if len(updated) == len(data):
            data = updated
            break
    else:
        raise ValueError("EVIDENCE_SIZE_FIXED_POINT_DID_NOT_CONVERGE")
    fd = os.open(report_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    digest = sha256_bytes(data)
    sidecar_content = f"{digest}  {report_path.name}\n".encode("utf-8")
    side_fd = os.open(sidecar_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(side_fd, "wb") as stream:
        stream.write(sidecar_content)
        stream.flush()
        os.fsync(stream.fileno())
    observed_after = scan_tree(root)["total_bytes"]
    report["evidence_record"]["measured_bytes_after_persist"] = observed_after
    report["evidence_record"]["predicted_bytes_after_persist"] = report["inventory"]["bytes_after_this_evidence_record"]
    report["evidence_record"]["post_persist_exact_match"] = observed_after == report["inventory"]["bytes_after_this_evidence_record"]
    # The persisted record itself is immutable/append-only. If concurrent writes raced
    # with this measurement, expose the discrepancy in stdout and the next audit record.
    return report_path


def candidate_tree_digest(root: Path, exclude_paths: set[str] | list[str] | None = None) -> tuple[str, int, int]:
    """Hash every regular payload file except explicitly listed evidence outputs.

    The caller must provide a narrow, exact list of current run receipts/manifests.
    Historical evidence remains part of the subject digest. Every excluded output
    still contributes to the physical size budget and must have its own hash sidecar.
    """
    exclusions: set[str] = set()
    for value in exclude_paths or set():
        try:
            target = safe_relative(root, value)
        except ValueError as exc:
            raise ValueError("UNSAFE_SUBJECT_EXCLUSION:" + str(value)) from exc
        rel = target.relative_to(root).as_posix()
        if not rel.startswith(".cajita-optimization-candidates/evidence/"):
            raise ValueError("SUBJECT_EXCLUSION_OUTSIDE_GENERATED_EVIDENCE_LEDGER:" + rel)
        exclusions.add(rel)
    records: list[dict[str, Any]] = []
    files_hashed = 0
    total_hashed_bytes = 0
    for base, dirs, names in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        for name in list(dirs):
            p = base_path / name
            if p.is_symlink():
                raise ValueError(f"SYMLINK_DURING_SUBJECT_HASH:{p.relative_to(root).as_posix()}")
        for name in names:
            p = base_path / name
            rel = p.relative_to(root).as_posix()
            if rel in exclusions:
                continue
            if p.is_symlink() or not p.is_file():
                raise ValueError(f"UNSAFE_PATH_DURING_SUBJECT_HASH:{rel}")
            digest = sha256_file(p)
            size = p.stat().st_size
            records.append({"path": rel, "bytes": size, "sha256": digest})
            files_hashed += 1
            total_hashed_bytes += size
    records.sort(key=lambda item: item["path"])
    return sha256_bytes(canonical_json(records)), files_hashed, total_hashed_bytes

def validate_functional_manifest(root: Path) -> list[str]:
    path = root / FUNCTIONAL_REL
    if not path.is_file():
        return ["FUNCTIONAL_VALIDATION_MANIFEST_MISSING"]
    try:
        manifest = read_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["FUNCTIONAL_VALIDATION_MANIFEST_INVALID"]
    errors: list[str] = []
    if manifest.get("schema") != "CAJITA_FUNCTIONAL_VALIDATION_V9/1.0":
        errors.append("FUNCTIONAL_VALIDATION_SCHEMA_MISMATCH")
    if manifest.get("status") != "PASS" or manifest.get("executor") != "CUSTOSZ_V9":
        errors.append("FUNCTIONAL_VALIDATION_NOT_PASS_OR_EXECUTOR_MISMATCH")
    domains = manifest.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(EXPECTED_DOMAINS):
        errors.append("FUNCTIONAL_VALIDATION_DOMAIN_COVERAGE_INVALID")
    else:
        for domain, item in domains.items():
            if not isinstance(item, dict) or item.get("status") != "PASS":
                errors.append(f"DOMAIN_FUNCTIONAL_TEST_NOT_PASS:{domain}")
            elif not is_sha256(item.get("test_report_sha256")):
                errors.append(f"DOMAIN_TEST_REPORT_HASH_MISSING:{domain}")
    components = manifest.get("components")
    if not isinstance(components, list):
        errors.append("FUNCTIONAL_COMPONENT_COVERAGE_MISSING")
    else:
        component_map = {
            item.get("component"): item for item in components if isinstance(item, dict)
        }
        if set(component_map) != set(PENDING_COMPONENTS):
            errors.append("FUNCTIONAL_COMPONENT_COVERAGE_INVALID")
        for component in PENDING_COMPONENTS:
            item = component_map.get(component)
            if not isinstance(item, dict) or item.get("status") != "PASS":
                errors.append(f"PENDING_COMPONENT_NOT_FUNCTIONAL:{component}")
            elif not is_sha256(item.get("test_report_sha256")):
                errors.append(f"PENDING_COMPONENT_REPORT_HASH_MISSING:{component}")
    edge = manifest.get("edge_profile")
    if not isinstance(edge, dict) or edge.get("status") != "PASS":
        errors.append("EDGE_PROFILE_FUNCTIONAL_TEST_NOT_PASS")
    else:
        if edge.get("authentication_state_preserved") is not True:
            errors.append("EDGE_AUTHENTICATION_PRESERVATION_NOT_TESTED")
        for field in ("smoke_test_sha256", "restore_test_sha256"):
            if not is_sha256(edge.get(field)):
                errors.append("EDGE_PROFILE_EVIDENCE_HASH_MISSING:" + field)
    if not is_sha256(manifest.get("subject_inventory_sha256")):
        errors.append("FUNCTIONAL_VALIDATION_SUBJECT_INVENTORY_HASH_MISSING")
    return sorted(set(errors))


def validate_gate_matrix(root: Path) -> list[str]:
    path = root / GATE_MATRIX_REL
    if not path.is_file():
        return ["G01_G22_EVIDENCE_MATRIX_MISSING"]
    try:
        manifest = read_object(path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["G01_G22_EVIDENCE_MATRIX_INVALID"]
    errors: list[str] = []
    if manifest.get("schema") != "CAJITA_PUAC2_G01_G22_EVIDENCE/1.0":
        errors.append("GATE_MATRIX_SCHEMA_MISMATCH")
    gates = manifest.get("gates")
    if not isinstance(gates, list):
        return errors + ["GATE_MATRIX_LIST_INVALID"]
    by_gate = {g.get("gate_id"): g for g in gates if isinstance(g, dict)}
    if set(by_gate) != set(GATE_IDS_22) or len(gates) != len(GATE_IDS_22):
        errors.append("G01_G22_GATE_SET_INCOMPLETE_OR_DUPLICATED")
    for gate_id in GATE_IDS_22:
        row = by_gate.get(gate_id)
        if not isinstance(row, dict) or row.get("status") != "PASS" or not is_sha256(row.get("evidence_sha256")):
            errors.append(f"MANDATORY_GATE_NOT_PASS_OR_NOT_EVIDENCED:{gate_id}")
    if manifest.get("candidate_tree_sha256") is not None and not is_sha256(manifest.get("candidate_tree_sha256")):
        errors.append("GATE_MATRIX_SUBJECT_HASH_INVALID")
    return sorted(set(errors))


def validate_execution_manifest(root: Path) -> list[str]:
    plan_path = root / PLAN_REL
    execution_path = root / ".cajita-optimization-candidates" / "OPTIMIZATION_EXECUTION_V9.json"
    frozen_path = root / FROZEN_MANIFEST_REL
    if not plan_path.is_file():
        return ["OPTIMIZATION_PLAN_MISSING"]
    if not execution_path.is_file():
        return ["OPTIMIZATION_EXECUTION_MANIFEST_MISSING"]
    try:
        plan = read_object(plan_path)
        execution = read_object(execution_path)
    except (OSError, ValueError, json.JSONDecodeError):
        return ["OPTIMIZATION_PLAN_OR_EXECUTION_MANIFEST_INVALID"]
    errors: list[str] = []
    if plan.get("schema") != "CAJITA_OPTIMIZATION_PLAN_V9/1.0" or plan.get("final_cap_bytes") != CAP_BYTES:
        errors.append("OPTIMIZATION_PLAN_SCOPE_OR_CAP_INVALID")
    if plan.get("authority") != "Louksna.md" or plan.get("executor") != "CUSTOSZ_V9":
        errors.append("OPTIMIZATION_PLAN_AUTHORITY_INVALID")
    if execution.get("schema") != "CAJITA_OPTIMIZATION_EXECUTION_V9/1.0":
        errors.append("OPTIMIZATION_EXECUTION_SCHEMA_MISMATCH")
    if execution.get("status") != "PASS" or execution.get("rollback_verified") is not True:
        errors.append("OPTIMIZATION_EXECUTION_OR_ROLLBACK_NOT_PASS")
    execution_commit = execution.get("candidate_commit")
    if not isinstance(execution_commit, str) or re.fullmatch(r"[0-9a-f]{40}", execution_commit) is None:
        errors.append("OPTIMIZATION_EXECUTION_CANDIDATE_COMMIT_INVALID")
    if execution.get("executor") != "CUSTOSZ_V9":
        errors.append("OPTIMIZATION_EXECUTION_EXECUTOR_MISMATCH")
    if execution.get("plan_sha256") != sha256_file(plan_path):
        errors.append("OPTIMIZATION_EXECUTION_PLAN_DIGEST_MISMATCH")
    rows = execution.get("completed_operations")
    if not isinstance(rows, list):
        return sorted(set(errors + ["OPTIMIZATION_EXECUTION_ROWS_INVALID"]))
    by_component = {row.get("component"): row for row in rows if isinstance(row, dict)}
    if len(rows) != len(PENDING_COMPONENTS) or set(by_component) != set(PENDING_COMPONENTS):
        errors.append("OPTIMIZATION_EXECUTION_COMPONENT_COVERAGE_INVALID")
    frozen_roots: list[str] = []
    if frozen_path.is_file():
        try:
            frozen = read_object(frozen_path)
            roots = frozen.get("scope_roots", {})
            if isinstance(roots, dict):
                frozen_roots = [str(v).rstrip("/") for v in roots.values() if isinstance(v, str)]
        except (OSError, ValueError, json.JSONDecodeError):
            errors.append("FROZEN_MANIFEST_UNREADABLE_DURING_EXECUTION_AUDIT")
    for component in PENDING_COMPONENTS:
        row = by_component.get(component)
        if not isinstance(row, dict) or row.get("status") != "PASS":
            errors.append(f"OPTIMIZATION_OPERATION_NOT_PASS:{component}")
            continue
        for field in ("input_scope_sha256", "output_scope_sha256", "test_report_sha256", "rollback_test_sha256"):
            if not is_sha256(row.get(field)):
                errors.append(f"OPTIMIZATION_EXECUTION_EVIDENCE_HASH_MISSING:{component}:{field}")
        outputs = row.get("output_targets")
        if not isinstance(outputs, list) or not outputs:
            errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_TARGETS_MISSING:{component}")
            continue
        for output in outputs:
            if not isinstance(output, dict) or not isinstance(output.get("path"), str):
                errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_TARGET_INVALID:{component}")
                continue
            rel = output["path"]
            try:
                target = safe_relative(root, rel)
            except ValueError:
                errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_PATH_UNSAFE:{component}")
                continue
            if any(rel == protected or rel.startswith(protected + "/") for protected in frozen_roots):
                errors.append(f"OPTIMIZATION_EXECUTION_TOUCHES_FROZEN_SCOPE:{component}:{rel}")
                continue
            if not target.is_file() or target.is_symlink():
                errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_MISSING:{component}:{rel}")
                continue
            if output.get("size_bytes") != target.stat().st_size:
                errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_SIZE_MISMATCH:{component}:{rel}")
            if not is_sha256(output.get("sha256")) or sha256_file(target) != output.get("sha256"):
                errors.append(f"OPTIMIZATION_EXECUTION_OUTPUT_HASH_MISMATCH:{component}:{rel}")
    edge = execution.get("edge_profile")
    if not isinstance(edge, dict) or edge.get("status") != "PASS" or edge.get("authentication_state_preserved") is not True:
        errors.append("EDGE_EXECUTION_PRESERVATION_NOT_PASS")
    return sorted(set(errors))


def verify_puac2(root: Path, repo_root: Path, manifest_path: Path,
                  candidate_commit: str | None = None) -> dict[str, Any]:
    """Delegate Cajita certification to its own G23/G24 trust chain, not bridge mTLS."""
    gate_script = Path(__file__).with_name("cajita_luna_puac2_gates.py")
    if not gate_script.is_file():
        return {"decision": "HOLD", "certification_status": "NOT_GRANTED",
                "blockers": ["CAJITA_PUAC2_GATE_SCRIPT_MISSING"]}
    command = [
        sys.executable, str(gate_script), "verify-release",
        "--root", str(root), "--manifest", str(manifest_path),
    ]
    if candidate_commit:
        command.extend(["--candidate-commit", candidate_commit])
    completed = subprocess.run(
        command, cwd=repo_root, env=os.environ.copy(), capture_output=True,
        text=True, timeout=180, check=False,
    )
    try:
        report = json.loads(completed.stdout)
        if isinstance(report, dict):
            report.setdefault("delegate_exit_code", completed.returncode)
            return report
    except (ValueError, json.JSONDecodeError):
        pass
    return {"decision": "HOLD", "certification_status": "NOT_GRANTED",
            "blockers": ["CAJITA_PUAC2_GATE_OUTPUT_INVALID"],
            "exit_code": completed.returncode,
            "stdout_tail": completed.stdout[-2000:],
            "stderr_tail": completed.stderr[-2000:]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    pre = sub.add_parser("preflight", help="Measure Cajita and validate plan/manifests without transforming payloads.")
    pre.add_argument("--root", type=Path, required=True)
    pre.add_argument("--no-persist", action="store_true", help="Print report without writing to Cajita.")
    release = sub.add_parser("verify-release", help="Independently verify final functional gates and signed PUAC2 G23/G24 receipts.")
    release.add_argument("--root", type=Path, required=True)
    release.add_argument("--repo-root", type=Path, default=None)
    release.add_argument("--candidate-commit", default=None)
    release.add_argument("--manifest", type=Path, default=None, help="PUAC2 signed manifest; defaults to the in-Cajita evidence path.")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve(strict=True)
        if args.command == "preflight":
            report = check_preflight(root)
            if not args.no_persist:
                report_path = persist_report(root, report)
                report["evidence_record"]["report_path"] = report_path.relative_to(root).as_posix()
                report["evidence_record"]["sha256"] = sha256_file(report_path)
                observed_bytes = scan_tree(root)["total_bytes"]
                report["evidence_record"]["observed_bytes_after_persist"] = observed_bytes
                if observed_bytes > CAP_BYTES:
                    report["evidence_record"]["final_tree_with_this_report_over_cap"] = True
                # stdout carries the measured post-write record; the immutable on-disk
                # copy carries the same pre-write decision and includes byte projections.
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
            return 0 if report["release_status"] == "READY_FOR_CONTROLLED_OPTIMIZATION" else 2
        if args.command == "verify-release":
            repo_root = args.repo_root.resolve(strict=True) if args.repo_root else Path(__file__).resolve().parents[1]
            manifest = args.manifest or (root / RELEASE_MANIFEST_REL)
            report = verify_puac2(root, repo_root, manifest, args.candidate_commit)
            print(json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False))
            return 0 if report.get("decision") == "PASS" else 3
    except (OSError, ValueError, json.JSONDecodeError, subprocess.SubprocessError) as exc:
        print(json.dumps({
            "schema": "CAJITA_GOVERNED_PREFLIGHT_ERROR/1.0",
            "decision": "HOLD",
            "certification_status": "NOT_GRANTED",
            "error_type": type(exc).__name__,
            "reason": str(exc),
            "measured_at_utc": utc_now(),
        }, sort_keys=True, indent=2, ensure_ascii=False))
        return 3
    return 3


if __name__ == "__main__":
    raise SystemExit(main())
