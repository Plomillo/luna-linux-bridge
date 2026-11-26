"""Runs one registered capability in-process. That is a local test, not a sandbox."""
from __future__ import annotations

import io
import json
import time
import uuid
from contextlib import redirect_stderr, redirect_stdout

import jsonschema

from metagente_luna_s3.registry import EXECUTORS, ORACLES, REGISTRY
from metagente_luna_s4.guard import authorize, require_case_id


def execute(capability_id: str, arguments: dict, case_id: str, backend: str = "LOCAL_TEST_ONLY") -> dict:
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
