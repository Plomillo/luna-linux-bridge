#!/usr/bin/env python3
"""Source-pinned, on-demand retrieval for the ten externalized Cajita assets.

No asset is fetched during startup. Downloads are allowed only for registered IDs,
from the exact immutable source commit, and are accepted only after size and
SHA-256 checks. Extraction is an explicit operation with path/tree verification.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path, PurePosixPath

REGISTRY_SCHEMA = "LOUKSNAPG2_EXTERNALIZED_ASSET_REGISTRY/1.0"
PINNED_COMMIT = "17d9dfc3aba4b0f4132f3a0d18d4d078fdb6736d"
PINNED_REPOSITORY = "Plomillo/luna-linux-bridge"
PINNED_BASE_URL = f"https://raw.githubusercontent.com/{PINNED_REPOSITORY}/{PINNED_COMMIT}/externalized-assets-staging/optimized-containers/"
MAX_ARCHIVE_BYTES = 40_000_000
MAX_EXPANDED_BYTES = 200_000_000
MAX_EXPANDED_FILES = 20_000


class AssetLoaderError(RuntimeError):
    pass


def canonical_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def safe_relative_path(value: str) -> PurePosixPath:
    if not isinstance(value, str) or not value or "\\" in value or value.startswith("/"):
        raise AssetLoaderError("ASSET_PATH_ABSOLUTE_OR_INVALID")
    path = PurePosixPath(value)
    if any(part in ("", ".", "..") for part in path.parts) or path.as_posix() != value:
        raise AssetLoaderError("ASSET_PATH_TRAVERSAL_REJECTED")
    return path


def load_registry(path: Path | None = None) -> dict:
    if path is None:
        path = Path(__file__).resolve().parent / "externalized_assets.json"
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise AssetLoaderError("EXTERNALIZED_ASSET_REGISTRY_MISSING_OR_UNSAFE")
    try:
        registry = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AssetLoaderError("EXTERNALIZED_ASSET_REGISTRY_INVALID_JSON") from exc
    if not isinstance(registry, dict) or registry.get("schema") != REGISTRY_SCHEMA:
        raise AssetLoaderError("EXTERNALIZED_ASSET_REGISTRY_SCHEMA_MISMATCH")
    if registry.get("source_repository") != PINNED_REPOSITORY or registry.get("source_commit") != PINNED_COMMIT:
        raise AssetLoaderError("EXTERNALIZED_ASSET_SOURCE_BINDING_MISMATCH")
    if registry.get("source_base_url") != PINNED_BASE_URL:
        raise AssetLoaderError("EXTERNALIZED_ASSET_URL_BASE_MISMATCH")
    if registry.get("activation_policy") != "ON_DEMAND_ONLY":
        raise AssetLoaderError("EXTERNALIZED_ASSET_ACTIVATION_POLICY_MISMATCH")
    rows = registry.get("assets")
    if not isinstance(rows, list) or len(rows) != 10:
        raise AssetLoaderError("EXTERNALIZED_ASSET_COUNT_MISMATCH")
    seen_ids, seen_names = set(), set()
    for row in rows:
        if not isinstance(row, dict):
            raise AssetLoaderError("EXTERNALIZED_ASSET_ROW_INVALID")
        asset_id = row.get("id")
        filename = row.get("filename")
        if not isinstance(asset_id, str) or asset_id in seen_ids:
            raise AssetLoaderError("EXTERNALIZED_ASSET_ID_DUPLICATE_OR_INVALID")
        if not isinstance(filename, str) or Path(filename).name != filename or filename in seen_names:
            raise AssetLoaderError("EXTERNALIZED_ASSET_FILENAME_DUPLICATE_OR_INVALID")
        size = row.get("bytes")
        digest = row.get("sha256")
        expanded = safe_relative_path(row.get("expanded_path", ""))
        if isinstance(size, bool) or not isinstance(size, int) or not 1 <= size <= MAX_ARCHIVE_BYTES:
            raise AssetLoaderError("EXTERNALIZED_ASSET_SIZE_INVALID:" + asset_id)
        if not isinstance(digest, str) or len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
            raise AssetLoaderError("EXTERNALIZED_ASSET_SHA256_INVALID:" + asset_id)
        if not isinstance(row.get("expanded_tree_sha256"), str) or len(row["expanded_tree_sha256"]) != 64:
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_TREE_HASH_INVALID:" + asset_id)
        if isinstance(row.get("expanded_bytes"), bool) or not isinstance(row.get("expanded_bytes"), int) or not 1 <= row["expanded_bytes"] <= MAX_EXPANDED_BYTES:
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_SIZE_INVALID:" + asset_id)
        if isinstance(row.get("expanded_file_count"), bool) or not isinstance(row.get("expanded_file_count"), int) or not 1 <= row["expanded_file_count"] <= MAX_EXPANDED_FILES:
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_FILE_COUNT_INVALID:" + asset_id)
        seen_ids.add(asset_id)
        seen_names.add(filename)
    return registry


def _safe_url(registry: dict, row: dict) -> str:
    filename = row["filename"]
    if Path(filename).name != filename:
        raise AssetLoaderError("EXTERNALIZED_ASSET_FILENAME_PATH_TRAVERSAL")
    return PINNED_BASE_URL + urllib.parse.quote(filename, safe="._-")


def _stream_download(url: str, target: Path, expected_bytes: int) -> dict:
    if urllib.parse.urlsplit(url).scheme != "https" or urllib.parse.urlsplit(url).hostname != "raw.githubusercontent.com":
        raise AssetLoaderError("EXTERNALIZED_ASSET_URL_HOST_NOT_ALLOWED")
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=".louksnapg2-download-", dir=str(target.parent))
    digest = hashlib.sha256()
    total = 0
    try:
        request = urllib.request.Request(
            url, headers={"User-Agent": "LOUKSNAPG2-ExternalizedAssetLoader/1.0", "Cache-Control": "no-cache"}
        )
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(request, timeout=45) as response:
            final = urllib.parse.urlsplit(response.geturl())
            if response.status != 200 or final.scheme != "https" or final.hostname != "raw.githubusercontent.com":
                raise AssetLoaderError("EXTERNALIZED_ASSET_HTTP_SOURCE_REDIRECT_REJECTED")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                total += len(block)
                if total > expected_bytes or total > MAX_ARCHIVE_BYTES:
                    raise AssetLoaderError("EXTERNALIZED_ASSET_DOWNLOAD_EXCEEDS_PINNED_SIZE")
                digest.update(block)
                output.write(block)
        if total != expected_bytes:
            raise AssetLoaderError("EXTERNALIZED_ASSET_DOWNLOAD_SIZE_MISMATCH")
        return {"temp_path": temp_name, "bytes": total, "sha256": digest.hexdigest()}
    except Exception:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise


def fetch_asset(asset_id: str, cache_root: Path, *, registry_path: Path | None = None) -> dict:
    registry = load_registry(registry_path)
    matches = [row for row in registry["assets"] if row["id"] == asset_id]
    if len(matches) != 1:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ID_NOT_REGISTERED")
    row = matches[0]
    cache_root = Path(cache_root).resolve()
    target = cache_root / "archives" / row["filename"]
    if target.exists() or target.is_symlink():
        if target.is_symlink() or not target.is_file():
            raise AssetLoaderError("EXTERNALIZED_ASSET_CACHE_TARGET_UNSAFE")
        size = target.stat().st_size
        digest = sha256_file(target)
        if size == row["bytes"] and digest == row["sha256"]:
            return {"status": "PASS_CACHE_HIT_HASH_VERIFIED", "asset_id": asset_id, "path": str(target), "bytes": size, "sha256": digest}
        # Do not silently overwrite a corrupt cached asset.
        raise AssetLoaderError("EXTERNALIZED_ASSET_CACHE_IDENTITY_MISMATCH")
    downloaded = _stream_download(_safe_url(registry, row), target, row["bytes"])
    if downloaded["sha256"] != row["sha256"]:
        Path(downloaded["temp_path"]).unlink(missing_ok=True)
        raise AssetLoaderError("EXTERNALIZED_ASSET_SHA256_MISMATCH")
    target.parent.mkdir(parents=True, exist_ok=True)
    os.replace(downloaded["temp_path"], target)
    return {
        "status": "PASS_DOWNLOADED_HASH_VERIFIED",
        "asset_id": asset_id,
        "path": str(target),
        "bytes": downloaded["bytes"],
        "sha256": downloaded["sha256"],
        "source_commit": registry["source_commit"],
    }


def _list_archive_paths(archive: Path) -> list[str]:
    executable = shutil.which("7z") or shutil.which("7zz")
    if not executable:
        raise AssetLoaderError("7Z_EXECUTABLE_REQUIRED_FOR_EXPLICIT_EXTRACTION")
    result = subprocess.run(
        [executable, "l", "-slt", "-ba", str(archive)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120, check=False,
    )
    if result.returncode:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ARCHIVE_LIST_FAILED")
    rows = []
    for line in result.stdout.splitlines():
        if line.startswith("Path = "):
            name = line[7:].strip()
            if not name or name == str(archive):
                continue
            safe_relative_path(name.rstrip("/"))
            rows.append(name)
    if not rows:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ARCHIVE_EMPTY")
    if len(rows) > MAX_EXPANDED_FILES:
        raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANSION_FILE_COUNT_LIMIT")
    return rows


def tree_rows(root: Path) -> list[dict]:
    root = Path(root).resolve(strict=True)
    rows = []
    total = 0
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        base_path = Path(base)
        for directory in list(dirs):
            p = base_path / directory
            if p.is_symlink() or not p.resolve().is_relative_to(root):
                raise AssetLoaderError("EXTERNALIZED_ASSET_TREE_SYMLINK_OR_ESCAPE")
        for filename in sorted(files):
            p = base_path / filename
            if p.is_symlink() or not p.is_file() or not p.resolve().is_relative_to(root):
                raise AssetLoaderError("EXTERNALIZED_ASSET_TREE_NONREGULAR_ENTRY")
            size = p.stat().st_size
            total += size
            if total > MAX_EXPANDED_BYTES:
                raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_BYTES_LIMIT")
            rows.append({
                "path": p.relative_to(root).as_posix(),
                "bytes": size,
                "sha256": sha256_file(p),
            })
            if len(rows) > MAX_EXPANDED_FILES:
                raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANSION_FILE_COUNT_LIMIT")
    return sorted(rows, key=lambda item: item["path"].encode("utf-8"))


def extract_asset(asset_id: str, cache_root: Path, *, registry_path: Path | None = None) -> dict:
    registry = load_registry(registry_path)
    row = next((item for item in registry["assets"] if item["id"] == asset_id), None)
    if row is None:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ID_NOT_REGISTERED")
    archive_evidence = fetch_asset(asset_id, cache_root, registry_path=registry_path)
    archive = Path(archive_evidence["path"])
    listing = _list_archive_paths(archive)
    # Avoid path traversal and link entries before extraction.
    executable = shutil.which("7z") or shutil.which("7zz")
    info = subprocess.run(
        [executable, "l", "-slt", str(archive)],
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=120, check=False,
    )
    if info.returncode:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ARCHIVE_METADATA_FAILED")
    if any("Symbolic Link" in line or "Hard Link" in line for line in info.stdout.splitlines()):
        raise AssetLoaderError("EXTERNALIZED_ASSET_LINK_ENTRIES_FORBIDDEN")
    test = subprocess.run([executable, "t", "-bd", str(archive)], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=600, check=False)
    if test.returncode:
        raise AssetLoaderError("EXTERNALIZED_ASSET_ARCHIVE_CRC_FAILED")
    expanded_root = Path(cache_root).resolve() / "expanded" / asset_id
    if expanded_root.exists() or expanded_root.is_symlink():
        if expanded_root.is_symlink() or not expanded_root.is_dir():
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_CACHE_TARGET_UNSAFE")
        rows = tree_rows(expanded_root)
        byte_count = sum(item["bytes"] for item in rows)
        tree_sha = hashlib.sha256(canonical_json(rows)).hexdigest()
        if byte_count == row["expanded_bytes"] and len(rows) == row["expanded_file_count"] and tree_sha == row["expanded_tree_sha256"]:
            return {"status": "PASS_EXPANDED_CACHE_HASH_VERIFIED", "asset_id": asset_id, "path": str(expanded_root), "bytes": byte_count, "file_count": len(rows), "tree_sha256": tree_sha}
        raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_CACHE_IDENTITY_MISMATCH")
    expanded_root.parent.mkdir(parents=True, exist_ok=True)
    temp_root = Path(tempfile.mkdtemp(prefix=".louksnapg2-extract-", dir=str(expanded_root.parent)))
    try:
        out = temp_root / "content"
        out.mkdir()
        extraction = subprocess.run(
            [executable, "x", "-y", "-bd", "-o" + str(out), str(archive)],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900, check=False,
        )
        if extraction.returncode:
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXTRACTION_FAILED")
        rows = tree_rows(out)
        byte_count = sum(item["bytes"] for item in rows)
        tree_sha = hashlib.sha256(canonical_json(rows)).hexdigest()
        if byte_count != row["expanded_bytes"] or len(rows) != row["expanded_file_count"] or tree_sha != row["expanded_tree_sha256"]:
            raise AssetLoaderError("EXTERNALIZED_ASSET_EXPANDED_TREE_HASH_MISMATCH")
        os.replace(out, expanded_root)
        return {
            "status": "PASS_EXPLICIT_EXTRACTION_TREE_HASH_VERIFIED",
            "asset_id": asset_id,
            "path": str(expanded_root),
            "bytes": byte_count,
            "file_count": len(rows),
            "tree_sha256": tree_sha,
            "source_archive_sha256": archive_evidence["sha256"],
        }
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=Path(__file__).resolve().parent / "externalized_assets.json")
    parser.add_argument("--cache-root", type=Path, default=Path.home() / ".cache" / "louksnapg2" / "externalized")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list")
    fetch = sub.add_parser("fetch")
    fetch.add_argument("--id", required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--id", required=True)
    extract = sub.add_parser("extract")
    extract.add_argument("--id", required=True)
    args = parser.parse_args(argv)
    try:
        registry = load_registry(args.registry)
        if args.command == "list":
            result = {"schema": "LOUKSNAPG2_EXTERNALIZED_ASSET_STATUS/1.0", "source_commit": registry["source_commit"], "assets": [{"id": a["id"], "version": a["version"], "bytes": a["bytes"], "sha256": a["sha256"], "activation_status": a["activation_status"]} for a in registry["assets"]], "automatic_download_on_startup": False}
        elif args.command == "fetch":
            result = fetch_asset(args.id, args.cache_root, registry_path=args.registry)
        elif args.command == "verify":
            result = fetch_asset(args.id, args.cache_root, registry_path=args.registry)
            result["status"] = "PASS_EXTERNALIZED_SOURCE_INTEGRITY"
        else:
            result = extract_asset(args.id, args.cache_root, registry_path=args.registry)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)[:240]}, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
