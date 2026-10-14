#!/usr/bin/env python3
"""Scoped G23/G24 for D05 133-136. Never grants global SUPER1200 certification."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(".").resolve()
SCOPE = "D05:133-136"
EXPECTED = {
    133: ("PROOF_INVALIDATION", "test_invalidate_proof_closure_records_changed_and_dependents"),
    134: ("PROOF_CARRYING_ARTIFACT", "test_proof_carrying_artifact_rejects_global_claim"),
    135: ("PROOF_CARRYING_CONFIGURATION", "test_bind_proof_carrying_configuration_is_hash_bound"),
    136: ("PROOF_CARRYING_MIGRATION", "test_record_proof_carrying_migration_requires_distinct_states"),
}
MODULE = ROOT / "implementation/super1200/domains/D05_proof_lifecycle.py"
TEST = ROOT / "implementation/super1200/tests/test_d05_proof_lifecycle.py"
PRIOR_PATH = ROOT / "continuity/certification/D05_129_132.json"
PRIOR_MODULE = ROOT / "implementation/super1200/domains/D05_proof_assurance.py"
PRIOR_TEST = ROOT / "implementation/super1200/tests/test_d05_proof_assurance.py"
CHAIN_PATH = ROOT / "continuity/certification/D05_125_128.json"
SUITES = [
    "implementation/super1200/tests/test_shared.py",
    "implementation/super1200/tests/test_d03_runtime.py",
    "implementation/super1200/tests/test_d04_runtime.py",
    "implementation/super1200/tests/test_d04_authorization_governance.py",
    "implementation/super1200/tests/test_d04_governance_controls.py",
    "implementation/super1200/tests/test_d04_trust_controls.py",
    "implementation/super1200/tests/test_d05_formal_reasoning.py",
    "implementation/super1200/tests/test_d05_formal_foundations.py",
    "implementation/super1200/tests/test_d05_proof_assurance.py",
    "implementation/super1200/tests/test_d05_proof_lifecycle.py",
]


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob_sha(path: Path) -> str:
    blob = path.read_bytes()
    return hashlib.sha1(f"blob {len(blob)}\0".encode("ascii") + blob).hexdigest()


def evidence_hash(ev: dict) -> str:
    unsigned = dict(ev)
    unsigned.pop("evidence_sha256", None)
    return hashlib.sha256(
        json.dumps(unsigned, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def deny(stage: str, reason: str) -> None:
    raise SystemExit(f"{stage}_D05_133_136_DENY:{reason}")


def run_suite(rel: str, stage: str) -> dict:
    proc = subprocess.run(
        [sys.executable, "-B", str(ROOT / rel), "-v"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        timeout=300,
    )
    if proc.returncode != 0:
        print(proc.stdout[-8000:])
        print(proc.stderr[-8000:])
        deny(stage, "REGRESSION:" + rel)
    return {
        "path": rel,
        "exit_code": 0,
        "test_sha256": sha(ROOT / rel),
        "stdout_sha256": hashlib.sha256(proc.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
    }


def assert_scope_ready(state: dict, stage: str) -> None:
    if state.get("current_checkpoint") != "D05_133_136_MATERIALIZED":
        deny(stage, "CHECKPOINT")
    if state.get("certified") is not False or state.get("global_certification_status") != "NOT_CERTIFIED":
        deny(stage, "GLOBAL_CERTIFICATION_DRIFT")
    last = state.get("last_execution") or {}
    if last.get("status") != "COMPLETED_SUCCESS_MATERIAL_TRANCHE" or last.get("material_capabilities") != [133, 134, 135, 136]:
        deny(stage, "MATERIAL_RUN_SCOPE")
    if state.get("g23") != "PENDING_FOR_SCOPE_D05_133_136" or state.get("g24") != "PENDING_G23":
        deny(stage, "GATE_STATE")
    prior_state = (state.get("scoped_certifications") or {}).get("D05:129-132", {})
    if prior_state.get("scope") != "D05:129-132" or prior_state.get("status") != "PASS" or prior_state.get("global_certification_granted") is not False:
        deny(stage, "PRIOR_SCOPE_STATE")


def assert_prior_certificate(stage: str) -> tuple[dict, str]:
    if not PRIOR_PATH.is_file():
        deny(stage, "PRIOR_CERTIFICATE_MISSING")
    prior = load(PRIOR_PATH)
    if prior.get("result") != "PASS" or prior.get("scope") != "D05:129-132" or prior.get("g23") != "PASS" or prior.get("g24") != "PASS":
        deny(stage, "PRIOR_CERTIFICATE_SCOPE")
    if prior.get("certification_granted") is not True or prior.get("global_super1200_certified") is not False or prior.get("scope_only") is not True:
        deny(stage, "PRIOR_CERTIFICATE_BOUNDARY")
    if prior.get("theorem_claim_from_type_checking") is not False:
        deny(stage, "PRIOR_THEOREM_OVERCLAIM")
    if prior.get("module_sha256") != sha(PRIOR_MODULE) or prior.get("test_sha256") != sha(PRIOR_TEST):
        deny(stage, "PRIOR_SOURCE_DRIFT")
    if not CHAIN_PATH.is_file() or prior.get("prior_certificate_blob_sha") != git_blob_sha(CHAIN_PATH):
        deny(stage, "PRIOR_CERTIFICATE_CHAIN_DRIFT")
    return prior, git_blob_sha(PRIOR_PATH)


def assert_evidence(stage: str, prior_blob: str, module_hash: str, test_hash: str) -> list[dict]:
    domain = load(ROOT / "implementation/super1200/domains/D05.json")
    reg = load(ROOT / "implementation/super1200/registry/capabilities.json")
    if domain.get("domain_id") != "D05" or domain.get("range") != [121, 176] or domain.get("count") != 56:
        deny(stage, "DOMAIN_CONTRACT")
    if reg.get("count") != 1200 or len(reg.get("items", [])) != 1200:
        deny(stage, "GLOBAL_REGISTRY_COUNT")
    reg_by = {item["capability_id"]: item for item in reg["items"]}
    dom_by = {item["capability_id"]: item for item in domain["capabilities"]}
    evidence = []
    for cid, (name, test_name) in EXPECTED.items():
        if reg_by.get(cid, {}).get("canonical_name") != name or reg_by[cid].get("implementation_state") != "EVIDENCED":
            deny(stage, f"REGISTRY_STATE_{cid}")
        if dom_by.get(cid, {}).get("canonical_name") != name or dom_by[cid].get("implementation_state") != "EVIDENCED":
            deny(stage, f"DOMAIN_STATE_{cid}")
        path = ROOT / "continuity/runtime-evidence/D05" / f"capability-{cid:04d}.json"
        if not path.is_file():
            deny(stage, f"EVIDENCE_MISSING_{cid}")
        ev = load(path)
        if ev.get("evidence_sha256") != evidence_hash(ev):
            deny(stage, f"EVIDENCE_HASH_{cid}")
        if ev.get("schema") != "SUPER1200_D05_PROOF_LIFECYCLE_EVIDENCE/1":
            deny(stage, f"EVIDENCE_SCHEMA_{cid}")
        if ev.get("status") != "PASS" or ev.get("capability_id") != cid or ev.get("canonical_name") != name or ev.get("test_case") != test_name:
            deny(stage, f"EVIDENCE_SCOPE_{cid}")
        if ev.get("module_sha256") != module_hash or ev.get("test_sha256") != test_hash:
            deny(stage, f"EVIDENCE_SOURCE_HASH_{cid}")
        if ev.get("prior_scoped_certificate") != "continuity/certification/D05_129_132.json" or ev.get("prior_certificate_blob_sha") != prior_blob:
            deny(stage, f"EVIDENCE_PRIOR_CERT_{cid}")
        if ev.get("theorem_claim_from_type_checking") is not False or ev.get("certification_granted") is not False:
            deny(stage, f"EVIDENCE_OVERCLAIM_{cid}")
        if ev.get("g23") != "PENDING_INDEPENDENT_VALIDATION" or ev.get("g24") != "PENDING_G23":
            deny(stage, f"EVIDENCE_GATE_STATE_{cid}")
        evidence.append({"capability_id": cid, "evidence_sha256": ev["evidence_sha256"], "test_case": test_name})
    return evidence


def specific_tests(stage: str) -> list[dict]:
    found = []
    for cid, (_, test_name) in EXPECTED.items():
        proc = subprocess.run(
            [sys.executable, "-B", str(TEST), "-v", f"D05ProofLifecycleTests.{test_name}"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=120,
        )
        output = proc.stdout + "\n" + proc.stderr
        if proc.returncode != 0 or test_name not in output or "Ran 1 test" not in output or "OK" not in output or "FAILED" in output:
            print(output[-10000:])
            deny(stage, "SPECIFIC_TEST:" + str(cid))
        found.append({
            "capability_id": cid,
            "test_case": test_name,
            "result": "PASS",
            "exit_code": 0,
            "stderr_sha256": hashlib.sha256(proc.stderr.encode()).hexdigest(),
            "single_test_run_confirmed": True,
        })
    return found


def g23() -> None:
    state = load(ROOT / "continuity/STATE.json")
    assert_scope_ready(state, "G23")
    _prior, prior_blob = assert_prior_certificate("G23")
    module_hash, test_hash = sha(MODULE), sha(TEST)
    evidence = assert_evidence("G23", prior_blob, module_hash, test_hash)
    suites = [run_suite(rel, "G23") for rel in SUITES]
    specific = specific_tests("G23")
    run_id = int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else 0
    run_url = ""
    if os.environ.get("GITHUB_REPOSITORY") and run_id:
        server = os.environ.get("GITHUB_SERVER_URL", "https://github.com")
        run_url = f"{server}/{os.environ['GITHUB_REPOSITORY']}/actions/runs/{run_id}"
    record = {
        "schema": "SUPER1200_G23_VALIDATION/1",
        "result": "PASS",
        "scope": SCOPE,
        "validator_workflow_run_id": run_id,
        "validator_workflow_url": run_url,
        "source_commit": os.environ.get("GITHUB_SHA", "local"),
        "module_sha256": module_hash,
        "test_sha256": test_hash,
        "prior_certificate_blob_sha": prior_blob,
        "evidence": evidence,
        "regression_suites": suites,
        "specific_tests": specific,
        "theorem_claim_from_type_checking": False,
        "g23": "PASS_FOR_SCOPE_D05_133_136",
        "g24": "PENDING_G23",
        "certification_granted": False,
        "global_super1200_certified": False,
    }
    (ROOT / "g23-validation.json").write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    output = os.environ.get("GITHUB_OUTPUT")
    if output:
        with open(output, "a", encoding="utf-8") as handle:
            handle.write("result=PASS\nscope=D05:133-136\n")
    print("SUPER1200_G23_PASS " + json.dumps({
        "scope": SCOPE,
        "specific_tests": "4/4 PASS",
        "regression_suites": len(suites),
        "global_certification": "NOT_CERTIFIED",
    }, sort_keys=True))


def g24() -> None:
    if os.environ.get("G23_RESULT") != "PASS" or os.environ.get("G23_SCOPE") != SCOPE:
        deny("G24", "CALLER_OUTPUT")
    g23_record = load(ROOT / "g23-validation.json")
    if g23_record.get("result") != "PASS" or g23_record.get("scope") != SCOPE or g23_record.get("theorem_claim_from_type_checking") is not False:
        deny("G24", "G23_ARTIFACT_SCOPE")
    if g23_record.get("certification_granted") is not False or g23_record.get("global_super1200_certified") is not False:
        deny("G24", "G23_OVERCLAIM")
    state = load(ROOT / "continuity/STATE.json")
    assert_scope_ready(state, "G24")
    _prior, prior_blob = assert_prior_certificate("G24")
    module_hash, test_hash = sha(MODULE), sha(TEST)
    if g23_record.get("module_sha256") != module_hash or g23_record.get("test_sha256") != test_hash:
        deny("G24", "G23_SOURCE_HASH_DRIFT")
    if g23_record.get("prior_certificate_blob_sha") != prior_blob:
        deny("G24", "PRIOR_CERTIFICATE_BLOB_DRIFT")
    evidence = assert_evidence("G24", prior_blob, module_hash, test_hash)
    for rel in SUITES:
        run_suite(rel, "G24")
    specific_tests("G24")
    cert = {
        "schema": "SUPER1200_G24_CERTIFICATION_DECISION/1",
        "result": "PASS",
        "scope": SCOPE,
        "basis": "G23_PASS_PLUS_INDEPENDENT_G24_SOURCE_REVALIDATION",
        "g23": "PASS",
        "g24": "PASS",
        "certification_granted": True,
        "scope_only": True,
        "global_super1200_certified": False,
        "theorem_claim_from_type_checking": False,
        "module_sha256": module_hash,
        "test_sha256": test_hash,
        "prior_certificate": "continuity/certification/D05_129_132.json",
        "prior_certificate_blob_sha": prior_blob,
        "g23_workflow_run_id": g23_record.get("validator_workflow_run_id"),
        "g24_workflow_run_id": int(os.environ["GITHUB_RUN_ID"]) if os.environ.get("GITHUB_RUN_ID") else 0,
        "evidence": [{"capability_id": item["capability_id"], "evidence_sha256": item["evidence_sha256"]} for item in evidence],
    }
    (ROOT / "g24-certification-decision.json").write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print("SUPER1200_G24_PASS " + json.dumps({
        "scope": SCOPE,
        "certification_granted": True,
        "global_super1200_certified": False,
    }, sort_keys=True))


def persist() -> None:
    cert = load(ROOT / "g24-certification-decision.json")
    if cert.get("result") != "PASS" or cert.get("scope") != SCOPE or cert.get("global_super1200_certified") is not False or cert.get("scope_only") is not True:
        deny("G24_PERSIST", "CERTIFICATE_SCOPE")
    state_path = ROOT / "continuity/STATE.json"
    state = load(state_path)
    if state.get("current_checkpoint") != "D05_133_136_MATERIALIZED" or state.get("g23") != "PENDING_FOR_SCOPE_D05_133_136":
        deny("G24_PERSIST", "CHECKPOINT")
    if state.get("global_certification_status") != "NOT_CERTIFIED" or state.get("certified") is not False:
        deny("G24_PERSIST", "GLOBAL")
    now = datetime.now(timezone.utc).isoformat()
    out = ROOT / "continuity/certification/D05_133_136.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    state["g23"] = "PASS_FOR_SCOPE_D05_133_136"
    state["g24"] = "PASS_FOR_SCOPE_D05_133_136"
    state["certified"] = False
    state["global_certification_status"] = "NOT_CERTIFIED"
    record = {
        "scope": SCOPE,
        "status": "PASS",
        "record_path": "continuity/certification/D05_133_136.json",
        "workflow_run_id": cert.get("g24_workflow_run_id"),
        "certification_granted": True,
        "global_certification_granted": False,
    }
    state["scoped_certification"] = record
    scopes = state.get("scoped_certifications") or {}
    if scopes.get("D05:129-132", {}).get("status") != "PASS":
        deny("G24_PERSIST", "PRIOR_SCOPE_LOST")
    scopes[SCOPE] = record
    state["scoped_certifications"] = scopes
    state["status"] = "BLOCKED"
    state["blocked"] = True
    state["block_reason"] = "NEXT_D05_TRANCHE_EXECUTOR_NOT_REGISTERED"
    state["blocked_at"] = now
    state["active_worker"] = False
    state["next_point"] = "D05"
    state["next_tranche_authorization"] = None
    state["diagnostic"] = (
        "D05 capabilities 133-136 passed scoped G23/G24. "
        "Continuation is held fail-closed until a reviewed executor for the next D05 tranche is registered. "
        "Scoped certification does not propagate. Global SUPER1200 certification remains NOT_CERTIFIED."
    )
    last = state.get("last_execution") or {}
    last["g23"] = "PASS_FOR_SCOPE_D05_133_136"
    last["g24"] = "PASS_FOR_SCOPE_D05_133_136"
    last["global_certification_status"] = "NOT_CERTIFIED"
    state["last_execution"] = last
    state_path.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("SUPER1200_G24_PERSISTENCE=PASS SCOPE=D05:133-136 GLOBAL_CERTIFICATION=FALSE")


def main() -> None:
    stage = os.environ.get("GATE_STAGE", "")
    if stage == "G23":
        g23()
    elif stage == "G24":
        g24()
    elif stage == "PERSIST":
        persist()
    else:
        deny("GATE", "STAGE")


if __name__ == "__main__":
    main()
