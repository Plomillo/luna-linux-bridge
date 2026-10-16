"""Evidence binder only. CRFU itself cannot certify G23/G24 or promote canonical status."""
from __future__ import annotations
from typing import Any,Callable
import re
from .model import is_sha256
from .puac2 import validate_puac_control

CANONICAL_GATES=tuple(f"G{i:02d}" for i in range(1,25))
LOCAL_PUAC_CONTROLS=tuple(f"PUAC.C{i}" for i in range(25,33))
def is_git_commit(value:Any)->bool:
 return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{40}",value) is not None

def evaluate_gate_evidence(records:Any,*,candidate_commit_sha:str,package_sha256:str,
 trusted_workflow_sha:str,producer_identity:str,
 trusted_signature_verifier:Callable[[dict[str,Any]],dict[str,Any]]|None=None,
 applicability_verifier:Callable[[list[dict[str,Any]],str],dict[str,Any]]|None=None)->dict[str,Any]:
 """Bind evidence; unavailable verifiers yield HOLD, contradictions yield FAIL."""
 if not is_git_commit(candidate_commit_sha) or not is_sha256(package_sha256) or not is_git_commit(trusted_workflow_sha):
  return {"status":"HOLD","reason":"CANDIDATE_OR_TRUST_ROOT_IDENTITY_INVALID","release_eligible":False}
 if not isinstance(producer_identity,str) or not producer_identity.strip():
  return {"status":"HOLD","reason":"PRODUCER_IDENTITY_MISSING","release_eligible":False}
 if not isinstance(records,list):
  return {"status":"HOLD","reason":"GATE_EVIDENCE_ROOT_NOT_LIST","release_eligible":False}
 index={}
 registered=set(CANONICAL_GATES)|set(LOCAL_PUAC_CONTROLS)
 for position,row in enumerate(records):
  if not isinstance(row,dict) or not isinstance(row.get("gate_id"),str) or not row["gate_id"].strip():
   return {"status":"FAIL","reason":"MALFORMED_GATE_RECORD:"+str(position),"release_eligible":False}
  gate_id=row["gate_id"]
  if gate_id not in registered:
   return {"status":"FAIL","reason":"UNREGISTERED_GATE_IDENTIFIER:"+gate_id,"release_eligible":False}
  if gate_id in index:
   return {"status":"FAIL","reason":"DUPLICATE_GATE_RECORD:"+gate_id,"release_eligible":False}
  index[gate_id]=row
 cp=[];ch=[];cf=[];lp=[];lh=[];lf=[];signature_results={}
 for gate in list(CANONICAL_GATES)+list(LOCAL_PUAC_CONTROLS):
  local=gate in LOCAL_PUAC_CONTROLS
  passed=lp if local else cp;held=lh if local else ch;failed=lf if local else cf
  row=index.get(gate)
  if row is None:
   held.append(gate+":EVIDENCE_MISSING");continue
  hard=[];pending=[]
  if row.get("candidate_commit_sha")!=candidate_commit_sha:hard.append("CANDIDATE_COMMIT_MISMATCH")
  if row.get("package_sha256")!=package_sha256:hard.append("PACKAGE_DIGEST_MISMATCH")
  if row.get("trusted_workflow_sha")!=trusted_workflow_sha:hard.append("TRUST_ROOT_MISMATCH")
  if row.get("producer_identity")!=producer_identity:hard.append("PRODUCER_IDENTITY_MISMATCH")
  if not row.get("evaluator_identity"):pending.append("INDEPENDENT_EVALUATOR_NOT_ESTABLISHED")
  elif row.get("evaluator_identity")==row.get("producer_identity"):hard.append("EXECUTOR_EVALUATOR_IDENTITY_COLLISION")
  if not is_sha256(row.get("evidence_sha256")):pending.append("EVIDENCE_DIGEST_INVALID_OR_MISSING")
  gate_state=row.get("status")
  if gate_state=="FAIL":hard.append("UPSTREAM_GATE_REPORTED_FAIL")
  elif gate_state!="PASS":pending.append("GATE_RESULT_NOT_PASS")
  if trusted_signature_verifier is None:
   pending.append("TRUSTED_SIGNATURE_VERIFIER_UNAVAILABLE")
  else:
   try:
    result=trusted_signature_verifier(dict(row));signature_results[gate]=result
    if not isinstance(result,dict) or result.get("status")!="PASS":pending.append("TRUSTED_SIGNATURE_NOT_VERIFIED")
   except Exception:pending.append("TRUSTED_SIGNATURE_VERIFICATION_EXCEPTION")
  if local:
   try:
    checked=validate_puac_control(gate,row.get("evidence_payload"),
      producer_identity=row.get("producer_identity"),evaluator_identity=row.get("evaluator_identity"),
      candidate_sha256=package_sha256,candidate_commit_sha=candidate_commit_sha)
    if checked.get("status")=="HOLD":
     pending.extend("PUAC_CONTROL:"+x for x in checked.get("reasons",["CONTROL_EVIDENCE_INCOMPLETE"]))
    elif checked.get("status")!="PASS_FOR_LOCAL_CONTROL_SCOPE":
     hard.extend("PUAC_CONTROL:"+x for x in checked.get("reasons",["CONTROL_VALIDATION_FAILED"]))
   except Exception:pending.append("PUAC_CONTROL_VALIDATOR_UNAVAILABLE")
  if hard:failed.extend(gate+":"+x for x in sorted(set(hard)))
  elif pending:held.extend(gate+":"+x for x in sorted(set(pending)))
  else:passed.append(gate)
 if applicability_verifier is None:
  ch.append("CANONICAL_APPLICABILITY_MATRIX_UNVERIFIED")
 else:
  try:
   application=applicability_verifier([dict(x) for x in index.values()],candidate_commit_sha)
   if not isinstance(application,dict) or application.get("status")!="PASS":
    ch.append("CANONICAL_APPLICABILITY_NOT_VALIDATED")
   else:
    allowed=application.get("applicable_gate_ids")
    if not isinstance(allowed,list) or set(allowed)!=set(CANONICAL_GATES):
     ch.append("CANONICAL_APPLICABILITY_SET_MISMATCH")
  except Exception:ch.append("CANONICAL_APPLICABILITY_VERIFICATION_EXCEPTION")
 if cf or lf:status="FAIL"
 elif len(cp)==24 and len(lp)==8 and not ch and not lh:status="EVIDENCE_BINDINGS_PASS_ONLY"
 else:status="HOLD"
 return {"schema":"CUSTOSZV9_GATE_EVIDENCE_BINDING/1.1","status":status,
  "canonical_gate_count":24,"canonical_gates_passed":cp,"canonical_gates_held":ch,
  "canonical_gates_failed":cf,"local_puac_control_count":8,"local_controls_passed":lp,
  "local_controls_held":lh,"local_controls_failed":lf,"signature_verification_results":signature_results,
  "release_eligible":False,"certification":"NOT_GRANTED_BY_CRFU","puac2_canonical_admission":"NOT_GRANTED",
  "canonical_promotion":"NOT_AUTHORIZED",
  "note":"Unavailable or incomplete assurance prerequisites yield HOLD. Contradictions yield FAIL. A field claiming VERIFIED is never itself a signature check."}
