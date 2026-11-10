#!/usr/bin/env python3
"""Create a no-mutation, content-bound checkpoint for a Lunita candidate rootfs."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import stat
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

EXPECTED_CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
EXPECTED_RECEIPT_SCHEMA = "LUNITA_RUNTIME_OVERLAY_CHECKPOINT/1.0"
EXPECTED_MANIFEST_SCHEMA = "LUNITA_RUNTIME_OVERLAY_CHECKPOINT_MANIFEST/1.0"
EXPECTED_SCOPE = "LUNITA_ADDITIVE_RUNTIME_ENGINE_OVERLAY"


class CheckpointError(RuntimeError):
    pass


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _signature(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def reject_symlink_components(path: pathlib.Path) -> None:
    absolute = pathlib.Path(os.path.abspath(path))
    current = pathlib.Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise CheckpointError(f"Symlink path component is not allowed: {current}")


def build_manifest(rootfs: pathlib.Path, candidate_id: str = EXPECTED_CANDIDATE_ID) -> dict[str, Any]:
    if candidate_id != EXPECTED_CANDIDATE_ID:
        raise CheckpointError("Candidate identifier mismatch")
    reject_symlink_components(rootfs)
    rootfs = rootfs.resolve(strict=True)
    if not rootfs.is_dir() or rootfs.is_symlink():
        raise CheckpointError("Rootfs must be an existing real directory")

    rows: list[dict[str, Any]] = []
    observed_signatures: dict[pathlib.Path, tuple[int, ...]] = {}
    observed_symlink_targets: dict[pathlib.Path, str] = {}
    pending: list[tuple[pathlib.Path, str]] = [(rootfs, ".")]

    while pending:
        directory, relative_directory = pending.pop()
        directory_stat = directory.lstat()
        if not stat.S_ISDIR(directory_stat.st_mode):
            raise CheckpointError(f"Rootfs directory changed type during scan: {directory}")
        observed_signatures[directory] = _signature(directory_stat)
        rows.append({
            "path": relative_directory,
            "type": "directory",
            "mode": stat.S_IMODE(directory_stat.st_mode),
            "uid": directory_stat.st_uid,
            "gid": directory_stat.st_gid,
            "mtime_ns": directory_stat.st_mtime_ns,
            "size_bytes": directory_stat.st_size,
            "sha256": None,
            "symlink_target": None,
            "device": None,
        })

        try:
            with os.scandir(directory) as stream:
                children = sorted(list(stream), key=lambda item: item.name)
        except OSError as exc:
            raise CheckpointError(f"Cannot enumerate rootfs directory {directory}: {exc}") from exc

        for child in children:
            path = directory / child.name
            relative = (path.relative_to(rootfs)).as_posix()
            before = path.lstat()
            mode = stat.S_IMODE(before.st_mode)
            row: dict[str, Any] = {
                "path": relative,
                "type": "special",
                "mode": mode,
                "uid": before.st_uid,
                "gid": before.st_gid,
                "mtime_ns": before.st_mtime_ns,
                "size_bytes": before.st_size,
                "sha256": None,
                "symlink_target": None,
                "device": None,
            }

            if stat.S_ISDIR(before.st_mode):
                row["type"] = "directory"
                pending.append((path, relative))
            elif stat.S_ISREG(before.st_mode):
                row["type"] = "file"
                row["sha256"] = sha256_file(path)
            elif stat.S_ISLNK(before.st_mode):
                row["type"] = "symlink"
                target = os.readlink(path)
                row["symlink_target"] = target
                observed_symlink_targets[path] = target
            else:
                row["device"] = before.st_rdev

            after = path.lstat()
            if _signature(before) != _signature(after):
                raise CheckpointError(f"Rootfs entry changed while hashing: {relative}")
            observed_signatures[path] = _signature(after)
            rows.append(row)

    rows.sort(key=lambda item: item["path"])
    for path, expected_signature in observed_signatures.items():
        try:
            current_signature = _signature(path.lstat())
        except OSError as exc:
            raise CheckpointError(f"Rootfs entry disappeared during checkpoint: {path}") from exc
        if current_signature != expected_signature:
            raise CheckpointError(f"Rootfs changed during checkpoint: {path}")
        expected_target = observed_symlink_targets.get(path)
        if expected_target is not None and os.readlink(path) != expected_target:
            raise CheckpointError(f"Rootfs symlink changed during checkpoint: {path}")

    regular_files = [row for row in rows if row["type"] == "file"]
    entries_sha256 = hashlib.sha256(canonical_json(rows)).hexdigest()
    return {
        "schema": EXPECTED_MANIFEST_SCHEMA,
        "candidate_id": candidate_id,
        "scope": EXPECTED_SCOPE,
        "rootfs_path": str(rootfs),
        "entry_count": len(rows),
        "regular_file_count": len(regular_files),
        "regular_file_total_bytes": sum(row["size_bytes"] for row in regular_files),
        "entries_sha256": entries_sha256,
        "entries": rows,
    }


def _atomic_write(path: pathlib.Path, payload: bytes, mode: int = 0o600) -> None:
    temporary = path.with_name(path.name + f".tmp-{os.getpid()}-{uuid.uuid4().hex}")
    fd = os.open(temporary, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while persisting checkpoint evidence")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def create_checkpoint(
    rootfs: pathlib.Path,
    checkpoint_dir: pathlib.Path,
    candidate_id: str = EXPECTED_CANDIDATE_ID,
) -> dict[str, Any]:
    reject_symlink_components(rootfs)
    rootfs = rootfs.resolve(strict=True)
    if not rootfs.is_dir():
        raise CheckpointError("Rootfs must be an existing directory")

    reject_symlink_components(checkpoint_dir)
    checkpoint_dir = pathlib.Path(os.path.abspath(checkpoint_dir))
    try:
        checkpoint_dir.relative_to(rootfs)
        raise CheckpointError("Checkpoint directory must be outside the rootfs being protected")
    except ValueError:
        pass
    try:
        rootfs.relative_to(checkpoint_dir.resolve(strict=False))
        raise CheckpointError("Checkpoint directory must not contain the rootfs")
    except ValueError:
        pass
    checkpoint_dir.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    checkpoint_dir.mkdir(mode=0o700, exist_ok=False)

    try:
        manifest = build_manifest(rootfs, candidate_id)
        manifest_bytes = json.dumps(manifest, sort_keys=True, ensure_ascii=True, indent=2).encode("utf-8") + b"\n"
        manifest_path = checkpoint_dir / "MANIFEST.json"
        _atomic_write(manifest_path, manifest_bytes)
        receipt = {
            "schema": EXPECTED_RECEIPT_SCHEMA,
            "status": "PASS",
            "candidate_id": candidate_id,
            "scope": EXPECTED_SCOPE,
            "checkpoint_id": "LUNITA-" + uuid.uuid4().hex,
            "checkpoint_root": str(checkpoint_dir.resolve(strict=True)),
            "checkpoint_manifest": str(manifest_path.resolve(strict=True)),
            "checkpoint_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "rootfs_path": str(rootfs),
            "rootfs_tree_sha256": manifest["entries_sha256"],
            "rootfs_entry_count": manifest["entry_count"],
            "captured_at_utc": datetime.now(timezone.utc).isoformat(),
            "certification": "NOT_GRANTED",
        }
        receipt_path = checkpoint_dir / "CHECKPOINT_RECEIPT.json"
        receipt_bytes = json.dumps(receipt, sort_keys=True, ensure_ascii=True, indent=2).encode("utf-8") + b"\n"
        _atomic_write(receipt_path, receipt_bytes)
        return {**receipt, "receipt_path": str(receipt_path),
                "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest()}
    except Exception:
        if checkpoint_dir.is_dir() and not checkpoint_dir.is_symlink():
            shutil.rmtree(checkpoint_dir)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", required=True, type=pathlib.Path)
    parser.add_argument("--checkpoint-dir", required=True, type=pathlib.Path)
    parser.add_argument("--candidate-id", default=EXPECTED_CANDIDATE_ID)
    args = parser.parse_args()
    try:
        result = create_checkpoint(args.rootfs, args.checkpoint_dir, args.candidate_id)
    except (OSError, ValueError, CheckpointError) as exc:
        print(json.dumps({"status": "DENIED", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
