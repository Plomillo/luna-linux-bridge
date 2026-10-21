[Reading 1213 lines from start (total: 1213 lines, 0 remaining)]

#!/usr/bin/env python3
"""Fail-closed step classification and persistent Cajita quantization side-lane.

The side lane is deliberately independent of Lunita's S32 receipt gate. It records
its own state and evidence, operates only on a versioned output candidate, and
never promotes/certifies Cajita or mutates source model weights.
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import shutil
import subprocess
import sys
import shlex
import time
import uuid
from typing import Any

EXPECTED_LLAMA_CPP_COMMIT = "6a1a922d269908a29cbd4b49c27e6a8e7fd10fae"
MIN_CONVERSION_RAM_BYTES = 2 * 1024**3
MIN_CONVERSION_DISK_BYTES = 70 * 1024**3
REFRESH_SECONDS = 300

_BLOCK_MARKERS = (
    "BLOCKED", "FAIL", "ERROR", "SOURCE_MISSING", "PARTIAL", "DENIED",
    "MISMATCH", "NOT_RUN", "WAITING_FOR_EVENT", "WAITING_FOR_RESOURCE",
    "RECOVERY_REQUIRED", "UNAVAILABLE", "INVALID", "UNRESOLVED",
    "NOT_PUBLISHED_TARGET_EXISTS", "NOT_PUBLISHED_TARGET_ALREADY_EXISTS",
)


def result_blocks_step(result: dict[str, Any]) -> bool:
    """Fail closed when a handler omits step_completion but reports a blocker."""
    if not isinstance(result, dict):
        return True
    if result.get("step_completion") is False:
        return True
    status = str(result.get("status", "")).strip().upper()
    return not status or any(marker in status for marker in _BLOCK_MARKERS)


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _parse_utc(value: str) -> dt.datetime:
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))


def _minimum_conversion_ram_bytes(resource_recovery_verified: bool) -> int:
    """A hash-verified 4 GiB swap route permits a lower, still bounded host-RAM floor."""
    return (1536 * 1024**2) if resource_recovery_verified else MIN_CONVERSION_RAM_BYTES


def _build_conversion_command(lane: dict[str, Any], source_script: pathlib.Path,
                              model_dir: pathlib.Path, output: pathlib.Path, attempt: int) -> list[str]:
    """Build a converter command without combining incompatible tempfile/split options."""
    cmd = [str(lane["venv_python"]), str(source_script), "--outtype", "bf16",
           "--use-temp-file", "--outfile", str(output), str(model_dir)]
    tensor_bytes = int((lane.get("model_inventory") or {}).get("tensor_total_size_bytes", 0))
    # Only split outputs whose declared tensor payload exceeds 40 GiB. llama.cpp rejects
    # --use-temp-file together with --split-max-size; retain the safer streaming temp path
    # for the current 29.5 GB Qwen3 model and remove that option only when splitting is needed.
    if attempt > 1 and tensor_bytes > 40 * 1024**3:
        cmd = [arg for arg in cmd if arg != "--use-temp-file"]
        cmd += ["--split-max-size", "4G"]
    return cmd


def _bounded_compute_env(source: dict[str, str] | None = None,
                         temp_dir: pathlib.Path | str | None = None) -> dict[str, str]:
    """Bound numerical threads and route large converter spools off the small tmpfs."""
    env = dict(os.environ if source is None else source)
    env.update({
        "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1", "OMP_WAIT_POLICY": "PASSIVE",
        "OPENBLAS_NUM_THREADS": "1", "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1", "KMP_BLOCKTIME": "0", "TOKENIZERS_PARALLELISM": "false",
    })
    if temp_dir is not None:
        temp_path = pathlib.Path(temp_dir)
        temp_path.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not os.access(temp_path, os.W_OK | os.X_OK):
            raise RuntimeError("CAJITA_CONVERTER_TEMP_DIR_NOT_WRITABLE: " + str(temp_path))
        env.update({"TMPDIR": str(temp_path), "TEMP": str(temp_path), "TMP": str(temp_path)})
    return env


def _sha256(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def _load(path: pathlib.Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return default


def _atomic(path: pathlib.Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, path)


def _mem_available_bytes() -> int:
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _pid_alive(pid: int | None) -> bool:
    if not isinstance(pid, int) or pid <= 1:
        return False
    try:
        stat = pathlib.Path(f"/proc/{pid}/stat").read_text().split()
        if len(stat) > 2 and stat[2] == "Z":
            return False
        os.kill(pid, 0)
        return True
    except (OSError, ValueError, IndexError):
        return False


def _spawn_receipted_job(
    argv: list[str], cwd: pathlib.Path, env: dict[str, str], outputs: pathlib.Path, prefix: str
) -> dict[str, Any]:
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    log_path = outputs / f"{prefix}_{stamp}.log"
    receipt_path = outputs / f"{prefix}_{stamp}.json"
    outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
    wrapper = (
        "import datetime,json,os,pathlib,subprocess,sys,uuid\n"
        "out=pathlib.Path(sys.argv[-1]); argv=sys.argv[1:-1]\n"
        "started=datetime.datetime.now(datetime.timezone.utc).isoformat()\n"
        "try:\n"
        " p=subprocess.run(argv,check=False); rc=p.returncode; err=None\n"
        "except BaseException as exc:\n"
        " rc=125; err=type(exc).__name__+': '+str(exc)[:1000]\n"
        "row={'schema':'CUSTOSZ_RECEIPTED_JOB/1.0','started_at_utc':started,"
        "'finished_at_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),"
        "'argv':argv,'returncode':rc,'error':err}\n"
        "tmp=out.with_name(out.name+'.'+uuid.uuid4().hex+'.tmp')\n"
        "tmp.write_text(json.dumps(row,sort_keys=True,indent=2)+'\\n',encoding='utf-8')\n"
        "os.replace(tmp,out); sys.exit(rc)\n"
    )
    with log_path.open("xb") as log:
        proc = subprocess.Popen(
            [sys.executable, "-B", "-c", wrapper, *argv, str(receipt_path)],
            cwd=str(cwd), env=env, stdin=subprocess.DEVNULL, stdout=log,
            stderr=subprocess.STDOUT, close_fds=True, start_new_session=True,
        )
    return {
        "pid": proc.pid, "argv": argv, "log_path": str(log_path),
        "receipt_path": str(receipt_path), "started_at_utc": utc_now(),
        "process_wrapper": sys.executable,
    }


def _write_lane_event(state_dir: pathlib.Path, mission_sha256: str, event: dict[str, Any]) -> dict[str, Any]:
    outputs = state_dir / "worker_outputs"
    outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = outputs / f"CAJITA_PRIORITY_LANE_{stamp}.json"
    row = {
        "schema": "CUSTOSZ_CAJITA_PRIORITY_LANE_EVENT/1.0",
        "timestamp_utc": utc_now(), "mission_sha256": mission_sha256,
        "certification": "NOT_GRANTED", "mission_completion_claim": False, **event,
    }
    _atomic(path, row)
    return {"path": str(path), "sha256": _sha256(path), "status": row.get("status")}


def _model_inventory(model_dir: pathlib.Path) -> dict[str, Any]:
    config_path = model_dir / "config.json"
    index_path = model_dir / "model.safetensors.index.json"
    if not config_path.is_file() or not index_path.is_file():
        return {"status": "BLOCKED_MODEL_CONFIG_OR_INDEX_MISSING", "config_exists": config_path.is_file(),
                "index_exists": index_path.is_file(), "model_dir": str(model_dir)}
    config = json.loads(config_path.read_text(encoding="utf-8-sig"))
    index = json.loads(index_path.read_text(encoding="utf-8-sig"))
    weight_map = index.get("weight_map")
    if not isinstance(weight_map, dict) or not weight_map:
        return {"status": "BLOCKED_WEIGHT_MAP_INVALID", "model_dir": str(model_dir)}
    shards = sorted(set(str(x) for x in weight_map.values()))
    rows = []
    missing = []
    for name in shards:
        p = model_dir / name
        if not p.is_file():
            missing.append(name)
            continue
        st = p.stat()
        rows.append({"name": name, "bytes": st.st_size, "mtime_ns": st.st_mtime_ns})
    architecture = config.get("architectures") or []
    total = (index.get("metadata") or {}).get("total_size")
    status = "PASS_MODEL_INVENTORY" if (
        "Qwen3ForCausalLM" in architecture and config.get("torch_dtype") == "bfloat16"
        and not missing and len(rows) == len(shards) and isinstance(total, int) and total > 0
    ) else "BLOCKED_MODEL_IDENTITY_OR_SHARDS"
    return {
        "status": status, "model_id": "CAJITA_SISTEMA_INTELIGENTE_ANALISIS_AVANZADO_QWEN3",
        "model_dir": str(model_dir), "config_path": str(config_path), "config_sha256": _sha256(config_path),
        "index_path": str(index_path), "index_sha256": _sha256(index_path),
        "architectures": architecture, "torch_dtype": config.get("torch_dtype"),
        "tensor_total_size_bytes": total, "shard_count": len(shards), "shards": rows,
        "missing_shards": missing, "model_weights_modified": False,
    }


def _source_and_quantizer(state_dir: pathlib.Path) -> tuple[pathlib.Path | None, pathlib.Path | None, dict[str, Any]]:
    source = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699"
    script = source / "convert_hf_to_gguf.py"
    pin = subprocess.run(
        ["git", "-C", str(source), "rev-parse", "HEAD"],
        capture_output=True, text=True, timeout=15, check=False,
    ) if source.is_dir() else None
    source_ok = bool(pin and pin.returncode == 0 and pin.stdout.strip() == EXPECTED_LLAMA_CPP_COMMIT and script.is_file())
    report = _load(state_dir / "cajita_quantization_preflight.json", {}) or {}
    runtime_dir_value = ((report.get("quantization_toolchain") or {}).get("runtime_dir"))
    runtime_dir = pathlib.Path(runtime_dir_value) if runtime_dir_value else None
    quantizer = runtime_dir / "llama-quantize" if runtime_dir else None
    if not (quantizer and quantizer.is_file()):
        candidates = sorted((state_dir / "tools").glob("llama-b10819_*/llama-quantize"))
        quantizer = candidates[0] if candidates else None
        runtime_dir = quantizer.parent if quantizer else None
    q_ok = bool(quantizer and quantizer.is_file())
    details = {
        "converter_source_path": str(source), "converter_source_commit": pin.stdout.strip() if pin and pin.returncode == 0 else None,
        "expected_converter_commit": EXPECTED_LLAMA_CPP_COMMIT,
        "converter_source_status": "PASS" if source_ok else "BLOCKED_PINNED_CONVERTER_SOURCE",
        "quantizer_path": str(quantizer) if quantizer else None,
        "quantizer_status": "PASS" if q_ok else "BLOCKED_PINNED_QUANTIZER_MISSING",
        "quantizer_runtime_dir": str(runtime_dir) if runtime_dir else None,
    }
    return (script if source_ok else None), (quantizer if q_ok else None), details


def _resolve_runtime_requirements(
    state_dir: pathlib.Path, source: pathlib.Path, python_version: str
) -> tuple[pathlib.Path, dict[str, Any]]:
    """Honor pinned source requirements, but adapt only the incompatible Python 3.13 dependency edge.

    The official legacy requirements in some pinned llama.cpp revisions require NumPy 1.26.4,
    which has no CPython 3.13 wheel and does not declare Python 3.13 support. For 3.13 only,
    use the same checkout's top-level pyproject.toml compatibility metadata and its local gguf-py
    source package. Keep the original requirements immutable and hash-bound.
    """
    original = source / "requirements" / "requirements-convert_hf_to_gguf.txt"
    if not original.is_file():
        raise RuntimeError("PINNED_CONVERTER_REQUIREMENTS_MISSING")
    original_sha = _sha256(original)
    try:
        pieces = python_version.split(".")
        major, minor = int(pieces[0]), int(pieces[1])
    except (ValueError, IndexError):
        raise RuntimeError("PYTHON_VERSION_UNPARSEABLE:" + python_version)
    if (major, minor) < (3, 13):
        return original, {
            "profile": "PINNED_UPSTREAM_REQUIREMENTS",
            "python_version": python_version,
            "original_requirements_path": str(original),
            "original_requirements_sha256": original_sha,
            "runtime_requirements_path": str(original),
            "runtime_requirements_sha256": original_sha,
            "compatibility_override": False,
        }

    pyproject = source / "pyproject.toml"
    gguf_project = source / "gguf-py" / "pyproject.toml"
    if not pyproject.is_file() or not gguf_project.is_file():
        raise RuntimeError("PYTHON313_COMPATIBILITY_METADATA_MISSING")
    pytext = pyproject.read_text(encoding="utf-8")
    gguf_text = gguf_project.read_text(encoding="utf-8")
    if ">=3.10,<3.15" not in pytext or "numpy (>=1.26.4,<3.0.0)" not in pytext or "version = \"0.19.0\"" not in gguf_text:
        raise RuntimeError("PYTHON313_COMPATIBILITY_METADATA_MISMATCH")
    runtime_root = state_dir / "tools" / "requirements"
    runtime_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    # Preserve the earlier generic profile; create a distinct versioned file after the evidenced sdist failure.
    output = runtime_root / ("llama-cpp-converter-python" + str(major) + str(minor) + "-" + EXPECTED_LLAMA_CPP_COMMIT[:12] + "-numpy226-v2.txt")
    content = (
        "# Derived, compatibility-scoped runtime requirements; original upstream files remain unchanged.\n"
        "# Source commit: " + EXPECTED_LLAMA_CPP_COMMIT + "\n"
        "# Source pyproject SHA-256: " + _sha256(pyproject) + "\n"
        "# Legacy requirements SHA-256: " + _sha256(source / "requirements" / "requirements-convert_legacy_llama.txt") + "\n"
        "numpy==2.2.6\n"
        "sentencepiece>=0.1.98,<0.3.0\n"
        "transformers==4.57.6\n"
        "protobuf>=4.21.0,<5.0.0\n"
        "gguf @ " + (source / "gguf-py").resolve().as_uri() + "\n"
        "tqdm>=4.27\n"
        "pyyaml>=5.1\n"
        "requests>=2.25\n"
    )
    if output.exists():
        if output.read_text(encoding="utf-8") != content:
            raise RuntimeError("RUNTIME_REQUIREMENTS_CANDIDATE_COLLISION")
    else:
        with output.open("x", encoding="utf-8") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(output, 0o600)
    return output, {
        "profile": "SOURCE_METADATA_COMPATIBLE_PYTHON313_NUMPY226_V2",
        "compatibility_profile_id": "PYTHON313_NUMPY226_V2",
        "python_version": python_version,
        "original_requirements_path": str(original),
        "original_requirements_sha256": original_sha,
        "runtime_requirements_path": str(output),
        "runtime_requirements_sha256": _sha256(output),
        "source_pyproject_path": str(pyproject),
        "source_pyproject_sha256": _sha256(pyproject),
        "source_gguf_pyproject_path": str(gguf_project),
        "source_gguf_pyproject_sha256": _sha256(gguf_project),
        "runtime_numpy_constraint": "==2.2.6",
        "runtime_gguf_source": str(source / "gguf-py"),
        "compatibility_override": True,
        "reason": "Pinned legacy NumPy 1.26.4 requires an sdist on Python 3.13; this source checkout allows NumPy <3.0.0, so use the CPython 3.13 wheel pinned at 2.2.6 and keep the original upstream requirements immutable.",
    }


def _compatibility_recovery_route(lane: dict[str, Any], state_dir: pathlib.Path | str) -> dict[str, Any] | None:
    """Select one evidence-triggered Python 3.13 route after a proven legacy-NumPy sdist failure."""
    if lane.get("stage") != "BLOCKED_ENVIRONMENT_PROVISIONING":
        return None
    if int(lane.get("compatibility_recovery_attempts", 0)) >= 1:
        return None
    if lane.get("runtime_requirements_path"):
        return None
    python_path = str(lane.get("venv_python", ""))
    if "py313" not in python_path or not python_path.endswith("/bin/python"):
        return None
    attempts = lane.get("attempts") or []
    failed = next((row for row in reversed(attempts)
                   if row.get("stage") == "ENV_INSTALL_FALLBACK_RUNNING"
                   and row.get("status") == "FAIL"
                   and row.get("returncode") == 1
                   and row.get("receipt_path")
                   and row.get("log_path")), None)
    if not failed:
        return None
    receipt_path = pathlib.Path(failed["receipt_path"])
    log_path = pathlib.Path(failed["log_path"])
    receipt = _load(receipt_path, None)
    if not isinstance(receipt, dict) or receipt.get("returncode") != 1:
        return None
    argv = receipt.get("argv")
    argv_text = json.dumps(argv, ensure_ascii=False) if isinstance(argv, (list, dict)) else str(argv or "")
    if "numpy~=1.26.4" not in argv_text:
        return None
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace").casefold()
    except OSError:
        return None
    if "metadata-generation-failed" not in log_text or "numpy-1.26.4.tar.gz" not in log_text:
        return None
    return {
        "next_stage": "PROVISION_ENV",
        "reason_code": "PYTHON313_NUMPY_LEGACY_SDIST_INCOMPATIBLE",
        "numpy_requirement": "numpy==2.2.6",
        "source_commit": EXPECTED_LLAMA_CPP_COMMIT,
        "evidence": {
            "receipt_path": str(receipt_path),
            "receipt_sha256": _sha256(receipt_path),
            "log_path": str(log_path),
            "log_sha256": _sha256(log_path),
            "failure_signature": "metadata-generation-failed: numpy-1.26.4.tar.gz on CPython 3.13",
            "previous_argv_sha256": hashlib.sha256(argv_text.encode()).hexdigest(),
        },
        "action": "Re-enter pinned-source PROVISION_ENV so _resolve_runtime_requirements selects the source-declared Python 3.13 profile; do not repeat the legacy requirements route.",
    }


def _compatibility_recovery_route(lane: dict[str, Any], state_dir: pathlib.Path | str) -> dict[str, Any] | None:
    """Select a single, evidence-bound route away from the proven Python 3.13 NumPy sdist failure."""
    if lane.get("stage") != "BLOCKED_ENVIRONMENT_PROVISIONING":
        return None
    if int(lane.get("compatibility_recovery_attempts", 0)) >= 1:
        return None
    if lane.get("runtime_requirements_path"):
        return None
    python_path = str(lane.get("venv_python", ""))
    if "py313" not in python_path or not python_path.endswith("/bin/python"):
        return None
    failed = next((row for row in reversed(lane.get("attempts") or [])
                   if row.get("stage") == "ENV_INSTALL_FALLBACK_RUNNING"
                   and row.get("status") == "FAIL"
                   and row.get("returncode") == 1
                   and row.get("receipt_path")
                   and row.get("log_path")), None)
    if not failed:
        return None
    receipt_path = pathlib.Path(failed["receipt_path"])
    log_path = pathlib.Path(failed["log_path"])
    receipt = _load(receipt_path, None)
    if not isinstance(receipt, dict) or receipt.get("returncode") != 1:
        return None
    argv = receipt.get("argv")
    argv_text = json.dumps(argv, ensure_ascii=False) if isinstance(argv, (list, dict)) else str(argv or "")
    if "numpy~=1.26.4" not in argv_text:
        return None
    try:
        log_text = log_path.read_text(encoding="utf-8", errors="replace").casefold()
    except OSError:
        return None
    if "metadata-generation-failed" not in log_text or "numpy-1.26.4.tar.gz" not in log_text:
        return None
    return {
        "next_stage": "PROVISION_ENV",
        "reason_code": "PYTHON313_NUMPY_LEGACY_SDIST_INCOMPATIBLE",
        "numpy_requirement": "numpy==2.2.6",
        "source_commit": EXPECTED_LLAMA_CPP_COMMIT,
        "evidence": {
            "receipt_path": str(receipt_path),
            "receipt_sha256": _sha256(receipt_path),
            "log_path": str(log_path),
            "log_sha256": _sha256(log_path),
            "failure_signature": "metadata-generation-failed: numpy-1.26.4.tar.gz on CPython 3.13",
            "previous_argv_sha256": hashlib.sha256(argv_text.encode()).hexdigest(),
        },
        "action": "Use the pinned-source Python 3.13 compatibility resolver and its versioned requirements file; do not repeat the legacy NumPy 1.26.4 source-build route.",
    }


def _recover_runtime_requirements_permission_block(
    lane: dict[str, Any], state_dir: pathlib.Path | str
) -> dict[str, Any] | None:
    """Retry only after the saved PermissionError premise is measurably repaired."""
    if lane.get("stage") != "BLOCKED_RUNTIME_REQUIREMENTS_PROFILE":
        return None
    if int(lane.get("runtime_requirements_permission_recovery_attempts", 0)) >= 1:
        return None
    last_error = lane.get("last_error") or {}
    if not isinstance(last_error, dict) or last_error.get("error_type") != "PermissionError":
        return None
    state_dir = pathlib.Path(state_dir)
    requirements_dir = state_dir / "tools" / "requirements"
    error_text = str(last_error.get("error", ""))
    if str(requirements_dir) not in error_text:
        return None
    if not requirements_dir.is_dir() or not os.access(requirements_dir, os.W_OK | os.X_OK):
        return None
    source = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699"
    required = (
        source / "pyproject.toml",
        source / "gguf-py" / "pyproject.toml",
        source / "requirements" / "requirements-convert_hf_to_gguf.txt",
        source / "requirements" / "requirements-convert_legacy_llama.txt",
    )
    if not all(path.is_file() for path in required):
        return None
    previous_error_sha = hashlib.sha256(
        json.dumps(last_error, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    lane.setdefault("attempts", []).append({
        "stage": "BLOCKED_RUNTIME_REQUIREMENTS_PROFILE",
        "status": "ROOT_CAUSE_PREMISE_CHANGED_RETRY_ALLOWED",
        "reason_code": "REQUIREMENTS_DIRECTORY_WRITE_PERMISSION_RESTORED",
        "timestamp_utc": utc_now(),
        "requirements_dir": str(requirements_dir),
        "requirements_dir_uid": requirements_dir.stat().st_uid,
        "effective_uid": os.geteuid(),
        "prior_error_type": last_error.get("error_type"),
        "prior_error_sha256": previous_error_sha,
        "preserve_existing_requirements_overlay": True,
        "new_profile_id": "PYTHON313_NUMPY226_V2",
    })
    lane["stage"] = "PROVISION_ENV"
    lane["runtime_requirements_path"] = None
    lane["runtime_requirements_sha256"] = None
    lane["requirements_profile"] = None
    lane["runtime_requirements_permission_recovery_attempts"] = 1
    lane.pop("next_action_utc", None)
    lane.pop("last_error", None)
    lane["last_progress_utc"] = utc_now()
    return {
        "status": "CAJITA_RUNTIME_REQUIREMENTS_PERMISSION_RECOVERY_SELECTED",
        "stage": "PROVISION_ENV",
        "did_work": True,
        "reason_code": "REQUIREMENTS_DIRECTORY_WRITE_PERMISSION_RESTORED",
        "prior_error_sha256": previous_error_sha,
        "new_profile_id": "PYTHON313_NUMPY226_V2",
        "next_action": "Create a distinct -numpy226-v2.txt from pinned source metadata; preserve the earlier requirements file byte-for-byte.",
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }


def _read_job(state: dict[str, Any]) -> tuple[dict[str, Any] | None, bool]:
    job = state.get("job") or {}
    receipt_path = pathlib.Path(job["receipt_path"]) if job.get("receipt_path") else None
    receipt = _load(receipt_path, None) if receipt_path else None
    if isinstance(receipt, dict):
        return receipt, False
    return None, _pid_alive(job.get("pid"))


def tick_cajita_priority_lane(
    state_dir: pathlib.Path | str, cajita_root: pathlib.Path | str, mission_sha256: str
) -> dict[str, Any]:
    """Advance or monitor one bounded action in Cajita's independent quantization lane."""
    state_dir = pathlib.Path(state_dir)
    cajita_root = pathlib.Path(cajita_root)
    mission_path = state_dir.parent.parent / "MISION1.txt"
    if not mission_path.is_file():
        raise RuntimeError("CAJITA_LANE_MISSION_FILE_MISSING")
    mission_text = mission_path.read_text(encoding="utf-8-sig")
    observed_mission_sha = _sha256(mission_path)
    if observed_mission_sha != mission_sha256:
        raise RuntimeError("CAJITA_LANE_MISSION_SHA256_MISMATCH")
    mission_lower = mission_text.casefold()
    mission_controls = {
        "mission_path": str(mission_path), "mission_sha256": observed_mission_sha,
        "cajita_priority_declared": "cajita de luna: máxima prioridad operativa" in mission_lower,
        "quantization_required": "3.3. cuantización, poda y optimización" in mission_lower,
        "lunita_secondary_front_declared": "5. segundo frente" in mission_lower and "cierre de lunita" in mission_lower,
        "certification_requires_independent_validation": "validación independiente" in mission_lower and "certificación" in mission_lower,
    }
    if not all(value for key, value in mission_controls.items() if key not in {"mission_path", "mission_sha256"}):
        raise RuntimeError("CAJITA_LANE_MISSION_CONTROL_CONTRACT_MISMATCH")
    lane_path = state_dir / "cajita_priority_lane.json"
    outputs = state_dir / "worker_outputs"
    lane = _load(lane_path, None)
    if lane is None:
        lane = {
            "schema": "CUSTOSZ_CAJITA_PRIORITY_LANE_STATE/1.0", "mission_sha256": mission_sha256,
            "stage": "PREFLIGHT", "candidate_id": None, "job": None, "attempts": [],
            "created_at_utc": utc_now(), "last_progress_utc": None, "certification": "NOT_GRANTED",
            "mission_controls": mission_controls,
        }
        _atomic(lane_path, lane)
    if lane.get("mission_sha256") != mission_sha256:
        raise RuntimeError("CAJITA_PRIORITY_LANE_MISSION_HASH_MISMATCH")

    stage = lane.get("stage")
    if stage == "BLOCKED_RUNTIME_REQUIREMENTS_PROFILE":
        permission_recovery = _recover_runtime_requirements_permission_block(lane, state_dir)
        if permission_recovery:
            _atomic(lane_path, lane)
            return permission_recovery
    if stage == "BLOCKED_ENVIRONMENT_PROVISIONING":
        recovery = _compatibility_recovery_route(lane, state_dir)
        if recovery:
            # Preserve both failed receipts. This is a different versioned dependency profile,
            # selected only because the preceding receipt and log prove the legacy NumPy sdist failure.
            lane.setdefault("attempts", []).append({
                "stage": stage,
                "status": "ALTERNATIVE_ROUTE_SELECTED",
                "timestamp_utc": utc_now(),
                "reason_code": recovery["reason_code"],
                "evidence": recovery["evidence"],
                "next_stage": recovery["next_stage"],
            })
            lane["stage"] = recovery["next_stage"]
            lane["compatibility_recovery_attempts"] = int(lane.get("compatibility_recovery_attempts", 0)) + 1
            lane["compatibility_recovery_route"] = recovery
            lane["last_progress_utc"] = utc_now()
            lane["next_action_utc"] = None
            _atomic(lane_path, lane)
            return {
                "status": "CAJITA_COMPATIBILITY_RECOVERY_ROUTE_SELECTED",
                "stage": lane["stage"],
                "did_work": True,
                "reason_code": recovery["reason_code"],
                "evidence": recovery["evidence"],
                "next_action": recovery["action"],
            }
        return {
            "status": "CAJITA_ENVIRONMENT_PROVISIONING_BLOCKED_AWAITING_NEW_EVIDENCE",
            "stage": stage,
            "did_work": False,
            "next_action": "Do not repeat the same failed installer. Keep the failure receipt and wait for a materially different, evidence-bound dependency/interpreter route.",
        }
    if stage in {"ENV_INSTALL_RUNNING", "ENV_INSTALL_FALLBACK_RUNNING", "DRY_RUN_RUNNING", "CONVERSION_RUNNING", "QUANTIZATION_RUNNING", "HASH_RUNNING"}:
        job_result, alive = _read_job(lane)
        if job_result is None and alive:
            return {"status": "CAJITA_JOB_RUNNING", "stage": stage, "did_work": False,
                    "candidate_id": lane.get("candidate_id"), "job": lane.get("job"),
                    "next_action": "Keep the bounded worker alive; poll its receipt without launching a duplicate."}
        if job_result is None and not alive:
            lane.setdefault("attempts", []).append({
                "stage": stage, "status": "BLOCKED_JOB_EXIT_WITHOUT_RECEIPT", "timestamp_utc": utc_now(),
                "pid": (lane.get("job") or {}).get("pid"),
            })
            fallback_to_real_conversion = False
            job_info = lane.get("job") or {}
            if stage == "DRY_RUN_RUNNING":
                log_path = pathlib.Path(str(job_info.get("log_path") or ""))
                try:
                    log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-12000:] if log_path.is_file() else ""
                except OSError:
                    log_tail = ""
                fallback_to_real_conversion = bool(
                    "token_embd.weight" in log_tail
                    and lane.get("model_inventory", {}).get("status") == "PASS_MODEL_INVENTORY"
                    and lane.get("toolchain", {}).get("converter_source_commit") == EXPECTED_LLAMA_CPP_COMMIT
                    and lane.get("toolchain", {}).get("converter_source_status") == "PASS"
                )
                if fallback_to_real_conversion:
                    lane["dry_run_fallback_evidence"] = {
                        "schema": "CUSTOSZ_CAJITA_DRY_RUN_FALLBACK_EVIDENCE/1.0",
                        "timestamp_utc": utc_now(), "reason": "DRY_RUN_EXITED_WITHOUT_RECEIPT_AT_LARGEST_TENSOR; use bounded real conversion as the next diagnostic step",
                        "receipt_path": job_info.get("receipt_path"), "log_path": str(log_path),
                        "log_sha256": _sha256(log_path) if log_path.is_file() else None,
                        "model_inventory_status": lane.get("model_inventory", {}).get("status"),
                        "pinned_converter_commit": EXPECTED_LLAMA_CPP_COMMIT,
                        "source_model_weights_modified": False, "certification": "NOT_GRANTED",
                    }
            lane["stage"] = (
                "CONVERT_RETRY" if fallback_to_real_conversion else {
                    "ENV_INSTALL_RUNNING": "PROVISION_ENV",
                    "ENV_INSTALL_FALLBACK_RUNNING": "BLOCKED_ENVIRONMENT_FALLBACK_EXIT_WITHOUT_RECEIPT",
                    "DRY_RUN_RUNNING": "DRY_RUN",
                    "CONVERSION_RUNNING": "CONVERT_RETRY",
                    "QUANTIZATION_RUNNING": "QUANTIZE_RETRY",
                    "HASH_RUNNING": "HASH_OUTPUT",
                }[stage]
            )
            lane["job"] = None
            lane["last_error"] = "JOB_EXIT_WITHOUT_RECEIPT"
            _atomic(lane_path, lane)
            action = ("Launch pinned BF16 conversion with one-thread numerical libraries; on success the lane advances to Q4_K_M quantization."
                      if fallback_to_real_conversion else "Use the preserved log, then retry via the explicit fallback route.")
            return {"status": "CAJITA_JOB_RECOVERY_ROUTE_SELECTED", "stage": lane["stage"],
                    "did_work": True, "next_action": action}

        assert job_result is not None
        rc = job_result.get("returncode")
        lane.setdefault("attempts", []).append({
            "stage": stage, "status": "PASS" if rc == 0 else "FAIL",
            "returncode": rc, "receipt_path": (lane.get("job") or {}).get("receipt_path"),
            "log_path": (lane.get("job") or {}).get("log_path"), "timestamp_utc": utc_now(),
        })
        if rc != 0:
            if stage == "ENV_INSTALL_RUNNING":
                attempts = int(lane.get("env_install_attempts", 1))
                lane["stage"] = "PROVISION_ENV_FALLBACK" if attempts >= 2 else "PROVISION_ENV"
                lane["next_action_utc"] = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
            elif stage == "ENV_INSTALL_FALLBACK_RUNNING":
                lane["stage"] = "BLOCKED_ENVIRONMENT_PROVISIONING"
                lane["fallback_environment_failed"] = True
                lane["fallback_failure_log_path"] = (lane.get("job") or {}).get("log_path")
            elif stage == "DRY_RUN_RUNNING":
                # The dry-run itself loads the model's largest tensor. An interrupted or
                # libgomp-thread-blocked dry-run is a non-production probe failure, not a
                # reason to loop forever: preserve it and attempt the real conversion once
                # with a bounded numerical-library thread environment. Other failures fail closed.
                job_info = lane.get("job") or {}
                err_text = str(job_result.get("error") or "")
                log_path = pathlib.Path(str(job_info.get("log_path") or ""))
                try:
                    log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-12000:] if log_path.is_file() else ""
                except OSError:
                    log_tail = ""
                failure_text = (err_text + "\n" + log_tail).casefold()
                known_resource_probe_failure = (
                    rc in {1, 125}
                    and any(marker in failure_text for marker in (
                        "keyboardinterrupt", "libgomp: thread creation failed", "resource temporarily unavailable"
                    ))
                    and lane.get("model_inventory", {}).get("status") == "PASS_MODEL_INVENTORY"
                    and lane.get("toolchain", {}).get("converter_source_commit") == EXPECTED_LLAMA_CPP_COMMIT
                    and lane.get("toolchain", {}).get("converter_source_status") == "PASS"
                )
                if known_resource_probe_failure:
                    lane["stage"] = "CONVERT_RETRY"
                    lane["dry_run_fallback_evidence"] = {
                        "schema": "CUSTOSZ_CAJITA_DRY_RUN_FALLBACK_EVIDENCE/1.0",
                        "timestamp_utc": utc_now(), "reason": "INTERRUPTED_OR_THREAD_BLOCKED_DRY_RUN; bounded real conversion is next diagnostic step",
                        "dry_run_returncode": rc, "receipt_path": job_info.get("receipt_path"),
                        "receipt_error": err_text[:1200], "log_path": str(log_path),
                        "log_sha256": _sha256(log_path) if log_path.is_file() else None,
                        "model_inventory_status": lane.get("model_inventory", {}).get("status"),
                        "pinned_converter_commit": EXPECTED_LLAMA_CPP_COMMIT,
                        "source_model_weights_modified": False,
                        "certification": "NOT_GRANTED",
                    }
                else:
                    lane["stage"] = "DRY_RUN"
            elif stage == "CONVERSION_RUNNING":
                job_info = lane.get("job") or {}
                log_path = pathlib.Path(str(job_info.get("log_path") or ""))
                try:
                    log_tail = log_path.read_text(encoding="utf-8", errors="replace")[-16000:] if log_path.is_file() else ""
                except OSError:
                    log_tail = ""
                resource_failure = (
                    rc in {1, 125, 137, -9}
                    and int(lane.get("conversion_attempts", 0)) >= 1
                    and "token_embd.weight" in log_tail
                    and lane.get("model_inventory", {}).get("status") == "PASS_MODEL_INVENTORY"
                    and lane.get("toolchain", {}).get("converter_source_commit") == EXPECTED_LLAMA_CPP_COMMIT
                )
                if resource_failure:
                    lane["stage"] = "BLOCKED_CONVERSION_RESOURCE"
                    lane["conversion_resource_failure"] = {
                        "schema": "CUSTOSZ_CAJITA_CONVERSION_RESOURCE_FAILURE/1.0",
                        "timestamp_utc": utc_now(), "reason": "CONVERSION_FAILED_AT_LARGEST_TENSOR; resource recovery required before any retry",
                        "returncode": rc, "receipt_path": job_info.get("receipt_path"),
                        "log_path": str(log_path), "log_sha256": _sha256(log_path) if log_path.is_file() else None,
                        "largest_tensor_marker": "token_embd.weight", "conversion_attempts": int(lane.get("conversion_attempts", 0)),
                        "pinned_converter_commit": EXPECTED_LLAMA_CPP_COMMIT,
                        "model_source_weights_modified": False, "certification": "NOT_GRANTED",
                    }
                    lane["resource_recovery_evidence"] = None
                else:
                    lane["stage"] = "CONVERT_RETRY"
            elif stage == "QUANTIZATION_RUNNING":
                lane["stage"] = "QUANTIZE_RETRY"
            elif stage == "HASH_RUNNING":
                lane["stage"] = "HASH_OUTPUT"
            lane["last_error"] = {"stage": stage, "returncode": rc, "log_path": (lane.get("job") or {}).get("log_path")}
            lane["job"] = None
            lane["last_progress_utc"] = utc_now()
            _atomic(lane_path, lane)
            next_action = (
                "BLOCKED: converter failed at the largest tensor. Do not retry until a versioned resource-recovery receipt is recorded and bound to the lane."
                if lane.get("conversion_resource_failure") else
                "Launch pinned BF16 conversion with one-thread numerical libraries; the heavy lane starts Q4_K_M quantization only after a validated conversion receipt."
                if lane.get("dry_run_fallback_evidence") else
                "Run the configured lower-resource or dependency-repair fallback; original model weights remain read-only."
            )
            return {"status": "CAJITA_JOB_FAILURE_DIAGNOSED", "stage": lane["stage"], "did_work": True,
                    "returncode": rc, "log_path": lane["last_error"]["log_path"], "next_action": next_action}

        if stage in {"ENV_INSTALL_RUNNING", "ENV_INSTALL_FALLBACK_RUNNING"}:
            vpy = pathlib.Path(lane["venv_python"])
            probe = subprocess.run(
                [str(vpy), "-c", "import torch,transformers,gguf; print('torch='+torch.__version__); print('transformers='+transformers.__version__)"],
                capture_output=True, text=True, timeout=60, check=False,
            )
            if probe.returncode != 0:
                lane["stage"] = "PROVISION_ENV_FALLBACK" if stage == "ENV_INSTALL_RUNNING" else "BLOCKED_ENVIRONMENT_PROVISIONING"
                lane["last_error"] = {"stage": "ENV_IMPORT_PROBE", "stderr": probe.stderr[-1600:]}
                if stage == "ENV_INSTALL_FALLBACK_RUNNING":
                    lane["fallback_environment_failed"] = True
            else:
                freeze = subprocess.run([str(vpy), "-m", "pip", "freeze"], capture_output=True, text=True, timeout=90, check=False)
                manifest = {
                    "schema": "CUSTOSZ_CAJITA_CONVERTER_ENVIRONMENT/1.0",
                    "captured_at_utc": utc_now(), "python": str(vpy),
                    "source_commit": EXPECTED_LLAMA_CPP_COMMIT,
                    "import_probe": (probe.stdout + probe.stderr)[-1500:],
                    "pip_freeze": freeze.stdout.splitlines() if freeze.returncode == 0 else None,
                    "pip_freeze_sha256": hashlib.sha256(freeze.stdout.encode()).hexdigest() if freeze.returncode == 0 else None,
                    "returncode": freeze.returncode, "certification": "NOT_GRANTED",
                }
                _atomic(state_dir / "cajita_converter_environment.json", manifest)
                lane["stage"] = "DRY_RUN"
                lane["environment_manifest"] = str(state_dir / "cajita_converter_environment.json")
            lane["job"] = None
            lane["last_progress_utc"] = utc_now()
            _atomic(lane_path, lane)
            return {"status": "CAJITA_CONVERTER_ENVIRONMENT_RECONCILED" if lane["stage"] == "DRY_RUN" else "CAJITA_ENV_IMPORT_RETRY",
                    "stage": lane["stage"], "did_work": True, "next_action": "Run the pinned converter dry-run before touching model tensors."}
        if stage == "DRY_RUN_RUNNING":
            lane["stage"] = "CONVERT"
        elif stage == "CONVERSION_RUNNING":
            output = pathlib.Path(lane["bf16_output"])
            if not output.is_file() or output.stat().st_size < int(lane["model_inventory"]["tensor_total_size_bytes"] * 0.65):
                lane["stage"] = "CONVERT_RETRY"
                lane["last_error"] = {"stage": stage, "reason": "OUTPUT_MISSING_OR_IMPLAUSIBLY_SMALL",
                                      "output_bytes": output.stat().st_size if output.is_file() else None}
            else:
                lane["stage"] = "QUANTIZE"
        elif stage == "QUANTIZATION_RUNNING":
            lane["quantizer_job"] = lane.get("job")
            output = pathlib.Path(lane["q4_output"])
            if not output.is_file() or output.stat().st_size < 1_000_000:
                lane["stage"] = "QUANTIZE_RETRY"
                lane["last_error"] = {"stage": stage, "reason": "QUANTIZED_OUTPUT_MISSING_OR_TOO_SMALL"}
            else:
                lane["stage"] = "HASH_OUTPUT"
        elif stage == "HASH_RUNNING":
            lane["hash_job"] = lane.get("job")
            lane["stage"] = "VALIDATE_HASH"
        lane["job"] = None
        lane["last_progress_utc"] = utc_now()
        _atomic(lane_path, lane)
        return {"status": "CAJITA_STAGE_ADVANCED", "stage": lane["stage"], "did_work": True,
                "next_action": "Continue the next checkpointed Cajita substep."}

    now = dt.datetime.now(dt.timezone.utc)
    next_action = lane.get("next_action_utc")
    if next_action:
        try:
            if _parse_utc(next_action) > now:
                return {"status": "CAJITA_LANE_BACKOFF", "stage": stage, "did_work": False,
                        "next_action_utc": next_action, "next_action": "Respect the bounded lane retry timer; keep the mission service active."}
        except (ValueError, TypeError):
            pass

    model_dir = cajita_root / "6. Sistema Inteligente" / "Análisis Avanzado"
    if stage == "PREFLIGHT":
        inv = _model_inventory(model_dir)
        source_script, quantizer, tool = _source_and_quantizer(state_dir)
        mem = _mem_available_bytes()
        disk = shutil.disk_usage(state_dir)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        lane.update({
            "model_inventory": inv, "toolchain": tool,
            "resource_probe": {"ram_available_bytes": mem, "disk_free_bytes": disk.free,
                               "minimum_conversion_ram_bytes": MIN_CONVERSION_RAM_BYTES,
                               "minimum_conversion_disk_bytes": MIN_CONVERSION_DISK_BYTES},
            "candidate_id": lane.get("candidate_id") or f"QWEN3_ANALISIS_AVANZADO_R1_{stamp}",
            "candidate_dir": str(state_dir / "cajita_candidates" / (lane.get("candidate_id") or f"QWEN3_ANALISIS_AVANZADO_R1_{stamp}")),
            "preflight_at_utc": utc_now(),
        })
        if inv.get("status") != "PASS_MODEL_INVENTORY":
            lane["stage"] = "BLOCKED_MODEL_INVENTORY"
            lane["last_error"] = inv
            event = {"status": lane["stage"], "stage": stage, "did_work": True, "evidence": inv,
                     "next_action": "Reconcile the exact model config/index/shard inventory without editing source weights."}
        elif not source_script or not quantizer:
            lane["stage"] = "BLOCKED_TOOLCHAIN"
            lane["last_error"] = tool
            event = {"status": lane["stage"], "stage": stage, "did_work": True, "evidence": tool,
                     "next_action": "Recover/validate pinned official converter or quantizer; do not substitute an unpinned binary."}
        else:
            lane["stage"] = "PROVISION_ENV"
            event = {"status": "CAJITA_PREFLIGHT_PASS", "stage": stage, "did_work": True,
                     "model_id": inv["model_id"], "tensor_total_size_bytes": inv["tensor_total_size_bytes"],
                     "shard_count": inv["shard_count"], "toolchain": tool,
                     "ram_available_bytes": mem, "disk_free_bytes": disk.free,
                     "candidate_id": lane["candidate_id"],
                     "next_action": "Provision a dedicated CPU converter environment from the pinned source requirements."}
        lane["last_progress_utc"] = utc_now()
        lane["next_action_utc"] = None
        _atomic(lane_path, lane)
        return event

    if stage == "PROVISION_ENV":
        source = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699"
        requirements = source / "requirements" / "requirements-convert_hf_to_gguf.txt"
        rev = subprocess.run(["git", "-C", str(source), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=15, check=False)
        if rev.returncode != 0 or rev.stdout.strip() != EXPECTED_LLAMA_CPP_COMMIT or not requirements.is_file():
            lane["stage"] = "BLOCKED_TOOLCHAIN"
            lane["last_error"] = {"status": "BLOCKED_PINNED_REQUIREMENTS_OR_SOURCE", "commit": rev.stdout.strip(),
                                  "requirements_exists": requirements.is_file()}
            lane["last_progress_utc"] = utc_now()
            _atomic(lane_path, lane)
            return {"status": lane["stage"], "stage": stage, "did_work": True, "evidence": lane["last_error"],
                    "next_action": "Resolve the pinned source/dependency manifest mismatch; never install from an unverified source."}
        venv_dir = state_dir / "tools" / "venvs" / "llama-cpp-b10819-py313"
        vpy = venv_dir / "bin" / "python"
        venv_dir.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not vpy.is_file():
            created = subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], capture_output=True, text=True, timeout=120, check=False)
            if created.returncode != 0:
                count = int(lane.get("venv_create_attempts", 0)) + 1
                lane["venv_create_attempts"] = count
                lane["last_error"] = {"status": "BLOCKED_VENV_CREATE", "attempt": count, "returncode": created.returncode, "stderr": created.stderr[-1600:]}
                lane["stage"] = "BLOCKED_VENV_CREATE" if count >= 2 else "PROVISION_ENV"
                lane["next_action_utc"] = (now + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
                lane["attempts"].append(lane["last_error"])
                _atomic(lane_path, lane)
                return {"status": "CAJITA_VENV_CREATE_RETRY" if count < 2 else "BLOCKED_VENV_CREATE",
                        "stage": lane["stage"], "did_work": True,
                        "next_action": "The isolated venv creation failed twice; preserve the cause and route to a scoped interpreter/dependency repair instead of blind repetition."}
        pyver_result = subprocess.run(
            [str(vpy), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
            capture_output=True, text=True, timeout=15, check=False,
        )
        if pyver_result.returncode != 0:
            lane["stage"] = "BLOCKED_PYTHON_VERSION_PROBE"
            lane["last_error"] = {"returncode": pyver_result.returncode, "stderr": pyver_result.stderr[-1200:]}
            lane["last_progress_utc"] = utc_now()
            _atomic(lane_path, lane)
            return {"status": lane["stage"], "stage": stage, "did_work": True,
                    "next_action": "Repair the isolated Python interpreter; do not repeat dependency installation without a valid version probe."}
        try:
            runtime_requirements, requirement_profile = _resolve_runtime_requirements(
                state_dir, source, pyver_result.stdout.strip()
            )
        except Exception as exc:
            lane["stage"] = "BLOCKED_RUNTIME_REQUIREMENTS_PROFILE"
            lane["last_error"] = {"error_type": type(exc).__name__, "error": str(exc)[:1200]}
            lane["last_progress_utc"] = utc_now()
            _atomic(lane_path, lane)
            return {"status": lane["stage"], "stage": stage, "did_work": True,
                    "evidence": lane["last_error"],
                    "next_action": "Reconcile the pinned source compatibility metadata before retrying installation."}
        probe = subprocess.run([str(vpy), "-c", "import torch,transformers,gguf,numpy; print('torch='+torch.__version__); print('transformers='+transformers.__version__); print('numpy='+numpy.__version__)"], capture_output=True, text=True, timeout=60, check=False)
        if probe.returncode == 0:
            lane["venv_python"] = str(vpy)
            lane["stage"] = "DRY_RUN"
            lane["last_progress_utc"] = utc_now()
            lane["next_action_utc"] = None
            _atomic(lane_path, lane)
            return {"status": "CAJITA_CONVERTER_ENV_ALREADY_READY", "stage": stage, "did_work": True,
                    "next_action": "Run pinned converter dry-run."}
        outputs.mkdir(parents=True, exist_ok=True, mode=0o700)
        install_env = os.environ.copy()
        install_env.update({"PIP_NO_CACHE_DIR": "1", "PIP_DISABLE_PIP_VERSION_CHECK": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        install_attempt = int(lane.get("env_install_attempts", 0)) + 1
        lane["env_install_attempts"] = install_attempt
        if requirement_profile.get("compatibility_override"):
            pyq = shlex.quote(str(vpy))
            rq = shlex.quote(str(runtime_requirements))
            shell_command = (
                "set -e\n"
                + pyq + " -m pip install --no-cache-dir --prefer-binary --disable-pip-version-check "
                "--index-url https://download.pytorch.org/whl/cpu 'torch==2.11.0'\n"
                + pyq + " -m pip install --no-cache-dir --prefer-binary --disable-pip-version-check -r " + rq + "\n"
            )
            install_argv = ["/bin/bash", "-lc", shell_command]
        else:
            install_argv = [str(vpy), "-m", "pip", "install", "--no-cache-dir", "--prefer-binary",
                            "--disable-pip-version-check", "-r", str(runtime_requirements)]
        job = _spawn_receipted_job(
            install_argv, source, install_env, outputs, "CAJITA_CONVERTER_ENV_INSTALL",
        )
        lane.update({"stage": "ENV_INSTALL_RUNNING", "venv_python": str(vpy), "job": job,
                     "requirements_path": str(requirements), "requirements_sha256": _sha256(requirements),
                     "runtime_requirements_path": str(runtime_requirements),
                     "runtime_requirements_sha256": _sha256(runtime_requirements),
                     "requirements_profile": requirement_profile,
                     "install_attempt": install_attempt,
                     "next_action_utc": None, "last_progress_utc": utc_now()})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_CONVERTER_ENV_INSTALL_STARTED", "stage": stage, "did_work": True,
                "job": job, "requirements_sha256": lane["requirements_sha256"],
                "next_action": "Let the isolated CPU requirements install finish; the original models are not loaded or modified."}

    if stage == "PROVISION_ENV_FALLBACK":
        if lane.get("fallback_environment_failed") or int(lane.get("fallback_env_install_attempts", 0)) >= 1:
            lane["stage"] = "BLOCKED_ENVIRONMENT_PROVISIONING"
            lane["last_error"] = lane.get("last_error") or {"status": "ALTERNATIVE_ENVIRONMENT_INSTALL_EXHAUSTED"}
            lane["next_action_utc"] = (now + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
            _atomic(lane_path, lane)
            return {"status": "BLOCKED_ENVIRONMENT_PROVISIONING", "stage": lane["stage"], "did_work": True,
                    "next_action": "The primary and one alternative installer route failed; preserve logs and wait for a changed dependency/resource premise rather than looping."}
        vpy = pathlib.Path(lane.get("venv_python", ""))
        if not vpy.is_file():
            lane["stage"] = "BLOCKED_ENVIRONMENT_PROVISIONING"
            lane["last_error"] = {"status": "ALTERNATIVE_INSTALLER_NO_VENV", "path": str(vpy)}
            _atomic(lane_path, lane)
            return {"status": lane["stage"], "stage": stage, "did_work": True,
                    "next_action": "Repair the isolated Python environment before attempting converter installation."}
        source = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699"
        runtime_requirements = pathlib.Path(lane.get("runtime_requirements_path", ""))
        if not runtime_requirements.is_file():
            try:
                pyver = subprocess.run(
                    [str(vpy), "-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"],
                    capture_output=True, text=True, timeout=15, check=False,
                )
                if pyver.returncode != 0:
                    raise RuntimeError("ALTERNATIVE_PYTHON_VERSION_PROBE_FAILED")
                runtime_requirements, requirement_profile = _resolve_runtime_requirements(state_dir, source, pyver.stdout.strip())
                lane["runtime_requirements_path"] = str(runtime_requirements)
                lane["runtime_requirements_sha256"] = _sha256(runtime_requirements)
                lane["requirements_profile"] = requirement_profile
            except Exception as exc:
                lane["stage"] = "BLOCKED_RUNTIME_REQUIREMENTS_PROFILE"
                lane["last_error"] = {"error_type": type(exc).__name__, "error": str(exc)[:1200]}
                _atomic(lane_path, lane)
                return {"status": lane["stage"], "stage": stage, "did_work": True,
                        "next_action": "Resolve runtime compatibility metadata before dependency fallback."}
        pyq = shlex.quote(str(vpy))
        rq = shlex.quote(str(runtime_requirements))
        alternative = (
            "set -e\n"
            + pyq + " -m pip install --no-cache-dir --disable-pip-version-check --only-binary=:all: "
            "--index-url https://download.pytorch.org/whl/cpu 'torch==2.11.0'\n"
            + pyq + " -m pip install --no-cache-dir --disable-pip-version-check --only-binary=:all: -r " + rq + "\n"
        )
        job = _spawn_receipted_job(["/bin/bash", "-lc", alternative], source, os.environ.copy(),
                                   outputs, "CAJITA_CONVERTER_ENV_FALLBACK")
        lane["fallback_env_install_attempts"] = int(lane.get("fallback_env_install_attempts", 0)) + 1
        lane.update({"stage": "ENV_INSTALL_FALLBACK_RUNNING", "job": job,
                     "last_progress_utc": utc_now(), "next_action_utc": None})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_CONVERTER_ENV_FALLBACK_STARTED", "stage": stage, "did_work": True,
                "job": job, "next_action": "Install pinned CPU PyTorch separately, then the converter's declared dependencies; do not load or mutate the model during installation."}

    if stage == "DRY_RUN":
        source_script = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699" / "convert_hf_to_gguf.py"
        vpy = pathlib.Path(lane["venv_python"])
        candidate_dir = pathlib.Path(lane["candidate_dir"])
        candidate_dir.mkdir(parents=True, exist_ok=False, mode=0o700) if not candidate_dir.exists() else None
        bf16 = candidate_dir / "qwen3-analysis-advanced-bf16.gguf"
        cmd = [str(vpy), str(source_script), "--outtype", "bf16", "--use-temp-file",
               "--dry-run", "--outfile", str(bf16), str(model_dir)]
        temp_dir = candidate_dir / "converter_tmp"
        env = _bounded_compute_env(os.environ.copy(), temp_dir=temp_dir)
        env.update({"PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        job = _spawn_receipted_job(cmd, source_script.parent, env, outputs, "CAJITA_QWEN3_DRY_RUN")
        lane.update({"stage": "DRY_RUN_RUNNING", "job": job, "bf16_output": str(bf16),
                     "last_progress_utc": utc_now(), "next_action_utc": None})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_QWEN3_DRY_RUN_STARTED", "stage": stage, "did_work": True,
                "candidate_id": lane["candidate_id"], "job": job,
                "next_action": "Validate the pinned converter against the actual local Qwen3 inventory."}

    if stage in {"CONVERT", "CONVERT_RETRY"}:
        resource_failure = lane.get("conversion_resource_failure")
        recovery_evidence = lane.get("resource_recovery_evidence")
        if resource_failure and not isinstance(recovery_evidence, dict):
            lane["stage"] = "BLOCKED_CONVERSION_RESOURCE"
            lane["next_action_utc"] = None
            _atomic(lane_path, lane)
            return {"status": "BLOCKED_CONVERSION_RESOURCE", "stage": stage, "did_work": True,
                    "evidence": resource_failure,
                    "next_action": "Require a verified resource change and hash-bound recovery receipt; do not repeat the same OOM attempt."}
        if resource_failure:
            receipt = pathlib.Path(str(recovery_evidence.get("receipt_path") or ""))
            receipt_row = _load(receipt, {}) if receipt.is_file() else {}
            try:
                active_swap_paths = {line.split()[0] for line in pathlib.Path("/proc/swaps").read_text().splitlines()[1:] if line.split()}
            except OSError:
                active_swap_paths = set()
            swap_path_active = str(receipt_row.get("swap_path") or "") in active_swap_paths
            resource_valid = (
                receipt.is_file()
                and _sha256(receipt) == recovery_evidence.get("receipt_sha256")
                and receipt_row.get("schema") == "CUSTOSZ_CAJITA_RESOURCE_RECOVERY/1.0"
                and receipt_row.get("status") == "RESOURCE_RECOVERY_VERIFIED"
                and receipt_row.get("mission_sha256") == mission_sha256
                and receipt_row.get("swap_active") is True
                and swap_path_active
                and int(receipt_row.get("swap_bytes", 0)) >= 4 * 1024**3
                and int(receipt_row.get("memory_high_bytes", 0)) >= 2560 * 1024**2
                and int(receipt_row.get("memory_max_bytes", 0)) == 3 * 1024**3
                and receipt_row.get("source_model_weights_modified") is False
                and receipt_row.get("no_competing_conversion") is True
            )
            if not resource_valid:
                lane["stage"] = "BLOCKED_CONVERSION_RESOURCE"
                lane["last_error"] = {"status": "BLOCKED_RESOURCE_RECOVERY_RECEIPT_INVALID", "receipt_path": str(receipt)}
                _atomic(lane_path, lane)
                return {"status": "BLOCKED_CONVERSION_RESOURCE", "stage": stage, "did_work": True,
                        "evidence": lane["last_error"], "next_action": "Resource recovery receipt failed its hash, mission, swap, or memory-limit checks; refuse retry."}
        mem = _mem_available_bytes()
        free = shutil.disk_usage(state_dir).free
        required_ram = _minimum_conversion_ram_bytes(bool(resource_failure and resource_valid))
        if mem < required_ram or free < MIN_CONVERSION_DISK_BYTES:
            lane["resource_wait"] = {"ram_available_bytes": mem, "disk_free_bytes": free,
                                     "minimum_ram_bytes": required_ram, "minimum_disk_bytes": MIN_CONVERSION_DISK_BYTES,
                                     "observed_at_utc": utc_now()}
            lane["next_action_utc"] = (now + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
            _atomic(lane_path, lane)
            return {"status": "CAJITA_WAITING_FOR_RESOURCE", "stage": stage, "did_work": False,
                    "evidence": lane["resource_wait"], "next_action": "Wait for resource recovery; retry safely without loading all shards into RAM."}
        candidate_dir = pathlib.Path(lane["candidate_dir"])
        candidate_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        attempt = int(lane.get("conversion_attempts", 0)) + 1
        lane["conversion_attempts"] = attempt
        output = candidate_dir / ("qwen3-analysis-advanced-bf16.gguf" if attempt == 1 else f"qwen3-analysis-advanced-bf16-R{attempt}.gguf")
        source_script = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699" / "convert_hf_to_gguf.py"
        cmd = _build_conversion_command(lane, source_script, model_dir, output, attempt)
        temp_dir = candidate_dir / "converter_tmp"
        env = _bounded_compute_env(os.environ.copy(), temp_dir=temp_dir)
        env.update({"PYTHONUNBUFFERED": "1", "PYTHONDONTWRITEBYTECODE": "1"})
        job = _spawn_receipted_job(cmd, source_script.parent, env, outputs, "CAJITA_QWEN3_CONVERT")
        lane.update({"stage": "CONVERSION_RUNNING", "job": job, "bf16_output": str(output),
                     "last_progress_utc": utc_now(), "next_action_utc": None})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_QWEN3_CONVERSION_STARTED", "stage": stage, "did_work": True,
                "candidate_id": lane["candidate_id"], "output_path": str(output), "attempt": attempt,
                "job": job, "next_action": "Monitor the hash-bound converter receipt; source model shards remain read-only."}

    if stage in {"QUANTIZE", "QUANTIZE_RETRY"}:
        bf16 = pathlib.Path(lane["bf16_output"])
        if not bf16.is_file():
            lane["stage"] = "CONVERT_RETRY"
            lane["last_error"] = {"status": "BLOCKED_BF16_SOURCE_MISSING", "path": str(bf16)}
            _atomic(lane_path, lane)
            return {"status": "CAJITA_QUANTIZER_SOURCE_REPAIR", "stage": stage, "did_work": True,
                    "next_action": "Return to converter fallback; do not quantize a missing/incomplete file."}
        _, quantizer, tool = _source_and_quantizer(state_dir)
        if not quantizer:
            lane["stage"] = "BLOCKED_TOOLCHAIN"
            lane["last_error"] = tool
            _atomic(lane_path, lane)
            return {"status": "CAJITA_QUANTIZER_TOOLCHAIN_BLOCKED", "stage": stage, "did_work": True,
                    "evidence": tool, "next_action": "Resolve the pinned quantizer binary before converting further."}
        candidate_dir = pathlib.Path(lane["candidate_dir"])
        attempt = int(lane.get("quantization_attempts", 0)) + 1
        lane["quantization_attempts"] = attempt
        out = candidate_dir / ("qwen3-analysis-advanced-Q4_K_M.gguf" if attempt == 1 else f"qwen3-analysis-advanced-Q4_0-R{attempt}.gguf")
        qtype = "Q4_K_M" if attempt == 1 else "Q4_0"
        env = _bounded_compute_env(os.environ.copy())
        runtime_dir = str(quantizer.parent)
        env["LD_LIBRARY_PATH"] = runtime_dir + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        job = _spawn_receipted_job([str(quantizer), str(bf16), str(out), qtype, "1"],
                                   quantizer.parent, env, outputs, "CAJITA_QWEN3_QUANTIZE")
        lane.update({"stage": "QUANTIZATION_RUNNING", "job": job, "q4_output": str(out),
                     "quantization_type": qtype, "last_progress_utc": utc_now(), "next_action_utc": None})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_QWEN3_QUANTIZATION_STARTED", "stage": stage, "did_work": True,
                "candidate_id": lane["candidate_id"], "input_path": str(bf16), "output_path": str(out),
                "quantization_type": qtype, "job": job,
                "next_action": "Monitor the quantizer receipt; output remains a versioned candidate, not a certified distribution."}

    if stage == "HASH_OUTPUT":
        q4 = pathlib.Path(lane.get("q4_output", ""))
        if not q4.is_file() or q4.stat().st_size <= 0:
            lane["stage"] = "QUANTIZE_RETRY"
            lane["last_error"] = {"status": "BLOCKED_QUANTIZED_OUTPUT_MISSING", "path": str(q4)}
            _atomic(lane_path, lane)
            return {"status": "CAJITA_HASH_GATE_RETRY_QUANTIZATION", "stage": stage, "did_work": True,
                    "next_action": "Retry with the lower-resource Q4_0 fallback; preserve incomplete artifacts."}
        job = _spawn_receipted_job([sys.executable, "-B", "-c",
            "import hashlib,json,pathlib,sys; p=pathlib.Path(sys.argv[1]); h=hashlib.sha256(); "
            "f=p.open('rb'); "
            "[(h.update(b)) for b in iter(lambda:f.read(1024*1024),b'')]; "
            "print(json.dumps({'path':str(p),'bytes':p.stat().st_size,'sha256':h.hexdigest()}))",
            str(q4)], q4.parent, os.environ.copy(), outputs, "CAJITA_QWEN3_HASH")
        lane.update({"stage": "HASH_RUNNING", "job": job, "last_progress_utc": utc_now()})
        _atomic(lane_path, lane)
        return {"status": "CAJITA_QWEN3_OUTPUT_HASH_STARTED", "stage": stage, "did_work": True,
                "job": job, "next_action": "Hash candidate in a bounded background process before writing its report."}

    if stage == "VALIDATE_HASH":
        job = lane.get("hash_job") or {}
        receipt = _load(pathlib.Path(job.get("receipt_path", "")), {}) if job.get("receipt_path") else {}
        log_path = pathlib.Path(job.get("log_path", "")) if job.get("log_path") else None
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines() if log_path and log_path.is_file() else []
            hash_row = json.loads(lines[-1]) if lines else {}
        except (OSError, ValueError, TypeError):
            hash_row = {}
        q4 = pathlib.Path(lane.get("q4_output", ""))
        source_before = lane["model_inventory"]["shards"]
        source_after = []
        unchanged = True
        for row in source_before:
            p = pathlib.Path(lane["model_inventory"]["model_dir"]) / row["name"]
            if not p.is_file():
                unchanged = False
                source_after.append({"name": row["name"], "exists": False})
            else:
                st = p.stat()
                current = {"name": row["name"], "bytes": st.st_size, "mtime_ns": st.st_mtime_ns}
                source_after.append(current)
                if current["bytes"] != row["bytes"] or current["mtime_ns"] != row["mtime_ns"]:
                    unchanged = False
        quantizer_job = lane.get("quantizer_job") or {}
        quantizer_receipt = _load(pathlib.Path(quantizer_job["receipt_path"]), {}) if quantizer_job.get("receipt_path") else {}
        report = {
            "schema": "CUSTOSZ_CAJITA_QWEN3_QUANTIZATION_REPORT/1.0",
            "captured_at_utc": utc_now(), "mission_sha256": mission_sha256,
            "candidate_id": lane["candidate_id"], "model_id": lane["model_inventory"]["model_id"],
            "source_model_dir": lane["model_inventory"]["model_dir"],
            "source_config_sha256": lane["model_inventory"]["config_sha256"],
            "source_index_sha256": lane["model_inventory"]["index_sha256"],
            "source_tensor_total_size_bytes": lane["model_inventory"]["tensor_total_size_bytes"],
            "source_shard_inventory_before": source_before, "source_shard_inventory_after": source_after,
            "source_shards_unchanged_by_size_and_mtime": unchanged,
            "quantized_output_path": str(q4), "quantized_output_bytes": q4.stat().st_size if q4.is_file() else None,
            "quantized_output_sha256": hash_row.get("sha256"), "quantization_type": lane.get("quantization_type"),
            "quantizer_job": quantizer_job, "quantizer_receipt": quantizer_receipt,
            "hash_job": job, "hash_receipt": receipt, "mission_controls": lane.get("mission_controls"),
            "certification": "NOT_GRANTED", "independent_quality_validation": "PENDING",
            "status": "QUANTIZED_CANDIDATE_READY_FOR_VALIDATION" if (
                q4.is_file() and hash_row.get("sha256") and unchanged
                and quantizer_receipt.get("returncode") == 0 and receipt.get("returncode") == 0
            ) else "BLOCKED_QUANTIZATION_OUTPUT_OR_SOURCE_INTEGRITY",
            "mission_completion_claim": False,
        }
        report_path = state_dir / "worker_outputs" / ("CAJITA_QWEN3_QUANTIZATION_REPORT_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
        _atomic(report_path, report)
        lane["stage"] = "COMPLETE" if report["status"] == "QUANTIZED_CANDIDATE_READY_FOR_VALIDATION" else "QUANTIZE_RETRY"
        lane["report_path"] = str(report_path)
        lane["report_sha256"] = _sha256(report_path)
        lane["last_progress_utc"] = utc_now()
        _atomic(lane_path, lane)
        return {"status": report["status"], "stage": stage, "did_work": True,
                "report_path": str(report_path), "report_sha256": lane["report_sha256"],
                "candidate_id": lane["candidate_id"],
                "next_action": "Run independent functional/quality validation before any integration or certification."}

    if stage == "COMPLETE":
        return {"status": "CAJITA_CANDIDATE_READY_VALIDATION_PENDING", "stage": stage, "did_work": False,
                "candidate_id": lane.get("candidate_id"), "report_path": lane.get("report_path"),
                "report_sha256": lane.get("report_sha256"),
                "next_action": "Do not rerun quantization; perform independent candidate quality and size validation."}
    if stage.startswith("BLOCKED_"):
        # Never dead-end: retain the defect and route the next attempt through a distinct, bounded repair branch.
        if stage == "BLOCKED_TOOLCHAIN":
            source_script = state_dir / "tools" / "llama.cpp-source-b10819-6a1a922d2699" / "convert_hf_to_gguf.py"
            quantizer = sorted((state_dir / "tools").glob("llama-b10819_*/llama-quantize"))
            if source_script.is_file() and quantizer:
                lane["stage"] = "PROVISION_ENV"
                lane["next_action_utc"] = (now + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
                _atomic(lane_path, lane)
                return {"status": "CAJITA_TOOLCHAIN_REPAIR_QUEUED", "stage": stage, "did_work": True,
                        "next_action": "Retry pinned environment/toolchain reconciliation after bounded backoff."}
        lane["next_action_utc"] = (now + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
        _atomic(lane_path, lane)
        return {"status": stage, "stage": stage, "did_work": False, "evidence": lane.get("last_error"),
                "next_action": "Keep collecting evidence and retry through the configured repair route; do not mark this lane complete."}

    return {"status": "CAJITA_LANE_UNRECOGNIZED_STAGE", "stage": stage, "did_work": False,
            "next_action": "Reconcile the versioned lane checkpoint before any mutation."}

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]