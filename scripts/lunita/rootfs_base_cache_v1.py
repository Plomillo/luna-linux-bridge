#!/usr/bin/env python3
"""Hash-bound, fail-closed cache for the pristine Lunita v1.8 Ubuntu rootfs base."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA = "LUNITA_ROOTFS_BASE_CACHE/1.0"
CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
CANDIDATE_VERSION = "1.8.0"
SOURCE_PATHS = (
    "scripts/lunita/build_rootfs_candidate_v1.sh",
    "scripts/lunita/brujula.js",
    "recovery/lunita-custoszv9/lunita_beta_v1_7.py",
    "scripts/lunita/rootfs_base_cache_v1.py",
)
RECEIPT_RELATIVE = Path("opt/lunita/metadata/ROOTFS_BUILD_RECEIPT.json")
CACHE_RECEIPT_NAME = "LUNITA_ROOTFS_BASE_CACHE_RECEIPT.json"
ARCHIVE_NAME = "LUNITA_ROOTFS_BASE.tar"


def deny(message: str) -> "NoReturn":
    raise SystemExit(f"ROOTFS_BASE_CACHE_BLOCKED: {message}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def input_identity(workspace: Path) -> tuple[dict[str, str], str]:
    sources: dict[str, str] = {}
    for relative in SOURCE_PATHS:
        path = workspace / relative
        if path.is_symlink() or not path.is_file():
            deny(f"required rootfs input is missing or unsafe: {relative}")
        sources[relative] = sha256_file(path)
    fingerprint = hashlib.sha256(canonical_bytes(sources)).hexdigest()
    return sources, fingerprint


def load_json(path: Path, description: str) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        deny(f"{description} is missing or unsafe: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        deny(f"{description} is not valid UTF-8 JSON: {exc}")
    if not isinstance(value, dict):
        deny(f"{description} must be a JSON object")
    return value


def validate_rootfs_identity(rootfs: Path) -> tuple[dict[str, Any], str]:
    if rootfs.is_symlink() or not rootfs.is_dir():
        deny(f"rootfs path is missing, not a directory, or a symlink: {rootfs}")
    for mount_name in ("dev", "proc", "sys", "run"):
        mount_path = rootfs / mount_name
        if mount_path.exists() and os.path.ismount(mount_path):
            deny(f"rootfs still contains an active mount: {mount_name}")
    overlay = rootfs / "opt/lunita/engines/runtime_engines_v1"
    if overlay.exists():
        deny("base rootfs is not pristine: engine overlay already exists")
    receipt_path = rootfs / RECEIPT_RELATIVE
    build = load_json(receipt_path, "Ubuntu rootfs build receipt")
    if build.get("schema") != "LUNITA_ROOTFS_BUILD_RECEIPT/1.0":
        deny("Ubuntu rootfs build receipt schema mismatch")
    if build.get("status") != "PASS_ROOTFS_BUILD_NOT_CERTIFIED":
        deny("Ubuntu rootfs build receipt is not a passing, non-certifying build receipt")
    if build.get("candidate_id") != CANDIDATE_ID or build.get("version") != CANDIDATE_VERSION:
        deny("Ubuntu rootfs candidate identity mismatch")
    if build.get("rootfs_origin") != "REBUILT_FROM_PINNED_SOURCES_ON_GITHUB_ACTIONS":
        deny("Ubuntu rootfs origin is not the expected pinned-source builder")
    ubuntu = build.get("ubuntu", {})
    if not isinstance(ubuntu, dict) or ubuntu.get("release") != "24.04" or ubuntu.get("codename") != "noble" or ubuntu.get("architecture") != "amd64":
        deny("Ubuntu rootfs release, codename, or architecture mismatch")
    labels = build.get("label_hierarchy", {})
    if not isinstance(labels, dict) or labels.get("schema") != "LUNITA_LABEL_HIERARCHY/1.0":
        deny("rootfs build receipt does not bind the expected label hierarchy")
    for key in ("json_path", "json_sha256", "text_path", "text_sha256"):
        if not isinstance(labels.get(key), str) or not labels[key]:
            deny(f"rootfs label hierarchy binding is incomplete: {key}")
    for path_key, digest_key in (("json_path", "json_sha256"), ("text_path", "text_sha256")):
        relative = Path(labels[path_key].lstrip("/"))
        if relative.is_absolute() or ".." in relative.parts:
            deny(f"unsafe rootfs label metadata path: {labels[path_key]}")
        label_path = rootfs / relative
        if label_path.is_symlink() or not label_path.is_file():
            deny(f"rootfs label metadata is missing or unsafe: {labels[path_key]}")
        if sha256_file(label_path) != labels[digest_key]:
            deny(f"rootfs label metadata digest mismatch: {labels[path_key]}")
    hierarchy = load_json(rootfs / Path(labels["json_path"].lstrip("/")), "rootfs label hierarchy")
    if hierarchy.get("schema") != "LUNITA_LABEL_HIERARCHY/1.0":
        deny("rootfs label hierarchy schema mismatch")
    return build, sha256_file(receipt_path)



def canonical_console_mode(
    *,
    is_character: bool,
    major: int,
    minor: int,
    uid: int,
    gid: int,
    mode: int,
) -> int:
    """Validate Ubuntu's exact console identity and return its restrictive mode."""
    if not (is_character and major == 5 and minor == 1 and uid == 0 and gid == 0):
        deny(
            "rootfs /dev/console identity mismatch: "
            f"type={'character' if is_character else 'non-character'} "
            f"major={major} minor={minor} uid={uid} gid={gid}"
        )
    # The pinned Ubuntu bootstrap may leave the canonical 5:1 node at 0666.
    # Accept only that known source mode (or already-hardened 0600), then
    # normalize it to root-only access before archive creation.
    if mode not in (0o600, 0o666):
        deny(f"rootfs /dev/console has an unapproved source mode: {oct(mode)}")
    return 0o600


def normalize_console_device(rootfs: Path) -> dict[str, Any]:
    """Harden only the exact root-owned 5:1 console node before caching."""
    dev_dir = rootfs / "dev"
    if dev_dir.is_symlink():
        deny("rootfs /dev must not be a symlink")
    if not dev_dir.exists():
        return {"path": "dev/console", "present": False, "normalization": "NOT_PRESENT"}
    if not dev_dir.is_dir():
        deny("rootfs /dev is not a directory")
    console = dev_dir / "console"
    if console.is_symlink():
        deny("rootfs /dev/console must not be a symlink")
    try:
        before = console.lstat()
    except FileNotFoundError:
        return {"path": "dev/console", "present": False, "normalization": "NOT_PRESENT"}
    is_character = stat.S_ISCHR(before.st_mode)
    source_mode = stat.S_IMODE(before.st_mode)
    target_mode = canonical_console_mode(
        is_character=is_character,
        major=os.major(before.st_rdev) if is_character else -1,
        minor=os.minor(before.st_rdev) if is_character else -1,
        uid=before.st_uid,
        gid=before.st_gid,
        mode=source_mode,
    )
    if source_mode != target_mode:
        os.chmod(console, target_mode, follow_symlinks=False)
    after = console.lstat()
    if (
        not stat.S_ISCHR(after.st_mode)
        or os.major(after.st_rdev) != 5
        or os.minor(after.st_rdev) != 1
        or after.st_uid != 0
        or after.st_gid != 0
        or stat.S_IMODE(after.st_mode) != target_mode
    ):
        deny("rootfs /dev/console failed post-normalization verification")
    return {
        "path": "dev/console",
        "present": True,
        "type": "character",
        "major": 5,
        "minor": 1,
        "uid": 0,
        "gid": 0,
        "source_mode_octal": oct(source_mode),
        "normalized_mode_octal": oct(target_mode),
        "normalization": "ALREADY_CANONICAL" if source_mode == target_mode else "HARDENED_TO_0600",
    }


def normalized_archive_path(name: str) -> str:
    path = PurePosixPath(name)
    parts = path.parts[1:] if path.parts and path.parts[0] == "." else path.parts
    return "/".join(parts) if parts else "."


def validate_archive_paths(archive: Path) -> None:
    """Reject unsafe paths and every special entry except Ubuntu's canonical /dev/console."""
    seen_paths: set[str] = set()
    try:
        with tarfile.open(archive, mode="r:") as bundle:
            for member in bundle:
                name = PurePosixPath(member.name)
                if name.is_absolute() or ".." in name.parts:
                    deny(f"unsafe archive member path: {member.name}")
                relative_name = normalized_archive_path(member.name)
                if relative_name in seen_paths:
                    deny(f"duplicate rootfs cache archive path: {member.name}")
                seen_paths.add(relative_name)
                if member.isdev():
                    # Ubuntu's boot console is a required static rootfs device node.
                    # No other block/character device or altered console metadata is admitted.
                    canonical_console = (
                        relative_name == "dev/console"
                        and member.ischr()
                        and member.devmajor == 5
                        and member.devminor == 1
                        and member.uid == 0
                        and member.gid == 0
                        and member.mode == 0o600
                    )
                    if not canonical_console:
                        deny(
                            "non-canonical device node is forbidden in rootfs cache: "
                            f"{member.name} type={'character' if member.ischr() else 'block'} "
                            f"major={member.devmajor} minor={member.devminor} "
                            f"uid={member.uid} gid={member.gid} mode={oct(member.mode)}"
                        )
                if member.isfifo():
                    deny(f"FIFO filesystem entry is forbidden in rootfs cache: {member.name}")
                if member.issym() and not PurePosixPath(member.linkname).is_absolute():
                    stack: list[str] = []
                    for part in (name.parent / PurePosixPath(member.linkname)).parts:
                        if part in ("", ".", "/"):
                            continue
                        if part == "..":
                            if not stack:
                                deny(f"rootfs symlink escapes extraction root: {member.name}")
                            stack.pop()
                        else:
                            stack.append(part)
                if member.islnk():
                    link = PurePosixPath(member.linkname)
                    if link.is_absolute() or ".." in link.parts:
                        deny(f"unsafe hardlink target in rootfs cache: {member.name}")
    except SystemExit:
        raise
    except Exception as exc:
        deny(f"rootfs cache archive cannot be inspected: {exc}")


def cache_paths(cache_dir: Path) -> tuple[Path, Path]:
    return cache_dir / ARCHIVE_NAME, cache_dir / CACHE_RECEIPT_NAME


def pack_base(workspace: Path, rootfs: Path, cache_dir: Path, commit: str) -> dict[str, Any]:
    sources, fingerprint = input_identity(workspace)
    build, build_receipt_sha = validate_rootfs_identity(rootfs)
    console_policy = normalize_console_device(rootfs)
    cache_dir.mkdir(parents=True, exist_ok=True)
    if cache_dir.is_symlink():
        deny("cache directory must not be a symlink")
    archive, receipt_path = cache_paths(cache_dir)
    if archive.exists() or receipt_path.exists():
        deny("refusing to overwrite an existing rootfs cache snapshot")
    temporary = cache_dir / f".{ARCHIVE_NAME}.{os.getpid()}.tmp"
    command = [
        "tar", "--sort=name", "--numeric-owner", "--format=posix",
        "--xattrs", "--acls", "--sparse", "-cpf", str(temporary),
        "-C", str(rootfs), ".",
    ]
    try:
        subprocess.run(command, check=True)
        # Validate before publishing the snapshot: a bad first fill must never
        # poison the cache and fail only on a later cache hit.
        validate_archive_paths(temporary)
        with temporary.open("rb") as stream:
            os.fsync(stream.fileno())
        archive_sha = sha256_file(temporary)
        archive_bytes = temporary.stat().st_size
        os.chmod(temporary, 0o644)
        os.replace(temporary, archive)
        record = {
            "schema": SCHEMA,
            "status": "PASS_PRISTINE_ROOTFS_BASE_PACKED",
            "candidate_id": CANDIDATE_ID,
            "candidate_version": CANDIDATE_VERSION,
            "ubuntu": {"release": "24.04", "codename": "noble", "architecture": "amd64"},
            "input_fingerprint_sha256": fingerprint,
            "input_sources": sources,
            "rootfs_build_receipt_sha256": build_receipt_sha,
            "rootfs_build_status": build["status"],
            "rootfs_console_policy": console_policy,
            "archive": {
                "file": ARCHIVE_NAME,
                "sha256": archive_sha,
                "bytes": archive_bytes,
            },
            "created_from_commit": commit or "unknown",
            "cache_scope": "PRISTINE_BASE_ONLY;OVERLAY_AND_RUNTIME_RECEIPTS_EXCLUDED",
        }
        receipt_tmp = cache_dir / f".{CACHE_RECEIPT_NAME}.{os.getpid()}.tmp"
        receipt_tmp.write_bytes(canonical_bytes(record))
        os.chmod(receipt_tmp, 0o644)
        os.replace(receipt_tmp, receipt_path)
        print(f"PASS_ROOTFS_BASE_CACHE_PACKED sha256={archive_sha} bytes={archive_bytes} fingerprint={fingerprint}")
        return record
    finally:
        temporary.unlink(missing_ok=True)


def verify_cache(workspace: Path, cache_dir: Path) -> tuple[Path, dict[str, Any]]:
    sources, fingerprint = input_identity(workspace)
    archive, receipt_path = cache_paths(cache_dir)
    record = load_json(receipt_path, "rootfs base cache receipt")
    if record.get("schema") != SCHEMA or record.get("status") != "PASS_PRISTINE_ROOTFS_BASE_PACKED":
        deny("rootfs base cache receipt schema or status mismatch")
    if record.get("candidate_id") != CANDIDATE_ID or record.get("candidate_version") != CANDIDATE_VERSION:
        deny("rootfs base cache candidate identity mismatch")
    if record.get("input_fingerprint_sha256") != fingerprint or record.get("input_sources") != sources:
        deny("rootfs base cache does not match the current rootfs builder inputs")
    if not archive.is_file() or archive.is_symlink():
        deny("cached rootfs archive is missing or unsafe")
    bound = record.get("archive", {})
    if not isinstance(bound, dict) or bound.get("file") != ARCHIVE_NAME:
        deny("rootfs cache receipt archive binding is malformed")
    actual_bytes = archive.stat().st_size
    if bound.get("bytes") != actual_bytes:
        deny("cached rootfs archive size mismatch")
    actual_sha = sha256_file(archive)
    if bound.get("sha256") != actual_sha:
        deny("cached rootfs archive SHA-256 mismatch")
    validate_archive_paths(archive)
    return archive, record


def restore_base(workspace: Path, cache_dir: Path, rootfs: Path) -> None:
    archive, record = verify_cache(workspace, cache_dir)
    if rootfs.exists() or rootfs.is_symlink():
        deny(f"refusing to overwrite existing rootfs path: {rootfs}")
    rootfs.mkdir(parents=True, exist_ok=False)
    try:
        subprocess.run([
            "tar", "--extract", "--numeric-owner", "--same-owner",
            "--same-permissions", "--xattrs", "--acls",
            "--file", str(archive), "--directory", str(rootfs),
        ], check=True)
        build, build_receipt_sha = validate_rootfs_identity(rootfs)
        if build_receipt_sha != record.get("rootfs_build_receipt_sha256"):
            deny("restored rootfs build receipt digest differs from the cache receipt")
        if build.get("status") != record.get("rootfs_build_status"):
            deny("restored rootfs build status differs from the cache receipt")
    except Exception:
        shutil.rmtree(rootfs, ignore_errors=True)
        raise
    print(
        "PASS_ROOTFS_BASE_CACHE_RESTORED "
        f"sha256={record['archive']['sha256']} "
        f"fingerprint={record['input_fingerprint_sha256']}"
    )


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="lunita-rootfs-cache-selftest-") as temporary:
        root = Path(temporary)
        workspace = root / "workspace"
        rootfs = root / "rootfs"
        restored = root / "restored"
        cache = root / "cache"

        if canonical_console_mode(
            is_character=True, major=5, minor=1, uid=0, gid=0, mode=0o666
        ) != 0o600:
            deny("self-test failed to harden canonical /dev/console mode 0666")
        if canonical_console_mode(
            is_character=True, major=5, minor=1, uid=0, gid=0, mode=0o600
        ) != 0o600:
            deny("self-test failed to preserve canonical /dev/console mode 0600")
        invalid_console_metadata = (
            {"is_character": False, "major": 5, "minor": 1, "uid": 0, "gid": 0, "mode": 0o600},
            {"is_character": True, "major": 1, "minor": 1, "uid": 0, "gid": 0, "mode": 0o600},
            {"is_character": True, "major": 5, "minor": 2, "uid": 0, "gid": 0, "mode": 0o600},
            {"is_character": True, "major": 5, "minor": 1, "uid": 1000, "gid": 0, "mode": 0o600},
            {"is_character": True, "major": 5, "minor": 1, "uid": 0, "gid": 1000, "mode": 0o600},
            {"is_character": True, "major": 5, "minor": 1, "uid": 0, "gid": 0, "mode": 0o644},
        )
        for metadata_case in invalid_console_metadata:
            try:
                canonical_console_mode(**metadata_case)
            except SystemExit:
                continue
            deny("self-test failed to reject altered /dev/console identity or permissions")

        # Admit only the canonical Ubuntu boot console device and reject
        # altered metadata, other device nodes, and FIFOs.
        valid_console_archive = root / "valid-console.tar"
        console = tarfile.TarInfo("./dev/console")
        console.type = tarfile.CHRTYPE
        console.mode = 0o600
        console.uid = 0
        console.gid = 0
        console.devmajor = 5
        console.devminor = 1
        with tarfile.open(valid_console_archive, "w") as bundle:
            bundle.addfile(console)
        validate_archive_paths(valid_console_archive)

        invalid_device_archive = root / "invalid-device.tar"
        invalid_device = tarfile.TarInfo("./dev/mem")
        invalid_device.type = tarfile.CHRTYPE
        invalid_device.mode = 0o600
        invalid_device.uid = 0
        invalid_device.gid = 0
        invalid_device.devmajor = 1
        invalid_device.devminor = 1
        with tarfile.open(invalid_device_archive, "w") as bundle:
            bundle.addfile(invalid_device)
        try:
            validate_archive_paths(invalid_device_archive)
        except SystemExit:
            pass
        else:
            deny("self-test failed to reject a non-canonical device node")

        altered_console_archive = root / "altered-console.tar"
        altered_console = tarfile.TarInfo("./dev/console")
        altered_console.type = tarfile.CHRTYPE
        altered_console.mode = 0o666
        altered_console.uid = 0
        altered_console.gid = 0
        altered_console.devmajor = 5
        altered_console.devminor = 1
        with tarfile.open(altered_console_archive, "w") as bundle:
            bundle.addfile(altered_console)
        try:
            validate_archive_paths(altered_console_archive)
        except SystemExit:
            pass
        else:
            deny("self-test failed to reject altered /dev/console permissions")

        for relative in SOURCE_PATHS:
            path = workspace / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"fixture:{relative}\n", encoding="utf-8")
        metadata = rootfs / "opt/lunita/metadata"
        metadata.mkdir(parents=True)
        label_json = canonical_bytes({
            "schema": "LUNITA_LABEL_HIERARCHY/1.0",
            "candidate_id": CANDIDATE_ID,
            "version": CANDIDATE_VERSION,
        })
        label_text = b"LA PIEZA\n"
        (metadata / "LUNITA_LABEL_HIERARCHY.json").write_bytes(label_json)
        (metadata / "LUNITA_LABEL_HIERARCHY.txt").write_bytes(label_text)
        build = {
            "schema": "LUNITA_ROOTFS_BUILD_RECEIPT/1.0",
            "status": "PASS_ROOTFS_BUILD_NOT_CERTIFIED",
            "candidate_id": CANDIDATE_ID,
            "version": CANDIDATE_VERSION,
            "rootfs_origin": "REBUILT_FROM_PINNED_SOURCES_ON_GITHUB_ACTIONS",
            "ubuntu": {"release": "24.04", "codename": "noble", "architecture": "amd64"},
            "label_hierarchy": {
                "schema": "LUNITA_LABEL_HIERARCHY/1.0",
                "json_path": "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.json",
                "json_sha256": hashlib.sha256(label_json).hexdigest(),
                "text_path": "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.txt",
                "text_sha256": hashlib.sha256(label_text).hexdigest(),
            },
        }
        (metadata / "ROOTFS_BUILD_RECEIPT.json").write_bytes(canonical_bytes(build))
        (rootfs / "sample.txt").write_text("rootfs fixture\n", encoding="utf-8")
        pack_base(workspace, rootfs, cache, "self-test")
        restore_base(workspace, cache, restored)
        if (restored / "sample.txt").read_text(encoding="utf-8") != "rootfs fixture\n":
            deny("self-test round-trip content mismatch")
        if sha256_file(restored / RECEIPT_RELATIVE) != sha256_file(rootfs / RECEIPT_RELATIVE):
            deny("self-test rootfs receipt mismatch")
        archive, _ = cache_paths(cache)
        original = archive.read_bytes()
        archive.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        try:
            verify_cache(workspace, cache)
        except SystemExit:
            pass
        else:
            deny("self-test failed to reject a tampered rootfs cache archive")
    print("PASS_ROOTFS_BASE_CACHE_SELF_TEST")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    pack = subparsers.add_parser("pack")
    pack.add_argument("--workspace", type=Path, required=True)
    pack.add_argument("--rootfs", type=Path, required=True)
    pack.add_argument("--cache-dir", type=Path, required=True)
    pack.add_argument("--commit", default="unknown")
    restore = subparsers.add_parser("restore")
    restore.add_argument("--workspace", type=Path, required=True)
    restore.add_argument("--cache-dir", type=Path, required=True)
    restore.add_argument("--rootfs", type=Path, required=True)
    subparsers.add_parser("self-test")
    args = parser.parse_args()
    if args.command == "pack":
        pack_base(args.workspace.resolve(), Path(os.path.abspath(args.rootfs)), Path(os.path.abspath(args.cache_dir)), args.commit)
    elif args.command == "restore":
        restore_base(args.workspace.resolve(), Path(os.path.abspath(args.cache_dir)), Path(os.path.abspath(args.rootfs)))
    else:
        self_test()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
