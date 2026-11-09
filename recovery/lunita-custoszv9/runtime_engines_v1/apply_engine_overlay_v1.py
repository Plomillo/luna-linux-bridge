#!/usr/bin/env python3
"""Fail-closed, additive installer for the E01-E15 candidate overlay.

This installer authorizes deployment from a hash-verified checkpoint; it does not depend on an external worker identity.
It never changes the existing Lunita launcher, model weights, frozen G06/G08,
or system paths outside the new versioned engine directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

try:
    from . import checkpoint_v1
except ImportError:
    import checkpoint_v1

EXPECTED_CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
EXPECTED_LAUNCHER_SHA256 = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2"
EXPECTED_CHECKPOINT_SCHEMA = "LUNITA_RUNTIME_OVERLAY_CHECKPOINT/1.0"
EXPECTED_CHECKPOINT_SCOPE = "LUNITA_ADDITIVE_RUNTIME_ENGINE_OVERLAY"
EXPECTED_CHECKPOINT_MANIFEST_SCHEMA = "LUNITA_RUNTIME_OVERLAY_CHECKPOINT_MANIFEST/1.0"
OVERLAY_RELATIVE_PATH = pathlib.Path("opt/lunita/engines/runtime_engines_v1")
FILES = (
    "__init__.py",
    "engine_runtime_v1.py",
    "engine_acceptance_v1.py",
    "engine_gateway_v1.py",
    "gateway_acceptance_v1.py",
    "lunita_beta_v1_8.py",
    "launcher_acceptance_v1.py",
    "target_runtime_acceptance_v1.py",
    "apply_engine_overlay_v1.py",
    "checkpoint_v1.py",
    "overlay_acceptance_v1.py",
    "engine_assignments_v1.json",
    "requirements-engine-stack.txt",
    "DEPENDENCY_EVIDENCE_v1.json",
    "ENGINE_RUNTIME_V1_README.md",
)
DIRECTORIES = (
    "vendor/python3.12/site-packages",
    "model-cache/fastembed",
)


class GateError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def reject_any_symlink(path: pathlib.Path) -> None:
    absolute = pathlib.Path(os.path.abspath(path))
    current = pathlib.Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        if current.exists() and current.is_symlink():
            raise GateError(f"Symlink path component is not allowed: {current}")


def reject_symlink_components(path: pathlib.Path, stop: pathlib.Path) -> None:
    """Reject symlink traversal from path down to the declared root."""
    path_abs = pathlib.Path(os.path.abspath(path))
    stop_abs = pathlib.Path(os.path.abspath(stop))
    try:
        relative = path_abs.relative_to(stop_abs)
    except ValueError as exc:
        raise GateError(f"Path escapes approved root: {path}") from exc
    current = stop_abs
    if current.is_symlink():
        raise GateError(f"Approved root must not be a symlink: {current}")
    for component in relative.parts:
        current = current / component
        if current.is_symlink():
            raise GateError(f"Symlink component is not allowed: {current}")


def hash_tree(path: pathlib.Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_dir():
        raise GateError(f"Required payload directory is missing or not a real directory: {path}")
    entries = []
    for item in sorted(path.rglob("*")):
        if item.is_symlink():
            raise GateError(f"Symlink inside deployable payload is forbidden: {item}")
        if item.is_file():
            entries.append({
                "path": item.relative_to(path).as_posix(),
                "sha256": sha256_file(item),
                "bytes": item.stat().st_size,
            })
        elif not item.is_dir():
            raise GateError(f"Unsupported filesystem object in payload: {item}")
    if not entries:
        raise GateError(f"Deployable payload directory is empty: {path}")
    canonical = json.dumps(entries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return {"file_count": len(entries), "bytes": sum(item["bytes"] for item in entries),
            "sha256": hashlib.sha256(canonical).hexdigest()}


def load_checkpoint_receipt(
    receipt_path: pathlib.Path,
    candidate_id: str,
    rootfs: pathlib.Path,
) -> dict[str, Any]:
    reject_any_symlink(receipt_path)
    receipt_path = receipt_path.resolve(strict=True)
    if not receipt_path.is_file():
        raise GateError("Checkpoint receipt must be a regular file")
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    if data.get("schema") != EXPECTED_CHECKPOINT_SCHEMA:
        raise GateError("Checkpoint receipt schema mismatch")
    if data.get("status") != "PASS":
        raise GateError("Checkpoint receipt status is not PASS")
    if data.get("candidate_id") != candidate_id or candidate_id != EXPECTED_CANDIDATE_ID:
        raise GateError("Checkpoint candidate identity mismatch")
    if data.get("scope") != EXPECTED_CHECKPOINT_SCOPE:
        raise GateError("Checkpoint scope mismatch")
    root_value = data.get("checkpoint_root")
    manifest_value = data.get("checkpoint_manifest")
    expected_hash = data.get("checkpoint_manifest_sha256")
    if not isinstance(root_value, str) or not root_value or not isinstance(manifest_value, str) or not manifest_value:
        raise GateError("Checkpoint root and manifest paths are required")
    if not isinstance(expected_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", expected_hash):
        raise GateError("Checkpoint manifest SHA-256 is required")
    reject_any_symlink(pathlib.Path(root_value))
    reject_any_symlink(pathlib.Path(manifest_value))
    checkpoint_root = pathlib.Path(root_value).resolve(strict=True)
    manifest_path = pathlib.Path(manifest_value).resolve(strict=True)
    rootfs = rootfs.resolve(strict=True)
    if not checkpoint_root.is_dir() or not manifest_path.is_file():
        raise GateError("Checkpoint root or manifest is not available")
    try:
        manifest_path.relative_to(checkpoint_root)
    except ValueError as exc:
        raise GateError("Checkpoint manifest must be contained inside checkpoint root") from exc
    try:
        checkpoint_root.relative_to(rootfs)
        raise GateError("Checkpoint directory must be outside the protected rootfs")
    except ValueError:
        pass
    try:
        rootfs.relative_to(checkpoint_root)
        raise GateError("Checkpoint directory must not contain the protected rootfs")
    except ValueError:
        pass
    observed_manifest_hash = sha256_file(manifest_path)
    if observed_manifest_hash != expected_hash:
        raise GateError("Checkpoint manifest SHA-256 mismatch")

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise GateError("Checkpoint manifest is not valid JSON") from exc
    if (
        manifest.get("schema") != EXPECTED_CHECKPOINT_MANIFEST_SCHEMA
        or manifest.get("candidate_id") != candidate_id
        or manifest.get("scope") != EXPECTED_CHECKPOINT_SCOPE
    ):
        raise GateError("Checkpoint manifest identity or schema mismatch")
    if data.get("rootfs_path") != str(rootfs) or manifest.get("rootfs_path") != str(rootfs):
        raise GateError("Checkpoint is not bound to the exact rootfs path")
    if (
        data.get("rootfs_tree_sha256") != manifest.get("entries_sha256")
        or data.get("rootfs_entry_count") != manifest.get("entry_count")
    ):
        raise GateError("Checkpoint receipt and manifest rootfs bindings differ")

    # Re-hash the current rootfs. A valid receipt for another tree or an older
    # tree must never authorize installation onto the present candidate.
    current_manifest = checkpoint_v1.build_manifest(rootfs, candidate_id)
    if manifest != current_manifest:
        raise GateError("Checkpoint manifest does not describe the current rootfs bytes and metadata")
    return {
        "receipt_path": str(receipt_path),
        "receipt_sha256": sha256_file(receipt_path),
        "checkpoint_root": str(checkpoint_root),
        "checkpoint_manifest": str(manifest_path),
        "checkpoint_manifest_sha256": observed_manifest_hash,
        "rootfs_path": str(rootfs),
        "rootfs_tree_sha256": current_manifest["entries_sha256"],
        "rootfs_entry_count": current_manifest["entry_count"],
        "checkpoint_id": data.get("checkpoint_id"),
    }


def preflight(
    rootfs: pathlib.Path,
    source_dir: pathlib.Path,
    checkpoint_receipt: pathlib.Path,
    candidate_id: str,
) -> dict[str, Any]:
    if candidate_id != EXPECTED_CANDIDATE_ID:
        raise GateError("Candidate identifier mismatch")
    reject_any_symlink(rootfs)
    rootfs = rootfs.resolve(strict=True)
    if not rootfs.is_dir():
        raise GateError("Rootfs must be a directory")
    launcher = rootfs / "opt/lunita/agent/lunita.py"
    reject_symlink_components(launcher, rootfs)
    if not launcher.is_file():
        raise GateError("Candidate launcher is missing")
    launcher_hash = sha256_file(launcher)
    if launcher_hash != EXPECTED_LAUNCHER_SHA256:
        raise GateError("Candidate launcher does not match the hash-pinned beta-v1.7 source")
    reject_any_symlink(source_dir)
    source_dir = source_dir.resolve(strict=True)
    if not source_dir.is_dir():
        raise GateError("Engine source directory is missing")
    sources: dict[str, str] = {}
    for filename in FILES:
        source = source_dir / filename
        if source.is_symlink() or not source.is_file():
            raise GateError(f"Required additive payload is missing or not regular: {filename}")
        sources[filename] = sha256_file(source)
    directories: dict[str, Any] = {}
    for relative in DIRECTORIES:
        source = source_dir / relative
        reject_any_symlink(source)
        directories[relative] = hash_tree(source)
    checkpoint = load_checkpoint_receipt(checkpoint_receipt, candidate_id, rootfs)
    engines_dir = rootfs / "opt/lunita/engines"
    target = rootfs / OVERLAY_RELATIVE_PATH
    reject_symlink_components(engines_dir, rootfs)
    reject_symlink_components(target, rootfs)
    if target.exists():
        raise GateError("Versioned overlay already exists; overwrite/reapply is forbidden")
    return {
        "status": "PREFLIGHT_PASS",
        "candidate_id": candidate_id,
        "rootfs": str(rootfs),
        "launcher_sha256": launcher_hash,
        "target": str(target),
        "checkpoint": checkpoint,
        "files": sources,
        "directories": directories,
    }


def apply_overlay(
    rootfs: pathlib.Path,
    source_dir: pathlib.Path,
    checkpoint_receipt: pathlib.Path,
    candidate_id: str,
    apply: bool = False,
) -> dict[str, Any]:
    result = preflight(rootfs, source_dir, checkpoint_receipt, candidate_id)
    if not apply:
        return {**result, "status": "DRY_RUN_PASS_NO_MUTATION", "mutated": False}
    rootfs = pathlib.Path(result["rootfs"])
    target = rootfs / OVERLAY_RELATIVE_PATH
    engines_dir = target.parent
    engines_dir.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(engines_dir, rootfs)
    if target.exists():
        raise GateError("Target appeared after preflight; no overwrite performed")
    stage = engines_dir / f".runtime_engines_v1.staging-{os.getpid()}"
    if stage.exists():
        raise GateError("Staging path collision; refusing cleanup or overwrite")
    stage.mkdir(mode=0o755)
    try:
        copied: dict[str, str] = {}
        source_dir = pathlib.Path(source_dir).resolve(strict=True)
        for filename in FILES:
            source = source_dir / filename
            destination = stage / filename
            shutil.copyfile(source, destination, follow_symlinks=False)
            os.chmod(destination, 0o644)
            observed = sha256_file(destination)
            if observed != result["files"][filename]:
                raise GateError(f"Copied file digest mismatch: {filename}")
            copied[filename] = observed
        copied_directories: dict[str, Any] = {}
        for relative in DIRECTORIES:
            source = source_dir / relative
            destination = stage / relative
            shutil.copytree(source, destination, symlinks=False)
            observed = hash_tree(destination)
            if observed != result["directories"][relative]:
                raise GateError(f"Copied directory digest mismatch: {relative}")
            copied_directories[relative] = observed
        receipt = {
            "schema": "LUNITA_ADDITIVE_ENGINE_OVERLAY_RECEIPT/1.0",
            "status": "APPLIED_ADDITIVELY_NOT_CERTIFIED",
            "mutated": True,
            "candidate_id": candidate_id,
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "launcher_sha256": result["launcher_sha256"],
            "checkpoint": result["checkpoint"],
            "files": copied,
            "directories": copied_directories,
            "target_relative_path": str(OVERLAY_RELATIVE_PATH),
            "canonical_identity_mutation": False,
            "engine_reassignment": False,
            "command_reassignment": False,
            "agent_reassignment": False,
            "frozen_g06_mutated": False,
            "canonical_g08_mutated": False,
            "launcher_mutated": False,
            "model_weights_mutated": False,
            "certification": "NOT_GRANTED",
        }
        receipt_path = stage / "OVERLAY_APPLY_RECEIPT.json"
        receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        with receipt_path.open("rb") as stream:
            os.fsync(stream.fileno())
        os.rename(stage, target)
        return {**result, "status": "APPLIED_ADDITIVELY_NOT_CERTIFIED", "mutated": True,
                "target": str(target), "receipt": str(target / "OVERLAY_APPLY_RECEIPT.json"),
                "files": copied, "directories": copied_directories}
    except Exception:
        # Only the uniquely-owned staging directory is cleaned. No existing path is touched.
        if stage.exists() and not stage.is_symlink():
            shutil.rmtree(stage)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", required=True, type=pathlib.Path)
    parser.add_argument("--source-dir", type=pathlib.Path, default=pathlib.Path(__file__).resolve().parent)
    parser.add_argument("--checkpoint-receipt", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-id", required=True)
    parser.add_argument("--apply", action="store_true", help="Perform the additive write; otherwise dry-run only")
    args = parser.parse_args()
    try:
        result = apply_overlay(args.rootfs, args.source_dir, args.checkpoint_receipt,
                               args.candidate_id, args.apply)
    except (OSError, ValueError, GateError) as exc:
        print(json.dumps({"status": "DENIED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
