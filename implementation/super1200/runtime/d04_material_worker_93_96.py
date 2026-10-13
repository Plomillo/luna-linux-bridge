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
    pending = [cid for cid, _, _ in TASKS if by_id[cid].get("implementation_state") != "EVIDENCED"]
    if not pending:
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event":"D04_MATERIAL_WORKER_IDEMPOTENT_HOLD", "capabilities":[x[0] for x in TASKS],
            "reason":"ALL_CAPABILITIES_ALREADY_EVIDENCED", "certification_granted":False
        }, sort_keys=True), flush=True)
        return 0
    if any(by_id[cid].get("implementation_state") != "QUEUED_FOR_MATERIAL_IMPLEMENTATION" for cid in pending):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY UNEXPECTED_CAPABILITY_STATE")
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    run = subprocess.run([sys.executable, "-B", str(TEST)], cwd=ROOT, text=True,
                         capture_output=True, timeout=240)
    if run.returncode:
        print("SUPER1200_TELEMETRY " + json.dumps({
            "event":"D04_MATERIAL_TESTS_FAILED", "exit_code":run.returncode,
            "stdout":run.stdout[-12000:], "stderr":run.stderr[-12000:],
            "module_sha256":digest(MODULE), "test_sha256":digest(TEST)
        }, sort_keys=True), flush=True)
        return run.returncode or 1
    module_hash, test_hash = digest(MODULE), digest(TEST)
    suite_stdout_hash = hashlib.sha256(run.stdout.encode()).hexdigest()
    suite_stderr_hash = hashlib.sha256(run.stderr.encode()).hexdigest()
    for cid, name, test_name in TASKS:
        if by_id[cid].get("implementation_state") == "EVIDENCED":
            continue
        evidence = {
            "schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1",
            "capability_id":cid, "canonical_name":name,
            "executor":"implementation/super1200/runtime/d04_material_worker_93_96.py",
            "implementation_artifact":"implementation/super1200/domains/D04_runtime.py",
            "test_artifact":"implementation/super1200/tests/test_d04_runtime.py",
            "test_case":test_name, "status":"PASS",
            "validated_at_utc":datetime.now(timezone.utc).isoformat(),
            "worker_started_at_utc":started,
            "module_sha256":module_hash, "test_sha256":test_hash,
            "suite_stdout_sha256":suite_stdout_hash, "suite_stderr_sha256":suite_stderr_hash,
            "suite_exit_code":run.returncode,
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
            item["materialization"] = "CODE+BEHAVIOR_TEST+HASH_BOUND_EVIDENCE"
    DOMAIN.write_text(json.dumps(domain, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    state.update({
        "current_checkpoint":"D04_93_96_MATERIALIZED",
        "next_point":"D04",
        "status":"BLOCKED",
        "blocked":True,
        "block_reason":"NEXT_D04_TRANCHE_EXECUTOR_NOT_REGISTERED",
        "blocked_at":datetime.now(timezone.utc).isoformat(),
        "active_worker":False,
        "material_worker_ready":False,
        "certified":False,
        "global_certification_status":"NOT_CERTIFIED",
        "g23":"PENDING_FOR_SCOPE_D04_93_96",
        "g24":"PENDING_G23",
        "diagnostic":"D04 capabilities 93-96 materially implemented and behavior-tested with hash-bound evidence. Continuation is held fail-closed because no reviewed task-specific executor is registered for the next pending D04 tranche. MetaOS remains deferred.",
        "recovery_note":"Register and review a material executor for the next pending D04 tranche; do not rerun completed IDs or propagate scoped validation/certification. GitHub-hosted bounded workflow is authoritative; no local runner required."
    })
    state["last_material_execution"] = {
        "executor":"implementation/super1200/runtime/d04_material_worker_93_96.py",
        "capabilities":[93,94,95,96],
        "tests":"PASS",
        "module_sha256":module_hash,
        "test_sha256":test_hash,
        "g23":"PENDING",
        "g24":"PENDING",
        "certification_granted":False,
        "completed_at_utc":datetime.now(timezone.utc).isoformat()
    }
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False)+"\n", encoding="utf-8")
    print("SUPER1200_TELEMETRY " + json.dumps({
        "event":"D04_MATERIAL_IMPLEMENTATION_PASS", "capabilities":[93,94,95,96],
        "count":4, "module_sha256":module_hash, "test_sha256":test_hash,
        "suite_exit_code":run.returncode, "g23":"PENDING",
        "g24":"PENDING_G23", "certification_granted":False,
        "next_state":"BLOCKED_NEXT_EXECUTOR_REQUIRED"
    }, sort_keys=True), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
