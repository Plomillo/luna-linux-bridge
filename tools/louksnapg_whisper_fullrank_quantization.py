#!/usr/bin/env python3
"""Build and evaluate a full-rank Whisper quantization candidate under hard CPU/RAM cgroups.

This is an isolated experiment. It never edits the active Cajita runtime, source
weights, model manifest, LOUKSNAPG2 bundle, or certification state.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import importlib.util
import json
import os
import re
import resource
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

SOURCE_REPO = "openai/whisper-large-v3-turbo"
SOURCE_REVISION = "7e2743d4d1fc5182f43d53b0204b2e151ffb6ef7"
SOURCE_MODEL_SHA256 = "542566a422ae4f3fd23f1ba11add198fca01bbf82e66e6a2857b3f608b1eb9d1"
DATASET_REPO = "hf-internal-testing/librispeech_asr_dummy"
DATASET_REVISION = "5be91486e11a2d616f4ec5db8d3fd248585ac07a"
DATASET_PARQUET_SHA256 = "4e69a06fa5edc90921e5e7e39a7084881f8b3ed9c805c574f4f39c6fde27c603"
REAL_AUDIO_ID = "1272-128104-0000"
REAL_WER_MAX = 0.25

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




def create_streaming_converter(upstream_converter: Path, output_dir: Path) -> Path:
    """Read the pinned Whisper safetensors checkpoint one tensor at a time."""
    source = upstream_converter.read_text(encoding="utf-8")
    replacements = [
        (
            "from transformers import WhisperForConditionalGeneration\n",
            "from safetensors import safe_open\n",
        ),
        (
            "model = WhisperForConditionalGeneration.from_pretrained(dir_model)\n",
            'weight_path = dir_model / "model.safetensors"\n'
            'if not weight_path.is_file():\n'
            '    raise FileNotFoundError("PINNED_WHISPER_SAFETENSORS_MISSING")\n'
            'safe_weights = safe_open(str(weight_path), framework="pt", device="cpu")\n'
            "safe_weights.__enter__()\n",
        ),
        (
            "list_vars = model.state_dict()\n",
            "list_vars = safe_weights\n",
        ),
        (
            "data = list_vars[src].squeeze().numpy()\n",
            "data = safe_weights.get_tensor(src).squeeze().numpy()\n",
        ),
        (
            "fout.close()\n",
            "fout.close()\nsafe_weights.__exit__(None, None, None)\n",
        ),
    ]
    for original, replacement in replacements:
        if source.count(original) != 1:
            raise RuntimeError(
                "UPSTREAM_CONVERTER_PATCH_ANCHOR_MISMATCH:"
                + original.splitlines()[0]
            )
        source = source.replace(original, replacement)
    if "WhisperForConditionalGeneration.from_pretrained" in source:
        raise RuntimeError("FULL_TRANSFORMERS_MODEL_LOADING_NOT_REMOVED")
    if "safe_weights.get_tensor(src)" not in source:
        raise RuntimeError("SAFE_TENSOR_LAZY_READ_NOT_INSTALLED")
    patched = output_dir / "convert-h5-to-ggml-streaming.py"
    compile(source, str(patched), "exec")
    patched.write_text(source, encoding="utf-8")
    return patched

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

    converter = cpp_root / "models" / "convert-h5-to-ggml.py"
    mel_filters = openai_root / "whisper" / "assets" / "mel_filters.npz"
    if not converter.is_file() or not mel_filters.is_file():
        raise RuntimeError("PINNED_CONVERTER_OR_OPENAI_MEL_ASSET_MISSING")
    converter_sha = sha256_file(converter)
    if converter_sha != CONVERTER_SHA256:
        raise RuntimeError("WHISPER_CPP_CONVERTER_SHA256_MISMATCH:" + converter_sha)
    streaming_converter = create_streaming_converter(converter, out)
    streaming_converter_sha = sha256_file(streaming_converter)
    if git_head(cpp_root) != WHISPER_CPP_REVISION:
        raise RuntimeError("WHISPER_CPP_REVISION_MISMATCH")
    if git_head(openai_root) != OPENAI_WHISPER_REVISION:
        raise RuntimeError("OPENAI_WHISPER_ASSETS_REVISION_MISMATCH")

    from huggingface_hub import snapshot_download

    model_dir = Path(snapshot_download(
        repo_id=SOURCE_REPO,
        revision=SOURCE_REVISION,
        repo_type="model",
        local_dir=str(out / "source-cache"),
        allow_patterns=[
            "model.safetensors", "config.json", "vocab.json", "added_tokens.json",
            "generation_config.json", "preprocessor_config.json",
            "tokenizer_config.json", "special_tokens_map.json",
        ],
        max_workers=1,
    )).resolve(strict=True)
    source_weights = model_dir / "model.safetensors"
    if not source_weights.is_file():
        raise RuntimeError("PINNED_TEACHER_MODEL_WEIGHTS_MISSING")
    source_sha = sha256_file(source_weights)
    if source_sha != SOURCE_MODEL_SHA256:
        raise RuntimeError("PINNED_TEACHER_MODEL_SHA256_MISMATCH:" + source_sha)
    for required in ("config.json", "vocab.json", "added_tokens.json"):
        if not (model_dir / required).is_file():
            raise RuntimeError("PINNED_TEACHER_METADATA_MISSING:" + required)

    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OMP_THREAD_LIMIT": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "HF_HUB_OFFLINE": "1",
        "TRANSFORMERS_OFFLINE": "1",
        "PYTHONNOUSERSITE": "1",
        "PYTHONUNBUFFERED": "1",
    })
    fp16_model = out / "ggml-model-f16.bin"
    conversion = run_checked(
        [sys.executable, str(streaming_converter), str(model_dir), str(openai_root), str(out)],
        cwd=cpp_root, timeout=3600, env=env,
    )
    if not fp16_model.is_file():
        # The pinned converter writes ggml-model.bin in the requested output directory.
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

    # Preserve the exact executable and shared libraries built from the pinned source.
    for path in (cpp_root / "build" / "bin").iterdir():
        if path.is_file() and (path.name == "whisper-cli" or path.name.startswith("lib")):
            shutil.copy2(path, toolchain_root / path.name)
    if not (toolchain_root / "whisper-cli").is_file():
        raise RuntimeError("WHISPER_CLI_TOOLCHAIN_COPY_MISSING")
    manifest = {
        "schema": "LOUKSNAPG_WHISPER_FULLRANK_QUANTIZATION_CANDIDATE/1.0",
        "created_at_utc": utc_now(),
        "candidate_status": "BUILT_AWAITING_SEPARATE_1GIB_FUNCTIONAL_EVALUATION",
        "source_model": {
            "repo": SOURCE_REPO,
            "revision": SOURCE_REVISION,
            "sha256": source_sha,
            "bytes": source_weights.stat().st_size,
            "model_type": "whisper-large-v3-turbo",
        },
        "conversion": {
            "whisper_cpp_repository": "https://github.com/ggml-org/whisper.cpp",
            "whisper_cpp_revision": WHISPER_CPP_REVISION,
            "openai_whisper_assets_repository": "https://github.com/openai/whisper",
            "openai_whisper_assets_revision": OPENAI_WHISPER_REVISION,
            "converter_path": "models/convert-h5-to-ggml.py",
            "converter_sha256": converter_sha,
            "streaming_converter_sha256": streaming_converter_sha,
            "converter_execution_mode": "PINNED_UPSTREAM_TENSOR_MAPPING_WITH_LAZY_SAFETENSORS_PER_TENSOR_STREAMING",
            "full_transformers_model_materialization": False,
            "fp16_intermediate_bytes": fp16_model.stat().st_size,
            "fp16_intermediate_sha256": sha256_file(fp16_model),
            "conversion_execution": conversion,
            "quantizer_sha256": quantizer_sha,
            "whisper_cli_sha256": cli_sha,
            "quantization_commands": quantization_commands,
        },
        "resource_policy": budget,
        "build_peak_rss_bytes": child_peak_rss_bytes(),
        "build_cgroup_snapshot": cgroup_snapshot(),
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
    shutil.rmtree(model_dir, ignore_errors=True)
    shutil.rmtree(out / "source-cache", ignore_errors=True)
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


def load_helper(path: Path):
    spec = importlib.util.spec_from_file_location("louksnapg_existing_whisper_fixtures", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("EXISTING_WHISPER_FIXTURE_HELPER_UNAVAILABLE")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def resolve_artifact_root(path: Path) -> Path:
    """Resolve direct and GitHub Actions least-common-ancestor artifact ZIP layouts."""
    root = Path(path).resolve(strict=True)
    candidates = [root, root / "artifact"]
    matches = [candidate for candidate in candidates if (candidate / "fullrank_manifest.json").is_file()]
    if len(matches) > 1:
        raise RuntimeError("WHISPER_ARTIFACT_ROOT_AMBIGUOUS")
    if not matches:
        raise FileNotFoundError("WHISPER_FULLRANK_MANIFEST_NOT_FOUND:" + str(root))
    return matches[0].resolve(strict=True)


def evaluate(args) -> int:
    budget = cgroup_budget(CANDIDATE_RAM_BYTES)
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
    if not model_path.is_file() or model_path.is_symlink():
        raise RuntimeError("FULLRANK_QUANTIZED_MODEL_MISSING_OR_UNSAFE")
    if model_path.stat().st_size != int(row.get("bytes", -1)) or sha256_file(model_path) != row.get("sha256"):
        raise RuntimeError("FULLRANK_QUANTIZED_MODEL_IDENTITY_MISMATCH")
    cli = artifact_root / "toolchain" / "bin" / "whisper-cli"
    if not cli.is_file() or cli.is_symlink():
        raise RuntimeError("PINNED_WHISPER_CLI_MISSING_OR_UNSAFE")
    # GitHub artifact ZIP transport does not preserve POSIX executable bits.
    os.chmod(cli, cli.stat().st_mode | 0o111)
    if not os.access(cli, os.X_OK):
        raise RuntimeError("PINNED_WHISPER_CLI_NOT_EXECUTABLE_AFTER_RESTORE")

    helper = load_helper(Path(args.fixture_helper).resolve(strict=True))
    work = Path(args.work_dir).resolve()
    work.mkdir(parents=True, exist_ok=True)
    fixtures = work / "fixtures"
    fixtures.mkdir(parents=True, exist_ok=True)
    synthetic = helper.make_synthetic_audio(fixtures / "synthetic-hello-world.wav")
    real_audio, real_transcript, dataset_info = helper.get_librispeech_fixture(fixtures)
    env = os.environ.copy()
    env.update({
        "OMP_NUM_THREADS": "1",
        "OMP_THREAD_LIMIT": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "TOKENIZERS_PARALLELISM": "false",
        "PYTHONNOUSERSITE": "1",
        "LD_LIBRARY_PATH": str(cli.parent) + (":" + os.environ["LD_LIBRARY_PATH"] if os.environ.get("LD_LIBRARY_PATH") else ""),
    })
    tests = []
    max_elapsed = 0.0
    for task_id, audio_path in (
        ("synthetic-hello-world", synthetic),
        ("librispeech-" + REAL_AUDIO_ID, real_audio),
    ):
        out_dir = work / task_id
        out_dir.mkdir(parents=True, exist_ok=True)
        prefix = out_dir / "transcript"
        text_path = Path(str(prefix) + ".txt")
        text_path.unlink(missing_ok=True)
        command = [
            str(cli), "-m", str(model_path), "-f", str(audio_path),
            "-l", "en", "-t", "1", "-ng", "-nt", "-otxt", "-of", str(prefix),
            "-np", "-nf", "-bo", "1",
        ]
        started = time.monotonic()
        completed = subprocess.run(
            command, cwd=str(artifact_root), env=env,
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, errors="replace", timeout=900, check=False,
        )
        elapsed = round(time.monotonic() - started, 3)
        max_elapsed = max(max_elapsed, elapsed)
        output_text = text_path.read_text(encoding="utf-8", errors="replace").strip() if text_path.is_file() else ""
        result = {
            "task_id": task_id,
            "command": command,
            "exit_code": completed.returncode,
            "elapsed_seconds": elapsed,
            "execution_status": "PASS_EXECUTION" if completed.returncode == 0 and text_path.is_file() and output_text else "FAIL_EXECUTION",
            "transcription_text": output_text[:1600],
            "output_sha256": hashlib.sha256(output_text.encode("utf-8")).hexdigest(),
            "output_file_bytes": text_path.stat().st_size if text_path.is_file() else 0,
            "diagnostic_output_tail": completed.stdout[-2500:],
        }
        words = helper.normalized_words(output_text)
        if task_id == "synthetic-hello-world":
            missing = [word for word in ("hello", "world") if word not in words]
            result["quality_check"] = {
                "kind": "SYNTHETIC_KNOWN_ANSWER",
                "expected_words": ["hello", "world"],
                "missing_words": missing,
                "status": "PASS" if not missing else "FAIL",
            }
        else:
            wer = helper.word_error_rate(real_transcript, output_text) if output_text else 1.0
            result["quality_check"] = {
                "kind": "REAL_PUBLIC_RECORDED_SPEECH",
                "dataset_repo": DATASET_REPO,
                "dataset_revision": DATASET_REVISION,
                "audio_id": REAL_AUDIO_ID,
                "reference_word_count": len(helper.normalized_words(real_transcript)),
                "wer": round(wer, 6),
                "wer_limit": REAL_WER_MAX,
                "status": "PASS" if wer <= REAL_WER_MAX else "FAIL",
            }
        result["task_pass"] = result["execution_status"] == "PASS_EXECUTION" and result["quality_check"]["status"] == "PASS"
        tests.append(result)

    snapshot = cgroup_snapshot()
    events = snapshot.get("memory_events", {})
    if events.get("oom", 0) or events.get("oom_kill", 0):
        raise RuntimeError("CANDIDATE_CGROUP_OOM_EVENT:" + json.dumps(events, sort_keys=True))
    peak = snapshot.get("memory_peak_bytes")
    if not isinstance(peak, int) or peak > CANDIDATE_RAM_BYTES:
        raise RuntimeError("CANDIDATE_MEMORY_PEAK_OVER_1GIB:" + str(peak))
    passed = all(item.get("task_pass") is True for item in tests)
    projection = release_projection(model_path.stat().st_size)
    report = {
        "schema": "LOUKSNAPG_WHISPER_FULLRANK_CANDIDATE_EVALUATION/1.0",
        "status": (
            "PASS_FULLRANK_CANDIDATE_TWO_TASKS_EXTERNAL_ASSET_REQUIRED"
            if passed and projection["external_asset_required"] else
            "PASS_FULLRANK_CANDIDATE_TWO_TASKS"
            if passed else
            "FAIL_FUNCTIONAL_OR_QUALITY_GATE"
        ),
        "candidate_id": "WHISPER_LARGE_V3_TURBO_FULLRANK_" + args.quantization.upper(),
        "quantization": args.quantization,
        "representation": "FULL_RANK_GGML_BLOCKWISE_INTEGER_QUANTIZATION",
        "teacher_source": manifest["source_model"],
        "candidate_weight": {
            "path": str(row["path"]),
            "bytes": model_path.stat().st_size,
            "sha256": sha256_file(model_path),
        },
        "candidate_resource_policy": budget,
        "candidate_memory_measurement": snapshot,
        "child_peak_rss_bytes": child_peak_rss_bytes(),
        "elapsed_seconds_total": max_elapsed,
        "dataset_fixture": dataset_info,
        "task_results": tests,
        "global_release_projection": projection,
        "source_teacher_mutated": False,
        "active_runtime_mutated": False,
        "candidate_integrated": False,
        "promotion_performed": False,
        "externalization": "REQUIRED_BUT_NOT_IMPLEMENTED" if projection["external_asset_required"] else "NOT_REQUIRED_BY_PROJECTION",
        "domain_certification": "NOT_GRANTED",
        "global_certification": "NOT_GRANTED",
        "conclusion": (
            "The full-rank representation passed these two speech checks under the exact 1-GiB/1-core candidate envelope. This is experimental evidence only; the model is not integrated or certified."
            if passed else
            "The full-rank representation did not pass both speech checks. Do not integrate or promote it."
        ),
    }
    json_write(Path(args.report), report)
    return 0 if passed else 3


def main() -> int:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="mode", required=True)
    b = sub.add_parser("build")
    b.add_argument("--whisper-cpp-root", type=Path, required=True)
    b.add_argument("--openai-whisper-root", type=Path, required=True)
    b.add_argument("--output-dir", type=Path, required=True)
    b.add_argument("--report", type=Path, required=True)
    e = sub.add_parser("evaluate")
    e.add_argument("--artifact-root", type=Path, required=True)
    e.add_argument("--quantization", required=True, choices=QUANTIZATIONS)
    e.add_argument("--fixture-helper", type=Path, required=True)
    e.add_argument("--work-dir", type=Path, required=True)
    e.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    try:
        if args.mode == "build":
            return build(args)
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
