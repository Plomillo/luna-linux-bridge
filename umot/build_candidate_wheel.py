#!/usr/bin/env python3
"""Build the PEP 427 candidate without mutating post11 or the post12 source wheel."""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import zipfile
from pathlib import Path

PARENT_SHA256 = "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6"
PARENT_BYTES = 205679247
VERSION = "1.0.5.post12"
TAG = "py3-none-manylinux_2_34_x86_64"
FILENAME = f"umot_compact-{VERSION}-1additive-{TAG}.whl"
DIST = f"umot_compact-{VERSION}.dist-info"
PACKAGE_FILES = ("__init__.py", "__main__.py", "cli.py", "runtime.py")


def sha256_file(path: Path) -> tuple[str, int]:
    digest, size = hashlib.sha256(), 0
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    return digest.hexdigest(), size


def b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode().rstrip("=")


def build(source: Path, parent: Path, output: Path) -> dict:
    if output.resolve() in {source.resolve(), parent.resolve()}:
        raise SystemExit("REFUSING_TO_OVERWRITE_SOURCE")
    parent_hash, parent_size = sha256_file(parent)
    if (parent_hash, parent_size) != (PARENT_SHA256, PARENT_BYTES):
        raise SystemExit(f"PARENT_IDENTITY_MISMATCH {parent_hash} {parent_size}")
    source_hash, source_size = sha256_file(source)
    root = Path(__file__).resolve().parent
    files: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(source) as archive:
        payload_name = "umot_compact/payload.tar.gz"
        if payload_name not in archive.namelist():
            raise SystemExit("SOURCE_PAYLOAD_MISSING")
        payload = archive.read(payload_name)
    files.append((payload_name, payload))
    for name in PACKAGE_FILES:
        files.append((f"umot/{name}", (root / name).read_bytes()))
    metadata = (
        "Metadata-Version: 2.1\n"
        "Name: umot_compact\n"
        f"Version: {VERSION}\n"
        "Summary: Additive UMOT core. Build tag 1additive satisfies PEP 427. "
        "Parent post11 is not modified. Core import has no remote dependency.\n"
        "Requires-Python: >=3.10\n"
        "Provides-Extra: browser\n"
        "Requires-Dist: playwright==1.62.0; extra == 'browser'\n"
        "Provides-Extra: cli-lib\n"
        "Requires-Dist: click==8.5.1; extra == 'cli-lib'\n"
    ).encode()
    wheel = (
        "Wheel-Version: 1.0\n"
        "Generator: umot-candidate-builder-1additive\n"
        "Root-Is-Purelib: false\n"
        f"Tag: {TAG}\n"
    ).encode()
    entry = b"[console_scripts]\numot = umot.cli:main\n"
    files.extend([
        (f"{DIST}/METADATA", metadata),
        (f"{DIST}/WHEEL", wheel),
        (f"{DIST}/entry_points.txt", entry),
    ])
    record_lines = []
    for name, data in sorted(files):
        record_lines.append(f"{name},sha256={b64(data)},{len(data)}")
    record_name = f"{DIST}/RECORD"
    record_lines.append(f"{record_name},,")
    record = ("\n".join(record_lines) + "\n").encode()
    files.append((record_name, record))
    if output.exists():
        output.unlink()
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(files):
            info = zipfile.ZipInfo(filename=name, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = (0o755 if name.endswith(".py") else 0o644) << 16
            archive.writestr(info, data, compresslevel=6)
    digest, size = sha256_file(output)
    return {
        "wheel": str(output),
        "filename": FILENAME,
        "sha256": digest,
        "bytes": size,
        "parent_sha256": parent_hash,
        "parent_unchanged": True,
        "source_sha256": source_hash,
        "source_bytes": source_size,
        "payload_bytes": len(payload),
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
        "nomenclature": "BUILD_TAG_1additive_VERSION_REMAINS_1.0.5.post12",
        "record_self_entry": "EMPTY_HASH_AND_SIZE",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.source, args.parent, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
