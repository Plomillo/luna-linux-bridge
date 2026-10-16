"""Typed task contract and identity checks; authorization is never inferred."""
from __future__ import annotations
import hashlib,json,re
from dataclasses import dataclass
from datetime import datetime
from typing import Any,Mapping
SHA256_RE=re.compile(r"^[0-9a-f]{64}$")
REQUIRED=("task_id","mission_id","project_id","source_identity","target_identity","source_state_hash","dependency_set","authorized_scope","required_capabilities","inputs","preconditions","permitted_effects","resource_budget","execution_deadline","maximum_planning_budget","maximum_retry_budget","acceptance_criteria","expected_outputs","validation_strategy","evidence_requirements","checkpoint_reference","rollback_strategy","completion_condition","escalation_condition")
def canonical_json(value:Any)->str:return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha256_bytes(data:bytes)->str:return hashlib.sha256(data).hexdigest()
def is_sha256(value:Any)->bool:return isinstance(value,str) and SHA256_RE.fullmatch(value) is not None
def valid_utc(value:Any)->bool:
 if not isinstance(value,str) or not value.strip():return False
 try:return datetime.fromisoformat(value.replace("Z","+00:00")).tzinfo is not None
 except ValueError:return False
@dataclass(frozen=True)
class TaskContract:
 value:Mapping[str,Any]
 @classmethod
 def validate(cls,value:Any)->tuple["TaskContract|None",list[str]]:
  if not isinstance(value,dict):return None,["TASK_CONTRACT_NOT_OBJECT"]
  issues=[f"TASK_FIELD_MISSING:{k}" for k in REQUIRED if k not in value]
  for k in ("task_id","mission_id","project_id","source_identity","target_identity","authorized_scope","validation_strategy","rollback_strategy","completion_condition","escalation_condition"):
   if not isinstance(value.get(k),str) or not value[k].strip():issues.append(f"TASK_FIELD_INVALID:{k}")
  if not is_sha256(value.get("source_state_hash")):issues.append("SOURCE_STATE_HASH_INVALID")
  for k in ("dependency_set","required_capabilities","inputs","preconditions","permitted_effects","acceptance_criteria","expected_outputs","evidence_requirements"):
   if not isinstance(value.get(k),(list,dict)):issues.append(f"TASK_COLLECTION_INVALID:{k}")
  for k,m in (("maximum_planning_budget",1),("maximum_retry_budget",0)):
   n=value.get(k)
   if isinstance(n,bool) or not isinstance(n,int) or n<m:issues.append(f"TASK_BUDGET_INVALID:{k}")
  b=value.get("resource_budget")
  if not isinstance(b,dict):issues.append("RESOURCE_BUDGET_INVALID")
  elif any(isinstance(b.get(k),bool) or not isinstance(b.get(k),int) or b[k]<0 for k in ("ram_required_bytes","ram_reserved_bytes","disk_required_bytes","max_concurrency")):issues.append("RESOURCE_BUDGET_FIELDS_INVALID")
  if not valid_utc(value.get("execution_deadline")):issues.append("EXECUTION_DEADLINE_INVALID")
  if issues:return None,issues
  # A reference to authorization is not a grant; an independent trusted verifier is required.
  if not value.get("authorization_evidence_reference"):issues.append("AUTHORIZATION_EVIDENCE_REFERENCE_MISSING")
  return cls(dict(value)),issues
 @property
 def task_id(self)->str:return str(self.value["task_id"])
