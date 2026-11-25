"""Runs a registered capability. It does not accept source text as code."""
from __future__ import annotations

import io
import json
import time
import uuid
from contextlib import redirect_stderr, redirect_stdout

import jsonschema

from metagente_luna_s3.registry import EXECUTORS, REGISTRY


def execute(capability_id: str, arguments: dict, case_id: str) -> dict:
    started = time.time()
    run_id = str(uuid.uuid4())
    if capability_id not in REGISTRY:
        return _record(run_id, case_id, capability_id, started, 2, "", "unknown capability", None, "REJECTED")
    capability = REGISTRY[capability_id]
    if capability.oracle_id == capability_id:
        return _record(run_id, case_id, capability_id, started, 2, "", "executor cannot be its own oracle", None, "REJECTED")
    try:
        jsonschema.validate(arguments, capability.input_schema)
    except jsonschema.ValidationError as exc:
        return _record(run_id, case_id, capability_id, started, 2, "", exc.message, None, "REJECTED")
    stdout, stderr = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            observed = EXECUTORS[capability_id](**arguments)
        jsonschema.validate(observed, capability.output_schema)
    except Exception as exc:  # noqa: BLE001 - the runner boundary must record any executor failure
        return _record(run_id, case_id, capability_id, started, 1, stdout.getvalue(), stderr.getvalue() or type(exc).__name__, None, "ERROR")
    return _record(run_id, case_id, capability_id, started, 0, stdout.getvalue(), stderr.getvalue(), observed, "EXECUTED")


def _record(run_id, case_id, capability_id, started, code, stdout, stderr, observed, status) -> dict:
    return {
        "run_id": run_id,
        "case_id": case_id,
        "capability_id": capability_id,
        "exit_code": code,
        "stdout": stdout,
        "stderr": stderr,
        "observed": observed,
        "execution_status": status,
        "contract_status": "NOT_A_PASS",
        "started": started,
        "ended": time.time(),
    }


def dumps(record: dict) -> str:
    return json.dumps(record, sort_keys=True)
