#!/usr/bin/env python3
"""Material D04 worker for capability IDs 93-96; no certification authority."""
from __future__ import annotations
import hashlib, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "implementation/super1200/domains/D04.json"
REGISTRY = ROOT / "implementation/super1200/registry/capabilities.json"
MODULE = ROOT / "implementation/super1200/domains/D04_runtime.py"
TEST = ROOT / "implementation/super1200/tests/test_d04_runtime.py"
STATE = ROOT / "continuity/STATE.json"
OUT = ROOT / "continuity/runtime-evidence/D04"
TASKS = [
    (93, "CERTIFICATION_NON_TRANSITIVITY",
     "test_certification_non_transitivity_rejects_derived_subject_and_scope"),
    (94, "EVIDENCE_EXPIRATION",
     "test_evidence_expiration_uses_half_open_utc_interval_and_fails_closed"),
    (95, "EVIDENCE_INVALIDATION_GRAPH",
     "test_evidence_invalidation_graph_propagates_and_rejects_cycles"),
    (96, "EVIDENCE_REUSE_ENGINE",
     "test_evidence_reuse_requires_exact_validated_non_invalidated_key"),
]

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main() -> int:
    for path in (DOMAIN, REGISTRY, MODULE, TEST, STATE):
        if not path.is_file():
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={path.relative_to(ROOT)}")
    domain = json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8"))
    if registry.get("count") != 1200 or len(registry.get("items", [])) != 1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_COUNT_MISMATCH")
    if domain.get("domain_id") != "D04" or domain.get("range") != [81, 120]:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH")
    by_id = {item.get("capability_id"): item for item in registry["items"]}
    domain_by_id = {item.get("capability_id"): item for item in domain.get("capabilities", [])}
    for cid, name, _ in TASKS:
        if cid not in by_id or by_id[cid].get("canonical_name") != name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_IDENTITY_MISMATCH ID={cid}")
        if cid not in domain_by_id or domain_by_id[cid].get("canonical_name") != name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH ID={cid}")
    state_pairs = {
        cid: (by_id[cid].get("implementation_state"), domain_by_id[cid].get("implementation_state"))
        for cid, _, _ in TASKS
    }
    if all(reg_state == "EVIDENCED" and domain_state == "EVIDENCED"
           for reg_state, domain_state in state_pairs.values()):
        for cid, name, test_name in TASKS:
            evidence_path = OUT / f"capability-{cid:04d}.json"
            if not evidence_path.is_file():
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING_PRIOR_EVIDENCE ID={cid}")
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            recorded_hash = evidence.get("evidence_sha256")
            unsigned_evidence = dict(evidence)
            unsigned_evidence.pop("evidence_sha256", None)
            computed_hash = hashlib.sha256(json.dumps(
                unsigned_evidence, sort_keys=True, separators=(",",":"), ensure_ascii=False
            ).encode()).hexdigest()
            if (evidence.get("capability_id") != cid or evidence.get("canonical_name") != name
                    or evidence.get("test_case") != test_name or recorded_hash != computed_hash
                    or evidence.get("status") != "PASS"):
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_EVIDENCE_INTEGRITY ID={cid}")
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event":"D04_MATERIAL_WORKER_IDEMPOTENT_HOLD", "capabilities":[x[0] for x in TASKS],
            "reason":"ALL_CAPABILITIES_EVIDENCED_AND_PRIOR_EVIDENCE_HASHES_VERIFIED",
            "certification_granted":False
        }, sort_keys=True), flush=True)
        return 0
    if any(pair != ("DECLARED", "QUEUED_FOR_MATERIAL_IMPLEMENTATION")
           for pair in state_pairs.values()):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY UNEXPECTED_OR_PARTIAL_CAPABILITY_STATE")
    if (state.get("current_checkpoint") != "D04_87_92_MATERIALIZED"
            or state.get("blocked") is not False
            or state.get("status") not in {"ACTIVE", "READY_FOR_CONTINUATION"}
            or state.get("material_worker_ready") is not True):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY CHECKPOINT_RECONCILIATION_REQUIRED")
    if not __import__("os").environ.get("GITHUB_RUN_ID"):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY GITHUB_RUN_ID_REQUIRED")
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    suite = subprocess.run([sys.executable, "-B", str(TEST), "-v"], cwd=ROOT, text=True,
                           capture_output=True, timeout=240)
    suite_output = suite.stdout + "\n" + suite.stderr
    expected_test_names = [task[2] for task in TASKS]
    if suite.returncode or any(name not in suite_output for name in expected_test_names):
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event":"D04_MATERIAL_TESTS_FAILED_OR_INCOMPLETE", "exit_code":suite.returncode,
            "required_test_names_seen":{name:name in suite_output for name in expected_test_names},
            "stdout":suite.stdout[-12000:], "stderr":suite.stderr[-12000:],
            "module_sha256":digest(MODULE), "test_sha256":digest(TEST)
        }, sort_keys=True), flush=True)
        return suite.returncode or 1
    case_results = {}
    for cid, name, test_name in TASKS:
        selected = subprocess.run(
            [sys.executable, "-B", str(TEST), "-v", f"D04RuntimeTests.{test_name}"],
            cwd=ROOT, text=True, capture_output=True, timeout=120
        )
        selected_output = selected.stdout + "\n" + selected.stderr
        selected_pass = (
            selected.returncode == 0 and test_name in selected_output
            and "Ran 1 test" in selected_output and "OK" in selected_output
            and "FAILED" not in selected_output
        )
        case_results[cid] = {
            "test_case":test_name,
            "exit_code":selected.returncode,
            "result":"PASS" if selected_pass else "FAIL",
            "stdout_sha256":hashlib.sha256(selected.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(selected.stderr.encode()).hexdigest(),
            "test_name_seen":test_name in selected_output,
            "single_test_run_confirmed":"Ran 1 test" in selected_output,
            "unittest_ok_marker":"OK" in selected_output and "FAILED" not in selected_output
        }
        if not selected_pass:
            print("SUPER1200_TELEMETRY " + json.dumps({
                "event":"D04_CAPABILITY_TEST_FAILED", "capability_id":cid,
                "test_case":test_name, "exit_code":selected.returncode,
                "stdout":selected.stdout[-12000:], "stderr":selected.stderr[-12000:]
            }, sort_keys=True), flush=True)
            return selected.returncode or 1
    module_hash, test_hash = digest(MODULE), digest(TEST)
    suite_stdout_hash = hashlib.sha256(suite.stdout.encode()).hexdigest()
    suite_stderr_hash = hashlib.sha256(suite.stderr.encode()).hexdigest()
    for cid, name, test_name in TASKS:
        case = case_results[cid]
        evidence = {
            "schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1",
            "capability_id":cid, "canonical_name":name,
            "executor":"implementation/super1200/runtime/d04_material_worker_93_96.py",
            "implementation_artifact":"implementation/super1200/domains/D04_runtime.py",
            "test_artifact":"implementation/super1200/tests/test_d04_runtime.py",
            "test_case":test_name, "status":"PASS",
            "test_invocation":["python", "-B", "test_d04_runtime.py", "-v", f"D04RuntimeTests.{test_name}"],
            "selected_test_result":case,
            "validated_at_utc":datetime.now(timezone.utc).isoformat(),
            "worker_started_at_utc":started,
            "github_actions_run_id":__import__("os").environ.get("GITHUB_RUN_ID"),
            "module_sha256":module_hash, "test_sha256":test_hash,
            "suite_stdout_sha256":suite_stdout_hash, "suite_stderr_sha256":suite_stderr_hash,
            "suite_exit_code":suite.returncode,
            "g23":"PENDING_INDEPENDENT_VALIDATION", "g24":"PENDING_G23",
            "certification_granted":False
        }
        evidence["evidence_sha256"] = hashlib.sha256(
            json.dumps(evidence, sort_keys=True, separators=(",",":"), ensure_ascii=False).encode()
        ).hexdigest()
        (OUT / f"capability-{cid:04d}.json").write_text(
            json.dumps(evidence, indent=2, sort_keys=True)+"\n", encoding="utf-8")
        for item in (by_id[cid], domain_by_id[cid]):
            item["implementation_state"] = "EVIDENCED"
            item["implementation_artifact"] = "implementation/super1200/domains/D04_runtime.py"
            item["test_artifact"] = "implementation/super1200/tests/test_d04_runtime.py"
            item["materialization"] = "CODE+PER_CAPABILITY_TEST+FULL_SUITE+HASH_BOUND_EVIDENCE"
    DOMAIN.write_text(json.dumps(domain, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    previous_execution = state.get("last_execution")
    reconciled_previous = None
    if previous_execution and previous_execution.get("workflow_run_id") == 38469912731:
        reconciled_previous = dict(previous_execution)
        reconciled_previous.update({
            "status":"COMPLETED_FAILURE_RECONCILED",
            "remote_status":"completed",
            "remote_conclusion":"failure",
            "reconciled_at_utc":now,
            "reconciliation_source_url":"https://api.github.com/repos/Plomillo/luna-linux-bridge/actions/runs/38469912731"
        })
        if reconciled_previous.get("status") != previous_execution.get("status"):
            history = state.setdefault("execution_history", [])
            if not any(item.get("workflow_run_id") == 38469912731 for item in history):
                history.append(reconciled_previous)
    run_id = __import__("os").environ["GITHUB_RUN_ID"]
    server_url = __import__("os").environ.get("GITHUB_SERVER_URL", "https://github.com")
    repo_name = __import__("os").environ.get("GITHUB_REPOSITORY", "Plomillo/luna-linux-bridge")
    run_url = f"{server_url}/{repo_name}/actions/runs/{run_id}"
    state.update({
        "current_checkpoint":"D04_93_96_MATERIALIZED",
        "next_point":"D04",
        "status":"BLOCKED",
        "blocked":True,
        "block_reason":"NEXT_D04_TRANCHE_EXECUTOR_NOT_REGISTERED",
        "blocked_at":now,
        "active_worker":False,
        "material_worker_ready":False,
        "certified":False,
        "global_certification_status":"NOT_CERTIFIED",
        "g23":"PENDING_FOR_SCOPE_D04_93_96",
        "g24":"PENDING_G23",
        "diagnostic":"D04 capabilities 93-96 materially implemented. The full D04 test suite and each mapped capability test were executed independently; hash-bound evidence was recorded. Continuation is held fail-closed because no reviewed task-specific executor is registered for the next pending D04 tranche. MetaOS remains deferred.",
        "recovery_note":"Register and review a material executor for the next pending D04 tranche; do not rerun completed IDs or propagate scoped validation/certification. GitHub-hosted bounded workflow is authoritative; no local runner required.",
        "execution_reconciliation":{
            "workflow_run_id":38469912731,
            "previously_reported_status":"IN_PROGRESS",
            "verified_remote_status":"completed",
            "verified_remote_conclusion":"failure",
            "source_url":"https://api.github.com/repos/Plomillo/luna-linux-bridge/actions/runs/38469912731",
            "reconciled_at_utc":now
        },
        "last_execution":{
            "workflow_run_id":int(run_id),
            "workflow_url":run_url,
            "status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "started_at_utc":started,
            "completed_at_utc":now,
            "configured_runtime_hours":0.05,
            "material_capabilities":[93,94,95,96],
            "behavior_tests":"FULL_SUITE_PASS;4_OF_4_CAPABILITY_TESTS_PASS",
            "executor":"implementation/super1200/runtime/d04_material_worker_93_96.py",
            "g23":"PENDING",
            "g24":"PENDING_G23",
            "global_certification_status":"NOT_CERTIFIED"
        }
    })
    state["last_material_execution"] = {
        "executor":"implementation/super1200/runtime/d04_material_worker_93_96.py",
        "capabilities":[93,94,95,96],
        "tests":"FULL_SUITE_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS",
        "test_case_results":[case_results[cid] for cid, _, _ in TASKS],
        "module_sha256":module_hash,
        "test_sha256":test_hash,
        "github_actions_run_id":run_id,
        "g23":"PENDING",
        "g24":"PENDING",
        "certification_granted":False,
        "completed_at_utc":now
    }
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("SUPER1200_TELEMETRY " + json.dumps({
        "event":"D04_MATERIAL_IMPLEMENTATION_PASS", "capabilities":[93,94,95,96],
        "count":4, "module_sha256":module_hash, "test_sha256":test_hash,
        "suite_exit_code":suite.returncode,
        "per_capability_tests":{cid:case_results[cid]["result"] for cid,_,_ in TASKS},
        "g23":"PENDING", "g24":"PENDING_G23", "certification_granted":False,
        "next_state":"BLOCKED_NEXT_EXECUTOR_REQUIRED",
        "github_actions_run_id":run_id
    }, sort_keys=True), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
