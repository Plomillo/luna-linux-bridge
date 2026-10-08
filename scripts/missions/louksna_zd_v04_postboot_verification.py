#!/usr/bin/env python3
from __future__ import annotations
import json,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/"continuity/runtime-evidence/postboot"; OUT.mkdir(parents=True,exist_ok=True)
def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text()); result=json.loads((ROOT/"continuity/CONTINUATION_RESULT.json").read_text())
    auth=ROOT/"continuity/runtime-evidence/authorization/OPERATIONAL_AUTHORIZATION.json"
    failures=[]; checks=[]
    if not auth.is_file(): failures.append("POSTBOOT_AUTHORIZATION_MISSING")
    else:
        e=json.loads(auth.read_text()); ok=e.get("status")=="PASS" and e.get("authorization")=="OPERATIONAL_POSTBOOT_AUTHORIZED"
        checks.append({"test":"OPERATIONAL_AUTHORIZATION","status":"PASS" if ok else "FAIL"})
        if not ok: failures.append("POSTBOOT_AUTHORIZATION_INVALID")
    test=subprocess.run(["python3","-B","-m","unittest","bridge/tests/test_mtls_gateway.py"],cwd=ROOT,text=True,capture_output=True,timeout=900)
    checks.append({"test":"POSTBOOT_FRESH_PROCESS","status":"PASS" if test.returncode==0 else "FAIL","returncode":test.returncode,"stdout":test.stdout[-6000:],"stderr":test.stderr[-6000:]})
    if test.returncode!=0: failures.append("POSTBOOT_FRESH_PROCESS_FAILED")
    head=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
    evidence={"schema":"LOUKSNA_ZD_POSTBOOT_VERIFICATION/1.0","status":"PASS" if not failures else "HOLD","timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"source_commit":head,"checks":checks,"failures":failures,"active":"FORBIDDEN_FROM_CI"}
    (OUT/"POSTBOOT_VERIFICATION.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"
")
    if failures:
        out={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"SEPARATE_OPERATIONAL_AUTHORIZATION","next_point":"POSTBOOT_VERIFICATION","transition_id":"POSTBOOT-HOLD-NEW-EVIDENCE-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","open_blockers":failures,"material_evidence":evidence}
    else:
        out={"status":"PASS","checkpoint":"POSTBOOT_VERIFICATION","parent_checkpoint":"SEPARATE_OPERATIONAL_AUTHORIZATION","next_point":"ACTIVE_AUTHORIZATION_REVIEW","transition_id":"POSTBOOT-TO-ACTIVE-REVIEW-001","certified":True,"active":False,"g23":"PASS","g24":"PASS","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(out,indent=2,sort_keys=True)+"
")
    print("LOUKSNA_POSTBOOT_TELEMETRY "+json.dumps({"status":out["status"],"next_point":out["next_point"],"failures":failures},sort_keys=True),flush=True)
if __name__=="__main__": main()
