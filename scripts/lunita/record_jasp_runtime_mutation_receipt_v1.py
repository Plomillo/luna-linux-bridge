#!/usr/bin/env python3
"""Create a hash-bound receipt for JASP/Qt mutations applied before SquashFS packaging."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import pathlib
import re
import tempfile
from typing import Any

PINNED_APP_COMMIT = "83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"


def sha256_file(path: pathlib.Path) -> str:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"Not a regular file: {path}")
    digest = hashlib.sha256()
    with resolved.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def file_record(path: pathlib.Path) -> dict[str, Any]:
    resolved = path.resolve(strict=True)
    return {"path": str(resolved), "sha256": sha256_file(resolved), "size_bytes": resolved.stat().st_size}


def parse_sha256sum_snapshot(path: pathlib.Path) -> list[dict[str, str]]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Pre-mutation Qt library snapshot is missing or unsafe")
    rows = []
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})\s+[* ](.+)", line)
        if not match:
            raise ValueError("Malformed sha256sum snapshot row")
        rows.append({"sha256": match.group(1), "path": match.group(2)})
    return sorted(rows, key=lambda row: row["path"])


def collect_library_records(root: pathlib.Path) -> list[dict[str, Any]]:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"Library directory is missing or unsafe: {root}")
    files = sorted(
        path for path in root.rglob("libQt6HttpServer.so*")
        if path.is_file() and not path.is_symlink()
    )
    return [file_record(path) for path in files]


def parse_patch_log(path: pathlib.Path, files_root: pathlib.Path) -> tuple[list[dict[str, Any]], int, int]:
    """Require explicit before/after hashes for each formatter resource actually modified."""
    if path.is_symlink() or not path.is_file():
        raise ValueError("JASP formatter patch log is missing or unsafe")
    pattern = re.compile(
        r"^Patched JASP result formatter in (.+) "
        r"\(call sites=(\d+), latex sites=(\d+), "
        r"before_sha256=([0-9a-f]{64}), after_sha256=([0-9a-f]{64})\)$"
    )
    resources = []
    total_calls = 0
    total_latex = 0
    root = files_root.resolve(strict=True)
    for line in path.read_text(encoding="utf-8", errors="strict").splitlines():
        if not line.startswith("Patched JASP result formatter in "):
            continue
        match = pattern.fullmatch(line)
        if not match:
            raise ValueError("Formatter patch log row lacks exact path and pre/post SHA-256 values")
        path_text, calls_text, latex_text, before_sha, after_sha = match.groups()
        resource_path = pathlib.Path(path_text).resolve(strict=True)
        if resource_path.is_symlink() or not resource_path.is_file():
            raise ValueError("Patched formatter resource is missing or unsafe")
        try:
            resource_path.relative_to(root)
        except ValueError as exc:
            raise ValueError("Patched formatter resource escapes the pinned JASP Flatpak files tree") from exc
        observed_sha = sha256_file(resource_path)
        if before_sha == after_sha or observed_sha != after_sha:
            raise ValueError("Formatter resource pre/post hash transition is invalid")
        calls, latex = int(calls_text), int(latex_text)
        if calls < 1 or latex < 1:
            raise ValueError("Formatter resource lacks required patch sites")
        resources.append({
            "path": str(resource_path),
            "before_sha256": before_sha,
            "after_sha256": after_sha,
            "observed_after_sha256": observed_sha,
            "call_sites": calls,
            "latex_sites": latex,
            "size_bytes": resource_path.stat().st_size,
        })
        total_calls += calls
        total_latex += latex
    if not resources or total_calls < 1 or total_latex < 1:
        raise ValueError("No fully hash-verified JASP formatter resource mutation was observed")
    if len({row["path"] for row in resources}) != len(resources):
        raise ValueError("Duplicate formatter resource paths were reported")
    return resources, total_calls, total_latex


def build_receipt(args: argparse.Namespace) -> dict[str, Any]:
    if args.app_commit_before != PINNED_APP_COMMIT or args.app_commit_after != PINNED_APP_COMMIT:
        raise ValueError("JASP application Flatpak commit moved from the pinned candidate")
    for label, value in (
        ("runtime commit before", args.runtime_commit_before),
        ("runtime commit after", args.runtime_commit_after),
        ("SDK commit", args.sdk_commit),
    ):
        if not re.fullmatch(r"[0-9a-f]{64}", value or ""):
            raise ValueError(f"Missing or malformed {label}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", args.qt_version or ""):
        raise ValueError("Qt SDK version is missing or malformed")
    if not args.runtime_ref or not args.sdk_ref or not args.source_url:
        raise ValueError("Runtime, SDK and Qt source identities are required")

    source_archive = file_record(args.source_archive)
    build_root = args.build_dir
    if build_root.is_symlink() or not build_root.is_dir():
        raise ValueError("QtHttpServer build directory is missing or unsafe")
    build_libs = collect_library_records(build_root)
    installed_libs = collect_library_records(args.qt_library_dir)
    jasp_binary = file_record(args.jasp_binary)
    if not re.fullmatch(r"[0-9a-f]{64}", args.jasp_binary_before_sha256 or ""):
        raise ValueError("Pre-mutation JASP executable hash is missing or malformed")
    binary_unchanged = jasp_binary["sha256"] == args.jasp_binary_before_sha256

    patch_script = file_record(args.patch_script)
    patch_log = file_record(args.patch_log)
    files_root = args.jasp_binary.resolve(strict=True).parent.parent
    patched_resources, call_sites, latex_sites = parse_patch_log(args.patch_log, files_root)
    pre_qt_snapshot = parse_sha256sum_snapshot(args.pre_qt_snapshot)
    pre_qt_snapshot_record = file_record(args.pre_qt_snapshot)

    if not build_libs or not installed_libs:
        raise ValueError("QtHttpServer build or installed library inventory is empty")
    output = {
        "schema": "LUNITA_JASP_RUNTIME_POST_MUTATION_RECEIPT/1.0",
        "status": "PASS",
        "candidate_id": "G06_REBUILD_CANDIDATE_R1",
        "candidate_version": "1.8.0",
        "application": {
            "flatpak_ref": "org.jaspstats.JASP",
            "pinned_commit": PINNED_APP_COMMIT,
            "commit_before": args.app_commit_before,
            "commit_after": args.app_commit_after,
            "binary_before_sha256": args.jasp_binary_before_sha256,
            "binary_after": jasp_binary,
            "binary_unchanged_by_formatter_patch": binary_unchanged,
        },
        "runtime": {
            "flatpak_ref": args.runtime_ref,
            "commit_before": args.runtime_commit_before,
            "commit_after": args.runtime_commit_after,
        },
        "sdk": {"flatpak_ref": args.sdk_ref, "commit": args.sdk_commit},
        "qt_http_server": {
            "qt_version": args.qt_version,
            "source_url": args.source_url,
            "source_archive": source_archive,
            "build_directory": str(build_root.resolve()),
            "built_libraries": build_libs,
            "installed_libraries_after": installed_libs,
            "installed_library_directory": str(args.qt_library_dir.resolve()),
            "installed_libraries_before_snapshot": pre_qt_snapshot,
            "installed_libraries_before_snapshot_file": pre_qt_snapshot_record,
        },
        "formatter_patch": {
            "script": patch_script,
            "log": patch_log,
            "call_sites": call_sites,
            "latex_sites": latex_sites,
            "patched_resources": patched_resources,
            "changed_jasp_binary": False,
            "r_startup_profile_mutated": False,
        },
        "certification": "NOT_GRANTED",
        "canonical_g06_certification": "NOT_GRANTED",
        "g23_status": "NOT_GRANTED",
        "g24_status": "NOT_GRANTED",
        "created_at_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
    }
    return output


def write_receipt(args: argparse.Namespace) -> dict[str, Any]:
    receipt = build_receipt(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists() or args.output.is_symlink():
        raise FileExistsError(f"Refusing to overwrite mutation receipt: {args.output}")
    encoded = json.dumps(receipt, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    temporary = args.output.with_name(args.output.name + ".tmp")
    flags = 0
    with temporary.open("xb") as stream:
        stream.write(encoded)
        stream.flush()
    temporary.chmod(0o600)
    temporary.replace(args.output)
    return {"status": receipt["status"], "path": str(args.output), "sha256": hashlib.sha256(encoded).hexdigest()}


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser()
    result.add_argument("--output", type=pathlib.Path, required=False)
    result.add_argument("--app-commit-before", required=False)
    result.add_argument("--app-commit-after", required=False)
    result.add_argument("--runtime-ref", required=False)
    result.add_argument("--runtime-commit-before", required=False)
    result.add_argument("--runtime-commit-after", required=False)
    result.add_argument("--sdk-ref", required=False)
    result.add_argument("--sdk-commit", required=False)
    result.add_argument("--qt-version", required=False)
    result.add_argument("--source-url", required=False)
    result.add_argument("--source-archive", type=pathlib.Path, required=False)
    result.add_argument("--build-dir", type=pathlib.Path, required=False)
    result.add_argument("--qt-library-dir", type=pathlib.Path, required=False)
    result.add_argument("--jasp-binary", type=pathlib.Path, required=False)
    result.add_argument("--jasp-binary-before-sha256", required=False)
    result.add_argument("--pre-qt-snapshot", type=pathlib.Path, required=False)
    result.add_argument("--patch-script", type=pathlib.Path, required=False)
    result.add_argument("--patch-log", type=pathlib.Path, required=False)
    result.set_defaults(self_test=False)
    result.add_argument("--self-test", action="store_true")
    return result


def self_test() -> None:
    with tempfile.TemporaryDirectory(prefix="lunita-jasp-mutation-receipt-test-") as temporary:
        base = pathlib.Path(temporary)
        archive = base / "qt-source.tar.gz"
        archive.write_bytes(b"pinned qt source archive")
        build = base / "build"
        build.mkdir()
        (build / "libQt6HttpServer.so.6").write_bytes(b"built Qt server")
        installed = base / "installed"
        installed.mkdir()
        (installed / "libQt6HttpServer.so.6").write_bytes(b"built Qt server")
        jasp = base / "JASP"
        jasp.write_bytes(b"post-patch JASP")
        before = base / "qt-before.sha256"
        before.write_text("", encoding="utf-8")
        patch_script = base / "patch.py"
        patch_script.write_text("# patcher\n", encoding="utf-8")
        resource = base / "resources" / "formatter.bin"
        resource.parent.mkdir()
        before_resource = b"unpatched formatter bytes"
        after_resource = b"patched formatter bytes"
        resource.write_bytes(after_resource)
        patch_log = base / "patch.log"
        patch_log.write_text(
            f"Patched JASP result formatter in {resource} "
            f"(call sites=1, latex sites=1, "
            f"before_sha256={hashlib.sha256(before_resource).hexdigest()}, "
            f"after_sha256={hashlib.sha256(after_resource).hexdigest()})\n",
            encoding="utf-8",
        )
        args = argparse.Namespace(
            app_commit_before=PINNED_APP_COMMIT, app_commit_after=PINNED_APP_COMMIT,
            runtime_ref="org.kde.Platform/x86_64/6.11",
            runtime_commit_before="a" * 64, runtime_commit_after="b" * 64,
            sdk_ref="org.kde.Sdk//6.11", sdk_commit="c" * 64, qt_version="6.11.3",
            source_url="https://example.invalid/qt/archive/v6.11.3.tar.gz",
            source_archive=archive, build_dir=build, qt_library_dir=installed,
            jasp_binary=jasp, jasp_binary_before_sha256=hashlib.sha256(b"pre-patch JASP").hexdigest(),
            pre_qt_snapshot=before, patch_script=patch_script, patch_log=patch_log,
        )
        receipt = build_receipt(args)
        assert receipt["status"] == "PASS"
        assert receipt["formatter_patch"]["call_sites"] == 1
        assert receipt["application"]["binary_unchanged_by_formatter_patch"] is True
        assert receipt["formatter_patch"]["patched_resources"][0]["before_sha256"] != receipt["formatter_patch"]["patched_resources"][0]["after_sha256"]
    print("record_jasp_runtime_mutation_receipt_v1 self-test PASS", flush=True)


def main() -> int:
    argument_parser = parser()
    args = argument_parser.parse_args()
    if args.self_test:
        self_test()
        return 0
    required_names = (
        "output", "app_commit_before", "app_commit_after", "runtime_ref",
        "runtime_commit_before", "runtime_commit_after", "sdk_ref", "sdk_commit",
        "qt_version", "source_url", "source_archive", "build_dir", "qt_library_dir",
        "jasp_binary", "jasp_binary_before_sha256", "pre_qt_snapshot", "patch_script", "patch_log",
    )
    missing = [name for name in required_names if getattr(args, name) is None]
    if missing:
        argument_parser.error("missing required arguments: " + ", ".join("--" + name.replace("_", "-") for name in missing))
    result = write_receipt(args)
    print(json.dumps(result, sort_keys=True), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
