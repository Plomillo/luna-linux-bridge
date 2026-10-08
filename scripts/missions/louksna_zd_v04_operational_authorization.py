#!/usr/bin/env python3
from __future__ import annotations
import json,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"continuity/runtime-evidence/authorization"; OUT.mkdir(parents=True,exist_ok=True)
def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    post=ROOT/"continuity/runtime-evidence/post_g24/POST_G24_VALIDATION.json"
    failures=[]; checks=[]
    ok=state.get("certified") is True and state.get("current_checkpoint")=="POST_G24_VALIDATION" and result.get("status")=="PASS"
    checks.append({"test":"CERTIFIED_POST_G24_GATE","status":"PASS" if ok else "FAIL"})
    if not ok: failures.append("AUTH_CERTIFICATION_GATE_FAILED")
    if not post.is_file(): failures.append("AUTH_POST_G24_EVIDENCE_MISSING")
    else:
        e=json.loads(post.read_text()); ok=e.get("status")=="PASS" and not e.get("failures")
        checks.append({"test":"POST_G24_VALIDATION","status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("AUTH_POST_G24_VALIDATION_FAILED")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    checks.append({"test":"SOURCE_IDENTITY","status":"PASS","commit":head})
    evidence={"schema":"LOUKSNA_ZD_SEPARATE_OPERATIONAL_AUTHORIZATION/1.0","status":"PASS" if not failures else "HOLD","timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_commit":head,"checks":checks,"failures":failures,"authorization":"OPERATIONAL_POSTBOOT_AUTHORIZED" if not failures else "DENIED","active":"FORBIDDEN"}
    (OUT/"OPERATIONAL_AUTHORIZATION.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\\n")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"POST_G24_VALIDATION","next_point":"SEPARATE_OPERATIONAL_AUTHORIZATION","transition_id":"AUTH-HOLD-NEW-EVIDENCE-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"SEPARATE_OPERATIONAL_AUTHORIZATION","parent_checkpoint":"POST_G24_VALIDATION","next_point":"POSTBOOT_VERIFICATION","transition_id":"AUTH-TO-POSTBOOT-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"\\n")
    print("LOUKSNA_AUTH_TELEMETRY "+json.dumps({"status":out["status"],"next_point":out["next_point"],"failures":failures},sort_keys=True),flush=True)
if __name__=="__main__": main()
