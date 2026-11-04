#!/usr/bin/env python3
"""Build and evaluate a full-rank Whisper quantization candidate under hard CPU/RAM cgroups.

This is an isolated experiment. It never edits the active Cajita runtime, source
weights, model manifest, LOUKSNAPG2 bundle, or certification state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path
from typing import Any

# Official OpenAI checkpoint; no hosted model-hub API/account is used.
SOURCE_REPO = "openai/whisper-large-v3-turbo"
SOURCE_REVISION = "OPENAI_OFFICIAL_AZURE_RELEASE"
SOURCE_MODEL_URL = "https://openaipublic.azureedge.net/main/whisper/models/aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a/large-v3-turbo.pt"
SOURCE_MODEL_SHA256 = "aff26ae408abcba5fbf8813c21e62b0941638c5f6eebfb145be0c9839262a19a"
DATASET_REPO = "ggml-org/whisper.cpp"
DATASET_REVISION = "482279b8a18855ba741d7b88c30fcb3874691f59"
REAL_AUDIO_ID = "jfk"
REAL_WER_MAX = 0.25
JFK_TRANSCRIPT = "And so my fellow Americans, ask not what your country can do for you, ask what you can do for your country."

REPAIR_RAM_BYTES = 3 * 1024**3
CANDIDATE_RAM_BYTES = 1 * 1024**3
GLOBAL_RELEASE_MAX_BYTES = 490_000_000
BASELINE_RELEASE_BYTES = 371_977_806
BASELINE_WHISPER_WEIGHT_BYTES = 10_399_882
PACKAGE_METADATA_RESERVE_BYTES = 1_000_000
BASELINE_EVIDENCE_COMMIT = "7a73c524ecaef709fd9e6fdacb8edefb74482e0a"

WHISPER_CPP_REVISION = "482279b8a18855ba741d7b88c30fcb3874691f59"
OPENAI_WHISPER_REVISION = "86098128c0b4f24f0e2aa2994de830614b474227"
CONVERTER_SHA256 = "9cc282dfcd9a24da03ffa1b4123b5508ee935e19e369c33520b1a73f89440094"
QUANTIZATIONS = ("q4_0", "q5_0")




def stage_shared_libraries(build_root: Path, destination: Path) -> list[dict]:
    """Stage the complete pinned whisper.cpp shared-library closure as regular files."""
    build_root = Path(build_root).resolve(strict=True)
    destination = Path(destination).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    staged: dict[str, dict] = {}
    for source in sorted(build_root.rglob("*")):
        if not source.is_file() or ".so" not in source.name:
            continue
        resolved = source.resolve(strict=True)
        if not resolved.is_relative_to(build_root) or not resolved.is_file():
            raise RuntimeError("WHISPER_SHARED_LIBRARY_SOURCE_ESCAPES_BUILD_TREE:" + str(source))
        name = source.name
        target = destination / name
        digest = sha256_file(resolved)
        if target.exists():
            if not target.is_file() or sha256_file(target) != digest:
                raise RuntimeError("WHISPER_SHARED_LIBRARY_NAME_COLLISION:" + name)
        else:
            shutil.copy2(resolved, target)
        staged[name] = {
            "name": name,
            "path": "toolchain/lib/" + name,
            "bytes": target.stat().st_size,
            "sha256": sha256_file(target),
        }
    if "libwhisper.so.1" not in staged:
        raise RuntimeError("WHISPER_SHARED_LIBRARY_SONAME_MISSING:libwhisper.so.1")
    return [staged[name] for name in sorted(staged)]


def whisper_runtime_env(base_env: dict, library_dir: Path) -> dict:
    env = dict(base_env)
    current = env.get("LD_LIBRARY_PATH", "")
    env["LD_LIBRARY_PATH"] = str(Path(library_dir).resolve(strict=True)) + (os.pathsep + current if current else "")
    return env


def verify_whisper_runtime_dependencies(cli: Path, library_dir: Path) -> dict:
    cli = Path(cli).resolve(strict=True)
    library_dir = Path(library_dir).resolve(strict=True)
    env = whisper_runtime_env(os.environ, library_dir)
    checked = subprocess.run(
        ["ldd", str(cli)], capture_output=True, text=True, errors="replace",
        timeout=30, check=False, env=env,
    )
    output = checked.stdout + checked.stderr
    missing = [line.strip() for line in output.splitlines() if "not found" in line]
    if checked.returncode != 0 or missing:
        raise RuntimeError("WHISPER_NATIVE_DEPENDENCY_RESOLUTION_FAILED:" + json.dumps({
            "exit_code": checked.returncode, "missing": missing, "output_tail": output[-5000:]
        }, ensure_ascii=False))
    if "libwhisper.so.1" not in output or str(library_dir) not in output:
        raise RuntimeError("WHISPER_NATIVE_DEPENDENCY_NOT_RESOLVED_FROM_PINNED_BUNDLE:" + output[-3000:])
    return {
        "status": "PASS_ALL_NATIVE_SHARED_LIBRARIES_RESOLVED",
        "cli_sha256": sha256_file(cli),
        "library_dir": str(library_dir),
        "ldd_output": output[-8000:],
        "missing_dependencies": [],
    }


def verify_staged_shared_libraries(artifact_root: Path, manifest: dict) -> list[dict]:
    artifact_root = Path(artifact_root).resolve(strict=True)
    rows = manifest.get("conversion", {}).get("runtime_libraries")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("WHISPER_RUNTIME_LIBRARY_MANIFEST_MISSING")
    verified = []
    for row in rows:
        if not isinstance(row, dict):
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_ROW_INVALID")
        rel = row.get("path")
        if not isinstance(rel, str) or not rel or Path(rel).is_absolute() or ".." in Path(rel).parts:
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_PATH_INVALID")
        path = (artifact_root / rel).resolve(strict=True)
        if not path.is_relative_to(artifact_root) or path.is_symlink() or not path.is_file():
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_PATH_UNSAFE:" + rel)
        if path.stat().st_size != int(row.get("bytes", -1)) or sha256_file(path) != row.get("sha256"):
            raise RuntimeError("WHISPER_RUNTIME_LIBRARY_IDENTITY_MISMATCH:" + rel)
        verified.append({"path": rel, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    if not any(Path(row["path"]).name == "libwhisper.so.1" for row in verified):
        raise RuntimeError("WHISPER_RUNTIME_LIBRARY_SONAME_NOT_BUNDLED")
    return verified

def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def json_write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".building")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def cgroup_budget(expected_bytes: int) -> dict:
    root = Path("/sys/fs/cgroup")
    required = ("memory.max", "memory.peak", "memory.swap.max", "cpu.max", "memory.events")
    missing = [name for name in required if not (root / name).is_file()]
    if missing:
        raise RuntimeError("CGROUP_V2_CONTROL_UNAVAILABLE:" + ",".join(missing))
    memory_max = (root / "memory.max").read_text(encoding="ascii").strip()
    if memory_max != str(expected_bytes):
        raise RuntimeError("CGROUP_MEMORY_BUDGET_MISMATCH:" + memory_max + ":" + str(expected_bytes))
    swap_max = (root / "memory.swap.max").read_text(encoding="ascii").strip()
    if swap_max != "0":
        raise RuntimeError("CGROUP_SWAP_MUST_BE_DISABLED:" + swap_max)
    fields = (root / "cpu.max").read_text(encoding="ascii").split()
    if len(fields) != 2:
        raise RuntimeError("CGROUP_CPU_MAX_FIELDS_INVALID")
    quota, period = map(int, fields)
    if quota <= 0 or period <= 0 or quota != period:
        raise RuntimeError("CGROUP_CPU_MUST_EQUAL_ONE_CORE:" + str(fields))
    events = {}
    for line in (root / "memory.events").read_text(encoding="ascii").splitlines():
        key, value = line.split()
        events[key] = int(value)
    if events.get("oom", 0) or events.get("oom_kill", 0):
        raise RuntimeError("CGROUP_OOM_EVENT_PRESENT:" + json.dumps(events, sort_keys=True))
    return {
        "status": "PASS_EXACT_CGROUP_V2_LIMITS",
        "memory_limit_bytes": expected_bytes,
        "memory_limit_gib": expected_bytes / 1024**3,
        "memory_limit_mechanism": "DOCKER_CGROUP_V2_MEMORY_MAX",
        "swap_limit_bytes": int(swap_max),
        "swap_policy": "DISABLED",
        "cpu_quota": quota,
        "cpu_period": period,
        "cpu_limit_cores": quota / period,
        "cpu_limit_mechanism": "DOCKER_CGROUP_V2_CPU_MAX",
        "initial_memory_events": events,
    }


def cgroup_snapshot() -> dict:
    root = Path("/sys/fs/cgroup")
    try:
        current = int((root / "memory.current").read_text(encoding="ascii").strip())
        peak = int((root / "memory.peak").read_text(encoding="ascii").strip())
        events = {}
        for line in (root / "memory.events").read_text(encoding="ascii").splitlines():
            key, value = line.split()
            events[key] = int(value)
        return {"memory_current_bytes": current, "memory_peak_bytes": peak, "memory_events": events}
    except Exception as exc:
        return {"measurement_error": type(exc).__name__ + ":" + str(exc)[:160]}


def child_peak_rss_bytes() -> int:
    value = int(resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss)
    return value * 1024 if sys.platform.startswith("linux") else value


def run_checked(command: list[str], *, cwd: Path, timeout: int, env: dict | None = None) -> dict:
    started = time.monotonic()
    completed = subprocess.run(
        command, cwd=str(cwd), env=env or os.environ.copy(),
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, errors="replace", timeout=timeout, check=False,
    )
    result = {
        "command": command,
        "exit_code": completed.returncode,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "output_tail": completed.stdout[-8000:],
    }
    if completed.returncode != 0:
        raise RuntimeError("SUBPROCESS_FAILED:" + json.dumps(result, ensure_ascii=False)[:5000])
    return result


def git_head(path: Path) -> str:
    result = subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=False,
    )
    if result.returncode:
        raise RuntimeError("GIT_HEAD_UNAVAILABLE:" + str(path))
    return result.stdout.strip()




def download_official_whisper_checkpoint(destination: Path) -> dict:
    """Stream the official OpenAI checkpoint and verify its published SHA-256."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".building")
    digest = hashlib.sha256()
    total = 0
    try:
        with urllib.request.urlopen(SOURCE_MODEL_URL, timeout=180) as response, temporary.open("wb") as output:
            while True:
                chunk = response.read(8 * 1024 * 1024)
                if not chunk:
                    break
                output.write(chunk)
                digest.update(chunk)
                total += len(chunk)
        observed = digest.hexdigest()
        if observed != SOURCE_MODEL_SHA256 or total <= 0:
            raise RuntimeError("OFFICIAL_OPENAI_CHECKPOINT_SHA256_MISMATCH:" + observed)
        os.replace(temporary, destination)
        return {
            "source_url": SOURCE_MODEL_URL,
            "source_model_id": SOURCE_REPO,
            "release_revision": SOURCE_REVISION,
            "sha256": observed,
            "bytes": total,
            "verification": "PASS_OFFICIAL_RELEASE_SHA256",
            "provider": "OPENAI_OFFICIAL_AZURE_BLOB",
            "hub_api_used": False,
        }
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def create_mmap_pt_converter(upstream_converter: Path, output_dir: Path) -> Path:
    """Patch pinned convert-pt-to-ggml.py to mmap the .pt checkpoint instead of reading it into RAM."""
    source = Path(upstream_converter).read_text(encoding="utf-8")
    original = (
        '    model_bytes = open(fname_inp, "rb").read()\n'
        '    with io.BytesIO(model_bytes) as fp:\n'
        '        checkpoint = torch.load(fp, map_location="cpu")'
    )
    replacement = '    checkpoint = torch.load(fname_inp, map_location="cpu", mmap=True, weights_only=True)'
    if source.count(original) != 1:
        raise RuntimeError("PINNED_PT_CONVERTER_MMAP_PATCH_ANCHOR_MISMATCH")
    source = source.replace(original, replacement)
    if "model_bytes = open(fname_inp" in source or "mmap=True, weights_only=True" not in source:
        raise RuntimeError("PT_CONVERTER_SAFE_MMAP_MODE_MISSING")
    patched = Path(output_dir) / "convert-pt-to-ggml-mmap.py"
    compile(source, str(patched), "exec")
    patched.write_text(source, encoding="utf-8")
    return patched


def read_memory_events(path: Path) -> dict:
    values = {}
    for line in Path(path).read_text(encoding="ascii").splitlines():
        key, value = line.split()
        values[key] = int(value)
    return values


def memory_event_delta(before: dict, after: dict) -> dict:
    return {key: max(0, int(after.get(key, 0)) - int(before.get(key, 0)))
            for key in set(before) | set(after)}


def make_synthetic_audio(path: Path) -> Path:
    executable = shutil.which("espeak-ng")
    if not executable:
        raise RuntimeError("ESPEAK_NG_REQUIRED_FOR_KNOWN_SPEECH_FIXTURE")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [executable, "-v", "en-us", "-s", "135", "-w", str(path), "hello world"],
        check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
        text=True, timeout=30,
    )
    with wave.open(str(path), "rb") as stream:
        if stream.getnframes() <= 0 or stream.getsampwidth() != 2 or stream.getnchannels() not in (1, 2):
            raise RuntimeError("ESPEAK_NG_FIXTURE_WAV_INVALID")
    return path


def release_projection(candidate_bytes: int) -> dict:
    projected = (
        BASELINE_RELEASE_BYTES
        - BASELINE_WHISPER_WEIGHT_BYTES
        + candidate_bytes
        + PACKAGE_METADATA_RESERVE_BYTES
    )
    return {
        "baseline_release_bytes": BASELINE_RELEASE_BYTES,
        "baseline_evidence_commit": BASELINE_EVIDENCE_COMMIT,
        "baseline_whisper_weight_bytes": BASELINE_WHISPER_WEIGHT_BYTES,
        "candidate_weight_bytes": candidate_bytes,
        "metadata_reserve_bytes": PACKAGE_METADATA_RESERVE_BYTES,
        "projected_release_bytes": projected,
        "hard_max_bytes": GLOBAL_RELEASE_MAX_BYTES,
        "projected_size_pass": projected <= GLOBAL_RELEASE_MAX_BYTES,
        "is_projection_not_final_package_measurement": True,
        "package_policy": "DO_NOT_PROMOTE_WHEN_OVER_CAP",
        "external_asset_required": projected > GLOBAL_RELEASE_MAX_BYTES,
    }


def build(args) -> int:
    budget = cgroup_budget(REPAIR_RAM_BYTES)
    out = Path(args.output_dir).resolve()
    if out.exists() and any(out.iterdir()):
        raise RuntimeError("OUTPUT_DIRECTORY_MUST_BE_EMPTY")
    out.mkdir(parents=True, exist_ok=True)
    artifact_root = out / "artifact"
    quantized_root = artifact_root / "quantized"
    toolchain_root = artifact_root / "toolchain" / "bin"
    quantized_root.mkdir(parents=True)
    toolchain_root.mkdir(parents=True)
    cpp_root = Path(args.whisper_cpp_root).resolve(strict=True)
    openai_root = Path(args.openai_whisper_root).resolve(strict=True)

    converter = cpp_root / "models" / "convert-pt-to-ggml.py"
    mel_filters = openai_root / "whisper" / "assets" / "mel_filters.npz"
    tokenizer = openai_root / "whisper" / "assets" / "multilingual.tiktoken"
    if not converter.is_file() or not mel_filters.is_file() or not tokenizer.is_file():
        raise RuntimeError("PINNED_PT_CONVERTER_OR_OPENAI_ASSETS_MISSING")
    if git_head(cpp_root) != WHISPER_CPP_REVISION:
        raise RuntimeError("WHISPER_CPP_REVISION_MISMATCH")
    if git_head(openai_root) != OPENAI_WHISPER_REVISION:
        raise RuntimeError("OPENAI_WHISPER_ASSETS_REVISION_MISMATCH")
    converter_sha = sha256_file(converter)
    streaming_converter = create_mmap_pt_converter(converter, out)
    streaming_converter_sha = sha256_file(streaming_converter)

    source_dir = out / "source-cache"
    source_dir.mkdir(parents=True, exist_ok=True)
    source_weights = source_dir / "large-v3-turbo.pt"
    source_download = download_official_whisper_checkpoint(source_weights)
    source_sha = sha256_file(source_weights)
    if source_sha != SOURCE_MODEL_SHA256:
        raise RuntimeError("PINNED_TEACHER_MODEL_SHA256_MISMATCH:" + source_sha)

    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OMP_THREAD_LIMIT": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
    })
    fp16_model = out / "ggml-model-f16.bin"
    conversion = run_checked(
        [sys.executable, str(streaming_converter), str(source_weights), str(openai_root), str(out)],
        cwd=cpp_root, timeout=3600, env=env,
    )
    if not fp16_model.is_file():
        # The pinned upstream .pt converter writes ggml-model.bin.
        expected = out / "ggml-model.bin"
        if expected.is_file():
            os.replace(expected, fp16_model)
        else:
            raise RuntimeError("FULL_PRECISION_GGML_CONVERSION_OUTPUT_MISSING")
    if fp16_model.stat().st_size <= 0:
        raise RuntimeError("FULL_PRECISION_GGML_CONVERSION_EMPTY")

    quantizer = cpp_root / "build" / "bin" / "whisper-quantize"
    cli = cpp_root / "build" / "bin" / "whisper-cli"
    if not quantizer.is_file() or not cli.is_file():
        raise RuntimeError("PINNED_WHISPER_CPP_BINARIES_MISSING")
    quantizer_sha = sha256_file(quantizer)
    cli_sha = sha256_file(cli)
    quantization_rows = []
    quantization_commands = []
    for quantization in QUANTIZATIONS:
        output = quantized_root / quantization / ("ggml-large-v3-turbo-" + quantization + ".bin")
        output.parent.mkdir(parents=True, exist_ok=True)
        row = run_checked(
            [str(quantizer), str(fp16_model), str(output), quantization],
            cwd=cpp_root, timeout=1800, env=env,
        )
        if not output.is_file() or output.stat().st_size <= 0:
            raise RuntimeError("QUANTIZED_MODEL_OUTPUT_MISSING:" + quantization)
        projection = release_projection(output.stat().st_size)
        quantization_rows.append({
            "quantization": quantization,
            "representation": "FULL_RANK_GGML_BLOCKWISE_INTEGER_QUANTIZATION",
            "relative_to_failed_method": "NO_SVD_OR_LOW_RANK_FACTOR_TRUNCATION",
            "path": str(output.relative_to(artifact_root)),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
            "global_release_projection": projection,
            "quantizer_execution": row,
            "functional_status": "PENDING_SEPARATE_1GIB_EVALUATION",
        })
        quantization_commands.append(row)

    # Preserve the exact executable and the full shared-library closure. CMake
    # emits libwhisper.so.1 under build/src (not necessarily build/bin); omitting
    # that file makes whisper-cli exit 127 before any model-quality measurement.
    for path in (cpp_root / "build" / "bin").iterdir():
        if path.is_file() and path.name == "whisper-cli":
            shutil.copy2(path, toolchain_root / path.name)
    toolchain_library_root = artifact_root / "toolchain" / "lib"
    runtime_libraries = stage_shared_libraries(cpp_root / "build", toolchain_library_root)
    if not (toolchain_root / "whisper-cli").is_file():
        raise RuntimeError("WHISPER_CLI_TOOLCHAIN_COPY_MISSING")
    runtime_dependency_check = verify_whisper_runtime_dependencies(
        toolchain_root / "whisper-cli", toolchain_library_root
    )
    fixture_source = cpp_root / "samples" / "jfk.wav"
    if fixture_source.is_symlink() or not fixture_source.is_file():
        raise RuntimeError("PINNED_JFK_AUDIO_FIXTURE_MISSING")
    fixture_destination = artifact_root / "fixtures" / "jfk.wav"
    fixture_destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(fixture_source, fixture_destination)
    fixture_record = {
        "path": "fixtures/jfk.wav",
        "bytes": fixture_destination.stat().st_size,
        "sha256": sha256_file(fixture_destination),
        "source_repository": "https://github.com/ggml-org/whisper.cpp",
        "source_revision": WHISPER_CPP_REVISION,
        "source_path": "samples/jfk.wav",
        "source_type": "PINNED_GIT_COMMIT_ASSET",
        "reference_transcript": JFK_TRANSCRIPT,
        "reference_transcript_sha256": hashlib.sha256(JFK_TRANSCRIPT.encode("utf-8")).hexdigest(),
    }
    manifest = {
        "schema": "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0",
        "created_at_utc": utc_now(),
        "candidate_status": "BUILT_AWAITING_SEPARATE_1GIB_FUNCTIONAL_EVALUATION",
        "source_model": {
            "model_id": SOURCE_REPO,
            "release_revision": SOURCE_REVISION,
            "source_url": SOURCE_MODEL_URL,
            "sha256": source_sha,
            "bytes": source_weights.stat().st_size,
            "model_type": "whisper-large-v3-turbo",
            "provider": "OPENAI_OFFICIAL_AZURE_BLOB",
            "download_record": source_download,
            "hub_api_used": False,
        },
        "conversion": {
            "whisper_cpp_repository": "https://github.com/ggml-org/whisper.cpp",
            "whisper_cpp_revision": WHISPER_CPP_REVISION,
            "openai_whisper_assets_repository": "https://github.com/openai/whisper",
            "openai_whisper_assets_revision": OPENAI_WHISPER_REVISION,
            "converter_path": "models/convert-pt-to-ggml.py",
            "converter_sha256": converter_sha,
            "streaming_converter_path": "convert-pt-to-ggml-mmap.py",
            "streaming_converter_sha256": streaming_converter_sha,
            "converter_execution_mode": "PINNED_UPSTREAM_PYTORCH_CHECKPOINT_WITH_MMAP_AND_WEIGHTS_ONLY",
            "full_transformers_model_materialization": False,
            "fp16_intermediate_bytes": fp16_model.stat().st_size,
            "fp16_intermediate_sha256": sha256_file(fp16_model),
            "conversion_execution": conversion,
            "quantizer_sha256": quantizer_sha,
            "whisper_cli_sha256": cli_sha,
            "runtime_libraries": runtime_libraries,
            "runtime_dependency_check": runtime_dependency_check,
            "quantization_commands": quantization_commands,
        },
        "resource_policy": budget,
        "build_peak_rss_bytes": child_peak_rss_bytes(),
        "build_cgroup_snapshot": cgroup_snapshot(),
        "evaluation_fixture": fixture_record,
        "quantization_candidates": quantization_rows,
        "global_release_policy": {
            "hard_max_bytes": GLOBAL_RELEASE_MAX_BYTES,
            "no_promotion_without_exact_package_measurement": True,
            "no_in_place_runtime_mutation": True,
            "externalized_asset_path_requires_separate_validation": True,
        },
        "invariants": {
            "source_teacher_mutated": False,
            "active_runtime_mutated": False,
            "current_weight_manifest_mutated": False,
            "candidate_integrated_into_louksnapg2": False,
            "automatic_promotion": False,
            "domain_certification": "NOT_GRANTED",
            "global_certification": "NOT_GRANTED",
        },
    }
    json_write(artifact_root / "fullrank_manifest.json", manifest)
    fp16_model.unlink(missing_ok=True)
    source_weights.unlink(missing_ok=True)
    shutil.rmtree(source_dir, ignore_errors=True)
    report = {
        "schema": "LOUKSNAPG_WHISPER_FULLRANK_REPAIR_BUILD_EVIDENCE/1.0",
        "status": "PASS_FULLRANK_QUANTIZED_CANDIDATES_BUILT",
        "manifest_sha256": sha256_file(artifact_root / "fullrank_manifest.json"),
        "quantization_candidates": quantization_rows,
        "resource_policy": budget,
        "build_peak_rss_bytes": child_peak_rss_bytes(),
        "build_cgroup_snapshot": cgroup_snapshot(),
        "promotion_performed": False,
        "candidate_integration": "NOT_PERFORMED",
        "certification": "NOT_GRANTED",
    }
    json_write(Path(args.report), report)
    return 0


def resolve_artifact_root(path: Path) -> Path:
    """Locate the single manifest in a bounded GitHub Actions artifact extraction tree."""
    root = Path(path).resolve(strict=True)
    if root.is_symlink() or not root.is_dir():
        raise RuntimeError("WHISPER_ARTIFACT_ROOT_INVALID")
    matches = []
    for base, dirs, files in os.walk(root, topdown=True, followlinks=False):
        directory = Path(base)
        depth = len(directory.relative_to(root).parts)
        dirs[:] = sorted(
            name for name in dirs
            if depth < 6 and not (directory / name).is_symlink()
        )
        if "fullrank_manifest.json" in files:
            candidate = directory / "fullrank_manifest.json"
            if candidate.is_symlink() or not candidate.is_file():
                raise RuntimeError("WHISPER_FULLRANK_MANIFEST_UNSAFE")
            matches.append(directory.resolve(strict=True))
            if len(matches) > 1:
                raise RuntimeError("WHISPER_ARTIFACT_ROOT_AMBIGUOUS")
    if not matches:
        raise FileNotFoundError("WHISPER_FULLRANK_MANIFEST_NOT_FOUND:" + str(root))
    return matches[0]


def prepare_fixtures(args) -> int:
    """Prepare synthetic and source-pinned JFK fixtures without external datasets or model hubs."""
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    fixtures_dir = work / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    synthetic = make_synthetic_audio(fixtures_dir / "synthetic-hello-world.wav")

    artifact_root = Path(args.artifact_root).resolve(strict=True)
    manifest = json.loads((artifact_root / "fullrank_manifest.json").read_text(encoding="utf-8"))
    expected = manifest.get("evaluation_fixture", {})
    if expected.get("source_revision") != WHISPER_CPP_REVISION or expected.get("source_path") != "samples/jfk.wav":
        raise RuntimeError("JFK_FIXTURE_MANIFEST_IDENTITY_MISMATCH")
    if args.real_source_revision != WHISPER_CPP_REVISION:
        raise RuntimeError("JFK_FIXTURE_SOURCE_REVISION_MISMATCH")
    source_audio = Path(args.real_audio)
    if source_audio.is_symlink() or not source_audio.is_file():
        raise RuntimeError("PINNED_JFK_AUDIO_FIXTURE_MISSING_OR_UNSAFE")
    real_audio = source_audio.resolve(strict=True)
    expected_audio = (artifact_root / str(expected.get("path", ""))).resolve(strict=True)
    if real_audio != expected_audio:
        raise RuntimeError("JFK_FIXTURE_PATH_NOT_BOUND_TO_CANDIDATE_MANIFEST")
    if real_audio.stat().st_size != int(expected.get("bytes", -1)) or sha256_file(real_audio) != expected.get("sha256"):
        raise RuntimeError("JFK_FIXTURE_HASH_NOT_BOUND_TO_CANDIDATE_MANIFEST")
    if real_audio.suffix.lower() != ".wav" or real_audio.stat().st_size <= 0:
        raise RuntimeError("PINNED_JFK_AUDIO_FIXTURE_INVALID")
    with wave.open(str(real_audio), "rb") as stream:
        if stream.getnframes() <= 0 or stream.getsampwidth() != 2 or stream.getframerate() != 16000:
            raise RuntimeError("PINNED_JFK_AUDIO_FIXTURE_WAVE_FORMAT_INVALID")
    transcript = args.real_transcript.strip()
    if not transcript or hashlib.sha256(transcript.encode("utf-8")).hexdigest() != expected.get("reference_transcript_sha256"):
        raise RuntimeError("JFK_REFERENCE_TRANSCRIPT_NOT_BOUND_TO_CANDIDATE_MANIFEST")
    fixture_manifest = {
        "schema": "LOUKSNAPG_WHISPER_FULLRANK_PREPARED_FIXTURES/1.0",
        "synthetic_audio": {
            "path": str(synthetic.resolve()), "bytes": synthetic.stat().st_size,
            "sha256": sha256_file(synthetic),
        },
        "real_audio": {
            "path": str(real_audio), "bytes": real_audio.stat().st_size,
            "sha256": sha256_file(real_audio),
        },
        "real_transcript": transcript,
        "real_transcript_sha256": hashlib.sha256(transcript.encode("utf-8")).hexdigest(),
        "dataset_fixture": {
            "source_repository": "https://github.com/ggml-org/whisper.cpp",
            "source_revision": WHISPER_CPP_REVISION,
            "source_path": "samples/jfk.wav",
            "source_type": "PINNED_GIT_COMMIT_ASSET",
            "provider_api_used": False,
        },
    }
    json_write(Path(args.report), fixture_manifest)
    print(json.dumps({
        "status": "PASS_FIXTURES_PREPARED_OFFLINE",
        "synthetic_audio_sha256": fixture_manifest["synthetic_audio"]["sha256"],
        "real_audio_sha256": fixture_manifest["real_audio"]["sha256"],
        "real_transcript_sha256": fixture_manifest["real_transcript_sha256"],
        "source_revision": WHISPER_CPP_REVISION,
        "provider_api_used": False,
        "report": str(Path(args.report).resolve()),
    }, ensure_ascii=False, sort_keys=True))
    return 0

def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalized_words(reference), normalized_words(hypothesis)
    if not ref:
        raise ValueError("WER_REFERENCE_EMPTY")
    previous = list(range(len(hyp) + 1))
    for i, reference_word in enumerate(ref, 1):
        current = [i]
        for j, hypothesis_word in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                previous[j - 1] + (reference_word != hypothesis_word)))
        previous = current
    return previous[-1] / len(ref)


def evaluate(args) -> int:
    """Replace Python with a tiny shell supervisor before native inference."""
    cgroup_budget(CANDIDATE_RAM_BYTES)
    if args.quantization not in QUANTIZATIONS:
        raise RuntimeError("QUANTIZATION_NOT_REGISTERED")
    artifact_root = resolve_artifact_root(args.artifact_root)
    manifest_path = artifact_root / "fullrank_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0":
        raise RuntimeError("FULLRANK_CANDIDATE_MANIFEST_SCHEMA_MISMATCH")
    if manifest.get("source_model", {}).get("sha256") != SOURCE_MODEL_SHA256:
        raise RuntimeError("FULLRANK_TEACHER_SOURCE_IDENTITY_MISMATCH")
    row = next((item for item in manifest.get("quantization_candidates", []) if item.get("quantization") == args.quantization), None)
    if not isinstance(row, dict):
        raise RuntimeError("FULLRANK_QUANTIZATION_CANDIDATE_MISSING")
    model_path = artifact_root / str(row.get("path", ""))
    if not model_path.is_file() or model_path.is_symlink() or model_path.stat().st_size != int(row.get("bytes", -1)) or sha256_file(model_path) != row.get("sha256"):
        raise RuntimeError("FULLRANK_QUANTIZED_MODEL_IDENTITY_MISMATCH")
    cli = artifact_root / "toolchain" / "bin" / "whisper-cli"
    if not cli.is_file() or cli.is_symlink():
        raise RuntimeError("PINNED_WHISPER_CLI_MISSING_OR_UNSAFE")
    os.chmod(cli, cli.stat().st_mode | 0o111)
    if not os.access(cli, os.X_OK):
        raise RuntimeError("PINNED_WHISPER_CLI_NOT_EXECUTABLE_AFTER_RESTORE")
    library_dir = artifact_root / "toolchain" / "lib"
    verified_libraries = verify_staged_shared_libraries(artifact_root, manifest)
    runtime_dependency_check = verify_whisper_runtime_dependencies(cli, library_dir)
    native_env = whisper_runtime_env(os.environ, library_dir)
    fixtures_path = Path(args.prepared_fixtures).resolve(strict=True)
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    if fixtures.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_PREPARED_FIXTURES/1.0":
        raise RuntimeError("PREPARED_SPEECH_FIXTURE_SCHEMA_MISMATCH")
    def checked_audio(name: str) -> Path:
        row = fixtures.get(name, {})
        path = Path(str(row.get("path", "")))
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("PREPARED_AUDIO_MISSING_OR_UNSAFE:" + name)
        path = path.resolve(strict=True)
        if path.stat().st_size != int(row.get("bytes", -1)) or sha256_file(path) != row.get("sha256"):
            raise RuntimeError("PREPARED_AUDIO_IDENTITY_MISMATCH:" + name)
        return path
    synthetic = checked_audio("synthetic_audio")
    real_audio = checked_audio("real_audio")
    real_transcript = str(fixtures.get("real_transcript", ""))
    if hashlib.sha256(real_transcript.encode("utf-8")).hexdigest() != fixtures.get("real_transcript_sha256"):
        raise RuntimeError("PREPARED_TRANSCRIPT_IDENTITY_MISMATCH")
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    import shlex
    q = lambda value: shlex.quote(str(value))
    runner = work / "whisper-native-inference.sh"
    lines = [
        "#!/usr/bin/env bash", "set -uo pipefail",
        "CLI=" + q(cli), "MODEL=" + q(model_path), "WORK=" + q(work),
        "export LD_LIBRARY_PATH=" + q(library_dir) + ':"${LD_LIBRARY_PATH:-}"',
        "SYNTH=" + q(synthetic), "REAL=" + q(real_audio),
        "CGROUP=/sys/fs/cgroup",
        "test -w \"$CGROUP/memory.reclaim\" || { echo CGROUP_MEMORY_RECLAIM_UNAVAILABLE >&2; exit 90; }",
        "cat \"$CGROUP/memory.events\" > \"$WORK/candidate-memory-events-before.txt\"",
        "run_one() {", " local audio=\"$1\" outdir=\"$2\"",
        " local prefix=\"$outdir/transcript\"",
        " mkdir -p \"$outdir\"", " rm -f \"$prefix.txt\" \"$outdir/exit_code\" \"$outdir/peak-rss-kib.txt\"",
        " printf '1073741824\\n' > \"$CGROUP/memory.reclaim\"",
        " local baseline=$(cat \"$CGROUP/memory.current\")",
        " printf '%s\\n' \"$baseline\" > \"$outdir/resident-baseline-bytes.txt\"",
        " if [ \"$baseline\" -gt 268435456 ]; then echo CANDIDATE_RESIDENT_BASELINE_OVER_256MIB:$baseline >&2; return 91; fi",
        " set +e",
        " /usr/bin/time -f '%M' -o \"$outdir/peak-rss-kib.txt\" \"$CLI\" -m \"$MODEL\" -f \"$audio\" -l en -t 1 -ng -nt -otxt -of \"$prefix\" -np -nf -bs 1 -bo 1 >\"$outdir/whisper-cli.log\" 2>&1",
        " local rc=$?", " set -e", " printf '%s\\n' \"$rc\" > \"$outdir/exit_code\"", "}",
        "set -e",
        "run_one \"$SYNTH\" \"$WORK/synthetic-hello-world\"",
        "run_one \"$REAL\" \"$WORK/real-" + REAL_AUDIO_ID + "\"",
        "cat \"$CGROUP/memory.events\" > \"$WORK/candidate-memory-events-after.txt\"",
        "cat \"$CGROUP/memory.current\" > \"$WORK/candidate-memory-current-after.txt\"",
        "cat \"$CGROUP/memory.peak\" > \"$WORK/candidate-cgroup-peak-diagnostic.txt\"",
        "exec " + q(sys.executable) + " -B " + q(Path(__file__).resolve()) + " report"
        + " --artifact-root " + q(artifact_root)
        + " --quantization " + q(args.quantization)
        + " --prepared-fixtures " + q(fixtures_path)
        + " --work-dir " + q(work) + " --report " + q(Path(args.report).resolve()),
    ]
    runner.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.execvpe("/bin/bash", ["/bin/bash", str(runner)], native_env)
    raise RuntimeError("WHISPER_NATIVE_EXEC_REPLACEMENT_FAILED")


def normalized_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", str(text).casefold())


def word_error_rate(reference: str, hypothesis: str) -> float:
    ref, hyp = normalized_words(reference), normalized_words(hypothesis)
    if not ref:
        raise ValueError("WER_REFERENCE_EMPTY")
    previous = list(range(len(hyp) + 1))
    for i, reference_word in enumerate(ref, 1):
        current = [i]
        for j, hypothesis_word in enumerate(hyp, 1):
            current.append(min(current[-1] + 1, previous[j] + 1,
                previous[j - 1] + (reference_word != hypothesis_word)))
        previous = current
    return previous[-1] / len(ref)


def report_evaluation(args) -> int:
    cgroup_budget(CANDIDATE_RAM_BYTES)
    artifact_root = resolve_artifact_root(args.artifact_root)
    manifest = json.loads((artifact_root / "fullrank_manifest.json").read_text(encoding="utf-8"))
    if manifest.get("schema") != "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0" or manifest.get("source_model", {}).get("sha256") != SOURCE_MODEL_SHA256:
        raise RuntimeError("FULLRANK_CANDIDATE_MANIFEST_IDENTITY_MISMATCH")
    row = next((x for x in manifest.get("quantization_candidates", []) if x.get("quantization") == args.quantization), None)
    if not isinstance(row, dict):
        raise RuntimeError("FULLRANK_QUANTIZATION_CANDIDATE_MISSING")
    model_path = artifact_root / str(row["path"])
    if not model_path.is_file() or model_path.stat().st_size != int(row["bytes"]) or sha256_file(model_path) != row["sha256"]:
        raise RuntimeError("FULLRANK_QUANTIZED_MODEL_IDENTITY_MISMATCH")
    fixtures_path = Path(args.prepared_fixtures).resolve(strict=True)
    fixtures = json.loads(fixtures_path.read_text(encoding="utf-8"))
    work = Path(args.work_dir).resolve()
    def load_task(task_id: str) -> tuple[dict, str]:
        outdir = work / task_id
        text_path = outdir / "transcript.txt"
        rc_path = outdir / "exit_code"
        log = outdir / "whisper-cli.log"
        if not text_path.is_file() or not rc_path.is_file():
            diagnostic = log.read_text(encoding="utf-8", errors="replace")[-2400:] if log.is_file() else "WHISPER_CLI_LOG_MISSING"
            exit_code = rc_path.read_text(encoding="ascii", errors="replace").strip() if rc_path.is_file() else "EXIT_CODE_MISSING"
            observed_files = sorted(p.name for p in outdir.iterdir()) if outdir.is_dir() else []
            print("WHISPER_NATIVE_DIAGNOSTIC:" + json.dumps({"task_id": task_id,
                "exit_code": exit_code, "files": observed_files, "cli_log_tail": diagnostic},
                ensure_ascii=False, sort_keys=True), flush=True)
            raise RuntimeError("WHISPER_NATIVE_INFERENCE_OUTPUT_MISSING:" + task_id + ":exit=" + exit_code)
        text = text_path.read_text(encoding="utf-8", errors="replace").strip()
        result = {"task_id": task_id, "exit_code": int(rc_path.read_text(encoding="ascii").strip()),
            "execution_status": "PASS_EXECUTION" if int(rc_path.read_text(encoding="ascii").strip()) == 0 and text else "FAIL_EXECUTION",
            "transcription_text": text[:1600], "output_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "output_file_bytes": text_path.stat().st_size,
            "diagnostic_output_tail": log.read_text(encoding="utf-8", errors="replace")[-2500:] if log.is_file() else ""}
        return result, text
    synth, synth_text = load_task("synthetic-hello-world")
    missing = [x for x in ("hello", "world") if x not in normalized_words(synth_text)]
    synth["quality_check"] = {"kind": "SYNTHETIC_KNOWN_ANSWER", "expected_words": ["hello", "world"],
        "missing_words": missing, "status": "PASS" if not missing else "FAIL"}
    real, real_text = load_task("real-" + REAL_AUDIO_ID)
    transcript = str(fixtures.get("real_transcript", ""))
    if hashlib.sha256(transcript.encode("utf-8")).hexdigest() != fixtures.get("real_transcript_sha256"):
        raise RuntimeError("PREPARED_TRANSCRIPT_IDENTITY_MISMATCH")
    wer = word_error_rate(transcript, real_text) if real_text else 1.0
    real["quality_check"] = {"kind": "PINNED_UPSTREAM_RECORDED_SPEECH", "dataset_repo": DATASET_REPO,
        "dataset_revision": DATASET_REVISION, "audio_id": REAL_AUDIO_ID,
        "reference_word_count": len(normalized_words(transcript)), "wer": round(wer, 6),
        "wer_limit": REAL_WER_MAX, "status": "PASS" if wer <= REAL_WER_MAX else "FAIL"}
    before_path = work / "candidate-memory-events-before.txt"
    after_path = work / "candidate-memory-events-after.txt"
    current_path = work / "candidate-memory-current-after.txt"
    cgroup_peak_path = work / "candidate-cgroup-peak-diagnostic.txt"
    if not before_path.is_file() or not after_path.is_file() or not current_path.is_file():
        raise RuntimeError("WHISPER_CGROUP_MEMORY_EVIDENCE_MISSING")
    events_before = read_memory_events(before_path)
    events_after = read_memory_events(after_path)
    events_delta = memory_event_delta(events_before, events_after)
    if events_delta.get("oom", 0) or events_delta.get("oom_kill", 0):
        raise RuntimeError("CANDIDATE_CGROUP_OOM_EVENT:" + json.dumps(events_delta, sort_keys=True))
    memory_rows = {}
    for task_id, task in (("synthetic-hello-world", synth), ("real-" + REAL_AUDIO_ID, real)):
        task_dir = work / task_id
        peak_path = task_dir / "peak-rss-kib.txt"
        baseline_path = task_dir / "resident-baseline-bytes.txt"
        if not peak_path.is_file() or not baseline_path.is_file():
            raise RuntimeError("WHISPER_PROCESS_RSS_EVIDENCE_MISSING:" + task_id)
        peak_kib = int(peak_path.read_text(encoding="ascii").strip())
        peak_bytes = peak_kib * 1024
        baseline_bytes = int(baseline_path.read_text(encoding="ascii").strip())
        if peak_bytes <= 0 or peak_bytes > CANDIDATE_RAM_BYTES:
            raise RuntimeError("CANDIDATE_NATIVE_PROCESS_PEAK_OVER_1GIB:" + task_id + ":" + str(peak_bytes))
        if baseline_bytes > 268435456:
            raise RuntimeError("CANDIDATE_RESIDENT_BASELINE_OVER_256MIB:" + task_id + ":" + str(baseline_bytes))
        task["native_process_peak_rss_bytes"] = peak_bytes
        task["resident_baseline_bytes"] = baseline_bytes
        memory_rows[task_id] = {
            "native_process_peak_rss_bytes": peak_bytes,
            "resident_baseline_bytes": baseline_bytes,
        }
    snapshot = {
        "measurement_method": "GNU_TIME_PER_NATIVE_WHISPER_CLI_PROCESS_PLUS_CGROUP_OOM_DELTA",
        "memory_limit_bytes": CANDIDATE_RAM_BYTES,
        "swap_limit_bytes": 0,
        "cpu_limit_cores": 1,
        "process_measurements": memory_rows,
        "max_native_process_peak_rss_bytes": max(x["native_process_peak_rss_bytes"] for x in memory_rows.values()),
        "cgroup_memory_current_after_bytes": int(current_path.read_text(encoding="ascii").strip()),
        "cgroup_memory_peak_diagnostic_bytes": int(cgroup_peak_path.read_text(encoding="ascii").strip()) if cgroup_peak_path.is_file() else None,
        "cgroup_memory_events_before": events_before,
        "cgroup_memory_events_after": events_after,
        "cgroup_memory_events_delta": events_delta,
        "oom_events_delta": events_delta.get("oom", 0),
        "oom_kill_events_delta": events_delta.get("oom_kill", 0),
    }
    tests = [synth, real]
    passed = all(x["execution_status"] == "PASS_EXECUTION" and x["quality_check"]["status"] == "PASS" for x in tests)
    projection = release_projection(model_path.stat().st_size)
    report = {"schema": "LOUKSNAPG_WHISPER_FULLRANK_CANDIDATE_EVALUATION/4.0",
        "status": "PASS_FULLRANK_CANDIDATE_TWO_TASKS_EXTERNAL_ASSET_REQUIRED" if passed and projection["external_asset_required"]
            else "PASS_FULLRANK_CANDIDATE_TWO_TASKS" if passed else "FAIL_FUNCTIONAL_OR_QUALITY_GATE",
        "candidate_id": "WHISPER_LARGE_V3_TURBO_FULLRANK_" + args.quantization.upper(),
        "quantization": args.quantization, "representation": "FULL_RANK_GGML_BLOCKWISE_INTEGER_QUANTIZATION",
        "teacher_source": manifest["source_model"],
        "candidate_weight": {"path": str(row["path"]), "bytes": model_path.stat().st_size, "sha256": sha256_file(model_path)},
        "candidate_resource_policy": {"status": "PASS_EXACT_CGROUP_V2_LIMITS", "memory_limit_bytes": CANDIDATE_RAM_BYTES,
            "swap_limit_bytes": 0, "cpu_limit_cores": 1},
        "candidate_memory_measurement": snapshot, "child_peak_rss_bytes": snapshot["max_native_process_peak_rss_bytes"],
        "dataset_fixture": fixtures["dataset_fixture"], "prepared_fixture_manifest_sha256": sha256_file(fixtures_path),
        "task_results": tests, "global_release_projection": projection,
        "source_teacher_mutated": False, "active_runtime_mutated": False, "candidate_integrated": False,
        "promotion_performed": False, "externalization": "REQUIRED_BUT_NOT_IMPLEMENTED" if projection["external_asset_required"] else "NOT_REQUIRED_BY_PROJECTION",
        "domain_certification": "NOT_GRANTED", "global_certification": "NOT_GRANTED"}
    json_write(Path(args.report), report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if passed else 3

def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("build")
    b.add_argument("--whisper-cpp-root", type=Path, required=True)
    b.add_argument("--openai-whisper-root", type=Path, required=True)
    b.add_argument("--output-dir", type=Path, required=True)
    b.add_argument("--report", type=Path, required=True)
    p = sub.add_parser("prepare-fixtures")
    p.add_argument("--artifact-root", type=Path, required=True)
    p.add_argument("--real-audio", type=Path, required=True)
    p.add_argument("--real-transcript", required=True)
    p.add_argument("--real-source-revision", required=True)
    p.add_argument("--work-dir", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--artifact-root", type=Path, required=True)
    e.add_argument("--quantization", required=True, choices=QUANTIZATIONS)
    e.add_argument("--prepared-fixtures", type=Path, required=True)
    e.add_argument("--work-dir", type=Path, required=True)
    e.add_argument("--report", type=Path, required=True)
    r = sub.add_parser("report")
    r.add_argument("--artifact-root", type=Path, required=True)
    r.add_argument("--quantization", required=True, choices=QUANTIZATIONS)
    r.add_argument("--prepared-fixtures", type=Path, required=True)
    r.add_argument("--work-dir", type=Path, required=True)
    r.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "build":
            return build(args)
        if args.mode == "prepare-fixtures":
            return prepare_fixtures(args)
        if args.mode == "report":
            return report_evaluation(args)
        return evaluate(args)
    except Exception as exc:
        report = {
            "schema": "LOUKSNAPG_WHISPER_FULLRANK_EXPERIMENT_ERROR/1.0",
            "status": "ERROR_FAIL_CLOSED",
            "mode": args.mode,
            "error_type": type(exc).__name__,
            "error": str(exc)[:5000],
            "cgroup_snapshot": cgroup_snapshot(),
            "child_peak_rss_bytes": child_peak_rss_bytes(),
            "promotion_performed": False,
            "certification": "NOT_GRANTED",
            "timestamp_utc": utc_now(),
        }
        report_path = getattr(args, "report", None)
        if report_path:
            json_write(Path(report_path), report)
        print(json.dumps(report, ensure_ascii=False, sort_keys=True), file=sys.stderr, flush=True)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
