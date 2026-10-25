#!/usr/bin/env python3
"""Losslessly gzip large tokenizer JSON files and materialize them from verified temporary views."""
from __future__ import annotations

import gzip
import hashlib
import io
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path, PurePosixPath

SCHEMA = "CAJITA_COMPRESSED_TOKENIZER_MANIFEST/1.0"
MANIFEST_NAME = "CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json"
DEFAULT_TOKENIZER_PATHS = (
    "1. Cerebro/tokenizer.json",
    "3. Transcripción/tokenizer.json",
    "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/tokenizer.json",
    "6. Sistema Inteligente/Análisis Avanzado/tokenizer.json",
)


class TokenizerMaterializationError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _decompress_bounded(data: bytes, expected_bytes: int) -> bytes:
    if isinstance(expected_bytes, bool) or not isinstance(expected_bytes, int) or not 1 <= expected_bytes <= 128_000_000:
        raise TokenizerMaterializationError("TOKENIZER_EXPANSION_SIZE_OUT_OF_RANGE")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(data), mode="rb") as stream:
            raw = stream.read(expected_bytes + 1)
            if len(raw) != expected_bytes or stream.read(1):
                raise TokenizerMaterializationError("TOKENIZER_EXPANSION_SIZE_MISMATCH")
            return raw
    except (OSError, EOFError) as exc:
        raise TokenizerMaterializationError("TOKENIZER_GZIP_INVALID") from exc


def _safe_rel(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise TokenizerMaterializationError("TOKENIZER_PATH_INVALID")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise TokenizerMaterializationError("TOKENIZER_PATH_UNSAFE:" + value[:180])
    return path.as_posix()


def _source_commit(root: Path) -> str:
    for parent in (root, *root.parents):
        if (parent / ".git").exists():
            try:
                return subprocess.run(
                    ["git", "-C", str(parent), "rev-parse", "HEAD"],
                    check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10,
                ).stdout.strip()
            except (OSError, subprocess.SubprocessError):
                break
    return "UNAVAILABLE_OUTSIDE_GIT_WORKTREE"


def _atomic_write(path: Path, data: bytes) -> None:
    if path.is_symlink():
        raise TokenizerMaterializationError("TOKENIZER_OUTPUT_SYMLINK_REFUSED:" + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(path.name + ".building")
    if temp.is_symlink():
        raise TokenizerMaterializationError("TOKENIZER_TEMP_SYMLINK_REFUSED:" + temp.name)
    try:
        temp.write_bytes(data)
        os.replace(temp, path)
    finally:
        if temp.exists():
            temp.unlink()


def _canonical_manifest(root: Path, paths: tuple[str, ...]) -> dict:
    root = Path(root).resolve()
    rows = []
    seen = set()
    for raw_rel in paths:
        rel = _safe_rel(raw_rel)
        if rel in seen:
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_PATH_COLLISION:" + rel)
        seen.add(rel)
        source = root.joinpath(*PurePosixPath(rel).parts)
        if source.is_symlink() or not source.is_file() or not source.resolve().is_relative_to(root):
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_NOT_REGULAR:" + rel)
        original = source.read_bytes()
        original_sha = sha256_bytes(original)
        # mtime=0 removes timestamps; normalize the gzip OS byte to 255 so the
        # header is stable across Python/zlib build environments.
        packed = bytearray(gzip.compress(original, compresslevel=9, mtime=0))
        if len(packed) >= 10:
            packed[9] = 255
        packed_bytes = bytes(packed)
        compressed_rel = rel + ".gz"
        compressed = root.joinpath(*PurePosixPath(compressed_rel).parts)
        if compressed.is_symlink() or not compressed.resolve().is_relative_to(root):
            raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_PATH_UNSAFE:" + compressed_rel)
        packed_enabled = len(packed_bytes) < len(original)
        if packed_enabled:
            _atomic_write(compressed, packed_bytes)
            # Verify that writing the sidecar did not alter the source and that
            # the decompressed bytes remain byte-identical.
            if sha256_file(source) != original_sha or gzip.decompress(compressed.read_bytes()) != original:
                raise TokenizerMaterializationError("TOKENIZER_LOSSLESS_RECHECK_FAILED:" + rel)
            compressed_sha = sha256_bytes(packed_bytes)
            compressed_size = len(packed_bytes)
        else:
            compressed_sha = None
            compressed_size = None
            if compressed.exists():
                # Do not leave an unreferenced derived file if compression
                # provides no size benefit.
                compressed.unlink()
        rows.append({
            "id": "TOK_" + str(len(rows) + 1).zfill(3),
            "source_path": rel,
            "source_bytes": len(original),
            "source_sha256": original_sha,
            "packed": packed_enabled,
            "compression": "GZIP_LEVEL9_MTIME0_LOSSLESS" if packed_enabled else "NOT_PACKED_NO_SIZE_SAVING",
            "compressed_path": compressed_rel if packed_enabled else None,
            "compressed_bytes": compressed_size,
            "compressed_sha256": compressed_sha,
            "runtime_materialization": "TEMPORARY_VIEW_WITH_SOURCE_BYTES_RESTORED",
            "semantic_change": False,
            "quality_equivalence": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        })
    return {
        "schema": SCHEMA,
        "source_commit": _source_commit(root),
        "policy": "LOSSLESS_DETERMINISTIC_GZIP_WITH_HASH_PINNED_TEMPORARY_MATERIALIZATION",
        "source_files_preserved_in_repository": True,
        "only_packed_sources_excluded_from_distribution": True,
        "entries": rows,
        "source_bytes_total": sum(row["source_bytes"] for row in rows),
        "compressed_bytes_total": sum(row["compressed_bytes"] or 0 for row in rows),
        "bytes_saved_total": sum(row["source_bytes"] - row["compressed_bytes"] for row in rows if row["packed"]),
        "semantic_equivalence": "BYTE_EXACT_TOKENIZER_BYTES; MODEL_QUALITY_EQUIVALENCE_NOT_ESTABLISHED",
        "certification": "NOT_GRANTED",
    }


def prepare_compressed_tokenizers(runtime_root: Path, tokenizer_paths: tuple[str, ...] = DEFAULT_TOKENIZER_PATHS) -> dict:
    root = Path(runtime_root).resolve()
    manifest_path = root / MANIFEST_NAME
    if manifest_path.is_symlink():
        raise TokenizerMaterializationError("TOKENIZER_MANIFEST_SYMLINK_REFUSED")
    missing = [
        _safe_rel(value) for value in tokenizer_paths
        if not (root.joinpath(*PurePosixPath(_safe_rel(value)).parts).is_file())
    ]
    if missing:
        # For reruns over a package that has already omitted source JSON, accept
        # only an existing, hash-valid manifest and all registered .gz payloads.
        if not manifest_path.is_file():
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_FILES_MISSING:" + ",".join(missing))
        manifest = load_tokenizer_manifest(root)
        registered = {row["source_path"] for row in manifest["entries"] if row.get("packed")}
        if not set(missing) <= registered:
            raise TokenizerMaterializationError("TOKENIZER_MISSING_SOURCE_NOT_REGISTERED")
        return manifest
    manifest = _canonical_manifest(root, tuple(tokenizer_paths))
    encoded = (json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
    _atomic_write(manifest_path, encoded)
    # Re-read and verify through the same public validation path used by runtime.
    return load_tokenizer_manifest(root)


def load_tokenizer_manifest(runtime_root: Path) -> dict:
    root = Path(runtime_root).resolve()
    path = root / MANIFEST_NAME
    if path.is_symlink() or not path.is_file() or not path.resolve().is_relative_to(root):
        raise TokenizerMaterializationError("TOKENIZER_MANIFEST_MISSING_OR_UNSAFE")
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise TokenizerMaterializationError("TOKENIZER_MANIFEST_INVALID_JSON:" + type(exc).__name__) from exc
    if not isinstance(manifest, dict) or manifest.get("schema") != SCHEMA or not isinstance(manifest.get("entries"), list):
        raise TokenizerMaterializationError("TOKENIZER_MANIFEST_SCHEMA_INVALID")
    seen_sources = set()
    seen_compressed = set()
    for row in manifest["entries"]:
        if not isinstance(row, dict):
            raise TokenizerMaterializationError("TOKENIZER_MANIFEST_ROW_INVALID")
        source_rel = _safe_rel(row.get("source_path"))
        if source_rel in seen_sources:
            raise TokenizerMaterializationError("TOKENIZER_MANIFEST_SOURCE_COLLISION:" + source_rel)
        seen_sources.add(source_rel)
        source_bytes = row.get("source_bytes")
        source_sha = row.get("source_sha256")
        if isinstance(source_bytes, bool) or not isinstance(source_bytes, int) or source_bytes < 1:
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_SIZE_INVALID:" + source_rel)
        if not isinstance(source_sha, str) or len(source_sha) != 64 or any(ch not in "0123456789abcdef" for ch in source_sha):
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_SHA_INVALID:" + source_rel)
        if row.get("packed") is True:
            compressed_rel = _safe_rel(row.get("compressed_path"))
            if compressed_rel != source_rel + ".gz" or compressed_rel in seen_compressed:
                raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_PATH_COLLISION_OR_MISMATCH:" + source_rel)
            seen_compressed.add(compressed_rel)
            packed = root.joinpath(*PurePosixPath(compressed_rel).parts)
            if packed.is_symlink() or not packed.is_file() or not packed.resolve().is_relative_to(root):
                raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_FILE_MISSING_OR_UNSAFE:" + compressed_rel)
            size = row.get("compressed_bytes")
            digest = row.get("compressed_sha256")
            if isinstance(size, bool) or not isinstance(size, int) or packed.stat().st_size != size:
                raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_SIZE_MISMATCH:" + compressed_rel)
            if not isinstance(digest, str) or sha256_file(packed) != digest:
                raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_SHA_MISMATCH:" + compressed_rel)
    return manifest


def find_runtime_root(model_root: Path) -> Path:
    model_root = Path(model_root).resolve()
    for candidate in (model_root, *model_root.parents):
        manifest = candidate / MANIFEST_NAME
        if manifest.is_file() and not manifest.is_symlink():
            return candidate
    raise TokenizerMaterializationError("TOKENIZER_RUNTIME_ROOT_NOT_FOUND")


def _validate_tree_no_symlinks(root: Path) -> None:
    root = Path(root).resolve()
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        bp = Path(base)
        kept = []
        for name in sorted(dirs):
            p = bp / name
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise TokenizerMaterializationError("TOKENIZER_MODEL_TREE_SYMLINK_OR_ESCAPE:" + str(p))
            kept.append(name)
        dirs[:] = kept
        for name in sorted(files):
            p = bp / name
            if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root):
                raise TokenizerMaterializationError("TOKENIZER_MODEL_TREE_NON_REGULAR:" + str(p))


def load_pretrained_with_compressed_tokenizer(model_root: Path, loader_class, **kwargs):
    """Load an HF processor/tokenizer from raw data or a verified gzip-backed temporary view."""
    model_root = Path(model_root).resolve()
    if not model_root.is_dir() or model_root.is_symlink():
        raise TokenizerMaterializationError("TOKENIZER_MODEL_ROOT_INVALID")
    manifest_path = None
    runtime_root = None
    for candidate in (model_root, *model_root.parents):
        p = candidate / MANIFEST_NAME
        if p.is_file() and not p.is_symlink():
            manifest_path = p
            runtime_root = candidate
            break
    if manifest_path is None or runtime_root is None:
        raise TokenizerMaterializationError("TOKENIZER_COMPRESSION_MANIFEST_NOT_FOUND")
    manifest = load_tokenizer_manifest(runtime_root)
    source_rel = (model_root.relative_to(runtime_root) / "tokenizer.json").as_posix()
    matches = [row for row in manifest["entries"] if row.get("source_path") == source_rel]
    if len(matches) != 1:
        tokenizer_path = model_root / "tokenizer.json"
        compressed_path = model_root / "tokenizer.json.gz"
        if tokenizer_path.is_file() and not tokenizer_path.is_symlink():
            return loader_class.from_pretrained(str(model_root), **kwargs)
        if compressed_path.exists() or compressed_path.is_symlink():
            raise TokenizerMaterializationError("TOKENIZER_COMPRESSED_FILE_NOT_REGISTERED:" + source_rel)
        # Some processors are intentionally SentencePiece/vocab based and do
        # not contain tokenizer.json. Keep their original local-only loader.
        return loader_class.from_pretrained(str(model_root), **kwargs)
    row = matches[0]
    source = model_root / "tokenizer.json"
    if source.is_file() and not source.is_symlink():
        if source.stat().st_size != row["source_bytes"] or sha256_file(source) != row["source_sha256"]:
            raise TokenizerMaterializationError("TOKENIZER_SOURCE_IDENTITY_MISMATCH:" + source_rel)
        return loader_class.from_pretrained(str(model_root), **kwargs)
    if not row.get("packed"):
        raise TokenizerMaterializationError("TOKENIZER_SOURCE_ABSENT_AND_NOT_PACKED:" + source_rel)
    _validate_tree_no_symlinks(model_root)
    packed_rel = _safe_rel(row["compressed_path"])
    packed = runtime_root.joinpath(*PurePosixPath(packed_rel).parts)
    if packed.is_symlink() or not packed.is_file() or not packed.resolve().is_relative_to(runtime_root):
        raise TokenizerMaterializationError("TOKENIZER_PACKED_PAYLOAD_UNSAFE:" + packed_rel)
    packed_bytes = packed.read_bytes()
    if len(packed_bytes) != row["compressed_bytes"] or sha256_bytes(packed_bytes) != row["compressed_sha256"]:
        raise TokenizerMaterializationError("TOKENIZER_PACKED_PAYLOAD_CHANGED:" + packed_rel)
    try:
        raw = _decompress_bounded(packed_bytes, row["source_bytes"])
    except (OSError, EOFError) as exc:
        raise TokenizerMaterializationError("TOKENIZER_GZIP_INVALID:" + packed_rel) from exc
    if len(raw) != row["source_bytes"] or sha256_bytes(raw) != row["source_sha256"]:
        raise TokenizerMaterializationError("TOKENIZER_DECOMPRESSED_IDENTITY_MISMATCH:" + source_rel)
    with tempfile.TemporaryDirectory(prefix="cajita-tokenizer-view-") as temporary:
        view = Path(temporary) / "model"
        view.mkdir()
        for child in model_root.iterdir():
            if child.name in {"tokenizer.json", Path(packed_rel).name}:
                continue
            target = view / child.name
            if child.is_symlink():
                raise TokenizerMaterializationError("TOKENIZER_VIEW_CHILD_SYMLINK_REFUSED:" + child.name)
            target.symlink_to(child, target_is_directory=child.is_dir())
        (view / "tokenizer.json").write_bytes(raw)
        if sha256_file(view / "tokenizer.json") != row["source_sha256"]:
            raise TokenizerMaterializationError("TOKENIZER_VIEW_RECHECK_FAILED:" + source_rel)
        return loader_class.from_pretrained(str(view), **kwargs)


def tokenizer_tree_rows(module_root: Path, runtime_root: Path, rows: list[dict]) -> list[dict]:
    """Preserve the original module tree identity when JSON tokenizers are packed as .gz."""
    root = Path(runtime_root).resolve()
    module = Path(module_root).resolve()
    if not module.is_relative_to(root):
        raise TokenizerMaterializationError("TOKENIZER_TREE_MODULE_OUTSIDE_RUNTIME")
    manifest = load_tokenizer_manifest(root)
    by_source = {row["source_path"]: row for row in manifest["entries"] if row.get("packed")}
    by_compressed = {row["compressed_path"]: row for row in manifest["entries"] if row.get("packed")}
    module_rel = module.relative_to(root).as_posix()
    filtered = []
    for row in rows:
        rel = (PurePosixPath(module_rel) / PurePosixPath(row["path"])).as_posix()
        if rel in by_compressed:
            # Gzip is a storage representation, not a new logical module file.
            continue
        if rel in by_source and row["path"] == "tokenizer.json":
            # Source checkout: keep the exact original row in the module hash.
            filtered.append(row)
            continue
        filtered.append(row)
    has_raw = any(row["path"] == "tokenizer.json" for row in filtered)
    if not has_raw:
        candidate = (PurePosixPath(module_rel) / "tokenizer.json").as_posix()
        entry = by_source.get(candidate)
        if entry:
            compressed_rel = _safe_rel(entry["compressed_path"])
            compressed = root.joinpath(*PurePosixPath(compressed_rel).parts)
            if compressed.is_symlink() or not compressed.is_file() or sha256_file(compressed) != entry["compressed_sha256"]:
                raise TokenizerMaterializationError("TOKENIZER_TREE_COMPRESSED_SHA_MISMATCH:" + candidate)
            raw = _decompress_bounded(compressed.read_bytes(), entry["source_bytes"])
            if len(raw) != entry["source_bytes"] or sha256_bytes(raw) != entry["source_sha256"]:
                raise TokenizerMaterializationError("TOKENIZER_TREE_RECONSTRUCTION_MISMATCH:" + candidate)
            filtered.append({"path": "tokenizer.json", "bytes": entry["source_bytes"], "sha256": entry["source_sha256"]})
    return sorted(filtered, key=lambda row: row["path"].encode("utf-8"))
