#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence")); OUT.mkdir(parents=True,exist_ok=True)
MISSION=ROOT/"mailbox"
V03=ROOT/"mailbox"
BRIDGE=ROOT/"mailbox"
AUTH=ROOT/"Louksna.md"
PUAC=ROOT/"PUAC2.md"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def markers(path,items):
    t=Path(path).read_text(errors="replace")
    return {x:(x in t) for x in items}
def emit(e,**kw):
    row={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"event":e,**kw}
    print("LOUKSNA_P04_TELEMETRY "+json.dumps(row,sort_keys=True),flush=True)
def main():
    if not AUTH.is_file(): raise SystemExit("P04_LOUKSNA_MISSING")
    if not PUAC.is_file(): raise SystemExit("P04_PUAC2_MISSING")
    # Preserve the same CUSTOSZ preflight contract proven by P03.
    c=os.environ.get("CUSTOSZ_WORKSPACE_OVERRIDE")
    if not c: raise SystemExit("P04_CUSTOSZ_WORKSPACE_UNDECLARED")
    emit("P04_START",parent_checkpoint="CHECKPOINT_03",next_point="P05")
    mailbox=Path(c)
    emit("CUSTOSZ_WORKSPACE_CHECK",exists=mailbox.is_dir())
    if not mailbox.is_dir(): raise SystemExit("P04_CUSTOSZ_WORKSPACE_MISSING")
    # Material evidence already present in the mission substrate.
    master=ROOT/"scripts/missions/louksna_zd_v04_master_live.py"
    bridge_core=ROOT/"bridge/lrb_core.py"
    inv={
      "p04_master_inventory":markers(master,["inventory["P04"]","CREATE TABLE IF NOT EXISTS evidence","INSERT INTO evidence"]),
      "bridge_ledger":markers(bridge_core,["EvidenceLedger","entry_hash"])
    }
    emit("P04_MATERIAL_EVIDENCE_RECONCILED",inventory=inv)
    if not all(inv["p04_master_inventory"].values()): raise SystemExit("P04_EVENT_LOG_EVIDENCE_MISSING")
    if not all(inv["bridge_ledger"].values()): raise SystemExit("P04_LEDGER_EVIDENCE_MISSING")
    result={
      "status":"PASS","checkpoint":"CHECKPOINT_04","next_point":"P05",
      "transition_id":"P04-CHECKPOINT-TO-P05-001",
      "g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED",
      "certified":False,"active":False,"material_evidence":inv
    }
    (ROOT/"continuity"/"CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    emit("CHECKPOINT_04_REACHED",state="PASS",next_point="P05",certified=False)
if __name__=="__main__": raise SystemExit(main())
