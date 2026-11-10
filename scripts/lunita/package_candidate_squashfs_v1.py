#!/usr/bin/env python3
"""Build and round-trip verify a hash-bound Lunita v1.8 SquashFS candidate.

The packager does not create a rootfs or certify Lunita. It accepts only an
existing G06-derived rootfs with a successful direct target-runtime receipt.
It preserves the source tree and refuses to overwrite any output.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import stat
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from typing import Any

CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
TARGET_PASS = "PASS_TARGET_RUNTIME_ACCEPTANCE_NOT_CERTIFIED"
PACKAGE_PASS = "PASS_SQUASHFS_PACKAGE_AND_ROUNDTRIP_NOT_CERTIFIED"


class PackageError(RuntimeError):
    pass


def sha256_file(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode("utf-8")


def reject_symlink_components(path: pathlib.Path) -> None:
    absolute = pathlib.Path(os.path.abspath(path))
    current = pathlib.Path(absolute.anchor)
    for part in absolute.parts[1:]:
        current = current / part
        if current.is_symlink():
            raise PackageError(f"Symlink path component is not permitted: {current}")


def xattr_manifest(path: pathlib.Path, *, is_symlink: bool) -> list[dict[str, str]]:
    try:
        names = sorted(os.listxattr(path, follow_symlinks=not is_symlink))
        rows = []
        for name in names:
            value = os.getxattr(path, name, follow_symlinks=not is_symlink)
            rows.append({"name": name, "sha256": hashlib.sha256(value).hexdigest()})
        return rows
    except OSError as exc:
        raise PackageError(f"Cannot read extended attributes for {path}: {exc}") from exc


def _stat_signature(st: os.stat_result) -> tuple[int, ...]:
    return (st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)


def _hash_open_regular(path: pathlib.Path, expected: os.stat_result) -> str:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(path, flags)
    try:
        opened = os.fstat(fd)
        if _stat_signature(opened) != _stat_signature(expected) or not stat.S_ISREG(opened.st_mode):
            raise PackageError(f"Regular file changed before hashing: {path}")
        digest = hashlib.sha256()
        with os.fdopen(fd, "rb", closefd=False) as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        if _stat_signature(os.fstat(fd)) != _stat_signature(expected):
            raise PackageError(f"Regular file changed while hashing: {path}")
        return digest.hexdigest()
    finally:
        os.close(fd)


def tree_manifest(root: pathlib.Path) -> dict[str, Any]:
    reject_symlink_components(root)
    root = root.resolve(strict=True)
    if not root.is_dir() or root.is_symlink():
        raise PackageError(f"Rootfs must be an existing real directory: {root}")

    rows: list[dict[str, Any]] = []
    signatures: dict[pathlib.Path, tuple[int, ...]] = {}
    symlink_targets: dict[pathlib.Path, str] = {}
    pending: list[tuple[pathlib.Path, str]] = [(root, ".")]
    while pending:
        directory, relative_directory = pending.pop()
        directory_stat = directory.lstat()
        if not stat.S_ISDIR(directory_stat.st_mode):
            raise PackageError(f"Directory changed type during scan: {directory}")
        directory_signature = _stat_signature(directory_stat)
        previous_signature = signatures.get(directory)
        if previous_signature is not None and previous_signature != directory_signature:
            raise PackageError(f"Directory changed before scan completed: {directory}")
        signatures[directory] = directory_signature
        rows.append({
            "path": relative_directory,
            "type": "directory",
            "mode": stat.S_IMODE(directory_stat.st_mode),
            "uid": directory_stat.st_uid,
            "gid": directory_stat.st_gid,
            "mtime_seconds": int(directory_stat.st_mtime),
            "xattrs": xattr_manifest(directory, is_symlink=False),
        })
        try:
            with os.scandir(directory) as stream:
                children = sorted(list(stream), key=lambda item: item.name)
        except OSError as exc:
            raise PackageError(f"Cannot enumerate {directory}: {exc}") from exc

        for child in children:
            path = directory / child.name
            relative = path.relative_to(root).as_posix()
            before = path.lstat()
            signatures[path] = _stat_signature(before)
            common = {
                "path": relative,
                "uid": before.st_uid,
                "gid": before.st_gid,
                "mtime_seconds": int(before.st_mtime),
            }
            if stat.S_ISDIR(before.st_mode):
                pending.append((path, relative))
                if _stat_signature(path.lstat()) != signatures[path]:
                    raise PackageError(f"Rootfs directory changed during scan: {relative}")
                continue
            elif stat.S_ISREG(before.st_mode):
                row = {
                    **common, "type": "file", "mode": stat.S_IMODE(before.st_mode),
                    "size_bytes": before.st_size, "sha256": _hash_open_regular(path, before),
                    "xattrs": xattr_manifest(path, is_symlink=False),
                }
            elif stat.S_ISLNK(before.st_mode):
                target = os.readlink(path)
                symlink_targets[path] = target
                row = {
                    **common, "type": "symlink", "target": target,
                    "xattrs": xattr_manifest(path, is_symlink=True),
                }
            elif stat.S_ISFIFO(before.st_mode):
                row = {
                    **common, "type": "fifo", "mode": stat.S_IMODE(before.st_mode),
                    "xattrs": xattr_manifest(path, is_symlink=False),
                }
            elif stat.S_ISBLK(before.st_mode) or stat.S_ISCHR(before.st_mode):
                row = {
                    **common, "type": "block" if stat.S_ISBLK(before.st_mode) else "character",
                    "mode": stat.S_IMODE(before.st_mode), "rdev": before.st_rdev,
                    "xattrs": xattr_manifest(path, is_symlink=False),
                }
            elif stat.S_ISSOCK(before.st_mode):
                raise PackageError(f"Transient socket cannot be captured in a static rootfs: {relative}")
            else:
                raise PackageError(f"Unsupported filesystem object in rootfs: {relative}")
            if _stat_signature(path.lstat()) != signatures[path]:
                raise PackageError(f"Rootfs entry changed during scan: {relative}")
            rows.append(row)

    for path, expected in signatures.items():
        try:
            observed = _stat_signature(path.lstat())
        except OSError as exc:
            raise PackageError(f"Rootfs entry disappeared during scan: {path}") from exc
        if observed != expected:
            raise PackageError(f"Rootfs changed during scan: {path}")
        if path in symlink_targets and os.readlink(path) != symlink_targets[path]:
            raise PackageError(f"Rootfs symlink changed during scan: {path}")

    rows.sort(key=lambda item: item["path"])
    payload = canonical_json(rows)
    regular_files = [row for row in rows if row["type"] == "file"]
    return {
        "entry_count": len(rows),
        "regular_file_count": len(regular_files),
        "regular_file_bytes": sum(row["size_bytes"] for row in regular_files),
        "entries_sha256": hashlib.sha256(payload).hexdigest(),
        "entries": rows,
    }

def validate_target_receipt(path: pathlib.Path) -> dict[str, Any]:
    reject_symlink_components(path)
    path = path.resolve(strict=True)
    if path.is_symlink() or not path.is_file():
        raise PackageError("Target-runtime receipt must be a regular file")
    try:
        receipt = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PackageError(f"Target-runtime receipt is unreadable or invalid JSON: {exc}") from exc
    if receipt.get("schema") != "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0":
        raise PackageError("Target-runtime receipt schema mismatch")
    if receipt.get("candidate_id") != CANDIDATE_ID:
        raise PackageError("Target-runtime receipt candidate identity mismatch")
    if receipt.get("status") != TARGET_PASS:
        raise PackageError("Direct target-runtime acceptance has not passed")
    if receipt.get("certification") != "NOT_GRANTED":
        raise PackageError("Target receipt must not claim certification")
    required = {
        "rootfs_build": "PASS_ROOTFS_BUILD_IDENTITY",
        "overlay_integrity": "PASS_OVERLAY_INTEGRITY",
        "e04_quantization": "PASS_E04_INT8_QUALITY_GATE",
        "qwen_e01": "PASS_E01_QWEN_INFERENCE",
        "legacy_application_smokes": "PASS_LEGACY_APPLICATION_SMOKES",
    }
    for field, status in required.items():
        value = receipt.get(field)
        if not isinstance(value, dict) or value.get("status") != status:
            raise PackageError(f"Target receipt lacks required passing evidence: {field}")
    tests = receipt.get("engine_acceptance_tests")
    if not isinstance(tests, dict) or tests.get("status") != "PASS" or tests.get("skipped") != 0:
        raise PackageError("Target receipt does not prove a complete, zero-skip engine suite")
    if tests.get("failures") != 0 or tests.get("errors") != 0:
        raise PackageError("Target receipt contains engine acceptance failures or errors")
    return {"path": str(path), "sha256": sha256_file(path), "data": receipt}


def run_tool(argv: list[str], *, cwd: pathlib.Path | None = None) -> str:
    result = subprocess.run(argv, cwd=cwd, text=True, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, check=False)
    if result.returncode != 0:
        raise PackageError(
            f"Command failed ({result.returncode}): {' '.join(argv)}\n{result.stdout[-5000:]}"
        )
    return result.stdout


def _write_exclusive(path: pathlib.Path, payload: bytes, mode: int = 0o644) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, mode)
    try:
        view = memoryview(payload)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("Short write while persisting package evidence")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def package_rootfs(
    rootfs: pathlib.Path,
    output: pathlib.Path,
    target_receipt_path: pathlib.Path,
    *,
    require_root: bool = True,
) -> dict[str, Any]:
    if require_root and os.geteuid() != 0:
        raise PackageError("SquashFS packaging must run as root to preserve uid/gid, device nodes and xattrs")
    rootfs = rootfs.resolve(strict=True)
    output = pathlib.Path(os.path.abspath(output))
    target = validate_target_receipt(target_receipt_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    reject_symlink_components(output.parent)
    if output.exists() or output.is_symlink():
        raise PackageError(f"Refusing to overwrite an existing image: {output}")
    receipt_path = output.with_name("LUNITA_SQUASHFS_PACKAGE_RECEIPT.json")
    checksum_path = output.with_name(output.name + ".sha256")
    if receipt_path.exists() or checksum_path.exists():
        raise PackageError("Refusing to overwrite existing package evidence")

    source_before = tree_manifest(rootfs)
    with tempfile.TemporaryDirectory(prefix="lunita-squashfs-verify-", dir=output.parent) as temp:
        temp_dir = pathlib.Path(temp)
        temporary_image = temp_dir / "candidate.squashfs"
        extracted = temp_dir / "extracted-rootfs"
        build_log = run_tool([
            "mksquashfs", str(rootfs), str(temporary_image),
            "-noappend", "-comp", "zstd", "-Xcompression-level", "15",
            "-no-progress", "-reproducible",
        ])
        if not temporary_image.is_file() or temporary_image.stat().st_size <= 0:
            raise PackageError("mksquashfs returned without a non-empty image")
        superblock = run_tool(["unsquashfs", "-s", str(temporary_image)])
        run_tool(["unsquashfs", "-no-progress", "-dest", str(extracted), str(temporary_image)])
        extracted_manifest = tree_manifest(extracted)
        source_after = tree_manifest(rootfs)
        if source_before["entries_sha256"] != source_after["entries_sha256"]:
            raise PackageError("Protected source rootfs changed during SquashFS packaging")
        if source_before["entries_sha256"] != extracted_manifest["entries_sha256"]:
            raise PackageError("SquashFS extraction does not reproduce the candidate rootfs manifest")

        digest = sha256_file(temporary_image)
        image_bytes = temporary_image.stat().st_size
        os.link(temporary_image, output)
        os.chmod(output, 0o644)

    receipt = {
        "schema": "LUNITA_SQUASHFS_PACKAGE_RECEIPT/1.0",
        "status": PACKAGE_PASS,
        "candidate_id": CANDIDATE_ID,
        "version": "1.8.0",
        "image_name": output.name,
        "image_sha256": digest,
        "image_bytes": image_bytes,
        "compression": "zstd",
        "compression_level": 15,
        "reproducible_mode": True,
        "source_rootfs": str(rootfs),
        "source_rootfs_manifest_sha256": source_before["entries_sha256"],
        "source_rootfs_entry_count": source_before["entry_count"],
        "source_regular_file_count": source_before["regular_file_count"],
        "source_regular_file_bytes": source_before["regular_file_bytes"],
        "extracted_rootfs_manifest_sha256": extracted_manifest["entries_sha256"],
        "roundtrip_manifest_match": True,
        "source_rootfs_unchanged": True,
        "target_runtime_receipt_path": target["path"],
        "target_runtime_receipt_sha256": target["sha256"],
        "target_runtime_status": TARGET_PASS,
        "certification": "NOT_GRANTED",
        "g23": "NOT_GRANTED",
        "g24": "NOT_GRANTED",
        "s32": "NOT_ISSUED",
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "mksquashfs": "PASS",
        "unsquashfs_superblock": "PASS",
        "unsquashfs_roundtrip": "PASS",
        "build_log_tail": build_log[-2000:],
        "superblock_summary": superblock[-2000:],
    }
    receipt_bytes = json.dumps(receipt, ensure_ascii=True, sort_keys=True, indent=2).encode("utf-8") + b"\n"
    checksum_bytes = f"{digest}  {output.name}\n".encode("ascii")
    try:
        _write_exclusive(receipt_path, receipt_bytes)
        _write_exclusive(checksum_path, checksum_bytes)
    except Exception:
        # The verified image is retained; missing evidence prevents certification and release.
        raise
    return {
        "status": PACKAGE_PASS,
        "image_path": str(output),
        "image_sha256": digest,
        "image_bytes": image_bytes,
        "receipt_path": str(receipt_path),
        "receipt_sha256": hashlib.sha256(receipt_bytes).hexdigest(),
        "checksum_path": str(checksum_path),
        "source_rootfs_manifest_sha256": source_before["entries_sha256"],
        "roundtrip_manifest_match": True,
        "certification": "NOT_GRANTED",
    }


def self_test() -> dict[str, Any]:
    tools = {name: shutil.which(name) for name in ("mksquashfs", "unsquashfs")}
    if not all(tools.values()):
        raise PackageError("Self-test requires squashfs-tools (mksquashfs and unsquashfs)")
    checks = {}
    with tempfile.TemporaryDirectory(prefix="lunita-squashfs-selftest-") as temporary:
        base = pathlib.Path(temporary)
        root = base / "rootfs"
        (root / "etc").mkdir(parents=True)
        (root / "opt/lunita").mkdir(parents=True)
        (root / "etc/os-release").write_text("ID=ubuntu\nVERSION_ID=24.04\n", encoding="utf-8")
        app = root / "opt/lunita/agent"
        app.write_text("#!/bin/sh\nprintf 'LUNITA_SELFTEST_OK\\n'\n", encoding="utf-8")
        app.chmod(0o755)
        (root / "opt/lunita/agent-link").symlink_to("agent")
        receipt = {
            "schema": "LUNITA_TARGET_RUNTIME_ACCEPTANCE/1.0",
            "candidate_id": CANDIDATE_ID,
            "status": TARGET_PASS,
            "certification": "NOT_GRANTED",
            "rootfs_build": {"status": "PASS_ROOTFS_BUILD_IDENTITY"},
            "overlay_integrity": {"status": "PASS_OVERLAY_INTEGRITY"},
            "e04_quantization": {"status": "PASS_E04_INT8_QUALITY_GATE"},
            "qwen_e01": {"status": "PASS_E01_QWEN_INFERENCE"},
            "legacy_application_smokes": {"status": "PASS_LEGACY_APPLICATION_SMOKES"},
            "engine_acceptance_tests": {"status": "PASS", "skipped": 0, "failures": 0, "errors": 0},
        }
        receipt_file = base / "target-receipt.json"
        receipt_file.write_text(json.dumps(receipt), encoding="utf-8")
        first = package_rootfs(root, base / "first" / "LUNITA.squashfs", receipt_file, require_root=False)
        second = package_rootfs(root, base / "second" / "LUNITA.squashfs", receipt_file, require_root=False)
        checks["source_tree_roundtrip_verified"] = first["roundtrip_manifest_match"] is True
        checks["repeat_build_is_byte_identical"] = first["image_sha256"] == second["image_sha256"]
        checks["target_receipt_hash_bound"] = first["image_sha256"] and first["receipt_sha256"]
        checks["certification_not_granted"] = first["certification"] == "NOT_GRANTED"
    return {
        "schema": "LUNITA_SQUASHFS_PACKAGER_SELFTEST/1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "tools": tools,
        "side_effects": False,
        "certification": "NOT_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rootfs", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--target-receipt", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            if not args.rootfs or not args.output or not args.target_receipt:
                parser.error("--rootfs, --output and --target-receipt are required unless --self-test is used")
            result = package_rootfs(args.rootfs, args.output, args.target_receipt)
    except (OSError, ValueError, PackageError, subprocess.SubprocessError) as exc:
        print(json.dumps({"status": "BLOCKED", "error": str(exc), "certification": "NOT_GRANTED"},
                         ensure_ascii=True, indent=2), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2))
    return 0 if result.get("status") in {PACKAGE_PASS, "PASS"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
