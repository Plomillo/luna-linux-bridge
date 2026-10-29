#!/usr/bin/env python3
"""Explicit, source-pinned materializer for externalized LOUKSNAPG2 model payloads.

Weights are not embedded in the candidate and are never downloaded at import/startup.
An operator or CI job must explicitly invoke the materialize subcommand. Every payload
is streamed to a temporary file and activated only after its byte count and SHA-256 match.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import urllib.parse
import urllib.request
from pathlib import Path

from louksnapg2_engine import EXPECTED_MODELS

SCHEMA = "LOUKSNAPG2_EXTERNALIZED_MODEL_REGISTRY/1.0"
MAX_MODEL_BYTES = 300_000_000
BLOCK_BYTES = 1024 * 1024
ALLOWED_REDIRECT_SUFFIXES = (".huggingface.co", ".hf.co")


class ModelMaterializationError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK_BYTES), b""):
            digest.update(block)
    return digest.hexdigest()


def model_registry() -> dict:
    rows = []
    for model_id, spec in EXPECTED_MODELS.items():
        row = {
            "id": model_id,
            **spec,
        }
        if (
            not isinstance(row.get("path"), str)
            or not isinstance(row.get("repo"), str)
            or not isinstance(row.get("revision"), str)
            or not isinstance(row.get("file"), str)
            or not isinstance(row.get("bytes"), int)
            or not 1 <= row["bytes"] <= MAX_MODEL_BYTES
            or not isinstance(row.get("sha256"), str)
            or len(row["sha256"]) != 64
            or any(ch not in "0123456789abcdef" for ch in row["sha256"])
            or len(row["revision"]) != 40
            or any(ch not in "0123456789abcdef" for ch in row["revision"])
        ):
            raise ModelMaterializationError("MODEL_REGISTRY_ROW_INVALID:" + model_id)
        if not row["path"].startswith("models/") or ".." in Path(row["path"]).parts or Path(row["path"]).is_absolute():
            raise ModelMaterializationError("MODEL_REGISTRY_PATH_INVALID:" + model_id)
        rows.append(row)
    if len(rows) != 2 or {row["id"] for row in rows} != {"QWEN3_0_6B_Q2_K", "WHISPER_TINY_Q5_1"}:
        raise ModelMaterializationError("MODEL_REGISTRY_SET_MISMATCH")
    return {
        "schema": SCHEMA,
        "activation_policy": "EXPLICIT_MATERIALIZE_ONLY",
        "network_policy": "NO_FETCH_AT_RUNTIME_STARTUP",
        "maximum_model_bytes": MAX_MODEL_BYTES,
        "models": rows,
    }


def source_url(row: dict) -> str:
    repo = row["repo"]
    revision = row["revision"]
    filename = row["file"]
    if (
        not repo
        or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_/." for ch in repo)
        or "/" not in repo
        or len(revision) != 40
        or any(ch not in "0123456789abcdef" for ch in revision)
        or Path(filename).name != filename
    ):
        raise ModelMaterializationError("MODEL_SOURCE_BINDING_INVALID:" + row["id"])
    return f"https://huggingface.co/{repo}/resolve/{revision}/{urllib.parse.quote(filename, safe='')}"


def _safe_target(root: Path, relative: str) -> Path:
    rel = Path(relative)
    if rel.is_absolute() or ".." in rel.parts or rel.as_posix() != relative:
        raise ModelMaterializationError("MODEL_TARGET_PATH_INVALID")
    root = root.resolve(strict=True)
    models_dir = root / "models"
    if models_dir.is_symlink():
        raise ModelMaterializationError("MODEL_DIRECTORY_SYMLINK_FORBIDDEN")
    models_dir.mkdir(mode=0o755, exist_ok=True)
    if models_dir.resolve(strict=True).parent != root:
        raise ModelMaterializationError("MODEL_DIRECTORY_ESCAPE")
    target = root.joinpath(*rel.parts)
    if target.is_symlink():
        raise ModelMaterializationError("MODEL_TARGET_SYMLINK_FORBIDDEN:" + relative)
    if not target.parent.resolve(strict=True).is_relative_to(root):
        raise ModelMaterializationError("MODEL_TARGET_ESCAPE:" + relative)
    return target


def _download(row: dict, target: Path, *, timeout_seconds: int = 300) -> dict:
    expected_bytes = row["bytes"]
    if expected_bytes > MAX_MODEL_BYTES:
        raise ModelMaterializationError("MODEL_DOWNLOAD_SIZE_CAP_EXCEEDED:" + row["id"])
    url = source_url(row)
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "huggingface.co":
        raise ModelMaterializationError("MODEL_SOURCE_HOST_FORBIDDEN:" + row["id"])

    fd, temp_name = tempfile.mkstemp(prefix=".louksnapg2-model-", dir=str(target.parent))
    digest = hashlib.sha256()
    count = 0
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "LOUKSNAPG2-ExternalizedModelLoader/1.0",
                "Accept-Encoding": "identity",
                "Cache-Control": "no-cache",
            },
            method="GET",
        )
        with os.fdopen(fd, "wb") as output:
            try:
                response = urllib.request.urlopen(request, timeout=timeout_seconds)
            except Exception as exc:
                raise ModelMaterializationError("MODEL_SOURCE_FETCH_FAILED:" + row["id"] + ":" + type(exc).__name__) from exc
            with response:
                final = urllib.parse.urlparse(response.geturl())
                host = final.hostname or ""
                if final.scheme != "https" or not (
                    host == "huggingface.co"
                    or any(host.endswith(suffix) for suffix in ALLOWED_REDIRECT_SUFFIXES)
                ):
                    raise ModelMaterializationError("MODEL_REDIRECT_HOST_FORBIDDEN:" + row["id"])
                content_length = response.headers.get("Content-Length")
                if content_length is not None:
                    try:
                        if int(content_length) != expected_bytes:
                            raise ModelMaterializationError("MODEL_CONTENT_LENGTH_MISMATCH:" + row["id"])
                    except ValueError as exc:
                        raise ModelMaterializationError("MODEL_CONTENT_LENGTH_INVALID:" + row["id"]) from exc
                while True:
                    block = response.read(BLOCK_BYTES)
                    if not block:
                        break
                    count += len(block)
                    if count > expected_bytes or count > MAX_MODEL_BYTES:
                        raise ModelMaterializationError("MODEL_DOWNLOAD_EXCEEDS_PINNED_SIZE:" + row["id"])
                    digest.update(block)
                    output.write(block)
                output.flush()
                os.fsync(output.fileno())
        observed_hash = digest.hexdigest()
        if count != expected_bytes:
            raise ModelMaterializationError("MODEL_SIZE_MISMATCH:" + row["id"])
        if observed_hash != row["sha256"]:
            raise ModelMaterializationError("MODEL_SHA256_MISMATCH:" + row["id"])
        if target.exists() or target.is_symlink():
            raise ModelMaterializationError("MODEL_TARGET_APPEARED_DURING_FETCH:" + row["id"])
        os.chmod(temp_name, 0o644)
        os.replace(temp_name, target)
        return {
            "model_id": row["id"],
            "status": "PASS_DOWNLOADED_HASH_VERIFIED",
            "path": row["path"],
            "repo": row["repo"],
            "revision": row["revision"],
            "bytes": count,
            "sha256": observed_hash,
        }
    finally:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass


def materialize_models(runtime_root: Path) -> dict:
    root = Path(runtime_root).resolve(strict=True)
    registry = model_registry()
    evidence = []
    for row in registry["models"]:
        target = _safe_target(root, row["path"])
        if target.exists():
            if not target.is_file() or target.is_symlink():
                raise ModelMaterializationError("MODEL_CACHE_TARGET_UNSAFE:" + row["id"])
            size = target.stat().st_size
            digest = sha256_file(target)
            if size == row["bytes"] and digest == row["sha256"]:
                evidence.append({
                    "model_id": row["id"], "status": "PASS_CACHE_HASH_VERIFIED",
                    "path": row["path"], "bytes": size, "sha256": digest,
                    "repo": row["repo"], "revision": row["revision"],
                })
                continue
            # Never replace a pre-existing file whose identity does not match the pin.
            raise ModelMaterializationError("MODEL_CACHE_IDENTITY_MISMATCH:" + row["id"])
        evidence.append(_download(row, target))
    return {
        "schema": "LOUKSNAPG2_MODEL_MATERIALIZATION_EVIDENCE/1.0",
        "status": "PASS" if all(row["status"].startswith("PASS_") for row in evidence) else "FAIL",
        "runtime_root": str(root),
        "network_access": "EXPLICIT_COMMAND_ONLY",
        "models": evidence,
        "certification": "NOT_GRANTED_BY_MATERIALIZATION",
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("show-registry")
    sub.add_parser("materialize")
    args = parser.parse_args(argv)
    try:
        if args.command == "show-registry":
            result = model_registry()
        else:
            result = materialize_models(args.runtime_root)
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as exc:
        print(json.dumps({
            "schema": "LOUKSNAPG2_MODEL_MATERIALIZATION_EVIDENCE/1.0",
            "status": "FAIL_CLOSED",
            "reason": type(exc).__name__ + ":" + str(exc)[:300],
            "certification": "NOT_GRANTED",
        }, ensure_ascii=False, sort_keys=True))
        return 4


if __name__ == "__main__":
    raise SystemExit(main())
