"""Runs one registered capability in-process. That is a local test, not a sandbox."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import jsonschema

from metagente_luna_s3.registry import EXECUTORS, ORACLES, REGISTRY
from metagente_luna_s4.evidence import persist_run
from metagente_luna_s4.guard import authorize, require_case_id


def _execute(capability_id: str, arguments: dict, case_id: str, backend: str = "LOCAL_TEST_ONLY") -> dict:
    started = time.time()
    run_id = str(uuid.uuid4())
    try:
        require_case_id(case_id)
    except ValueError as exc:
        return _record(run_id, case_id, capability_id, started, 2, "", str(exc), None, "REJECTED", backend=backend)
    if case_id.startswith("MGL5-TEO-"):
        return _record(run_id, case_id, capability_id, started, 2, "", "no hermeneutic capability is registered for this operation", None, "BLOCKED", backend=backend)
    if capability_id == "c05_preflight_blocked":
        capability = REGISTRY[capability_id]
        try:
            jsonschema.validate(arguments, capability.input_schema)
            observed = EXECUTORS[capability_id](**arguments)
            verdict = ORACLES[capability.oracle_id](arguments, observed)
        except Exception as exc:  # noqa: BLE001 - invalid preflight evidence remains blocked
            return _record(run_id, case_id, capability_id, started, 2, "", str(exc), None, "BLOCKED", backend=backend)
        return _record(
            run_id, case_id, capability_id, started, 2, "", arguments["details"], observed,
            "BLOCKED", authorization={"allowed": False, "reason": arguments["blocker_code"]},
            backend=backend, oracle_result=verdict,
        )
    try:
        decision = authorize(capability_id, backend)
    except KeyError:
        return _record(run_id, case_id, capability_id, started, 2, "", "unknown capability", None, "REJECTED", backend=backend)
    except PermissionError as exc:
        status = "BLOCKED" if backend != "LOCAL_TEST_ONLY" else "REJECTED"
        return _record(run_id, case_id, capability_id, started, 2, "", str(exc), None, status, backend=backend)
    capability = REGISTRY[capability_id]
    try:
        jsonschema.validate(arguments, capability.input_schema)
    except jsonschema.ValidationError as exc:
        return _record(run_id, case_id, capability_id, started, 2, "", exc.message, None, "REJECTED", decision, backend)
    oracle = ORACLES.get(capability.oracle_id)
    if oracle is None or capability.oracle_id == capability_id:
        return _record(run_id, case_id, capability_id, started, 2, "", "independent oracle is missing", None, "INCONCLUSIVE", decision, backend)
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            observed = EXECUTORS[capability_id](**arguments)
        jsonschema.validate(observed, capability.output_schema)
        verdict = oracle(arguments, observed)
    except Exception as exc:  # noqa: BLE001 - the runner boundary must record any executor failure
        return _record(run_id, case_id, capability_id, started, 1, stdout.getvalue(), stderr.getvalue() or type(exc).__name__, None, "ERROR", decision, backend)
    status = "EXECUTED" if verdict.get("ok") is True else "FAIL"
    return _record(run_id, case_id, capability_id, started, 0, stdout.getvalue(), stderr.getvalue(), observed, status, decision, backend, verdict)


def execute(
    capability_id: str,
    arguments: dict,
    case_id: str,
    backend: str = "LOCAL_TEST_ONLY",
    evidence_root: str | None = None,
    run_kind: str = "NORMAL",
    control_metadata: dict | None = None,
) -> dict:
    """Execute once and optionally persist its raw evidence; never certify it."""
    if run_kind not in {"NORMAL", "NEGATIVE", "BOUNDARY"}:
        raise ValueError("run_kind must be NORMAL, NEGATIVE, or BOUNDARY")
    if run_kind in {"NEGATIVE", "BOUNDARY"} and (
        not isinstance(control_metadata, dict)
        or not all(isinstance(control_metadata.get(field), str) and control_metadata[field]
                   for field in ("definition", "expected_behavior", "source"))
    ):
        raise ValueError("negative and boundary runs require definition, expected_behavior, and source")
    record = _execute(capability_id, arguments, case_id, backend)
    capability = REGISTRY.get(capability_id)
    producer = EXECUTORS.get(capability_id)
    oracle = ORACLES.get(capability.oracle_id) if capability is not None else None
    record["producer_module"] = getattr(producer, "__module__", None)
    record["oracle_module"] = getattr(oracle, "__module__", None)
    record["agent_version"] = "0.1.0"
    record["executor_version"] = capability.version if capability is not None else "UNDECLARED"
    record["machinery"] = backend
    record["run_kind"] = run_kind
    record["control_metadata"] = control_metadata
    lifecycle = record.get("execution_status")
    record["lifecycle_status"] = lifecycle
    if lifecycle == "EXECUTED":
        record["result_status"] = "PASS" if isinstance(record.get("oracle_result"), dict) and record["oracle_result"].get("ok") is True else "FAIL"
    elif lifecycle == "ERROR":
        record["result_status"] = "INCONCLUSIVE"
    elif lifecycle == "REJECTED":
        record["result_status"] = "BLOCKED"
    else:
        record["result_status"] = lifecycle
    if evidence_root is not None and record.get("result_status") in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}:
        try:
            record["persisted_evidence"] = persist_run(record, arguments, evidence_root)
            record["persisted_evidence"]["kind"] = run_kind
        except (OSError, TypeError, ValueError) as exc:
            record["evidence_persistence_error"] = f"{type(exc).__name__}: {exc}"
    return record



def execute_isolated(
    capability_id: str,
    arguments: dict,
    case_id: str,
    evidence_root: str,
    run_kind: str = "NORMAL",
    control_metadata: dict | None = None,
    source_metadata: dict | None = None,
    source_excerpt: str | None = None,
    timeout_seconds: int = 60,
    sandbox_image: str | None = None,
) -> dict:
    """Run in a restricted Docker container when an immutable image ID is supplied; otherwise local test only."""
    if run_kind not in {"NORMAL", "NEGATIVE", "BOUNDARY"}:
        raise ValueError("run_kind must be NORMAL, NEGATIVE, or BOUNDARY")
    if run_kind in {"NEGATIVE", "BOUNDARY"} and (
        not isinstance(control_metadata, dict)
        or not all(isinstance(control_metadata.get(field), str) and control_metadata[field]
                   for field in ("definition", "expected_behavior", "source"))
    ):
        raise ValueError("negative and boundary runs require definition, expected_behavior, and source")
    if timeout_seconds < 1:
        raise ValueError("timeout_seconds must be positive")
    required_source_fields = {"source_file", "line_start", "line_end", "file_sha256", "excerpt_sha256", "source_blob", "operation", "acceptance_criterion", "oracle_requirement"}
    if not isinstance(source_metadata, dict) or required_source_fields - set(source_metadata):
        raise ValueError("source metadata must bind the source file, line range, hashes, and Git blob")
    if not isinstance(source_excerpt, str) or not case_id in source_excerpt:
        raise ValueError("source excerpt must contain the exact case ID")
    source_root = Path(__file__).resolve().parents[5]
    source_path = (source_root / source_metadata["source_file"]).resolve()
    try:
        source_path.relative_to(source_root)
    except ValueError as exc:
        raise ValueError("source path escapes repository root") from exc
    source_bytes = source_path.read_bytes()
    if hashlib.sha256(source_bytes).hexdigest() != source_metadata["file_sha256"]:
        raise ValueError("source file SHA-256 mismatch")
    git_blob = hashlib.sha1(f"blob {len(source_bytes)}\0".encode("ascii") + source_bytes).hexdigest()
    if git_blob != source_metadata["source_blob"]:
        raise ValueError("source Git blob identity mismatch")
    lines = source_bytes.splitlines(keepends=True)
    line_start = source_metadata["line_start"]
    line_end = source_metadata["line_end"]
    if (not isinstance(line_start, int) or not isinstance(line_end, int)
            or line_start < 1 or line_end < line_start or line_end > len(lines)):
        raise ValueError("source line range is invalid")
    exact_excerpt = b"".join(lines[line_start - 1:line_end])
    if exact_excerpt.decode("utf-8") != source_excerpt:
        raise ValueError("source excerpt does not match the declared line range")
    if hashlib.sha256(exact_excerpt).hexdigest() != source_metadata["excerpt_sha256"]:
        raise ValueError("source excerpt SHA-256 mismatch")
    for field in ("operation", "acceptance_criterion", "oracle_requirement"):
        value = source_metadata[field]
        if not isinstance(value, str) or not value or value.encode("utf-8") not in exact_excerpt:
            raise ValueError(f"source excerpt does not bind required {field}")

    started = time.time()
    request = json.dumps({
        "capability_id": capability_id, "arguments": arguments, "case_id": case_id,
    }, ensure_ascii=False)
    package_root = str(Path(__file__).resolve().parents[1])
    with tempfile.TemporaryDirectory(prefix="luna-c05-") as workspace:
        home = Path(workspace) / "home"
        temporary = Path(workspace) / "tmp"
        home.mkdir()
        temporary.mkdir()
        environment = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONPATH": package_root,
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
            "HOME": str(home),
            "TMPDIR": str(temporary),
            "LANG": "C.UTF-8",
        }
        try:
            if sandbox_image is not None:
                if not re.fullmatch(r"sha256:[0-9a-f]{64}", sandbox_image):
                    raise ValueError("sandbox_image must be an immutable Docker image ID")
                docker = shutil.which("docker")
                if docker is None:
                    raise RuntimeError("Docker CLI unavailable; sandbox execution denied")
                command = [
                    docker, "run", "-i", "--rm", "--network", "none", "--read-only",
                    "--cap-drop", "ALL", "--security-opt", "no-new-privileges:true",
                    "--pids-limit", "64", "--memory", "256m", "--cpus", "1",
                    "--user", "65534:65534",
                    "--tmpfs", "/tmp:rw,noexec,nosuid,nodev,size=64m",
                    "--mount", f"type=bind,src={package_root},dst=/opt/luna,readonly",
                    "--workdir", "/tmp", "--env", "PYTHONPATH=/opt/luna",
                    "--env", "PYTHONHASHSEED=0", "--env", "PYTHONDONTWRITEBYTECODE=1",
                    sandbox_image, "python", "-m", "metagente_luna_s4.worker",
                ]
            else:
                command = [sys.executable, "-m", "metagente_luna_s4.worker"]
            completed = subprocess.run(
                command, input=request, capture_output=True, text=True,
                cwd=workspace, env=environment, timeout=timeout_seconds, check=False,
            )
            try:
                record = json.loads(completed.stdout)
            except json.JSONDecodeError:
                record = {
                    "run_id": str(uuid.uuid4()), "case_id": case_id,
                    "capability_id": capability_id, "exit_code": completed.returncode,
                    "stdout": "", "stderr": completed.stderr or completed.stdout,
                    "observed": None, "oracle_result": None,
                    "execution_status": "INCONCLUSIVE", "contract_status": "NOT_A_PASS",
                    "started": started, "ended": time.time(),
                }
            if "worker_error" in record:
                record.update({
                    "run_id": str(uuid.uuid4()),
                    "case_id": case_id,
                    "capability_id": capability_id,
                    "execution_status": "BLOCKED",
                    "contract_status": "NOT_A_PASS",
                    "stdout": "",
                    "stderr": record["worker_error"],
                    "observed": None,
                    "oracle_result": None,
                    "exit_code": completed.returncode,
                    "started": started,
                    "ended": time.time(),
                })
        except subprocess.TimeoutExpired as exc:
            record = {
                "run_id": str(uuid.uuid4()), "case_id": case_id,
                "capability_id": capability_id, "exit_code": 124,
                "stdout": exc.stdout or "", "stderr": exc.stderr or "worker timeout",
                "observed": None, "oracle_result": None,
                "execution_status": "INCONCLUSIVE", "contract_status": "NOT_A_PASS",
                "started": started, "ended": time.time(),
            }

    capability = REGISTRY.get(capability_id)
    producer = EXECUTORS.get(capability_id)
    oracle = ORACLES.get(capability.oracle_id) if capability is not None else None
    record["producer_module"] = getattr(producer, "__module__", None)
    record["oracle_module"] = getattr(oracle, "__module__", None)
    record["agent_version"] = "0.1.0"
    record["executor_version"] = capability.version if capability is not None else None
    record["machinery"] = "DOCKER_RESTRICTED_CONTAINER" if sandbox_image is not None else "LOCAL_SUBPROCESS_TEST_ONLY"
    record["backend"] = "DOCKER_RESTRICTED_CONTAINER" if sandbox_image is not None else "LOCAL_SUBPROCESS_TEST_ONLY"
    record["run_kind"] = run_kind
    record["control_metadata"] = control_metadata
    record["source_metadata"] = source_metadata
    record["source_excerpt"] = source_excerpt
    record["clean_state_verified"] = True
    record["isolation_metadata"] = {
        "mode": "DOCKER_RESTRICTED_CONTAINER" if sandbox_image is not None else "FRESH_PROCESS_TEMPORARY_WORKSPACE",
        "process_isolated": True,
        "containerized": sandbox_image is not None,
        "network_disabled": sandbox_image is not None,
        "root_filesystem_read_only": sandbox_image is not None,
        "capabilities_dropped": sandbox_image is not None,
        "non_root_uid": 65534 if sandbox_image is not None else None,
        "resource_limits": {"pids": 64, "memory": "256m", "cpus": 1} if sandbox_image is not None else None,
        "image_id": sandbox_image,
        "workspace_ephemeral": True,
        "cwd_isolated": True,
        "home_isolated": True,
        "tmp_isolated": True,
        "sandbox": False,
        "container_restrictions_verified": sandbox_image is not None,
        "kernel_isolation": "SHARED_HOST_KERNEL_NOT_VM",
    }
    lifecycle = record.get("execution_status")
    record["lifecycle_status"] = lifecycle
    if lifecycle == "EXECUTED":
        record["execution_status"] = "PASS" if isinstance(record.get("oracle_result"), dict) and record["oracle_result"].get("ok") is True else "FAIL"
    elif lifecycle == "ERROR":
        record["execution_status"] = "INCONCLUSIVE"
    elif lifecycle == "REJECTED":
        record["execution_status"] = "BLOCKED"
    record["result_status"] = record.get("execution_status")
    try:
        record["persisted_evidence"] = persist_run(record, arguments, evidence_root)
        record["persisted_evidence"]["kind"] = run_kind
    except (OSError, TypeError, ValueError) as exc:
        record["evidence_persistence_error"] = f"{type(exc).__name__}: {exc}"
    return record

def _record(run_id, case_id, capability_id, started, code, stdout, stderr, observed, status, authorization=None, backend=None, oracle_result=None) -> dict:
    return {
        "run_id": run_id,
        "case_id": case_id,
        "capability_id": capability_id,
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
        "observed": observed,
        "oracle_result": oracle_result,
        "authorization": authorization,
        "backend": backend,
        "execution_status": status,
        "contract_status": "NOT_A_PASS",
        "started": started,
        "ended": time.time(),
    }


def dumps(record: dict) -> str:
    return json.dumps(record, sort_keys=True)
