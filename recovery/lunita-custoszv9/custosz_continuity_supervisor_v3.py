#!/usr/bin/env python3
"""Persistent unbounded-contract CUSTOSZ V9 supervisor; individual actions remain bounded."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import traceback

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import custosz_continuity as core
import custosz_mision1_worker_v2 as worker
import custosz_mision1_continuation_v1 as continuation
import custosz_fault_recovery_v1 as recovery

ST = core.ST
CONTRACT = core.CONTRACT
STATUS = core.STATUS
HEARTBEAT = core.HEART
BINDING = ROOT / "worker_binding_v2.json"
V9 = core.V9
MISSION = core.MISSION
MISSION_SHA = core.HS_MISSION
V9_SHA = core.HS_V9
SERVICE_POLL_SECONDS = 60
GITHUB_REFRESH_SECONDS = 900
OBSERVE_SECONDS = 300
PREFLIGHT_SECONDS = 21600

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def atomic(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + "." + str(os.getpid()) + ".tmp")
    temp.write_text(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.chmod(temp, 0o600)
    os.replace(temp, path)

def load(path, default=None):
    try:
        return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    except Exception:
        return default

def run_worker_selftest():
    worker_path = ROOT / "custosz_mision1_worker_v2.py"
    if not worker_path.is_file():
        raise RuntimeError("MISSION_WORKER_MISSING")
    if not MISSION.is_file() or sha(MISSION) != MISSION_SHA:
        raise RuntimeError("MISSION_INPUT_HASH_DRIFT")
    if not V9.is_file() or sha(V9) != V9_SHA:
        raise RuntimeError("CUSTOSZV9_PACKAGE_HASH_DRIFT")
    result = subprocess.run([sys.executable, "-B", str(worker_path), "--self-test"], capture_output=True, text=True, timeout=35, check=False)
    try:
        parsed = json.loads(result.stdout)
    except Exception:
        parsed = {"status": "UNPARSEABLE", "stdout_tail": result.stdout[-3000:], "stderr_tail": result.stderr[-2000:]}
    checks = {
        "process_rc_zero": result.returncode == 0,
        "worker_selftest_pass": parsed.get("status") == "PASS",
        "worker_hash_measured": len(sha(worker_path)) == 64,
        "v9_hash_pinned": sha(V9) == V9_SHA,
        "mission_hash_pinned": sha(MISSION) == MISSION_SHA,
    }
    report = {
        "schema": "CUSTOSZ_MISION1_WORKER_INDEPENDENT_VALIDATION/1.0",
        "captured_at_utc": utc(),
        "status": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "test_result": parsed,
        "worker_path": str(worker_path),
        "worker_sha256": sha(worker_path),
        "mission_sha256": MISSION_SHA,
        "custoszv9_sha256": V9_SHA,
        "test_runner": "separate Python subprocess; no project mutation test",
        "certification": "NOT_GRANTED",
    }
    atomic(ST / "worker_v2_independent_validation.json", report)
    if report["status"] != "PASS":
        raise RuntimeError("WORKER_INDEPENDENT_VALIDATION_FAILED")
    old = load(BINDING, {}) or {}
    binding = {
        "schema": "CUSTOSZ_MISION1_WORKER_BINDING/1.0",
        "status": "VALIDATED",
        "mission_id": core.MID,
        "mission_sha256": MISSION_SHA,
        "scope": core.SCOPE,
        "entrypoint": str(worker_path),
        "entrypoint_sha256": report["worker_sha256"],
        "test_command": [sys.executable, "-B", str(worker_path), "--self-test"],
        "test_result": "PASS",
        "validation_report_path": str(ST / "worker_v2_independent_validation.json"),
        "validation_report_sha256": sha(ST / "worker_v2_independent_validation.json"),
        "validated_at_utc": utc(),
        "validation_process_returncode": result.returncode,
        "capabilities": ["LOCAL_FILE_READ", "HASH_STREAMING", "V9_CRUF_PLANNING", "CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE"],
        "allowed_effects": ["WRITE_LOCAL_AUDIT", "WRITE_CAJITA_WITH_CHECKPOINTS", "APPEND_ONLY_PROTOCOL_ADDENDUM_AFTER_CHECKPOINT"],
        "certification_authority": False,
        "canonical_promotion_authority": False,
    }
    if old and old.get("status") == "VALIDATED" and old.get("entrypoint_sha256") != binding["entrypoint_sha256"]:
        # Never silently replace a previously validated executable binding.
        atomic(ST / "worker_binding_candidate.json", binding)
        raise RuntimeError("VALIDATED_WORKER_BINDING_DRIFT_RECORDED_AS_CANDIDATE")
    atomic(BINDING, binding)
    return report

def get_queue():
    m = core.components()
    q = m["PersistentMissionQueue"](core.QUEUE)
    contract = load(CONTRACT, {}) or {}
    return q, q.get(contract["mission_id"]), q.verify_event_chain()

def do_preflight():
    if not (ST / "initial_validation.json").is_file():
        core.inventory()
    v9 = core.v9_preflight()
    resource = core.resource()
    q, mission, chain = get_queue()
    journal = core.components()["verify_journal"](core.JOURNAL)
    return {
        "schema": "CUSTOSZ_CONTINUITY_SUPERVISOR_PREFLIGHT/2.0",
        "captured_at_utc": utc(),
        "status": "PASS" if v9.get("status") == "PASS" and resource["gate"].get("status") == "PASS" and chain.get("status") == "PASS" and journal.get("status") == "PASS" else "PARTIAL",
        "v9": v9.get("checks"),
        "resources": resource,
        "queue_state": mission.get("state"),
        "queue_chain": chain,
        "journal": journal,
        "mission_execution_started_by_worker": False,
    }

def loop():
    core.setup()
    contract = core.init()
    if not contract:
        contract = load(CONTRACT, {}) or {}
    if not contract:
        raise RuntimeError("24H_CONTRACT_UNAVAILABLE")
    if sha(MISSION) != MISSION_SHA or sha(V9) != V9_SHA:
        raise RuntimeError("PINNED_MISSION_OR_CUSTOSZV9_HASH_DRIFT")
    independent = run_worker_selftest()
    atomic(ST / "supervisor_preflight.json", do_preflight())
    next_github = 0.0
    next_observe = 0.0
    next_v9_probe = time.monotonic() + PREFLIGHT_SECONDS
    last_step_signature = None
    while True:
        contract = load(CONTRACT, {}) or {}
        now_dt = dt.datetime.now(dt.timezone.utc)
        deadline_text = contract.get("deadline_utc")
        if deadline_text and now_dt >= core.parseutc(deadline_text):
            expiry = {
                "schema": "CUSTOSZ_CONTINUITY_STATUS/2.0",
                "mission_id": contract.get("mission_id"),
                "phase": "CONTRACT_EXPIRED",
                "status": "EXPIRED_RESUMABLE",
                "timestamp_utc": utc(),
                "deadline_utc": contract.get("deadline_utc"),
                "mission_completion_claim": False,
                "certification_claim": "NONE",
                "evidence_preserved": True,
            }
            atomic(STATUS, expiry)
            core.event("CONTRACT_EXPIRED", "EXPIRED_RESUMABLE", {"deadline_utc": contract.get("deadline_utc")}, MISSION_SHA, MISSION.stat().st_size)
            return 0
        worker_result = None
        errors = []
        # GitHub synchronization, target observation, and worker execution are isolated:
        # failure in one subsystem must not suppress the others.
        if time.monotonic() >= next_github:
            try:
                github = core.github()
                atomic(ST / "github_evidence_search.json", github)
                next_github = time.monotonic() + GITHUB_REFRESH_SECONDS
                recovery.clear_stage("github_sync")
            except Exception as exc:
                errors.append("GITHUB_SYNC:" + type(exc).__name__)
                try:
                    recovery.record_fault("github_sync", exc, traceback.format_exc())
                except Exception:
                    pass
                next_github = time.monotonic() + SERVICE_POLL_SECONDS
        if time.monotonic() >= next_observe:
            try:
                observed = core.observe()
                next_observe = time.monotonic() + OBSERVE_SECONDS
                if observed:
                    errors.append("PROJECT_ARTIFACT_CHANGE_OBSERVED_NOT_ATTRIBUTED")
                recovery.clear_stage("target_observation")
            except Exception as exc:
                errors.append("TARGET_OBSERVATION:" + type(exc).__name__)
                try:
                    recovery.record_fault("target_observation", exc, traceback.format_exc())
                except Exception:
                    pass
                next_observe = time.monotonic() + SERVICE_POLL_SECONDS

        worker_due, worker_wait = recovery.retry_due("worker")
        if not worker_due:
            worker_result = {
                "status": "WAITING_FOR_EVENT",
                "phase": "CONTINUOUS_GOVERNED_SUBTASK_EXECUTION",
                "next_action": "Retry the same checkpoint-bound worker step after bounded backoff",
                "retry_after_seconds": worker_wait,
                "mission_completion_claim": False,
                "certification": "NOT_GRANTED",
            }
        else:
            try:
                worker_result = worker.tick()
                if worker_result.get("status") == "PHASE_2_ANALYSIS_STEPS_COMPLETE":
                    continuation_due, continuation_wait = recovery.retry_due("continuation")
                    if continuation_due:
                        try:
                            worker_result = continuation.tick()
                            if worker_result.get("status") == "PASS_FOR_SUBTASK_ONLY":
                                recovery.clear_stage("continuation")
                        except Exception as exc:
                            fault = recovery.record_fault("continuation", exc, traceback.format_exc())
                            errors.append("CONTINUATION:" + type(exc).__name__)
                            worker_result = {
                                "status": "RECOVERY_REQUIRED",
                                "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
                                "step_id": (load(ST / "continuation_progress.json", {}) or {}).get("completed_steps", [{}])[-1].get("step_id"),
                                "next_action": "Repair/retry the current continuation step using the GitHub-backed fault queue",
                                "fault": fault,
                                "mission_completion_claim": False,
                                "certification": "NOT_GRANTED",
                            }
                    else:
                        worker_result = {
                            "status": "WAITING_FOR_EVENT",
                            "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
                            "step_id": "CONTINUATION_RETRY_BACKOFF",
                            "next_action": "Retry the same continuation action after bounded backoff",
                            "retry_after_seconds": continuation_wait,
                            "mission_completion_claim": False,
                            "certification": "NOT_GRANTED",
                        }
                if worker_result.get("status") == "PASS_FOR_SUBTASK_ONLY":
                    recovery.clear_stage("worker")
            except Exception as exc:
                fault = recovery.record_fault("worker", exc, traceback.format_exc())
                errors.append("WORKER:" + type(exc).__name__)
                progress = load(ST / "mission_progress.json", {}) or {}
                rows = progress.get("completed_steps", [])
                worker_result = {
                    "status": "RECOVERY_REQUIRED",
                    "phase": "CONTINUOUS_GOVERNED_SUBTASK_EXECUTION",
                    "step_id": rows[-1].get("step_id") if rows else None,
                    "next_action": "Retry the checkpoint-bound current worker step after diagnosis/backoff",
                    "fault": fault,
                    "mission_completion_claim": False,
                    "certification": "NOT_GRANTED",
                }
        try:
            atomic(ST / "last_worker_invocation.json", {
                "timestamp_utc": utc(),
                "parsed": worker_result,
                "status": "PASS" if worker_result and worker_result.get("status") in {
                    "PASS_FOR_SUBTASK_ONLY", "WAITING_FOR_EVENT", "PHASE_2_ANALYSIS_STEPS_COMPLETE", "EXPIRED_RESUMABLE"
                } else "RECOVERY_REQUIRED",
            })
        except Exception as exc:
            errors.append("INVOCATION_STATE_PERSISTENCE:" + type(exc).__name__)
            try:
                recovery.record_fault("invocation_state_persistence", exc, traceback.format_exc())
            except Exception:
                pass
        try:
            q, queued_mission, qchain = get_queue()
            m = core.components()
            journal = m["verify_journal"](core.JOURNAL)
            resource = core.resource()
        except Exception as exc:
            qchain = {"status": "ERROR", "reason": type(exc).__name__}
            journal = {"status": "ERROR"}
            resource = {"ram_available_bytes": None, "gate": {"status": "HOLD", "reasons": [type(exc).__name__]}}
            queued_mission = {}
            errors.append("QUEUE_STATUS_RECONCILIATION:" + type(exc).__name__)
            try:
                recovery.record_fault("queue_status_reconciliation", exc, traceback.format_exc())
            except Exception:
                pass
        worker_done = worker_result or {}
        phase_done = worker_done.get("status") == "PHASE_2_ANALYSIS_STEPS_COMPLETE"
        implementation_phase = worker_done.get("phase") == "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION"
        phase_label = worker_done.get("phase") or ("PHASE_2_ANALYSIS_STEPS_COMPLETE" if phase_done else "CONTINUOUS_GOVERNED_SUBTASK_EXECUTION")
        if phase_done:
            status_label = "ACTIVE_ANALYSIS_COMPLETE_IMPLEMENTATION_PENDING"
        elif implementation_phase and worker_done.get("status") == "PASS_FOR_SUBTASK_ONLY":
            status_label = "ACTIVE_IMPLEMENTATION_CONTINUATION"
        elif implementation_phase and worker_done.get("status") == "WAITING_FOR_EVENT":
            status_label = "ACTIVE_IMPLEMENTATION_WAITING_FOR_EVENT"
        elif worker_done.get("status") == "PASS_FOR_SUBTASK_ONLY":
            status_label = "ACTIVE_SUBTASK_EXECUTION"
        else:
            status_label = "ACTIVE_SEARCHING_AND_RECOVERING"
        status = {
            "schema": "CUSTOSZ_CONTINUITY_STATUS/2.0",
            "mission_id": contract.get("mission_id"),
            "mission_sha256": MISSION_SHA,
            "contract_deadline_utc": contract.get("deadline_utc"),
            "phase": phase_label,
            "status": status_label,
            "last_heartbeat_utc": utc(),
            "pid": os.getpid(),
            "process_rss_bytes": core.rss(),
            "host_ram_available_bytes": resource.get("ram_available_bytes"),
            "memory_hard_cap_bytes": 1024 * 1024 * 1024,
            "memory_high_bytes": 256 * 1024 * 1024,
            "resource_gate": resource.get("gate"),
            "queue_state": queued_mission.get("state"),
            "queue_next_action": queued_mission.get("next_action"),
            "queue_integrity": qchain,
            "journal_integrity": journal,
            "worker_independent_validation": independent,
            "worker_result": worker_done,
            "github_read_only": True,
            "last_github_sync_utc": utc() if time.monotonic() >= next_github - GITHUB_REFRESH_SECONDS else None,
            "desktop_commander_in_runtime_loop": False,
            "mission_completion_claim": False,
            "certification_claim": "NONE",
            "errors": errors,
            "next_action": worker_done.get("next_action") or worker_done.get("step_id") or queued_mission.get("next_action") or "Continue the next independently validated action",
            "continuation_progress": load(ST / "continuation_progress.json", {}) or {},
            "fault_recovery_source": "Plomillo/luna-linux-bridge (read-only; candidate code must pass hash/tests before promotion)",
        }
        atomic(STATUS, status)
        atomic(HEARTBEAT, {
            "schema": "CUSTOSZ_CONTINUITY_HEARTBEAT/2.0",
            "timestamp_utc": utc(),
            "pid": os.getpid(),
            "process_rss_bytes": core.rss(),
            "host_ram_available_bytes": resource.get("ram_available_bytes"),
            "heartbeat_is_not_progress": True,
            "queue_integrity": qchain.get("status"),
            "journal_integrity": journal.get("status"),
            "worker_step_id": worker_done.get("step_id"),
            "worker_status": worker_done.get("status"),
        })
        if time.monotonic() >= next_v9_probe:
            try:
                pf = core.v9_preflight()
                atomic(ST / "periodic_v9_preflight.json", pf)
                core.event("PERIODIC_V9_PREFLIGHT", pf.get("status", "PARTIAL"), pf.get("checks", {}), MISSION_SHA, MISSION.stat().st_size)
            except Exception as exc:
                errors.append("V9_PREFLIGHT:" + type(exc).__name__)
                try:
                    recovery.record_fault("v9_preflight", exc, traceback.format_exc())
                except Exception:
                    pass
            next_v9_probe = time.monotonic() + PREFLIGHT_SECONDS
        time.sleep(max(20, min(SERVICE_POLL_SECONDS, 180)))

def selftest():
    checks = {
        "worker_selftest": worker.selftest().get("status") == "PASS",
        "mission_hash": MISSION.is_file() and sha(MISSION) == MISSION_SHA,
        "v9_hash": V9.is_file() and sha(V9) == V9_SHA,
        "contract_exists": CONTRACT.is_file(),
        "continuation_module_selftest": continuation.selftest().get("status") == "PASS",
        "fault_recovery_module_selftest": recovery.selftest().get("status") == "PASS",
    }
    report = {"schema": "CUSTOSZ_CONTINUITY_SUPERVISOR_SELFTEST/2.0", "timestamp_utc": utc(), "status": "PASS" if all(checks.values()) else "FAIL", "checks": checks, "project_mutations": False, "certification_claim": "NONE"}
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0 if report["status"] == "PASS" else 2

def resilient_loop():
    delay = 5
    while True:
        try:
            return loop()
        except (KeyboardInterrupt, SystemExit):
            raise
        except BaseException as exc:
            try:
                recovery.record_fault("supervisor_startup_or_outer_loop", exc, traceback.format_exc())
            except BaseException:
                pass
            try:
                time.sleep(delay)
            except (KeyboardInterrupt, SystemExit):
                raise
            delay = min(300, max(5, delay * 2))

def main():
    if "--self-test" in sys.argv:
        return selftest()
    return resilient_loop()

if __name__ == "__main__":
    raise SystemExit(main())
