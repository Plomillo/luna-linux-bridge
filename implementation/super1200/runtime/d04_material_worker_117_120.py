#!/usr/bin/env python3
"""Material D04 worker for trust capabilities 117-120; no certification authority."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOMAIN=ROOT/"implementation/super1200/domains/D04.json"
REGISTRY=ROOT/"implementation/super1200/registry/capabilities.json"
BASE_MODULE=ROOT/"implementation/super1200/domains/D04_runtime.py"
BASE_TEST=ROOT/"implementation/super1200/tests/test_d04_runtime.py"
AUTH_MODULE=ROOT/"implementation/super1200/domains/D04_authorization_governance.py"
AUTH_TEST=ROOT/"implementation/super1200/tests/test_d04_authorization_governance.py"
GOV_MODULE=ROOT/"implementation/super1200/domains/D04_governance_controls.py"
GOV_TEST=ROOT/"implementation/super1200/tests/test_d04_governance_controls.py"
MODULE=ROOT/"implementation/super1200/domains/D04_trust_controls.py"
TEST=ROOT/"implementation/super1200/tests/test_d04_trust_controls.py"
STATE=ROOT/"continuity/STATE.json"
PRIOR_CERT=ROOT/"continuity/certification/D04_113_116.json"
OUT=ROOT/"continuity/runtime-evidence/D04"
TASKS=[
 (117,"ACTOR_INDEPENDENCE_VERIFIER","test_actor_independence_verifier_rejects_shared_identity_domain_credentials_path_and_permissions"),
 (118,"TRUST_ROOT_REGISTRY","test_trust_root_registry_binds_key_purpose_custody_validity_and_revocation"),
 (119,"TRUST_ROOT_ROTATION","test_trust_root_rotation_requires_cross_signatures_overlap_and_monotonic_history"),
 (120,"OFFLINE_TRUST_BUNDLE","test_offline_trust_bundle_binds_version_chain_expiry_hash_and_signature"),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def main() -> int:
    required=(DOMAIN,REGISTRY,BASE_MODULE,BASE_TEST,AUTH_MODULE,AUTH_TEST,GOV_MODULE,GOV_TEST,MODULE,TEST,STATE,PRIOR_CERT)
    for path in required:
        if not path.is_file():
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={path.relative_to(ROOT)}")
    domain=json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    state=json.loads(STATE.read_text(encoding="utf-8"))
    cert=json.loads(PRIOR_CERT.read_text(encoding="utf-8"))
    base_module_hash,base_test_hash=sha(BASE_MODULE),sha(BASE_TEST)
    auth_module_hash,auth_test_hash=sha(AUTH_MODULE),sha(AUTH_TEST)
    gov_module_hash,gov_test_hash=sha(GOV_MODULE),sha(GOV_TEST)
    module_hash,test_hash=sha(MODULE),sha(TEST)
    if registry.get("count")!=1200 or len(registry.get("items",[]))!=1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_COUNT_MISMATCH")
    if domain.get("domain_id")!="D04" or domain.get("range")!=[81,120]:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH")
    scoped=state.get("scoped_certification",{})
    scope_map=state.get("scoped_certifications",{})
    scope_map=scope_map if isinstance(scope_map,dict) else {}
    if (state.get("current_checkpoint")!="D04_113_116_MATERIALIZED"
        or state.get("g23")!="PASS_FOR_SCOPE_D04_113_116"
        or state.get("g24")!="PASS_FOR_SCOPE_D04_113_116"
        or state.get("certified") is not False
        or state.get("global_certification_status")!="NOT_CERTIFIED"
        or scoped.get("scope")!="D04:113-116"
        or scoped.get("status")!="PASS"
        or scoped.get("global_certification_granted") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPE_GATES_NOT_PASSED")
    prior_map=scope_map.get("D04:113-116",{})
    if (prior_map.get("scope")!="D04:113-116" or prior_map.get("status")!="PASS"
        or prior_map.get("global_certification_granted") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPE_NOT_IN_STATE")
    if (cert.get("result")!="PASS" or cert.get("scope")!="D04:113-116"
        or cert.get("g23")!="PASS" or cert.get("g24")!="PASS"
        or cert.get("certification_granted") is not True
        or cert.get("global_super1200_certified") is not False
        or cert.get("module_sha256")!=gov_module_hash
        or cert.get("test_sha256")!=gov_test_hash
        or cert.get("authorization_dependency_sha256")!=auth_module_hash
        or cert.get("authorization_test_dependency_sha256")!=auth_test_hash
        or cert.get("runtime_dependency_sha256")!=base_module_hash
        or cert.get("base_test_dependency_sha256")!=base_test_hash):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPED_CERTIFICATE_INVALID")
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
            path=OUT/f"capability-{cid:04d}.json"
            if not path.is_file():
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING_PRIOR_EVIDENCE ID={cid}")
            ev=json.loads(path.read_text(encoding="utf-8"))
            recorded=ev.get("evidence_sha256"); unsigned=dict(ev); unsigned.pop("evidence_sha256",None)
            if (ev.get("capability_id")!=cid or ev.get("canonical_name")!=name or ev.get("test_case")!=test_name
                or recorded!=canonical_hash(unsigned) or ev.get("status")!="PASS"
                or ev.get("module_sha256")!=module_hash or ev.get("test_sha256")!=test_hash
                or ev.get("governance_dependency_sha256")!=gov_module_hash
                or ev.get("governance_test_dependency_sha256")!=gov_test_hash):
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_EVIDENCE_INTEGRITY ID={cid}")
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_WORKER_IDEMPOTENT_HOLD",
            "capabilities":[x[0] for x in TASKS],"certification_granted":False},sort_keys=True),flush=True)
        return 0
    if any(pair != ("DECLARED","QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY UNEXPECTED_OR_PARTIAL_CAPABILITY_STATE")
    authorization=state.get("next_tranche_authorization")
    expected_executor="implementation/super1200/runtime/d04_material_worker_117_120.py"
    if (not isinstance(authorization,dict)
        or authorization.get("checkpoint_predecessor")!="D04_113_116_MATERIALIZED"
        or authorization.get("executor")!=expected_executor
        or authorization.get("capabilities")!=[117,118,119,120]
        or authorization.get("prior_scope_g23")!="PASS_FOR_SCOPE_D04_113_116"
        or authorization.get("prior_scope_g24")!="PASS_FOR_SCOPE_D04_113_116"
        or authorization.get("scoped_certificate")!="continuity/certification/D04_113_116.json"
        or authorization.get("global_certification_granted") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_NEXT_TRANCHE_AUTHORIZATION_INVALID")
    run_id=os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY GITHUB_RUN_ID_REQUIRED")
    OUT.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    suites=[]
    for test_path in (BASE_TEST,AUTH_TEST,GOV_TEST,TEST):
        result=subprocess.run([sys.executable,"-B",str(test_path),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=300)
        output=result.stdout+"\n"+result.stderr
        if result.returncode:
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_TRUST_REGRESSION_SUITE_FAILED",
                "test_artifact":str(test_path.relative_to(ROOT)),"exit_code":result.returncode,
                "stdout":result.stdout[-12000:],"stderr":result.stderr[-12000:]},sort_keys=True),flush=True)
            return result.returncode or 1
        suites.append({"test_artifact":str(test_path.relative_to(ROOT)),"exit_code":result.returncode,
            "stdout_sha256":hashlib.sha256(result.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(result.stderr.encode()).hexdigest(),"output":output})
    trust_output=suites[-1]["output"]
    if any(test_name not in trust_output for _,_,test_name in TASKS):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_REQUIRED_TEST_CASE_NOT_IN_FULL_SUITE")
    case_results={}
    for cid,name,test_name in TASKS:
        selected=subprocess.run([sys.executable,"-B",str(TEST),"-v",f"D04TrustControlsTests.{test_name}"],
            cwd=ROOT,text=True,capture_output=True,timeout=120)
        output=selected.stdout+"\n"+selected.stderr
        passed=(selected.returncode==0 and test_name in output and "Ran 1 test" in output
                and "OK" in output and "FAILED" not in output)
        case_results[cid]={"test_case":test_name,"exit_code":selected.returncode,
            "result":"PASS" if passed else "FAIL",
            "stdout_sha256":hashlib.sha256(selected.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(selected.stderr.encode()).hexdigest(),
            "test_name_seen":test_name in output,"single_test_run_confirmed":"Ran 1 test" in output,
            "unittest_ok_marker":"OK" in output and "FAILED" not in output}
        if not passed:
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_TRUST_CAPABILITY_TEST_FAILED",
                "capability_id":cid,"test_case":test_name,"stdout":selected.stdout[-12000:],
                "stderr":selected.stderr[-12000:]},sort_keys=True),flush=True)
            return selected.returncode or 1
    now=datetime.now(timezone.utc).isoformat()
    suite_hashes={}
    for suite in suites:
        stem=Path(suite["test_artifact"]).stem.replace("test_","")
        suite_hashes[stem+"_suite_exit_code"]=suite["exit_code"]
        suite_hashes[stem+"_suite_stdout_sha256"]=suite["stdout_sha256"]
        suite_hashes[stem+"_suite_stderr_sha256"]=suite["stderr_sha256"]
    for cid,name,test_name in TASKS:
        ev={"schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1","capability_id":cid,"canonical_name":name,
            "executor":expected_executor,"implementation_artifact":"implementation/super1200/domains/D04_trust_controls.py",
            "test_artifact":"implementation/super1200/tests/test_d04_trust_controls.py",
            "test_case":test_name,"status":"PASS",
            "test_invocation":["python","-B","test_d04_trust_controls.py","-v",f"D04TrustControlsTests.{test_name}"],
            "selected_test_result":case_results[cid],"validated_at_utc":now,"worker_started_at_utc":started,
            "github_actions_run_id":run_id,"module_sha256":module_hash,"test_sha256":test_hash,
            "governance_dependency_sha256":gov_module_hash,"governance_test_dependency_sha256":gov_test_hash,
            "authorization_dependency_sha256":auth_module_hash,"authorization_test_dependency_sha256":auth_test_hash,
            "runtime_dependency_sha256":base_module_hash,"base_test_dependency_sha256":base_test_hash,
            "regression_suites":suite_hashes,"prior_scope_certificate":"continuity/certification/D04_113_116.json",
            "g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23","certification_granted":False}
        ev["evidence_sha256"]=canonical_hash(ev)
        (OUT/f"capability-{cid:04d}.json").write_text(json.dumps(ev,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        for item in (by_id[cid],domain_by_id[cid]):
            item["implementation_state"]="EVIDENCED"
            item["implementation_artifact"]="implementation/super1200/domains/D04_trust_controls.py"
            item["test_artifact"]="implementation/super1200/tests/test_d04_trust_controls.py"
            item["materialization"]="CODE+TRUST_POLICY+PER_CAPABILITY_TEST+REGRESSION_SUITES+HASH_BOUND_EVIDENCE"
    DOMAIN.write_text(json.dumps(domain,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    completed=datetime.now(timezone.utc).isoformat()
    server=os.environ.get("GITHUB_SERVER_URL","https://github.com")
    repo=os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")
    run_url=f"{server}/{repo}/actions/runs/{run_id}"
    state.update({
        "current_checkpoint":"D04_117_120_MATERIALIZED",
        "next_point":"D05",
        "status":"BLOCKED","blocked":True,"block_reason":"NEXT_DOMAIN_D05_EXECUTOR_NOT_REGISTERED",
        "blocked_at":completed,"active_worker":False,"material_worker_ready":False,
        "certified":False,"global_certification_status":"NOT_CERTIFIED",
        "g23":"PENDING_FOR_SCOPE_D04_117_120","g24":"PENDING_G23",
        "diagnostic":"D04 capabilities 117-120 were materialized with independent mapped tests and four regression suites. D04 covers IDs 81-120 and is now materialized through its final four capabilities; continuation is held fail-closed because D05 has no registered material executor. The D04:113-116 scoped certificate does not propagate. Global SUPER1200 certification remains NOT_CERTIFIED; MetaOS remains deferred.",
        "recovery_note":"Register and review a task-specific executor for the next declared domain D05 only after D04:117-120 obtains G23/G24. Bind D05 to its own domain contract and test evidence; do not propagate any scoped certification.",
        "next_tranche_authorization":None,
        "last_execution":{"workflow_run_id":int(run_id),"workflow_url":run_url,"status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "started_at_utc":started,"completed_at_utc":completed,"configured_runtime_hours":0.05,
            "material_capabilities":[117,118,119,120],
            "behavior_tests":"BASE_D04_SUITE_PASS;AUTHORIZATION_GOVERNANCE_SUITE_PASS;GOVERNANCE_CONTROLS_SUITE_PASS;TRUST_CONTROLS_SUITE_PASS;4_OF_4_CAPABILITY_TESTS_PASS",
            "executor":expected_executor,"g23":"PENDING","g24":"PENDING_G23","global_certification_status":"NOT_CERTIFIED"},
        "last_material_execution":{"executor":expected_executor,"capabilities":[117,118,119,120],
            "tests":"4_REGRESSION_SUITES_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS",
            "test_case_results":[case_results[cid] for cid,_,_ in TASKS],
            "module_sha256":module_hash,"test_sha256":test_hash,
            "governance_dependency_sha256":gov_module_hash,"governance_test_dependency_sha256":gov_test_hash,
            "authorization_dependency_sha256":auth_module_hash,"authorization_test_dependency_sha256":auth_test_hash,
            "runtime_dependency_sha256":base_module_hash,"base_test_dependency_sha256":base_test_hash,
            "github_actions_run_id":int(run_id),"g23":"PENDING","g24":"PENDING",
            "certification_granted":False,"completed_at_utc":completed}
    })
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_TRUST_MATERIAL_IMPLEMENTATION_PASS",
        "capabilities":[117,118,119,120],"count":4,"module_sha256":module_hash,"test_sha256":test_hash,
        "suite_count":len(suites),"per_capability_tests":{cid:case_results[cid]["result"] for cid,_,_ in TASKS},
        "g23":"PENDING","g24":"PENDING_G23","certification_granted":False,
        "next_state":"D05_BLOCKED_NEXT_DOMAIN_EXECUTOR_REQUIRED","github_actions_run_id":int(run_id)},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
