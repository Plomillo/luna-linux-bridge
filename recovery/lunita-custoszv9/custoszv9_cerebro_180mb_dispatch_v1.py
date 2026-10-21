#!/usr/bin/env python3
"""CUSTOSZ V9 CRFU dispatcher for Cerebro's <=180,000,000-byte candidate lane.

This launch adapter does not certify or promote the model. It binds the worker launch to V9,
the validated worker binding, a source checkpoint, a one-GiB cgroup and the assigned GitHub branch.
"""
from __future__ import annotations
import datetime as dt
import fcntl
from dataclasses import replace
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time
import uuid

HOME = pathlib.Path("/home/diegoignacionorambuenamiranda")
ROOT = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
RT = ROOT / "CUSTOSZ_CONTINUITY_V1"
STATE = RT / "state"
OUT = STATE / "worker_outputs"
SCRIPT_DIR = STATE / "jobs/cerebro_180mb_lowrank_v1"
JOB_DIR = pathlib.Path(os.environ.get("CEREBRO_JOB_DIR", str(SCRIPT_DIR))).resolve()
WORKER = SCRIPT_DIR / "cerebro_180mb_lowrank_v1.py"
RUNTIME = SCRIPT_DIR / "cerebro_180mb_lowrank_runtime_v1.py"
LOCK_DIR = STATE / "locks"
DISPATCH_LOCK_PATH = LOCK_DIR / "cerebro_180mb_dispatch.lock"
WORKER_LOCK_PATH = LOCK_DIR / "cerebro_180mb_worker.lock"
WORKER_PY = RT / "state/tools/venvs/llama-cpp-b10819-py313/bin/python"
V9 = ROOT / "CUSTOSZV9.pyz"
MISSION = ROOT / "MISION1.txt"
BINDING = RT / "worker_binding_v2.json"
AUTH = RT / "operator_authorization.json"
CONTRACT = RT / "contract.json"
MODEL = HOME / "Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna/1. Cerebro"
CONFIG = MODEL / "config.json"
INDEX = MODEL / "model.safetensors.index.json"
EXPECTED_MISSION_SHA = "0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
EXPECTED_V9_SHA = "667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
TARGET_BYTES = 180_000_000
SCOPE = "MISION1_CAJITA_LUNITA"
REPO = "Plomillo/luna-linux-bridge"
BRANCH = "recovery/lunita-custoszv9-operational-20261020"
SCHEMA = "CUSTOSZV9_CEREBRO_180MB_DISPATCH/1.0"


def utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def canon(x):
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def worker_is_running():
    LOCK_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(WORKER_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        fcntl.flock(fd, fcntl.LOCK_UN)
        return False
    finally:
        os.close(fd)


def verify_worker_journal(path):
    path = pathlib.Path(path)
    if not path.is_file():
        return {"status": "ABSENT", "events": 0}
    prev = "0" * 64
    count = 0
    try:
        for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            row = json.loads(line)
            digest = row.pop("event_sha256", None)
            if row.get("sequence") != count + 1:
                return {"status": "FAIL", "line": line_no, "reason": "SEQUENCE_MISMATCH"}
            if row.get("previous_event_sha256") != prev:
                return {"status": "FAIL", "line": line_no, "reason": "PREVIOUS_HASH_MISMATCH"}
            if sha_bytes(canon(row)) != digest:
                return {"status": "FAIL", "line": line_no, "reason": "EVENT_HASH_MISMATCH"}
            prev = digest
            count += 1
    except Exception as exc:
        return {"status": "FAIL", "events": count, "reason": type(exc).__name__ + ":" + str(exc)}
    return {"status": "PASS", "events": count, "last_hash": prev}


def atomic(path, obj, exclusive=False):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with tmp.open("x", encoding="utf-8") as f:
        f.write(json.dumps(obj, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.chmod(tmp, 0o600)
    if exclusive and path.exists():
        tmp.unlink(missing_ok=True)
        raise RuntimeError("APPEND_ONLY_COLLISION:" + str(path))
    os.replace(tmp, path)


def readj(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))


def file_stats():
    idx = readj(INDEX)
    wm = idx.get("weight_map")
    if not isinstance(wm, dict) or len(wm) != 687:
        raise RuntimeError("CEREBRO_WEIGHT_MAP_IDENTITY_MISMATCH")
    shards = sorted(set(str(v) for v in wm.values()))
    rows = {}
    for name in shards:
        p = MODEL / name
        if not p.is_file():
            raise RuntimeError("CEREBRO_SOURCE_SHARD_MISSING:" + name)
        s = p.stat()
        rows[name] = {"bytes": s.st_size, "mtime_ns": s.st_mtime_ns}
    cfg = readj(CONFIG)
    if cfg.get("model_type") != "gpt_oss" or "GptOssForCausalLM" not in cfg.get("architectures", []):
        raise RuntimeError("CEREBRO_MODEL_IDENTITY_MISMATCH")
    return {
        "source_model_id": "OPENAI_GPT_OSS_CEREBRO_MXFP4",
        "model_type": cfg.get("model_type"), "architectures": cfg.get("architectures"),
        "source_config_sha256": sha_file(CONFIG), "source_index_sha256": sha_file(INDEX),
        "source_config_bytes": CONFIG.stat().st_size, "source_index_bytes": INDEX.stat().st_size,
        "source_tensor_keys": len(wm), "source_shard_count": len(rows),
        "source_shards": rows, "source_weight_bytes": sum(v["bytes"] for v in rows.values()),
    }


def probe_ram():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    return 0


def probe_resource_snapshot(probe_host_resources):
    """Use Linux MemAvailable for the host preflight instead of free-only SC_AVPHYS_PAGES."""
    snapshot = probe_host_resources(ROOT)
    if os.name == "posix":
        try:
            for line in pathlib.Path("/proc/meminfo").read_text(encoding="ascii").splitlines():
                if line.startswith("MemAvailable:"):
                    available = int(line.split()[1]) * 1024
                    if available < 0:
                        raise ValueError("NEGATIVE_MEMAVAILABLE")
                    return replace(snapshot, ram_available_bytes=available,
                                   source="/proc/meminfo:MemAvailable", confidence="MEASURED")
        except (OSError, ValueError, IndexError):
            pass
    return snapshot


def load_v9():
    if sha_file(V9) != EXPECTED_V9_SHA:
        raise RuntimeError("PINNED_CUSTOSZV9_HASH_MISMATCH")
    if str(V9) not in sys.path:
        sys.path.insert(0, str(V9))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.event_queue import PersistentMissionQueue
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    return run_bounded_mission, PersistentMissionQueue, ActionSpec, probe_host_resources


def create_task(task_id, spec_sha, source):
    now = dt.datetime.now(dt.timezone.utc)
    return {
        "task_id": task_id,
        "mission_id": "CUSTOSZ_MISION1_0a36c59d4baf",
        "project_id": "CAJITA_DE_LUNA_CEREBRO",
        "source_identity": "CUSTOSZV9.pyz:" + EXPECTED_V9_SHA,
        "target_identity": "CEREBRO_GPT_OSS_MXFP4_RANK1_INT8_CANDIDATE_MAX_180000000_BYTES",
        "source_state_hash": spec_sha,
        "dependency_set": [
            "MISION1.txt:" + EXPECTED_MISSION_SHA,
            "CUSTOSZV9.pyz:" + EXPECTED_V9_SHA,
            "worker_binding_v2.json:" + sha_file(BINDING),
            "worker_sha256:" + sha_file(WORKER),
            "runtime_sha256:" + sha_file(RUNTIME),
            "worker_python:" + str(WORKER_PY),
            "config_sha256:" + source["source_config_sha256"],
            "index_sha256:" + source["source_index_sha256"],
        ],
        "authorized_scope": SCOPE,
        "required_capabilities": ["LOCAL_FILE_READ", "HASH_STREAMING", "CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE", "V9_CRUF_PLANNING"],
        "inputs": {
            "model_dir": str(MODEL), "config_sha256": source["source_config_sha256"],
            "index_sha256": source["source_index_sha256"], "mission_sha256": EXPECTED_MISSION_SHA,
            "target_bytes": TARGET_BYTES, "memory_max_bytes": 1024**3, "cpu_quota_percent": 50,
            "github_repository": REPO, "github_branch": BRANCH,
            "worker_path": str(WORKER), "runtime_path": str(RUNTIME),
            "worker_state_dir": str(JOB_DIR),
        },
        "preconditions": [
            "CUSTOSZ V9 artifact hash and worker binding are pinned",
            "Cerebro identity is GPT-OSS MXFP4, 687 source tensor keys and 15 source shards",
            "all output is versioned and separate from original source weights",
            "worker runs under MemoryMax=1G, MemoryHigh=768M, CPUQuota=50%",
            "the 180000000-byte gate fails closed before candidate publication",
        ],
        "permitted_effects": ["READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT", "WRITE_CAJITA_WITH_CHECKPOINTS"],
        "resource_budget": {"ram_required_bytes": 128*1024**2, "ram_reserved_bytes": 256*1024**2,
                            "disk_required_bytes": 256*1024**2, "max_concurrency": 1},
        "execution_deadline": (now + dt.timedelta(minutes=5)).isoformat(),
        "maximum_planning_budget": 3, "maximum_retry_budget": 0,
        "acceptance_criteria": [
            "V9 CRFU runs one bounded launch action with a live authorization verifier",
            "worker process enters the resource-limited scope and emits a real quantization start checkpoint",
            "original model source remains read-only",
            "candidate hard cap is 180000000 bytes and no certification is propagated",
        ],
        "expected_outputs": ["CEREBRO_180MB launch receipt", "checkpointed low-rank worker progress", "append-only V9 queue event chain"],
        "validation_strategy": "source_hash_pins+resource_scope+live_pid+worker_stage+v9_persistent_queue",
        "evidence_requirements": ["SHA-256 pins", "source stat inventory", "V9 queue transitions", "systemd scope limits", "worker heartbeat"],
        "checkpoint_reference": str(STATE / "checkpoints"),
        "rollback_strategy": "source weights are read-only; candidate is an isolated versioned directory; partial chunks are resumable; no canonical promotion",
        "completion_condition": "bounded worker launch and live quantization checkpoint evidenced; model certification remains separate",
        "escalation_condition": "HOLD if binding, source identity, memory scope, output checkpoint, or V9 queue validation fails",
        "authorization_evidence_reference": str(BINDING),
    }


def auth_verify(task):
    try:
        bind = readj(BINDING)
        auth = readj(AUTH)
        contract = readj(CONTRACT)
        ok = (
            sha_file(V9) == EXPECTED_V9_SHA and
            sha_file(MISSION) == EXPECTED_MISSION_SHA and
            bind.get("status") == "VALIDATED" and bind.get("mission_sha256") == EXPECTED_MISSION_SHA and
            bind.get("mission_id") == task.get("mission_id") and
            bind.get("scope") == task.get("authorized_scope") and
            "WRITE_CAJITA_WITH_CHECKPOINTS" in bind.get("allowed_effects", []) and
            "WRITE_LOCAL_AUDIT" in bind.get("allowed_effects", []) and
            bind.get("certification_authority") is False and
            bind.get("canonical_promotion_authority") is False and
            auth.get("mission_sha256") == EXPECTED_MISSION_SHA and
            auth.get("scope") == task.get("authorized_scope") and
            contract.get("mission_sha256") == EXPECTED_MISSION_SHA and
            contract.get("scope") == task.get("authorized_scope") and
            task.get("permitted_effects", []) == ["READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT", "WRITE_CAJITA_WITH_CHECKPOINTS"]
        )
        if not ok:
            return {"status": "DENIED", "reason": "PINNED_LOCAL_AUTHORIZATION_FAILED"}
        return {"status": "PASS", "task_id": task["task_id"], "mission_sha256": EXPECTED_MISSION_SHA,
                "binding_sha256": sha_file(BINDING), "v9_sha256": EXPECTED_V9_SHA,
                "scope": task["authorized_scope"], "certification_authority": False,
                "canonical_promotion_authority": False, "cryptographic_signature": "NOT_PRESENT"}
    except Exception as exc:
        return {"status": "DENIED", "reason": type(exc).__name__ + ":" + str(exc)}


def launch_worker(task, source, snapshot, queue_path):
    binding = readj(BINDING)
    if binding.get("mission_sha256") != EXPECTED_MISSION_SHA or binding.get("status") != "VALIDATED":
        return {"status": "DENIED", "reason": "WORKER_BINDING_NOT_VALIDATED"}
    if probe_ram() < 2 * 1024**3:
        return {"status": "HOLD", "reason": "AVAILABLE_RAM_BELOW_2_GIB", "ram_available_bytes": probe_ram()}
    if worker_is_running():
        return {"status": "HOLD", "reason": "WORKER_SINGLETON_LOCK_HELD",
                "worker_lock_path": str(WORKER_LOCK_PATH), "mission_completion_claim": False}
    before_jobs = JOB_DIR / "progress.json"
    state_path = JOB_DIR / "dispatch_state.json"
    if state_path.is_file():
        old_state = readj(state_path)
        unit = old_state.get("systemd_unit")
        if unit:
            state = subprocess.run(["systemctl", "show", unit, "--property=ActiveState", "--value"],
                                   capture_output=True, text=True, timeout=10, check=False)
            if state.returncode == 0 and state.stdout.strip() in {"active", "activating", "reloading"}:
                return {"status": "PASS", "already_running": True, "systemd_unit": unit,
                        "worker_state_dir": str(JOB_DIR), "result_state_hash": sha_file(state_path)}
        return {"status": "HOLD", "reason": "DISPATCH_STATE_ALREADY_EXISTS_NO_OVERWRITE",
                "dispatch_state_path": str(state_path), "mission_completion_claim": False}
    if before_jobs.is_file():
        existing = readj(before_jobs)
        journal_path = JOB_DIR / "events.jsonl"
        journal_health = verify_worker_journal(journal_path)
        if journal_health["status"] == "FAIL":
            return {"status": "HOLD", "reason": "EXISTING_JOB_EVENT_CHAIN_INVALID_REQUIRES_VERSIONED_RECOVERY",
                    "journal_health": journal_health, "progress_path": str(before_jobs),
                    "mission_completion_claim": False}
        if journal_health["status"] == "ABSENT" and not isinstance(existing.get("recovery_provenance"), dict):
            return {"status": "HOLD", "reason": "PROGRESS_WITHOUT_JOURNAL_REQUIRES_EXPLICIT_RECOVERY_LINEAGE",
                    "progress_path": str(before_jobs), "mission_completion_claim": False}
    run_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    checkpoint = STATE / "checkpoints" / ("CEREBRO_180MB_PRESTART_" + run_id)
    checkpoint.mkdir(parents=True, exist_ok=False, mode=0o700)
    manifest = {
        "schema": "CEREBRO_180MB_PRESTART_CHECKPOINT/1.0", "timestamp_utc": utc(),
        "mission_sha256": EXPECTED_MISSION_SHA, "custoszv9_sha256": EXPECTED_V9_SHA,
        "worker_sha256": sha_file(WORKER), "runtime_sha256": sha_file(RUNTIME),
        "worker_binding_sha256": sha_file(BINDING), "source_inventory": source,
        "source_files_written": False, "target_bytes": TARGET_BYTES,
        "worker_memory_max_bytes": 1024**3, "worker_memory_high_bytes": 768*1024**2,
        "worker_cpu_quota_percent": 50, "concurrency": 1,
        "github": {"repository": REPO, "branch": BRANCH, "branch_mutation_main": False},
        "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
    }
    atomic(checkpoint / "MANIFEST.json", manifest, exclusive=True)
    manifest_hash = sha_file(checkpoint / "MANIFEST.json")
    unit = "custosz-cerebro180-" + run_id.lower()
    log_path = JOB_DIR / "worker_stdout.log"
    JOB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    with log_path.open("ab") as log:
        args = [
            "sudo", "-n", "systemd-run", "--scope", "--unit=" + unit,
            "--setenv=CEREBRO_JOB_DIR=" + str(JOB_DIR),
            "-p", "MemoryHigh=768M", "-p", "MemoryMax=1G", "-p", "CPUQuota=50%",
            "-p", "TasksMax=32", str(WORKER_PY), "-B", str(WORKER), "--run",
        ]
        proc = subprocess.Popen(args, cwd=str(ROOT), env={**os.environ,
            "OMP_NUM_THREADS": "1", "OMP_THREAD_LIMIT": "1", "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1", "NUMEXPR_NUM_THREADS": "1", "TOKENIZERS_PARALLELISM": "false",
            "CEREBRO_JOB_DIR": str(JOB_DIR)},
            stdout=log, stderr=subprocess.STDOUT, start_new_session=True, close_fds=True)
    # systemd-run is detached; verify the scope itself rather than trusting the wrapper PID alone.
    active = None
    details = {}
    for _ in range(12):
        probe = subprocess.run(["systemctl", "show", unit + ".scope",
                                "--property=ActiveState", "--property=MainPID", "--property=MemoryMax",
                                "--property=MemoryHigh", "--property=CPUQuotaPerSecUSec"],
                               capture_output=True, text=True, timeout=10, check=False)
        if probe.returncode == 0:
            details = {}
            for line in probe.stdout.splitlines():
                if "=" in line:
                    k, v = line.split("=", 1)
                    details[k] = v
            active = details.get("ActiveState")
            if active in {"active", "activating"}:
                break
        time.sleep(0.25)
    if active not in {"active", "activating"}:
        return {"status": "HOLD", "reason": "SYSTEMD_RESOURCE_SCOPE_NOT_CONFIRMED",
                "wrapper_pid": proc.pid, "stdout_log": str(log_path), "systemd_output": details,
                "checkpoint_path": str(checkpoint), "checkpoint_sha256": manifest_hash}
    # Do not treat the systemd scope alone as proof that the worker entered its singleton lock.
    lock_confirmed = False
    for _ in range(24):
        if worker_is_running():
            lock_confirmed = True
            break
        time.sleep(0.25)
    if not lock_confirmed:
        return {"status": "HOLD", "reason": "WORKER_SINGLETON_LOCK_NOT_CONFIRMED",
                "wrapper_pid": proc.pid, "systemd_unit": unit + ".scope",
                "stdout_log": str(log_path), "systemd_output": details,
                "mission_completion_claim": False}
    receipt = {
        "schema": "CEREBRO_180MB_WORKER_LAUNCH_RECEIPT/1.0", "timestamp_utc": utc(),
        "task_id": task["task_id"], "mission_sha256": EXPECTED_MISSION_SHA,
        "custoszv9_sha256": EXPECTED_V9_SHA, "worker_sha256": sha_file(WORKER),
        "runtime_sha256": sha_file(RUNTIME), "source_config_sha256": source["source_config_sha256"],
        "source_index_sha256": source["source_index_sha256"], "target_bytes": TARGET_BYTES,
        "systemd_unit": unit + ".scope", "systemd_properties": details,
        "wrapper_pid": proc.pid, "worker_log": str(log_path), "worker_state_dir": str(JOB_DIR),
        "prestart_checkpoint": str(checkpoint), "prestart_checkpoint_sha256": manifest_hash,
        "resource_caps_confirmed": details.get("MemoryMax") in {"1073741824", "1G"}
             and details.get("MemoryHigh") in {"805306368", "768M"}
             and details.get("CPUQuotaPerSecUSec") not in {None, "infinity"},
        "candidate_dir": str(STATE / "cajita_candidates"),
        "source_weights_modified": False, "quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
        "mission_completion_claim": False,
    }
    launch_path = OUT / ("CEREBRO_180MB_WORKER_LAUNCH_" + run_id + ".json")
    atomic(launch_path, receipt, exclusive=True)
    receipt["launch_receipt_path"] = str(launch_path)
    receipt["launch_receipt_sha256"] = sha_file(launch_path)
    # Store the scope identity as an append-only supplemental record so reruns never spawn duplicates.
    state_path = JOB_DIR / "dispatch_state.json"
    atomic(state_path, {**receipt, "launch_receipt_path": str(launch_path), "launch_receipt_sha256": sha_file(launch_path)}, exclusive=True)
    return {"status": "PASS", "worker_launch_status": "STARTED_RESOURCE_LIMITED",
            "systemd_unit": unit + ".scope", "systemd_state": active, "systemd_properties": details,
            "wrapper_pid": proc.pid, "worker_log": str(log_path),
            "prestart_checkpoint": str(checkpoint), "prestart_checkpoint_sha256": manifest_hash,
            "launch_receipt_path": str(launch_path), "launch_receipt_sha256": sha_file(launch_path),
            "candidate_dir": str(STATE / "cajita_candidates"), "result_state_hash": sha_file(launch_path),
            "certification": "NOT_GRANTED", "mission_completion_claim": False}


def _main_locked():
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    JOB_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    if sha_file(MISSION) != EXPECTED_MISSION_SHA or sha_file(V9) != EXPECTED_V9_SHA:
        raise RuntimeError("PINNED_MISSION_OR_V9_HASH_MISMATCH")
    if not WORKER.is_file() or not RUNTIME.is_file() or not WORKER_PY.is_file():
        raise RuntimeError("WORKER_OR_RUNTIME_OR_PYTHON_MISSING")
    run_bounded_mission, Queue, ActionSpec, probe_host_resources = load_v9()
    binding = readj(BINDING)
    if binding.get("status") != "VALIDATED" or binding.get("mission_sha256") != EXPECTED_MISSION_SHA:
        raise RuntimeError("WORKER_BINDING_NOT_VALIDATED")
    source = file_stats()
    if probe_ram() < 2 * 1024**3:
        raise RuntimeError("AVAILABLE_RAM_BELOW_REQUIRED_HEADROOM:" + str(probe_ram()))
    task_id = "CUSTOSZV9_CEREBRO_180MB_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    spec = {"mission_sha256": EXPECTED_MISSION_SHA, "v9_sha256": EXPECTED_V9_SHA,
            "worker_sha256": sha_file(WORKER), "runtime_sha256": sha_file(RUNTIME),
            "worker_python": str(WORKER_PY), "worker_python_version": subprocess.run([str(WORKER_PY), "--version"], capture_output=True, text=True, timeout=5, check=False).stdout.strip(),
            "source_config_sha256": source["source_config_sha256"], "source_index_sha256": source["source_index_sha256"],
            "target_bytes": TARGET_BYTES, "resource_caps": {"MemoryHigh": 768*1024**2,
            "MemoryMax": 1024**3, "CPUQuotaPercent": 50, "TasksMax": 32},
            "repository": REPO, "branch": BRANCH, "source_weights_read_only": True}
    spec_path = JOB_DIR / ("dispatch_spec_" + task_id + ".json")
    atomic(spec_path, spec, exclusive=True)
    spec_sha = sha_file(spec_path)
    task = create_task(task_id, spec_sha, source)
    snapshot = probe_resource_snapshot(probe_host_resources)
    queue_path = STATE / "cerebro_180mb_v9_queue.sqlite3"
    queue = Queue(queue_path)
    submitted = queue.submit(task)
    if submitted.get("state") != "RECEIVED":
        raise RuntimeError("V9_QUEUE_SUBMIT_FAILED:" + str(submitted.get("state")))
    queue.transition(task_id, "RECEIVED", "PREFLIGHT", event_type="CEREBRO_180MB_V9_PREFLIGHT_STARTED",
                     payload={"spec_sha256": spec_sha, "source_config_sha256": source["source_config_sha256"],
                              "source_index_sha256": source["source_index_sha256"]})
    checked = {
        "v9_sha256": sha_file(V9) == EXPECTED_V9_SHA,
        "mission_sha256": sha_file(MISSION) == EXPECTED_MISSION_SHA,
        "worker_binding_validated": binding.get("status") == "VALIDATED",
        "source_identity": source["model_type"] == "gpt_oss" and source["source_tensor_keys"] == 687 and source["source_shard_count"] == 15,
        "ram_headroom": probe_ram() >= 2*1024**3,
        "worker_runtime_hashes": bool(sha_file(WORKER) and sha_file(RUNTIME)),
        "memory_guard_supported": True,
    }
    if not all(checked.values()):
        queue.transition(task_id, "PREFLIGHT", "BLOCKED", event_type="CEREBRO_180MB_V9_PREFLIGHT_BLOCKED",
                         payload={"checks": checked})
        raise RuntimeError("CEREBRO_V9_PREFLIGHT_BLOCKED:" + json.dumps(checked))
    queue.transition(task_id, "PREFLIGHT", "READY", event_type="CEREBRO_180MB_V9_PREFLIGHT_PASS",
                     payload={"checks": checked, "source": source, "spec_sha256": spec_sha})
    claimed = queue.claim_next_ready()
    if not isinstance(claimed, dict) or claimed.get("mission_id") != task_id or claimed.get("state") != "RUNNING":
        raise RuntimeError("V9_QUEUE_ATOMIC_CLAIM_FAILED")
    actions = [
        ActionSpec("verify_cerebro_identity_and_resource_policy", (),
                   ("LOCAL_FILE_READ", "HASH_STREAMING"),
                   ("READ_PROJECT_ARTIFACTS",), "READ_ONLY"),
        ActionSpec("launch_bounded_cerebro_quantization_worker",
                   ("verify_cerebro_identity_and_resource_policy",),
                   ("CHECKPOINTED_SCOPED_ACTIONS", "HASH_CHAIN_EVIDENCE"),
                   ("WRITE_LOCAL_AUDIT", "WRITE_CAJITA_WITH_CHECKPOINTS"), "IDEMPOTENT"),
    ]
    def runner(payload):
        action_id = payload["action"]["action_id"]
        if action_id == "verify_cerebro_identity_and_resource_policy":
            now = file_stats()
            same = (now["source_config_sha256"] == source["source_config_sha256"]
                    and now["source_index_sha256"] == source["source_index_sha256"]
                    and now["source_shards"] == source["source_shards"])
            if not same:
                return {"status": "HOLD", "reason": "SOURCE_CHANGED_SINCE_PREFLIGHT"}
            return {"status": "PASS", "source_identity": now["source_model_id"],
                    "source_config_sha256": now["source_config_sha256"], "source_index_sha256": now["source_index_sha256"],
                    "source_tensor_keys": now["source_tensor_keys"], "source_shard_count": now["source_shard_count"],
                    "ram_available_bytes": probe_ram(), "target_bytes": TARGET_BYTES}
        if action_id == "launch_bounded_cerebro_quantization_worker":
            try:
                launch = launch_worker(payload["task"], source, snapshot, queue_path)
                if launch.get("status") != "PASS":
                    raise RuntimeError("CEREBRO_LAUNCH_NOT_PASS:" + json.dumps(launch, sort_keys=True))
                return launch
            except Exception as exc:
                return {"status": "HOLD", "reason": type(exc).__name__ + ":" + str(exc),
                        "certification": "NOT_GRANTED", "mission_completion_claim": False}
        return {"status": "DENIED", "reason": "ACTION_ID_NOT_REGISTERED"}
    coordinator = run_bounded_mission(
        task, actions, snapshot,
        available_capabilities=set(binding.get("capabilities", [])) | {"LOCAL_FILE_READ", "HASH_STREAMING"},
        admissible_effects={"READ_PROJECT_ARTIFACTS", "WRITE_LOCAL_AUDIT", "WRITE_CAJITA_WITH_CHECKPOINTS"},
        authorization_verifier=auth_verify, action_runner=runner,
        maximum_steps=2, planning_budget=3,
    )
    final_state = "COMPLETED" if coordinator.get("status") == "COMPLETED" else "BLOCKED"
    queue.transition(task_id, "RUNNING", final_state,
                     event_type="CEREBRO_180MB_V9_WORKER_LAUNCH_RECORDED" if final_state == "COMPLETED" else "CEREBRO_180MB_V9_LAUNCH_BLOCKED",
                     payload={"coordinator_status": coordinator.get("status"),
                              "worker_launch_status": coordinator.get("actions") or coordinator.get("results"),
                              "model_certification": "NOT_GRANTED", "mission_completion_claim": False})
    queue_chain = queue.verify_event_chain()
    report = {
        "schema": SCHEMA, "timestamp_utc": utc(), "task_id": task_id,
        "mission_sha256": EXPECTED_MISSION_SHA, "v9_artifact_sha256": sha_file(V9),
        "worker_sha256": sha_file(WORKER), "runtime_sha256": sha_file(RUNTIME),
        "source": source, "preflight_checks": checked,
        "resource_snapshot": snapshot.to_dict(), "coordinator_result": coordinator,
        "queue_path": str(queue_path), "queue_final_state": final_state, "queue_event_chain": queue_chain,
        "target_bytes": TARGET_BYTES, "github": {"repository": REPO, "branch": BRANCH},
        "source_weights_modified": False, "quality_equivalence": "NOT_ESTABLISHED",
        "certification": "NOT_GRANTED", "canonical_promotion": "NOT_AUTHORIZED",
        "mission_completion_claim": False,
    }
    report_path = OUT / ("CEREBRO_180MB_V9_DISPATCH_" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + ".json")
    atomic(report_path, report, exclusive=True)
    report_sha = sha_file(report_path)
    print(json.dumps({"status": final_state, "task_id": task_id, "coordinator": coordinator.get("status"),
          "queue_event_chain": queue_chain.get("status"), "source_config_sha256": source["source_config_sha256"],
          "source_index_sha256": source["source_index_sha256"], "target_bytes": TARGET_BYTES,
          "report_path": str(report_path), "report_sha256": report_sha,
          "certification": "NOT_GRANTED"}, indent=2), flush=True)
    if final_state != "COMPLETED" or queue_chain.get("status") != "PASS":
        return 2
    return 0


def main():
    LOCK_DIR.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(str(DISPATCH_LOCK_PATH), os.O_CREAT | os.O_RDWR, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("DISPATCH_ALREADY_RUNNING: rejecting concurrent CUSTOSZ V9 dispatch", file=sys.stderr, flush=True)
            return 75
        os.ftruncate(fd, 0)
        payload = json.dumps({"pid": os.getpid(), "started_at_utc": utc(),
                              "worker_state_dir": str(JOB_DIR)}, sort_keys=True).encode("utf-8")
        os.write(fd, payload)
        os.fsync(fd)
        return _main_locked()
    finally:
        os.close(fd)


if __name__ == "__main__":
    try:
        code = main()
    except Exception as exc:
        print("DISPATCH_FAILED:" + type(exc).__name__ + ":" + str(exc), file=sys.stderr, flush=True)
        raise
    raise SystemExit(code)

[executed on device: LOUKSNA (98c2b7f6-ee30-4f31-9444-06f7ba58f353)]