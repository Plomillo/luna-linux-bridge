#!/usr/bin/env python3
import hashlib, json, os, subprocess, sys, time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
MAILBOX=Path(os.environ["MAILBOX_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence")).resolve()
OUT.mkdir(parents=True,exist_ok=True)
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"
BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b"

def emit(event,**kw):
    row={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"event":event,**kw}
    print("LOUKSNA_P05_TELEMETRY "+json.dumps(row,sort_keys=True),flush=True)

def main():
    auth=ROOT/"Louksna.md"; puac=ROOT/"PUAC2.md"
    if not auth.is_file() or not puac.is_file(): raise SystemExit("P05_AUTHORITY_INPUT_MISSING")
    subprocess.run(["git","cat-file","-e",V03_SHA+"^{commit}"],cwd=ROOT,check=True)
    subprocess.run(["git","cat-file","-e",BRIDGE_SHA+"^{commit}"],cwd=ROOT,check=True)
    emit("P05_START",parent_checkpoint="CHECKPOINT_04",next_point="P06",v03_head=V03_SHA,bridge_head=BRIDGE_SHA)

    v03_text=subprocess.run(["git","show",V03_SHA+":scripts/missions/v03_templates/main.rs"],cwd=ROOT,text=True,capture_output=True,check=True).stdout
    bridge_text=subprocess.run(["git","show",BRIDGE_SHA+":bridge/lrb_core.py"],cwd=ROOT,text=True,capture_output=True,check=True).stdout
    substrate={
      "v03_event_evidence_table":"CREATE TABLE IF NOT EXISTS evidence" in v03_text,
      "v03_event_insert":"INSERT INTO evidence" in v03_text,
      "bridge_EvidenceLedger":"EvidenceLedger" in bridge_text,
      "bridge_entry_hash":"entry_hash" in bridge_text
    }
    if not all(substrate.values()): raise SystemExit("P05_EVIDENCE_SUBSTRATE_FAIL")
    emit("P05_EVIDENCE_SUBSTRATE_VERIFIED",checks=substrate)

    sys.path.insert(0,str(ROOT/"scripts/missions"))
    from louksna_zd_v04_artifact_transfer import run_p05_selftest
    report=run_p05_selftest(OUT)
    if report.get("status")!="PASS": raise SystemExit("P05_TRANSFER_SELFTEST_FAIL")
    negative=report.get("negative",{})
    required={"false_mime","oversized","path_traversal","symlink","corrupt_hash","ack_missing","provenance_missing"}
    if not required.issubset(negative) or not all(bool(negative[k]) for k in required):
        raise SystemExit("P05_NEGATIVE_CONTROLS_INCOMPLETE")
    emit("P05_TRANSFER_PIPELINE_VERIFIED",pipeline=report["pipeline"],positive=report["positive"],negative=negative,sha256=report["sha256"],size=report["size"])

    result={
      "status":"PASS","checkpoint":"CHECKPOINT_05","parent_checkpoint":"CHECKPOINT_04",
      "next_point":"P06","transition_id":"P05-CHECKPOINT-TO-P06-001",
      "v03_head":V03_SHA,"bridge_head":BRIDGE_SHA,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED",
      "certified":False,"active":False,
      "material_evidence":{"substrate":substrate,"artifact_transfer":report},
      "scope":"P05 governed attachment transfer operational closure; P06 remains next."
    }
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit("CHECKPOINT_05_REACHED",state="PASS",next_point="P06",certified=False)
    return 0

if __name__=="__main__": raise SystemExit(main())
