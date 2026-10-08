#!/usr/bin/env python3
from __future__ import annotations
import json,time,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"continuity/runtime-evidence/active-review"; OUT.mkdir(parents=True,exist_ok=True)
def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    required={
      "g23":ROOT/"continuity/runtime-evidence/g23/G23_INDEPENDENT_VALIDATION.json",
      "g24":ROOT/"continuity/runtime-evidence/g24/G24_CERTIFICATION_DECISION.json",
      "post":ROOT/"continuity/runtime-evidence/post_g24/POST_G24_VALIDATION.json",
      "auth":ROOT/"continuity/runtime-evidence/authorization/OPERATIONAL_AUTHORIZATION.json",
      "postboot":ROOT/"continuity/runtime-evidence/postboot/POSTBOOT_VERIFICATION.json",
    }
    failures=[]; checks=[]
    if state.get("current_checkpoint")!="POSTBOOT_VERIFICATION": failures.append("ACTIVE_REVIEW_CHECKPOINT_INVALID")
    for label,path in required.items():
        ok=path.is_file()
        checks.append({"test":label.upper()+"_EVIDENCE","status":"PASS" if ok else "FAIL","path":str(path.relative_to(ROOT))})
        if not ok: failures.append("ACTIVE_REVIEW_MISSING:"+label)
    if not failures:
        for label in ("g23","g24","post","auth","postboot"):
            e=json.loads(required[label].read_text())
            if e.get("status")!="PASS": failures.append("ACTIVE_REVIEW_"+label.upper()+"_NOT_PASS")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    evidence={"schema":"LOUKSNA_ZD_ACTIVE_AUTHORIZATION_REVIEW/1.0","status":"PASS" if not failures else "HOLD","timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_commit":head,"checks":checks,"failures":failures,"certified":not bool(failures),"active":False,"activation":"EXPLICIT_EXTERNAL_OPERATIONAL_ACTIVATION_REQUIRED"}
    (OUT/"ACTIVE_AUTHORIZATION_REVIEW.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"
")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"POSTBOOT_VERIFICATION","next_point":"ACTIVE_AUTHORIZATION_REVIEW","transition_id":"ACTIVE-REVIEW-HOLD-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"ACTIVE_AUTHORIZATION_REVIEW","parent_checkpoint":"POSTBOOT_VERIFICATION","next_point":"NONE","transition_id":"ACTIVE-REVIEW-READY-001","certified":True,"active":False,"terminal":True,"operationally_ready":True,"material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"
")
    print("LOUKSNA_ACTIVE_REVIEW_TELEMETRY "+json.dumps({"status":out["status"],"terminal":out.get("terminal",False),"operationally_ready":out.get("operationally_ready",False)},sort_keys=True),flush=True)
if __name__=="__main__": main()
