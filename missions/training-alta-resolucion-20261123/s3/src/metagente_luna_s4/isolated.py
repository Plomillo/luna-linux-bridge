"""Runs one case in another process. This is not a container and not a sandbox."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path


def run_bounded(code: str, payload: str, timeout: float) -> dict:
    work = Path(tempfile.mkdtemp(prefix="luna-case-"))
    env = {
        "PATH": os.environ.get("PATH", ""),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "PYTHONDONTWRITEBYTECODE": "1",
        "LC_ALL": "C.UTF-8",
    }
    try:
        completed = subprocess.run(
            [sys.executable, "-c", code],
            input=payload,
            text=True,
            cwd=work,
            env=env,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return {"status": "TIMEOUT", "stdout": exc.stdout or "", "stderr": exc.stderr or "", "exit_code": None, "cwd": str(work)}
    return {
        "status": "FINISHED",
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "exit_code": completed.returncode,
        "cwd": str(work),
    }


_CHILD = (
    "import json,sys\n"
    "from metagente_luna_s4.runner import execute\n"
    "capability, arguments, case_id = json.loads(sys.stdin.read())\n"
    "print(json.dumps(execute(capability, arguments, case_id)))\n"
)


def execute_isolated(capability_id: str, arguments: dict, case_id: str, timeout: float = 10) -> dict:
    outcome = run_bounded(_CHILD, json.dumps([capability_id, arguments, case_id]), timeout)
    outcome["backend"] = "PROCESS_SEPARATION"
    outcome["sandbox"] = False
    outcome["network_restricted"] = False
    outcome["same_user"] = True
    if outcome["status"] != "FINISHED" or outcome["exit_code"] != 0:
        outcome["observed"] = None
        return outcome
    record = json.loads(outcome["stdout"].strip().splitlines()[-1])
    record["backend"] = "PROCESS_SEPARATION"
    record["sandbox"] = False
    record["workspace"] = outcome["cwd"]
    return record
