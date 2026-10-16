"""Bounded deterministic topological planner; a plan never grants execution authority."""
from dataclasses import dataclass,asdict
from typing import Any,Iterable
@dataclass(frozen=True)
class ActionSpec:
 action_id:str
 dependencies:tuple[str,...]=()
 required_capabilities:tuple[str,...]=()
 permitted_effects:tuple[str,...]=()
 idempotency:str="UNKNOWN"
 @classmethod
 def from_dict(cls,v:dict[str,Any])->"ActionSpec":
  if not isinstance(v,dict) or not isinstance(v.get("action_id"),str) or not v["action_id"].strip():raise ValueError("ACTION_ID_REQUIRED")
  idem=v.get("idempotency","UNKNOWN")
  if idem not in {"READ_ONLY","IDEMPOTENT","NON_IDEMPOTENT","UNKNOWN"}:raise ValueError("IDEMPOTENCY_CLASS_INVALID")
  return cls(v["action_id"],tuple(v.get("dependencies",())),tuple(v.get("required_capabilities",())),tuple(v.get("permitted_effects",())),idem)
def build_plan(actions:Iterable[ActionSpec],*,max_alternatives:int,available_capabilities:set[str],admissible_effects:set[str])->dict[str,Any]:
 if isinstance(max_alternatives,bool) or max_alternatives<1:return {"status":"DENIED","reason":"PLANNING_BUDGET_INVALID","ordered_actions":[]}
 rows=list(actions)
 if len(rows)>max_alternatives:return {"status":"HOLD","reason":"ALTERNATIVE_BUDGET_EXCEEDED","ordered_actions":[],"actions_seen":len(rows),"max_alternatives":max_alternatives}
 by={}
 for row in rows:
  if row.action_id in by:return {"status":"DENIED","reason":"DUPLICATE_ACTION_ID:"+row.action_id,"ordered_actions":[]}
  by[row.action_id]=row
 missing=sorted({d for row in rows for d in row.dependencies if d not in by})
 if missing:return {"status":"HOLD","reason":"DEPENDENCY_UNRESOLVED","missing_dependencies":missing,"ordered_actions":[]}
 for row in rows:
  caps=sorted(set(row.required_capabilities)-available_capabilities);effects=sorted(set(row.permitted_effects)-admissible_effects)
  if caps or effects:return {"status":"DENIED","reason":"ACTION_NOT_ADMISSIBLE","action_id":row.action_id,"missing_capabilities":caps,"forbidden_effects":effects,"ordered_actions":[]}
 incoming={k:set(v.dependencies) for k,v in by.items()};ordered=[];ready=sorted(k for k,d in incoming.items() if not d)
 while ready:
  cur=ready.pop(0);ordered.append(cur)
  for key in sorted(incoming):
   if cur in incoming[key]:
    incoming[key].remove(cur)
    if not incoming[key] and key not in ordered and key not in ready:ready.append(key)
  ready.sort()
 if len(ordered)!=len(rows):return {"status":"DENIED","reason":"DEPENDENCY_CYCLE","ordered_actions":[],"cyclic_actions":sorted(k for k,d in incoming.items() if d)}
 return {"status":"PLAN_VALIDATED","ordered_actions":ordered,"actions":[asdict(by[k]) for k in ordered],"execution_authorized":False,"global_optimum_claimed":False}
