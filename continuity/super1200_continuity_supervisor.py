import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
state=json.loads((ROOT/"continuity/STATE.json").read_text())
ex=json.loads((ROOT/"continuity/EXECUTORS.json").read_text())["executors"]
nxt=state["next_point"]
ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
worker=bool(state.get("active_worker"))
if state.get("block_reason")=="DISPATCH_COMMAND_FAILED" or state.get("dispatch_error"):
    state.update({"blocked":False,"block_reason":"NONE","status":"DISPATCH_PENDING","dispatch_error":None})
if state.get("blocked") and nxt in ex:
  state.update({"blocked":False,"block_reason":"NONE","status":"DISPATCH_PENDING"})
safe=not state["terminal"] and not state["blocked"] and nxt not in ("","NONE","TERMINAL")
if safe and not worker and nxt not in ex:
    status="BLOCKED"
    state.update({"status":status,"blocked":True,"block_reason":"NO_REGISTERED_EXECUTOR_FOR_NEXT_DOMAIN","blocked_at":ts,"diagnostic":"No material executor exists; do not synthesize capability evidence."})
elif safe and not worker:
    status="DISPATCH_REQUIRED"
    state.update({"status":status,"blocked":False,"dispatch_requested_at":ts})
elif worker:
    status="WORKER_ACTIVE"
else:
    status="TERMINAL" if state["terminal"] else "BLOCKED"
state["status"]=status
(ROOT/"continuity/STATE.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
nextworker=ex.get(nxt,"NONE")
unknown=("material executor for "+nxt if status=="BLOCKED" else "NONE")
(ROOT/"continuity/CONTINUITY_REPORT.txt").write_text("\n".join(["SUPER1200 CONTINUITY REPORT","BRANCH=custosz/super-1200-implementation-20261007","TIMESTAMP_UTC="+ts,"CURRENT_CHECKPOINT="+state["current_checkpoint"],"NEXT_POINT="+nxt,"WHAT_WAS_DONE=durable continuation reconciliation","WHAT_WAS_VALIDATED=state executor registry terminal worker invariants","WHAT_FAILED="+state.get("block_reason","NONE"),"WHAT_REMAINS_UNKNOWN="+unknown,"NEXT_ACTION="+("REGISTER_EXECUTOR_AND_REDISPATCH" if status=="BLOCKED" else status),"NEXT_WORKER="+nextworker,"DISPATCH_STATUS="+status,"SUPERVISOR_STATUS=ACTIVE","META_SUPERVISOR_STATUS=REQUIRED","WATCHDOG_STATUS=EXTERNAL_REQUIRED","G23=SEPARATE","G24=SEPARATE","CERTIFIED=false","ACTIVE=false"])+"\n")
print("SUPER1200_CONTINUITY "+status+" next="+nxt,flush=True)
