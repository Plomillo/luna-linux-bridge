#!/usr/bin/env python3
"""Material D05 worker for formal-foundations capabilities 129-132; no certification authority."""
from __future__ import annotations
import hashlib,json,os,subprocess,sys
from datetime import datetime,timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[3]
DOMAIN=ROOT/"implementation/super1200/domains/D05.json"
REGISTRY=ROOT/"implementation/super1200/registry/capabilities.json"
BASE_MODULE=ROOT/"implementation/super1200/domains/D05_formal_foundations.py"
BASE_TEST=ROOT/"implementation/super1200/tests/test_d05_formal_foundations.py"
MODULE=ROOT/"implementation/super1200/domains/D05_proof_assurance.py"
TEST=ROOT/"implementation/super1200/tests/test_d05_proof_assurance.py"
STATE=ROOT/"continuity/STATE.json"
EXECUTORS=ROOT/"continuity/EXECUTORS.json"
PRIOR_CERT=ROOT/"continuity/certification/D05_125_128.json"
OUT=ROOT/"continuity/runtime-evidence/D05"
REGRESSION_SUITES=[
 "implementation/super1200/tests/test_shared.py",
 "implementation/super1200/tests/test_d03_runtime.py",
 "implementation/super1200/tests/test_d04_runtime.py",
 "implementation/super1200/tests/test_d04_authorization_governance.py",
 "implementation/super1200/tests/test_d04_governance_controls.py",
 "implementation/super1200/tests/test_d04_trust_controls.py",
 "implementation/super1200/tests/test_d05_formal_reasoning.py",
 "implementation/super1200/tests/test_d05_formal_foundations.py",
 "implementation/super1200/tests/test_d05_proof_assurance.py",
]
TASKS=[
 (129,"PROOF_CHECKER","test_checker_binding_requires_independent_checker_and_untrusted_producer"),
 (130,"PROOF_ARTIFACT_STORE","test_proof_artifact_descriptor_is_hash_bound_and_does_not_claim_persistence"),
 (131,"PROOF_DEPENDENCY_GRAPH","test_proof_dependency_graph_rejects_cycles_and_computes_reverse_invalidation"),
 (132,"PROOF_REPLAY","test_proof_replay_requires_trusted_exact_callback_and_never_grants_global_certification"),
]

def sha(path:Path)->str:
 return hashlib.sha256(path.read_bytes()).hexdigest()
def blob_sha(path:Path)->str:
 b=path.read_bytes()
 return hashlib.sha1(f"blob {len(b)}\0".encode("ascii")+b).hexdigest()
def canonical_hash(value)->str:
 return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()
def load(path): return json.loads(path.read_text(encoding="utf-8"))

def main()->int:
 required=[DOMAIN,REGISTRY,BASE_MODULE,BASE_TEST,MODULE,TEST,STATE,EXECUTORS,PRIOR_CERT]
 for p in required:
  if not p.is_file(): raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING:"+str(p.relative_to(ROOT)))
 domain,registry,state,executors,cert=map(load,[DOMAIN,REGISTRY,STATE,EXECUTORS,PRIOR_CERT])
 if registry.get("count")!=1200 or len(registry.get("items",[]))!=1200:
  raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_REGISTRY_COUNT")
 if domain.get("domain_id")!="D05" or domain.get("range")!=[121,176] or domain.get("count")!=56:
  raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_DOMAIN_CONTRACT")
 scope=state.get("scoped_certifications",{}).get("D05:125-128",{})
 checks={
  "checkpoint":state.get("current_checkpoint")=="D05_125_128_MATERIALIZED",
  "g23":state.get("g23")=="PASS_FOR_SCOPE_D05_125_128",
  "g24":state.get("g24")=="PASS_FOR_SCOPE_D05_125_128",
  "global_not_certified":state.get("certified") is False and state.get("global_certification_status")=="NOT_CERTIFIED",
  "prior_scope":scope.get("scope")=="D05:125-128" and scope.get("status")=="PASS" and scope.get("global_certification_granted") is False,
  "certificate":cert.get("result")=="PASS" and cert.get("scope")=="D05:125-128" and cert.get("g23")=="PASS" and cert.get("g24")=="PASS" and cert.get("certification_granted") is True and cert.get("global_super1200_certified") is False,
  "prior_sources":cert.get("module_sha256")==sha(BASE_MODULE) and cert.get("test_sha256")==sha(BASE_TEST),
 }
 if not all(checks.values()):
  print("SUPER1200_TELEMETRY PRIOR_SCOPE_DIAGNOSTIC "+json.dumps({"checks":checks,"checkpoint":state.get("current_checkpoint"),"g23":state.get("g23"),"g24":state.get("g24")},sort_keys=True),flush=True)
  raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PRIOR_SCOPE")
 by={x.get("capability_id"):x for x in registry["items"]}
 dom_by={x.get("capability_id"):x for x in domain["capabilities"]}
 for cid,name,_ in TASKS:
  if by.get(cid,{}).get("canonical_name")!=name or dom_by.get(cid,{}).get("canonical_name")!=name:
   raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_IDENTITY_{cid}")
 pairs={cid:(by[cid].get("implementation_state"),dom_by[cid].get("implementation_state")) for cid,_,_ in TASKS}
 executor="implementation/super1200/runtime/d05_material_worker_129_132.py"
 auth=state.get("next_tranche_authorization")
 prior_blob=blob_sha(PRIOR_CERT)
 if (not isinstance(auth,dict) or auth.get("checkpoint_predecessor")!="D05_125_128_MATERIALIZED"
  or auth.get("executor")!=executor or auth.get("capabilities")!=[129,130,131,132]
  or auth.get("prior_scope_g23")!="PASS_FOR_SCOPE_D05_125_128"
  or auth.get("prior_scope_g24")!="PASS_FOR_SCOPE_D05_125_128"
  or auth.get("scoped_certificate")!="continuity/certification/D05_125_128.json"
  or auth.get("prior_certificate_blob_sha")!=prior_blob
  or auth.get("global_certification_granted") is not False
  or executors.get("executors",{}).get("D05")!=executor):
  raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_AUTHORIZATION")
 if all(a=="EVIDENCED" and b=="EVIDENCED" for a,b in pairs.values()):
  for cid,name,test_name in TASKS:
   p=OUT/f"capability-{cid:04d}.json"
   if not p.is_file(): raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING_PRIOR_EVIDENCE_{cid}")
   ev=load(p); rec=ev.get("evidence_sha256"); unsigned=dict(ev); unsigned.pop("evidence_sha256",None)
   if rec!=canonical_hash(unsigned) or ev.get("module_sha256")!=sha(MODULE) or ev.get("test_sha256")!=sha(TEST) or ev.get("test_case")!=test_name or ev.get("status")!="PASS":
    raise SystemExit(f"SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_EVIDENCE_INTEGRITY_{cid}")
  print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_129_132_IDEMPOTENT_HOLD","certification_granted":False},sort_keys=True),flush=True)
  return 0
 if any(pair!=("DECLARED","QUEUED_FOR_MATERIAL_IMPLEMENTATION") for pair in pairs.values()):
  raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_PARTIAL_OR_UNEXPECTED_STATE")
 run_id=os.environ.get("GITHUB_RUN_ID")
 if not run_id: raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_GITHUB_RUN_ID")
 OUT.mkdir(parents=True,exist_ok=True)
 started=datetime.now(timezone.utc).isoformat()
 suite_results={}
 for rel in REGRESSION_SUITES:
  p=ROOT/rel
  if not p.is_file(): raise SystemExit("SUPER1200_TELEMETRY MATERIAL_WORKER=DENY_MISSING_SUITE:"+rel)
  proc=subprocess.run([sys.executable,"-B",str(p),"-v"],cwd=ROOT,text=True,capture_output=True,timeout=300)
  if proc.returncode:
   print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_PROOF_ASSURANCE_REGRESSION_FAILED","suite":rel,"exit_code":proc.returncode,"stdout":proc.stdout[-8000:],"stderr":proc.stderr[-8000:]},sort_keys=True),flush=True)
   return proc.returncode or 1
  suite_results[rel]={"exit_code":0,"test_sha256":sha(p),"stdout_sha256":hashlib.sha256(proc.stdout.encode()).hexdigest(),"stderr_sha256":hashlib.sha256(proc.stderr.encode()).hexdigest()}
 case_results={}
 for cid,name,test_name in TASKS:
  proc=subprocess.run([sys.executable,"-B",str(TEST),"-v",f"D05ProofAssuranceTests.{test_name}"],cwd=ROOT,text=True,capture_output=True,timeout=120)
  output=proc.stdout+"\n"+proc.stderr
  passed=proc.returncode==0 and test_name in output and "Ran 1 test" in output and "OK" in output and "FAILED" not in output
  case_results[cid]={"test_case":test_name,"exit_code":proc.returncode,"result":"PASS" if passed else "FAIL",
   "stdout_sha256":hashlib.sha256(proc.stdout.encode()).hexdigest(),"stderr_sha256":hashlib.sha256(proc.stderr.encode()).hexdigest(),
   "test_name_seen":test_name in output,"single_test_run_confirmed":"Ran 1 test" in output,"unittest_ok_marker":"OK" in output and "FAILED" not in output}
  if not passed:
   print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_PROOF_ASSURANCE_TEST_FAILED","capability_id":cid,"test_case":test_name,"stdout":proc.stdout[-8000:],"stderr":proc.stderr[-8000:]},sort_keys=True),flush=True)
   return proc.returncode or 1
 completed=datetime.now(timezone.utc).isoformat(); module_hash=sha(MODULE); test_hash=sha(TEST)
 for cid,name,test_name in TASKS:
  ev={"schema":"SUPER1200_D05_PROOF_ASSURANCE_EVIDENCE/1","capability_id":cid,"canonical_name":name,
   "executor":executor,"implementation_artifact":"implementation/super1200/domains/D05_proof_assurance.py",
   "test_artifact":"implementation/super1200/tests/test_d05_proof_assurance.py","test_case":test_name,"status":"PASS",
   "test_invocation":["python3","-B","test_d05_proof_assurance.py","-v",f"D05ProofAssuranceTests.{test_name}"],
   "selected_test_result":case_results[cid],"validated_at_utc":completed,"worker_started_at_utc":started,
   "github_actions_run_id":int(run_id),"module_sha256":module_hash,"test_sha256":test_hash,
   "prior_scoped_certificate":"continuity/certification/D05_125_128.json","prior_certificate_blob_sha":prior_blob,
   "proof_semantics":"TRUSTED_REPLAY_CALLBACK_AND_STRUCTURAL_VALIDATION_ONLY","theorem_claim_from_type_checking":False,
   "certification_granted":False,"g23":"PENDING_INDEPENDENT_VALIDATION","g24":"PENDING_G23",
   "regression_suites":suite_results}
  ev["evidence_sha256"]=canonical_hash(ev)
  (OUT/f"capability-{cid:04d}.json").write_text(json.dumps(ev,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
  for item in (by[cid],dom_by[cid]):
   item["implementation_state"]="EVIDENCED"
   item["implementation_artifact"]="implementation/super1200/domains/D05_proof_assurance.py"
   item["test_artifact"]="implementation/super1200/tests/test_d05_proof_assurance.py"
   item["materialization"]="CODE+PER_CAPABILITY_TEST+REGRESSION_SUITES+HASH_BOUND_EVIDENCE"
   item["theorem_claim_from_type_checking"]=False
 DOMAIN.write_text(json.dumps(domain,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 REGISTRY.write_text(json.dumps(registry,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 url=f'{os.environ.get("GITHUB_SERVER_URL","https://github.com")}/{os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")}/actions/runs/{run_id}'
 state.update({"current_checkpoint":"D05_129_132_MATERIALIZED","next_point":"D05","status":"BLOCKED","blocked":True,
  "block_reason":"NEXT_D05_TRANCHE_EXECUTOR_NOT_REGISTERED","blocked_at":completed,"active_worker":False,"material_worker_ready":False,
  "certified":False,"global_certification_status":"NOT_CERTIFIED","g23":"PENDING_FOR_SCOPE_D05_129_132","g24":"PENDING_G23",
  "diagnostic":"D05 capabilities 129-132 now have proof-checker binding, content-addressed artifact descriptors, typed acyclic proof-dependency graph with reverse invalidation, and a trusted-callback replay receipt. External checker execution is not performed by the binding function; replay is accepted only through the supplied trusted callback. G23/G24 pending; global SUPER1200 remains NOT_CERTIFIED.",
  "recovery_note":"Register a reviewed task-specific executor for capabilities 133-136 only after scoped G23/G24 for D05 129-132. Preserve D05 125-128 source hashes and its historical scoped certificate; no certification propagation.",
  "next_tranche_authorization":None,
  "last_execution":{"workflow_run_id":int(run_id),"workflow_url":url,"status":"COMPLETED_SUCCESS_MATERIAL_TRANCHE","started_at_utc":started,"completed_at_utc":completed,
   "configured_runtime_hours":0.05,"material_capabilities":[129,130,131,132],"behavior_tests":"8_REGRESSION_SUITES_PASS;4_OF_4_CAPABILITY_TESTS_PASS",
   "executor":executor,"g23":"PENDING","g24":"PENDING_G23","global_certification_status":"NOT_CERTIFIED"},
  "last_material_execution":{"executor":executor,"capabilities":[129,130,131,132],"tests":"8_REGRESSION_SUITES_PASS;4_OF_4_INDEPENDENT_TEST_INVOCATIONS_PASS",
   "test_case_results":[case_results[cid] for cid,_,_ in TASKS],"module_sha256":module_hash,"test_sha256":test_hash,
   "github_actions_run_id":int(run_id),"g23":"PENDING","g24":"PENDING","certification_granted":False,"completed_at_utc":completed}})
 STATE.write_text(json.dumps(state,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
 print("SUPER1200_TELEMETRY "+json.dumps({"event":"D05_FOUNDATIONS_MATERIAL_PASS","capabilities":[129,130,131,132],
  "module_sha256":module_hash,"test_sha256":test_hash,"g23":"PENDING","g24":"PENDING_G23",
  "certification_granted":False,"global_certification_status":"NOT_CERTIFIED","workflow_run_id":int(run_id)},sort_keys=True),flush=True)
 return 0

if __name__=="__main__":
 raise SystemExit(main())
