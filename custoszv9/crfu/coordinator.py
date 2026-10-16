"""Bounded coordinator. Execution requires trusted authorization and action adapters."""
from typing import Any,Callable
from .anti_paralysis import decide_next_action,state_fingerprint
from .model import TaskContract
from .planner import ActionSpec,build_plan
from .resources import ResourceBudget,ResourceSnapshot,evaluate_budget
def run_bounded_mission(task_raw:Any,actions:list[ActionSpec],snapshot:ResourceSnapshot,*,available_capabilities:set[str],admissible_effects:set[str],authorization_verifier:Callable[[dict[str,Any]],dict[str,Any]]|None,action_runner:Callable[[dict[str,Any]],dict[str,Any]]|None,maximum_steps:int,planning_budget:int)->dict[str,Any]:
 task,issues=TaskContract.validate(task_raw)
 if issues or task is None:return {"status":"DENIED","stage":"TASK_VALIDATION","reasons":issues,"next_action":"CORRECT_TASK_CONTRACT"}
 if authorization_verifier is None:return {"status":"HOLD","stage":"AUTHORIZATION","reasons":["TRUSTED_AUTHORIZATION_VERIFIER_UNAVAILABLE"],"next_action":"CONFIGURE_TRUSTED_AUTHORIZATION_ADAPTER"}
 auth=authorization_verifier(dict(task.value))
 if not isinstance(auth,dict) or auth.get("status")!="PASS" or auth.get("task_id")!=task.task_id:return {"status":"DENIED","stage":"AUTHORIZATION","reasons":["AUTHORIZATION_NOT_VALIDLY_BOUND"],"next_action":"OBTAIN_VALID_SCOPE_BOUND_AUTHORIZATION"}
 raw=task.value["resource_budget"];budget=ResourceBudget(raw["ram_required_bytes"],raw["ram_reserved_bytes"],raw["disk_required_bytes"],raw["max_concurrency"])
 resource=evaluate_budget(budget,snapshot)
 if resource["status"]!="PASS":return {"status":"HOLD","stage":"RESOURCE_PREFLIGHT","resource":resource,"next_action":"WAIT_FOR_RESOURCE_CONDITION_OR_REPLAN"}
 plan=build_plan(actions,max_alternatives=planning_budget,available_capabilities=available_capabilities,admissible_effects=admissible_effects)
 if plan["status"]!="PLAN_VALIDATED":return {"status":"HOLD","stage":"PLANNING","plan":plan,"next_action":"REPLAN_OR_RECORD_BLOCKER"}
 if action_runner is None:return {"status":"HOLD","stage":"EXECUTION","plan":plan,"next_action":"CONFIGURE_GOVERNED_ACTION_ADAPTER"}
 completed=[];attempts=[];state=task.source_state_hash
 for step in plan["actions"][:max(0,min(maximum_steps,planning_budget))]:
  fp=state_fingerprint({"source":state,"completed":completed,"next":step["action_id"]})
  decision=decide_next_action(action_id=step["action_id"],strategy_id="topological-v1",state_hash=fp,previous_attempts=attempts,new_evidence=False,planning_budget_remaining=planning_budget-len(completed),retry_budget_remaining=int(task.value["maximum_retry_budget"]))
  if decision["decision"]!="EXECUTE_NEXT_ACTION":return {"status":"BLOCKED","completed":completed,"decision":decision}
  outcome=action_runner({"action":step,"task":dict(task.value),"authorization":auth})
  if not isinstance(outcome,dict) or outcome.get("status")!="PASS":return {"status":"BLOCKED","completed":completed,"failed_action":step["action_id"],"failure":outcome,"next_action":"PRESERVE_CHECKPOINT_AND_REVALIDATE"}
  attempts.append({"action_id":step["action_id"],"strategy_id":"topological-v1","state_hash":fp});completed.append(step["action_id"]);state=str(outcome.get("result_state_hash",state))
 status="COMPLETED" if len(completed)==len(plan["actions"]) else "PAUSED_BUDGET_BOUND"
 return {"status":status,"completed_actions":completed,"plan":plan,"completion_claim":status=="COMPLETED","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
