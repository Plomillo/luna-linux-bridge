#!/usr/bin/env python3
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
STATE=ROOT/"continuity/STATE.json"
try:
    state=json.loads(STATE.read_text())
    ex=json.loads((ROOT/"continuity/EXECUTORS.json").read_text())["executors"]
    nxt=os.environ.get("NEXT_POINT","")
    if nxt!=state["next_point"]: raise SystemExit("TRANSITION_MISMATCH")
    cmd=ex.get(nxt)
    if not cmd: raise SystemExit("EXECUTOR_NOT_REGISTERED")
    state.update({"active_worker":True,"blocked":False,"status":"RUNNING","block_reason":"NONE","next_worker":cmd})
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
    p=subprocess.run(["python3","-B",cmd],cwd=ROOT,text=True)
    if p.returncode:
        state=json.loads(STATE.read_text())
        state.update({"active_worker":False,"blocked":True,"status":"BLOCKED","block_reason":"EXECUTOR_FAILURE","diagnostic":f"Executor {cmd} exited {p.returncode}.","next_worker":cmd})
        STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
        raise SystemExit(p.returncode)
    result=ROOT/"continuity/CONTINUATION_RESULT.json"
    if not result.is_file(): raise SystemExit("MISSING_CONTINUATION_RESULT")
    r=json.loads(result.read_text())
    if r.get("status") not in ("PASS","HOLD_INDEPENDENT_CONTINUATION") or not r.get("next_point"):
        raise SystemExit("INVALID_CONTINUATION_RESULT")
    state=json.loads(STATE.read_text())
    next_point=r["next_point"]
    next_worker=ex.get(next_point)
    resolved=set(r.get("resolved_blockers",[]))
    blockers=[b for b in state.get("open_blockers",[]) if b not in resolved]
    blockers=list(dict.fromkeys(blockers+list(r.get("open_blockers",[]))))
    same_point_hold=(r.get("status")=="HOLD_INDEPENDENT_CONTINUATION" and next_point==nxt)
    state.update({
        "active_worker":False,
        "blocked":same_point_hold or not next_worker,
        "status":"BLOCKED" if (same_point_hold or not next_worker) else "DISPATCH_PENDING",
        "block_reason":("HOLD_REQUIRES_NEW_EVIDENCE" if same_point_hold else ("NO_REGISTERED_EXECUTOR_FOR_NEXT_POINT" if not next_worker else "NONE")),
        "current_checkpoint":r.get("checkpoint",state["current_checkpoint"]),
        "next_point":next_point,
        "next_worker":next_worker,
        "open_blockers":blockers,
        "certified":False,
        "transition_id":r.get("transition_id",state["transition_id"]+"->"+next_point)
    })
    STATE.write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
except BaseException:
    raise
