#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,tempfile
from pathlib import Path

MISSION_REL="missions/inbox/document-factory-custosz-v7-continuation-20261005/MISSION_ORIGINAL.md"
MISSION_SHA="5fa6287ac594c82234a78b7c6e8934bb41ce2f88e236df3e1ec0b4da9c93aee7"
CERTIFIED="067e1be0b13d9400c2c78d6174138c10ce980dd7"

def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,timeout=60):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if p.returncode: raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-3000:]+"\n"+p.stderr[-3000:])
    return p.stdout.strip()

def main():
    root=Path(os.environ["MISSION_ROOT"]).resolve()
    target_root=Path(os.environ["TARGET_ROOT"]).resolve()
    main_root=Path(os.environ["MAIN_ROOT"]).resolve()
    outdir=Path(os.environ["OUT_DIR"]).resolve(); outdir.mkdir(parents=True,exist_ok=True)
    mission=root/MISSION_REL
    custosz=root/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    runtime=root/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    authority=root/"Louksna.md"
    census=root/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json"
    executor=root/"scripts/missions/document_factory_finish_materializer.py"

    if sha(mission)!=MISSION_SHA: raise SystemExit("MISSION_SHA_MISMATCH")
    head=run(["git","-C",str(target_root),"rev-parse","HEAD"])
    p=subprocess.run(["git","-C",str(target_root),"merge-base","--is-ancestor",CERTIFIED,head])
    if p.returncode: raise SystemExit("TARGET_NOT_DESCENDANT_OF_CERTIFIED_CHECKPOINT")
    if head==CERTIFIED: raise SystemExit("FIRST_TRANCHE_REQUIRED_BEFORE_FINISH")

    c=json.loads(census.read_text(encoding="utf-8"))
    if (c.get("family_count"),c.get("capability_count"),c.get("unique_capability_count"))!=(9,72,72): raise SystemExit("CUSTOSZ_CENSUS_INVALID")
    worker_checks={}
    for command in ("v07-status","v07-selftest"):
        p=subprocess.run([sys.executable,"-B","-I",str(custosz),command],text=True,capture_output=True,timeout=30)
        worker_checks[command]={"exit_code":p.returncode,"stdout":p.stdout[-6000:],"stderr":p.stderr[-2000:]}
        if p.returncode: raise SystemExit("CUSTOSZ_"+command+"_FAILED")

    workspace=Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).resolve()
    if not workspace.is_dir(): raise SystemExit("CUSTOSZ_WORKSPACE_OVERRIDE_MISSING")
    state=Path.home()/".local/state/louksna"/("document-factory-finish-"+os.environ.get("GITHUB_RUN_ID","manual"))
    state.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"]=str(workspace); os.environ["CUSTOSZ_STATE_DIR"]=str(state)

    sys.path.insert(0,str(custosz))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}
    worker.workspace=lambda: workspace
    worker.discover=lambda:{"workspace":str(workspace),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(workspace),"score":999}}}
    def sources(_large=False):
        observed=sha(authority); st=authority.stat()
        rel,size,expected,role=worker.PINS["LOUKSNA"]
        return {"observed_at":"MAILBOX_VERIFIED","sources":{"LOUKSNA":{"relative":rel,"bytes":size,"sha256":expected,"role":role,"path":str(authority),"exists":True,"observed_bytes":st.st_size,"observed_sha256":observed,"integrity":"PASS" if observed==expected and st.st_size==size else "DRIFT","binding":"MAILBOX_VERIFIED_REPOSITORY_AUTHORITY"}}}
    worker.sources=sources
    mission_state=worker.mission_start(
        600/3600.0,"LUNA_PROJECT",
        "DOCUMENT_FACTORY_GOVERNED_CONTINUATION_V1 completion; hard_ceiling=600s; continue_without_voluntary_idle; nine CUSTOSZ families as pertinent; main=dependency/download dispatch; Desktop Commander forbidden; fail closed; no certification propagation.",
        report_minutes=1
    )
    tick=worker.mission_tick(mission_state["mission_id"])

    with tempfile.TemporaryDirectory(prefix="document-factory-finish-") as td:
        tmp=Path(td); sys.path.insert(0,str(runtime))
        from runtime_core import Runtime,ExecutorAdapter,TimeBudgetController
        from sr_exec_bound_fme_01 import SRExecBoundFME01
        rt=Runtime(tmp/"runtime",authority,sha(authority))
        selftest=rt.selftest()
        if selftest.get("status")!="PASS": raise SystemExit("RUNTIME_SELFTEST_FAILED")
        rt.budget=TimeBudgetController(520); rt.mission.transition("PRECHECK")
        eid="CUSTOSZ_V7_DOCUMENT_FACTORY_FINISH"
        rt.executors.register(ExecutorAdapter(eid,"LOCAL_SUBPROCESS",sys.executable,capabilities={"DOCUMENT_FACTORY_COMPLETION":1.0}))
        checkpoint=rt.checkpoints.capture_file("DOCUMENT_FACTORY_MISSION_SOURCE",mission)
        result_file=outdir/"MATERIAL_RESULT.json"
        spec={
          "mission_id":mission_state["mission_id"],"mission_spec_digest":sha(mission),
          "required_abilities":{"DOCUMENT_FACTORY_COMPLETION":1.0},
          "authority_context":{"authority":"Louksna.md","sha256":sha(authority)},
          "policy_context":{"policy_id":"DOCUMENT_FACTORY_CUSTOSZ_V7_FINISH","scope":"DOCUMENT_FACTORY_WORK_BRANCH_ONLY","allow":True},
          "execution_payload_digest":sha(executor),
          "expected_effect":{"target":str(result_file),"effect_type":"DOCUMENT_FACTORY_WORK_BRANCH_COMPLETION"},
          "checkpoint_pointer":checkpoint["checkpoint_id"],"runtime_digest":sha(runtime),"mission_state":"DISPATCH_READY",
          "executor_metadata":{eid:{"identity_valid":True,"provenance_valid":True,"digest":sha(Path(sys.executable))}},
          "executor_policy":{eid:{"permissions_valid":True,"resource_envelope_valid":True,"policy_allow":True,"risk":0,"cost":0}},
          "probe_argv":{eid:["{COMMAND}","-B","-I","-c","import sys;sys.exit(0)"]},
          "dispatch":{"cwd":str(tmp),"argv_template":["{COMMAND}","-B","-I",str(executor),"{DISPATCH_PATH}","{ACK_PATH}","{FME_PATH}","{TARGET}",str(root),str(target_root),str(main_root),str(census)],"timeout_s":450,"ack_timeout_s":20,"fme_timeout_s":40}
        }
        rr=SRExecBoundFME01(rt).establish_material_execution(spec)
        report={"schema":"DOCUMENT_FACTORY_CUSTOSZ_RUNTIME_FINISH/1.0","status":"PASS" if rr.get("result")=="PASS" else "FAIL","custosz_mission_id":mission_state["mission_id"],"heartbeat_state":tick.get("state"),"custosz_checks":worker_checks,"runtime_selftest":selftest,"runtime_dispatch":{k:rr.get(k) for k in ("result","global_step_gate","material_execution_proven","evidence_chain_head")},"runtime_evidence_ledger":rt.journal.verify(),"family_count":9,"capability_count":72,"target_head_before":head,"main_dispatch_sha":run(["git","-C",str(main_root),"rev-parse","HEAD"]),"certified_checkpoint_sha":CERTIFIED,"desktop_commander":"FORBIDDEN","hard_ceiling_seconds":600,"certification_propagated":False}
        (outdir/"CUSTOSZ_RUNTIME_FINISH_RESULT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        if report["status"]!="PASS": raise SystemExit("RUNTIME_MATERIAL_FINISH_FAILED")
        print(json.dumps({"status":"CUSTOSZ_V7_RUNTIME_FINISH_WORKING","mission_id":mission_state["mission_id"],"material_execution_proven":rr.get("material_execution_proven"),"global_step_gate":rr.get("global_step_gate")},sort_keys=True))
if __name__=="__main__": main()
