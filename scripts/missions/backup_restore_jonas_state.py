#!/usr/bin/env python3
"""Integrity-checked SQLite backup/restore for the Jonas family service.

Restore is fail-closed: it requires the operator to confirm the service is stopped,
explicitly authorize restore, and supply the expected SHA-256 of the backup.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import hmac
import json
import os
import sqlite3
import tempfile
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def check_integrity(path: Path) -> None:
    if not path.is_file():
        raise ValueError(f"database file does not exist: {path}")
    uri = path.resolve().as_uri() + "?mode=ro"
    with sqlite3.connect(uri, uri=True, timeout=10) as conn:
        result = conn.execute("PRAGMA integrity_check").fetchone()
    if not result or result[0] != "ok":
        raise ValueError(f"SQLite integrity check failed for {path}: {result[0] if result else 'no result'}")


def sqlite_backup(source: Path, destination: Path) -> None:
    source_uri = source.resolve().as_uri() + "?mode=ro"
    destination.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(source_uri, uri=True, timeout=30) as src:
        with sqlite3.connect(destination, timeout=30) as dst:
            src.backup(dst)
            result = dst.execute("PRAGMA integrity_check").fetchone()
            if not result or result[0] != "ok":
                raise ValueError(f"Backup integrity check failed: {result[0] if result else 'no result'}")


def backup(source: Path, destination: Path) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if not source.is_file():
        raise ValueError(f"source database missing: {source}")
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite backup: {destination}")
    check_integrity(source)
    sqlite_backup(source, destination)
    check_integrity(destination)
    digest = sha256_file(destination)
    manifest = {
        "schema": "jonas.sqlite-backup.v1",
        "created_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_path": str(source),
        "backup_path": str(destination),
        "size_bytes": destination.stat().st_size,
        "sha256": digest,
        "integrity_check": "ok",
        "certified": False,
    }
    destination.with_suffix(destination.suffix + ".json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    destination.with_suffix(destination.suffix + ".sha256").write_text(
        f"{digest}  {destination.name}\n", encoding="utf-8"
    )
    return manifest


def restore(source: Path, destination: Path, expected_sha256: str, *, confirm_restore: bool, service_stopped_confirmed: bool) -> dict:
    source = source.resolve()
    destination = destination.resolve()
    if not confirm_restore:
        raise PermissionError("restore denied: pass --confirm-restore explicitly")
    if not service_stopped_confirmed:
        raise PermissionError("restore denied: pass --service-stopped-confirmed only after stopping the service")
    if not source.is_file():
        raise ValueError(f"backup file missing: {source}")
    if len(expected_sha256) != 64 or any(ch not in "0123456789abcdefABCDEF" for ch in expected_sha256):
        raise ValueError("expected SHA-256 must contain exactly 64 hexadecimal characters")
    actual = sha256_file(source)
    if not hmac.compare_digest(actual.encode("ascii"), expected_sha256.lower().encode("ascii")):
        raise ValueError("backup SHA-256 mismatch; restore denied")
    check_integrity(source)
    for suffix in ("-wal", "-shm"):
        if Path(str(destination) + suffix).exists():
            raise RuntimeError(f"restore denied while SQLite sidecar exists: {destination}{suffix}")

    checkpoint = None
    if destination.exists():
        stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        checkpoint = destination.with_name(destination.name + f".pre-restore-{stamp}.sqlite3")
        if checkpoint.exists():
            raise FileExistsError(f"pre-restore checkpoint already exists: {checkpoint}")
        sqlite_backup(destination, checkpoint)
        check_integrity(checkpoint)

    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=destination.name + ".restore-", suffix=".sqlite3", dir=destination.parent)
    os.close(fd)
    temporary = Path(temp_name)
    try:
        sqlite_backup(source, temporary)
        check_integrity(temporary)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)

    result = {
        "schema": "jonas.sqlite-restore.v1",
        "restored_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_backup": str(source),
        "destination": str(destination),
        "backup_sha256": actual,
        "destination_sha256": sha256_file(destination),
        "pre_restore_checkpoint": str(checkpoint) if checkpoint else None,
        "integrity_check": "ok",
        "service_stopped_confirmed": True,
        "restore_explicitly_authorized": True,
        "certified": False,
    }
    destination.with_suffix(destination.suffix + ".restore.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    p_backup = commands.add_parser("backup")
    p_backup.add_argument("--source", required=True, type=Path)
    p_backup.add_argument("--destination", required=True, type=Path)
    p_verify = commands.add_parser("verify")
    p_verify.add_argument("--database", required=True, type=Path)
    p_verify.add_argument("--expected-sha256")
    p_restore = commands.add_parser("restore")
    p_restore.add_argument("--source-backup", required=True, type=Path)
    p_restore.add_argument("--destination", required=True, type=Path)
    p_restore.add_argument("--expected-sha256", required=True)
    p_restore.add_argument("--confirm-restore", action="store_true")
    p_restore.add_argument("--service-stopped-confirmed", action="store_true")
    args = parser.parse_args()

    if args.command == "backup":
        result = backup(args.source, args.destination)
    elif args.command == "verify":
        check_integrity(args.database)
        digest = sha256_file(args.database)
        if args.expected_sha256 and not hmac.compare_digest(digest, args.expected_sha256.lower()):
            raise SystemExit("database SHA-256 mismatch")
        result = {"database": str(args.database.resolve()), "sha256": digest, "integrity_check": "ok"}
    else:
        result = restore(
            args.source_backup, args.destination, args.expected_sha256,
            confirm_restore=args.confirm_restore,
            service_stopped_confirmed=args.service_stopped_confirmed,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
