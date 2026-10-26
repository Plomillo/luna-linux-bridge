#!/usr/bin/env python3
"""Fail-closed Cajita entry point for the pinned Calibre Slim PDF/EPUB overlay."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
import stat
from pathlib import Path, PurePosixPath

INPUTS = {".pdf", ".epub", ".txt"}
OUTPUTS = {".pdf", ".epub"}
COMMAND = "ebook-convert"
ARCHIVE_NAME = "calibre-slim-overlay.tar.xz"
ARCHIVE_BYTES = 58180
ARCHIVE_SHA256 = "dc1518eccd24d0bb6a294918381d9d42fa24df8b05026d1f173dadbd6e70977b"


def fail(message: str, code: int = 2) -> int:
    print(f"FAIL_CLOSED: {message}", file=sys.stderr)
    return code


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _validated_archive_inventory(archive: Path) -> tuple[dict[str, bytes], dict[str, int], set[str]]:
    """Read and validate the pinned overlay before trusting either it or its cache."""
    file_bytes: dict[str, bytes] = {}
    file_modes: dict[str, int] = {}
    directories: set[str] = set()
    seen: set[str] = set()
    with tarfile.open(archive, mode="r:xz") as bundle:
        for member in bundle.getmembers():
            raw = member.name
            parsed = PurePosixPath(raw)
            if "\\" in raw or parsed.is_absolute() or any(part == ".." for part in parsed.parts):
                raise RuntimeError(f"unsafe archive path: {raw!r}")
            parts = tuple(part for part in parsed.parts if part not in ("", "."))
            if not parts or (":" in parts[0]):
                raise RuntimeError(f"unsafe archive path: {raw!r}")
            normalized = "/".join(parts)
            if normalized in seen:
                raise RuntimeError(f"duplicate archive path: {normalized}")
            seen.add(normalized)
            if member.isdir():
                directories.add(normalized)
                continue
            if not member.isfile():
                raise RuntimeError(f"unsupported archive member type: {normalized}")
            source_stream = bundle.extractfile(member)
            if source_stream is None:
                raise RuntimeError(f"could not read archive member: {normalized}")
            with source_stream:
                payload = source_stream.read()
            file_bytes[normalized] = payload
            file_modes[normalized] = member.mode & 0o777

    for name in file_bytes:
        parent = PurePosixPath(name).parent
        while parent.as_posix() not in ("", "."):
            directories.add(parent.as_posix())
            parent = parent.parent
    collision = set(file_bytes).intersection(directories)
    if collision:
        raise RuntimeError("archive file/directory path collision: " + ",".join(sorted(collision)))
    return file_bytes, file_modes, directories


def _overlay_tree_inventory(root: Path) -> tuple[dict[str, dict], set[str]]:
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("MATERIALIZED_OVERLAY_CACHE_UNSAFE")
    base = root.resolve(strict=True)
    files: dict[str, dict] = {}
    directories: set[str] = set()
    for current, dirs, names in os.walk(base, topdown=True, followlinks=False):
        current_path = Path(current)
        safe_dirs = []
        for name in sorted(dirs):
            item = current_path / name
            if item.is_symlink() or not item.resolve(strict=True).is_relative_to(base):
                raise RuntimeError("MATERIALIZED_OVERLAY_CACHE_SYMLINK_OR_ESCAPE")
            directories.add(item.relative_to(base).as_posix())
            safe_dirs.append(name)
        dirs[:] = safe_dirs
        for name in sorted(names):
            item = current_path / name
            if item.is_symlink() or not item.is_file() or not item.resolve(strict=True).is_relative_to(base):
                raise RuntimeError("MATERIALIZED_OVERLAY_CACHE_NON_REGULAR_OR_ESCAPE")
            rel = item.relative_to(base).as_posix()
            files[rel] = {
                "bytes": item.stat().st_size,
                "sha256": sha256_file(item),
                "mode": stat.S_IMODE(item.stat().st_mode),
            }
    return files, directories


def materialize_overlay(here: Path) -> Path:
    here = Path(here).resolve(strict=True)
    root = here / ".calibre-slim-overlay"
    source = root / "source"
    archive = here / ARCHIVE_NAME
    if archive.is_symlink() or not archive.is_file():
        raise RuntimeError(f"required embedded archive is missing or unsafe: {archive}")
    actual_size = archive.stat().st_size
    if actual_size != ARCHIVE_BYTES:
        raise RuntimeError(f"archive size mismatch: expected {ARCHIVE_BYTES}, got {actual_size}")
    actual_hash = sha256_file(archive)
    if actual_hash != ARCHIVE_SHA256:
        raise RuntimeError(f"archive SHA-256 mismatch: {actual_hash}")

    # Always validate the source archive and all cached members. The original
    # fast-path trusted one existing file and would silently accept a modified cache.
    file_bytes, file_modes, expected_directories = _validated_archive_inventory(archive)
    expected_files = {
        name: {"bytes": len(payload), "sha256": hashlib.sha256(payload).hexdigest(), "mode": file_modes[name]}
        for name, payload in file_bytes.items()
    }
    if root.is_symlink():
        raise RuntimeError("MATERIALIZED_OVERLAY_CACHE_UNSAFE")
    if root.exists():
        observed_files, observed_directories = _overlay_tree_inventory(root)
        if observed_files != expected_files or observed_directories != expected_directories:
            raise RuntimeError("MATERIALIZED_OVERLAY_TREE_HASH_MISMATCH")
        if not (source / "calibre" / "customize" / "builtins.py").is_file():
            raise RuntimeError("MATERIALIZED_OVERLAY_REQUIRED_REGISTRY_MISSING")
        return source

    staging = here / ".calibre-slim-overlay.staging"
    if staging.is_symlink():
        raise RuntimeError("MATERIALIZED_OVERLAY_STAGING_UNSAFE")
    if staging.exists():
        if not staging.is_dir():
            raise RuntimeError("MATERIALIZED_OVERLAY_STAGING_UNSAFE")
        shutil.rmtree(staging)
    staging.mkdir(mode=0o700)
    try:
        for name in sorted(expected_directories, key=lambda value: (value.count("/"), value)):
            (staging / Path(*PurePosixPath(name).parts)).mkdir(parents=True, exist_ok=True)
        for name, payload in sorted(file_bytes.items()):
            target = staging / Path(*PurePosixPath(name).parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                output.write(payload)
            target.chmod(file_modes[name])
        observed_files, observed_directories = _overlay_tree_inventory(staging)
        if observed_files != expected_files or observed_directories != expected_directories:
            raise RuntimeError("MATERIALIZED_OVERLAY_EXTRACTION_HASH_MISMATCH")
        if not (staging / "source" / "calibre" / "customize" / "builtins.py").is_file():
            raise RuntimeError("embedded overlay did not contain source/calibre/customize/builtins.py")
        os.replace(staging, root)
        return source
    except Exception:
        if staging.exists() and staging.is_dir() and not staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
        raise


def verify_pinned_converter(converter: str, here: Path) -> dict:
    """Require the official runtime version declared by the source lock."""
    lock_path = here / "source-lock.json"
    if lock_path.is_symlink() or not lock_path.is_file():
        raise RuntimeError("CALIBRE_SOURCE_LOCK_MISSING_OR_UNSAFE")
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if (
        lock.get("schema") != "CAJITA_CALIBRE_SLIM_SOURCE_LOCK/1.0"
        or lock.get("upstream_repository") != "https://github.com/kovidgoyal/calibre"
        or lock.get("tag") != "v9.17.0"
        or lock.get("commit_sha") != "e6b9e09472f6e63f8a12bf376eb54836042f0f5f"
    ):
        raise RuntimeError("CALIBRE_SOURCE_LOCK_IDENTITY_MISMATCH")
    executable = Path(converter).resolve(strict=True)
    if not executable.is_file() or not os.access(executable, os.X_OK):
        raise RuntimeError("CALIBRE_CONVERTER_NOT_EXECUTABLE")
    try:
        probe = subprocess.run(
            [str(executable), "--version"],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=20, check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError("CALIBRE_CONVERTER_VERSION_PROBE_FAILED:" + type(exc).__name__) from exc
    output = probe.stdout[-2000:]
    if probe.returncode != 0 or "9.17.0" not in output:
        raise RuntimeError("CALIBRE_RUNTIME_VERSION_MISMATCH:" + output[-500:])
    return {"executable": str(executable), "version_output": output, "expected_version": "9.17.0", "status": "PASS_PINNED_VERSION"}


def main(argv: list[str]) -> int:
    if argv in (["--help"], ["-h"]):
        print("Usage: python3 calibre-slim-convert.py INPUT.(pdf|epub|txt) OUTPUT.(pdf|epub) [Calibre options]")
        return 0
    if len(argv) < 2 or argv[0].startswith("-") or argv[1].startswith("-"):
        return fail("usage: INPUT OUTPUT [Calibre options]")

    source = Path(argv[0]).expanduser().resolve()
    destination = Path(argv[1]).expanduser().resolve()
    source_ext, output_ext = source.suffix.lower(), destination.suffix.lower()
    if source_ext not in INPUTS:
        return fail(f"unsupported input format: {source_ext or '(no extension)'}")
    if output_ext not in OUTPUTS:
        return fail(f"only PDF and EPUB outputs are permitted: {output_ext or '(no extension)'}")
    if not source.is_file() or not os.access(source, os.R_OK):
        return fail(f"input is missing or unreadable: {source}")
    if source == destination:
        return fail("input and output paths must differ")
    if destination.exists() and destination.is_dir():
        return fail("output path is a directory")

    here = Path(__file__).resolve().parent
    try:
        overlay_source = materialize_overlay(here)
    except (OSError, RuntimeError, tarfile.TarError) as exc:
        return fail(f"cannot verify/materialize the pinned Calibre overlay: {exc}", 78)

    configured = os.environ.get("CALIBRE_EBOOK_CONVERT")
    candidates = [Path(configured)] if configured else []
    candidates.extend([here / COMMAND, here / "bin" / COMMAND, here / "usr" / "bin" / COMMAND])
    converter = next((str(p) for p in candidates if p.is_file() and os.access(p, os.X_OK)), None)
    converter = converter or shutil.which(COMMAND)
    if not converter:
        return fail("official Calibre ebook-convert runtime not found; set CALIBRE_EBOOK_CONVERT", 78)
    try:
        runtime_identity = verify_pinned_converter(converter, here)
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return fail(f"cannot verify the pinned official Calibre runtime: {exc}", 78)
    print(f"CALIBRE_RUNTIME_IDENTITY={json.dumps(runtime_identity, sort_keys=True)}")

    env = os.environ.copy()
    env["CALIBRE_DEVELOP_FROM"] = str(overlay_source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run([converter, str(source), str(destination), *argv[2:]], env=env, check=False).returncode
    except OSError as exc:
        return fail(f"unable to launch ebook-convert: {exc}", 78)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
