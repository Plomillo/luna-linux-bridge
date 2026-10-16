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
