#!/usr/bin/env python3
"""Build/verify a single-file LOUKSNAPG distribution container.

LOUKSNAPG.md is a ZIP container with the requested product filename. It contains
Louksna1.md plus the expanded, hash-verified files from the Cajita .macrodown
runtime; the .macrodown is not left as a second delivered artifact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import stat
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

SCHEMA = "LOUKSNAPG_BUNDLE/1.0"
DEFAULT_MAX_BYTES = 470_000_000
RUNTIME_MANIFEST = "MACRODOWN_MANIFEST.json"
BUNDLE_MANIFEST = "LOUKSNAPG_MANIFEST.json"
OPS_DOC = "LOUKSNAPG_OPERATIONS.md"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def validate_member_name(name: str) -> str:
    if not isinstance(name, str) or not name or "\\" in name or name.startswith("/"):
        raise ValueError("UNSAFE_ARCHIVE_MEMBER_NAME")
    path = PurePosixPath(name)
    if any(part in {"", ".", ".."} for part in path.parts) or (path.parts and ":" in path.parts[0]):
        raise ValueError("ARCHIVE_PATH_TRAVERSAL_REJECTED:" + name[:160])
    return path.as_posix()


def regular_file_info(name: str, compress_type: int, mode: int = 0o644) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=FIXED_TIME)
    info.create_system = 3
    info.compress_type = compress_type
    info.external_attr = ((stat.S_IFREG | mode) & 0xFFFF) << 16
    info.flag_bits |= 0x800
    return info


def _stream_entry(source_zip: zipfile.ZipFile, source_info: zipfile.ZipInfo,
                  destination_zip: zipfile.ZipFile, destination_info: zipfile.ZipInfo) -> dict:
    digest = hashlib.sha256()
    size = 0
    with source_zip.open(source_info, "r") as source, destination_zip.open(destination_info, "w", force_zip64=True) as dest:
        while True:
            chunk = source.read(4 * 1024 * 1024)
            if not chunk:
                break
            dest.write(chunk)
            digest.update(chunk)
            size += len(chunk)
    return {"path": source_info.filename, "bytes": size, "sha256": digest.hexdigest()}


def _read_runtime_manifest(runtime_zip: zipfile.ZipFile) -> tuple[dict, dict[str, dict]]:
    names = runtime_zip.namelist()
    if len(names) != len(set(names)):
        raise ValueError("RUNTIME_DUPLICATE_ZIP_MEMBERS")
    if RUNTIME_MANIFEST not in names:
        raise ValueError("RUNTIME_MANIFEST_MISSING")
    manifest_bytes = runtime_zip.read(RUNTIME_MANIFEST)
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("schema") != "CAJITA_RUNTIME_MACRODOWN/1.0":
        raise ValueError("RUNTIME_MANIFEST_SCHEMA_MISMATCH")
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise ValueError("RUNTIME_MANIFEST_FILES_INVALID")
    table: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("RUNTIME_MANIFEST_ROW_INVALID")
        name = validate_member_name(row.get("path", ""))
        if name == RUNTIME_MANIFEST or name in table:
            raise ValueError("RUNTIME_MANIFEST_MEMBER_COLLISION:" + name)
        if not isinstance(row.get("size_bytes"), int) or row["size_bytes"] < 0:
            raise ValueError("RUNTIME_MANIFEST_SIZE_INVALID:" + name)
        digest = row.get("sha256")
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("RUNTIME_MANIFEST_SHA256_INVALID:" + name)
        if row.get("zip_method") not in {"STORED", "DEFLATED"}:
            raise ValueError("RUNTIME_MANIFEST_COMPRESSION_INVALID:" + name)
        table[name] = row
    actual = {info.filename for info in runtime_zip.infolist() if not info.is_dir() and info.filename != RUNTIME_MANIFEST}
    if actual != set(table):
        raise ValueError("RUNTIME_MEMBER_SET_DIFFERS_FROM_MANIFEST")
    for name in actual:
        info = runtime_zip.getinfo(name)
        if (info.external_attr >> 16) & 0o170000 == stat.S_IFLNK:
            raise ValueError("RUNTIME_SYMLINK_REJECTED:" + name)
        validate_member_name(name)
    return manifest, table


def _write_bytes(zout: zipfile.ZipFile, name: str, payload: bytes, compress_type: int) -> dict:
    info = regular_file_info(name, compress_type)
    with zout.open(info, "w", force_zip64=True) as dest:
        dest.write(payload)
    return {"path": name, "bytes": len(payload), "sha256": sha256_bytes(payload)}


def build_bundle(document: Path, runtime_archive: Path, output: Path,
                 source_architecture: Path, cajita_doc: Path,
                 max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    if max_bytes <= 0:
        raise ValueError("MAX_BYTES_MUST_BE_POSITIVE")
    for p in (document, runtime_archive, source_architecture, cajita_doc):
        if p.is_symlink() or not p.is_file():
            raise ValueError("REQUIRED_INPUT_NOT_REGULAR_FILE:" + str(p))
    document_bytes = document.read_bytes()
    protected_bytes = source_architecture.read_bytes()
    cajita_bytes = cajita_doc.read_bytes()
    if not document_bytes.startswith(protected_bytes):
        raise ValueError("LOUKSNAMEJORADA_PREFIX_NOT_BYTE_EXACT")
    marker = b"# Documento central del runtime Cajita de Luna (copia literal)\n\n"
    if marker not in document_bytes:
        raise ValueError("CAJITA_DOCUMENT_EMBED_MARKER_MISSING")
    if not document_bytes.endswith(cajita_bytes):
        raise ValueError("CAJITA_DOCUMENT_COPY_NOT_EXACT_SUFFIX")
    runtime_sha = sha256_file(runtime_archive)
    runtime_bytes = runtime_archive.stat().st_size
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or output.is_symlink():
        output.unlink()

    try:
        payload_rows: list[dict] = []
        runtime_member_rows: list[dict] = []
        with zipfile.ZipFile(runtime_archive, "r") as zin:
            bad = zin.testzip()
            if bad:
                raise ValueError("RUNTIME_CRC_FAILURE:" + bad)
            runtime_manifest, runtime_table = _read_runtime_manifest(zin)
            reserved = {Path(n).name for n in (BUNDLE_MANIFEST, OPS_DOC, document.name)}
            collisions = reserved.intersection(runtime_table)
            if collisions:
                raise ValueError("RUNTIME_MEMBER_COLLIDES_WITH_BUNDLE_METADATA:" + ",".join(sorted(collisions)))
    
            with zipfile.ZipFile(output, "w", allowZip64=True) as zout:
                doc_row = _write_bytes(zout, "Louksna1.md", document_bytes, zipfile.ZIP_DEFLATED)
                doc_row["role"] = "GOVERNED_ARCHITECTURE_DOCUMENT"
                payload_rows.append(doc_row)
    
                # Flatten the verified runtime files into the same outer distribution.
                for name in sorted(runtime_table, key=lambda value: value.encode("utf-8")):
                    source_info = zin.getinfo(name)
                    source_mode = (source_info.external_attr >> 16) & 0o777
                    target_info = regular_file_info(
                        name,
                        zipfile.ZIP_STORED if runtime_table[name]["zip_method"] == "STORED" else zipfile.ZIP_DEFLATED,
                        source_mode or 0o644,
                    )
                    row = _stream_entry(zin, source_info, zout, target_info)
                    expected = runtime_table[name]
                    if row["bytes"] != expected["size_bytes"] or row["sha256"] != expected["sha256"]:
                        raise ValueError("RUNTIME_MEMBER_HASH_OR_SIZE_MISMATCH:" + name)
                    row["role"] = "CAJITA_RUNTIME_MEMBER"
                    row["source_zip_method"] = expected["zip_method"]
                    payload_rows.append(row)
                    runtime_member_rows.append({"path": name, "bytes": row["bytes"], "sha256": row["sha256"]})
    
                runtime_manifest_payload = zin.read(RUNTIME_MANIFEST)
                runtime_manifest_row = _write_bytes(zout, RUNTIME_MANIFEST, runtime_manifest_payload, zipfile.ZIP_DEFLATED)
                runtime_manifest_row["role"] = "CAJITA_RUNTIME_MANIFEST"
                payload_rows.append(runtime_manifest_row)
    
                operations = (
                    "# LOUKSNAPG distribution instructions\n\n"
                    "This file is a single ZIP distribution container with the requested filename LOUKSNAPG.md.\n\n"
                    "Extract it with a ZIP-compatible archive manager. Louksna1.md is the governed architecture document. "
                    "The Cajita runtime files are installed at the archive root with their original relative paths; "
                    "MACRODOWN_MANIFEST.json records the source runtime member hashes. The original macrodown is "
                    "not shipped as a second payload. Do not treat this container as plain Markdown or execute it in place.\n\n"
                    "The container carries integrity and provenance evidence, not an automatic functional certificate. "
                    "Use the accompanying build/independent-validation evidence; global certification remains NOT_GRANTED "
                    "until every mandatory functional, semantic, host-resource and rollback gate is independently PASS.\n"
                ).encode("utf-8")
                ops_row = _write_bytes(zout, OPS_DOC, operations, zipfile.ZIP_DEFLATED)
                ops_row["role"] = "DISTRIBUTION_OPERATIONS_DOCUMENT"
                payload_rows.append(ops_row)
    
                bundle_manifest = {
                    "schema": SCHEMA,
                    "product_name": "LOUKSNAPG",
                    "distribution_filename": output.name,
                    "container_format": "ZIP_ARCHIVE_WITH_MARKDOWN_SUFFIX",
                    "source_commit": os.environ.get("GITHUB_SHA") or "UNKNOWN",
                    "built_at_utc": utc_now(),
                    "source": {
                        "louksna1_path": document.name,
                        "louksna1_bytes": len(document_bytes),
                        "louksna1_sha256": sha256_bytes(document_bytes),
                        "protected_architecture_path": source_architecture.name,
                        "protected_architecture_bytes": len(protected_bytes),
                        "protected_architecture_sha256": sha256_bytes(protected_bytes),
                        "protected_prefix_byte_exact": True,
                        "embedded_cajita_document_bytes": len(cajita_bytes),
                        "embedded_cajita_document_sha256": sha256_bytes(cajita_bytes),
                        "runtime_archive_path": runtime_archive.name,
                        "runtime_archive_bytes": runtime_bytes,
                        "runtime_archive_sha256": runtime_sha,
                        "runtime_manifest_sha256": sha256_bytes(runtime_manifest_payload),
                        "runtime_candidate_id": runtime_manifest.get("candidate_id"),
                    },
                    "budget": {"max_bytes": max_bytes, "status": "CAP_ENFORCED_AFTER_ARCHIVE_CLOSE", "measurement_method": "stat_size_after_zip_close"},
                    "members": payload_rows,
                    "runtime_member_count": len(runtime_member_rows),
                    "runtime_member_inventory": runtime_member_rows,
                    "global_certification": "NOT_GRANTED",
                    "certification_reason": "Bundle construction and member integrity do not establish full 21-target functionality, semantic equivalence, target-host coverage or product-update rollback.",
                }
                _write_bytes(
                    zout, BUNDLE_MANIFEST,
                    (json.dumps(bundle_manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
                    zipfile.ZIP_DEFLATED,
                )
    
        size = output.stat().st_size
        if size > max_bytes:
            output.unlink(missing_ok=True)
            raise ValueError(f"LOUKSNAPG_OVER_CAP:{size}>{max_bytes}")
        report = verify_bundle(output, max_bytes=max_bytes)
        report.update({
            "built_at_utc": utc_now(),
            "bundle_sha256": sha256_file(output),
            "source_commit": os.environ.get("GITHUB_SHA") or "UNKNOWN",
            "source_document_sha256": sha256_bytes(document_bytes),
            "source_runtime_archive_sha256": runtime_sha,
            "source_runtime_archive_bytes": runtime_bytes,
            "protected_architecture_sha256": sha256_bytes(protected_bytes),
            "embedded_cajita_document_sha256": sha256_bytes(cajita_bytes),
            "global_certification": "NOT_GRANTED",
        })
        report_path = output.with_name("LOUKSNAPG_BUILD_REPORT.json")
        report_path.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        return report
    
    except Exception:
        # Fail closed: never leave a partial/invalid package looking like a candidate.
        output.unlink(missing_ok=True)
        output.with_name("LOUKSNAPG_BUILD_REPORT.json").unlink(missing_ok=True)
        raise


def verify_bundle(bundle: Path, max_bytes: int = DEFAULT_MAX_BYTES) -> dict:
    if bundle.is_symlink() or not bundle.is_file():
        raise ValueError("BUNDLE_NOT_REGULAR_FILE")
    size = bundle.stat().st_size
    if size > max_bytes:
        raise ValueError(f"LOUKSNAPG_OVER_CAP:{size}>{max_bytes}")
    if not zipfile.is_zipfile(bundle):
        raise ValueError("LOUKSNAPG_NOT_A_ZIP_CONTAINER")
    with zipfile.ZipFile(bundle, "r") as archive:
        bad = archive.testzip()
        if bad:
            raise ValueError("BUNDLE_CRC_FAILURE:" + bad)
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("BUNDLE_DUPLICATE_MEMBERS")
        if BUNDLE_MANIFEST not in names or OPS_DOC not in names or "Louksna1.md" not in names:
            raise ValueError("BUNDLE_REQUIRED_MEMBERS_MISSING")
        manifest = json.loads(archive.read(BUNDLE_MANIFEST).decode("utf-8"))
        if manifest.get("schema") != SCHEMA or manifest.get("product_name") != "LOUKSNAPG":
            raise ValueError("BUNDLE_MANIFEST_SCHEMA_OR_IDENTITY_MISMATCH")
        records = manifest.get("members")
        if not isinstance(records, list):
            raise ValueError("BUNDLE_MEMBER_INVENTORY_INVALID")
        table = {}
        for row in records:
            name = validate_member_name(row.get("path", ""))
            if name == BUNDLE_MANIFEST or name in table:
                raise ValueError("BUNDLE_MEMBER_INVENTORY_COLLISION:" + name)
            table[name] = row
        actual = {name for name in names if name != BUNDLE_MANIFEST}
        if actual != set(table):
            raise ValueError("BUNDLE_MEMBER_SET_DIFFERS_FROM_INVENTORY")
        for name, row in table.items():
            info = archive.getinfo(name)
            if info.is_dir() or ((info.external_attr >> 16) & 0o170000) == stat.S_IFLNK:
                raise ValueError("BUNDLE_UNSAFE_MEMBER:" + name)
            digest = hashlib.sha256()
            total = 0
            with archive.open(info, "r") as stream:
                for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
                    digest.update(chunk)
                    total += len(chunk)
            if total != row.get("bytes") or digest.hexdigest() != row.get("sha256"):
                raise ValueError("BUNDLE_MEMBER_HASH_OR_SIZE_MISMATCH:" + name)
        source = manifest.get("source", {})
        with archive.open("Louksna1.md", "r") as doc:
            prefix = doc.read(int(source.get("protected_architecture_bytes", -1)))
        if len(prefix) != source.get("protected_architecture_bytes") or sha256_bytes(prefix) != source.get("protected_architecture_sha256"):
            raise ValueError("PROTECTED_ARCHITECTURE_PREFIX_HASH_MISMATCH")
        doc_size = archive.getinfo("Louksna1.md").file_size
        cajita_len = int(source.get("embedded_cajita_document_bytes", -1))
        if cajita_len < 0 or cajita_len > doc_size:
            raise ValueError("CAJITA_EMBEDDED_SUFFIX_SIZE_INVALID")
        with archive.open("Louksna1.md", "r") as doc:
            doc.seek(doc_size - cajita_len)
            cajita_digest = hashlib.sha256()
            for chunk in iter(lambda: doc.read(1024 * 1024), b""):
                cajita_digest.update(chunk)
        if cajita_digest.hexdigest() != source.get("embedded_cajita_document_sha256"):
            raise ValueError("CAJITA_EMBEDDED_SUFFIX_HASH_MISMATCH")
        if "CAJITA_LUNA_RUNTIME_V10.macrodown" in names:
            raise ValueError("NESTED_RUNTIME_ARCHIVE_FORBIDDEN")
        runtime_inventory = manifest.get("runtime_member_inventory", [])
        for row in runtime_inventory:
            if row["path"] not in actual:
                raise ValueError("RUNTIME_MEMBER_MISSING:" + row["path"])
    return {
        "schema": SCHEMA,
        "artifact": bundle.name,
        "source_commit": manifest.get("source_commit", "UNKNOWN"),
        "bundle_bytes": size,
        "max_bytes": max_bytes,
        "budget_status": "PASS",
        "integrity_status": "PASS",
        "container_format": "ZIP_ARCHIVE_WITH_MARKDOWN_SUFFIX",
        "member_count": len(names),
        "runtime_member_count": len(manifest["runtime_member_inventory"]),
        "document_sha256": manifest["source"]["louksna1_sha256"],
        "runtime_source_sha256": manifest["source"]["runtime_archive_sha256"],
        "protected_prefix_sha256": manifest["source"]["protected_architecture_sha256"],
        "global_certification": "NOT_GRANTED",
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--document", type=Path)
    parser.add_argument("--runtime", type=Path)
    parser.add_argument("--source-architecture", type=Path)
    parser.add_argument("--cajita-doc", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--max-bytes", type=int, default=DEFAULT_MAX_BYTES)
    parser.add_argument("--verify-bundle", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.verify_bundle:
            report = verify_bundle(args.verify_bundle, max_bytes=args.max_bytes)
        else:
            required = (args.document, args.runtime, args.source_architecture, args.cajita_doc, args.output)
            if any(item is None for item in required):
                parser.error("build mode requires --document, --runtime, --source-architecture, --cajita-doc and --output")
            report = build_bundle(args.document, args.runtime, args.output, args.source_architecture, args.cajita_doc, args.max_bytes)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": f"{type(exc).__name__}:{str(exc)[:1200]}", "global_certification": "NOT_GRANTED"}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
