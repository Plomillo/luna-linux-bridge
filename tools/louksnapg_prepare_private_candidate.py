#!/usr/bin/env python3
"""Safely materialize a private, authenticated experimental runtime bundle on a hosted runner."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import tarfile
from pathlib import Path, PurePosixPath

MAX_BUNDLE_BYTES = 2_000_000_000
MAX_UNPACKED_BYTES = 4_000_000_000
HEX64 = re.compile(r"^[0-9a-f]{64}$")
EXPECTED_PATHS = {
    "D01_CEREBRO": "1. Cerebro/model.safetensors",
    "D03_TRANSCRIPCION": "3. Transcripción/model.safetensors",
    "D04_TRADUCTOR_INTELIGENTE": "4. Traductor Inteligente/Traducción general/model.safetensors",
    "D06_SISTEMA_INTELIGENTE": "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
}
REQUIRED_FILES = [
    "cajita_runtime.py",
    "cajita_task_adapters.py",
    "cajita_target_adapters.py",
    "CAJITA_RUNTIME_V1/weights_manifest.json",
    "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json",
    "1. Cerebro/CAJITA_MODULE.json",
    "3. Transcripción/CAJITA_MODULE.json",
    "4. Traductor Inteligente/Traducción general/CAJITA_MODULE.json",
    "4. Traductor Inteligente/Traducción de lenguas antiguas/CAJITA_MODULE.json",
    "6. Sistema Inteligente/Análisis Avanzado/CAJITA_MODULE.json",
]


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def safe_extract(bundle: Path, destination: Path) -> None:
    if destination.exists():
        raise SystemExit("CANDIDATE_DESTINATION_ALREADY_EXISTS")
    destination.mkdir(parents=True)
    total = 0
    seen: set[str] = set()
    with tarfile.open(bundle, mode="r:gz") as archive:
        members = archive.getmembers()
        for member in members:
            name = member.name
            pure = PurePosixPath(name)
            if pure.is_absolute() or not name or any(part in {"..", ""} for part in pure.parts):
                raise SystemExit("PRIVATE_BUNDLE_PATH_TRAVERSAL_REJECTED")
            if name in seen:
                raise SystemExit("PRIVATE_BUNDLE_DUPLICATE_PATH_REJECTED")
            seen.add(name)
            if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                raise SystemExit("PRIVATE_BUNDLE_LINK_OR_SPECIAL_FILE_REJECTED")
            if member.isfile():
                total += int(member.size)
                if total > MAX_UNPACKED_BYTES:
                    raise SystemExit("PRIVATE_BUNDLE_UNPACKED_SIZE_LIMIT_EXCEEDED")
        for member in members:
            target = destination.joinpath(*PurePosixPath(member.name).parts)
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise SystemExit("PRIVATE_BUNDLE_FILE_CONTENT_MISSING")
            with source, target.open("xb") as output:
                while True:
                    chunk = source.read(1024 * 1024)
                    if not chunk:
                        break
                    output.write(chunk)
            target.chmod(0o644)


def tree_digest(root: Path) -> tuple[str, list[dict]]:
    records = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            raise SystemExit("CANDIDATE_RUNTIME_SYMLINK_REJECTED")
        if not path.is_file():
            continue
        records.append({
            "path": path.relative_to(root).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": digest_file(path),
        })
    canonical = json.dumps(records, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return digest_bytes(canonical), records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--out-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    raw_manifest = args.manifest.read_bytes()
    manifest = json.loads(raw_manifest.decode("utf-8"))
    bundle_desc = manifest.get("private_bundle", {})
    if manifest.get("schema") != "LOUKSNAPG_PHASE4_REPAIR_CANDIDATE/1.0":
        raise SystemExit("REPAIR_MANIFEST_SCHEMA_INVALID")
    if not args.bundle.is_file():
        raise SystemExit("PRIVATE_REPAIR_BUNDLE_MISSING")
    bundle_bytes = args.bundle.stat().st_size
    bundle_sha = digest_file(args.bundle)
    if bundle_bytes <= 0 or bundle_bytes > MAX_BUNDLE_BYTES:
        raise SystemExit("PRIVATE_REPAIR_BUNDLE_SIZE_OUT_OF_BOUNDS")
    if bundle_bytes != bundle_desc.get("bytes") or bundle_sha != bundle_desc.get("sha256"):
        raise SystemExit("PRIVATE_REPAIR_BUNDLE_IDENTITY_MISMATCH")

    safe_extract(args.bundle, args.out_root)
    for required in REQUIRED_FILES:
        if not (args.out_root / required).is_file():
            raise SystemExit("CANDIDATE_RUNTIME_REQUIRED_FILE_MISSING:" + required)

    actual_tree_sha, rows = tree_digest(args.out_root)
    if actual_tree_sha != bundle_desc.get("runtime_tree_sha256"):
        raise SystemExit("CANDIDATE_RUNTIME_TREE_SHA256_MISMATCH")

    weight_rows = manifest.get("candidate_weight_artifacts", [])
    by_domain = {row.get("domain_id"): row for row in weight_rows if isinstance(row, dict)}
    if set(by_domain) != set(EXPECTED_PATHS):
        raise SystemExit("CANDIDATE_WEIGHT_DOMAIN_SET_MISMATCH")
    verified = []
    for domain, expected_path in EXPECTED_PATHS.items():
        item = by_domain[domain]
        if item.get("path") != expected_path:
            raise SystemExit("CANDIDATE_WEIGHT_PATH_MISMATCH:" + domain)
        path = args.out_root / expected_path
        if path.is_symlink() or not path.is_file():
            raise SystemExit("CANDIDATE_WEIGHT_FILE_MISSING_OR_LINKED:" + domain)
        with path.open("rb") as stream:
            pointer = stream.read(64).startswith(b"version https://git-lfs.github.com/spec/v1")
        actual = {
            "domain_id": domain,
            "path": expected_path,
            "bytes": path.stat().st_size,
            "sha256": digest_file(path),
            "lfs_pointer": pointer,
        }
        if pointer or actual["bytes"] != item.get("bytes") or actual["sha256"] != item.get("sha256"):
            raise SystemExit("CANDIDATE_WEIGHT_IDENTITY_MISMATCH:" + domain)
        verified.append(actual)

    output = {
        "schema": "LOUKSNAPG_PRIVATE_CANDIDATE_MATERIALIZATION/1.0",
        "candidate_id": manifest.get("candidate_id"),
        "private_bundle_bytes": bundle_bytes,
        "private_bundle_sha256": bundle_sha,
        "runtime_tree_sha256": actual_tree_sha,
        "runtime_file_count": len(rows),
        "candidate_weights": verified,
        "source_provenance_rows": len(manifest.get("source_provenance", [])),
        "canonical_runtime_mutated": False,
        "repository_runtime_payload_used": False,
        "local_model_payload_uploaded_to_public_repository": False,
        "model_inference_performed": False,
        "global_certification": "NOT_GRANTED",
        "status": "PASS_PRIVATE_CANDIDATE_IDENTITY_VERIFIED",
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(output, sort_keys=True, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, sort_keys=True, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
