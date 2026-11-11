#!/usr/bin/env python3
"""UMOT stage 0: preserve the published wheel. Do not rebuild or overwrite it."""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys

WHEEL_NAME = (
    "umot_compact-1.0.5.post11-m11-m12-imatrix-cpu128-py3-none-manylinux_2_34_x86_64.whl"
)
EXPECTED_SHA256 = "2950aa605d972672af925015ec4d061e5f5e526187aaa2507fba6b6e80246db6"
EXPECTED_BYTES = 205679247
PLATFORM = "Debian Stable 13 Trixie"
GLIBC_DECLARED_BY_WHEEL = "2.34"
POINTER_RE = re.compile(
    r"^version https://git-lfs.github.com/spec/v1\noid sha256:([0-9a-f]{64})\nsize (\d+)\n\Z"
)


def verify_lfs_pointer(text: str) -> dict:
    match = POINTER_RE.match(text)
    if not match:
        return {"status": "FAIL", "reason": "NOT_AN_LFS_POINTER"}
    digest, size = match.group(1), int(match.group(2))
    ok = digest == EXPECTED_SHA256 and size == EXPECTED_BYTES
    return {
        "status": "PASS_POINTER_MATCHES_PROTECTED_WHEEL" if ok else "FAIL",
        "sha256": digest,
        "bytes": size,
        "wheel": WHEEL_NAME,
        "overwritten": False,
    }


def verify_file(path: pathlib.Path) -> dict:
    if path.is_symlink() or not path.is_file():
        return {"status": "FAIL", "reason": "WHEEL_NOT_A_REGULAR_FILE"}
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
            size += len(chunk)
    ok = digest.hexdigest() == EXPECTED_SHA256 and size == EXPECTED_BYTES
    return {
        "status": "PASS_FILE_MATCHES_PROTECTED_WHEEL" if ok else "FAIL",
        "sha256": digest.hexdigest(),
        "bytes": size,
        "wheel": WHEEL_NAME,
        "overwritten": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pointer-file", type=pathlib.Path)
    parser.add_argument("--wheel", type=pathlib.Path)
    args = parser.parse_args()
    if args.pointer_file is None and args.wheel is None:
        print(json.dumps({
            "status": "HOLD",
            "reason": "NO_LOCAL_WHEEL_SUPPLIED",
            "expected_sha256": EXPECTED_SHA256,
            "expected_bytes": EXPECTED_BYTES,
            "platform": PLATFORM,
            "glibc_declared_by_wheel_tag": GLIBC_DECLARED_BY_WHEEL,
            "debian_glibc_measured": False,
            "certification": "NOT_GRANTED",
        }, indent=2))
        return 2
    if args.pointer_file is not None:
        result = verify_lfs_pointer(args.pointer_file.read_text(encoding="utf-8"))
    else:
        result = verify_file(args.wheel)
    result.update({
        "platform": PLATFORM,
        "glibc_declared_by_wheel_tag": GLIBC_DECLARED_BY_WHEEL,
        "debian_glibc_measured": False,
        "certification": "NOT_GRANTED",
        "external_provider_required": False,
    })
    print(json.dumps(result, indent=2))
    return 0 if result["status"].startswith("PASS") else 2


if __name__ == "__main__":
    raise SystemExit(main())
