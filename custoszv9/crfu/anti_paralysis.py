"""Finite deliberation, progress and bounded waits."""
import hashlib
from .model import canonical_json
def state_fingerprint(state:object)->str:return hashlib.sha256(canonical_json(state).encode("utf-8")).hexdigest()
def decide_next_action(*,action_id:str|None,strategy_id:str|None,state_hash:str,previous_attempts:list[dict],new_evidence:bool,planning_budget_remaining:int,retry_budget_remaining:int,wait_condition:str|None=None,wait_deadline_utc:str|None=None)->dict:
 if planning_budget_remaining<=0:return {"decision":"BLOCKED","reason":"PLANNING_BUDGET_EXHAUSTED","next_action":None}
 if not action_id or not strategy_id or len(state_hash)!=64:return {"decision":"BLOCKED","reason":"ACTION_STRATEGY_OR_STATE_IDENTITY_INVALID","next_action":None}
 repeated=[x for x in previous_attempts if x.get("action_id")==action_id and x.get("strategy_id")==strategy_id and x.get("state_hash")==state_hash]
 if repeated and not new_evidence:return {"decision":"BLOCKED","reason":"REPEATED_STRATEGY_WITHOUT_NEW_EVIDENCE","next_action":None}
 if wait_condition is not None:
  if not wait_condition.strip() or not wait_deadline_utc:return {"decision":"BLOCKED","reason":"UNBOUNDED_WAIT_FORBIDDEN","next_action":None}
  return {"decision":"WAIT_CONDITIONALLY","wait_condition":wait_condition,"wait_deadline_utc":wait_deadline_utc,"next_action":"RESUME_ON_CONDITION_OR_DEADLINE"}
 if retry_budget_remaining<0:return {"decision":"BLOCKED","reason":"RETRY_BUDGET_INVALID","next_action":None}
 return {"decision":"EXECUTE_NEXT_ACTION","reason":"BOUNDED_PLAN_ADMISSIBLE","next_action":action_id,"strategy_id":strategy_id}
def retry_decision(*,idempotency_class:str,retries_used:int,max_retries:int,transient_failure:bool,
                   authorization_valid:bool,idempotency_key:str|None=None,effects_reconciled:bool=False,
                   wait_seconds:int=0)->dict:
 """Authorize a retry only when bounded, transient, authorized and safe for the effect class."""
 if idempotency_class not in {"READ_ONLY","IDEMPOTENT","NON_IDEMPOTENT","UNKNOWN"}:
  return {"decision":"DENY_RETRY","reason":"IDEMPOTENCY_CLASS_INVALID"}
 if any(isinstance(v,bool) or not isinstance(v,int) for v in (retries_used,max_retries,wait_seconds)) or retries_used<0 or max_retries<0 or wait_seconds<0:
  return {"decision":"DENY_RETRY","reason":"RETRY_BUDGET_INVALID"}
 if not transient_failure:return {"decision":"DENY_RETRY","reason":"FAILURE_NOT_CLASSIFIED_TRANSIENT"}
 if retries_used>=max_retries:return {"decision":"DENY_RETRY","reason":"RETRY_BUDGET_EXHAUSTED"}
 if authorization_valid is not True:return {"decision":"DENY_RETRY","reason":"AUTHORIZATION_NOT_VALID"}
 if idempotency_class=="UNKNOWN":return {"decision":"DENY_RETRY","reason":"UNKNOWN_IDEMPOTENCY_CLASS"}
 if idempotency_class=="NON_IDEMPOTENT" and (not effects_reconciled or not idempotency_key):
  return {"decision":"DENY_RETRY","reason":"NON_IDEMPOTENT_EFFECTS_NOT_RECONCILED"}
 return {"decision":"WAIT_CONDITIONALLY" if wait_seconds else "RETRY_ADMISSIBLE",
         "reason":"BOUNDED_TRANSIENT_RETRY","wait_seconds":wait_seconds,"retries_remaining":max_retries-retries_used-1,
         "authorization_reused_only_within_same_valid_scope":True}

