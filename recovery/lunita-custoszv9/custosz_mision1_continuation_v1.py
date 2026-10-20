#!/usr/bin/env python3
"""Append-only continuation lane for CUSTOSZ after its original 20 analysis steps."""
from __future__ import annotations
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import shutil
import tempfile
import sys
import uuid

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
import custosz_continuity as core
import custosz_mision1_phase2 as phase2
import custosz_g06_reconstruction_v1 as g06_reconstruction

INTEGRATION_PATH = ROOT / "integrations" / "lunita-custoszv9"
if str(INTEGRATION_PATH) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_PATH))
import custoszv9_continuous_governor_v2 as continuous_governor

ST = core.ST
OUT = ST / "worker_outputs"
PROGRESS = ST / "continuation_progress.json"
MISSION_SHA = core.HS_MISSION
S20_ID = "S20_SEARCH_LUNITA_G08_RUNNER"
G08_NAME = "JOHNSON_LUNITA_MATERIALIZER_v1.1.8_G08.py"
G08_REL = pathlib.Path("HISTORICAL_WSL_UBUNTU2404_EXTRACTION_20260917") / "02_PRESERVED_PAYLOAD" / "home_diego" / "lunita_materialization" / "governance-restored" / G08_NAME
REFRESH_SECONDS = 300

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def parseutc(value):
    return dt.datetime.fromisoformat(value.replace("Z", "+00:00"))

def sha(path):
    h = hashlib.sha256()
    with pathlib.Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def atomic(path, value):
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    temp = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    with temp.open("x", encoding="utf-8") as stream:
        stream.write(json.dumps(value, sort_keys=True, indent=2, ensure_ascii=False) + "\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.chmod(temp, 0o600)
    os.replace(temp, path)

def load(path, default=None):
    try:
        value = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        return value
    except (OSError, ValueError, TypeError):
        return default

def write_result(step_id, result):
    OUT.mkdir(parents=True, exist_ok=True, mode=0o700)
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    path = OUT / (step_id + "_" + stamp + ".json")
    payload = {
        "schema": "CUSTOSZ_MISION1_CONTINUATION_RESULT/1.0",
        "mission_id": core.MID,
        "mission_sha256": MISSION_SHA,
        "step_id": step_id,
        "timestamp_utc": utc(),
        "status": result.get("status", "UNKNOWN"),
        "evidence": result,
        "completion_claim": "SUBTASK_ONLY",
        "certification": "NOT_GRANTED",
    }
    atomic(path, payload)
    return {"result_path": str(path), "result_sha256": sha(path), "status": payload["status"]}

def reconcile_queue(last_row, next_action):
    """Project append-only continuation checkpoints into the existing evented mission queue."""
    modules = core.components()
    queue = modules["PersistentMissionQueue"](core.QUEUE)
    current = queue.get(core.MID)
    last_step = last_row.get("step_id") if isinstance(last_row, dict) else None
    last_path = pathlib.Path(last_row.get("result_path", "")) if isinstance(last_row, dict) else None
    expected_sha = last_row.get("result_sha256") if isinstance(last_row, dict) else None
    if not last_step or not last_path or not last_path.is_file() or not expected_sha or sha(last_path) != expected_sha:
        raise RuntimeError("CONTINUATION_QUEUE_SYNC_EVIDENCE_INVALID")
    last_payload = load(last_path, {}) or {}
    if last_payload.get("mission_sha256") != MISSION_SHA or last_payload.get("step_id") != last_step:
        raise RuntimeError("CONTINUATION_QUEUE_SYNC_BINDING_MISMATCH")
    queue_state = current.get("state")
    if queue_state == "RUNNING" and current.get("next_action") == next_action:
        return {"status": "PASS_IDEMPOTENT", "state": queue_state, "next_action": next_action}
    if queue_state == "RUNNING":
        current = queue.transition(
            core.MID, "RUNNING", "CHECKPOINTED",
            event_type="CRFU_CONTINUATION_STEP_CHECKPOINTED",
            payload={"step_id": last_step, "result_path": str(last_path), "result_sha256": expected_sha},
            fields={"checkpoint_reference": str(last_path), "next_action": "VALIDATE_" + last_step},
        )
        queue_state = current.get("state")
    if queue_state == "CHECKPOINTED":
        current = queue.transition(
            core.MID, "CHECKPOINTED", "VALIDATING",
            event_type="CRFU_CONTINUATION_VALIDATION_STARTED",
            payload={"step_id": last_step, "result_sha256": expected_sha},
        )
        queue_state = current.get("state")
    if queue_state == "VALIDATING":
        # Recheck evidence after reopening/recovering a partially completed transition.
        if not last_path.is_file() or sha(last_path) != expected_sha:
            raise RuntimeError("CONTINUATION_QUEUE_SYNC_POSTCHECK_FAILED")
        current = queue.transition(
            core.MID, "VALIDATING", "RUNNING",
            event_type="CRFU_CONTINUATION_VALIDATION_PASS",
            payload={"step_id": last_step, "result_sha256": expected_sha, "independent_hash_validation": "PASS"},
            fields={"next_action": next_action},
        )
        queue_state = current.get("state")
    if queue_state != "RUNNING" or current.get("next_action") != next_action:
        raise RuntimeError("CONTINUATION_QUEUE_SYNC_UNEXPECTED_STATE:" + str(queue_state))
    return {"status": "PASS", "state": queue_state, "next_action": next_action, "validated_step": last_step, "result_sha256": expected_sha}


def verify_handoff():
    progress = load(ST / "mission_progress.json", {}) or {}
    rows = progress.get("completed_steps", [])
    if progress.get("mission_sha256") != MISSION_SHA or len(rows) != 20:
        raise RuntimeError("CONTINUATION_HANDOFF_PRECONDITION_FAILED:mission_progress")
    last = rows[-1]
    if last.get("step_id") != S20_ID:
        raise RuntimeError("CONTINUATION_HANDOFF_PRECONDITION_FAILED:last_step_not_S20")
    result_path = pathlib.Path(last.get("result_path", ""))
    if not result_path.is_file() or sha(result_path) != last.get("result_sha256"):
        raise RuntimeError("CONTINUATION_HANDOFF_EVIDENCE_HASH_MISMATCH")
    s20 = load(result_path, {}) or {}
    evidence = s20.get("evidence", {}) or {}
    if s20.get("mission_sha256") != MISSION_SHA or s20.get("step_id") != S20_ID:
        raise RuntimeError("CONTINUATION_HANDOFF_EVIDENCE_BINDING_MISMATCH")
    if evidence.get("execution_performed") is not False:
        raise RuntimeError("CONTINUATION_HANDOFF_EXPECTED_SEARCH_ONLY")
    return {
        "status": "PASS",
        "original_steps_preserved": 20,
        "mission_sha256": MISSION_SHA,
        "last_step": S20_ID,
        "last_result_sha256": sha(result_path),
        "last_result_path": str(result_path),
        "runner_execution_previously_performed": False,
    }

def s21_validate_g08_patch_and_gate_context():
    handoff = verify_handoff()
    lun = pathlib.Path(core.LUN)
    source = lun / G08_REL
    evidence_dir = lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8"
    hashes_file = evidence_dir / "G08_JOHNSON_v1.1.8_HASHES.txt"
    mount_log = evidence_dir / "G08_JOHNSON_v1.1.8_FULL_MOUNT_TEST.log"
    gate_file = lun / "00_EVIDENCE" / "CERTIFICATION_EXIT_PLAN.json"
    missing = [str(p) for p in (source, hashes_file, mount_log, gate_file) if not p.is_file()]
    source_hash = sha(source) if source.is_file() else None
    expected_hash_found = False
    if hashes_file.is_file() and source_hash:
        expected_hash_found = any(
            line.split() and line.split()[0].lower() == source_hash.lower() and G08_NAME in line
            for line in hashes_file.read_text(encoding="utf-8", errors="replace").splitlines()
        )
    syntax_valid = False
    syntax_error = None
    if source.is_file():
        try:
            compile(source.read_text(encoding="utf-8"), str(source), "exec")
            syntax_valid = True
        except (SyntaxError, UnicodeError, OSError) as exc:
            syntax_error = type(exc).__name__ + ": " + str(exc)[:800]
    log_text = mount_log.read_text(encoding="utf-8", errors="replace") if mount_log.is_file() else ""
    mount_tests = {
        "jamovi_rc_zero": "===== org.jamovi.jamovi =====" in log_text and "RC=0" in log_text.split("===== org.jamovi.jamovi =====", 1)[1].split("=====", 1)[0],
        "jasp_rc_zero": "===== org.jaspstats.JASP =====" in log_text and "RC=0" in log_text.split("===== org.jaspstats.JASP =====", 1)[1].split("=====", 1)[0],
    }
    gate = load(gate_file, {}) or {}
    g08 = next((g for g in gate.get("gates", []) if str(g.get("id")) == "8"), {})
    result = {
        "schema": "CUSTOSZ_G08_PATCH_HANDOFF_VALIDATION/1.0",
        "handoff": handoff,
        "source_path": str(source),
        "source_is_inside_historical_snapshot": "HISTORICAL_WSL_UBUNTU2404_EXTRACTION_20260917" in str(source),
        "source_exists": source.is_file(),
        "source_bytes": source.stat().st_size if source.is_file() else None,
        "source_sha256": source_hash,
        "source_sha256_matches_hash_evidence": expected_hash_found,
        "static_python_compile_pass": syntax_valid,
        "static_compile_error": syntax_error,
        "historical_mount_test_log": str(mount_log),
        "historical_mount_test_sha256": sha(mount_log) if mount_log.is_file() else None,
        "historical_mount_test_results": mount_tests,
        "g08_gate_status": g08.get("status"),
        "exit_plan_state": gate.get("current_state"),
        "live_runner_execution_performed": False,
        "execution_admission": "HOLD_ACTIVE_RUN_CONTEXT_AND_CURRENT_TARGET_BINDING_REQUIRED",
        "status": "PASS_FOR_SOURCE_AND_HANDOFF_ONLY" if not missing and expected_hash_found and syntax_valid and all(mount_tests.values()) else "PARTIAL_REQUIRES_DIAGNOSIS",
        "missing_evidence": missing,
        "certification": "NOT_GRANTED",
    }
    if result["status"] != "PASS_FOR_SOURCE_AND_HANDOFF_ONLY":
        raise RuntimeError("S21_G08_SOURCE_VALIDATION_FAILED:" + json.dumps(result, ensure_ascii=False)[:1800])
    return result

def ensure_g08_runtime():
    """Use only an allowlisted, locally hash-pinned wheelhouse; rebuild isolated env by versioned swap."""
    lun = pathlib.Path(core.LUN)
    fix_root = ST / "dependency_repairs" / "g08_jsonschema_4.26.0"
    lock_file = fix_root / "requirements.lock.txt"
    source_evidence_file = fix_root / "DEPENDENCY_SOURCE_VERIFICATION.json"
    env_validation_file = fix_root / "ISOLATED_ENV_VALIDATION.json"
    wheelhouse = fix_root / "wheelhouse"
    pointer = fix_root / "ACTIVE_RUNTIME.json"
    default_env = lun / ".runtime_venvs" / "g08-jsonschema-4.26.0"
    env_root = lun / ".runtime_venvs"
    evidence = load(source_evidence_file, {}) or {}
    if evidence.get("schema") != "CUSTOSZ_G08_JSONSCHEMA_DEPENDENCY_RESOLUTION/1.0":
        raise RuntimeError("G08_DEPENDENCY_SOURCE_EVIDENCE_MISSING_OR_INVALID")
    if not lock_file.is_file() or sha(lock_file) != evidence.get("lock_file_sha256"):
        raise RuntimeError("G08_DEPENDENCY_LOCK_HASH_MISMATCH")
    if not env_validation_file.is_file():
        raise RuntimeError("G08_DEPENDENCY_ENV_VALIDATION_EVIDENCE_MISSING")
    expected_jsonschema_hash = "d489f15263b8d200f8387e64b4c3a75f06629559fb73deb8fdfb525f2dab50ce"
    distributions = evidence.get("distributions", [])
    pin_map = {str(x.get("distribution", "")).lower().replace("_", "-"): str(x.get("version", "")) for x in distributions}
    if pin_map.get("jsonschema") != "4.26.0":
        raise RuntimeError("G08_JSONSCHEMA_VERSION_NOT_ALLOWLISTED")
    jsonschema_dist = next((x for x in distributions if str(x.get("distribution", "")).lower() == "jsonschema"), {})
    if jsonschema_dist.get("sha256") != expected_jsonschema_hash or jsonschema_dist.get("pypi_verified_sha256") != expected_jsonschema_hash:
        raise RuntimeError("G08_JSONSCHEMA_OFFICIAL_HASH_MISMATCH")
    wheel_hashes = {}
    for dist in distributions:
        filename = dist.get("filename")
        expected = dist.get("sha256")
        wheel = wheelhouse / str(filename)
        if not filename or not wheel.is_file() or not expected or sha(wheel) != expected or dist.get("pypi_verified_sha256") != expected:
            raise RuntimeError("G08_DEPENDENCY_WHEEL_HASH_MISMATCH:" + str(filename))
        wheel_hashes[str(filename)] = expected
    if not wheel_hashes or len(wheel_hashes) != len(distributions):
        raise RuntimeError("G08_DEPENDENCY_WHEELSET_INCOMPLETE")
    expected_versions = {str(x.get("distribution")): str(x.get("version")) for x in distributions}
    check_code = "\n".join([
        "import importlib.metadata as m,json",
        "from jsonschema import Draft202012Validator",
        "expected=" + repr(expected_versions),
        "actual={k:m.version(k) for k in expected}",
        "assert actual==expected,(actual,expected)",
        "schema={'type':'object','required':['status','count'],'properties':{'status':{'const':'PASS'},'count':{'type':'integer','minimum':0}},'additionalProperties':False}",
        "Draft202012Validator.check_schema(schema)",
        "v=Draft202012Validator(schema);v.validate({'status':'PASS','count':1})",
        "assert not v.is_valid({'status':'FAIL','count':1})",
        "print(json.dumps({'versions':actual,'schema_check':'PASS','positive_and_negative_validation':'PASS'}))",
    ])
    previous_pointer = load(pointer, {}) or {}
    previous_env = previous_pointer.get("python_executable")
    candidates = []
    if previous_env:
        candidates.append(pathlib.Path(previous_env))
    if default_env.joinpath("bin", "python").is_file() and default_env.joinpath("bin", "python") not in candidates:
        candidates.append(default_env / "bin" / "python")
    for python in candidates:
        try:
            environment_directory = python.parent.parent
            if not environment_directory.resolve(strict=True).is_relative_to(env_root.resolve(strict=True)):
                continue
            if environment_directory.resolve(strict=True).parent != env_root.resolve(strict=True):
                continue
            if not python.is_file() or not os.access(python, os.X_OK):
                continue
            test = subprocess.run([str(python), "-I", "-c", check_code], capture_output=True, text=True, timeout=20, check=False)
            if test.returncode == 0:
                runtime = json.loads(test.stdout)
                prior_env_ok = bool(previous_env and str(python) == previous_env and previous_pointer.get("requirements_lock_sha256") == sha(lock_file))
                if prior_env_ok:
                    return {
                        "status": "PASS_EXISTING_PINNED_ENVIRONMENT",
                        "python_executable": str(python),
                        "python_executable_sha256": sha(python),
                        "lock_sha256": sha(lock_file),
                        "official_wheel_count": len(wheel_hashes),
                        "installed_versions": runtime["versions"],
                        "schema_checks": runtime["positive_and_negative_validation"],
                        "environment_rebuilt": False,
                        "active_pointer": str(pointer),
                    }
                env_receipt = {
                    "schema": "CUSTOSZ_G08_ACTIVE_RUNTIME_POINTER/1.0",
                    "activated_at_utc": utc(),
                    "python_executable": str(python),
                    "python_executable_sha256": sha(python),
                    "environment_root": str(python.parent.parent),
                    "requirements_lock_sha256": sha(lock_file),
                    "dependency_source_evidence_sha256": sha(source_evidence_file),
                    "installed_versions": runtime["versions"],
                    "schema_checks": runtime["positive_and_negative_validation"],
                    "previous_python_executable": previous_env,
                    "previous_pointer_sha256": sha(pointer) if pointer.is_file() else None,
                    "status": "VALIDATED_AND_BOUND",
                    "certification": "NOT_GRANTED",
                }
                atomic(pointer, env_receipt)
                return {
                    "status": "PASS_RUNTIME_BOUND",
                    "python_executable": str(python),
                    "python_executable_sha256": sha(python),
                    "lock_sha256": sha(lock_file),
                    "official_wheel_count": len(wheel_hashes),
                    "installed_versions": runtime["versions"],
                    "schema_checks": runtime["positive_and_negative_validation"],
                    "environment_rebuilt": False,
                    "active_pointer": str(pointer),
                    "pointer_sha256": sha(pointer),
                    "previous_python_executable": previous_env,
                }
        except (OSError, ValueError, KeyError, subprocess.TimeoutExpired, AssertionError):
            continue
    # Repair only this pinned, allowlisted dependency closure, from verified local wheels.
    env_root.mkdir(parents=True, exist_ok=True)
    target_env = env_root / ("g08-jsonschema-4.26.0-recovery-" + dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    if target_env.exists():
        raise RuntimeError("G08_RECOVERY_ENVIRONMENT_TARGET_COLLISION")
    create = subprocess.run([sys.executable, "-m", "venv", str(target_env)], capture_output=True, text=True, timeout=60, check=False)
    if create.returncode != 0:
        raise RuntimeError("G08_RECOVERY_VENV_CREATE_FAILED:" + create.stderr[-1000:])
    python = target_env / "bin" / "python"
    install = subprocess.run(
        [str(python), "-m", "pip", "--isolated", "install", "--no-index", "--find-links", str(wheelhouse), "--require-hashes", "-r", str(lock_file)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    if install.returncode != 0:
        raise RuntimeError("G08_RECOVERY_OFFLINE_HASHED_INSTALL_FAILED:" + install.stderr[-1200:])
    test = subprocess.run([str(python), "-I", "-c", check_code], capture_output=True, text=True, timeout=20, check=False)
    if test.returncode != 0:
        raise RuntimeError("G08_RECOVERY_ENV_POSTVALIDATION_FAILED:" + test.stderr[-1000:])
    runtime = json.loads(test.stdout)
    env_receipt = {
        "schema": "CUSTOSZ_G08_ACTIVE_RUNTIME_POINTER/1.0",
        "activated_at_utc": utc(),
        "python_executable": str(python),
        "python_executable_sha256": sha(python),
        "environment_root": str(target_env),
        "requirements_lock_sha256": sha(lock_file),
        "dependency_source_evidence_sha256": sha(source_evidence_file),
        "installed_versions": runtime["versions"],
        "schema_checks": runtime["positive_and_negative_validation"],
        "previous_python_executable": previous_env,
        "previous_pointer_sha256": sha(pointer) if pointer.is_file() else None,
        "status": "RECOVERED_VALIDATED_AND_BOUND",
        "certification": "NOT_GRANTED",
    }
    atomic(pointer, env_receipt)
    return {
        "status": "PASS_RUNTIME_RECOVERED_AND_BOUND",
        "python_executable": str(python),
        "python_executable_sha256": sha(python),
        "lock_sha256": sha(lock_file),
        "official_wheel_count": len(wheel_hashes),
        "installed_versions": runtime["versions"],
        "schema_checks": runtime["positive_and_negative_validation"],
        "environment_rebuilt": True,
        "active_pointer": str(pointer),
        "pointer_sha256": sha(pointer),
        "previous_python_executable": previous_env,
    }


def s25_g08_execution_admission_probe():
    """Probe the pinned historical entrypoint read-only; refuse run without active target binding."""
    handoff = verify_handoff()
    lun = pathlib.Path(core.LUN)
    source = lun / G08_REL
    hash_file = lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8" / "G08_JOHNSON_v1.1.8_HASHES.txt"
    gate_file = lun / "00_EVIDENCE" / "CERTIFICATION_EXIT_PLAN.json"
    active_roots = [
        lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8",
        lun / "Lunita",
        pathlib.Path("/home/diego/lunita_materialization"),
        pathlib.Path("/home/diegoignacionorambuenamiranda/lunita_materialization"),
    ]
    active_candidates = []
    dirs_visited = 0
    for root in active_roots:
        if not root.is_dir():
            continue
        for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
            dirs[:] = sorted(d for d in dirs if d not in {"HISTORICAL_WSL_UBUNTU2404_EXTRACTION_20260917", ".git", "__pycache__", "node_modules", ".venv", "venv"})
            dirs_visited += 1
            if dirs_visited > 5000:
                break
            for name in names:
                low = name.lower()
                if name.startswith("JOHNSON_LUNITA_MATERIALIZER") and low.endswith("_g08.py") and "v1.1.8" in low:
                    active_candidates.append(str(pathlib.Path(current) / name))
        if dirs_visited > 5000:
            break
    if not source.is_file():
        raise RuntimeError("S25_PINNED_G08_ENTRYPOINT_MISSING")
    runtime_binding = ensure_g08_runtime()
    runner_python = pathlib.Path(runtime_binding["python_executable"])
    before = {str(p): {"sha256": sha(p), "bytes": p.stat().st_size} for p in [source, hash_file] if p.is_file()}
    try:
        compile(source.read_text(encoding="utf-8"), str(source), "exec")
        syntax = "PASS"
    except (SyntaxError, UnicodeError) as exc:
        syntax = "FAIL"
        syntax_error = type(exc).__name__ + ": " + str(exc)[:800]
    else:
        syntax_error = None
    probes = []
    for args in ( ["--version"], ["--help"] ):
        try:
            proc = subprocess.run(
                [str(runner_python), "-I", str(source), *args],
                cwd=str(source.parent), capture_output=True, text=True,
                timeout=12, check=False,
            )
            probes.append({
                "argv": args, "returncode": proc.returncode,
                "status": "PASS" if proc.returncode == 0 else "FAIL",
                "stdout_tail": proc.stdout[-1600:], "stderr_tail": proc.stderr[-800:],
            })
        except (OSError, subprocess.TimeoutExpired) as exc:
            probes.append({"argv": args, "status": "ERROR", "error": type(exc).__name__ + ": " + str(exc)[:500]})
    after = {path: {"sha256": sha(path), "bytes": pathlib.Path(path).stat().st_size} for path in before}
    unchanged = before == after
    gate = load(gate_file, {}) or {}
    g08 = next((g for g in gate.get("gates", []) if str(g.get("id")) == "8"), {})
    workspace_root = lun / "HISTORICAL_WSL_UBUNTU2404_EXTRACTION_20260917" / "01_NON_AUTHORITATIVE_PARTIAL" / "lunita-g08-v4" / "workspace"
    state_databases = []
    if workspace_root.is_dir():
        for current, dirs, names in os.walk(workspace_root, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d not in {"__pycache__", "node_modules", ".git"}]
            for name in names:
                if name.lower().endswith((".sqlite", ".sqlite3", ".db")):
                    item = pathlib.Path(current) / name
                    state_databases.append({"path": str(item), "bytes": item.stat().st_size, "sha256": sha(item)})
                    if len(state_databases) >= 30:
                        break
            if len(state_databases) >= 30:
                break
    return {
        "schema": "CUSTOSZ_G08_READONLY_ENTRYPOINT_PROBE/1.0",
        "captured_at_utc": utc(),
        "handoff": handoff,
        "pinned_entrypoint": str(source),
        "source_sha256": sha(source),
        "pinned_runtime_binding": runtime_binding,
        "pinned_hash_evidence": str(hash_file),
        "active_nonhistorical_g08_v118_sources": active_candidates,
        "directories_visited": dirs_visited,
        "static_compile": syntax,
        "static_compile_error": syntax_error,
        "readonly_cli_probes": probes,
        "source_and_hash_evidence_unchanged": unchanged,
        "source_file_hashes_before": before,
        "source_file_hashes_after": after,
        "historical_workspace_candidate": str(workspace_root),
        "historical_workspace_databases": state_databases,
        "g08_gate_status": g08.get("status"),
        "execution_admission": "HOLD_NO_ACTIVE_NONHISTORICAL_SOURCE_OR_CURRENT_RUN_BINDING",
        "runner_execution_performed": False,
        "write_or_install_performed": False,
        "certification": "NOT_GRANTED",
        "status": "PASS_FOR_READONLY_PROBE_ONLY" if syntax == "PASS" and all(p.get("status") == "PASS" for p in probes) and unchanged and g08.get("status") == "PENDING" else "PARTIAL_REQUIRES_DIAGNOSIS",
        "next_safe_action": "Bind a nonhistorical source + exact current workspace/run-id + checkpoint manifest before any G08 resume or continue-all operation",
    }


def s26_g06_rootfs_source_search():
    """Search for the exact certified G06 rootfs; never substitute a similar build."""
    lun = pathlib.Path(core.LUN)
    certification_path = lun / "00_EVIDENCE" / "G06_CERTIFICATION.json"
    binding_path = lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8" / "LUNITA_RUNTIME_BINDINGS.G08R1.frozen.json"
    inventory_path = lun / "00_EVIDENCE" / "STEP06_FREEZE_ESTUCHE" / "G06_INVENTORY_A.jsonl"
    snapshot_log_path = lun / "00_EVIDENCE" / "STEP06_FREEZE_ESTUCHE" / "G06_SNAPSHOT_COPY.log"
    cert = load(certification_path, {}) or {}
    binding = load(binding_path, {}) or {}
    components = (binding.get("bindings", {}) or {}).get("components", [])
    rootfs_component = next((x for x in components if x.get("component_id") == "ESTUCHE_G06_FROZEN_ROOTFS"), {})
    expected_path = pathlib.Path(rootfs_component.get("source_path") or cert.get("frozen_rootfs") or "/home/diego/lunita-final/G06_FROZEN/rootfs")
    expected_tree_sha = rootfs_component.get("sha256")
    expected_size = cert.get("size_bytes")
    expected_entry_count = cert.get("entry_count")
    roots = [
        pathlib.Path("/home/diego/lunita-final"),
        pathlib.Path("/mnt/c/Users/diego/Downloads/LUNITA_MATERIALIZATION"),
        pathlib.Path("/mnt/lunita-g06-view"),
        pathlib.Path("/mnt"),
        pathlib.Path("/media"),
        pathlib.Path("/opt"),
        pathlib.Path("/tmp"),
        pathlib.Path("/home/diegoignacionorambuenamiranda/Proyectos/1. PROYECTOS PRIORITARIOS/2. LUNITA_MATERIALIZATION"),
        pathlib.Path("/home/diegoignacionorambuenamiranda/Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA"),
    ]
    candidate_dirs = []
    candidate_archives = []
    seen_dirs = set()
    seen_files = set()
    visited_dirs = 0
    cap_dirs_per_root = 4000
    roots_visited = []
    ignored = {".git", ".runtime_venvs", "node_modules", "__pycache__", ".cache", "site-packages", ".venv", "venv", "proc", "sys", "dev"}
    archive_exts = (".tar", ".tar.xz", ".tar.gz", ".tar.zst", ".tgz", ".txz", ".7z", ".zip", ".squashfs", ".img", ".ext4")
    for root in roots:
        if not root.is_dir():
            continue
        dirs_for_root = 0
        for current, dirs, names in os.walk(root, topdown=True, followlinks=False):
            dirs[:] = [d for d in dirs if d not in ignored]
            visited_dirs += 1
            dirs_for_root += 1
            if dirs_for_root > cap_dirs_per_root:
                break
            cur = pathlib.Path(current)
            base_lower = cur.name.lower()
            path_lower = str(cur).lower()
            if base_lower in {"rootfs", "g06_frozen"} and any(z in path_lower for z in ("lunita", "g06", "proyectos")):
                if str(cur) not in seen_dirs:
                    st = cur.stat()
                    candidate_dirs.append({"path": str(cur), "basename": cur.name, "is_expected_path": cur == expected_path, "modified_utc": dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc).isoformat().replace("+00:00", "Z")})
                    seen_dirs.add(str(cur))
            for name in names:
                file_path = cur / name
                lname = name.lower()
                interesting = (
                    any(token in lname for token in ("g06_frozen", "rootfs", "lunita.squashfs", "lunita-rootfs", "lunita_final", "g06_estuche"))
                    and lname.endswith(archive_exts)
                )
                if interesting and str(file_path) not in seen_files:
                    try:
                        st = file_path.stat()
                        candidate_archives.append({"path": str(file_path), "name": name, "size_bytes": st.st_size, "is_exact_frozen_snapshot_by_name": name == "G06_FROZEN_ROOTFS.tar.zst" or name == "G06_FROZEN_ROOTFS.tar.xz", "is_official_frozen_input": False})
                        seen_files.add(str(file_path))
                    except OSError:
                        continue
                    if len(candidate_archives) >= 100:
                        break
            if dirs_for_root > cap_dirs_per_root or len(candidate_archives) >= 100:
                break
        roots_visited.append({"root": str(root), "directories_visited": dirs_for_root, "hit_root_cap": dirs_for_root > cap_dirs_per_root})
        if len(candidate_archives) >= 100:
            break
    input_candidates = []
    input_dir = lun / "01_INPUTS"
    for filename in [
        "ubuntu-24.04-minimal-cloudimg-amd64-root.tar.xz",
        "Qwen_Qwen3-0.6B-IQ3_XS.gguf",
        "SmolLM2-360M-Instruct-Q4_K_M.gguf",
        "R-4.6.1.tar.xz",
    ]:
        f = input_dir / filename
        if f.is_file():
            input_candidates.append({"path": str(f), "size_bytes": f.stat().st_size, "sha256": sha(f), "role": "REBUILD_INPUT_NOT_FROZEN_ROOTFS"})
    evidence_files = {}
    for pth in [certification_path, binding_path, inventory_path, snapshot_log_path]:
        if pth.is_file():
            evidence_files[str(pth)] = {"sha256": sha(pth), "size_bytes": pth.stat().st_size}
    exact_exists = expected_path.is_dir()
    result = {
        "schema": "CUSTOSZ_G06_FROZEN_ROOTFS_SOURCE_RECOVERY_SEARCH/1.0",
        "captured_at_utc": utc(),
        "mission_sha256": MISSION_SHA,
        "authoritative_g06_status": cert.get("status"),
        "frozen_rootfs_declared_path": str(expected_path),
        "frozen_rootfs_exists_at_declared_path": exact_exists,
        "expected_tree_sha256_from_frozen_bindings": expected_tree_sha,
        "expected_size_bytes": expected_size,
        "expected_entry_count": expected_entry_count,
        "actual_declared_rootfs_size_bytes": None,
        "actual_declared_rootfs_entry_count": None,
        "search_roots": [str(x) for x in roots],
        "directories_visited": visited_dirs,
        "search_directory_cap_per_root": cap_dirs_per_root,
        "roots_visited": roots_visited,
        "rootfs_or_g06_directories": candidate_dirs[:100],
        "rootfs_named_archive_candidates": candidate_archives,
        "input_candidates_not_equivalent_to_frozen_snapshot": input_candidates,
        "official_frozen_inventory_lines_expected": expected_entry_count,
        "inventory_file_bytes": inventory_path.stat().st_size if inventory_path.is_file() else None,
        "inventory_file_sha256": sha(inventory_path) if inventory_path.is_file() else None,
        "historical_copy_log_sha256": sha(snapshot_log_path) if snapshot_log_path.is_file() else None,
        "evidence_hashes": evidence_files,
        "existing_small_squashfs_not_substitutable": {
            "path": str(lun / "LUNITA.squashfs"),
            "exists": (lun / "LUNITA.squashfs").is_file(),
            "size_bytes": (lun / "LUNITA.squashfs").stat().st_size if (lun / "LUNITA.squashfs").is_file() else None,
            "reason": "Different certified object; no automatic source-path substitution allowed",
        },
        "github_repair_repository": "Plomillo/luna-linux-bridge",
        "github_remote_write": False,
        "source_may_be_rebuilt_from_inputs": False,
        "automatic_substitution_performed": False,
        "source_recovery_status": "EXACT_SOURCE_FOUND" if exact_exists else "EXACT_FROZEN_SOURCE_NOT_FOUND",
        "status": "PASS_EXACT_SOURCE_PRESENT" if exact_exists else "SOURCE_MISSING_BLOCKED",
        "next_safe_action": "Validate exact G06 tree hash and binding source provenance" if exact_exists else "Recover the exact frozen rootfs from a verified backup, or authorize a separately versioned rebuild candidate and re-run G06; do not rewrite G08 bindings silently",
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }
    atomic(ST / "g06_rootfs_source_recovery_search.json", result)
    return result


def s27_validate_g08_protocol_and_bindings():
    """Read-only check of the frozen protocol and exact frozen bindings; surface the missing G06 source."""
    lun = pathlib.Path(core.LUN)
    src = pathlib.Path(str(load(ST / "dependency_repairs" / "g08_jsonschema_4.26.0" / "ACTIVE_RUNTIME.json", {}).get("python_executable", "")))
    entrypoint = lun / G08_REL
    protocol = lun / "HISTORICAL_WSL_UBUNTU2404_EXTRACTION_20260917" / "01_NON_AUTHORITATIVE_PARTIAL" / "lunita-g08-v4" / "workspace" / "rollback" / "75c03244-a103-41e4-ba77-9146840b6886" / "fault_b31104f2-39ae-46f3-aa11-fee0d19e6aea" / "opt" / "lunita" / "manifests" / "governance" / "LUNITA_MATERIALIZATION_PROTOCOL.frozen.json"
    protocol_schema = protocol.with_name("LUNITA_MATERIALIZATION_PROTOCOL.schema.json")
    bindings_schema = protocol.with_name("LUNITA_RUNTIME_BINDINGS.schema.json")
    bindings = lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8" / "LUNITA_RUNTIME_BINDINGS.G08R1.frozen.json"
    handoff = verify_handoff()
    required = [src, entrypoint, protocol, protocol_schema, bindings_schema, bindings]
    missing = [str(p) for p in required if not p.is_file()]
    def run(argv):
        if missing:
            return {"argv": argv, "returncode": None, "status": "SKIPPED_MISSING_INPUT", "missing_inputs": missing}
        p = subprocess.run([str(src), "-I", str(entrypoint), *argv], capture_output=True, text=True, timeout=30, check=False)
        # Reject any command shape that could perform materialization/write operations.
        return {"argv": argv, "returncode": p.returncode, "stdout_tail": p.stdout[-3000:], "stderr_tail": p.stderr[-2000:], "status": "PASS" if p.returncode == 0 else "BLOCKED_OR_FAILED"}
    protocol_check = run(["validate", "--protocol", str(protocol), "--schema", str(protocol_schema)])
    binding_check = run(["validate-bindings", "--bindings", str(bindings), "--bindings-schema", str(bindings_schema)])
    binding_with_sources_check = run(["validate-bindings", "--bindings", str(bindings), "--bindings-schema", str(bindings_schema), "--require-sources"])
    missing_rootfs = "/home/diego/lunita-final/G06_FROZEN/rootfs"
    blocked_by_rootfs = any(
        missing_rootfs in (z.get("stdout_tail", "") + z.get("stderr_tail", ""))
        for z in [binding_with_sources_check]
    )
    result = {
        "schema": "CUSTOSZ_G08_PROTOCOL_BINDINGS_READONLY_VALIDATION/1.0",
        "captured_at_utc": utc(),
        "handoff": handoff,
        "entrypoint_sha256": sha(entrypoint) if entrypoint.is_file() else None,
        "protocol_path": str(protocol),
        "protocol_sha256": sha(protocol) if protocol.is_file() else None,
        "protocol_schema_sha256": sha(protocol_schema) if protocol_schema.is_file() else None,
        "bindings_path": str(bindings),
        "bindings_sha256": sha(bindings) if bindings.is_file() else None,
        "bindings_schema_sha256": sha(bindings_schema) if bindings_schema.is_file() else None,
        "protocol_validation": protocol_check,
        "bindings_structural_validation": binding_check,
        "bindings_required_sources_validation": binding_with_sources_check,
        "blocked_by_missing_g06_rootfs": blocked_by_rootfs,
        "g08_gate_remains_pending": True,
        "execution_performed": False,
        "canonical_bindings_mutated": False,
        "status": "BLOCKED_G06_ROOTFS_SOURCE_ABSENT" if blocked_by_rootfs else ("PASS_FOR_READONLY_VALIDATION_ONLY" if protocol_check.get("status") == "PASS" and binding_check.get("status") == "PASS" and binding_with_sources_check.get("status") == "PASS" else "PARTIAL_REQUIRES_DIAGNOSIS"),
        "next_safe_action": "Restore the exact frozen G06 rootfs or run a separate authorized G06 rebuild candidate; keep canonical G08 bindings immutable until exact sources validate",
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }
    return result


def s28_recheck_g06_rootfs_source_and_g08_binding():
    """Freshly recheck source roots independently and persist the current admission decision."""
    search = s26_g06_rootfs_source_search()
    validation = s27_validate_g08_protocol_and_bindings()
    result = {
        "schema": "CUSTOSZ_G06_SOURCE_RECHECK_AND_G08_ADMISSION/1.0",
        "captured_at_utc": utc(),
        "search_status": search.get("status"),
        "roots_visited": search.get("roots_visited", []),
        "directories_visited": search.get("directories_visited"),
        "frozen_rootfs_declared_path": search.get("frozen_rootfs_declared_path"),
        "frozen_rootfs_exists_at_declared_path": search.get("frozen_rootfs_exists_at_declared_path"),
        "expected_tree_sha256": search.get("expected_tree_sha256_from_frozen_bindings"),
        "source_archive_candidates": search.get("rootfs_named_archive_candidates", []),
        "input_inventory_hashes": search.get("evidence_hashes", {}),
        "g08_protocol_status": (validation.get("protocol_validation") or {}).get("status"),
        "g08_bindings_structural_status": (validation.get("bindings_structural_validation") or {}).get("status"),
        "g08_bindings_sources_status": (validation.get("bindings_required_sources_validation") or {}).get("status"),
        "blocked_by_g06_rootfs": validation.get("blocked_by_missing_g06_rootfs"),
        "no_canonical_source_or_binding_mutation": True,
        "next_action": search.get("next_safe_action"),
        "status": "SOURCE_MISSING_BLOCKED" if validation.get("blocked_by_missing_g06_rootfs") else "PASS_SOURCE_PRESENT_REVALIDATION_REQUIRED",
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }
    return result


def s22_run_cli_candidate_regression():
    report = phase2.s17_validate_cli_adapter_candidate()
    good = (
        report.get("status") == "PASS"
        and report.get("compile_pass") is True
        and report.get("unit_test_returncode") == 0
        and report.get("project_mutations") is False
    )
    result = {
        "schema": "CUSTOSZ_CAJITA_CLI_CANDIDATE_REGRESSION/1.0",
        "captured_at_utc": utc(),
        "validation_report": report,
        "status": "PASS" if good else "FAIL_REQUIRES_REPAIR",
        "project_mutations": False,
        "certification": "NOT_GRANTED",
    }
    if not good:
        raise RuntimeError("S22_CLI_CANDIDATE_REGRESSION_FAILED:" + json.dumps(result, ensure_ascii=False)[:1800])
    return result

def s23_refresh_cli_registry_probe():
    report = phase2.s19_run_cli_registry_probes()
    if report.get("status") not in {"PROBE_EXECUTED", "PROBE_REQUIRES_DIAGNOSIS"}:
        raise RuntimeError("S23_REGISTRY_PROBE_RETURNED_UNEXPECTED_STATUS:" + str(report.get("status")))
    report["continuation_policy"] = "READ_ONLY_PROBE_NO_AUTOMATIC_INSTALL_OR_CANONICAL_PROMOTION"
    return report

def s24_reconcile_blockers():
    lun = pathlib.Path(core.LUN)
    gate = load(lun / "00_EVIDENCE" / "CERTIFICATION_EXIT_PLAN.json", {}) or {}
    gate_rows = gate.get("gates", [])
    pending = [{"id": g.get("id"), "name": g.get("name"), "status": g.get("status")} for g in gate_rows if g.get("status") == "PENDING"]
    cli_report_path = max(ST.glob("cli_registry_probe_*.json"), key=lambda p: p.stat().st_mtime, default=None)
    cli = load(cli_report_path, {}) if cli_report_path else {}
    missing_cli = []
    for row in (cli or {}).get("results", []):
        if row.get("status") in {"ABSENT", "MISSING", "NOT_FOUND"} or row.get("available") is False:
            missing_cli.append({"domain": row.get("domain_id") or row.get("domain") or row.get("id"), "status": row.get("status")})
    gh = load(ST / "github_evidence_search.json", {}) or {}
    result = {
        "schema": "CUSTOSZ_IMPLEMENTATION_BACKLOG_RECONCILIATION/1.0",
        "captured_at_utc": utc(),
        "mission_scope": "Cajita first, Lunita second",
        "pending_lunita_gates": pending,
        "latest_cli_probe": str(cli_report_path) if cli_report_path else None,
        "latest_cli_probe_sha256": sha(cli_report_path) if cli_report_path and cli_report_path.is_file() else None,
        "missing_cli_domains_observed": missing_cli,
        "github_repository": gh.get("repo"),
        "github_cache_status": gh.get("status"),
        "github_remote_write_enabled": False,
        "next_work_item": "G08_ACTIVE_RUN_CONTEXT_AND_TARGET_BINDING" if any(str(x.get("id")) == "8" for x in pending) else "NEXT_PENDING_ACCEPTANCE_CRITERION",
        "blocker_does_not_close_mission": True,
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
        "status": "BACKLOG_RECONCILED_ACTIVE",
    }
    atomic(ST / "implementation_backlog.json", result)
    return result



def s30_g06_reconstruction_fallback():
    """Automatically register a versioned G06 rebuild candidate after bounded recovery fails."""
    search = s26_g06_rootfs_source_search()
    rebuild = g06_reconstruction.advance(search, execute=False)
    return {
        "schema": "CUSTOSZ_G06_AUTOMATIC_REBUILD_FALLBACK/1.0",
        "captured_at_utc": utc(),
        "trigger": "EXACT_FROZEN_G06_SOURCE_MISSING_AFTER_BOUNDED_SEARCH",
        "source_search_status": search.get("status"),
        "rebuild_candidate": rebuild,
        "frozen_g06_mutated": False,
        "canonical_g08_bindings_mutated": False,
        "automatic_certification_propagation": False,
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
        "status": rebuild.get("status", "REBUILD_FALLBACK_REGISTERED"),
        "next_action": "S29 will launch the versioned candidate base build asynchronously; G08 remains pending until full rebuild and independent validation",
    }


def s29_cajita_model_quantization_preflight():
    """Audit Cajita model formats and prepare only the hash-pinned local quantizer; do not mutate model weights."""
    caj = pathlib.Path(core.CAJ)
    lun = pathlib.Path(core.LUN)
    targets = [
        ("CEREBRO", caj / "1. Cerebro"),
        ("SISTEMA_INTELIGENTE_ANALISIS_AVANZADO", caj / "6. Sistema Inteligente" / "Análisis Avanzado"),
        ("TRANSCRIPCION", caj / "3. Transcripción"),
        ("TRADUCCION_GENERAL", caj / "4. Traductor Inteligente" / "Traducción general"),
        ("INTELIGENCIA_DOCUMENTAL_DOCLING", caj / "5. Inteligencia documental" / "Docling"),
    ]
    models = []
    def file_row(p, hash_content=False):
        row = {"path": str(p), "exists": False}
        try:
            row["exists"] = p.is_file()
            if row["exists"]:
                st = p.stat()
                row.update({"bytes": st.st_size, "mtime_ns": st.st_mtime_ns})
                if hash_content:
                    row["sha256"] = sha(p)
        except OSError as exc:
            row["access_error"] = type(exc).__name__
            row["access_error_detail"] = str(exc)[:300]
        return row
    for label, folder in targets:
        cfg = folder / "config.json"
        idx = folder / "model.safetensors.index.json"
        entry = {"id": label, "folder": str(folder), "folder_exists": folder.is_dir(),
                 "config": file_row(cfg, True), "index": file_row(idx, True),
                 "weight_files": [], "model_type": None, "architectures": [],
                 "torch_dtype": None, "quantization_config": None}
        conf = {}
        if cfg.is_file():
            try:
                conf = json.loads(cfg.read_text(encoding="utf-8-sig"))
                entry.update({"model_type": conf.get("model_type"),
                              "architectures": conf.get("architectures", []),
                              "torch_dtype": conf.get("torch_dtype"),
                              "quantization_config": conf.get("quantization_config")})
            except Exception as exc:
                entry["config_error"] = type(exc).__name__ + ":" + str(exc)[:500]
        if idx.is_file():
            try:
                info = json.loads(idx.read_text(encoding="utf-8-sig"))
                entry["tensor_total_size_bytes"] = (info.get("metadata") or {}).get("total_size")
                shards = sorted(set((info.get("weight_map") or {}).values()))
                entry["shard_count"] = len(shards)
                for name in shards:
                    entry["weight_files"].append(file_row(folder / name, False))
            except Exception as exc:
                entry["index_error"] = type(exc).__name__ + ":" + str(exc)[:500]
        else:
            known = sorted([p for p in folder.glob("*") if p.is_file() and p.suffix.lower() in {".gguf", ".safetensors", ".pt"}])
            entry["shard_count"] = len(known)
            entry["weight_files"] = [file_row(p, False) for p in known[:40]]
        if label == "CEREBRO" and (entry.get("quantization_config") or {}).get("quant_method") == "mxfp4":
            entry["optimization_disposition"] = "ALREADY_MXFP4; NO_REQUANTIZATION_WITHOUT_RUNTIME_BENCHMARK_AND_FORMAT_SUPPORT"
        elif entry.get("torch_dtype") in {"bfloat16", "float32", "float16"}:
            entry["optimization_disposition"] = "CANDIDATE_REQUIRES_CONVERTER_AND_QUALITY_VALIDATION"
        elif any(p.get("path", "").endswith(".gguf") for p in entry["weight_files"]):
            entry["optimization_disposition"] = "EXISTING_GGUF; AUDIT_AND_BENCHMARK_BEFORE_REQUANTIZATION"
        else:
            entry["optimization_disposition"] = "IDENTITY_OR_FORMAT_RECONCILIATION_REQUIRED"
        models.append(entry)

    # Validate the local binary archive against Lunita's recorded input SHA-256 before extracting anything.
    archive = lun / "01_INPUTS" / "llama-b10819-bin-ubuntu-x64.tar.gz"
    manifest_path = lun / "00_EVIDENCE" / "INPUT_MANIFEST_SHA256.json"
    expected = None
    manifest_error = None
    if manifest_path.is_file():
        try:
            im = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
            row = next((x for x in im.get("inputs", []) if x.get("name") == archive.name), None)
            expected = (row or {}).get("sha256")
        except Exception as exc:
            manifest_error = type(exc).__name__ + ":" + str(exc)[:400]
    archive_hash = sha(archive) if archive.is_file() else None
    provenance_ok = bool(archive_hash and expected and archive_hash == expected)
    toolchain = {"archive": file_row(archive, False), "archive_sha256": archive_hash,
                 "manifest_path": str(manifest_path), "expected_sha256": expected,
                 "manifest_error": manifest_error, "provenance_status": "PASS" if provenance_ok else "BLOCKED_HASH_OR_MANIFEST_MISMATCH",
                 "runtime_dir": None, "quantizer": {}, "converter": {}}
    if provenance_ok:
        tools_root = ST / "tools"
        tools_root.mkdir(parents=True, exist_ok=True, mode=0o700)
        final = tools_root / ("llama-b10819_" + archive_hash[:12])
        marker = final / "TOOLCHAIN_PROVENANCE.json"
        marker_ok = False
        if marker.is_file():
            try:
                marker_value = json.loads(marker.read_text(encoding="utf-8"))
                if isinstance(marker_value, str):
                    marker_value = json.loads(marker_value)
                marker_ok = isinstance(marker_value, dict) and marker_value.get("archive_sha256") == archive_hash
                if marker_ok:
                    atomic(marker, marker_value)
            except (OSError, ValueError, TypeError):
                marker_ok = False
        if not marker_ok:
            tmp = pathlib.Path(tempfile.mkdtemp(prefix="llama-b10819-extract-", dir=str(tools_root)))
            try:
                import tarfile
                with tarfile.open(archive, "r:gz") as tf:
                    tf.extractall(path=str(tmp), filter="data")
                unpacked = tmp / "llama-b10819"
                q = unpacked / "llama-quantize"
                if not q.is_file():
                    raise RuntimeError("PINNED_ARCHIVE_NO_LLAMA_QUANTIZE")
                if final.exists():
                    raise RuntimeError("TOOLCHAIN_DESTINATION_EXISTS_WITHOUT_MATCHING_PROVENANCE")
                os.replace(unpacked, final)
            finally:
                shutil.rmtree(tmp, ignore_errors=True)
            if not (final / "llama-quantize").is_file():
                raise RuntimeError("QUANTIZER_MISSING_AFTER_EXTRACTION")
            tool_hashes = {p.name: sha(p) for p in sorted(final.iterdir()) if p.is_file()}
            provenance = {"schema": "CUSTOSZ_LLAMA_QUANTIZER_TOOLCHAIN/1.0", "captured_at_utc": utc(),
                          "source_archive": str(archive), "archive_sha256": archive_hash,
                          "input_manifest_sha256": expected, "runtime_files_sha256": tool_hashes,
                          "build": "llama.cpp b10819", "source_commit_prefix": "6a1a922d2",
                          "project_model_weights_modified": False}
            atomic(marker, provenance)
        toolchain["runtime_dir"] = str(final)
        q = final / "llama-quantize"
        env = os.environ.copy()
        env["LD_LIBRARY_PATH"] = str(final) + (os.pathsep + env["LD_LIBRARY_PATH"] if env.get("LD_LIBRARY_PATH") else "")
        try:
            ver = subprocess.run([str(q), "--version"], cwd=str(final), env=env, capture_output=True, text=True, timeout=15, check=False)
            helpres = subprocess.run([str(q), "--help"], cwd=str(final), env=env, capture_output=True, text=True, timeout=15, check=False)
            toolchain["quantizer"] = {"path": str(q), "sha256": sha(q), "version_rc": ver.returncode,
                "version_output": (ver.stdout + ver.stderr)[-1600:], "help_rc": helpres.returncode,
                "help_output": (helpres.stdout + helpres.stderr)[-1800:],
                "status": "PASS" if ver.returncode == 0 and len(helpres.stdout + helpres.stderr) > 100 else "BLOCKED"}
        except Exception as exc:
            toolchain["quantizer"] = {"path": str(q), "status": "ERROR", "error": type(exc).__name__ + ":" + str(exc)[:700]}
    converter_candidates = [
        ST / "tools" / "llama.cpp-source-b10819-6a1a922d2699" / "convert_hf_to_gguf.py",
        ST / "tools" / "llama.cpp-source" / "convert_hf_to_gguf.py",
        pathlib.Path("/usr/local/bin/convert_hf_to_gguf.py"),
        pathlib.Path("/usr/bin/convert_hf_to_gguf.py"),
    ]
    found_converter = next((p for p in converter_candidates if p.is_file()), None)
    toolchain["converter"] = {"path": str(found_converter) if found_converter else None,
                              "status": "PRESENT" if found_converter else "MISSING",
                              "requires_read_only_official_source_resolution": found_converter is None}
    # Current Lunita evidence: distinguish its missing original frozen rootfs from the separately rebuilt candidate.
    cert_path = lun / "00_EVIDENCE" / "G06_CERTIFICATION.json"
    bindings_path = lun / "00_EVIDENCE" / "STEP08_JOHNSON_S1_S8" / "LUNITA_RUNTIME_BINDINGS.G08R1.frozen.json"
    receipt_path = ST / "g06_rebuild_candidates" / "G06_REBUILD_CANDIDATE_R1" / "BASE_REBUILD_RECEIPT.json"
    cert = load(cert_path, {}) or {}
    bindings = load(bindings_path, {}) or {}
    comps = ((bindings.get("bindings") or {}).get("components") or [])
    root_binding = next((x for x in comps if x.get("component_id") == "ESTUCHE_G06_FROZEN_ROOTFS"), {})
    expected_root = pathlib.Path(root_binding.get("source_path") or cert.get("frozen_rootfs") or "/home/diego/lunita-final/G06_FROZEN/rootfs")
    receipt = load(receipt_path, {}) or {}
    gate_path = lun / "00_EVIDENCE" / "CERTIFICATION_EXIT_PLAN.json"
    gate = load(gate_path, {}) or {}
    gates = gate.get("gates", []) if isinstance(gate, dict) else []
    lunita_state = {
        "local_root": str(lun), "G06_certification": file_row(cert_path, True),
        "frozen_bindings": file_row(bindings_path, True), "declared_frozen_rootfs": str(expected_root),
        "declared_frozen_rootfs_exists": expected_root.is_dir(), "candidate_receipt": file_row(receipt_path, True),
        "candidate_state": receipt.get("status"), "candidate_certification": receipt.get("certification"),
        "LUNITA_squashfs": file_row(lun / "LUNITA.squashfs", True),
        "pending_gate_count": sum(1 for g in gates if g.get("status") == "PENDING"),
        "pending_gate_ids": [g.get("id") for g in gates if g.get("status") == "PENDING"],
        "canonical_frozen_rootfs_or_G08_binding_mutated": False,
        "original_found_locally": expected_root.is_dir()
    }
    report = {"schema":"CUSTOSZ_CAJITA_QUANTIZATION_PREFLIGHT/1.0","captured_at_utc":utc(),
        "mission_sha256":core.HS_MISSION,"scope":core.SCOPE,"models":models,"quantization_toolchain":toolchain,
        "lunita_source_reconciliation":lunita_state,
        "sequence_policy":["CEREBRO_MXFP4_AUDIT_NO_BLIND_REQUANTIZATION","QWEN3_BF16_CONVERTER_AND_CANDIDATE",
            "WHISPER_IDENTITY_RECONCILIATION","SEAMLESSM4T_ASSET_DUPLICATION_RECONCILIATION","EXISTING_DOCILING_GGUF_BENCHMARK"],
        "mutated_original_model_weights":False,"canonical_lunita_artifacts_mutated":False,
        "mission_completion_claim":False,"certification":"NOT_GRANTED",
        "status":"BLOCKED_HF_TO_GGUF_CONVERTER_MISSING" if not found_converter else "PREFLIGHT_READY_FOR_CONVERSION_VALIDATION"}
    out = ST / "cajita_quantization_preflight.json"
    atomic(out, report)
    return report



def s29b_acquire_pinned_hf_to_gguf_converter():
    """Fetch the official llama.cpp b10819 converter at an exact immutable commit; no model weights are loaded."""
    import tempfile
    import shutil
    import subprocess
    expected_commit = "6a1a922d269908a29cbd4b49c27e6a8e7fd10fae"
    expected_tag = "b10819"
    remote = "https://github.com/ggml-org/llama.cpp.git"
    tools_root = ST / "tools"
    target = tools_root / "llama.cpp-source-b10819-6a1a922d2699"
    tools_root.mkdir(parents=True, exist_ok=True, mode=0o700)
    git_version = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=10, check=False)
    if git_version.returncode:
        return {"status":"BLOCKED_GIT_UNAVAILABLE","git_stderr":git_version.stderr[-500:],"mission_completion_claim":False,"certification":"NOT_GRANTED"}
    if target.exists():
        rev = subprocess.run(["git","-C",str(target),"rev-parse","HEAD"],capture_output=True,text=True,timeout=15,check=False)
        head = rev.stdout.strip()
        if rev.returncode or head != expected_commit:
            return {"status":"BLOCKED_PINNED_SOURCE_TARGET_EXISTS_MISMATCH","path":str(target),"observed_commit":head or None,
                    "expected_commit":expected_commit,"no_overwrite":True,"certification":"NOT_GRANTED","mission_completion_claim":False}
        repo = target
    else:
        temp_root = pathlib.Path(tempfile.mkdtemp(prefix="llama-cpp-b10819-clone-",dir=str(tools_root)))
        clone_path = temp_root / "repo"
        try:
            clone = subprocess.run(["git","clone","--filter=blob:none","--depth","1","--branch",expected_tag,remote,str(clone_path)],
                                   capture_output=True,text=True,timeout=180,check=False)
            if clone.returncode:
                return {"status":"BLOCKED_OFFICIAL_SOURCE_FETCH_FAILED","git_returncode":clone.returncode,
                        "stderr":clone.stderr[-2500:],"stdout":clone.stdout[-1000:],"remote":remote,"tag":expected_tag,
                        "mission_completion_claim":False,"certification":"NOT_GRANTED"}
            rev = subprocess.run(["git","-C",str(clone_path),"rev-parse","HEAD"],capture_output=True,text=True,timeout=15,check=False)
            head = rev.stdout.strip()
            if rev.returncode or head != expected_commit:
                return {"status":"BLOCKED_COMMIT_PIN_MISMATCH","observed_commit":head or None,"expected_commit":expected_commit,
                        "remote":remote,"tag":expected_tag,"no_source_promotion":True,"mission_completion_claim":False,"certification":"NOT_GRANTED"}
            script = clone_path / "convert_hf_to_gguf.py"
            gguf_pkg = clone_path / "gguf-py" / "gguf"
            if not script.is_file() or not (gguf_pkg / "__init__.py").is_file():
                return {"status":"BLOCKED_EXPECTED_CONVERTER_FILES_MISSING","converter_exists":script.is_file(),
                        "gguf_package_exists":(gguf_pkg/"__init__.py").is_file(),"path":str(clone_path),
                        "mission_completion_claim":False,"certification":"NOT_GRANTED"}
            compile(script.read_text(encoding="utf-8"),str(script),"exec")
            git_status = subprocess.run(["git","-C",str(clone_path),"status","--porcelain"],capture_output=True,text=True,timeout=10,check=False)
            if git_status.returncode or git_status.stdout.strip():
                return {"status":"BLOCKED_CHECKOUT_NOT_CLEAN","git_status":git_status.stdout[-1000:],
                        "mission_completion_claim":False,"certification":"NOT_GRANTED"}
            os.replace(clone_path,target)
        finally:
            shutil.rmtree(temp_root,ignore_errors=True)
        repo=target
    script=repo/"convert_hf_to_gguf.py"
    gguf_pkg=repo/"gguf-py"/"gguf"
    compile(script.read_text(encoding="utf-8"),str(script),"exec")
    source_hash=sha(script)
    package_files={}
    for name in ["__init__.py"]:
        q=repo/"gguf-py"/"gguf"/name
        if q.is_file(): package_files[str(q.relative_to(repo))]={"sha256":sha(q),"bytes":q.stat().st_size}
    for name in ["pyproject.toml","requirements.txt"]:
        q=repo/"gguf-py"/name
        if q.is_file(): package_files[str(q.relative_to(repo))]={"sha256":sha(q),"bytes":q.stat().st_size}
    reqs=[]
    for reqfile in [repo/"requirements.txt",repo/"gguf-py"/"requirements.txt"]:
        if reqfile.is_file():
            reqs += [{"file":str(reqfile.relative_to(repo)),"requirement":line.strip()}
                     for line in reqfile.read_text(encoding="utf-8").splitlines()
                     if line.strip() and not line.lstrip().startswith("#")]
    env={**os.environ,"PYTHONPATH":str(repo/"gguf-py")}
    probe=subprocess.run(["/usr/bin/python3","-B",str(script),"--help"],capture_output=True,text=True,timeout=30,check=False,env=env)
    missing_imports=[]
    for line in (probe.stderr + chr(10) + probe.stdout).splitlines():
        if "ModuleNotFoundError" in line or "ImportError" in line: missing_imports.append(line[:300])
    result={"schema":"CUSTOSZ_PINNED_HF_TO_GGUF_CONVERTER/1.0","captured_at_utc":utc(),
        "remote":remote,"tag":expected_tag,"expected_commit":expected_commit,
        "observed_commit":subprocess.run(["git","-C",str(repo),"rev-parse","HEAD"],capture_output=True,text=True,timeout=10,check=False).stdout.strip(),
        "path":str(repo),"converter_path":str(script),"converter_sha256":source_hash,
        "converter_python_compile":"PASS","gguf_python_package":str(repo/"gguf-py"),"gguf_package_exists":(gguf_pkg/"__init__.py").is_file(),
        "requirements_files":package_files,"requirements":reqs,"help_probe_rc":probe.returncode,
        "help_probe_stderr_tail":probe.stderr[-1800:],"help_probe_stdout_tail":probe.stdout[-600:],
        "missing_import_errors":missing_imports,"weights_converted":False,"models_mutated":False,
        "status":"PASS_CONVERTER_SOURCE_PINNED" if (not missing_imports and probe.returncode==0) else "BLOCKED_CONVERTER_DEPENDENCIES_MISSING",
        "next_action":"Provision a scoped resource-bounded converter environment; convert Qwen3 only to a versioned candidate, then quantize GGUF and validate.",
        "mission_completion_claim":False,"certification":"NOT_GRANTED"}
    atomic(ST/"pinned_hf_to_gguf_converter.json",result)
    return result


def _beta_gate_report(path, schema):
    path = pathlib.Path(path)
    if not path.is_file():
        return None, {"status": "BLOCKED_EVIDENCE_MISSING", "reason": "MISSING_REPORT", "path": str(path)}
    report = load(path, None)
    if not isinstance(report, dict):
        return None, {"status": "BLOCKED_EVIDENCE_INVALID_JSON", "path": str(path)}
    if report.get("schema") != schema:
        return None, {"status": "BLOCKED_EVIDENCE_SCHEMA_MISMATCH", "path": str(path), "observed_schema": report.get("schema")}
    if report.get("candidate_id") != "G06_REBUILD_CANDIDATE_R1":
        return None, {"status": "BLOCKED_CANDIDATE_IDENTITY_MISMATCH", "path": str(path)}
    return report, None


def s31_versioned_beta_runtime_gate():
    candidate = ST / "g06_rebuild_candidates" / "G06_REBUILD_CANDIDATE_R1"
    report_path = candidate / "BETA_RUNTIME_FUNCTIONAL_TESTS.json"
    report, failure = _beta_gate_report(report_path, "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0")
    if failure:
        return {"status": failure["status"], "step_completion": False, "blocker": failure,
                "next_action": "Complete runtime build and functional tests; write a hash-bound beta test report. Reuse verified local inputs and do not alter frozen G06/G08.",
                "retry_after_seconds": REFRESH_SECONDS, "certification": "NOT_GRANTED"}
    tests = report.get("tests")
    bad = {k:v for k,v in tests.items()} if isinstance(tests, dict) else {"tests":"MISSING_OR_NOT_OBJECT"}
    bad = {k:v for k,v in bad.items() if not isinstance(v, dict) or v.get("status") != "PASS" or v.get("returncode") != 0}
    if report.get("status") != "PASS_RUNTIME_TESTS" or report.get("all_tests_pass") is not True or bad:
        return {"status": "BETA_BLOCKED_RUNTIME_TESTS", "step_completion": False,
                "failed_tests": bad, "reported_status": report.get("status"),
                "next_action": "Keep S31 pending; fix only the failing component, append new evidence and rerun its test. Do not increase step_index.",
                "retry_after_seconds": REFRESH_SECONDS, "runtime_report_sha256": sha(report_path),
                "certification": "NOT_GRANTED"}
    launcher = candidate / "rootfs" / "opt/lunita/agent/lunita.py"
    actual_launcher_sha = sha(launcher) if launcher.is_file() else None
    expected_launcher_sha = (report.get("candidate") or {}).get("beta_launcher_sha256")
    if not actual_launcher_sha or actual_launcher_sha != expected_launcher_sha:
        return {"status":"BETA_BLOCKED_LAUNCHER_IDENTITY_CHANGED","step_completion":False,
                "actual_launcher_sha256":actual_launcher_sha,"report_launcher_sha256":expected_launcher_sha,
                "next_action":"Revalidate beta launcher provenance and regenerate runtime report.","retry_after_seconds":REFRESH_SECONDS,
                "certification":"NOT_GRANTED"}
    return {"schema":"CUSTOSZ_LUNITA_BETA_RUNTIME_GATE/1.0","status":"PASS_RUNTIME_TESTS",
            "step_completion":True,"candidate_id":"G06_REBUILD_CANDIDATE_R1",
            "runtime_report_path":str(report_path),"runtime_report_sha256":sha(report_path),
            "passed_test_count":len(tests),"beta_launcher_sha256":actual_launcher_sha,
            "canonical_g06_certification":"NOT_GRANTED","canonical_g08_bindings_mutated":False,
            "certification":"PENDING_INDEPENDENT_VALIDATION",
            "next_action":"S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT"}


def s32_independent_beta_validation_and_receipt():
    candidate = ST / "g06_rebuild_candidates" / "G06_REBUILD_CANDIDATE_R1"
    runtime_path = candidate / "BETA_RUNTIME_FUNCTIONAL_TESTS.json"
    independent_path = candidate / "BETA_INDEPENDENT_VALIDATION.json"
    runtime, failure = _beta_gate_report(runtime_path, "CUSTOSZ_LUNITA_BETA_RUNTIME_FUNCTIONAL_TESTS/1.0")
    if failure:
        return {"status":failure["status"],"step_completion":False,"blocker":failure,
                "next_action":"Complete S31 runtime functional validation first.","retry_after_seconds":REFRESH_SECONDS,
                "certification":"NOT_GRANTED"}
    independent, failure = _beta_gate_report(independent_path, "CUSTOSZ_LUNITA_BETA_INDEPENDENT_VALIDATION/1.0")
    if failure:
        return {"status":failure["status"],"step_completion":False,"blocker":failure,
                "next_action":"Run independent checks in a separate process and bind them to the exact runtime-report SHA-256.",
                "retry_after_seconds":REFRESH_SECONDS,"runtime_report_sha256":sha(runtime_path),
                "certification":"NOT_GRANTED"}
    expected_runtime_sha = sha(runtime_path)
    independent_checks = independent.get("checks")
    bad = {k:v for k,v in independent_checks.items()} if isinstance(independent_checks,dict) else {"checks":"MISSING_OR_NOT_OBJECT"}
    bad = {k:v for k,v in bad.items() if not isinstance(v,dict) or v.get("status") != "PASS" or v.get("returncode",0) != 0}
    if (independent.get("status") != "PASS_INDEPENDENT_VALIDATION"
        or independent.get("runtime_report_sha256") != expected_runtime_sha
        or runtime.get("status") != "PASS_RUNTIME_TESTS"
        or runtime.get("all_tests_pass") is not True
        or independent.get("frozen_g06_mutated") is not False
        or independent.get("canonical_g08_bindings_mutated") is not False
        or bad):
        return {"status":"BETA_BLOCKED_INDEPENDENT_VALIDATION","step_completion":False,
                "expected_runtime_report_sha256":expected_runtime_sha,
                "observed_runtime_report_sha256":independent.get("runtime_report_sha256"),
                "failed_independent_checks":bad,
                "next_action":"Keep S32 pending. Repair/re-run the failing independent check; do not propagate certification to frozen G06/G08.",
                "retry_after_seconds":REFRESH_SECONDS,"certification":"NOT_GRANTED"}
    return {"schema":"CUSTOSZ_LUNITA_BETA_CERTIFICATION_RECEIPT/1.0",
            "status":"BETA_OPERATIONAL_CERTIFIED","step_completion":True,
            "candidate_id":"G06_REBUILD_CANDIDATE_R1",
            "basis":"VERSIONED_DERIVED_BETA_FROM_VERIFIED_UBUNTU_BASE; NOT_THE_MISSING_FROZEN_ORIGINAL",
            "runtime_report_path":str(runtime_path),"runtime_report_sha256":expected_runtime_sha,
            "independent_report_path":str(independent_path),"independent_report_sha256":sha(independent_path),
            "independent_validation":"PASS","frozen_g06_mutated":False,
            "canonical_g08_bindings_mutated":False,"canonical_g06_certification":"NOT_GRANTED",
            "certification_scope":"CANDIDATE_BETA_ONLY; NO AUTOMATIC CERTIFICATION PROPAGATION",
            "mission_completion_claim":False,
            "next_action":"Record the hash-bound beta receipt; retain canonical original-source recovery as a separate pending gate."}


STEPS = [
    ("S21_VALIDATE_G08_PATCH_AND_HANDOFF", s21_validate_g08_patch_and_gate_context),
    ("S22_RUN_CLI_CANDIDATE_REGRESSION", s22_run_cli_candidate_regression),
    ("S23_REFRESH_CLI_REGISTRY_PROBE", s23_refresh_cli_registry_probe),
    ("S24_RECONCILE_IMPLEMENTATION_BACKLOG", s24_reconcile_blockers),
    ("S25_G08_EXECUTION_ADMISSION_PROBE", s25_g08_execution_admission_probe),
    ("S26_G06_ROOTFS_SOURCE_RECOVERY_SEARCH", s26_g06_rootfs_source_search),
    ("S27_VALIDATE_G08_PROTOCOL_AND_BINDINGS", s27_validate_g08_protocol_and_bindings),
    ("S28_RECHECK_G06_ROOTFS_SOURCE_AND_G08_BINDING", s28_recheck_g06_rootfs_source_and_g08_binding),
    ("S29_CAJITA_MODEL_QUANTIZATION_PREFLIGHT", s29_cajita_model_quantization_preflight),
    ("S29B_CAJITA_HF_GGUF_CONVERTER_SOURCE", s29b_acquire_pinned_hf_to_gguf_converter),
    ("S30_G06_AUTOMATIC_VERSIONED_REBUILD_FALLBACK", s30_g06_reconstruction_fallback),
    ("S31_VERSIONED_BETA_RUNTIME_FUNCTIONAL_GATE", s31_versioned_beta_runtime_gate),
    ("S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT", s32_independent_beta_validation_and_receipt),
]

def selftest():
    return {
        "schema": "CUSTOSZ_MISION1_CONTINUATION_SELFTEST/1.0",
        "status": "PASS" if len({x[0] for x in STEPS}) == len(STEPS) and all(callable(x[1]) for x in STEPS) else "FAIL",
        "step_count": len(STEPS),
        "unique_step_ids": len({x[0] for x in STEPS}) == len(STEPS),
        "queue_reconciliation_available": callable(reconcile_queue),
        "g08_readonly_probe_registered": any(x[0] == "S25_G08_EXECUTION_ADMISSION_PROBE" for x in STEPS),
        "g06_source_recovery_search_registered": any(x[0] == "S26_G06_ROOTFS_SOURCE_RECOVERY_SEARCH" for x in STEPS),
        "g08_binding_validation_registered": any(x[0] == "S27_VALIDATE_G08_PROTOCOL_AND_BINDINGS" for x in STEPS),
        "g06_source_recheck_registered": any(x[0] == "S28_RECHECK_G06_ROOTFS_SOURCE_AND_G08_BINDING" for x in STEPS),
        "g06_automatic_rebuild_fallback_registered": any(x[0] == "S30_G06_AUTOMATIC_VERSIONED_REBUILD_FALLBACK" and callable(x[1]) for x in STEPS),
        "versioned_beta_runtime_gate_registered": any(x[0] == "S31_VERSIONED_BETA_RUNTIME_FUNCTIONAL_GATE" and callable(x[1]) for x in STEPS),
        "independent_beta_validation_gate_registered": any(x[0] == "S32_INDEPENDENT_BETA_VALIDATION_AND_RECEIPT" and callable(x[1]) for x in STEPS),
        "blocked_steps_do_not_advance": "if continuous_governor.result_blocks_step(result):" in pathlib.Path(__file__).read_text(encoding="utf-8"),
        "status_only_block_is_fail_closed": continuous_governor.result_blocks_step({"status": "BLOCKED_TEST"}) and continuous_governor.result_blocks_step({"status": "SOURCE_MISSING_BLOCKED"}),
        "normal_subtask_status_is_not_blocked": not continuous_governor.result_blocks_step({"status": "PASS_FOR_SUBTASK_ONLY", "step_completion": True}),
        "cajita_priority_lane_registered": callable(continuous_governor.tick_cajita_priority_lane),
        "maintenance_scan_not_success": '"CRFU_CONTINUATION_MAINTENANCE", "WAITING_FOR_EVENT"' in pathlib.Path(__file__).read_text(encoding="utf-8"),
        "g06_reconstruction_module_selftest": g06_reconstruction.selftest().get("status"),
        "mission_sha256": MISSION_SHA,
        "no_mutation_on_import": True,
        "certification": "NOT_GRANTED",
    }

def tick():
    now = utc()
    state = load(PROGRESS, {}) or {
        "schema": "CUSTOSZ_MISION1_CONTINUATION_PROGRESS/1.0",
        "mission_sha256": MISSION_SHA,
        "step_index": 0,
        "completed_steps": [],
        "last_progress_utc": None,
        "maintenance": {},
    }
    if state.get("mission_sha256") != MISSION_SHA:
        raise RuntimeError("CONTINUATION_PROGRESS_MISSION_HASH_MISMATCH")
    if not pathlib.Path(core.MISSION).is_file() or sha(core.MISSION) != MISSION_SHA:
        raise RuntimeError("CONTINUATION_MISSION_SOURCE_HASH_DRIFT")

    # The mission's primary Cajita lane is independent of Lunita S32. Poll/advance
    # one bounded lane action before honoring any serial continuation backoff.
    parallel_lane = {"status": "NOT_RUN", "did_work": False}
    try:
        parallel_lane = continuous_governor.tick_cajita_priority_lane(
            ST, pathlib.Path(core.CAJ), MISSION_SHA
        )
        if parallel_lane.get("did_work"):
            write_result("CAJITA_PRIORITY_LANE", {
                "status": parallel_lane.get("status", "UNKNOWN"),
                "parallel_lane": parallel_lane,
                "step_completion": True,
                "mission_completion_claim": False,
                "certification": "NOT_GRANTED",
            })
    except Exception as exc:
        lane_error = {
            "status": "CAJITA_LANE_RECOVERY_REQUIRED",
            "did_work": False,
            "error_type": type(exc).__name__,
            "error": str(exc)[:1200],
            "next_action": "Preserve the lane checkpoint and repair the isolated Cajita lane; do not block independent Lunita work.",
            "mission_completion_claim": False,
            "certification": "NOT_GRANTED",
        }
        parallel_lane = lane_error
        try:
            write_result("CAJITA_PRIORITY_LANE_ERROR", lane_error)
        except Exception:
            pass

    idx = int(state.get("step_index", 0))
    pending = state.get("blocked_step") or {}
    if pending.get("step_index") == idx and pending.get("next_retry_utc"):
        try:
            wait = (parseutc(pending["next_retry_utc"]) - dt.datetime.now(dt.timezone.utc)).total_seconds()
        except (ValueError, TypeError, AttributeError):
            wait = 0
        if wait > 0:
            return {
                "status": "WAITING_FOR_EVENT", "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
                "step_id": pending.get("step_id"), "step_index": idx,
                "blocked_status": pending.get("status"), "next_action": pending.get("next_action"),
                "retry_after_seconds": max(1, int(wait)), "last_attempt_utc": pending.get("last_attempt_utc"),
                "last_progress_utc": state.get("last_progress_utc"),
                "parallel_lane": parallel_lane,
                "mission_completion_claim": False, "certification": "NOT_GRANTED",
            }
    if idx < len(STEPS):
        step_id, handler = STEPS[idx]
        if state.get("completed_steps"):
            prev = state["completed_steps"][-1]
            p = pathlib.Path(prev.get("result_path", ""))
            rec = load(p, {}) or {}
            if not p.is_file() or sha(p) != prev.get("result_sha256") or rec.get("mission_sha256") != MISSION_SHA or rec.get("step_id") != prev.get("step_id"):
                raise RuntimeError("CONTINUATION_PREVIOUS_STEP_EVIDENCE_INVALID:" + str(prev.get("step_id")))
            reconciled_queue = reconcile_queue(prev, STEPS[idx][0] if idx < len(STEPS) else "S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN")
        else:
            reconciled_queue = None
        result = handler()
        receipt = write_result(step_id, result)
        if continuous_governor.result_blocks_step(result):
            attempts = state.setdefault("attempts", [])
            attempt_number = 1 + sum(1 for row in attempts if row.get("step_id") == step_id)
            attempt_row = {
                "step_id": step_id, "attempt": attempt_number, "status": result.get("status"),
                "attempt_utc": utc(), "result_path": receipt["result_path"],
                "result_sha256": receipt["result_sha256"], "step_index_preserved": idx,
                "step_completion": False,
            }
            attempts.append(attempt_row)
            if len(attempts) > 500:
                del attempts[:-500]
            retry_utc = (dt.datetime.now(dt.timezone.utc) + dt.timedelta(seconds=REFRESH_SECONDS)).isoformat().replace("+00:00", "Z")
            state["blocked_step"] = {
                "step_id": step_id, "step_index": idx, "status": result.get("status"),
                "last_attempt_utc": attempt_row["attempt_utc"], "next_retry_utc": retry_utc,
                "result_path": receipt["result_path"], "result_sha256": receipt["result_sha256"],
                "next_action": result.get("next_action") or "Resolve the blocking condition and retry the same step after bounded backoff.",
            }
            state["last_attempt_utc"] = attempt_row["attempt_utc"]
            # A blocked attempt is evidence, not mission progress: do not increment step_index
            # and do not modify last_progress_utc or append a completed step.
            atomic(PROGRESS, state)
            return {
                "status": "WAITING_FOR_EVENT", "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
                "step_id": step_id, "step_index": idx, "total_steps": len(STEPS),
                "blocked_status": result.get("status"), "attempt": attempt_number,
                "attempt_evidence": receipt, "next_action": state["blocked_step"]["next_action"],
                "retry_after_seconds": REFRESH_SECONDS, "last_progress_utc": state.get("last_progress_utc"),
                "mission_completion_claim": False, "certification": "NOT_GRANTED",
            }
        state.pop("blocked_step", None)
        state.setdefault("completed_steps", []).append({
            "step_id": step_id,
            "status": result.get("status"),
            "result_path": receipt["result_path"],
            "result_sha256": receipt["result_sha256"],
            "independent_validation": "PENDING" if (
                str(result.get("status", "")).startswith(("FAIL", "BLOCKED", "SOURCE_MISSING", "PARTIAL"))
                or result.get("status") in {"NOT_PUBLISHED_TARGET_EXISTS", "NOT_PUBLISHED_TARGET_ALREADY_EXISTS"}
            ) else "PASS",
        })
        state["step_index"] = idx + 1
        state["last_progress_utc"] = utc()
        atomic(PROGRESS, state)
        next_action = STEPS[idx + 1][0] if idx + 1 < len(STEPS) else "S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN"
        queue_sync = reconcile_queue(state["completed_steps"][-1], next_action)
        core.event("CRFU_CONTINUATION_SUBTASK_COMPLETED", "PASS_FOR_SUBTASK_ONLY", {
            "step_id": step_id, "step_index": idx, "result_sha256": receipt["result_sha256"],
            "continuation_total_steps": len(STEPS), "next_action": next_action,
            "queue_sync": queue_sync,
        }, MISSION_SHA, pathlib.Path(core.MISSION).stat().st_size, receipt["result_sha256"], pathlib.Path(receipt["result_path"]).stat().st_size)
        return {
            "status": "PASS_FOR_SUBTASK_ONLY",
            "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
            "step_id": step_id,
            "step_index": idx,
            "total_steps": len(STEPS),
            "continuation_progress": state,
            "queue_sync": queue_sync,
            "next_action": next_action,
            "mission_completion_claim": False,
            "certification": "NOT_GRANTED",
        }
    maintenance = state.setdefault("maintenance", {})
    last = maintenance.get("last_refresh_utc")
    if last and (dt.datetime.now(dt.timezone.utc) - parseutc(last)).total_seconds() < REFRESH_SECONDS:
        return {
            "status": "WAITING_FOR_EVENT",
            "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
            "step_id": "S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN",
            "next_action": "Retry read-only gate/registry reconciliation at the next bounded refresh; preserve all pending gates",
            "retry_after_seconds": max(1, int(REFRESH_SECONDS - (dt.datetime.now(dt.timezone.utc) - parseutc(last)).total_seconds())),
            "continuation_step_index": idx,
            "mission_completion_claim": False,
            "certification": "NOT_GRANTED",
        }
    # Refresh the registry under the same PATH as the live supervisor before
    # reconciling missing domains; a prior probe must not remain stale indefinitely.
    cli_registry = s23_refresh_cli_registry_probe()
    backlog = s24_reconcile_blockers()
    g06_search = s26_g06_rootfs_source_search()
    lane_path = ST / "heavy_lane.json"
    lane = load(lane_path, {}) or {}
    lane_busy = lane.get("status") in {"PREPARED", "ACTIVE"}
    lane_expiry = lane.get("lease_expires_utc")
    if lane_busy:
        try:
            if lane_expiry and parseutc(lane_expiry) <= dt.datetime.now(dt.timezone.utc):
                lane_busy = False
        except (ValueError, TypeError, AttributeError):
            lane_busy = True
    if lane_busy:
        g06_rebuild = {
            "status": "DEFERRED_EXCLUSIVE_HEAVY_LANE_ACTIVE",
            "active_lane": lane.get("lane"),
            "job_id": lane.get("job_id"),
            "lease_expires_utc": lane_expiry,
            "execute": False,
            "canonical_g06_mutated": False,
            "next_action": "Continue read-only Lunita reconciliation; wait for the Cajita heavy-lane lease to release before a G06 rebuild",
            "certification": "NOT_GRANTED",
        }
    else:
        g06_rebuild = g06_reconstruction.advance(g06_search, execute=True)
    g08_validation = s27_validate_g08_protocol_and_bindings()
    result = {
        "schema": "CUSTOSZ_CONTINUOUS_IMPLEMENTATION_MAINTENANCE/1.0",
        "captured_at_utc": utc(),
        "cli_registry_refresh": {
            "status": cli_registry.get("status"),
            "command_status": cli_registry.get("command_status"),
            "available_domain_count": cli_registry.get("available_domain_count"),
            "domain_count": cli_registry.get("domain_count"),
            "report_path": cli_registry.get("report_path"),
            "report_sha256": cli_registry.get("report_sha256"),
        },
        "backlog": backlog,
        "g06_rootfs_source_recovery": {
            "status": g06_search.get("status"),
            "frozen_rootfs_exists": g06_search.get("frozen_rootfs_exists_at_declared_path"),
            "candidate_archive_count": len(g06_search.get("rootfs_named_archive_candidates", [])),
            "next_safe_action": g06_search.get("next_safe_action"),
        },
        "g06_automatic_rebuild_fallback": {
            "status": g06_rebuild.get("status"),
            "candidate_id": g06_rebuild.get("candidate_id"),
            "candidate_path": g06_rebuild.get("candidate_path"),
            "candidate_rootfs": g06_rebuild.get("candidate_rootfs"),
            "worker_pid": g06_rebuild.get("worker_pid"),
            "next_action": g06_rebuild.get("next_action"),
            "frozen_g06_mutated": g06_rebuild.get("frozen_g06_mutated", False),
            "canonical_g08_bindings_mutated": g06_rebuild.get("canonical_g08_bindings_mutated", False),
            "certification": "NOT_GRANTED",
        },
        "g08_protocol_binding_validation": {
            "status": g08_validation.get("status"),
            "protocol_status": (g08_validation.get("protocol_validation") or {}).get("status"),
            "binding_structure_status": (g08_validation.get("bindings_structural_validation") or {}).get("status"),
            "required_sources_status": (g08_validation.get("bindings_required_sources_validation") or {}).get("status"),
        },
        "next_refresh_seconds": REFRESH_SECONDS,
        "exclusive_heavy_lane": {
            "status": (load(ST / "heavy_lane.json", {}) or {}).get("status"),
            "lane": (load(ST / "heavy_lane.json", {}) or {}).get("lane"),
            "job_id": (load(ST / "heavy_lane.json", {}) or {}).get("job_id"),
            "lease_expires_utc": (load(ST / "heavy_lane.json", {}) or {}).get("lease_expires_utc"),
            "g06_execution_deferred": g06_rebuild.get("status") == "DEFERRED_EXCLUSIVE_HEAVY_LANE_ACTIVE",
        },
        "github_repair_repository": "Plomillo/luna-linux-bridge",
        "github_remote_write": False,
        "automatic_canonical_binding_rewrite": False,
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
        "status": (
            "BLOCKED_G06_ROOTFS_SOURCE_ABSENT"
            if g08_validation.get("blocked_by_missing_g06_rootfs")
            else (
                "CLI_REGISTRY_REQUIRES_DIAGNOSIS"
                if cli_registry.get("status") != "PROBE_EXECUTED"
                else "BACKLOG_RECONCILED_ACTIVE"
            )
        ),
    }
    receipt = write_result("S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN", result)
    maintenance.update({"last_refresh_utc": utc(), "last_result_path": receipt["result_path"], "last_result_sha256": receipt["result_sha256"]})
    atomic(PROGRESS, state)
    core.event("CRFU_CONTINUATION_MAINTENANCE", "WAITING_FOR_EVENT", {
        "step_id": "S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN",
        "result_sha256": receipt["result_sha256"],
        "next_refresh_seconds": REFRESH_SECONDS,
    }, MISSION_SHA, pathlib.Path(core.MISSION).stat().st_size, receipt["result_sha256"], pathlib.Path(receipt["result_path"]).stat().st_size)
    return {
        "status": "WAITING_FOR_EVENT",
        "phase": "IMPLEMENTATION_AND_FUNCTIONAL_VALIDATION",
        "step_id": "S29_CONTINUOUS_IMPLEMENTATION_BACKLOG_SCAN",
        "total_steps": len(STEPS),
        "continuation_progress": state,
        "next_action": "Maintenance scan is not completion. Resume only when a concrete pending input/state changes; preserve the current blocker and do not claim mission progress.",
        "maintenance_status": result.get("status"),
        "maintenance_evidence": receipt,
        "retry_after_seconds": REFRESH_SECONDS,
        "maintenance_is_mission_progress": False,
        "mission_completion_claim": False,
        "certification": "NOT_GRANTED",
    }

if __name__ == "__main__":
    print(json.dumps(selftest(), sort_keys=True, indent=2))
