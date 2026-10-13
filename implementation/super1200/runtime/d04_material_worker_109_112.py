#!/usr/bin/env python3
"""Material D04 worker for capability IDs 109-112; no certification authority."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOMAIN=ROOT/"implementation/super1200/domains/D04.json"
REGISTRY=ROOT/"implementation/super1200/registry/capabilities.json"
BASE_MODULE=ROOT/"implementation/super1200/domains/D04_runtime.py"
BASE_TEST=ROOT/"implementation/super1200/tests/test_d04_runtime.py"
MODULE=ROOT/"implementation/super1200/domains/D04_authorization_governance.py"
TEST=ROOT/"implementation/super1200/tests/test_d04_authorization_governance.py"
STATE=ROOT/"continuity/STATE.json"
PRIOR_CERT=ROOT/"continuity/certification/D04_105_108.json"
OUT=ROOT/"continuity/runtime-evidence/D04"
TASKS=[
 (109,"AUTHORIZATION_PROOF","test_authorization_proof_binds_request_signature_time_scope_and_revocation"),
 (110,"CAPABILITY_LEASES","test_capability_lease_enforces_actor_action_resource_time_revocation_and_consumption"),
 (111,"LEAST_PRIVILEGE_ENGINE","test_least_privilege_plan_selects_only_goal_ancestors_and_rejects_bad_dags"),
 (112,"TIME_BOUND_AUTHORITY","test_time_bound_authority_requires_verified_clock_exact_scope_and_current_interval"),
]

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

def main() -> int:
    required=(DOMAIN,REGISTRY,BASE_MODULE,BASE_TEST,MODULE,TEST,STATE,PRIOR_CERT)
    for path in required:
        if not path.is_file():
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={path.relative_to(ROOT)}")
    domain=json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    state=json.loads(STATE.read_text(encoding="utf-8"))
    cert=json.loads(PRIOR_CERT.read_text(encoding="utf-8"))
    base_module_hash,base_test_hash=sha(BASE_MODULE),sha(BASE_TEST)
    module_hash,test_hash=sha(MODULE),sha(TEST)
    if registry.get("count")!=1200 or len(registry.get("items",[]))!=1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY REGISTRY_COUNT_MISMATCH")
    if domain.get("domain_id")!="D04" or domain.get("range")!=[81,120]:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY DOMAIN_IDENTITY_MISMATCH")
    scoped=state.get("scoped_certification",{})
    prior_map=state.get("scoped_certifications",{})
    prior_map=prior_map if isinstance(prior_map,dict) else {}
    if (state.get("current_checkpoint")!="D04_105_108_MATERIALIZED"
        or state.get("g23")!="PASS_FOR_SCOPE_D04_105_108"
        or state.get("g24")!="PASS_FOR_SCOPE_D04_105_108"
        or state.get("certified") is not False
        or state.get("global_certification_status")!="NOT_CERTIFIED"
        or scoped.get("scope")!="D04:105-108"
        or scoped.get("status")!="PASS"
        or scoped.get("global_certification_granted") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPE_GATES_NOT_PASSED")
    if (cert.get("result")!="PASS" or cert.get("scope")!="D04:105-108"
        or cert.get("g23")!="PASS" or cert.get("g24")!="PASS"
        or cert.get("certification_granted") is not True
        or cert.get("global_super1200_certified") is not False
        or cert.get("module_sha256")!=base_module_hash
        or cert.get("test_sha256")!=base_test_hash):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPED_CERTIFICATE_INVALID")
    recorded_prior=prior_map.get("D04:105-108",{})
    if (recorded_prior.get("scope")!="D04:105-108" or recorded_prior.get("status")!="PASS"
        or recorded_prior.get("global_certification_granted") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_SCOPE_NOT_IN_STATE")
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
            if not p.is_file():
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING_PRIOR_EVIDENCE ID={cid}")
            ev=json.loads(p.read_text(encoding="utf-8")); recorded=ev.get("evidence_sha256")
            unsigned=dict(ev); unsigned.pop("evidence_sha256",None)
            if (ev.get("capability_id")!=cid or ev.get("canonical_name")!=name or ev.get("test_case")!=test_name
                or recorded!=canonical_hash(unsigned) or ev.get("status")!="PASS"
                or ev.get("module_sha256")!=module_hash or ev.get("test_sha256")!=test_hash):
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY PRIOR_EVIDENCE_INTEGRITY ID={cid}")
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_WORKER_IDEMPOTENT_HOLD",
            "capabilities":[x[0] for x in TASKS],"certification_granted":False},sort_keys=True),flush=True)
        return 0
    if any(pair != ("DECLARED","QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY UNEXPECTED_OR_PARTIAL_CAPABILITY_STATE")
    run_id=os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY GITHUB_RUN_ID_REQUIRED")
    OUT.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    base_suite=subprocess.run([sys.executable,"-B",str(BASE_TEST),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=240)
    auth_suite=subprocess.run([sys.executable,"-B",str(TEST),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=240)
    auth_output=auth_suite.stdout+"\n"+auth_suite.stderr
    if base_suite.returncode or auth_suite.returncode or any(task[2] not in auth_output for task in TASKS):
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_TESTS_FAILED_OR_INCOMPLETE",
            "base_exit_code":base_suite.returncode,"authorization_exit_code":auth_suite.returncode,
            "base_stdout":base_suite.stdout[-12000:],"base_stderr":base_suite.stderr[-12000:],
            "authorization_stdout":auth_suite.stdout[-16000:],"authorization_stderr":auth_suite.stderr[-16000:]},sort_keys=True),flush=True)
        return base_suite.returncode or auth_suite.returncode or 1
    case_results={}
    for cid,name,test_name in TASKS:
        selected=subprocess.run([sys.executable,"-B",str(TEST),"-v",f"D04AuthorizationGovernanceTests.{test_name}"],
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
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_CAPABILITY_TEST_FAILED","capability_id":cid,
                "test_case":test_name,"stdout":selected.stdout[-12000:],"stderr":selected.stderr[-12000:]},sort_keys=True),flush=True)
            return selected.returncode or 1
    now=datetime.now(timezone.utc).isoformat()
    suite_hashes={
        "base_suite_stdout_sha256":hashlib.sha256(base_suite.stdout.encode()).hexdigest(),
        "base_suite_stderr_sha256":hashlib.sha256(base_suite.stderr.encode()).hexdigest(),
        "authorization_suite_stdout_sha256":hashlib.sha256(auth_suite.stdout.encode()).hexdigest(),
        "authorization_suite_stderr_sha256":hashlib.sha256(auth_suite.stderr.encode()).hexdigest(),
    }
    for cid,name,test_name in TASKS:
        ev={"schema":"SUPER1200_D04_MATERIAL_EVIDENCE/1","capability_id":cid,"canonical_name":name,
            "executor":"implementation/super1200/runtime/d04_material_worker_109_112.py",
            "implementation_artifact":"implementation/super1200/domains/D04_authorization_governance.py",
            "test_artifact":"implementation/super1200/tests/test_d04_authorization_governance.py",
            "test_case":test_name,"status":"PASS",
            "test_invocation":["python","-B","test_d04_authorization_governance.py","-v",f"D04AuthorizationGovernanceTests.{test_name}"],
            "selected_test_result":case_results[cid],"validated_at_utc":now,"worker_started_at_utc":started,
            "github_actions_run_id":run_id,"module_sha256":module_hash,"test_sha256":test_hash,
            "runtime_dependency_sha256":base_module_hash,"base_test_dependency_sha256":base_test_hash,
            "base_suite_exit_code":base_suite.returncode,"authorization_suite_exit_code":auth_suite.returncode,
            **suite_hashes,"prior_scope_certificate":"continuity/certification/D04_105_108.json",
            "g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23","certification_granted":False}
        ev["evidence_sha256"]=canonical_hash(ev)
        (OUT/f"capability-{cid:04d}.json").write_text(json.dumps(ev,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        for item in (by_id[cid],domain_by_id[cid]):
            item["implementation_state"]="EVIDENCED"
            item["implementation_artifact"]="implementation/super1200/domains/D04_authorization_governance.py"
            item["test_artifact"]="implementation/super1200/tests/test_d04_authorization_governance.py"
            item["materialization"]="AUTHORIZATION_CODE+PER_CAPABILITY_TEST+BASE_REGRESSION+HASH_BOUND_EVIDENCE"
    DOMAIN.write_text(json.dumps(domain,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    now=datetime.now(timezone.utc).isoformat()
    server=os.environ.get("GITHUB_SERVER_URL","https://github.com")
    repo=os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")
    url=f"{server}/{repo}/actions/runs/{run_id}"
    state.update({"current_checkpoint":"D04_109_112_MATERIALIZED","next_point":"D04","status":"BLOCKED","blocked":True,
        "block_reason":"NEXT_D04_TRANCHE_EXECUTOR_NOT_REGISTERED","blocked_at":now,"active_worker":False,"material_worker_ready":False,
        "certified":False,"global_certification_status":"NOT_CERTIFIED","g23":"PENDING_FOR_SCOPE_D04_109_112","g24":"PENDING_G23",
        "diagnostic":"D04 capabilities 109-112 were materially implemented in a separate authorization-governance module with per-capability tests and hash-bound evidence. Continuation is held fail-closed pending scoped G23/G24 for 109-112 and a reviewed executor for 113-116. Earlier D04 scope certificates remain bound to their exact source hashes. MetaOS remains deferred.",
        "recovery_note":"Run current-source G23/G24 for D04 109-112. Preserve the prior scoped certificate and do not propagate it. Register and review a task-specific executor for D04 113-116 only after the current scope is independently validated and certified.",
        "last_execution":{"workflow_run_id":int(run_id),"workflow_url":url,"status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "started_at_utc":started,"completed_at_utc":now,"configured_runtime_hours":0.05,"material_capabilities":[109,110,111,112],
            "behavior_tests":"BASE_D04_SUITE_PASS;AUTHORIZATION_GOVERNANCE_SUITE_PASS;4_OF_4_CAPABILITY_TESTS_PASS",
            "executor":"implementation/super1200/runtime/d04_material_worker_109_112.py",
            "g23":"PENDING","g24":"PENDING_G23","global_certification_status":"NOT_CERTIFIED"},
        "last_material_execution":{"executor":"implementation/super1200/runtime/d04_material_worker_109_112.py","capabilities":[109,110,111,112],
            "tests":"BASE_D04_SUITE_PASS;AUTHORIZATION_GOVERNANCE_SUITE_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS",
            "test_case_results":[case_results[cid] for cid,_,_ in TASKS],
            "module_sha256":module_hash,"test_sha256":test_hash,"runtime_dependency_sha256":base_module_hash,
            "base_test_dependency_sha256":base_test_hash,"github_actions_run_id":run_id,"g23":"PENDING","g24":"PENDING",
            "certification_granted":False,"completed_at_utc":now}})
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUPER1200_TELEMETRY "+json.dumps({"event":"D04_MATERIAL_IMPLEMENTATION_PASS","capabilities":[109,110,111,112],
        "count":4,"module_sha256":module_hash,"test_sha256":test_hash,"runtime_dependency_sha256":base_module_hash,
        "base_test_dependency_sha256":base_test_hash,"suite_exit_codes":{"base":base_suite.returncode,"authorization":auth_suite.returncode},
        "per_capability_tests":{cid:case_results[cid]["result"] for cid,_,_ in TASKS},"g23":"PENDING","g24":"PENDING_G23",
        "certification_granted":False,"next_state":"BLOCKED_NEXT_EXECUTOR_REQUIRED","github_actions_run_id":run_id},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
