#!/usr/bin/env python3
"""Provision hash-pinned whisper.cpp tiny multilingual runtime assets.

The auxiliary ASR model is separate from and never replaces the original Whisper
large-v3-turbo weights. The binary is built from one immutable upstream commit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

MODEL_URL = "https://huggingface.co/ggerganov/whisper.cpp/resolve/80da2d8bfee42b0e836fc3a9890373e5defc00a6/ggml-tiny.bin"
MODEL_BYTES = 77_691_713
MODEL_SHA256 = "be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21"
SOURCE_REPOSITORY = "https://github.com/ggml-org/whisper.cpp.git"
SOURCE_COMMIT = "d1be6fde11ac6e0407606b4e42fe72d34add8037"
SCHEMA = "LOUKSNAPG2_WHISPER_AUXILIARY_ASSETS/1.0"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run(command: list[str], *, cwd: Path | None = None, timeout: int = 2400) -> subprocess.CompletedProcess:
    try:
        result = subprocess.run(command, cwd=cwd, capture_output=True, text=True, timeout=timeout, check=False)
    except FileNotFoundError as exc:
        raise RuntimeError("WHISPER_BUILD_TOOL_NOT_FOUND:" + command[0]) from exc
    if result.returncode:
        raise RuntimeError(
            "WHISPER_BUILD_COMMAND_FAILED:" + " ".join(command[:5])
            + ":" + (result.stderr or result.stdout)[-2000:]
        )
    return result


def fetch_model(destination: Path) -> dict:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.is_symlink():
        raise RuntimeError("WHISPER_MODEL_SYMLINK_REJECTED")
    if destination.is_file():
        if destination.stat().st_size == MODEL_BYTES and sha256_file(destination) == MODEL_SHA256:
            return {"status": "PASS_REUSED_VERIFIED_MODEL", "bytes": MODEL_BYTES, "sha256": MODEL_SHA256}
        raise RuntimeError("WHISPER_MODEL_EXISTING_FILE_IDENTITY_MISMATCH")
    temporary = destination.with_name(destination.name + ".download")
    if temporary.exists() or temporary.is_symlink():
        if temporary.is_symlink() or not temporary.is_file():
            raise RuntimeError("WHISPER_MODEL_TEMPORARY_PATH_UNSAFE")
        temporary.unlink()
    request = urllib.request.Request(MODEL_URL, headers={"User-Agent": "LouksnapG2-AuxiliaryBuilder/1.0"})
    digest = hashlib.sha256()
    count = 0
    try:
        with urllib.request.urlopen(request, timeout=90) as response, temporary.open("xb") as output:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                count += len(chunk)
                if count > MODEL_BYTES:
                    raise RuntimeError("WHISPER_MODEL_DOWNLOAD_EXCEEDS_PINNED_SIZE")
                digest.update(chunk)
                output.write(chunk)
        if count != MODEL_BYTES or digest.hexdigest() != MODEL_SHA256:
            raise RuntimeError("WHISPER_MODEL_DOWNLOAD_IDENTITY_MISMATCH")
        os.replace(temporary, destination)
    finally:
        if temporary.exists():
            temporary.unlink()
    return {"status": "PASS_DOWNLOADED_HASH_VERIFIED_MODEL", "bytes": count, "sha256": digest.hexdigest()}


def build_binary(runtime: Path, work: Path) -> dict:
    target = runtime / "auxiliary_bin" / "linux-x86_64" / "whisper-cli"
    if target.is_symlink():
        raise RuntimeError("WHISPER_BINARY_SYMLINK_REJECTED")
    if target.is_file():
        run([str(target), "--help"], timeout=30)
        return {"status": "PASS_REUSED_BUILT_BINARY", "path": target.relative_to(runtime).as_posix(),
                "bytes": target.stat().st_size, "sha256": sha256_file(target)}
    if work.exists() or work.is_symlink():
        if work.is_symlink() or not work.is_dir():
            raise RuntimeError("WHISPER_BUILD_WORKDIR_UNSAFE")
        shutil.rmtree(work)
    work.parent.mkdir(parents=True, exist_ok=True)
    clone = work / "source"
    build = work / "build"
    run(["git", "clone", "--filter=blob:none", "--no-checkout", SOURCE_REPOSITORY, str(clone)], timeout=600)
    run(["git", "fetch", "--depth=1", "origin", SOURCE_COMMIT], cwd=clone, timeout=600)
    run(["git", "checkout", "--detach", SOURCE_COMMIT], cwd=clone, timeout=120)
    observed = run(["git", "rev-parse", "HEAD"], cwd=clone, timeout=30).stdout.strip()
    if observed != SOURCE_COMMIT:
        raise RuntimeError("WHISPER_CPP_SOURCE_COMMIT_MISMATCH")
    run([
        "cmake", "-S", str(clone), "-B", str(build),
        "-DCMAKE_BUILD_TYPE=Release",
        "-DBUILD_SHARED_LIBS=OFF",
        "-DWHISPER_BUILD_TESTS=OFF",
        "-DWHISPER_BUILD_EXAMPLES=ON",
        "-DWHISPER_BUILD_SERVER=OFF",
        "-DGGML_NATIVE=OFF",
    ], timeout=600)
    run(["cmake", "--build", str(build), "--parallel", "1", "--target", "whisper-cli"], timeout=2400)
    candidates = [
        build / "bin" / "whisper-cli",
        build / "bin" / "whisper-cli.exe",
    ]
    source_binary = next((p for p in candidates if p.is_file() and not p.is_symlink()), None)
    if source_binary is None:
        matches = [p for p in build.rglob("whisper-cli") if p.is_file() and not p.is_symlink()]
        if len(matches) != 1:
            raise RuntimeError("WHISPER_CLI_BUILD_OUTPUT_NOT_UNIQUE")
        source_binary = matches[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source_binary, target)
    target.chmod(0o755)
    run([str(target), "--help"], timeout=30)
    return {"status": "PASS_BUILT_FROM_PINNED_SOURCE", "path": target.relative_to(runtime).as_posix(),
            "source_commit": SOURCE_COMMIT, "bytes": target.stat().st_size, "sha256": sha256_file(target)}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path)
    args = parser.parse_args(argv)
    root = args.runtime_root.resolve(strict=True)
    runtime = root if root.name == "LOUKSNAPG2_RUNTIME" else root / "LOUKSNAPG2_RUNTIME"
    if runtime.is_symlink() or not runtime.is_dir():
        raise SystemExit("LOUKSNAPG2_RUNTIME_DIRECTORY_MISSING_OR_UNSAFE")
    work = args.work_dir.resolve() if args.work_dir else Path(tempfile.gettempdir()) / "louksnapg2-whisper-build"
    model_path = runtime / "auxiliary_models" / "ggml-tiny.bin"
    try:
        model = fetch_model(model_path)
        binary = build_binary(runtime, work)
        manifest = {
            "schema": SCHEMA,
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z"),
            "scope": "AUXILIARY_ASR_FALLBACK; ORIGINAL_WHISPER_LARGE_V3_TURBO_WEIGHTS_UNCHANGED",
            "source": {
                "model_repository": "ggerganov/whisper.cpp",
                "model_revision": "80da2d8bfee42b0e836fc3a9890373e5defc00a6",
                "model_url": MODEL_URL,
                "model_license": "MIT",
                "model_bytes": model["bytes"],
                "model_sha256": model["sha256"],
                "runtime_repository": SOURCE_REPOSITORY,
                "runtime_commit": SOURCE_COMMIT,
            },
            "model": model,
            "binary": binary,
            "host": "linux-x86_64",
            "thread_budget": 1,
            "semantic_equivalence_to_whisper_large_v3_turbo": "NOT_ESTABLISHED",
            "certification": "NOT_GRANTED",
        }
        manifest_path = runtime / "WHISPER_AUXILIARY_ASSETS.json"
        if manifest_path.is_symlink():
            raise RuntimeError("WHISPER_AUXILIARY_MANIFEST_SYMLINK_REJECTED")
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
        print(json.dumps({"status": "PASS_WHISPER_AUXILIARY_PROVISIONED", "model": model, "binary": binary,
                          "manifest_sha256": sha256_file(manifest_path)}, sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "reason": type(exc).__name__ + ":" + str(exc)[:2000]}))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
