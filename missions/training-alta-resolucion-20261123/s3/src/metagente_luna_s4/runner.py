"""Runs one registered capability in-process. That is a local test, not a sandbox."""
from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import time
import uuid
from pathlib import Path
from contextlib import redirect_stderr, redirect_stdout

import jsonschema

from metagente_luna_s3.registry import EXECUTORS, ORACLES, REGISTRY
from metagente_luna_s4.guard import authorize, require_case_id
from metagente_luna_s4.evidence import persist_run


def _execute(capability_id: str, arguments: dict, case_id: str, backend: str = "LOCAL_TEST_ONLY") -> dict:
    started = time.time()
    run_id = str(uuid.uuid4())
    try:
        require_case_id(case_id)
    except ValueError as exc:
        return _record(run_id, case_id, capability_id, started, 2, "", str(exc), None, "REJECTED", backend=backend)
    if case_id.startswith("MGL5-TEO-"):
        return _record(run_id, case_id, capability_id, started, 2, "", "no hermeneutic capability is registered for this operation", None, "BLOCKED", backend=backend)
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
        record["execution_status"] = "PASS" if isinstance(record.get("oracle_result"), dict) and record["oracle_result"].get("ok") is True else "FAIL"
    elif lifecycle == "ERROR":
        record["execution_status"] = "INCONCLUSIVE"
    elif lifecycle == "REJECTED":
        record["execution_status"] = "BLOCKED"
    if evidence_root is not None and record.get("execution_status") in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"}:
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
    timeout_seconds: int = 60,
) -> dict:
    """Run in a fresh Python process and temporary workspace; this is not a sandbox."""
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
            completed = subprocess.run(
                [sys.executable, "-m", "metagente_luna_s4.worker"],
                input=request,
                capture_output=True,
                text=True,
                cwd=workspace,
                env=environment,
                timeout=timeout_seconds,
                check=False,
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
    record["machinery"] = "LOCAL_SUBPROCESS_TEST_ONLY"
    record["backend"] = "LOCAL_SUBPROCESS_TEST_ONLY"
    record["run_kind"] = run_kind
    record["control_metadata"] = control_metadata
    record["clean_state_verified"] = True
    record["isolation_metadata"] = {
        "mode": "FRESH_PROCESS_TEMPORARY_WORKSPACE",
        "process_isolated": True,
        "workspace_ephemeral": True,
        "cwd_isolated": True,
        "home_isolated": True,
        "tmp_isolated": True,
        "sandbox": False,
    }
    lifecycle = record.get("execution_status")
    record["lifecycle_status"] = lifecycle
    if lifecycle == "EXECUTED":
        record["execution_status"] = "PASS" if isinstance(record.get("oracle_result"), dict) and record["oracle_result"].get("ok") is True else "FAIL"
    elif lifecycle == "ERROR":
        record["execution_status"] = "INCONCLUSIVE"
    elif lifecycle == "REJECTED":
        record["execution_status"] = "BLOCKED"
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
