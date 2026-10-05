#!/usr/bin/env python3
import hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path

ACTIVE_SHA="43a82aa30607b8775c998fa39b2bc08bfc2a263f"
ACTIVE_DIGEST="b0c59f37c70e58ca42f7fd215fad890e9a24b255d369110665e7141f26f57404"
PRECERT_CANDIDATE_SHA="3774cb102ad6318fc824b2cb87c5055e9f5f4b0b"
PRECERT_CANDIDATE_REF="refs/heads/candidate/document-factory-v1-ffprobe-20261005"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,timeout=60):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-3000:]+"\n"+p.stderr[-3000:])
    return p.stdout.strip()

def main():
    main_root=Path(os.environ["MAIN_ROOT"]).resolve()
    target_root=Path(os.environ["TARGET_ROOT"]).resolve()
    mailbox_root=Path(os.environ["MAILBOX_ROOT"]).resolve()
    outdir=Path(os.environ["OUT_DIR"]).resolve(); outdir.mkdir(parents=True,exist_ok=True)

    mission=main_root/"missions/document-factory-ffprobe-admission-20261005/MISSION.md"
    executor=main_root/"scripts/missions/document_factory_ffprobe_executor.py"
    custosz=mailbox_root/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    runtime=mailbox_root/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    census=mailbox_root/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json"
    authority=main_root/"Louksna.md"
    ledger=main_root/"operational-authorizations/document-factory/CURRENT.json"

    if run(["git","-C",str(target_root),"rev-parse","HEAD"])!=ACTIVE_SHA:
        raise SystemExit("ACTIVE_TARGET_SHA_DRIFT")
    led=json.loads(ledger.read_text(encoding="utf-8"))
    if not (led.get("active_authorized") is True and led.get("candidate_head_sha")==ACTIVE_SHA and led.get("candidate_digest_sha256")==ACTIVE_DIGEST):
        raise SystemExit("ACTIVE_LEDGER_NOT_EXACT")
    c=json.loads(census.read_text(encoding="utf-8"))
    if (c.get("family_count"),c.get("capability_count"),c.get("unique_capability_count"))!=(9,72,72):
        raise SystemExit("CUSTOSZ_CENSUS_INVALID")

    checks={}
    for command in ("v07-status","v07-selftest"):
        p=subprocess.run([sys.executable,"-B","-I",str(custosz),command],text=True,capture_output=True,timeout=30)
        checks[command]={"exit_code":p.returncode,"stdout":p.stdout[-5000:],"stderr":p.stderr[-2000:]}
        if p.returncode: raise SystemExit("CUSTOSZ_"+command+"_FAILED")

    workspace=Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).resolve()
    if not workspace.is_dir(): raise SystemExit("CUSTOSZ_WORKSPACE_OVERRIDE_MISSING")
    state=Path.home()/".local/state/louksna"/("document-factory-ffprobe-"+os.environ.get("GITHUB_RUN_ID","manual"))
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
        return {"observed_at":"MAIN_VERIFIED","sources":{"LOUKSNA":{"relative":rel,"bytes":size,"sha256":expected,"role":role,"path":str(authority),"exists":True,"observed_bytes":st.st_size,"observed_sha256":observed,"integrity":"PASS" if observed==expected and st.st_size==size else "DRIFT","binding":"MAIN_VERIFIED_REPOSITORY_AUTHORITY"}}}
    worker.sources=sources
    mission_state=worker.mission_start(
        1.0,"LUNA_PROJECT",
        "FFPROBE provider admission and pre-certification continuation from exact ACTIVE Document Factory; exact material candidate revalidation; existing certification preserved; fresh producer/G23/G24 required.",
        report_minutes=1
    )
    tick=worker.mission_tick(mission_state["mission_id"])

    with tempfile.TemporaryDirectory(prefix="ffprobe-runtime-") as td:
        tmp=Path(td); sys.path.insert(0,str(runtime))
        from runtime_core import Runtime,ExecutorAdapter,TimeBudgetController
        from sr_exec_bound_fme_01 import SRExecBoundFME01
        rt=Runtime(tmp/"runtime",authority,sha(authority))
        selftest=rt.selftest()
        if selftest.get("status")!="PASS": raise SystemExit("RUNTIME_SELFTEST_FAILED")
        rt.budget=TimeBudgetController(3300); rt.mission.transition("PRECHECK")

        remote_line=run(["git","-C",str(target_root),"ls-remote","origin",PRECERT_CANDIDATE_REF])
        remote_candidate_sha=remote_line.split()[0] if remote_line else ""
        if remote_candidate_sha==PRECERT_CANDIDATE_SHA:
            precert=main_root/"scripts/missions/document_factory_ffprobe_precert.py"
            cp=rt.checkpoints.capture_file("FFPROBE_PRECERT_SOURCE",precert)
            print(json.dumps({
              "status":"CUSTOSZ_V7_PRECERT_CONTINUATION_DISPATCHED",
              "candidate_sha":PRECERT_CANDIDATE_SHA,
              "active_sha":ACTIVE_SHA,
              "checkpoint_id":cp["checkpoint_id"],
              "certification_authority":False
            },sort_keys=True),flush=True)
            p=subprocess.Popen([
              sys.executable,"-B","-I",str(precert),str(target_root),str(outdir),PRECERT_CANDIDATE_SHA
            ])
            started=time.monotonic(); seq=0
            while p.poll() is None:
                seq+=1
                print(json.dumps({
                  "status":"CUSTOSZ_V7_PRECERT_HEARTBEAT",
                  "sequence":seq,
                  "state":"RUNNING",
                  "elapsed_seconds":round(time.monotonic()-started,3),
                  "candidate_sha":PRECERT_CANDIDATE_SHA
                },sort_keys=True),flush=True)
                if time.monotonic()-started>1200:
                    p.terminate()
                    raise SystemExit("PRECERT_CONTINUATION_TIMEOUT")
                time.sleep(2)
            if p.returncode!=0:
                raise SystemExit("PRECERT_CONTINUATION_FAILED:"+str(p.returncode))
            ep=outdir/"PRECERT_CONTINUATION.json"
            if not ep.is_file(): raise SystemExit("PRECERT_EVIDENCE_MISSING")
            evidence=json.loads(ep.read_text(encoding="utf-8"))
            if evidence.get("status")!="PASS_PRECERT_NOT_G23_G24":
                raise SystemExit("PRECERT_EVIDENCE_NOT_PASS")
            report={
              "schema":"CUSTOSZ_FFPROBE_PRECERT_RUNTIME_RUN/1.0",
              "status":"PASS_PRECERT_NOT_G23_G24",
              "mission_id":mission_state["mission_id"],
              "custosz_checks":checks,
              "runtime_selftest":selftest,
              "runtime_evidence_ledger":rt.journal.verify(),
              "candidate_head_sha":PRECERT_CANDIDATE_SHA,
              "active_certified_anchor":{"sha":ACTIVE_SHA,"digest":ACTIVE_DIGEST,"preserved":True},
              "certification_propagated":False,
              "certification_authority":False,
              "desktop_commander":"FORBIDDEN",
              "heartbeat_last_sequence":seq,
              "next_state":"FRESH_PRODUCER_INDEPENDENT_G23_G24_REQUIRED"
            }
            (outdir/"CUSTOSZ_FFPROBE_PRECERT_RUNTIME_RESULT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
            print(json.dumps({
              "status":"CUSTOSZ_V7_PRECERT_CONTINUATION_PASS",
              "candidate_sha":PRECERT_CANDIDATE_SHA,
              "next_state":report["next_state"]
            },sort_keys=True),flush=True)
            return

        eid="CUSTOSZ_V7_FFPROBE_PROVIDER_ADMISSION"
        rt.executors.register(ExecutorAdapter(eid,"LOCAL_SUBPROCESS",sys.executable,capabilities={"FFPROBE_PROVIDER_ADMISSION":1.0}))
        cp=rt.checkpoints.capture_file("FFPROBE_MISSION_SOURCE",mission)
        result_file=outdir/"RUNTIME_MATERIAL_RESULT.json"
        spec={
          "mission_id":mission_state["mission_id"],
          "mission_spec_digest":sha(mission),
          "required_abilities":{"FFPROBE_PROVIDER_ADMISSION":1.0},
          "authority_context":{"authority":"Louksna.md","sha256":sha(authority)},
          "policy_context":{"policy_id":"DOCUMENT_FACTORY_FFPROBE_ADMISSION","scope":"WORK_BRANCH_ONLY_ACTIVE_CERT_PRESERVED","allow":True},
          "execution_payload_digest":sha(executor),
          "expected_effect":{"target":str(result_file),"effect_type":"FFPROBE_PROVIDER_ADMISSION_EXECUTION_BINDING"},
          "checkpoint_pointer":cp["checkpoint_id"],
          "runtime_digest":sha(runtime),
          "mission_state":"DISPATCH_READY",
          "executor_metadata":{eid:{"identity_valid":True,"provenance_valid":True,"digest":sha(Path(sys.executable))}},
          "executor_policy":{eid:{"permissions_valid":True,"resource_envelope_valid":True,"policy_allow":True,"risk":0,"cost":0}},
          "probe_argv":{eid:["{COMMAND}","-B","-I","-c","import sys;sys.exit(0)"]},
          "dispatch":{
            "cwd":str(tmp),
            "argv_template":["{COMMAND}","-B","-I",str(executor),"{DISPATCH_PATH}","{ACK_PATH}","{FME_PATH}","{TARGET}",str(main_root),str(target_root),str(mailbox_root),str(outdir)],
            "timeout_s":120,"ack_timeout_s":20,"fme_timeout_s":20
          }
        }
        print(json.dumps({"status":"CUSTOSZ_V7_FFPROBE_RUNTIME_DISPATCHED","mission_id":mission_state["mission_id"],"active_sha":ACTIVE_SHA,"active_digest":ACTIVE_DIGEST},sort_keys=True),flush=True)
        rr=SRExecBoundFME01(rt).establish_material_execution(spec)
        if rr.get("result")!="PASS" or rr.get("material_execution_proven") is not True:
            raise SystemExit("FFPROBE_EXECUTION_BINDING_NOT_PROVEN")
        lease=json.loads(result_file.read_text(encoding="utf-8"))
        if lease.get("status")!="RUNNING" or lease.get("final_material_pass") is not False:
            raise SystemExit("FFPROBE_EXECUTION_BINDING_INVALID")
        heartbeat=Path(lease["heartbeat_path"])
        completion=Path(lease["completion_path"])
        final_result=Path(lease["final_result_path"])
        supervisor_pid=int(lease["supervisor_pid"])
        print(json.dumps({
          "status":"CUSTOSZ_V7_FFPROBE_SUPERVISOR_BOUND",
          "supervisor_pid":supervisor_pid,
          "heartbeat_path":str(heartbeat),
          "final_result_path":str(final_result),
          "anti_paralysis":{"heartbeat_seconds":1,"stale_threshold_seconds":10,"global_timeout_seconds":2400,"blind_retry":False}
        },sort_keys=True),flush=True)

        started=time.monotonic()
        last_sequence=-1
        while True:
            if completion.is_file():
                done=json.loads(completion.read_text(encoding="utf-8"))
                if done.get("status")!="PASS":
                    raise SystemExit("FFPROBE_SUPERVISOR_COMPLETION_FAIL:"+json.dumps(done,sort_keys=True))
                break
            if time.monotonic()-started>2400:
                try: os.kill(supervisor_pid,15)
                except Exception: pass
                raise SystemExit("FFPROBE_SUPERVISOR_GLOBAL_TIMEOUT")
            if not heartbeat.is_file():
                raise SystemExit("FFPROBE_HEARTBEAT_DISAPPEARED")
            hb=json.loads(heartbeat.read_text(encoding="utf-8"))
            seq=int(hb.get("sequence",-1))
            age=time.time()-heartbeat.stat().st_mtime
            if age>10:
                try: os.kill(supervisor_pid,15)
                except Exception: pass
                raise SystemExit("FFPROBE_HEARTBEAT_STALE:"+str(round(age,3)))
            if seq!=last_sequence:
                last_sequence=seq
                print(json.dumps({
                  "status":"CUSTOSZ_V7_FFPROBE_HEARTBEAT",
                  "sequence":seq,
                  "state":hb.get("state"),
                  "elapsed_seconds":hb.get("elapsed_seconds"),
                  "materializer_pid":hb.get("materializer_pid")
                },sort_keys=True),flush=True)
            time.sleep(2)

        if not final_result.is_file():
            raise SystemExit("FFPROBE_FINAL_RESULT_MISSING")
        material=json.loads(final_result.read_text(encoding="utf-8"))
        if material.get("status")!="PASS":
            raise SystemExit("FFPROBE_FINAL_RESULT_NOT_PASS")
        report={
          "schema":"CUSTOSZ_FFPROBE_RUNTIME_RUN/2.0",
          "status":"PASS",
          "mission_id":mission_state["mission_id"],
          "heartbeat_state":tick.get("state"),
          "custosz_checks":checks,
          "runtime_selftest":selftest,
          "runtime_dispatch":{k:rr.get(k) for k in ("result","global_step_gate","material_execution_proven","evidence_chain_head")},
          "runtime_evidence_ledger":rt.journal.verify(),
          "supervisor":{"pid":supervisor_pid,"heartbeat_last_sequence":last_sequence,"completion":done},
          "material_result":material,
          "active_certified_anchor":{"sha":ACTIVE_SHA,"digest":ACTIVE_DIGEST,"preserved":True},
          "certification_propagated":False,
          "desktop_commander":"FORBIDDEN",
          "anti_paralysis":{"heartbeat_seconds":1,"stale_threshold_seconds":10,"global_timeout_seconds":2400,"blind_retry":False}
        }
        (outdir/"CUSTOSZ_FFPROBE_RUNTIME_RESULT.json").write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({
          "status":"CUSTOSZ_V7_FFPROBE_RUNTIME_PASS",
          "material_execution_proven":rr.get("material_execution_proven"),
          "next_state":material.get("next_state")
        },sort_keys=True),flush=True)
if __name__=="__main__": main()
