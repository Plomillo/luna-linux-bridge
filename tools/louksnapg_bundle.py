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
DEFAULT_MAX_BYTES = 490_000_000
MAX_RUNTIME_BYTES = 470_000_000
RUNTIME_MANIFEST = "MACRODOWN_MANIFEST.json"
BUNDLE_MANIFEST = "LOUKSNAPG_MANIFEST.json"
OPS_DOC = "LOUKSNAPG_OPERATIONS.md"
FIXED_TIME = (1980, 1, 1, 0, 0, 0)

CANONICAL_DOMAIN_ORDER = ["D01_CEREBRO", "D02_ORQUESTACION", "D03_TRANSCRIPCION", "D04_TRADUCTOR_INTELIGENTE", "D05_INTELIGENCIA_DOCUMENTAL", "D06_SISTEMA_INTELIGENTE"]
CANONICAL_ENGINE_BINDINGS = [
    {"id": "E01", "name": "LLM"}, {"id": "E02", "name": "NLP"}, {"id": "E03", "name": "RAG"},
    {"id": "E04", "name": "EMBEDDINGS"}, {"id": "E05", "name": "VECTOR_SEARCH"}, {"id": "E06", "name": "KNOWLEDGE_GRAPH"},
    {"id": "E07", "name": "RDF"}, {"id": "E08", "name": "OWL"}, {"id": "E09", "name": "SEMANTIC_INFERENCE"},
    {"id": "E10", "name": "RULE_ENGINE"}, {"id": "E11", "name": "HERMENEUTIC"}, {"id": "E12", "name": "FORMALIZATION"},
    {"id": "E13", "name": "VALIDATION"}, {"id": "E14", "name": "PROVENANCE"}, {"id": "E15", "name": "CONSENSUS"},
]
CANONICAL_TARGET_IDS = [
    "D01_CEREBRO_ROOT", "D02_CONFESION_ECLESIAL_REFORMADA", "D02_MULTI_INTERDISCIPLINAR", "D02_ORQUESTADOR",
    "D03_TRANSCRIPCION_ROOT", "D04_HERMENEUTICA_HG", "D04_TRADUCCION_LENGUAS_ANTIGUAS", "D04_TRADUCCION_GENERAL",
    "D05_CALIBRE", "D05_DOCLING", "D06_ANTI_ALUCINACIONES", "D06_ANALISIS_AVANZADO", "D06_ARCHIVADO_DETECCION",
    "D06_COGNITIVE_CI_CD", "D06_CONSOLA", "D06_MEMORIA_GOBERNADA", "D06_MIGRACION_PERSISTENCIA", "D06_MOTOR_PROTOCOLAR",
    "D06_PORTABILIDAD_BASE", "D06_RUNTIME_ANDROID_WINDOWS", "D06_TESTING",
]
CANONICAL_COMMAND_IDS = ["HELP", "PT", "PA", "DCI", "DCIL", "TRAD", "E", "EMA", "P", "C", "CP", "MA", "H", "AE"]
MODEL_IDENTITY_SPECS = [
    ("D01_CEREBRO", "1. Cerebro/compression_metadata.json", "OPENAI_GPT_OSS_CEREBRO_MXFP4"),
    ("D03_TRANSCRIPCION", "3. Transcripción/compression_metadata.json", "CAJITA_TRANSCRIPCION_WHISPER_TURBO"),
    ("D04_TRADUCTOR_INTELIGENTE", "4. Traductor Inteligente/Traducción general/compression_metadata.json", "CAJITA_TRADUCCION_SEAMLESSM4T_V2_LARGE"),
    ("D05_INTELIGENCIA_DOCUMENTAL", "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_manifest.json", "ibm-granite/granite-docling-258M"),
    ("D06_SISTEMA_INTELIGENTE", "6. Sistema Inteligente/Análisis Avanzado/compression_metadata.json", "CAJITA_SISTEMA_INTELIGENTE_ANALISIS_AVANZADO_QWEN3"),
]
AXIOM_DEBT_POLICY = "PRESERVE_DECLARED_AXIOM_DEBT_NO_SYNTHETIC_ADMISSION"
BLOCK_IDENTITY_POLICY = "PRESERVE_B1_B134_NO_RENUMBERING_OR_REASSIGNMENT"


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




def _verified_json_member(archive: zipfile.ZipFile, runtime_table: dict[str, dict], name: str) -> tuple[dict, str]:
    row = runtime_table.get(name)
    if row is None:
        raise ValueError("IDENTITY_BINDING_MEMBER_MISSING:" + name)
    payload = archive.read(name)
    if len(payload) != row.get("size_bytes") or sha256_bytes(payload) != row.get("sha256"):
        raise ValueError("IDENTITY_BINDING_MEMBER_HASH_MISMATCH:" + name)
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("IDENTITY_BINDING_JSON_INVALID:" + name) from exc
    if not isinstance(value, dict):
        raise ValueError("IDENTITY_BINDING_JSON_ROOT_INVALID:" + name)
    return value, sha256_bytes(payload)


def build_identity_preservation(archive: zipfile.ZipFile, runtime_table: dict[str, dict]) -> dict:
    routing, routing_sha = _verified_json_member(archive, runtime_table, "command_subdomain_routing.json")
    domains = routing.get("domain_order")
    engines = [{"id": x.get("id"), "name": x.get("name")} for x in routing.get("engine_registry", [])]
    targets = [x.get("id") for x in routing.get("targets", [])]
    commands = [x.get("id") for x in routing.get("route_profiles", [])]
    if domains != CANONICAL_DOMAIN_ORDER:
        raise ValueError("CANONICAL_DOMAIN_ORDER_MUTATION")
    if engines != CANONICAL_ENGINE_BINDINGS or routing.get("state", {}).get("engine_count") != 15:
        raise ValueError("CANONICAL_ENGINE_REPLACEMENT_OR_REASSIGNMENT_DETECTED")
    if targets != CANONICAL_TARGET_IDS or len(set(targets)) != 21:
        raise ValueError("CANONICAL_TARGET_ID_MUTATION_OR_REASSIGNMENT_DETECTED")
    if commands != CANONICAL_COMMAND_IDS or len(set(commands)) != 14:
        raise ValueError("CANONICAL_COMMAND_ID_MUTATION_OR_REASSIGNMENT_DETECTED")
    model_rows = []
    for target_id, path, model_id in MODEL_IDENTITY_SPECS:
        metadata, digest = _verified_json_member(archive, runtime_table, path)
        if metadata.get("model_id") != model_id:
            raise ValueError("MODEL_ENGINE_REPLACEMENT_DETECTED:" + target_id)
        model_rows.append({"target_id": target_id, "metadata_path": path, "model_id": model_id, "metadata_sha256": digest})
    return {
        "status": "PASS_SOURCE_IDENTITY_PRESERVED",
        "engine_replacement": "FORBIDDEN",
        "domain_order": domains,
        "engine_bindings": engines,
        "target_ids": targets,
        "command_ids": commands,
        "routing_metadata_sha256": routing_sha,
        "model_identity_bindings": model_rows,
        "axiom_debt_policy": AXIOM_DEBT_POLICY,
        "block_identity_policy": BLOCK_IDENTITY_POLICY,
        "architecture_prefix_preservation": "BYTE_EXACT_HASH_VERIFIED",
        "synthetic_identity_admission": False,
    }


def validate_identity_preservation_in_bundle(archive: zipfile.ZipFile, names: set[str], identity: dict) -> str:
    if not isinstance(identity, dict) or identity.get("status") != "PASS_SOURCE_IDENTITY_PRESERVED":
        raise ValueError("ENGINE_IDENTITY_PRESERVATION_PROOF_MISSING")
    if identity.get("engine_replacement") != "FORBIDDEN":
        raise ValueError("ENGINE_REPLACEMENT_POLICY_MISMATCH")
    if identity.get("axiom_debt_policy") != AXIOM_DEBT_POLICY or identity.get("block_identity_policy") != BLOCK_IDENTITY_POLICY:
        raise ValueError("AXIOM_DEBT_OR_BLOCK_PRESERVATION_POLICY_MISMATCH")
    if identity.get("synthetic_identity_admission") is not False:
        raise ValueError("SYNTHETIC_IDENTITY_ADMISSION_FORBIDDEN")
    if "command_subdomain_routing.json" not in names:
        raise ValueError("CANONICAL_ROUTING_MEMBER_MISSING")
    routing_bytes = archive.read("command_subdomain_routing.json")
    if sha256_bytes(routing_bytes) != identity.get("routing_metadata_sha256"):
        raise ValueError("CANONICAL_ROUTING_HASH_BINDING_MISMATCH")
    routing = json.loads(routing_bytes.decode("utf-8"))
    engines = [{"id": x.get("id"), "name": x.get("name")} for x in routing.get("engine_registry", [])]
    targets = [x.get("id") for x in routing.get("targets", [])]
    commands = [x.get("id") for x in routing.get("route_profiles", [])]
    if routing.get("domain_order") != CANONICAL_DOMAIN_ORDER or identity.get("domain_order") != CANONICAL_DOMAIN_ORDER:
        raise ValueError("CANONICAL_DOMAIN_ORDER_IDENTITY_MISMATCH")
    if engines != CANONICAL_ENGINE_BINDINGS or identity.get("engine_bindings") != CANONICAL_ENGINE_BINDINGS:
        raise ValueError("ENGINE_BINDING_IDENTITY_MISMATCH")
    if targets != CANONICAL_TARGET_IDS or identity.get("target_ids") != CANONICAL_TARGET_IDS:
        raise ValueError("CANONICAL_TARGET_IDENTITY_MISMATCH")
    if commands != CANONICAL_COMMAND_IDS or identity.get("command_ids") != CANONICAL_COMMAND_IDS:
        raise ValueError("CANONICAL_COMMAND_IDENTITY_MISMATCH")
    if routing.get("state", {}).get("engine_count") != 15:
        raise ValueError("CANONICAL_ENGINE_COUNT_MISMATCH")
    bindings = identity.get("model_identity_bindings")
    if not isinstance(bindings, list) or len(bindings) != len(MODEL_IDENTITY_SPECS):
        raise ValueError("MODEL_IDENTITY_BINDING_COUNT_MISMATCH")
    by_target = {x.get("target_id"): x for x in bindings if isinstance(x, dict)}
    if len(by_target) != len(MODEL_IDENTITY_SPECS):
        raise ValueError("MODEL_IDENTITY_BINDING_COLLISION")
    for target_id, path, model_id in MODEL_IDENTITY_SPECS:
        record = by_target.get(target_id)
        if not isinstance(record, dict) or record.get("metadata_path") != path or record.get("model_id") != model_id:
            raise ValueError("MODEL_IDENTITY_BINDING_MUTATION:" + target_id)
        if path not in names:
            raise ValueError("MODEL_IDENTITY_METADATA_MISSING:" + path)
        payload = archive.read(path)
        if sha256_bytes(payload) != record.get("metadata_sha256"):
            raise ValueError("MODEL_IDENTITY_METADATA_HASH_MISMATCH:" + target_id)
        if json.loads(payload.decode("utf-8")).get("model_id") != model_id:
            raise ValueError("MODEL_ENGINE_REPLACEMENT_DETECTED:" + target_id)
    return "PASS_SOURCE_IDENTITY_PRESERVED"


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
    runtime_bytes = runtime_archive.stat().st_size
    if runtime_bytes > MAX_RUNTIME_BYTES:
        raise ValueError(f"CAJITA_RUNTIME_OVER_CAP:{runtime_bytes}>{MAX_RUNTIME_BYTES}")
    runtime_sha = sha256_file(runtime_archive)
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
            identity_preservation = build_identity_preservation(zin, runtime_table)
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
                    "Engine replacement is forbidden; E01-E15, 21 target IDs, 14 command IDs, model IDs, block identities and declared axiom debt are preserved.\n\n"
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
                    "identity_preservation": identity_preservation,
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
                    "budget": {
                        "max_bytes": max_bytes,
                        "runtime_archive_max_bytes": MAX_RUNTIME_BYTES,
                        "runtime_archive_bytes": runtime_bytes,
                        "runtime_archive_status": "PASS",
                        "status": "CAP_ENFORCED_AFTER_ARCHIVE_CLOSE",
                        "measurement_method": "stat_size_after_zip_close"
                    },
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
        source_record = manifest.get("source", {})
        runtime_archive_bytes = source_record.get("runtime_archive_bytes") if isinstance(source_record, dict) else None
        if isinstance(runtime_archive_bytes, bool) or not isinstance(runtime_archive_bytes, int) or runtime_archive_bytes <= 0:
            raise ValueError("RUNTIME_ARCHIVE_BYTE_COUNT_MISSING")
        if runtime_archive_bytes > MAX_RUNTIME_BYTES:
            raise ValueError(f"CAJITA_RUNTIME_OVER_CAP:{runtime_archive_bytes}>{MAX_RUNTIME_BYTES}")
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
        identity_status = validate_identity_preservation_in_bundle(archive, set(names), manifest.get("identity_preservation"))
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
        "runtime_archive_bytes": runtime_archive_bytes,
        "runtime_archive_max_bytes": MAX_RUNTIME_BYTES,
        "runtime_archive_budget_status": "PASS",
        "budget_status": "PASS",
        "integrity_status": "PASS",
        "container_format": "ZIP_ARCHIVE_WITH_MARKDOWN_SUFFIX",
        "member_count": len(names),
        "runtime_member_count": len(manifest["runtime_member_inventory"]),
        "document_sha256": manifest["source"]["louksna1_sha256"],
        "runtime_source_sha256": manifest["source"]["runtime_archive_sha256"],
        "identity_preservation_status": identity_status,
        "engine_replacement": "FORBIDDEN",
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
