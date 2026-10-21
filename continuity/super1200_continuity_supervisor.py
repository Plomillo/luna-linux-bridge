import json,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; STATE=ROOT/"continuity/STATE.json"; EXEC=ROOT/"continuity/EXECUTORS.json"; REPORT=ROOT/"continuity/CONTINUITY_REPORT.txt"
s=json.loads(STATE.read_text()); ex=json.loads(EXEC.read_text())["executors"]; nxt=s["next_point"]; ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
scoped_hold = (s.get("g23","").startswith("PASS_FOR_SCOPE_") or s.get("g23","").startswith("PENDING_FOR_SCOPE_")) and s.get("blocked") is True and s.get("global_certification_status")=="NOT_CERTIFIED" and s.get("certified") is False
if s.get("active_worker"): status="WORKER_ACTIVE"
elif s.get("terminal") or nxt in ("","NONE","TERMINAL"): status="TERMINAL"
elif scoped_hold:
 status="BLOCKED"
elif nxt not in ex:
 status="BLOCKED"; s.update({"blocked":True,"block_reason":"NO_REGISTERED_EXECUTOR_FOR_NEXT_DOMAIN","blocked_at":ts,"diagnostic":"No material executor exists; do not synthesize capability evidence."})
else:
 status="DISPATCH_REQUIRED"; s.update({"blocked":False,"block_reason":"NONE","dispatch_error":None,"status":status,"dispatch_requested_at":ts,"next_worker":ex[nxt]})
if not scoped_hold:
 s["status"]=status
REPORT.write_text("\n".join(["SUPER1200 CONTINUITY REPORT","BRANCH=custosz/super-1200-implementation-20261007","TIMESTAMP_UTC="+ts,"CURRENT_CHECKPOINT="+s["current_checkpoint"],"NEXT_POINT="+nxt,"WHAT_WAS_DONE=durable continuation reconciliation","WHAT_WAS_VALIDATED=state executor registry terminal worker invariants","WHAT_FAILED="+s.get("block_reason","NONE"),"WHAT_REMAINS_UNKNOWN=NONE" if status!="BLOCKED" else "executor implementation for "+nxt,"NEXT_ACTION="+("HOLD_SCOPED_CERTIFICATION" if scoped_hold else ("DISPATCH_REGISTERED_EXECUTOR" if status=="DISPATCH_REQUIRED" else ("REGISTER_EXECUTOR_AND_REDISPATCH" if status=="BLOCKED" else status))),"NEXT_WORKER="+ex.get(nxt,"NONE"),"DISPATCH_STATUS="+status,"SUPERVISOR_STATUS=ACTIVE","META_SUPERVISOR_STATUS=REQUIRED","WATCHDOG_STATUS=EXTERNAL_REQUIRED","G23=SEPARATE","G24=SEPARATE","CERTIFIED=false","ACTIVE=false"])+"\n")
if not scoped_hold:
 STATE.write_text(json.dumps(s,indent=2,sort_keys=True)+"\n")
print("SUPER1200_CONTINUITY "+status+" next="+nxt)
