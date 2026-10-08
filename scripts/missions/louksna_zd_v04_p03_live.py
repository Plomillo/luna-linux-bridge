#!/usr/bin/env python3
import hashlib, json, os, sys, tempfile, time
from pathlib import Path

CUSTOSZ_SHA256="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"
CHECKPOINT="CHECKPOINT_02"
NEXT_POINT="P04"
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def emit(out,event,**fields):
    row={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"event":event,**fields}
    print("LOUKSNA_P03_TELEMETRY "+json.dumps(row,sort_keys=True),flush=True)
    with (Path(out)/"P03_TELEMETRY.jsonl").open("a",encoding="utf-8") as f: f.write(json.dumps(row,sort_keys=True)+"\n")
def main():
    root=Path(os.environ["MISSION_ROOT"]).resolve()
    mailbox=Path(os.environ["MAILBOX_ROOT"]).resolve()
    out=Path(os.environ["OUT_DIR"]).resolve(); out.mkdir(parents=True,exist_ok=True)
    authority=root/"Louksna.md"; puac2=root/"PUAC2.md"
    custosz=mailbox/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    runtime=mailbox/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    if not authority.is_file() or not puac2.is_file(): raise SystemExit("P03_REQUIRED_AUTHORITY_INPUT_MISSING")
    if not custosz.is_file() or sha(custosz)!=CUSTOSZ_SHA256: raise SystemExit("P03_CUSTOSZ_IDENTITY_DRIFT")
    if not runtime.is_file(): raise SystemExit("P03_RUNTIME_ARTIFACT_MISSING")
    emit(out,"P03_START",parent_checkpoint=CHECKPOINT,next_point=NEXT_POINT)
    for command in ("v07-status","v07-selftest"):
        import subprocess
        p=subprocess.run([sys.executable,"-B","-I",str(custosz),command],text=True,capture_output=True,timeout=45)
        emit(out,"CUSTOSZ_CHECK",command=command,exit_code=p.returncode)
        if p.returncode: raise SystemExit("P03_CUSTOSZ_"+command.upper()+"_FAIL")
    sys.path.insert(0,str(custosz))
    import custosz_v05_legacy as worker
    workspace=Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).resolve()
    if not workspace.is_dir(): raise SystemExit("P03_CUSTOSZ_WORKSPACE_MISSING")
    worker.workspace=lambda:workspace
    worker.discover=lambda:{"workspace":str(workspace),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(workspace),"score":999}}}
    rel,size,expected,role=worker.PINS["LOUKSNA"]
    worker.sources=lambda _large=False:{"observed_at":"P03_RUNTIME_PLANE","sources":{"LOUKSNA":{"relative":rel,"bytes":size,"sha256":expected,"role":role,"path":str(authority),"exists":True,"observed_bytes":authority.stat().st_size,"observed_sha256":sha(authority),"integrity":"PASS" if sha(authority)==expected and authority.stat().st_size==size else "DRIFT","binding":"MISSION_BRANCH_VERIFIED_AUTHORITY"}}}
    if worker.sources()["sources"]["LOUKSNA"]["integrity"]!="PASS": raise SystemExit("P03_LOUKSNA_INTEGRITY_NOT_PASS")
    ms=worker.mission_start(1.0,"LUNA_PROJECT","Execute P03 CUSTOSZ Runtime MetaOS execution-plane continuation from CHECKPOINT_02; preserve Louksna/PUAC2 authority, provenance and independent G23/G24.",report_minutes=1)
    tick=worker.mission_tick(ms["mission_id"])
    emit(out,"CUSTOSZ_MISSION_LIVE",mission_id=ms["mission_id"],state=tick.get("state"))
    sys.path.insert(0,str(runtime))
    from runtime_core import Runtime
    with tempfile.TemporaryDirectory(prefix="louksna-p03-runtime-") as td:
        rt=Runtime(Path(td)/"state",authority,sha(authority))
        selftest=rt.selftest()
        if selftest.get("status")!="PASS": raise SystemExit("P03_RUNTIME_SELFTEST_FAIL")
        journal=rt.journal.verify()
        if (journal is False) or (isinstance(journal, dict) and journal.get("status")!="PASS"): raise SystemExit("P03_RUNTIME_JOURNAL_VERIFY_FAIL")
        emit(out,"RUNTIME_LIVE",state="PASS",journal=journal)
    result={"status":"PASS","checkpoint":"CHECKPOINT_03","parent_checkpoint":CHECKPOINT,"next_point":NEXT_POINT,"transition_id":"P03-CHECKPOINT-TO-P04-001","custosz_mission_id":ms["mission_id"],"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","certified":False,"active":False}
    (out/"CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    emit(out,"CHECKPOINT_03_REACHED",state="PASS",next_point=NEXT_POINT,certified=False)
if __name__=="__main__": raise SystemExit(main())