#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,time
from pathlib import Path
ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
MAILBOX=Path(os.environ["MAILBOX_ROOT"]).resolve()
AUTH=ROOT/"Louksna.md"; PUAC=ROOT/"PUAC2.md"; OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence")); OUT.mkdir(parents=True,exist_ok=True)
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"; BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b2"
def gitshow(sha,path): return subprocess.run(["git","show",f"{sha}:{path}"],cwd=ROOT,text=True,capture_output=True,check=True).stdout
def markers(p,items):
    t=Path(p).read_text(encoding="utf-8",errors="replace")
    return {x:(x in t) for x in items}
def emit(e,**kw):
    row={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"event":e,**kw}; print("LOUKSNA_P04_TELEMETRY "+json.dumps(row,sort_keys=True),flush=True)
def main():
    if not AUTH.is_file() or not PUAC.is_file(): raise SystemExit("P04_REQUIRED_AUTHORITY_INPUT_MISSING")
    subprocess.run(["git","cat-file","-e",V03_SHA+"^{commit}"],cwd=ROOT,check=True)
    subprocess.run(["git","cat-file","-e",BRIDGE_SHA+"^{commit}"],cwd=ROOT,check=True)
    custosz=MAILBOX/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    if not custosz.is_file(): raise SystemExit("P04_CUSTOSZ_ARTIFACT_MISSING")
    emit("P04_START",parent_checkpoint="CHECKPOINT_03",next_point="P05",v03_head=V03_SHA,bridge_head=BRIDGE_SHA)
    for command in ("v07-status","v07-selftest"):
        p=subprocess.run([sys.executable,"-B","-I",str(custosz),command],text=True,capture_output=True,timeout=45)
        emit("CUSTOSZ_CHECK",command=command,exit_code=p.returncode)
        if p.returncode: raise SystemExit("P04_CUSTOSZ_"+command.upper()+"_FAIL")
    v03_text=gitshow(V03_SHA,"scripts/missions/v03_templates/main.rs")
    bridge_text=gitshow(BRIDGE_SHA,"bridge/lrb_core.py")
    inv={
      "v03_event_log":{"CREATE TABLE IF NOT EXISTS evidence":"CREATE TABLE IF NOT EXISTS evidence" in v03_text,"INSERT INTO evidence":"INSERT INTO evidence" in v03_text},
      "bridge_ledger":{"EvidenceLedger":"EvidenceLedger" in bridge_text,"entry_hash":"entry_hash" in bridge_text}
    }
    emit("P04_MATERIAL_EVIDENCE_RECONCILED",inventory=inv)
    if not all(inv["v03_event_log"].values()): raise SystemExit("P04_EVENT_LOG_EVIDENCE_MISSING")
    if not all(inv["bridge_ledger"].values()): raise SystemExit("P04_LEDGER_EVIDENCE_MISSING")
    result={"status":"PASS","checkpoint":"CHECKPOINT_04","parent_checkpoint":"CHECKPOINT_03","next_point":"P05","transition_id":"P04-CHECKPOINT-TO-P05-001","v03_head":V03_SHA,"bridge_head":BRIDGE_SHA,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","certified":False,"active":False,"material_evidence":inv}
    (ROOT/"continuity"/"CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("CHECKPOINT_04_REACHED",state="PASS",next_point="P05",certified=False)
if __name__=="__main__": raise SystemExit(main())
