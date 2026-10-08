#!/usr/bin/env python3
import json,os,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
state=json.loads((ROOT/"continuity/STATE.json").read_text()); ex=json.loads((ROOT/"continuity/EXECUTORS.json").read_text())["executors"]
nxt=os.environ["NEXT_POINT"]
if nxt!=state["next_point"]: raise SystemExit("TRANSITION_MISMATCH")
cmd=ex.get(nxt)
if not cmd: raise SystemExit("EXECUTOR_NOT_REGISTERED")
state.update({"active_worker":True,"status":"RUNNING"}); (ROOT/"continuity/STATE.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
p=subprocess.run(["python3","-B",cmd],cwd=ROOT,text=True)
if p.returncode: raise SystemExit(p.returncode)
result=ROOT/"continuity/CONTINUATION_RESULT.json"
if not result.is_file(): raise SystemExit("MISSING_CONTINUATION_RESULT")
r=json.loads(result.read_text())
if r.get("status")!="PASS" or not r.get("next_point"): raise SystemExit("INVALID_CONTINUATION_RESULT")
state=json.loads((ROOT/"continuity/STATE.json").read_text()); state.update({"active_worker":False,"status":"DISPATCH_PENDING","current_checkpoint":r.get("checkpoint",state["current_checkpoint"]),"next_point":r["next_point"],"transition_id":r.get("transition_id",state["transition_id"]+"->"+r["next_point"])})
(ROOT/"continuity/STATE.json").write_text(json.dumps(state,indent=2,sort_keys=True)+"\n")
