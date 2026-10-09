#!/usr/bin/env python3
"""Build a deterministic source-only Jonas family-service candidate bundle."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCES = (
    "jonas_hott_api/__init__.py",
    "jonas_hott_api/app.py",
    "jonas_hott_api/account_state.py",
    "jonas_hott_api/family_checkin.html",
    "jonas_hott_api/requirements.txt",
    "jonas_hott_api/README.md",
    "docs/jonas-hott-live-telemetry.md",
    "docs/jonas-family-deployment.md",
    "scripts/missions/backup_restore_jonas_state.py",
    "tests/test_jonas_hott_api.py",
    "tests/test_jonas_account_state.py",
    "tests/test_jonas_backup_restore.py",
)
SECRET_PATTERNS = (
    re.compile(rb"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(rb"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"AKIA[0-9A-Z]{16}"),
)
PACKAGE_STATUS = (
    "STATUS=SOURCE_CANDIDATE_NOT_PRODUCTION_DEPLOYABLE\n"
    "This archive contains source and tests only; it contains no credentials or database.\n"
    "A shared deployment still requires HTTPS/TLS, rate limits, deployment secret management, "
    "security review, backup/restore validation, and an authorized runtime environment.\n"
    "It does not verify provider billing, official catalog completeness, G23, or G24.\n"
)


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="dist")
    args = parser.parse_args()
    output = (ROOT / args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=True)

    files: dict[str, bytes] = {}
    for relative in SOURCES:
        path = ROOT / relative
        if not path.is_file():
            raise SystemExit(f"required package input missing: {relative}")
        data = path.read_bytes()
        for pattern in SECRET_PATTERNS:
            if pattern.search(data):
                raise SystemExit(f"possible credential pattern found in {relative}")
        files[relative] = data

    manifest = "".join(f"{sha256(data)}  {name}\n" for name, data in sorted(files.items())).encode()
    files["PACKAGE_STATUS.txt"] = PACKAGE_STATUS.encode()
    files["MANIFEST.sha256"] = manifest
    archive = output / "jonas-family-source-candidate.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            zf.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)

    archive_digest = sha256(archive.read_bytes())
    (output / "jonas-family-source-candidate.zip.sha256").write_text(
        f"{archive_digest}  jonas-family-source-candidate.zip\n", encoding="utf-8"
    )
    report = {
        "schema": "jonas.family-source-package.v1",
        "status": "SOURCE_CANDIDATE_NOT_PRODUCTION_DEPLOYABLE",
        "archive": archive.name,
        "archive_sha256": archive_digest,
        "source_file_count": len(SOURCES),
        "source_sha256": {name: sha256(data) for name, data in sorted(files.items()) if name in SOURCES},
        "contains_credentials": False,
        "contains_database": False,
        "production_authorized": False,
        "certified": False,
    }
    (output / "jonas-family-source-package.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
