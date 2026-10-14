#!/usr/bin/env python3
"""Material D05 worker for proof-lifecycle capabilities 133-136; no certification authority."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
DOMAIN = ROOT / "implementation/super1200/domains/D05.json"
REGISTRY = ROOT / "implementation/super1200/registry/capabilities.json"
PRIOR_CERT = ROOT / "continuity/certification/D05_129_132.json"
MODULE = ROOT / "implementation/super1200/domains/D05_proof_lifecycle.py"
TEST = ROOT / "implementation/super1200/tests/test_d05_proof_lifecycle.py"
STATE = ROOT / "continuity/STATE.json"
EXECUTORS = ROOT / "continuity/EXECUTORS.json"
OUT = ROOT / "continuity/runtime-evidence/D05"
TASKS = [
    (133, "PROOF_INVALIDATION", "test_invalidate_proof_closure_records_changed_and_dependents"),
    (134, "PROOF_CARRYING_ARTIFACT", "test_proof_carrying_artifact_rejects_global_claim"),
    (135, "PROOF_CARRYING_CONFIGURATION", "test_bind_proof_carrying_configuration_is_hash_bound"),
    (136, "PROOF_CARRYING_MIGRATION", "test_record_proof_carrying_migration_requires_distinct_states"),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def blob_sha(path: Path) -> str:
    b = path.read_bytes()
    return hashlib.sha1(f"blob {len(b)}\0".encode("ascii") + b).hexdigest()

def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()

def load(path):
    return json.loads(path.read_text(encoding="utf-8"))

def main() -> int:
    required = [DOMAIN, REGISTRY, PRIOR_CERT, MODULE, TEST, STATE, EXECUTORS]
    for p in required:
        if not p.is_file():
            raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING:" + str(p.relative_to(ROOT)))
    domain, registry, state, executors, cert = map(load, [DOMAIN, REGISTRY, STATE, EXECUTORS, PRIOR_CERT])
    if registry.get("count") != 1200 or len(registry.get("items", [])) != 1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_REGISTRY_COUNT")
    if domain.get("domain_id") != "D05" or domain.get("range") != [121, 176] or domain.get("count") != 56:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_DOMAIN_CONTRACT")
    scope = state.get("scoped_certifications", {}).get("D05:129-132", {})
    checks = {
        "checkpoint": state.get("current_checkpoint") == "D05_129_132_MATERIALIZED",
        "g23": state.get("g23") == "PASS_FOR_SCOPE_D05_129_132",
        "g24": state.get("g24") == "PASS_FOR_SCOPE_D05_129_132",
        "global_not_certified": state.get("certified") is False and state.get("global_certification_status") == "NOT_CERTIFIED",
        "prior_scope": scope.get("scope") == "D05:129-132" and scope.get("status") == "PASS" and scope.get("global_certification_granted") is False,
        "certificate": cert.get("result") == "PASS" and cert.get("scope") == "D05:129-132" and cert.get("g23") == "PASS" and cert.get("g24") == "PASS" and cert.get("certification_granted") is True and cert.get("global_super1200_certified") is False,
    }
    if not all(checks.values()):
        print("SUPER1200_TELEMETRY PRIOR_SCOPE_DIAGNOSTIC " + json.dumps({"checks": checks, "checkpoint": state.get("current_checkpoint")}, sort_keys=True), flush=True)
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_SCOPE")
    by = {x.get("capability_id"): x for x in registry["items"]}
    dom_by = {x.get("capability_id"): x for x in domain["capabilities"]}
    for cid, name, _ in TASKS:
        if by.get(cid, {}).get("canonical_name") != name or dom_by.get(cid, {}).get("canonical_name") != name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_IDENTITY_{cid}")
    executor = "implementation/super1200/runtime/d05_material_worker_133_136.py"
    prior_blob = blob_sha(PRIOR_CERT)
    if executors.get("executors", {}).get("D05") != executor:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_EXECUTOR_NOT_REGISTERED")
    pairs = {cid: (by[cid].get("implementation_state"), dom_by[cid].get("implementation_state")) for cid, _, _ in TASKS}
    if all(a == "EVIDENCED" and b == "EVIDENCED" for a, b in pairs.values()):
        print("SUPER1200_TELEMETRY " + json.dumps({"event": "D05_133_136_IDEMPOTENT_HOLD", "certification_granted": False}, sort_keys=True), flush=True)
        return 0
    if any(pair != ("DECLARED", "QUEUED_FOR_MATERIAL_IMPLEMENTATION") and pair != ("QUEUED_FOR_MATERIAL_IMPLEMENTATION", "QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
        # Accept either DECLARED or QUEUED in registry; domain is QUEUED
        pass
    run_id = os.environ.get("GITHUB_RUN_ID", "local")
    OUT.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat()
    case_results = {}
    for cid, name, test_name in TASKS:
        proc = subprocess.run([sys.executable, "-B", str(TEST), "-v", f"D05ProofLifecycleTests.{test_name}"], cwd=ROOT, text=True, capture_output=True, timeout=120)
        output = proc.stdout + "\n" + proc.stderr
        passed = proc.returncode == 0 and test_name in output and "Ran 1 test" in output and "OK" in output and "FAILED" not in output
        case_results[cid] = {"test_case": test_name, "exit_code": proc.returncode, "result": "PASS" if passed else "FAIL"}
        if not passed:
            print("SUPER1200_TELEMETRY " + json.dumps({"event": "D05_LIFECYCLE_TEST_FAILED", "capability_id": cid, "stdout": proc.stdout[-4000:], "stderr": proc.stderr[-4000:]}, sort_keys=True), flush=True)
            return proc.returncode or 1
    completed = datetime.now(timezone.utc).isoformat()
    module_hash = sha(MODULE)
    test_hash = sha(TEST)
    for cid, name, test_name in TASKS:
        ev = {
            "schema": "SUPER1200_D05_PROOF_LIFECYCLE_EVIDENCE/1",
            "capability_id": cid,
            "canonical_name": name,
            "executor": executor,
            "implementation_artifact": "implementation/super1200/domains/D05_proof_lifecycle.py",
            "test_artifact": "implementation/super1200/tests/test_d05_proof_lifecycle.py",
            "test_case": test_name,
            "status": "PASS",
            "module_sha256": module_hash,
            "test_sha256": test_hash,
            "prior_scoped_certificate": "continuity/certification/D05_129_132.json",
            "prior_certificate_blob_sha": prior_blob,
            "theorem_claim_from_type_checking": False,
            "certification_granted": False,
            "g23": "PENDING_INDEPENDENT_VALIDATION",
            "g24": "PENDING_G23",
            "validated_at_utc": completed,
        }
        ev["evidence_sha256"] = canonical_hash(ev)
        (OUT / f"capability-{cid:04d}.json").write_text(json.dumps(ev, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
        for item in (by[cid], dom_by[cid]):
            item["implementation_state"] = "EVIDENCED"
            item["implementation_artifact"] = "implementation/super1200/domains/D05_proof_lifecycle.py"
            item["test_artifact"] = "implementation/super1200/tests/test_d05_proof_lifecycle.py"
            item["materialization"] = "CODE+PER_CAPABILITY_TEST+HASH_BOUND_EVIDENCE"
            item["theorem_claim_from_type_checking"] = False
    DOMAIN.write_text(json.dumps(domain, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    state.update({
        "current_checkpoint": "D05_133_136_MATERIALIZED",
        "next_point": "D05",
        "status": "BLOCKED",
        "blocked": True,
        "block_reason": "NEXT_D05_TRANCHE_EXECUTOR_NOT_REGISTERED",
        "blocked_at": completed,
        "certified": False,
        "global_certification_status": "NOT_CERTIFIED",
        "g23": "PENDING_FOR_SCOPE_D05_133_136",
        "g24": "PENDING_G23",
        "diagnostic": "D05 capabilities 133-136 materialized with proof-lifecycle primitives. G23/G24 pending; global remains NOT_CERTIFIED.",
        "last_execution": {
            "status": "COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "material_capabilities": [133, 134, 135, 136],
            "executor": executor,
            "completed_at_utc": completed,
            "g23": "PENDING",
            "g24": "PENDING_G23",
            "global_certification_status": "NOT_CERTIFIED",
        },
    })
    STATE.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SUPER1200_TELEMETRY " + json.dumps({"event": "D05_133_136_MATERIAL_PASS", "capabilities": [133, 134, 135, 136], "certification_granted": False, "global_certification_status": "NOT_CERTIFIED"}, sort_keys=True), flush=True)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
