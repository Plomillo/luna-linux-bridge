#!/usr/bin/env python3
import json,subprocess,time
from pathlib import Path
R=Path(__file__).resolve().parents[1]; s=json.loads((R/"continuity"/"STATE.json").read_text()); ts=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
if s.get("blocked"): verdict="ESCALATE_BLOCKED"
elif s.get("active_worker"): verdict="WATCH_WORKER"
elif s.get("status")=="DISPATCH_PENDING": verdict="REDISPATCH_REQUIRED"
else: verdict="OBSERVE"
(R/"continuity"/"META_REPORT.txt").write_text("\n".join(["LOUKSNA V0.4 META-SUPERVISOR REPORT","TIMESTAMP_UTC="+ts,"VERDICT="+verdict,"PRIMARY_SUPERVISOR_STATE="+s.get("status","UNKNOWN"),"NEXT_POINT="+s.get("next_point","UNKNOWN"),"CERTIFIED=false","ACTIVE=false"])+"\n")
print("LOUKSNA_META "+verdict,flush=True)
