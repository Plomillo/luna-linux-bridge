"""Evidence binder only. CRFU itself cannot perform G23/G24 certification or canonical promotion."""
from __future__ import annotations
from typing import Any,Callable
import re
from .model import is_sha256
from .puac2 import validate_puac_control

CANONICAL_GATES=tuple(f"G{i:02d}" for i in range(1,25))
LOCAL_PUAC_CONTROLS=tuple(f"PUAC.C{i}" for i in range(25,33))
def is_git_commit(value:Any)->bool:return isinstance(value,str) and re.fullmatch(r"[0-9a-f]{40}",value) is not None

def evaluate_gate_evidence(records:Any,*,candidate_commit_sha:str,package_sha256:str,
                           trusted_workflow_sha:str,producer_identity:str,
                           trusted_signature_verifier:Callable[[dict[str,Any]],dict[str,Any]]|None=None,
                           applicability_verifier:Callable[[list[dict[str,Any]],str],dict[str,Any]]|None=None)->dict[str,Any]:
 """Check evidence bindings without promoting status. External trusted checks are required."""
 if not is_git_commit(candidate_commit_sha) or not is_sha256(package_sha256) or not is_git_commit(trusted_workflow_sha):
  return {"status":"HOLD","reason":"CANDIDATE_OR_TRUST_ROOT_IDENTITY_INVALID","release_eligible":False}
 if not isinstance(producer_identity,str) or not producer_identity.strip():
  return {"status":"HOLD","reason":"PRODUCER_IDENTITY_MISSING","release_eligible":False}
 index={}
 for row in records if isinstance(records,list) else []:
  if isinstance(row,dict) and isinstance(row.get("gate_id"),str):
   if row["gate_id"] in index:
    return {"status":"FAIL","reason":"DUPLICATE_GATE_RECORD:"+row["gate_id"],"release_eligible":False}
   index[row["gate_id"]]=row
 canonical_pass=[];canonical_hold=[];canonical_fail=[]
 local_pass=[];local_hold=[];local_fail=[]
 verification_results={}
 for gate in list(CANONICAL_GATES)+list(LOCAL_PUAC_CONTROLS):
  row=index.get(gate)
  if not row:
   (canonical_hold if gate in CANONICAL_GATES else local_hold).append(gate+":EVIDENCE_MISSING")
   continue
  issues=[]
  if row.get("candidate_commit_sha")!=candidate_commit_sha:issues.append("CANDIDATE_COMMIT_MISMATCH")
  if row.get("package_sha256")!=package_sha256:issues.append("PACKAGE_DIGEST_MISMATCH")
  if row.get("trusted_workflow_sha")!=trusted_workflow_sha:issues.append("TRUST_ROOT_MISMATCH")
  if row.get("producer_identity")!=producer_identity:issues.append("PRODUCER_IDENTITY_MISMATCH")
  if not row.get("evaluator_identity") or row.get("evaluator_identity")==row.get("producer_identity"):
   issues.append("INDEPENDENT_EVALUATOR_NOT_ESTABLISHED")
  if not is_sha256(row.get("evidence_sha256")):issues.append("EVIDENCE_DIGEST_INVALID")
  if row.get("status")!="PASS":issues.append("GATE_RESULT_NOT_PASS")
  if trusted_signature_verifier is None:
   issues.append("TRUSTED_SIGNATURE_VERIFIER_UNAVAILABLE")
  else:
   try:
    verified=trusted_signature_verifier(dict(row))
    verification_results[gate]=verified
    if not isinstance(verified,dict) or verified.get("status")!="PASS":
     issues.append("TRUSTED_SIGNATURE_VERIFICATION_FAILED")
   except Exception:
    issues.append("TRUSTED_SIGNATURE_VERIFICATION_EXCEPTION")
  if gate in LOCAL_PUAC_CONTROLS:
   control=validate_puac_control(gate,row.get("evidence_payload"),
        producer_identity=row.get("producer_identity"),evaluator_identity=row.get("evaluator_identity"),candidate_sha256=package_sha256)
   if control.get("status")!="PASS_FOR_LOCAL_CONTROL_SCOPE":
    issues.extend("PUAC_CONTROL:"+x for x in control.get("reasons",["CONTROL_VALIDATION_FAILED"]))
  if issues:
   target=canonical_fail if gate in CANONICAL_GATES else local_fail
   target.extend(gate+":"+issue for issue in sorted(set(issues)))
  else:
   (canonical_pass if gate in CANONICAL_GATES else local_pass).append(gate)
 if applicability_verifier is None:
  canonical_hold.append("CANONICAL_APPLICABILITY_MATRIX_UNVERIFIED")
 else:
  try:
   applicability=applicability_verifier([dict(x) for x in index.values()],candidate_commit_sha)
   if not isinstance(applicability,dict) or applicability.get("status")!="PASS":
    canonical_hold.append("CANONICAL_APPLICABILITY_NOT_VALIDATED")
   else:
    allowed=applicability.get("applicable_gate_ids")
    if not isinstance(allowed,list) or set(allowed)!=set(CANONICAL_GATES):
     canonical_hold.append("CANONICAL_APPLICABILITY_SET_MISMATCH")
  except Exception:
   canonical_hold.append("CANONICAL_APPLICABILITY_VERIFICATION_EXCEPTION")
 status="EVIDENCE_BINDINGS_PASS_ONLY" if len(canonical_pass)==24 and len(local_pass)==8 and not canonical_hold and not canonical_fail and not local_hold and not local_fail else ("FAIL" if canonical_fail or local_fail else "HOLD")
 return {
  "schema":"CUSTOSZV9_GATE_EVIDENCE_BINDING/1.0","status":status,
  "canonical_gate_count":24,"canonical_gates_passed":canonical_pass,"canonical_gates_held":canonical_hold,
  "canonical_gates_failed":canonical_fail,"local_puac_control_count":8,
  "local_controls_passed":local_pass,"local_controls_held":local_hold,"local_controls_failed":local_fail,
  "signature_verification_results":verification_results,
  "release_eligible":False,"certification":"NOT_GRANTED_BY_CRFU",
  "puac2_canonical_admission":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED",
  "note":"This module binds evidence only. G23/G24, applicability, PUAC2 admission and release authorization require separate trusted authorities; a field claiming VERIFIED is not a signature check."
}
