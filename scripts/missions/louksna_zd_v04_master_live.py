#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, os, re, subprocess, sys, tempfile, time
from pathlib import Path

MISSION_ID="MIS-LOUKSNA-ZD-V04-MASTER-20261007"
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"
BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b"
MERGE_BASE="d7c06ef40141d8865815c18493604655280c2f2a"
CUSTOSZ_SHA256="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"
LOUKSNA_GIT_BLOB="1a399ab7494d6df5582436819eee557083e753ed"
PUAC2_GIT_BLOB="da3b216888c86e588685d384c34dd3c481414b22"

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""):
            h.update(block)
    return h.hexdigest()

def run(cmd, cwd=None, timeout=120, env=None, check=True):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,env=env)
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-4000:]+"\n"+p.stderr[-4000:])
    return p

def emit(out:Path,event:str,**fields):
    obj={"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"mission_id":MISSION_ID,"event":event,**fields}
    line=json.dumps(obj,sort_keys=True,ensure_ascii=False)
    print("LOUKSNA_V04_TELEMETRY "+line,flush=True)
    with (out/"V04_TELEMETRY.jsonl").open("a",encoding="utf-8") as f:
        f.write(line+"\n")
    return obj

def git_head(path:Path)->str:
    return run(["git","rev-parse","HEAD"],cwd=path).stdout.strip()

def git_blob(path:Path,file:str)->str:
    return run(["git","hash-object",file],cwd=path).stdout.strip()

def count_and_digest_tracked(root:Path):
    names=run(["git","ls-files","-z"],cwd=root).stdout.split("\0")
    names=[x for x in names if x]
    chain=hashlib.sha256()
    total=0
    for rel in names:
        p=root/rel
        if not p.is_file() or p.is_symlink():
            continue
        s=sha256(p)
        size=p.stat().st_size
        chain.update((rel+"\0"+str(size)+"\0"+s+"\n").encode())
        total+=size
    return {"tracked_files":len(names),"regular_bytes":total,"manifest_sha256":chain.hexdigest()}

def inspect_markers(root:Path, rel:str, markers:list[str]):
    p=root/rel
    if not p.is_file():
        return {"path":rel,"exists":False,"markers":{m:False for m in markers}}
    text=p.read_text(encoding="utf-8",errors="replace")
    return {"path":rel,"exists":True,"sha256":sha256(p),"markers":{m:(m in text) for m in markers}}

def main():
    mission_root=Path(os.environ["MISSION_ROOT"]).resolve()
    mailbox=Path(os.environ["MAILBOX_ROOT"]).resolve()
    v03=Path(os.environ["V03_ROOT"]).resolve()
    bridge=Path(os.environ["BRIDGE_ROOT"]).resolve()
    out=Path(os.environ["OUT_DIR"]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    mission=mission_root/"missions/inbox/louksna-zd-v04-master-20261007/MISSION_ORIGINAL.md"
    authority=mission_root/"Louksna.md"
    puac2=mission_root/"PUAC2.md"
    custosz=mailbox/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    runtime=mailbox/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    census=mailbox/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json"

    emit(out,"MISSION_BOOTSTRAP_STARTED",phase="P01",state="RUNNING")

    required=[mission,authority,puac2,custosz,runtime,census]
    missing=[str(p) for p in required if not p.is_file()]
    if missing:
        emit(out,"HOLD",phase="P01",reason="REQUIRED_INPUT_MISSING",missing=missing)
        raise SystemExit(3)

    actual={
      "mission_branch_head":git_head(mission_root),
      "v03_head":git_head(v03),
      "bridge_head":git_head(bridge),
      "louksna_git_blob":git_blob(mission_root,"Louksna.md"),
      "puac2_git_blob":git_blob(mission_root,"PUAC2.md"),
      "custosz_sha256":sha256(custosz),
      "runtime_sha256":sha256(runtime),
      "mission_sha256":sha256(mission),
      "louksna_sha256":sha256(authority),
      "puac2_sha256":sha256(puac2)
    }
    if actual["v03_head"]!=V03_SHA: raise RuntimeError("V03_SHA_DRIFT")
    if actual["bridge_head"]!=BRIDGE_SHA: raise RuntimeError("BRIDGE_SHA_DRIFT")
    if actual["louksna_git_blob"]!=LOUKSNA_GIT_BLOB: raise RuntimeError("LOUKSNA_BLOB_DRIFT")
    if actual["puac2_git_blob"]!=PUAC2_GIT_BLOB: raise RuntimeError("PUAC2_BLOB_DRIFT")
    if actual["custosz_sha256"]!=CUSTOSZ_SHA256: raise RuntimeError("CUSTOSZ_PYZ_DRIFT")

    mb=run(["git","merge-base",V03_SHA,BRIDGE_SHA],cwd=mission_root).stdout.strip()
    if mb!=MERGE_BASE: raise RuntimeError("V03_BRIDGE_MERGE_BASE_DRIFT")
    actual["v03_bridge_merge_base"]=mb
    emit(out,"INPUT_IDENTITY_VERIFIED",phase="P01",state="PASS",evidence=actual)

    census_data=json.loads(census.read_text(encoding="utf-8"))
    if (census_data.get("family_count"),census_data.get("capability_count"),census_data.get("unique_capability_count"))!=(9,72,72):
        raise RuntimeError("CUSTOSZ_CENSUS_DRIFT")

    checks={}
    for command in ("v07-status","v07-selftest"):
        p=run([sys.executable,"-B","-I",str(custosz),command],timeout=45,check=False)
        checks[command]={"exit_code":p.returncode,"stdout":p.stdout[-6000:],"stderr":p.stderr[-3000:]}
        emit(out,"CUSTOSZ_CLI_CHECK",phase="P03",command=command,exit_code=p.returncode)
        if p.returncode:
            raise RuntimeError("CUSTOSZ_"+command+"_FAIL")

    workspace=Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).resolve()
    if not workspace.is_dir():
        raise RuntimeError("CUSTOSZ_WORKSPACE_OVERRIDE_MISSING")

    sys.path.insert(0,str(custosz))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}
    worker.workspace=lambda: workspace
    worker.discover=lambda:{"workspace":str(workspace),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(workspace),"score":999}}}
    rel,size,expected,role=worker.PINS["LOUKSNA"]
    worker.sources=lambda _large=False:{
      "observed_at":"V04_MISSION_VERIFIED",
      "sources":{"LOUKSNA":{"relative":rel,"bytes":size,"sha256":expected,"role":role,
      "path":str(authority),"exists":True,"observed_bytes":authority.stat().st_size,
      "observed_sha256":sha256(authority),
      "integrity":"PASS" if sha256(authority)==expected and authority.stat().st_size==size else "DRIFT",
      "binding":"MISSION_BRANCH_VERIFIED_AUTHORITY"}}}
    mission_state=worker.mission_start(
      1.0,"LUNA_PROJECT",
      "Execute MIS-LOUKSNA-ZD-V04-MASTER-20261007 exactly as written: twelve operational points, no inferred PASS, PUAC2/Louksna governance, provenance, checkpoints, second-order anti-paralysis, direct/indirect error closure.",
      report_minutes=1
    )
    tick=worker.mission_tick(mission_state["mission_id"])
    emit(out,"CUSTOSZ_V7_MISSION_LIVE",phase="P03",state=tick.get("state"),custosz_mission_id=mission_state["mission_id"])

    with tempfile.TemporaryDirectory(prefix="louksna-v04-runtime-") as td:
        sys.path.insert(0,str(runtime))
        from runtime_core import Runtime
        rt=Runtime(Path(td)/"state",authority,sha256(authority))
        runtime_selftest=rt.selftest()
        if runtime_selftest.get("status")!="PASS":
            raise RuntimeError("RUNTIME_SELFTEST_FAIL")
        emit(out,"RUNTIME_LIVE",phase="P03",state="PASS",evidence_journal=rt.journal.verify())

        inventory={}
        inventory["P02"]= {
          "v03":inspect_markers(v03,"scripts/missions/v03_templates/main.rs",
             ["remote_chat_bridge",".post(","CHAT_BRIDGE"]),
          "bridge_gateway":inspect_markers(bridge,"bridge/mtls_gateway.py",
             ["127.0.0.1","HOLD_REMOTE_MUTATION_NOT_EXPOSED","/v1/status","/v1/observe","/v1/watch"]),
          "bridge_transport":inspect_markers(bridge,"bridge/live_link.py",
             ["UNREGISTERED_OPERATION_DENIED","review_model","gate_preflight"])
        }
        inventory["P04"]={
          "v03_event_log":inspect_markers(v03,"scripts/missions/v03_templates/main.rs",
             ["CREATE TABLE IF NOT EXISTS evidence","INSERT INTO evidence"]),
          "bridge_ledger":inspect_markers(bridge,"bridge/lrb_core.py",["EvidenceLedger","entry_hash"])
        }
        inventory["P05"]={"registered_in_bridge":False,"required_by_mission":True}
        inventory["P06"]={"v03_voice_gate":"OPEN_NOT_CLAIMED","primary_tts":"CHATTERBOX_ES_ES_SELF_HOSTED_API","local_voice":"SABELA","piper":"EXCLUDED"}
        inventory["P07"]={"v03_microphone_materialized":False,"required_chain":["CAPTURE","VAD","STT_LOCAL","TRANSCRIPT","REASONING_ADAPTER","RESPONSE_TEXT","TTS_ROUTER","AUDIO_OUTPUT"]}
        inventory["P08"]={"effort_modes_required":["Instantáneo","Medio","Alto","Muy alto","Pro"],"materialized_in_current_bridge":False}
        inventory["P09"]={"capability_registry_required":57,"repo_claims":36,"account_claims":21,"availability_must_be_probed":True}
        inventory["P10"]={"current_gateway_bind":"127.0.0.1","off_host_proven":False}
        inventory["P11"]={"puac2_tests_required":"T01-T28","current_exact_bridge_reproof":"RUNNING_NEXT"}
        inventory["P12"]={"release_active":False,"g23_current_scope":"REQUIRED","g24_current_scope":"REQUIRED","operational_authorization":"SEPARATE_REQUIRED"}
        emit(out,"V04_READINESS_AUDIT_MATERIALIZED",phase="P01",state="EVIDENCED",direct_and_indirect=True)

        manifests={
          "mission":count_and_digest_tracked(mission_root),
          "v03":count_and_digest_tracked(v03),
          "bridge":count_and_digest_tracked(bridge)
        }
        emit(out,"PROVENANCE_MANIFESTS_BUILT",phase="P01",state="PASS",manifests=manifests)

        fscks={}
        for label,root in (("mission",mission_root),("v03",v03),("bridge",bridge)):
            p=run(["git","fsck","--strict","--no-progress"],cwd=root,timeout=240,check=False)
            fscks[label]={"exit_code":p.returncode,"stderr":p.stderr[-3000:]}
            emit(out,"GIT_INTEGRITY_CHECK",phase="P01",source=label,exit_code=p.returncode)
            if p.returncode:
                raise RuntimeError("GIT_FSCK_FAIL_"+label.upper())

        test_env=os.environ.copy()
        test_env["PYTHONPATH"]=str(bridge/"bridge")
        proc=subprocess.Popen(
          [sys.executable,"-B","-m","unittest","discover","-s","bridge/tests","-p","test_*.py"],
          cwd=bridge,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE,env=test_env
        )
        started=time.monotonic(); seq=0
        while proc.poll() is None:
            seq+=1
            emit(out,"BRIDGE_REPROOF_HEARTBEAT",phase="P11",state="RUNNING",sequence=seq,elapsed_seconds=round(time.monotonic()-started,3))
            if time.monotonic()-started>900:
                proc.terminate()
                raise RuntimeError("BRIDGE_REPROOF_TIMEOUT")
            time.sleep(2)
        stdout,stderr=proc.communicate()
        m=re.search(r"Ran (\d+) tests?",stdout+"\n"+stderr)
        tests=int(m.group(1)) if m else None
        repro={"exit_code":proc.returncode,"tests":tests,"stdout_tail":stdout[-5000:],"stderr_tail":stderr[-5000:]}
        emit(out,"BRIDGE_REPROOF_FINISHED",phase="P11",state="PASS" if proc.returncode==0 else "FAIL",tests=tests)
        if proc.returncode:
            raise RuntimeError("BRIDGE_REPROOF_FAIL")

        checkpoint={
          "schema":"LOUKSNA_ZD_V04_CHECKPOINT/1.0",
          "mission_id":MISSION_ID,
          "status":"PASS_P01_INPUT_RECONCILIATION",
          "epistemic_state":"EVIDENCED_NOT_CERTIFIED",
          "active":False,
          "canonical_mutation":False,
          "certification_propagated":False,
          "inputs":actual,
          "custosz_checks":checks,
          "custosz_mission_id":mission_state["mission_id"],
          "runtime_selftest":runtime_selftest,
          "runtime_evidence_journal":rt.journal.verify(),
          "readiness_inventory":inventory,
          "tracked_manifests":manifests,
          "git_fsck":fscks,
          "bridge_reproof":repro,
          "checkpoint_id":"CHECKPOINT_01",
          "next_point":"P02_LRB_APP_0_4_TYPED_PROTOCOL",
          "holds":[
            "P02-P12 require material implementation/evidence before PASS",
            "Current mTLS gateway remains loopback/read-only",
            "V0.3 generic remote_chat_bridge POST is not an authorized V0.4 trust path",
            "Voice remains OPEN_NOT_CLAIMED in V0.3"
          ],
          "anti_paralysis":{
            "blind_retry":False,
            "safe_independent_work_may_continue":True,
            "resume_from_last_verified_checkpoint":True
          }
        }
        (out/"CHECKPOINT_01.json").write_text(json.dumps(checkpoint,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
        emit(out,"CHECKPOINT_01_REACHED",phase="P01",state="PASS",next_point=checkpoint["next_point"])
        emit(out,"MISSION_CONTINUATION_BOUNDARY",phase="P02",state="READY_FOR_MATERIAL_IMPLEMENTATION",active=False)
        return 0

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        try:
            out=Path(os.environ.get("OUT_DIR","/tmp"))
            out.mkdir(parents=True,exist_ok=True)
            emit(out,"HOLD",phase="UNRESOLVED",state="FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc)[:500])
        except Exception:
            pass
        print(json.dumps({"status":"HOLD","reason":type(exc).__name__+":"+str(exc)[:500],"active":False,"certified":False}),file=sys.stderr)
        raise SystemExit(3)
