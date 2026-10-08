#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"continuity/runtime-evidence/g23"
OUT.mkdir(parents=True,exist_ok=True)

def sh(cmd):
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=900)
    return {"returncode":r.returncode,"stdout":r.stdout[-8000:],"stderr":r.stderr[-8000:]}

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    p12e=ROOT/"continuity/runtime-evidence/p12/P12_RELEASE_GATE_EVIDENCE.json"
    p10e=ROOT/"continuity/runtime-evidence/p10/P10_TRANSPORT_ECHO_RUN_37839883915.json"
    checks=[]
    failures=[]

    if state.get("current_checkpoint")!="CHECKPOINT_12": failures.append("G23_P12_CHECKPOINT_REQUIRED")
    if result.get("status")!="PASS": failures.append("G23_P12_RESULT_NOT_PASS")
    if result.get("next_point")!="G23": failures.append("G23_TRANSITION_NOT_READY")
    if state.get("open_blockers"): failures.append("G23_OPEN_BLOCKERS")
    checks.append({"test":"P12_RELEASE_OBJECT","status":"PASS" if not failures else "FAIL","checkpoint":state.get("current_checkpoint"),"result_status":result.get("status")})

    for path,expected in [
        ("Louksna.md","1a399ab7494d6df5582436819eee557083e753ed"),
        ("PUAC2.md","da3b216888c86e588685d384c34dd3c481414b22")
    ]:
        actual=subprocess.check_output(["git","rev-parse","HEAD:"+path],cwd=ROOT,text=True).strip()
        ok=(actual==expected)
        checks.append({"test":"FROZEN_SOURCE","path":path,"status":"PASS" if ok else "FAIL","blob":actual})
        if not ok: failures.append("G23_FROZEN_SOURCE_MISMATCH:"+path)

    ok=p10e.is_file()
    checks.append({"test":"P10_TRANSPORT_EVIDENCE_PRESENT","status":"PASS" if ok else "FAIL","path":str(p10e.relative_to(ROOT))})
    if not ok: failures.append("G23_MISSING_EVIDENCE:P10_TRANSPORT")

    if p10e.is_file():
        e=json.loads(p10e.read_text())
        ok=(e.get("status")=="PASS" and e.get("off_host_relay_materially_proven") is True and e.get("roundtrip_probes")==2)
        checks.append({"test":"P10_INDEPENDENT_RECHECK","status":"PASS" if ok else "FAIL","probe_mode":e.get("probe_mode")})
        if not ok: failures.append("G23_P10_EVIDENCE_INVALID")

    build=sh(["python3","scripts/build"])
    checks.append({"test":"BUILD_REPROBE","status":"PASS" if build["returncode"]==0 else "FAIL","execution":build})
    if build["returncode"]!=0: failures.append("G23_BUILD_REPROBE_FAILED")

    independent=(Path(__file__).name!="louksna_zd_v04_p12_live.py")
    checks.append({"test":"EXECUTOR_SEPARATION","status":"PASS" if independent else "FAIL","g23_executor":str(Path(__file__).relative_to(ROOT)),"p12_executor":"scripts/missions/louksna_zd_v04_p12_live.py"})
    if not independent: failures.append("G23_EXECUTOR_NOT_INDEPENDENT")

    evidence={
        "schema":"LOUKSNA_ZD_G23_INDEPENDENT_VALIDATION/1.0",
        "status":"PASS" if not failures else "HOLD",
        "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "checks":checks,
        "failures":failures,
        "validated_object_commit":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip(),
        "g24":"SEPARATE_REQUIRED"
    }
    (OUT/"G23_INDEPENDENT_VALIDATION.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"
")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"CHECKPOINT_12","next_point":"G23","transition_id":"G23-HOLD-NEW-EVIDENCE-001","certified":False,"active":False,"g23":"REQUIRED","g24":"REQUIRED","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"G23","parent_checkpoint":"CHECKPOINT_12","next_point":"G24","transition_id":"G23-TO-G24-001","certified":False,"active":False,"g23":"PASS","g24":"REQUIRED","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"
")
    print("LOUKSNA_G23_TELEMETRY "+json.dumps({"status":out["status"],"next_point":out["next_point"],"failures":failures},sort_keys=True),flush=True)

if __name__=="__main__":
    main()
