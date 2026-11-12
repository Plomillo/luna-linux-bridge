#!/usr/bin/env python3
"""Verify JASP release identity from immutable Flathub and source-control objects.

Flatpak's friendly "Version" display is AppStream-derived and is not accepted as
a mandatory source: it may be absent or stale. This verifier binds the exact
Flathub manifest Git blob to the exact jasp-desktop source commit and derives
the public three-component version from that commit's CMake project version.
The runtime banner is still independently required by the JASP execution lane.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from typing import Any

SCHEMA = "LUNITA_JASP_SOURCE_RELEASE_IDENTITY/1.0"
APP_ID = "org.jaspstats.JASP"
FLATHUB_MANIFEST_COMMIT = "95e467d83089fb292e5d0746e98e188fef6f9113"
FLATHUB_MANIFEST_BLOB_SHA1 = "1aec5921883d56388c91627b09ba9cf6eb07c1d6"
JASP_SOURCE_COMMIT = "b6cd3b0310be4e18e1b673ac11f14e55615c8fa1"
JASP_CMAKE_BLOB_SHA1 = "d57ba1e22d4cd00f3848034dc09737498b91346b"
EXPECTED_VERSION = "0.98.8"


class IdentityError(ValueError):
    """Raised when release/source identity is absent or inconsistent."""


def git_blob_sha1(payload: bytes) -> str:
    header = f"blob {len(payload)}\\0".encode("ascii")
    return hashlib.sha1(header + payload).hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def normalize_project_version(value: str) -> str:
    parts = value.split(".")
    if any(not part.isdigit() for part in parts) or len(parts) not in (3, 4):
        raise IdentityError(f"Unsupported JASP CMake project version: {value!r}")
    if len(parts) == 4:
        if parts[3] != "0":
            raise IdentityError(
                "Four-component JASP CMake version must end in .0 to map to its public runtime version"
            )
        parts = parts[:3]
    return ".".join(parts)


def verify_jasp_release_identity(
    manifest_bytes: bytes,
    cmake_bytes: bytes,
    *,
    expected_manifest_blob_sha1: str = FLATHUB_MANIFEST_BLOB_SHA1,
    expected_cmake_blob_sha1: str = JASP_CMAKE_BLOB_SHA1,
    expected_source_commit: str = JASP_SOURCE_COMMIT,
    expected_version: str = EXPECTED_VERSION,
) -> dict[str, Any]:
    observed_manifest_blob = git_blob_sha1(manifest_bytes)
    observed_cmake_blob = git_blob_sha1(cmake_bytes)
    if observed_manifest_blob != expected_manifest_blob_sha1:
        raise IdentityError(
            f"Flathub manifest Git blob SHA-1 mismatch: {observed_manifest_blob}"
        )
    if observed_cmake_blob != expected_cmake_blob_sha1:
        raise IdentityError(
            f"JASP CMakeLists.txt Git blob SHA-1 mismatch: {observed_cmake_blob}"
        )

    try:
        manifest = json.loads(manifest_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise IdentityError(f"Flathub manifest is not valid UTF-8 JSON: {exc}") from exc
    if not isinstance(manifest, dict) or manifest.get("app-id") != APP_ID:
        raise IdentityError("Flathub manifest app-id does not match the pinned JASP application")

    modules = manifest.get("modules")
    if not isinstance(modules, list):
        raise IdentityError("Flathub manifest has no modules array")
    source_commits = []
    for module in modules:
        if not isinstance(module, dict) or module.get("name") != "jasp":
            continue
        sources = module.get("sources")
        if not isinstance(sources, list):
            continue
        for source in sources:
            if (
                isinstance(source, dict)
                and source.get("type") == "git"
                and source.get("url") == "https://github.com/jasp-stats/jasp-desktop.git"
            ):
                source_commits.append(source.get("commit"))
    if source_commits != [expected_source_commit]:
        raise IdentityError(
            "Flathub manifest does not uniquely pin the expected jasp-desktop source commit"
        )

    try:
        cmake_text = cmake_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise IdentityError("Pinned JASP CMakeLists.txt is not UTF-8") from exc
    match = re.search(
        r"project\\s*\\(\\s*JASP\\s+VERSION\\s+([0-9]+(?:\\.[0-9]+){2,3})",
        cmake_text,
        flags=re.IGNORECASE,
    )
    if not match:
        raise IdentityError("Pinned JASP CMakeLists.txt contains no project(JASP VERSION ...) declaration")
    cmake_version = match.group(1)
    public_version = normalize_project_version(cmake_version)
    if public_version != expected_version:
        raise IdentityError(
            f"Pinned JASP source version mismatch: expected {expected_version}, observed {public_version}"
        )

    return {
        "schema": SCHEMA,
        "status": "PASS_JASP_SOURCE_RELEASE_IDENTITY",
        "application_id": APP_ID,
        "version": public_version,
        "cmake_project_version": cmake_version,
        "version_source": "PINNED_JASP_CMAKE_PROJECT_VERSION",
        "flathub_manifest_commit": FLATHUB_MANIFEST_COMMIT,
        "flathub_manifest_git_blob_sha1": observed_manifest_blob,
        "flathub_manifest_sha256": sha256_bytes(manifest_bytes),
        "jasp_source_commit": expected_source_commit,
        "jasp_source_cmake_git_blob_sha1": observed_cmake_blob,
        "jasp_source_cmake_sha256": sha256_bytes(cmake_bytes),
        "manifest_jasp_source_commit_matches_pin": True,
        "source_cmake_version_matches_pin": True,
        "appstream_version_metadata_used": False,
    }


def self_test() -> dict[str, Any]:
    checks: dict[str, bool] = {}
    manifest = json.dumps(
        {
            "app-id": APP_ID,
            "modules": [
                {
                    "name": "jasp",
                    "sources": [
                        {
                            "type": "git",
                            "url": "https://github.com/jasp-stats/jasp-desktop.git",
                            "commit": "a" * 40,
                        }
                    ],
                }
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    cmake = b"project(\\n  JASP\\n  VERSION 0.98.8.0\\n  LANGUAGES CXX C\\n)"
    manifest_sha = git_blob_sha1(manifest)
    cmake_sha = git_blob_sha1(cmake)

    good = verify_jasp_release_identity(
        manifest,
        cmake,
        expected_manifest_blob_sha1=manifest_sha,
        expected_cmake_blob_sha1=cmake_sha,
        expected_source_commit="a" * 40,
        expected_version="0.98.8",
    )
    checks["accepts_exact_manifest_and_source_pins"] = good["status"] == "PASS_JASP_SOURCE_RELEASE_IDENTITY"
    checks["records_appstream_not_used"] = good["appstream_version_metadata_used"] is False

    try:
        verify_jasp_release_identity(
            manifest + b" ",
            cmake,
            expected_manifest_blob_sha1=manifest_sha,
            expected_cmake_blob_sha1=cmake_sha,
            expected_source_commit="a" * 40,
            expected_version="0.98.8",
        )
        checks["rejects_manifest_blob_drift"] = False
    except IdentityError:
        checks["rejects_manifest_blob_drift"] = True

    try:
        verify_jasp_release_identity(
            manifest,
            cmake.replace(b"0.98.8.0", b"0.98.1.0"),
            expected_manifest_blob_sha1=manifest_sha,
            expected_cmake_blob_sha1=git_blob_sha1(cmake.replace(b"0.98.8.0", b"0.98.1.0")),
            expected_source_commit="a" * 40,
            expected_version="0.98.8",
        )
        checks["rejects_source_version_drift"] = False
    except IdentityError:
        checks["rejects_source_version_drift"] = True

    try:
        verify_jasp_release_identity(
            manifest,
            cmake,
            expected_manifest_blob_sha1=manifest_sha,
            expected_cmake_blob_sha1=cmake_sha,
            expected_source_commit="b" * 40,
            expected_version="0.98.8",
        )
        checks["rejects_manifest_source_commit_drift"] = False
    except IdentityError:
        checks["rejects_manifest_source_commit_drift"] = True

    return {
        "schema": "LUNITA_JASP_SOURCE_RELEASE_IDENTITY_SELF_TEST/1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "certification": "NOT_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=pathlib.Path)
    parser.add_argument("--cmake", type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    try:
        if args.self_test:
            result = self_test()
        else:
            if not args.manifest or not args.cmake:
                parser.error("--manifest and --cmake are required unless --self-test is used")
            result = verify_jasp_release_identity(
                args.manifest.read_bytes(),
                args.cmake.read_bytes(),
            )
        payload = json.dumps(result, ensure_ascii=True, sort_keys=True, indent=2) + "\\n"
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(payload, encoding="utf-8")
        else:
            print(payload, end="")
    except (OSError, IdentityError) as exc:
        print(json.dumps({
            "schema": SCHEMA,
            "status": "BLOCKED_JASP_SOURCE_RELEASE_IDENTITY",
            "error": str(exc),
            "certification": "NOT_GRANTED",
        }, ensure_ascii=True, indent=2), file=sys.stderr)
        return 2
    return 0 if result.get("status") in {"PASS_JASP_SOURCE_RELEASE_IDENTITY", "PASS"} else 3


if __name__ == "__main__":
    raise SystemExit(main())
