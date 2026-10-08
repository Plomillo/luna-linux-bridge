#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,subprocess,time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"continuity/runtime-evidence/g24"
OUT.mkdir(parents=True,exist_ok=True)

def sh(cmd):
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=900)
    return {"returncode":r.returncode,"stdout":r.stdout[-8000:],"stderr":r.stderr[-8000:]}

def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    g23p=ROOT/"continuity/runtime-evidence/g23/G23_INDEPENDENT_VALIDATION.json"
    p10p=ROOT/"continuity/runtime-evidence/p10/P10_TRANSPORT_ECHO_RUN_37839883915.json"
    failures=[]; checks=[]

    if state.get("next_point")!="G24": failures.append("G24_TRANSITION_NOT_READY")
    if state.get("current_checkpoint")!="G23": failures.append("G24_G23_CHECKPOINT_REQUIRED")
    if result.get("status")!="PASS" or result.get("g23")!="PASS": failures.append("G24_G23_RESULT_NOT_PASS")

    if not g23p.is_file(): failures.append("G24_G23_EVIDENCE_MISSING")
    else:
        e=json.loads(g23p.read_text())
        ok=e.get("status")=="PASS" and not e.get("failures")
        checks.append({"test":"G23_INDEPENDENT_VALIDATION_EVIDENCE","status":"PASS" if ok else "FAIL","source":str(g23p.relative_to(ROOT))})
        if not ok: failures.append("G24_G23_EVIDENCE_INVALID")

    if not p10p.is_file(): failures.append("G24_P10_EVIDENCE_MISSING")
    else:
        e=json.loads(p10p.read_text())
        ok=e.get("status")=="PASS" and e.get("off_host_relay_materially_proven") is True
        checks.append({"test":"TRANSPORT_EVIDENCE_RECHECK","status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("G24_TRANSPORT_RECHECK_FAILED")

    for path,expected in [
        ("Louksna.md","1a399ab7494d6df5582436819eee557083e753ed"),
        ("PUAC2.md","da3b216888c86e588685d384c34dd3c481414b22")
    ]:
        actual=subprocess.check_output(["git","rev-parse","HEAD:"+path],cwd=ROOT,text=True).strip()
        ok=actual==expected
        checks.append({"test":"FROZEN_SOURCE_RECHECK","path":path,"status":"PASS" if ok else "FAIL","blob":actual})
        if not ok: failures.append("G24_FROZEN_SOURCE_MISMATCH:"+path)

    build=sh(["python3","scripts/build"])
    checks.append({"test":"BUILD_RECHECK","status":"PASS" if build["returncode"]==0 else "FAIL","execution":build})
    if build["returncode"]!=0: failures.append("G24_BUILD_RECHECK_FAILED")

    separation=("scripts/missions/louksna_zd_v04_g23_independent_validation.py"!="scripts/missions/louksna_zd_v04_g24_certification.py")
    checks.append({"test":"G23_G24_EXECUTOR_SEPARATION","status":"PASS" if separation else "FAIL"})
    if not separation: failures.append("G24_EXECUTOR_NOT_INDEPENDENT")

    evidence={
        "schema":"LOUKSNA_ZD_G24_CERTIFICATION/1.0",
        "status":"PASS" if not failures else "HOLD",
        "decision":"CERTIFIED_FOR_POST_VALIDATION" if not failures else "CERTIFICATION_DENIED",
        "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
        "checks":checks,
        "failures":failures,
        "g23_evidence":str(g23p.relative_to(ROOT)),
        "certified_claim":"P12_RELEASE_OBJECT" if not failures else None,
        "activation":"FORBIDDEN_UNTIL_POST_VALIDATION_AND_OPERATIONAL_AUTHORIZATION"
    }
    (OUT/"G24_CERTIFICATION_DECISION.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"G23","next_point":"G24","transition_id":"G24-HOLD-NEW-EVIDENCE-001","certified":False,"active":False,"g23":"PASS","g24":"REQUIRED","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"G24","parent_checkpoint":"G23","next_point":"POST_G24_VALIDATION","transition_id":"G24-TO-POST-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"
")
    print("LOUKSNA_G24_TELEMETRY "+json.dumps({"status":out["status"],"next_point":out["next_point"],"certified":out["certified"],"failures":failures},sort_keys=True),flush=True)

if __name__=="__main__":
    main()
