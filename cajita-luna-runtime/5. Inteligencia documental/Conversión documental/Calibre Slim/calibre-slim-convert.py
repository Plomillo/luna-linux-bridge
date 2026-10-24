#!/usr/bin/env python3
"""Fail-closed Cajita entry point for the pinned Calibre Slim PDF/EPUB overlay."""
from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tarfile
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


def materialize_overlay(here: Path) -> Path:
    root = here / ".calibre-slim-overlay"
    source = root / "source"
    registry = source / "calibre" / "customize" / "builtins.py"
    if registry.is_file():
        return source

    archive = here / ARCHIVE_NAME
    if not archive.is_file():
        raise RuntimeError(f"required embedded archive is missing: {archive}")
    actual_size = archive.stat().st_size
    if actual_size != ARCHIVE_BYTES:
        raise RuntimeError(f"archive size mismatch: expected {ARCHIVE_BYTES}, got {actual_size}")
    actual_hash = sha256_file(archive)
    if actual_hash != ARCHIVE_SHA256:
        raise RuntimeError(f"archive SHA-256 mismatch: {actual_hash}")
    if root.exists():
        raise RuntimeError(f"partial overlay directory exists without the required registry: {root}")

    staging = here / ".calibre-slim-overlay.staging"
    if staging.exists():
        if staging.is_symlink() or not staging.is_dir():
            raise RuntimeError(f"unsafe staging path: {staging}")
        shutil.rmtree(staging)
    staging.mkdir(mode=0o700)
    try:
        with tarfile.open(archive, mode="r:xz") as bundle:
            members = bundle.getmembers()
            seen: set[str] = set()
            safe_members = []
            for member in members:
                raw = member.name
                parsed = PurePosixPath(raw)
                if parsed.is_absolute() or any(part == ".." for part in parsed.parts):
                    raise RuntimeError(f"unsafe archive path: {raw!r}")
                parts = tuple(part for part in parsed.parts if part not in ("", "."))
                if not parts:
                    continue
                normalized = "/".join(parts)
                if normalized in seen:
                    raise RuntimeError(f"duplicate archive path: {normalized}")
                seen.add(normalized)
                if not (member.isdir() or member.isfile()):
                    raise RuntimeError(f"unsupported archive member type: {normalized}")
                member.name = normalized
                safe_members.append(member)
            # Extract only ordinary files/directories after validating every member path and type.
            for member in safe_members:
                target = staging.joinpath(*PurePosixPath(member.name).parts)
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=True)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source_stream = bundle.extractfile(member)
                if source_stream is None:
                    raise RuntimeError(f"could not read archive member: {member.name}")
                with source_stream, target.open("xb") as output:
                    shutil.copyfileobj(source_stream, output)
                target.chmod(member.mode & 0o777)
        extracted_registry = staging / "source" / "calibre" / "customize" / "builtins.py"
        if not extracted_registry.is_file():
            raise RuntimeError("embedded overlay did not contain source/calibre/customize/builtins.py")
        os.replace(staging, root)
        return source
    except Exception:
        if staging.exists() and staging.is_dir() and not staging.is_symlink():
            shutil.rmtree(staging, ignore_errors=True)
        raise


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

    env = os.environ.copy()
    env["CALIBRE_DEVELOP_FROM"] = str(overlay_source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        return subprocess.run([converter, str(source), str(destination), *argv[2:]], env=env, check=False).returncode
    except OSError as exc:
        return fail(f"unable to launch ebook-convert: {exc}", 78)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
