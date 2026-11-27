"""Persist execution evidence without upgrading its validation status."""
from __future__ import annotations

import hashlib
import importlib
import inspect
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
    source_payloads: dict[str, bytes] = {}
    for label, module_name in (("oracle_source", oracle_module), ("producer_source", producer_module)):
        if not isinstance(module_name, str) or not module_name:
            continue
        try:
            module = importlib.import_module(module_name)
            source_path = inspect.getsourcefile(module)
            if source_path:
                source_payloads[label] = Path(source_path).read_bytes()
        except (ImportError, OSError, TypeError):
            continue
    oracle_source_digest = hashlib.sha256(source_payloads["oracle_source"]).hexdigest() if "oracle_source" in source_payloads else None
    producer_source_digest = hashlib.sha256(source_payloads["producer_source"]).hexdigest() if "producer_source" in source_payloads else None

    payloads = {
        "fixture": _json_bytes({
            "case_id": case_id, "run_id": run_id, "capability_id": capability_id,
            "input": arguments, "fixture_origin": "runner-captured-input",
            "run_kind": record.get("run_kind"), "control": record.get("control_metadata"),
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
            "oracle_source_sha256": oracle_source_digest,
            "producer_source_sha256": producer_source_digest,
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
    payloads.update(source_payloads)
    artifacts = {}
    for name, data in payloads.items():
        suffix = ".txt" if name in {"stdout", "stderr"} else ".py" if name in {"oracle_source", "producer_source"} else ".json"
        entry = _write_bytes(destination / f"{name}{suffix}", data)
        entry["path"] = f"{case_id}/{run_id}/{entry['path']}"
        artifacts[name] = entry
    return {
        "case_id": case_id,
        "run_id": run_id,
        "started": started,
        "ended": ended,
        "artifacts": artifacts,
        "clean_state": False,
        "execution_status": record.get("execution_status"),
        "exit_code": record.get("exit_code"),
        "agent_version": record.get("agent_version"),
        "executor_version": record.get("executor_version"),
        "machinery": record.get("backend"),
        "independent_validation": {"passed": False, "status": "NOT_RUN"},
        "evidence_status": "PERSISTED_NOT_INDEPENDENTLY_VALIDATED",
    }


def assemble_case_record(case_id: str, runs: list[dict]) -> dict:
    """Assemble three persisted run records without upgrading their evidence status."""
    required_kinds = {"NORMAL", "NEGATIVE", "BOUNDARY"}
    repetitions = []
    for run in runs:
        persisted = run.get("persisted_evidence")
        if not isinstance(persisted, dict):
            raise ValueError("each run must have persisted evidence")
        if persisted.get("case_id") != case_id or run.get("case_id") != case_id:
            raise ValueError("run belongs to a different case")
        repetition = dict(persisted)
        repetition["kind"] = run.get("run_kind")
        repetitions.append(repetition)
    kinds = {item.get("kind") for item in repetitions}
    if len(repetitions) != 3 or kinds != required_kinds:
        raise ValueError("exactly one NORMAL, NEGATIVE, and BOUNDARY execution is required")
    run_ids = [item.get("run_id") for item in repetitions]
    if len(run_ids) != len(set(run_ids)):
        raise ValueError("repetition RUN_ID values must be unique")
    outcomes = [item.get("execution_status") for item in repetitions]
    if any(outcome not in {"PASS", "FAIL", "BLOCKED", "INCONCLUSIVE"} for outcome in outcomes):
        raise ValueError("each run must have an explicit execution outcome")
    outcome = outcomes[0] if len(set(outcomes)) == 1 else "INCONCLUSIVE"
    return {
        "CASE_ID": case_id,
        "execution_status": outcome,
        "contract_status": "NOT_A_PASS",
        "repetitions": repetitions,
        "independent_validation": {"passed": False, "status": "NOT_RUN"},
    }
