# P04_OBJECT_DATABASE_RETRY
# P04_SUBSTRATE_RETRY_MARKER
#!/usr/bin/env python3
import json, subprocess, time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/"continuity/STATE.json"
EXEC=ROOT/"continuity/EXECUTORS.json"
REPORT=ROOT/"continuity/CONTINUITY_REPORT.txt"
def sh(*cmd): return subprocess.run(cmd,text=True,capture_output=True,check=False)
def main():
 state=json.loads(STATE.read_text());
 if state.get("block_reason")=="DISPATCH_COMMAND_FAILED": state.update({"blocked":False,"block_reason":"NONE","status":"DISPATCH_PENDING","dispatch_stderr":None})
 executors=json.loads(EXEC.read_text())["executors"]; nxt=state["next_point"]; worker=bool(state.get("active_worker")); ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
 if state.get("blocked") and nxt in executors:
  state.update({"blocked":False,"block_reason":"NONE","status":"DISPATCH_PENDING"})
 safe_pending=(not state["terminal"] and not state["blocked"] and nxt not in ("","NONE","TERMINAL"))
 if safe_pending and not worker and nxt not in executors:
  status="BLOCKED"; state.update({"status":"BLOCKED","blocked":True,"block_reason":"NO_REGISTERED_EXECUTOR_FOR_NEXT_POINT","blocked_at":ts,"diagnostic":"No material executor exists for "+nxt+"; invention of work is forbidden."})
 elif safe_pending and not worker:
  status="DISPATCH_REQUIRED"; state["status"]=status; state["dispatch_requested_at"]=ts; STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
 elif worker: status="WORKER_ACTIVE"
 else: status="TERMINAL" if state["terminal"] else "BLOCKED"
 REPORT.write_text("\n".join(["LOUKSNA V0.4 CONTINUITY REPORT","BRANCH=work/louksna-zd-v04-master-20261007","TIMESTAMP_UTC="+ts,"CURRENT_CHECKPOINT="+state["current_checkpoint"],"NEXT_POINT="+nxt,"WHAT_WAS_DONE=durable continuation reconciliation","WHAT_WAS_VALIDATED=state executor registry terminal worker invariants","WHAT_FAILED="+(state.get("block_reason") or "NONE"),"WHAT_REMAINS_UNKNOWN="+("executor implementation for "+nxt if status=="BLOCKED" else "NONE"),"NEXT_ACTION="+("REGISTER_EXECUTOR_AND_REDISPATCH" if status=="BLOCKED" else status),"NEXT_WORKER="+executors.get(nxt,"NONE"),"DISPATCH_STATUS="+status,"SUPERVISOR_STATUS=ACTIVE","META_SUPERVISOR_STATUS=REQUIRED","WATCHDOG_STATUS=EXTERNAL_REQUIRED","G23=SEPARATE","G24=SEPARATE","CERTIFIED=false","ACTIVE=false"])+"\n")
 STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
 print("LOUKSNA_CONTINUITY "+status+" next="+nxt,flush=True); return 0
if __name__=="__main__": raise SystemExit(main())