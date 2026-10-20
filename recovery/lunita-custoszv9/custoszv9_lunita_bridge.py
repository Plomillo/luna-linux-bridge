#!/usr/bin/env python3
"""Scoped CUSTOSZ V9 CRFU adapter for the existing Lunita/Cajita continuation.

Default behavior is audit-only. --run-one-step calls exactly one already-approved
continuation tick through V9's bounded coordinator. It never promotes G06/G08,
changes the frozen original, or claims mission certification.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import uuid
from typing import Any

HERE = pathlib.Path(__file__).resolve().parent
BASE = HERE.parents[1]
OPERATOR_ROOT = BASE.parent
STATE = BASE / "state"
OUTPUTS = STATE / "worker_outputs"
PROGRESS = STATE / "continuation_progress.json"
CONTRACT_PATH = BASE / "contract.json"
AUTH_PATH = BASE / "operator_authorization.json"
V9_PATH = OPERATOR_ROOT / "CUSTOSZV9.pyz"
V9_EXPECTED_SHA256 = "667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
MISSION_SHA256 = "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
CANDIDATE_ID = "G06_REBUILD_CANDIDATE_R1"
REFRESH_SECONDS = 300


class BridgeError(RuntimeError):
    pass


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_json(path: pathlib.Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise BridgeError("FILE_MISSING:" + str(path)) from exc
    except PermissionError as exc:
        raise BridgeError("ACCESS_DENIED:" + str(path)) from exc
    except (OSError, ValueError) as exc:
        raise BridgeError("INVALID_JSON:" + str(path) + ":" + type(exc).__name__) from exc
    if not isinstance(value, dict):
        raise BridgeError("JSON_ROOT_NOT_OBJECT:" + str(path))
    return value


def import_v9():
    if not V9_PATH.is_file():
        raise BridgeError("CUSTOSZV9_ARTIFACT_MISSING")
    digest = sha256_file(V9_PATH)
    if digest != V9_EXPECTED_SHA256:
        raise BridgeError("CUSTOSZV9_ARTIFACT_HASH_MISMATCH")
    if str(V9_PATH) not in sys.path:
        sys.path.insert(0, str(V9_PATH))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.event_queue import PersistentMissionQueue
    from custoszv9.crfu.evidence import append_event, verify_journal
    from custoszv9.crfu.model import sha256_bytes as v9_sha256_bytes
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    return run_bounded_mission, PersistentMissionQueue, append_event, verify_journal, v9_sha256_bytes, ActionSpec, probe_host_resources


def validate_local_authorization(task: dict[str, Any]) -> dict[str, Any]:
    contract = read_json(CONTRACT_PATH)
    auth = read_json(AUTH_PATH)
    if contract.get("mission_sha256") != MISSION_SHA256 or auth.get("mission_sha256") != MISSION_SHA256:
        return {"status": "DENIED", "reason": "MISSION_IDENTITY_MISMATCH"}
    if contract.get("status") != "ACTIVE_UNBOUNDED_CONTRACT" or auth.get("authorization_mode") != "UNBOUNDED_NO_EXPIRY":
        return {"status": "DENIED", "reason": "LOCAL_OPERATOR_AUTHORIZATION_NOT_ACTIVE"}
    if task.get("mission_id") != contract.get("mission_id"):
        return {"status": "DENIED", "reason": "MISSION_ID_MISMATCH"}
    if task.get("authorized_scope") != contract.get("scope") or task.get("authorized_scope") != auth.get("scope"):
        return {"status": "DENIED", "reason": "SCOPE_MISMATCH"}
    if task.get("authorization_evidence_reference") != str(AUTH_PATH):
        return {"status": "DENIED", "reason": "AUTHORIZATION_REFERENCE_MISMATCH"}
    auth_text = set(str(x).casefold() for x in auth.get("allowed_effects", []))
    effect_map = {
        "READ_PROJECT_ARTIFACTS": "read project artifacts",
        "WRITE_LOCAL_AUDIT": "checkpointed changes inside scope",
    }
    missing = [effect for effect in task.get("permitted_effects", []) if effect not in effect_map or effect_map[effect] not in auth_text]
    if missing:
        return {"status": "DENIED", "reason": "EFFECT_NOT_AUTHORIZED", "missing_effects": missing}
    return {
        "status": "PASS",
        "task_id": task.get("task_id"),
        "authorization_scope": auth.get("scope"),
        "mission_sha256": MISSION_SHA256,
        "operator_authorization_sha256": sha256_file(AUTH_PATH),
        "contract_sha256": sha256_file(CONTRACT_PATH),
        "authorization_basis": "EXISTING_LOCAL_OPERATOR_DIRECTIVE_PLUS_EXPLICIT_CURRENT_USER_INSTRUCTION",
        "cryptographic_signature": "NOT_PRESENT",
        "scope_limited": True,
        "canonical_promotion_authorized": False,
        "certification_authority": False,
    }


def systemd_user_service_active() -> bool:
    env = os.environ.copy()
    env.setdefault("XDG_RUNTIME_DIR", "/run/user/1000")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS", "unix:path=/run/user/1000/bus")
    result = subprocess.run(
        ["systemctl", "--user", "show", "custosz-continuity-v1.service", "--property=ActiveState", "--value"],
        capture_output=True, text=True, timeout=10, env=env, check=False,
    )
    if result.returncode != 0:
        raise BridgeError("SUPERVISOR_STATE_UNKNOWN:" + result.stderr.strip()[-300:])
    return result.stdout.strip() == "active"


def create_task(source_state_hash: str, task_id: str, auth_reference: str) -> dict[str, Any]:
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "task_id": task_id,
        "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
        "project_id": "LUNITA_MATERIALIZATION",
        "source_identity": "CUSTOSZV9.pyz:" + V9_EXPECTED_SHA256,
        "target_identity": CANDIDATE_ID + ":checkpointed-continuation-state",
        "source_state_hash": source_state_hash,
        "dependency_set": ["CUSTOSZV9_PREFLIGHT_REPORT", "EXISTING_CONTINUATION_CHECKPOINT"],
        "authorized_scope": "MISION1_CAJITA_LUNITA",
        "required_capabilities": ["LOCAL_FILE_READ", "HASH_STREAMING", "CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE"],
        "inputs": {
            "v9_artifact": str(V9_PATH),
            "v9_sha256": V9_EXPECTED_SHA256,
            "operator_authorization": auth_reference,
            "progress_file": str(PROGRESS),
            "candidate_id": CANDIDATE_ID,
        },
        "preconditions": [
            "V9 artifact SHA-256 matches the frozen local V9 package",
            "V9 software self-test report is PASS and hash-bound to the same package",
            "continuity supervisor is inactive to prevent concurrent tick",
            "previous continuation result receipt verifies",
        ],
        "permitted_effects": ["READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT"],
        "resource_budget": {
            "ram_required_bytes": 32 * 1024 * 1024,
            "ram_reserved_bytes": 64 * 1024 * 1024,
            "disk_required_bytes": 8 * 1024 * 1024,
            "max_concurrency": 1,
        },
        "execution_deadline": (now + dt.timedelta(minutes=3)).isoformat(),
        "maximum_planning_budget": 2,
        "maximum_retry_budget": 0,
        "acceptance_criteria": [
            "V9 CRFU coordinator runs with explicit local authorization verifier",
            "one continuation tick is invoked at most once in this bridge run",
            "a blocked continuation step remains pending and keeps step_index unchanged",
            "a hash-bound bridge receipt is written",
        ],
        "expected_outputs": ["CUSTOSZV9_LUNITA_BRIDGE_RUN_*.json", "continuation attempt receipt or bounded backoff record"],
        "validation_strategy": "hash-bound-postcondition-checks",
        "evidence_requirements": ["V9 package SHA-256", "preflight report SHA-256", "before/after progress state", "tick result receipt"],
        "checkpoint_reference": str(STATE / "checkpoints" / "CUSTOSZ_ANTI_PARALYSIS_PRE_20261020T173429Z"),
        "rollback_strategy": "No rollback of append-only evidence. Candidate-state restoration uses its checkpoint; frozen G06/G08 remain untouched.",
        "completion_condition": "exactly one tick or existing bounded wait is recorded and independently postvalidated",
        "escalation_condition": "hold if authorization, resource, identity, concurrency, or postcondition check fails",
        "authorization_evidence_reference": auth_reference,
    }


def preflight_observation(report_path: pathlib.Path) -> dict[str, Any]:
    report = read_json(report_path)
    if report.get("schema") != "CUSTOSZV9_RUNTIME_PREFLIGHT_EVIDENCE/1.0":
        raise BridgeError("V9_PREFLIGHT_REPORT_SCHEMA_MISMATCH")
    if report.get("artifact_sha256") != V9_EXPECTED_SHA256:
        raise BridgeError("V9_PREFLIGHT_REPORT_ARTIFACT_MISMATCH")
    if report.get("decision") != "PASS_SOFTWARE_SELFTEST_ONLY; MISSION_DISPATCH_HOLD":
        raise BridgeError("V9_PREFLIGHT_REPORT_NOT_PASS")
    selftest = report.get("crfu_selftest", {}).get("json") or {}
    if selftest.get("status") != "PASS" or selftest.get("check_count") != 12 or selftest.get("failed_checks") != []:
        raise BridgeError("V9_SELFTEST_EVIDENCE_NOT_PASS")
    return {"path": str(report_path), "sha256": sha256_file(report_path), "status": "PASS_SOFTWARE_SELFTEST_ONLY"}


def get_latest_v9_preflight() -> pathlib.Path:
    matches = sorted((OUTPUTS).glob("CUSTOSZV9_RUNTIME_PREFLIGHT_*.json"))
    # The report is created in OUTPUTS; use the latest existing report rather than
    # freezing a one-off timestamp in the adapter.
    if not matches:
        raise BridgeError("V9_PREFLIGHT_REPORT_MISSING")
    verified = []
    for path in matches:
        try:
            row = read_json(path)
        except BridgeError:
            continue
        if row.get("artifact_sha256") == V9_EXPECTED_SHA256 and row.get("schema") == "CUSTOSZV9_RUNTIME_PREFLIGHT_EVIDENCE/1.0":
            verified.append(path)
    if not verified:
        raise BridgeError("V9_PREFLIGHT_REPORT_IDENTITY_NOT_FOUND")
    return max(verified, key=lambda path: path.stat().st_mtime_ns)


def execute_one_step(task: dict[str, Any], authorization: dict[str, Any]) -> dict[str, Any]:
    if authorization.get("status") != "PASS" or authorization.get("task_id") != task.get("task_id"):
        return {"status": "DENIED", "reason": "AUTHORIZED_CALLBACK_NOT_BOUND_TO_TASK"}
    report_path = get_latest_v9_preflight()
    preflight = preflight_observation(report_path)
    candidate = STATE / "g06_rebuild_candidates" / CANDIDATE_ID
    state_before = read_json(PROGRESS)
    idx = state_before.get("step_index")
    progress_hash_before = sha256_file(PROGRESS)
    supervisor_active = systemd_user_service_active()
    if supervisor_active:
        return {"status": "HOLD", "reason": "CONTINUITY_SUPERVISOR_ACTIVE_CONCURRENCY_1", "v9_preflight": preflight}
    if state_before.get("mission_sha256") != MISSION_SHA256:
        return {"status": "DENIED", "reason": "CONTINUATION_MISSION_HASH_MISMATCH"}
    if not candidate.is_dir():
        return {"status": "HOLD", "reason": "VERSIONED_G06_CANDIDATE_MISSING"}
    pending = state_before.get("blocked_step") or {}
    last_progress_before = state_before.get("last_progress_utc")
    if pending and pending.get("step_index") == idx and pending.get("next_retry_utc"):
        try:
            wait = (dt.datetime.fromisoformat(pending["next_retry_utc"].replace("Z", "+00:00")) - dt.datetime.now(dt.timezone.utc)).total_seconds()
        except (ValueError, TypeError, AttributeError):
            wait = 0
        if wait > 0:
            return {
                "status": "PASS",
                "action": "HONOR_EXISTING_BOUNDED_BACKOFF",
                "worker_result": {
                    "status": "WAITING_FOR_EVENT",
                    "step_id": pending.get("step_id"),
                    "step_index": idx,
                    "retry_after_seconds": max(1, int(wait)),
                    "next_action": pending.get("next_action"),
                },
                "v9_preflight": preflight,
                "result_state_hash": progress_hash_before,
                "last_progress_utc_preserved": True,
            }

    # Directly call the already-authorized single-step continuation entrypoint; never start a loop.
    if str(BASE) not in sys.path:
        sys.path.insert(0, str(BASE))
    import custosz_mision1_continuation_v1 as continuation
    result = continuation.tick()
    state_after = read_json(PROGRESS)
    idx_after = state_after.get("step_index")
    last_progress_after = state_after.get("last_progress_utc")
    row_count_before = len(state_before.get("completed_steps", []))
    row_count_after = len(state_after.get("completed_steps", []))
    blocked = state_after.get("blocked_step") or {}
    outcome_path = pathlib.Path((result.get("attempt_evidence") or {}).get("result_path", blocked.get("result_path", "")))
    outcome_hash = sha256_file(outcome_path) if outcome_path.is_file() else None
    expected_step = continuation.STEPS[idx][0] if isinstance(idx, int) and 0 <= idx < len(continuation.STEPS) else None
    if result.get("status") == "WAITING_FOR_EVENT":
        ok = (
            idx_after == idx
            and row_count_after == row_count_before
            and last_progress_after == last_progress_before
            and blocked.get("step_index") == idx
            and blocked.get("step_id") == expected_step
            and outcome_path.is_file()
            and outcome_hash == blocked.get("result_sha256")
        )
        if not ok:
            return {
                "status": "FAIL",
                "reason": "BLOCKED_STEP_POSTCONDITION_FAILED",
                "worker_result": result,
                "index_before": idx,
                "index_after": idx_after,
                "completed_rows_before": row_count_before,
                "completed_rows_after": row_count_after,
                "last_progress_before": last_progress_before,
                "last_progress_after": last_progress_after,
                "result_state_hash": sha256_file(PROGRESS),
            }
        return {
            "status": "PASS",
            "action": "BLOCK_RECORDED_WITHOUT_ADVANCING_MISSION",
            "worker_result": result,
            "index_before": idx,
            "index_after": idx_after,
            "completed_rows_before": row_count_before,
            "completed_rows_after": row_count_after,
            "last_progress_before": last_progress_before,
            "last_progress_after": last_progress_after,
            "blocked_result_path": str(outcome_path),
            "blocked_result_sha256": outcome_hash,
            "last_progress_utc_preserved": True,
            "step_index_preserved": True,
            "mission_completion_claim": False,
            "result_state_hash": sha256_file(PROGRESS),
        }
    if result.get("status") == "PASS_FOR_SUBTASK_ONLY" and result.get("step_id") == expected_step:
        completed = state_after.get("completed_steps") or []
        row = completed[-1] if completed else {}
        outcome_path = pathlib.Path(str(row.get("result_path", "")))
        outcome_hash = sha256_file(outcome_path) if outcome_path.is_file() else None
        outcome_record = read_json(outcome_path) if outcome_path.is_file() else {}
        expected_status = "PASS_RUNTIME_TESTS" if expected_step == "S31_VERSIONED_BETA_RUNTIME_FUNCTIONAL_GATE" else None
        ok = (
            idx_after == idx + 1
            and row_count_after == row_count_before + 1
            and last_progress_after != last_progress_before
            and row.get("step_id") == expected_step
            and outcome_path.is_file()
            and outcome_hash == row.get("result_sha256")
            and outcome_record.get("step_id") == expected_step
            and outcome_record.get("mission_sha256") == MISSION_SHA256
            and (expected_status is None or outcome_record.get("status") == expected_status)
            and outcome_record.get("step_completion") is True
        )
        if not ok:
            return {
                "status": "FAIL",
                "reason": "COMPLETED_STEP_POSTCONDITION_FAILED",
                "worker_result": result,
                "index_before": idx,
                "index_after": idx_after,
                "completed_rows_before": row_count_before,
                "completed_rows_after": row_count_after,
                "last_progress_before": last_progress_before,
                "last_progress_after": last_progress_after,
                "step_result_path": str(outcome_path),
                "step_result_sha256": outcome_hash,
                "result_state_hash": sha256_file(PROGRESS),
            }
        return {
            "status": "PASS",
            "action": "SINGLE_CHECKPOINTED_STEP_COMPLETED_WITH_RECEIPT",
            "worker_result": result,
            "index_before": idx,
            "index_after": idx_after,
            "completed_rows_before": row_count_before,
            "completed_rows_after": row_count_after,
            "last_progress_before": last_progress_before,
            "last_progress_after": last_progress_after,
            "step_result_path": str(outcome_path),
            "step_result_sha256": outcome_hash,
            "step_result_status": outcome_record.get("status"),
            "mission_completion_claim": False,
            "certification": "NOT_GRANTED",
            "result_state_hash": sha256_file(PROGRESS),
        }
    return {
        "status": "HOLD",
        "reason": "UNEXPECTED_CONTINUATION_TICK_OUTCOME",
        "worker_result": result,
        "index_before": idx,
        "index_after": idx_after,
        "result_state_hash": sha256_file(PROGRESS),
    }


def run_bridge() -> dict[str, Any]:
    run_bounded_mission, Queue, append_event, verify_journal, v9_sha, ActionSpec, probe_resources = import_v9()
    progress = read_json(PROGRESS)
    auth_reference = str(AUTH_PATH)
    preflight_path = get_latest_v9_preflight()
    preflight = preflight_observation(preflight_path)
    before_hash = sha256_file(PROGRESS)
    before_size = PROGRESS.stat().st_size
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    task_id = "CUSTOSZV9_LUNITA_BRIDGE_" + run_id
    task = create_task(before_hash, task_id, auth_reference)
    auth = validate_local_authorization(task)
    if auth.get("status") != "PASS":
        raise BridgeError("AUTHORIZATION_PREFLIGHT_DENIED:" + str(auth))
    snapshot = probe_resources(BASE)
    actions = [
        ActionSpec(
            "verify_v9_preflight",
            (),
            ("LOCAL_FILE_READ", "HASH_STREAMING"),
            ("READ_PROJECT_ARTIFACTS",),
            "READ_ONLY",
        ),
        ActionSpec(
            "continue_exactly_one_checkpointed_step",
            ("verify_v9_preflight",),
            ("CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE"),
            ("WRITE_LOCAL_AUDIT",),
            "IDEMPOTENT",
        ),
    ]

    def auth_verifier(candidate_task: dict[str, Any]) -> dict[str, Any]:
        return validate_local_authorization(candidate_task)

    def action_runner(payload: dict[str, Any]) -> dict[str, Any]:
        action_id = payload["action"]["action_id"]
        if action_id == "verify_v9_preflight":
            latest = preflight_observation(preflight_path)
            return {"status": "PASS", "v9_preflight": latest, "result_state_hash": sha256_file(PROGRESS)}
        if action_id == "continue_exactly_one_checkpointed_step":
            try:
                return execute_one_step(payload["task"], payload["authorization"])
            except Exception as exc:
                # Preserve the failure in V9 queue/report rather than lose the adapter receipt.
                return {"status": "HOLD", "reason": "CONTINUATION_TICK_EXCEPTION:" + type(exc).__name__,
                        "mission_completion_claim": False}
        return {"status": "DENIED", "reason": "ACTION_ID_NOT_REGISTERED"}

    # V9's persistent event queue records this adapter task before the coordinator
    # executes. It is separate from the legacy mission state and is append-only.
    queue_path = STATE / "custoszv9_lunita_bridge.sqlite3"
    mission_queue = Queue(queue_path)
    submitted = mission_queue.submit(task)
    if submitted.get("state") != "RECEIVED":
        raise BridgeError("V9_QUEUE_SUBMIT_NOT_RECEIVED:" + str(submitted.get("state")))
    mission_queue.transition(
        task_id, "RECEIVED", "PREFLIGHT", event_type="V9_BRIDGE_PREFLIGHT_STARTED",
        payload={"v9_sha256": V9_EXPECTED_SHA256, "preflight_sha256": preflight["sha256"]},
    )
    mission_queue.transition(
        task_id, "PREFLIGHT", "READY", event_type="V9_BRIDGE_PREFLIGHT_PASS",
        payload={"mission_sha256": MISSION_SHA256, "scope": task["authorized_scope"]},
    )
    claimed = mission_queue.claim_next_ready()
    if not isinstance(claimed, dict) or claimed.get("mission_id") != task_id or claimed.get("state") != "RUNNING":
        raise BridgeError("V9_QUEUE_ATOMIC_CLAIM_FAILED")
    coordinator = run_bounded_mission(
        task,
        actions,
        snapshot,
        available_capabilities={
            "LOCAL_FILE_READ", "HASH_STREAMING", "CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE",
        },
        admissible_effects={"READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT"},
        authorization_verifier=auth_verifier,
        action_runner=action_runner,
        maximum_steps=2,
        planning_budget=2,
    )
    if coordinator.get("status") == "COMPLETED":
        queue_terminal = mission_queue.transition(
            task_id, "RUNNING", "COMPLETED", event_type="V9_BRIDGE_ADAPTER_TASK_COMPLETED",
            payload={"underlying_mission_certification": "NOT_GRANTED",
                     "mission_completion_claim": False,
                     "coordinator_status": coordinator.get("status")},
        )
    else:
        queue_terminal = mission_queue.transition(
            task_id, "RUNNING", "BLOCKED", event_type="V9_BRIDGE_ADAPTER_TASK_BLOCKED",
            payload={"coordinator_status": coordinator.get("status"),
                     "reason": coordinator.get("next_action") or coordinator.get("stage"),
                     "mission_completion_claim": False},
        )
    queue_chain = mission_queue.verify_event_chain()
    report = {
        "schema": "CUSTOSZV9_LUNITA_BRIDGE_RUN/1.0",
        "timestamp_utc": utc_now(),
        "task_id": task_id,
        "task_scope": task["authorized_scope"],
        "mission_id": task["mission_id"],
        "mission_sha256": MISSION_SHA256,
        "v9_artifact": str(V9_PATH),
        "v9_artifact_sha256": sha256_file(V9_PATH),
        "v9_preflight_report": preflight,
        "local_authorization": auth,
        "resource_snapshot": snapshot.to_dict(),
        "coordinator_result": coordinator,
        "persistent_queue_path": str(queue_path),
        "persistent_queue_task_state": queue_terminal.get("state"),
        "persistent_queue_event_chain": queue_chain,
        "continuation_index_before": progress.get("step_index"),
        "continuation_index_after": read_json(PROGRESS).get("step_index"),
        "continuation_last_progress_utc": read_json(PROGRESS).get("last_progress_utc"),
        "mission_completion_claim": False,
        "canonical_g06_mutated": False,
        "canonical_g08_bindings_mutated": False,
        "canonical_promotion": "NOT_AUTHORIZED",
        "certification": "NOT_GRANTED",
    }
    raw = json.dumps(report, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    report_path = OUTPUTS / ("CUSTOSZV9_LUNITA_BRIDGE_RUN_" + run_id + ".json")
    OUTPUTS.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = report_path.with_suffix(".tmp")
    with tmp.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(tmp, 0o600)
    os.replace(tmp, report_path)
    report["report_path"] = str(report_path)
    report["report_sha256"] = sha256_file(report_path)
    journal_path = STATE / "custoszv9_lunita_bridge_events.jsonl"
    event = {
        "operation_id": task_id,
        "mission_id": task["mission_id"],
        "sequence_id": 1 + (journal_path.read_text(encoding="utf-8").count("\n") if journal_path.exists() else 0),
        "timestamp_utc": utc_now(),
        "actor": "CUSTOSZV9_LUNITA_BRIDGE",
        "tool_and_version": "CUSTOSZV9/9.0.0-candidate+external-action-adapter",
        "source_identity": str(V9_PATH),
        "input_hash_and_size": {"sha256": before_hash, "size_bytes": before_size},
        "output_hash_and_size": {"sha256": report["report_sha256"], "size_bytes": report_path.stat().st_size},
        "validation_result": "PASS_ADAPTER_TASK_ONLY" if coordinator.get("status") == "COMPLETED" else "HOLD",
        "authorization_evidence_reference": str(AUTH_PATH),
        "dependency_context": [preflight["sha256"], auth["operator_authorization_sha256"]],
        "rollback_pointer": str(STATE / "checkpoints" / "CUSTOSZ_ANTI_PARALYSIS_PRE_20261020T173429Z"),
        "status": "ADAPTER_TASK_COMPLETED_NOT_MISSION_CERTIFICATION",
    }
    append_event(journal_path, event)
    journal_validation = verify_journal(journal_path)
    report["event_journal_path"] = str(journal_path)
    report["event_journal_validation"] = journal_validation
    report["adapter_task_status"] = coordinator.get("status")
    report["bridge_result"] = (
        "PASS_ONE_CHECKPOINTED_TICK_AND_EVIDENCE_RECORDED"
        if coordinator.get("status") == "COMPLETED"
        and journal_validation.get("status") == "PASS"
        and queue_chain.get("status") == "PASS"
        and queue_terminal.get("state") == "COMPLETED"
        else "HOLD_REQUIRES_RECONCILIATION"
    )
    # Do not mutate the already hash-bound operation snapshot. Save the terminal
    # reconciliation as a separate append-only receipt to avoid a self-hash cycle.
    closeout = {
        "schema": "CUSTOSZV9_LUNITA_BRIDGE_CLOSEOUT/1.0",
        "timestamp_utc": utc_now(),
        "operation_report_path": str(report_path),
        "operation_report_sha256": sha256_file(report_path),
        "event_journal_path": str(journal_path),
        "event_journal_sha256": sha256_file(journal_path) if journal_path.is_file() else None,
        "event_journal_validation": journal_validation,
        "persistent_queue_path": str(queue_path),
        "persistent_queue_event_chain": queue_chain,
        "persistent_queue_task_state": queue_terminal.get("state"),
        "coordinator_status": coordinator.get("status"),
        "bridge_result": report["bridge_result"],
        "continuation_index_before": report["continuation_index_before"],
        "continuation_index_after": report["continuation_index_after"],
        "continuation_last_progress_utc": report["continuation_last_progress_utc"],
        "mission_completion_claim": False,
        "canonical_g06_mutated": False,
        "canonical_g08_bindings_mutated": False,
        "canonical_promotion": "NOT_AUTHORIZED",
        "certification": "NOT_GRANTED",
    }
    closeout_path = OUTPUTS / ("CUSTOSZV9_LUNITA_BRIDGE_CLOSEOUT_" + run_id + ".json")
    raw_closeout = json.dumps(closeout, sort_keys=True, indent=2, ensure_ascii=False).encode("utf-8") + b"\n"
    temp_closeout = closeout_path.with_suffix(".tmp")
    with temp_closeout.open("xb") as stream:
        stream.write(raw_closeout)
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp_closeout, 0o600)
    os.replace(temp_closeout, closeout_path)
    report["closeout_receipt_path"] = str(closeout_path)
    report["closeout_receipt_sha256"] = sha256_file(closeout_path)
    if report["bridge_result"] != "PASS_ONE_CHECKPOINTED_TICK_AND_EVIDENCE_RECORDED":
        raise BridgeError("BRIDGE_POSTVALIDATION_FAILED:" + json.dumps(report, ensure_ascii=False)[:3000])
    return report


def audit_only() -> dict[str, Any]:
    run_bounded_mission, _, _, _, _, _, probe_resources = import_v9()
    contract = read_json(CONTRACT_PATH)
    auth = read_json(AUTH_PATH)
    progress = read_json(PROGRESS)
    return {
        "schema": "CUSTOSZV9_LUNITA_BRIDGE_AUDIT/1.0",
        "status": "PASS" if sha256_file(V9_PATH) == V9_EXPECTED_SHA256
                  and contract.get("mission_sha256") == MISSION_SHA256
                  and auth.get("mission_sha256") == MISSION_SHA256 else "FAIL",
        "timestamp_utc": utc_now(),
        "v9_artifact_sha256": sha256_file(V9_PATH),
        "v9_hash_match": sha256_file(V9_PATH) == V9_EXPECTED_SHA256,
        "contract_mission_sha256_match": contract.get("mission_sha256") == MISSION_SHA256,
        "operator_authorization_scope": auth.get("scope"),
        "progress_step_index": progress.get("step_index"),
        "progress_step_count": len(progress.get("completed_steps", [])),
        "blocked_step": progress.get("blocked_step"),
        "resource_snapshot": probe_resources(BASE).to_dict(),
        "mission_dispatch_method": "EXTERNAL_SCOPED_ADAPTER_REQUIRED",
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }


def selftest() -> dict[str, Any]:
    run_bounded_mission, _, _, _, _, ActionSpec, probe_resources = import_v9()
    task = create_task("a" * 64, "CUSTOSZV9_BRIDGE_SELFTEST", str(AUTH_PATH))
    task["mission_id"] = "synthetic-selftest-mission"
    task["source_state_hash"] = "a" * 64
    task["authorization_evidence_reference"] = "selftest"
    task["authorized_scope"] = "LOCAL_TEST_ONLY"
    snapshot = probe_resources(pathlib.Path("/tmp"))
    def auth_ok(value):
        return {"status": "PASS", "task_id": value["task_id"]}
    actions = [ActionSpec("selftest_action", (), (), (), "READ_ONLY")]
    result = run_bounded_mission(
        task, actions, snapshot, available_capabilities=set(), admissible_effects=set(),
        authorization_verifier=auth_ok,
        action_runner=lambda payload: {"status": "PASS", "result_state_hash": "b" * 64},
        maximum_steps=1, planning_budget=1,
    )
    denied = run_bounded_mission(
        task, actions, snapshot, available_capabilities=set(), admissible_effects=set(),
        authorization_verifier=None,
        action_runner=lambda payload: {"status": "PASS"},
        maximum_steps=1, planning_budget=1,
    )
    checks = {
        "v9_coordinator_runs_bounded_action": result.get("status") == "COMPLETED",
        "coordinator_keeps_certification_ungranted": result.get("certification") == "NOT_GRANTED",
        "missing_authorization_verifier_holds": denied.get("status") == "HOLD",
        "no_canonical_promotion_claim": result.get("canonical_promotion") == "NOT_AUTHORIZED",
    }
    return {
        "schema": "CUSTOSZV9_LUNITA_BRIDGE_SELFTEST/1.0",
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "check_count": len(checks),
        "failed_checks": [k for k, v in checks.items() if not v],
        "host_mission_side_effects": False,
        "certification": "NOT_GRANTED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--audit", action="store_true")
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--run-one-step", action="store_true")
    args = parser.parse_args()
    try:
        if args.audit:
