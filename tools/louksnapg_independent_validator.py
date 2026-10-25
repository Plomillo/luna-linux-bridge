#!/usr/bin/env python3
"""Independent ZIP-level verifier for a LOUKSNAPG candidate.

This module intentionally does not import tools.louksnapg_bundle.py. It verifies
the package inventory from the outside and can safely extract a validated bundle
for runtime smoke tests. Structural inventory is never treated as functional proof.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from pathlib import Path, PurePosixPath

CAP_BYTES = 470_000_000
BUNDLE_MANIFEST = "LOUKSNAPG_MANIFEST.json"
RUNTIME_MANIFEST = "MACRODOWN_MANIFEST.json"
EXPECTED_DOMAINS = [
    "D01_CEREBRO", "D02_ORQUESTACION", "D03_TRANSCRIPCION",
    "D04_TRADUCTOR_INTELIGENTE", "D05_INTELIGENCIA_DOCUMENTAL",
    "D06_SISTEMA_INTELIGENTE",
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_stream(stream) -> tuple[int, str]:
    total = 0
    digest = hashlib.sha256()
    for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
        total += len(chunk)
        digest.update(chunk)
    return total, digest.hexdigest()


def safe_path(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        raise ValueError("UNSAFE_MEMBER_PATH")
    parsed = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in parsed.parts):
        raise ValueError("PATH_TRAVERSAL:" + name[:160])
    if parsed.parts and ":" in parsed.parts[0]:
        raise ValueError("DRIVE_PATH_REJECTED")
    return parsed.as_posix()


def extract_validated(archive: zipfile.ZipFile, destination: Path, members: set[str]) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    base = destination.resolve()
    for name in sorted(members, key=lambda value: value.encode("utf-8")):
        info = archive.getinfo(name)
        safe_path(name)
        mode = (info.external_attr >> 16) & 0o170000
        if info.is_dir() or mode == stat.S_IFLNK:
            raise ValueError("UNSAFE_MEMBER_TYPE:" + name)
        target = base.joinpath(*PurePosixPath(name).parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.resolve().is_relative_to(base):
            raise ValueError("EXTRACTION_PATH_ESCAPE:" + name)
        with archive.open(info, "r") as source, target.open("wb") as sink:
            while True:
                chunk = source.read(4 * 1024 * 1024)
                if not chunk:
                    break
                sink.write(chunk)
        if not target.is_file() or target.is_symlink():
            raise ValueError("EXTRACTED_ENTRY_NOT_REGULAR_FILE:" + name)


def verify(path: Path, max_bytes: int = CAP_BYTES, extract_dir: Path | None = None,
           expected_source_commit: str | None = None) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("BUNDLE_NOT_REGULAR_FILE")
    observed_bytes = path.stat().st_size
    if observed_bytes > max_bytes:
        raise ValueError(f"BUNDLE_OVER_CAP:{observed_bytes}>{max_bytes}")
    if not zipfile.is_zipfile(path):
        raise ValueError("BUNDLE_CONTAINER_NOT_ZIP")
    with zipfile.ZipFile(path, "r") as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("DUPLICATE_MEMBER_NAMES")
        bad = archive.testzip()
        if bad:
            raise ValueError("CRC_FAILURE:" + bad)
        if BUNDLE_MANIFEST not in names:
            raise ValueError("BUNDLE_MANIFEST_MISSING")
        manifest = json.loads(archive.read(BUNDLE_MANIFEST).decode("utf-8"))
        if manifest.get("schema") != "LOUKSNAPG_BUNDLE/1.0" or manifest.get("product_name") != "LOUKSNAPG":
            raise ValueError("BUNDLE_IDENTITY_MISMATCH")
        source_commit = manifest.get("source_commit")
        if expected_source_commit is not None and source_commit != expected_source_commit:
            raise ValueError("BUNDLE_SOURCE_COMMIT_MISMATCH")
        records = manifest.get("members")
        if not isinstance(records, list):
            raise ValueError("MEMBER_INVENTORY_MISSING")
        expected = {}
        for row in records:
            name = safe_path(row.get("path", ""))
            if name in expected or name == BUNDLE_MANIFEST:
                raise ValueError("MEMBER_INVENTORY_COLLISION:" + name)
            expected[name] = row
        actual = set(names) - {BUNDLE_MANIFEST}
        if actual != set(expected):
            raise ValueError("MEMBER_SET_DIFFERS_FROM_INVENTORY")
        for name, row in expected.items():
            info = archive.getinfo(name)
            mode = (info.external_attr >> 16) & 0o170000
            if info.is_dir() or mode == stat.S_IFLNK:
                raise ValueError("UNSAFE_MEMBER_TYPE:" + name)
            with archive.open(info, "r") as stream:
                byte_count, digest = sha256_stream(stream)
            if byte_count != row.get("bytes") or digest != row.get("sha256"):
                raise ValueError("MEMBER_SHA256_OR_SIZE_MISMATCH:" + name)

        source = manifest.get("source", {})
        document_name = "Louksna1.md"
        if document_name not in actual:
            raise ValueError("GOVERNED_DOCUMENT_MISSING")
        doc_info = archive.getinfo(document_name)
        prefix_bytes = source.get("protected_architecture_bytes")
        prefix_sha = source.get("protected_architecture_sha256")
        if not isinstance(prefix_bytes, int) or prefix_bytes <= 0:
            raise ValueError("PROTECTED_PREFIX_LENGTH_MISSING")
        with archive.open(doc_info, "r") as document:
            prefix = document.read(prefix_bytes)
            if len(prefix) != prefix_bytes or sha256_bytes(prefix) != prefix_sha:
                raise ValueError("PROTECTED_ARCHITECTURE_PREFIX_HASH_MISMATCH")
            cajita_bytes = source.get("embedded_cajita_document_bytes")
            cajita_sha = source.get("embedded_cajita_document_sha256")
            if not isinstance(cajita_bytes, int) or cajita_bytes <= 0 or cajita_bytes > doc_info.file_size:
                raise ValueError("EMBEDDED_CAJITA_LENGTH_INVALID")
            document.seek(doc_info.file_size - cajita_bytes)
            suffix_bytes, suffix_sha = sha256_stream(document)
            if suffix_bytes != cajita_bytes or suffix_sha != cajita_sha:
                raise ValueError("EMBEDDED_CAJITA_SUFFIX_HASH_MISMATCH")
        if "CAJITA_LUNA_RUNTIME_V10.macrodown" in actual:
            raise ValueError("NESTED_RUNTIME_ARCHIVE_PRESENT")
        if RUNTIME_MANIFEST not in actual:
            raise ValueError("RUNTIME_INTERNAL_MANIFEST_MISSING")
        runtime_manifest_bytes = archive.read(RUNTIME_MANIFEST)
        if sha256_bytes(runtime_manifest_bytes) != source.get("runtime_manifest_sha256"):
            raise ValueError("RUNTIME_INTERNAL_MANIFEST_SHA256_MISMATCH")
        runtime_manifest = json.loads(runtime_manifest_bytes.decode("utf-8"))
        if runtime_manifest.get("schema") != "CAJITA_RUNTIME_MACRODOWN/1.0":
            raise ValueError("RUNTIME_INTERNAL_MANIFEST_SCHEMA_MISMATCH")
        runtime_rows = runtime_manifest.get("files")
        if not isinstance(runtime_rows, list):
            raise ValueError("RUNTIME_INTERNAL_MANIFEST_FILE_TABLE_MISSING")
        runtime_table = {}
        for row in runtime_rows:
            name = safe_path(row.get("path", ""))
            if name in runtime_table or name == RUNTIME_MANIFEST:
                raise ValueError("RUNTIME_INTERNAL_MANIFEST_PATH_COLLISION:" + name)
            runtime_table[name] = row
        bundle_runtime_rows = manifest.get("runtime_member_inventory", [])
        if not isinstance(bundle_runtime_rows, list):
            raise ValueError("BUNDLE_RUNTIME_INVENTORY_INVALID")
        bundle_runtime_table = {}
        for row in bundle_runtime_rows:
            name = safe_path(row.get("path", ""))
            if name in bundle_runtime_table:
                raise ValueError("BUNDLE_RUNTIME_INVENTORY_COLLISION:" + name)
            bundle_runtime_table[name] = row
        if set(runtime_table) != set(bundle_runtime_table):
            raise ValueError("RUNTIME_INVENTORY_DIFFERS_FROM_INTERNAL_MANIFEST")
        for name, runtime_row in runtime_table.items():
            if name not in actual:
                raise ValueError("RUNTIME_MEMBER_NOT_PRESENT:" + name)
            with archive.open(name, "r") as stream:
                byte_count, digest = sha256_stream(stream)
            if byte_count != runtime_row.get("size_bytes") or digest != runtime_row.get("sha256"):
                raise ValueError("RUNTIME_MEMBER_DIFFERS_FROM_INTERNAL_MANIFEST:" + name)
            registered = bundle_runtime_table[name]
            if byte_count != registered.get("bytes") or digest != registered.get("sha256"):
                raise ValueError("RUNTIME_MEMBER_DIFFERS_FROM_BUNDLE_INVENTORY:" + name)
        if "Louksna1.md" not in actual:
            raise ValueError("GOVERNED_DOCUMENT_MISSING")
        document_bytes = archive.read("Louksna1.md")
        if len(document_bytes) != source.get("louksna1_bytes") or sha256_bytes(document_bytes) != source.get("louksna1_sha256"):
            raise ValueError("LOUKSNA1_DOCUMENT_DIFFERS_FROM_SOURCE_BINDING")

        routing_status = "NOT_PRESENT"
        module_registry_status = "NOT_PRESENT"
        target_count = None
        domain_count = None
        engine_count = None
        command_count = None
        if "command_subdomain_routing.json" in actual:
            routing = json.loads(archive.read("command_subdomain_routing.json").decode("utf-8"))
            targets = routing.get("targets", [])
            domains = routing.get("domain_order", [])
            target_count = len(targets) if isinstance(targets, list) else None
            domain_count = len(domains) if isinstance(domains, list) else None
            engine_count = routing.get("state", {}).get("engine_count")
            routing_status = (
                "PASS_DECLARATION_ONLY"
                if domain_count == 6 and domains == EXPECTED_DOMAINS and target_count == 21 and engine_count == 15
                else "FAIL"
            )
        if "CAJITA_DISTRIBUTION_MODULE_REGISTRY.json" in actual:
            registry = json.loads(archive.read("CAJITA_DISTRIBUTION_MODULE_REGISTRY.json").decode("utf-8"))
            command_count = registry.get("canonical_command_count")
            module_registry_status = (
                "PASS_DECLARATION_ONLY"
                if registry.get("schema") == "CAJITA_MODULE_REGISTRY/1.0"
                and registry.get("canonical_engine_count") == 15
                and command_count == 14
                else "FAIL"
            )
        if extract_dir is not None:
            if extract_dir.exists():
                raise ValueError("EXTRACTION_DESTINATION_ALREADY_EXISTS")
            extract_validated(archive, extract_dir, actual)

    return {
        "schema": "LOUKSNAPG_INDEPENDENT_VALIDATION/1.0",
        "artifact": path.name,
        "bundle_bytes": observed_bytes,
        "bundle_sha256": sha256_file(path),
        "max_bytes": max_bytes,
        "budget_status": "PASS",
        "container_integrity": "PASS",
        "protected_prefix_integrity": "PASS",
        "cajita_document_copy_integrity": "PASS",
        "runtime_member_integrity": "PASS",
        "single_distribution_container": "PASS",
        "runtime_routing_registry": routing_status,
        "module_registry": module_registry_status,
        "declared_domain_count": domain_count,
        "declared_target_count": target_count,
        "declared_engine_count": engine_count,
        "declared_command_count": command_count,
        "document_sha256": source.get("louksna1_sha256"),
        "runtime_source_sha256": source.get("runtime_archive_sha256"),
        "source_commit": manifest.get("source_commit"),
        "global_certification": "NOT_GRANTED",
        "functional_status": "NOT_ESTABLISHED_BY_CONTAINER_INTEGRITY_CHECK",
        "extracted_to": str(extract_dir) if extract_dir else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, type=Path)
    parser.add_argument("--max-bytes", type=int, default=CAP_BYTES)
    parser.add_argument("--extract-to", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--expected-source-commit")
    args = parser.parse_args(argv)
    try:
        report = verify(args.bundle, args.max_bytes, args.extract_to, args.expected_source_commit)
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0 if report["runtime_routing_registry"] != "FAIL" and report["module_registry"] != "FAIL" else 2
    except Exception as exc:
        report = {"status": "FAIL_CLOSED", "error": f"{type(exc).__name__}:{str(exc)[:1200]}", "global_certification": "NOT_GRANTED"}
        if args.report:
            args.report.parent.mkdir(parents=True, exist_ok=True)
            args.report.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
