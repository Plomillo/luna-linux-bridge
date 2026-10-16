"""Fail-closed gate evidence binder; it cannot create signatures or self-certify."""
from typing import Any
from .model import is_sha256
CANONICAL_GATES=tuple(f"G{i:02d}" for i in range(1,25))
LOCAL_PUAC_CONTROLS=tuple(f"PUAC.C{i}" for i in range(25,33))
def evaluate_gate_evidence(records:Any,*,candidate_commit_sha:str,package_sha256:str,trusted_workflow_sha:str,producer_identity:str)->dict[str,Any]:
 if not is_sha256(candidate_commit_sha) or not is_sha256(package_sha256) or len(trusted_workflow_sha)!=40:return {"status":"HOLD","reason":"CANDIDATE_OR_TRUST_ROOT_IDENTITY_INVALID","release_eligible":False}
 index={}
 for row in records if isinstance(records,list) else []:
  if isinstance(row,dict) and isinstance(row.get("gate_id"),str):
   if row["gate_id"] in index:return {"status":"FAIL","reason":"DUPLICATE_GATE_RECORD:"+row["gate_id"],"release_eligible":False}
   index[row["gate_id"]]=row
 required=list(CANONICAL_GATES)+list(LOCAL_PUAC_CONTROLS);hold=[];fail=[];passed=[]
 for gate in required:
  row=index.get(gate)
  if not row:hold.append(gate+":EVIDENCE_MISSING");continue
  errors=[]
  if row.get("candidate_commit_sha")!=candidate_commit_sha:errors.append("CANDIDATE_COMMIT_MISMATCH")
  if row.get("package_sha256")!=package_sha256:errors.append("PACKAGE_DIGEST_MISMATCH")
  if row.get("trusted_workflow_sha")!=trusted_workflow_sha:errors.append("TRUST_ROOT_MISMATCH")
  if row.get("producer_identity")==row.get("evaluator_identity") or not row.get("evaluator_identity"):errors.append("INDEPENDENT_EVALUATOR_NOT_ESTABLISHED")
  if row.get("signature_verification")!="VERIFIED":errors.append("TRUSTED_SIGNATURE_NOT_VERIFIED")
  if not is_sha256(row.get("evidence_sha256")):errors.append("EVIDENCE_DIGEST_INVALID")
  if errors:fail.extend(gate+":"+e for e in errors)
  elif row.get("status")=="PASS":passed.append(gate)
  else:hold.append(gate+":"+str(row.get("status","UNKNOWN")))
 status="PASS" if len(passed)==len(required) and not hold and not fail else ("FAIL" if fail else "HOLD")
 return {"status":status,"required_gate_count":len(required),"passed_gates":passed,"held_gates":hold,"failed_checks":fail,"release_eligible":status=="PASS","canonical_promotion":"NOT_AUTHORIZED","note":"Applicability and signatures must be verified by the protected gate workflow; this module only checks bindings."}
