#!/usr/bin/env python3
"""Material D05 worker for formal reasoning capabilities 121-124; no certification authority."""
from __future__ import annotations
import hashlib, json, os, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOMAIN=ROOT/"implementation/super1200/domains/D05.json"
REGISTRY=ROOT/"implementation/super1200/registry/capabilities.json"
MODULE=ROOT/"implementation/super1200/domains/D05_formal_reasoning.py"
TEST=ROOT/"implementation/super1200/tests/test_d05_formal_reasoning.py"
STATE=ROOT/"continuity/STATE.json"
EXECUTORS=ROOT/"continuity/EXECUTORS.json"
PRIOR_CERT=ROOT/"continuity/certification/D04_117_120.json"
OUT=ROOT/"continuity/runtime-evidence/D05"
REGRESSION_SUITES=[
 "implementation/super1200/tests/test_shared.py",
 "implementation/super1200/tests/test_d03_runtime.py",
 "implementation/super1200/tests/test_d04_runtime.py",
 "implementation/super1200/tests/test_d04_authorization_governance.py",
 "implementation/super1200/tests/test_d04_governance_controls.py",
 "implementation/super1200/tests/test_d04_trust_controls.py",
 "implementation/super1200/tests/test_d05_formal_reasoning.py",
]
TASKS=[
 (121,"FORMAL_REASONING_FABRIC","test_formal_reasoning_fabric_requires_explicit_assumptions_and_trusted_replay"),
 (122,"DEPENDENT_TYPE_THEORY_ENGINE","test_dependent_type_theory_checks_pi_lambda_application_and_dependent_codomain"),
 (123,"HIGHER_ORDER_TYPE_THEORY","test_higher_order_type_theory_validates_quantification_over_function_space"),
 (124,"HOTT_ENGINE","test_hott_identity_typechecks_refl_but_keeps_axioms_and_proof_claims_explicit"),
]
PRIOR_DEPENDENCIES={
 "module_sha256":("implementation/super1200/domains/D04_trust_controls.py","module_sha256"),
 "test_sha256":("implementation/super1200/tests/test_d04_trust_controls.py","test_sha256"),
 "governance_dependency_sha256":("implementation/super1200/domains/D04_governance_controls.py","governance_dependency_sha256"),
 "governance_test_dependency_sha256":("implementation/super1200/tests/test_d04_governance_controls.py","governance_test_dependency_sha256"),
 "authorization_dependency_sha256":("implementation/super1200/domains/D04_authorization_governance.py","authorization_dependency_sha256"),
 "authorization_test_dependency_sha256":("implementation/super1200/tests/test_d04_authorization_governance.py","authorization_test_dependency_sha256"),
 "runtime_dependency_sha256":("implementation/super1200/domains/D04_runtime.py","runtime_dependency_sha256"),
 "base_test_dependency_sha256":("implementation/super1200/tests/test_d04_runtime.py","base_test_dependency_sha256"),
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def git_blob_sha(path: Path) -> str:
    payload=path.read_bytes()
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii")+payload).hexdigest()

def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def main() -> int:
    required=[DOMAIN,REGISTRY,MODULE,TEST,STATE,EXECUTORS,PRIOR_CERT]
    for path in required:
        if not path.is_file():
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY MISSING={path.relative_to(ROOT)}")
    domain=json.loads(DOMAIN.read_text(encoding="utf-8"))
    registry=json.loads(REGISTRY.read_text(encoding="utf-8"))
    state=json.loads(STATE.read_text(encoding="utf-8"))
    executors=json.loads(EXECUTORS.read_text(encoding="utf-8"))
    cert=json.loads(PRIOR_CERT.read_text(encoding="utf-8"))
    if registry.get("count")!=1200 or len(registry.get("items",[]))!=1200:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_REGISTRY_COUNT_MISMATCH")
    if domain.get("domain_id")!="D05" or domain.get("range")!=[121,176] or domain.get("count")!=56:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_DOMAIN_CONTRACT_MISMATCH")
    prior_state=state.get("scoped_certifications",{}).get("D04:117-120",{})
    prior_scope_checks={
        "checkpoint":state.get("current_checkpoint")=="D04_117_120_MATERIALIZED",
        "g23":state.get("g23")=="PASS_FOR_SCOPE_D04_117_120",
        "g24":state.get("g24")=="PASS_FOR_SCOPE_D04_117_120",
        "certified_false":state.get("certified") is False,
        "global_not_certified":state.get("global_certification_status")=="NOT_CERTIFIED",
        "scoped_scope":state.get("scoped_certification",{}).get("scope")=="D04:117-120",
        "scoped_status":state.get("scoped_certification",{}).get("status")=="PASS",
        "scoped_global_false":state.get("scoped_certification",{}).get("global_certification_granted") is False,
        "scope_map_scope":prior_state.get("scope")=="D04:117-120",
        "scope_map_status":prior_state.get("status")=="PASS",
        "scope_map_global_false":prior_state.get("global_certification_granted") is False,
    }
    if not all(prior_scope_checks.values()):
        print("SUPER1200_TELEMETRY PRIOR_SCOPE_DIAGNOSTIC "+json.dumps({
            "checks":prior_scope_checks,
            "checkpoint":state.get("current_checkpoint"),
            "g23":state.get("g23"),"g24":state.get("g24"),
            "certified":state.get("certified"),
            "global_certification_status":state.get("global_certification_status"),
            "scoped_certification":state.get("scoped_certification"),
            "scope_map":prior_state,
            "state_sha256":sha(STATE)
        },sort_keys=True),flush=True)
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_SCOPE_GATES_NOT_PASSED")
    if (cert.get("result")!="PASS" or cert.get("scope")!="D04:117-120"
        or cert.get("g23")!="PASS" or cert.get("g24")!="PASS"
        or cert.get("certification_granted") is not True
        or cert.get("global_super1200_certified") is not False):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_CERTIFICATE_INVALID")
    # The prior scoped certificate must remain bound to its exact checked sources/dependencies.
    for field,(relative,cert_key) in PRIOR_DEPENDENCIES.items():
        if not (ROOT/relative).is_file() or cert.get(cert_key)!=sha(ROOT/relative):
            raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_CERT_SOURCE_DRIFT:"+field)
    by_id={x.get("capability_id"):x for x in registry["items"]}
    domain_by_id={x.get("capability_id"):x for x in domain.get("capabilities",[])}
    for cid,name,_ in TASKS:
        if cid not in by_id or by_id[cid].get("canonical_name")!=name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_REGISTRY_IDENTITY_MISMATCH_{cid}")
        if cid not in domain_by_id or domain_by_id[cid].get("canonical_name")!=name:
            raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_DOMAIN_IDENTITY_MISMATCH_{cid}")
    pairs={cid:(by_id[cid].get("implementation_state"),domain_by_id[cid].get("implementation_state")) for cid,_,_ in TASKS}
    executor="implementation/super1200/runtime/d05_material_worker_121_124.py"
    if all(a=="EVIDENCED" and b=="EVIDENCED" for a,b in pairs.values()):
        for cid,name,test_name in TASKS:
            evidence_path=OUT/f"capability-{cid:04d}.json"
            if not evidence_path.is_file():
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING_PRIOR_EVIDENCE_{cid}")
            ev=json.loads(evidence_path.read_text(encoding="utf-8"))
            recorded=ev.get("evidence_sha256");unsigned=dict(ev);unsigned.pop("evidence_sha256",None)
            if (ev.get("capability_id")!=cid or ev.get("canonical_name")!=name or ev.get("test_case")!=test_name
                or recorded!=canonical_hash(unsigned) or ev.get("status")!="PASS"
                or ev.get("module_sha256")!=sha(MODULE) or ev.get("test_sha256")!=sha(TEST)):
                raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_EVIDENCE_INTEGRITY_{cid}")
        print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_MATERIAL_WORKER_IDEMPOTENT_HOLD",
            "capabilities":[x[0] for x in TASKS],"certification_granted":False},sort_keys=True),flush=True)
        return 0
    if any(pair!=("DECLARED","QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_UNEXPECTED_OR_PARTIAL_CAPABILITY_STATE")
    authorization=state.get("next_tranche_authorization")
    expected_blob=git_blob_sha(PRIOR_CERT)
    if (not isinstance(authorization,dict)
        or authorization.get("checkpoint_predecessor")!="D04_117_120_MATERIALIZED"
        or authorization.get("executor")!=executor
        or authorization.get("capabilities")!=[121,122,123,124]
        or authorization.get("prior_scope_g23")!="PASS_FOR_SCOPE_D04_117_120"
        or authorization.get("prior_scope_g24")!="PASS_FOR_SCOPE_D04_117_120"
        or authorization.get("scoped_certificate")!="continuity/certification/D04_117_120.json"
        or authorization.get("prior_certificate_blob_sha")!=expected_blob
        or authorization.get("global_certification_granted") is not False
        or executors.get("executors",{}).get("D05")!=executor):
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_NEXT_TRANCHE_AUTHORIZATION_INVALID")
    run_id=os.environ.get("GITHUB_RUN_ID")
    if not run_id:
        raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_GITHUB_RUN_ID_REQUIRED")
    OUT.mkdir(parents=True,exist_ok=True)
    started=datetime.now(timezone.utc).isoformat()
    suite_results={}
    for relative in REGRESSION_SUITES:
        test_path=ROOT/relative
        if not test_path.is_file():
            raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING_REGRESSION_SUITE:"+relative)
        result=subprocess.run([sys.executable,"-B",str(test_path),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=300)
        output=result.stdout+"\n"+result.stderr
        if result.returncode!=0:
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_REGRESSION_SUITE_FAILED","suite":relative,
                "exit_code":result.returncode,"stdout":result.stdout[-10000:],"stderr":result.stderr[-10000:]},sort_keys=True),flush=True)
            return result.returncode or 1
        suite_results[relative]={"exit_code":result.returncode,
            "stdout_sha256":hashlib.sha256(result.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(result.stderr.encode()).hexdigest(),
            "test_names":[line.strip().split(" ")[0] for line in output.splitlines() if line.strip().startswith("test_")]}
    d05_output="\n".join(suite_results["implementation/super1200/tests/test_d05_formal_reasoning.py"].get("test_names",[]))
    for _,_,test_name in TASKS:
        if test_name not in d05_output:
            # The test runner may format verbose output differently; the specific invocations below remain authoritative.
            pass
    case_results={}
    for cid,name,test_name in TASKS:
        selected=subprocess.run([sys.executable,"-B",str(TEST),"-v",f"D05FormalReasoningTests.{test_name}"],
                                cwd=ROOT,text=True,capture_output=True,timeout=120)
        output=selected.stdout+"\n"+selected.stderr
        passed=(selected.returncode==0 and test_name in output and "Ran 1 test" in output
                and "OK" in output and "FAILED" not in output)
        case_results[cid]={"test_case":test_name,"exit_code":selected.returncode,
            "result":"PASS" if passed else "FAIL","stdout_sha256":hashlib.sha256(selected.stdout.encode()).hexdigest(),
            "stderr_sha256":hashlib.sha256(selected.stderr.encode()).hexdigest(),"test_name_seen":test_name in output,
            "single_test_run_confirmed":"Ran 1 test" in output,"unittest_ok_marker":"OK" in output and "FAILED" not in output}
        if not passed:
            print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_CAPABILITY_TEST_FAILED","capability_id":cid,
                "test_case":test_name,"stdout":selected.stdout[-10000:],"stderr":selected.stderr[-10000:]},sort_keys=True),flush=True)
            return selected.returncode or 1
    completed=datetime.now(timezone.utc).isoformat()
    module_hash,test_hash=sha(MODULE),sha(TEST)
    record_run={
        "schema":"SUPER1200_D05_MATERIAL_EVIDENCE/1",
        "checkpoint_predecessor":"D04_117_120_MATERIALIZED",
        "prior_scoped_certificate":"continuity/certification/D04_117_120.json",
        "prior_certificate_blob_sha":expected_blob,
        "module_sha256":module_hash,"test_sha256":test_hash,
        "regression_suites":suite_results,"capability_tests":case_results,
        "workflow_run_id":int(run_id),"completed_at_utc":completed,
        "g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23","global_certification_granted":False,
    }
    for cid,name,test_name in TASKS:
        ev={"schema":"SUPER1200_D05_MATERIAL_EVIDENCE/1","capability_id":cid,"canonical_name":name,
            "executor":executor,"implementation_artifact":"implementation/super1200/domains/D05_formal_reasoning.py",
            "test_artifact":"implementation/super1200/tests/test_d05_formal_reasoning.py","test_case":test_name,
            "status":"PASS","test_invocation":["python3","-B","test_d05_formal_reasoning.py","-v",f"D05FormalReasoningTests.{test_name}"],
            "selected_test_result":case_results[cid],"validated_at_utc":completed,"worker_started_at_utc":started,
            "github_actions_run_id":int(run_id),"module_sha256":module_hash,"test_sha256":test_hash,
            "regression_suites":{name:suite_results[name] for name in REGRESSION_SUITES},
            "prior_scoped_certificate":"continuity/certification/D04_117_120.json","prior_certificate_blob_sha":expected_blob,
            "proof_semantics":"TYPE_CHECKING_AND_OBLIGATION_FABRIC_ONLY",
            "theorem_claims_from_type_checking":False,
            "g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23","certification_granted":False}
        ev["evidence_sha256"]=canonical_hash(ev)
        (OUT/f"capability-{cid:04d}.json").write_text(json.dumps(ev,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        for item in (by_id[cid],domain_by_id[cid]):
            item["implementation_state"]="EVIDENCED"
            item["implementation_artifact"]="implementation/super1200/domains/D05_formal_reasoning.py"
            item["test_artifact"]="implementation/super1200/tests/test_d05_formal_reasoning.py"
            item["materialization"]="CODE+EXPLICIT_ASSUMPTIONS+DEPENDENT_TYPE_CHECKER+HOTT_IDENTITY_CHECK+PER_CAPABILITY_TEST+HASH_BOUND_EVIDENCE"
            item["theorem_claim_from_type_checking"]=False
    DOMAIN.write_text(json.dumps(domain,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    REGISTRY.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    url=f'{os.environ.get("GITHUB_SERVER_URL","https://github.com")}/{os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")}/actions/runs/{run_id}'
    state.update({
        "current_checkpoint":"D05_121_124_MATERIALIZED","next_point":"D05","status":"BLOCKED","blocked":True,
        "block_reason":"NEXT_D05_TRANCHE_EXECUTOR_NOT_REGISTERED","blocked_at":completed,
        "active_worker":False,"material_worker_ready":False,"certified":False,"global_certification_status":"NOT_CERTIFIED",
        "g23":"PENDING_FOR_SCOPE_D05_121_124","g24":"PENDING_G23",
        "diagnostic":"D05 capabilities 121-124 were materialized with typed Pi/Lambda/application checking, higher-order function-space type validation, explicit assumptions, HoTT identity-type checking, four mapped tests and seven regression suites. Type checking is not theorem certification. Continuation is held fail-closed until a reviewed executor for D05 125-128 is registered. Global SUPER1200 certification remains NOT_CERTIFIED; MetaOS remains deferred.",
        "recovery_note":"Register a reviewed D05 executor for capabilities 125-128 only after D05:121-124 obtains its own G23/G24 certificate. Bind all evidence to the exact source hashes and preserve the prior D04:117-120 scoped certificate; do not propagate scoped certification.",
        "next_tranche_authorization":None,
        "last_execution":{"workflow_run_id":int(run_id),"workflow_url":url,"status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE",
            "started_at_utc":started,"completed_at_utc":completed,"configured_runtime_hours":0.05,"material_capabilities":[121,122,123,124],
            "behavior_tests":"7_REGRESSION_SUITES_PASS;4_OF_4_CAPABILITY_TESTS_PASS","executor":executor,
            "g23":"PENDING","g24":"PENDING_G23","global_certification_status":"NOT_CERTIFIED"},
        "last_material_execution":{"executor":executor,"capabilities":[121,122,123,124],
            "tests":"7_REGRESSION_SUITES_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS",
            "test_case_results":[case_results[cid] for cid,_,_ in TASKS],"module_sha256":module_hash,"test_sha256":test_hash,
            "regression_suites":suite_results,"github_actions_run_id":int(run_id),"g23":"PENDING","g24":"PENDING",
            "certification_granted":False,"completed_at_utc":completed}
    })
    STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_MATERIAL_IMPLEMENTATION_PASS","capabilities":[121,122,123,124],
        "count":4,"module_sha256":module_hash,"test_sha256":test_hash,"suite_count":len(suite_results),
        "per_capability_tests":{cid:case_results[cid]["result"] for cid,_,_ in TASKS},
        "g23":"PENDING","g24":"PENDING_G23","certification_granted":False,
        "next_state":"D05_BLOCKED_NEXT_EXECUTOR_REQUIRED","github_actions_run_id":int(run_id)},sort_keys=True),flush=True)
    return 0

if __name__=="__main__":
    raise SystemExit(main())
