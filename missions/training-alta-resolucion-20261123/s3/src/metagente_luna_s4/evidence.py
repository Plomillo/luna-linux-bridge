"""Persist execution evidence without upgrading its validation status."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import sys
import tempfile
from pathlib import Path


def _write_bytes(path: Path, data: bytes) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=".evidence-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise
    return {"path": path.name, "sha256": hashlib.sha256(data).hexdigest()}


def _json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def persist_run(record: dict, arguments: dict, evidence_root: str | Path) -> dict:
    """Persist one observed run. This function never marks it independently validated."""
    case_id = record.get("case_id")
    run_id = record.get("run_id")
    if not isinstance(case_id, str) or not case_id.startswith("MGL5-"):
        raise ValueError("invalid case id for evidence persistence")
    if not isinstance(run_id, str) or not run_id:
        raise ValueError("missing run id for evidence persistence")

    root = Path(evidence_root).resolve()
    destination = (root / case_id / run_id).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:
        raise ValueError("evidence destination escapes root") from exc
    if destination.exists():
        raise FileExistsError(destination)
    destination.mkdir(parents=True, exist_ok=False)

    capability_id = record.get("capability_id")
    oracle_result = record.get("oracle_result")
    observed = record.get("observed")
    started = record.get("started")
    ended = record.get("ended")
    oracle_module = record.get("oracle_module")
    producer_module = record.get("producer_module")
    oracle_independent = bool(oracle_module and producer_module and oracle_module != producer_module)

    payloads = {
        "fixture": _json_bytes({
            "case_id": case_id, "run_id": run_id, "capability_id": capability_id,
            "input": arguments, "fixture_origin": "runner-captured-input",
        }),
        "environment": _json_bytes({
            "case_id": case_id, "run_id": run_id,
            "environment_id": f"{platform.system()}-{platform.machine()}-python-{sys.version_info.major}.{sys.version_info.minor}",
            "python": sys.version, "platform": platform.platform(),
        }),
        "procedure": _json_bytes({
            "case_id": case_id, "run_id": run_id, "capability_id": capability_id,
            "procedure": "metagente_luna_s4.runner.execute",
        }),
        "stdout": str(record.get("stdout", "")).encode("utf-8"),
        "stderr": str(record.get("stderr", "")).encode("utf-8"),
        "observed": _json_bytes({
            "case_id": case_id, "run_id": run_id, "value": observed,
            "exit_code": record.get("exit_code"),
        }),
        "oracle": _json_bytes({
            "case_id": case_id, "run_id": run_id,
            "independent": oracle_independent,
            "producer_used_as_oracle": not oracle_independent,
            "oracle_module": oracle_module,
            "producer_module": producer_module,
            "result": (
                "PASS" if isinstance(oracle_result, dict) and oracle_result.get("ok") is True
                else "FAIL" if isinstance(oracle_result, dict) and oracle_result.get("ok") is False
                else "INCONCLUSIVE"
            ),
            "detail": oracle_result,
        }),
        "metrics": _json_bytes({
            "case_id": case_id, "run_id": run_id,
            "started": started, "ended": ended,
            "duration_seconds": max(0, ended - started) if isinstance(started, (int, float)) and isinstance(ended, (int, float)) else None,
        }),
    }
    artifacts = {}
    for name, data in payloads.items():
        suffix = ".txt" if name in {"stdout", "stderr"} else ".json"
        entry = _write_bytes(destination / f"{name}{suffix}", data)
        entry["path"] = f"{case_id}/{run_id}/{entry['path']}"
        artifacts[name] = entry
    return {
        "case_id": case_id,
        "run_id": run_id,
        "artifacts": artifacts,
        "clean_state": False,
        "execution_status": record.get("execution_status"),
        "exit_code": record.get("exit_code"),
        "agent_version": record.get("agent_version", "UNDECLARED"),
        "executor_version": record.get("executor_version", "UNDECLARED"),
        "machinery": record.get("backend", "UNDECLARED"),
        "independent_validation": {"passed": False, "status": "NOT_RUN"},
        "evidence_status": "PERSISTED_NOT_INDEPENDENTLY_VALIDATED",
    }
