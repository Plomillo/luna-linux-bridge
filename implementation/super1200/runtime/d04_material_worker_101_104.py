#!/usr/bin/env python3
"""Material D04 worker for capability IDs 101-104; no certification authority."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOMAIN=ROOT/"implementation/super1200/domains/D04.json"
REGISTRY=ROOT/"implementation/super1200/registry/capabilities.json"
MODULE=ROOT/"implementation/super1200/domains/D04_runtime.py"
TEST=ROOT/"implementation/super1200/tests/test_d04_runtime.py"
STATE=ROOT/"continuity/STATE.json"
PRIOR_CERT=ROOT/"continuity/certification/D04_97_100.json"
OUT=ROOT/"continuity/runtime-evidence/D04"
TASKS=[
 (101,"POLICY_AS_CODE","test_policy_as_code_binds_versioned_policy_input_and_audit_receipt"),
 (102,"OPA_REGO_PROVIDER","test_opa_rego_provider_pins_version_bundle_and_sandbox"),
 (103,"CUE_SCHEMA_PROVIDER","test_cue_provider_binds_schema_input_and_deterministic_export"),
 (104,"JSON_SCHEMA_PROVIDER","test_json_schema_provider_pins_dialect_and_rejects_unknown_fields"),
]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    for p in (DOMAIN,REGISTRY,MODULE,TEST,STATE,PRIOR_CERT):
        if not p.is_file(): raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={p.relative_to(ROOT)}")
    domain=json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    state=json.loads(STATE.read_text(encoding="utf-8"))
    cert=json.loads(PRIOR_CERT.read_text(encoding="utf-8"))
    module_hash,test_hash=sha(MODULE),sha(TEST)
    if registry.get("count")!=1200 or len(registry.get("items",[]))!=1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_COUNT_MISMATCH")
    if domain.get("domain_id")!="D04" or domain.get("range")!=[81,120]:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH")
    if (state.get("current_checkpoint")!="D04_97_100_MATERIALIZED"
        or state.get("g23")!="PASS_FOR_SCOPE_D04_97_100"
        or state.get("g24")!="PASS_FOR_SCOPE_D04_97_100"
        or state.get("certified") is not False
        or state.get("global_certification_status")!="NOT_CERTIFIED"):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPE_GATES_NOT_PASSED")
    if (cert.get("result")!="PASS" or cert.get("scope")!="D04:97-100"
        or cert.get("certification_granted") is not True
        or cert.get("global_super1200_certified") is not False
        or cert.get("module_sha256")!=module_hash or cert.get("test_sha256")!=test_hash):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPED_CERTIFICATE_STALE_OR_INVALID")
    by_id={x.get("capability_id"):x for x in registry["items"]}
    domain_by_id={x.get("capability_id"):x for x in domain.get("capabilities",[])}
    for cid,name,_ in TASKS:
        if cid not in by_id or by_id[cid].get("canonical_name")!=name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_IDENTITY_MISMATCH ID={cid}")
        if cid not in domain_by_id or domain_by_id[cid].get("canonical_name")!=name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH ID={cid}")
    pairs={cid:(by_id[cid].get("implementation_state"),domain_by_id[cid].get("implementation_state")) for cid,_,_ in TASKS}
    if all(a=="EVIDENCED" and b=="EVIDENCED" for a,b in pairs.values()):
        for cid,name,test_name in TASKS:
            p=OUT/f"capability-{cid:04d}.json"
            if not p.is_file(): raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING_PRIOR_EVIDENCE ID={cid}")
            ev=json.loads(p.read_text(encoding="utf-8")); recorded=ev.get("evidence_sha256"); unsigned=dict(ev); unsigned.pop("evidence_sha256",None)
            computed=hashlib.sha256(json.dumps(unsigned,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
            if ev.get("capability_id")!=cid or ev.get("canonical_name")!=name or ev.get("test_case")!=test_name or recorded!=computed or ev.get("status")!="PASS":
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_EVIDENCE_INTEGRITY ID={cid}")
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_WORKER_IDEMPOTENT_HOLD","capabilities":[x[0] for x in TASKS],"certification_granted":False},sort_keys=True),flush=True)
        return 0
    if any(pair != ("DECLARED","QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY UNEXPECTED_OR_PARTIAL_CAPABILITY_STATE")
    if not os.environ.get("GITHUB_RUN_ID"):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY GITHUB_RUN_ID_REQUIRED")
    OUT.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    suite=subprocess.run([sys.executable,"-B",str(TEST),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=240)
    suite_output=suite.stdout+"\n"+suite.stderr
    if suite.returncode or any(test_name not in suite_output for _,_,test_name in TASKS):
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_TESTS_FAILED_OR_INCOMPLETE","exit_code":suite.returncode,"stdout":suite.stdout[-12000:],"stderr":suite.stderr[-12000:]},sort_keys=True),flush=True)
        return suite.returncode or 1
    case_results={}
    for cid,name,test_name in TASKS:
        selected=subprocess.run([sys.executable,"-B",str(TEST),"-v",f"D04RuntimeTests.{test_name}"],cwd=ROOT,text=True,capture_output=True,timeout=120)
        output=selected.stdout+"\n"+selected.stderr
        passed=selected.returncode==0 and test_name in output and "Ran 1 test" in output and "OK" in output and "FAILED" not in output
        case_results[cid]={"test_case":test_name,"exit_code":selected.returncode,"result":"PASS" if passed else "FAIL",
            "stdout_sha256":hashlib.sha256(selected.stdout.encode()).hexdigest(),"stderr_sha256":hashlib.sha256(selected.stderr.encode()).hexdigest(),
            "single_test_run_confirmed":"Ran 1 test" in output,"unittest_ok_marker":"OK" in output and "FAILED" not in output}
        if not passed:
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_CAPABILITY_TEST_FAILED","capability_id":cid,"test_case":test_name,"stdout":selected.stdout[-12000:],"stderr":selected.stderr[-12000:]},sort_keys=True),flush=True)
            return selected.returncode or 1
    suite_out_hash=hashlib.sha256(suite.stdout.encode()).hexdigest()
    suite_err_hash=hashlib.sha256(suite.stderr.encode()).hexdigest()
    now=datetime.now(timezone.utc).isoformat()
    for cid,name,test_name in TASKS:
        ev={"schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1","capability_id":cid,"canonical_name":name,
            "executor":"implementation/super1200/runtime/d04_material_worker_101_104.py",
            "implementation_artifact":"implementation/super1200/domains/D04_runtime.py",
            "test_artifact":"implementation/super1200/tests/test_d04_runtime.py","test_case":test_name,"status":"PASS",
            "test_invocation":["python","-B","test_d04_runtime.py","-v",f"D04RuntimeTests.{test_name}"],
            "selected_test_result":case_results[cid],"validated_at_utc":now,"worker_started_at_utc":started,
            "github_actions_run_id":os.environ["GITHUB_RUN_ID"],"module_sha256":module_hash,"test_sha256":test_hash,
            "suite_stdout_sha256":suite_out_hash,"suite_stderr_sha256":suite_err_hash,"suite_exit_code":suite.returncode,
            "prior_scope_certificate":"continuity/certification/D04_97_100.json",
            "g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23","certification_granted":False}
        ev["evidence_sha256"]=hashlib.sha256(json.dumps(ev,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()
        (OUT/f"capability-{cid:04d}.json").write_text(json.dumps(ev,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        for item in (by_id[cid],domain_by_id[cid]):
            item["implementation_state"]="EVIDENCED"
            item["implementation_artifact"]="implementation/super1200/domains/D04_runtime.py"
            item["test_artifact"]="implementation/super1200/tests/test_d04_runtime.py"
            item["materialization"]="SCHEMA+CODE+PER_CAPABILITY_TEST+FULL_SUITE+HASH_BOUND_EVIDENCE"
    DOMAIN.write_text(json.dumps(domain,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    now=datetime.now(timezone.utc).isoformat()
    run_id=os.environ["GITHUB_RUN_ID"]; server=os.environ.get("GITHUB_SERVER_URL","https://github.com"); repo=os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")
    url=f"{server}/{repo}/actions/runs/{run_id}"
    state.update({"current_checkpoint":"D04_101_104_MATERIALIZED","next_point":"D04","status":"BLOCKED","blocked":True,
        "block_reason":"NEXT_D04_TRANCHE_EXECUTOR_NOT_REGISTERED","blocked_at":now,"active_worker":False,"material_worker_ready":False,
        "certified":False,"global_certification_status":"NOT_CERTIFIED","g23":"PENDING_FOR_SCOPE_D04_101_104","g24":"PENDING_G23",
        "diagnostic":"D04 capabilities 101-104 materially implemented with version-bound policy decisions, provider pinning, strict schema checks and hash-bound evidence. Continuation held fail-closed because no reviewed executor for the next D04 tranche is registered. G23/G24 remain pending; prior scoped certification does not propagate.",
        "recovery_note":"Register and review a task-specific executor for the next pending D04 tranche. Do not propagate scoped certification. MetaOS remains deferred.",
        "last_execution":{"workflow_run_id":int(run_id),"workflow_url":url,"status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "started_at_utc":started,"completed_at_utc":now,"configured_runtime_hours":0.05,"material_capabilities":[101,102,103,104],
            "behavior_tests":"FULL_SUITE_PASS;4_OF_4_CAPABILITY_TESTS_PASS","executor":"implementation/super1200/runtime/d04_material_worker_101_104.py",
            "g23":"PENDING","g24":"PENDING_G23","global_certification_status":"NOT_CERTIFIED"},
        "last_material_execution":{"executor":"implementation/super1200/runtime/d04_material_worker_101_104.py","capabilities":[101,102,103,104],
            "tests":"FULL_SUITE_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS","test_case_results":[case_results[cid] for cid,_,_ in TASKS],
            "module_sha256":module_hash,"test_sha256":test_hash,"github_actions_run_id":run_id,"g23":"PENDING","g24":"PENDING",
            "certification_granted":False,"completed_at_utc":now}})
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_IMPLEMENTATION_PASS","capabilities":[101,102,103,104],
        "count":4,"module_sha256":module_hash,"test_sha256":test_hash,"suite_exit_code":suite.returncode,
        "per_capability_tests":{cid:case_results[cid]["result"] for cid,_,_ in TASKS},"g23":"PENDING","g24":"PENDING_G23",
        "certification_granted":False,"next_state":"BLOCKED_NEXT_EXECUTOR_REQUIRED","github_actions_run_id":run_id},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
