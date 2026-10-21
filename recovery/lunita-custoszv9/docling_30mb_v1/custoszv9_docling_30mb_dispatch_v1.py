#!/usr/bin/env python3
"""CUSTOSZ V9 CRFU launcher for Docling's strict 30 MB isolated candidate lane."""
from __future__ import annotations
import datetime as dt, fcntl, hashlib, json, os, pathlib, subprocess, sys, time, uuid

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
ROOT=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
RT=ROOT/"CUSTOSZ_CONTINUITY_V1"; STATE=RT/"state"; OUT=STATE/"worker_outputs"; CANDIDATES=STATE/"cajita_candidates"
JOB=STATE/"jobs/docling_30mb_lane_v1"; WORKER_STATE=STATE/"jobs/docling_30mb_worker_v1"
WORKER=JOB/"docling_30mb_quantize_worker_v1.py"; RUNTIME=JOB/"docling_30mb_runtime_v1.py"
MISSION_SPEC=JOB/"DOCLING_30MB_MISSION.json"
V9=ROOT/"CUSTOSZV9.pyz"; MISSION=ROOT/"MISION1.txt"
BINDING=RT/"worker_binding_v2.json"; AUTH=RT/"operator_authorization.json"; CONTRACT=RT/"contract.json"
PYTHON=RT/"state/tools/venvs/llama-cpp-b10819-py313/bin/python"
LOCK_DIR=STATE/"locks"; DISPATCH_LOCK=LOCK_DIR/"docling_30mb_dispatch.lock"
EXPECTED_MISSION_SHA="0a36c59d4baf5d547f5217dc9c6db2a58ad9f8f3ea65d88f9b16a0dbe1604f8f"
EXPECTED_V9_SHA="667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
EXPECTED_SPEC_SHA="4a1c5ccc2554c9ae76d50c285710cb5be0654ef7ea542c3400d14480ef4ba3f5"
EXPECTED_WORKER_SHA="14f96896cba1ed86a3af2aa769fd37b6dee760a384fd88b32fd33b028db7f127"
EXPECTED_RUNTIME_SHA="ac77f2bce09693aea9abd5bfc86c7317179388a5f861db459faf8f7eebe9e370"
CAP=30_000_000; REPO="Plomillo/luna-linux-bridge"; BRANCH="recovery/lunita-custoszv9-operational-20261020"
SCOPE="MISION1_CAJITA_LUNITA"; TASK_ID_PREFIX="CUSTOSZV9_DOCLING_30MB"
SCHEMA="CUSTOSZV9_DOCLING_30MB_DISPATCH/1.0"

def utc():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def canon(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
def sha_file(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda:f.read(8*1024*1024),b""): h.update(b)
    return h.hexdigest()
def readj(p):
    return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def atomic(path,obj,exclusive=False):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if exclusive and path.exists(): raise RuntimeError("APPEND_ONLY_COLLISION:"+str(path))
    tmp=path.with_name(path.name+"."+uuid.uuid4().hex+".tmp")
    with tmp.open("x",encoding="utf-8") as f:
        json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.chmod(tmp,0o600); os.replace(tmp,path)
def verify_journal(path):
    p=pathlib.Path(path)
    if not p.exists(): return {"status":"ABSENT","events":0}
    prev="0"*64; count=0
    for ln,line in enumerate(p.read_text(encoding="utf-8").splitlines(),1):
        row=json.loads(line); digest=row.pop("event_sha256",None)
        if row.get("sequence")!=count+1 or row.get("previous_event_sha256")!=prev:
            return {"status":"FAIL","line":ln,"reason":"CHAIN_OR_SEQUENCE_MISMATCH"}
        if hashlib.sha256(canon(row)).hexdigest()!=digest:
            return {"status":"FAIL","line":ln,"reason":"EVENT_HASH_MISMATCH"}
        prev=digest; count+=1
    return {"status":"PASS","events":count,"last_hash":prev}
def ram_available():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"): return int(line.split()[1])*1024
    return 0
def source_inventory():
    doc=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna/5. Inteligencia documental"
    pins=[
      ("granite_docling_q4_gguf",doc/"Docling/granite-docling-258M-Q4_K_M.gguf",138559520,"4ba41a480d2b6594613a23819df8fcc382d9dab9691e28bf327b3ac799fe0a82"),
      ("granite_docling_mmproj_f16",doc/"Docling/mmproj-granite-docling-258M-f16.gguf",190031712,"4b7b2c4ed3162bd9cb323668c188e2324838b8f8ca4f3f9767f16c4c600d43ad"),
      ("docling_slim_wheel",doc/"Docling/docling_slim-2.124.0-py3-none-any.whl",780430,"2c7c667394d3eae9080bc15143ed6f1d39a4838090d9e3f29be212606e6676bd"),
      ("calibre_binary_reference",doc/"Calibre/calibre-9.14.0-x86_64.txz",192898432,"7f53a0863ed6d32407bc72053b966e39d5b64813f2592bd9c741504c01c0e7f3"),
      ("calibre_source_reference",doc/"Calibre/calibre-9.14.0.tar.xz",48867616,"d1bc24024b0942429c627e9c5d0b25d51df9c1af1e1d8dca3e572f03b194c561"),
    ]
    out={}
    for key,p,size,digest in pins:
        if not p.is_file(): raise RuntimeError("PINNED_SOURCE_MISSING:"+key)
        actual=sha_file(p)
        if p.stat().st_size!=size or actual!=digest: raise RuntimeError("PINNED_SOURCE_HASH_OR_SIZE_MISMATCH:"+key)
        out[key]={"path":str(p),"bytes":size,"sha256":actual,"read_only":True}
    return out
def worker_is_running():
    p=WORKER_STATE/"worker.lock"
    if not p.exists(): return False
    try:
        pid=int(p.read_text().strip()); os.kill(pid,0); return True
    except (ValueError,ProcessLookupError,FileNotFoundError,PermissionError): return False
def verify_authorization(task):
    try:
        binding=readj(BINDING); auth=readj(AUTH); contract=readj(CONTRACT)
        ok=(sha_file(V9)==EXPECTED_V9_SHA and sha_file(MISSION)==EXPECTED_MISSION_SHA and
            sha_file(MISSION_SPEC)==EXPECTED_SPEC_SHA and sha_file(WORKER)==EXPECTED_WORKER_SHA and
            sha_file(RUNTIME)==EXPECTED_RUNTIME_SHA and binding.get("status")=="VALIDATED" and
            binding.get("mission_sha256")==EXPECTED_MISSION_SHA and binding.get("scope")==SCOPE and
            "WRITE_CAJITA_WITH_CHECKPOINTS" in binding.get("allowed_effects",[]) and
            binding.get("certification_authority") is False and binding.get("canonical_promotion_authority") is False and
            auth.get("mission_sha256")==EXPECTED_MISSION_SHA and auth.get("scope")==SCOPE and
            contract.get("mission_sha256")==EXPECTED_MISSION_SHA and contract.get("scope")==SCOPE and
            task.get("mission_id")=="CUSTOSZ_MISION1_0a36c59d4baf" and
            task.get("authorized_scope")==SCOPE and
            task.get("permitted_effects")==["READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"])
        if not ok: return {"status":"DENIED","reason":"PINNED_LOCAL_AUTHORIZATION_OR_IDENTITY_FAILED"}
        return {"status":"PASS","task_id":task.get("task_id"),"mission_sha256":EXPECTED_MISSION_SHA,
          "v9_sha256":EXPECTED_V9_SHA,"scope":SCOPE,"operator_authorization_sha256":sha_file(AUTH),
          "certification_authority":False,"canonical_promotion_authority":False,"cryptographic_signature":"NOT_PRESENT"}
    except Exception as e: return {"status":"DENIED","reason":type(e).__name__+":"+str(e)}
def launch_worker(task,source,queue_path):
    if worker_is_running(): return {"status":"HOLD","reason":"DOCLING_WORKER_ALREADY_RUNNING"}
    if ram_available()<2*1024**3: return {"status":"HOLD","reason":"RAM_HEADROOM_BELOW_2_GIB","ram_available_bytes":ram_available()}
    if not PYTHON.is_file() or not WORKER.is_file() or not RUNTIME.is_file(): return {"status":"HOLD","reason":"WORKER_RUNTIME_OR_PINNED_PYTHON_MISSING"}
    WORKER_STATE.mkdir(parents=True,exist_ok=True,mode=0o700)
    state_path=WORKER_STATE/"dispatch_state.json"
    if state_path.exists(): return {"status":"HOLD","reason":"DISPATCH_STATE_EXISTS_NO_OVERWRITE","path":str(state_path)}
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    checkpoint=STATE/"checkpoints"/("DOCLING_30MB_PRESTART_"+stamp)
    checkpoint.mkdir(parents=True,exist_ok=False,mode=0o700)
    manifest={"schema":"DOCLING_30MB_PRESTART_CHECKPOINT/1.0","timestamp_utc":utc(),
      "mission_spec_sha256":EXPECTED_SPEC_SHA,"mission_sha256":EXPECTED_MISSION_SHA,
      "custoszv9_sha256":EXPECTED_V9_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"runtime_sha256":EXPECTED_RUNTIME_SHA,
      "source_inventory":source,"source_mutation":False,"hard_cap_bytes":CAP,
      "resources":{"MemoryHigh":805306368,"MemoryMax":1073741824,"CPUQuotaPercent":50,"TasksMax":32,"concurrency":1},
      "github":{"repository":REPO,"branch":BRANCH},"canonical_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED"}
    atomic(checkpoint/"MANIFEST.json",manifest,exclusive=True); checkpoint_hash=sha_file(checkpoint/"MANIFEST.json")
    unit="custosz-docling30-"+stamp.lower()
    log=WORKER_STATE/"worker_stdout.log"
    with log.open("ab") as lf:
        proc=subprocess.Popen(["sudo","-n","systemd-run","--scope","--unit="+unit,
          "-p","MemoryHigh=768M","-p","MemoryMax=1G","-p","CPUQuota=50%","-p","TasksMax=32",
          str(PYTHON),"-B",str(WORKER),"--run","--job-dir",str(WORKER_STATE)],
          cwd=str(ROOT),env={**os.environ,"OMP_NUM_THREADS":"1","OMP_THREAD_LIMIT":"1",
          "OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1",
          "TOKENIZERS_PARALLELISM":"false"},stdout=lf,stderr=subprocess.STDOUT,
          start_new_session=True,close_fds=True)
    props={}; active=None
    for _ in range(20):
        q=subprocess.run(["systemctl","show",unit+".scope","--property=ActiveState","--property=MainPID",
          "--property=MemoryMax","--property=MemoryHigh","--property=CPUQuotaPerSecUSec","--no-pager"],
          capture_output=True,text=True,timeout=8,check=False)
        if q.returncode==0:
            for line in q.stdout.splitlines():
                if "=" in line:
                    k,v=line.split("=",1); props[k]=v
            active=props.get("ActiveState")
            if active in {"active","activating"}: break
        time.sleep(.25)
    if active not in {"active","activating"}:
        return {"status":"HOLD","reason":"SYSTEMD_RESOURCE_SCOPE_NOT_CONFIRMED","wrapper_pid":proc.pid,
          "scope_properties":props,"worker_log":str(log),"checkpoint":str(checkpoint)}
    lock_confirmed=False
    for _ in range(24):
        if worker_is_running(): lock_confirmed=True; break
        time.sleep(.25)
    if not lock_confirmed:
        return {"status":"HOLD","reason":"WORKER_PID_LOCK_NOT_CONFIRMED","wrapper_pid":proc.pid,
          "systemd_unit":unit+".scope","scope_properties":props,"worker_log":str(log),
          "checkpoint":str(checkpoint),"mission_completion_claim":False}
    receipt={"schema":"DOCLING_30MB_WORKER_LAUNCH_RECEIPT/1.0","timestamp_utc":utc(),
      "task_id":task["task_id"],"mission_sha256":EXPECTED_MISSION_SHA,"mission_spec_sha256":EXPECTED_SPEC_SHA,
      "custoszv9_sha256":EXPECTED_V9_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"runtime_sha256":EXPECTED_RUNTIME_SHA,
      "source_inventory":source,"target_bytes":CAP,"systemd_unit":unit+".scope","systemd_properties":props,
      "wrapper_pid":proc.pid,"worker_log":str(log),"worker_state_dir":str(WORKER_STATE),
      "prestart_checkpoint":str(checkpoint),"prestart_checkpoint_sha256":checkpoint_hash,
      "resource_caps_confirmed":props.get("MemoryMax") in {"1073741824","1G"} and props.get("MemoryHigh") in {"805306368","768M"},
      "candidate_path":str(CANDIDATES),"source_files_modified":False,"runtime_startup":"PENDING",
      "quality_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED",
      "mission_completion_claim":False}
    launch=OUT/("DOCLING_30MB_WORKER_LAUNCH_"+stamp+".json")
    atomic(launch,receipt,exclusive=True); receipt["launch_receipt_path"]=str(launch); receipt["launch_receipt_sha256"]=sha_file(launch)
    atomic(state_path,receipt,exclusive=True)
    return {"status":"PASS","worker_launch_status":"STARTED_RESOURCE_LIMITED","systemd_unit":unit+".scope",
      "scope_properties":props,"worker_log":str(log),"launch_receipt_path":str(launch),
      "launch_receipt_sha256":sha_file(launch),"prestart_checkpoint":str(checkpoint),
      "prestart_checkpoint_sha256":checkpoint_hash,"source_files_modified":False,
      "certification":"NOT_GRANTED","mission_completion_claim":False}
def main():
    OUT.mkdir(parents=True,exist_ok=True,mode=0o700); LOCK_DIR.mkdir(parents=True,exist_ok=True,mode=0o700)
    fd=os.open(str(DISPATCH_LOCK),os.O_CREAT|os.O_RDWR,0o600)
    try:
        try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            print("DISPATCH_ALREADY_RUNNING; rejecting concurrent launch",file=sys.stderr); return 75
        os.ftruncate(fd,0); os.write(fd,canon({"pid":os.getpid(),"started_at_utc":utc()})); os.fsync(fd)
        # All fixed identities are verified before queue submission.
        if sha_file(V9)!=EXPECTED_V9_SHA or sha_file(MISSION)!=EXPECTED_MISSION_SHA: raise RuntimeError("MISSION_OR_V9_HASH_MISMATCH")
        if sha_file(MISSION_SPEC)!=EXPECTED_SPEC_SHA or sha_file(WORKER)!=EXPECTED_WORKER_SHA or sha_file(RUNTIME)!=EXPECTED_RUNTIME_SHA:
            raise RuntimeError("PINNED_DOCLING_SCRIPT_OR_SPEC_HASH_MISMATCH")
        spec=readj(MISSION_SPEC)
        if spec.get("mission_id")!="CUSTOSZV9_DOCLING_INTELIGENCIA_DOCUMENTAL_30MB_BIVLM_NQ_V1" or spec.get("target",{}).get("hard_cap_bytes")!=CAP:
            raise RuntimeError("DOCLING_MISSION_SPEC_ID_OR_CAP_MISMATCH")
        source=source_inventory()
        if worker_is_running(): raise RuntimeError("DOCLING_WORKER_ALREADY_RUNNING")
        if ram_available()<2*1024**3: raise RuntimeError("RAM_HEADROOM_BELOW_2_GIB:"+str(ram_available()))
        if not WORKER_STATE.exists(): WORKER_STATE.mkdir(parents=True,exist_ok=False,mode=0o700)
        if (WORKER_STATE/"dispatch_state.json").exists(): raise RuntimeError("DISPATCH_STATE_COLLISION_NO_OVERWRITE")
        if str(V9) not in sys.path: sys.path.insert(0,str(V9))
        from custoszv9.crfu.coordinator import run_bounded_mission
        from custoszv9.crfu.event_queue import PersistentMissionQueue
        from custoszv9.crfu.planner import ActionSpec
        from custoszv9.crfu.resources import probe_host_resources
        # Imports from the pinned V9 package are loaded only after its SHA-256 check.
        snapshot=probe_host_resources(ROOT)
        task_id=TASK_ID_PREFIX+"_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
        task={"task_id":task_id,"mission_id":"CUSTOSZ_MISION1_0a36c59d4baf",
          "project_id":"CAJITA_DE_LUNA_DOCLING","source_identity":"CUSTOSZV9.pyz:"+EXPECTED_V9_SHA,
          "target_identity":"GRANITE_DOCLING_258M_HYBRID_BINARY_CANDIDATE_MAX_30000000_BYTES",
          "source_state_hash":EXPECTED_SPEC_SHA,"dependency_set":[
           "MISION1.txt:"+EXPECTED_MISSION_SHA,"CUSTOSZV9.pyz:"+EXPECTED_V9_SHA,
           "worker_binding_v2.json:"+sha_file(BINDING),"operator_authorization.json:"+sha_file(AUTH),
           "worker_sha256:"+EXPECTED_WORKER_SHA,"runtime_sha256:"+EXPECTED_RUNTIME_SHA,
           "mission_spec_sha256:"+EXPECTED_SPEC_SHA],
          "authorized_scope":SCOPE,"required_capabilities":["LOCAL_FILE_READ","HASH_STREAMING","CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE","V9_CRUF_PLANNING"],
          "inputs":{"mission_spec":str(MISSION_SPEC),"mission_spec_sha256":EXPECTED_SPEC_SHA,
            "worker_path":str(WORKER),"runtime_path":str(RUNTIME),"worker_state_dir":str(WORKER_STATE),
            "target_bytes":CAP,"model_path":"Cajita de Luna/5. Inteligencia documental/Docling",
            "github_repository":REPO,"github_branch":BRANCH,"source_files_read_only":True},
          "preconditions":["pinned V9 and mission verified","exact local resource hashes verified",
            "no duplicate Docling worker or dispatch state","host RAM headroom >=2 GiB",
            "worker runs with MemoryMax=1GiB, MemoryHigh=768MiB and CPUQuota=50%",
            "strict 30000000-byte candidate directory gate"],
          "permitted_effects":["READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"],
          "resource_budget":{"ram_required_bytes":134217728,"ram_reserved_bytes":268435456,"disk_required_bytes":268435456,"max_concurrency":1},
          "execution_deadline":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(minutes=5)).isoformat(),
          "maximum_planning_budget":3,"maximum_retry_budget":0,
          "acceptance_criteria":["V9 CRFU validates and launches worker in bounded systemd scope",
            "candidate bundle is <=30000000 bytes including model, assets, manifest and runtime shim",
            "real CPU image-to-text smoke passes before candidate publication",
            "local source artifacts remain unchanged","no model-quality or canonical certification claim"],
          "expected_outputs":["DOCLING_30MB worker launch receipt","checkpointed quantization progress","V9 hash-chain queue events"],
          "validation_strategy":"pinned_identity+resource_scope+live_worker_lock+candidate_size_gate+runtime_smoke",
          "evidence_requirements":["V9 and mission hashes","resource inventory SHA-256","scope properties","live lock and worker log","queue event chain"],
          "checkpoint_reference":str(STATE/"checkpoints"),"rollback_strategy":"local original artifacts are read-only; isolated candidate staging; no canonical promotion",
          "completion_condition":"bounded worker launch and progress evidence; startup gate is separately reported by worker",
          "escalation_condition":"HOLD on any identity, memory, source, size, load or startup precondition failure",
          "authorization_evidence_reference":str(AUTH)}
        qpath=STATE/"docling_30mb_v9_queue.sqlite3"; queue=PersistentMissionQueue(qpath)
        submitted=queue.submit(task)
        if submitted.get("state")!="RECEIVED": raise RuntimeError("V9_QUEUE_SUBMIT_FAILED:"+str(submitted))
        queue.transition(task_id,"RECEIVED","PREFLIGHT",event_type="DOCLING_30MB_V9_PREFLIGHT_STARTED",
          payload={"mission_spec_sha256":EXPECTED_SPEC_SHA,"source_inventory":source})
        checks={"v9_hash":sha_file(V9)==EXPECTED_V9_SHA,"mission_hash":sha_file(MISSION)==EXPECTED_MISSION_SHA,
          "mission_spec":sha_file(MISSION_SPEC)==EXPECTED_SPEC_SHA,"worker_hash":sha_file(WORKER)==EXPECTED_WORKER_SHA,
          "runtime_hash":sha_file(RUNTIME)==EXPECTED_RUNTIME_SHA,"binding_validated":readj(BINDING).get("status")=="VALIDATED",
          "source_inventory_hashes":True,"ram_headroom":ram_available()>=2*1024**3,
          "cap_exact":CAP==30_000_000,"source_unchanged":True}
        if not all(checks.values()):
            queue.transition(task_id,"PREFLIGHT","BLOCKED",event_type="DOCLING_30MB_V9_PREFLIGHT_BLOCKED",payload={"checks":checks})
            raise RuntimeError("DOCLING_V9_PREFLIGHT_BLOCKED:"+json.dumps(checks))
        queue.transition(task_id,"PREFLIGHT","READY",event_type="DOCLING_30MB_V9_PREFLIGHT_PASS",payload={"checks":checks})
        claimed=queue.claim_next_ready()
        if not isinstance(claimed,dict) or claimed.get("state")!="RUNNING":
            raise RuntimeError("V9_QUEUE_ATOMIC_CLAIM_FAILED:"+str(claimed))
        actions=[
          ActionSpec("verify_docling_identity_and_resource_policy",(),("LOCAL_FILE_READ","HASH_STREAMING"),
            ("READ_PROJECT_ARTIFACTS",),"READ_ONLY"),
          ActionSpec("launch_bounded_docling_quantization_worker",("verify_docling_identity_and_resource_policy",),
            ("CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE"),
            ("WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"),"IDEMPOTENT")]
        def runner(payload):
            action=payload["action"]["action_id"]
            if action=="verify_docling_identity_and_resource_policy":
                now=source_inventory()
                same=all(now[k]["sha256"]==source[k]["sha256"] and now[k]["bytes"]==source[k]["bytes"] for k in source)
                if not same: return {"status":"HOLD","reason":"SOURCE_HASH_CHANGED_SINCE_PREFLIGHT"}
                return {"status":"PASS","source_inventory":now,"ram_available_bytes":ram_available(),"target_bytes":CAP}
            if action=="launch_bounded_docling_quantization_worker":
                try: return launch_worker(payload["task"],source,qpath)
                except Exception as e: return {"status":"HOLD","reason":type(e).__name__+":"+str(e),"certification":"NOT_GRANTED"}
            return {"status":"DENIED","reason":"ACTION_ID_NOT_REGISTERED"}
        coord=run_bounded_mission(task,actions,snapshot,
          available_capabilities=set(readj(BINDING).get("capabilities",[]))|{"LOCAL_FILE_READ","HASH_STREAMING"},
          admissible_effects={"READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"},
          authorization_verifier=verify_authorization,action_runner=runner,maximum_steps=2,planning_budget=3)
        state="COMPLETED" if coord.get("status")=="COMPLETED" else "BLOCKED"
        queue.transition(task_id,"RUNNING",state,event_type="DOCLING_30MB_V9_LAUNCH_RECORDED" if state=="COMPLETED" else "DOCLING_30MB_V9_LAUNCH_BLOCKED",
          payload={"coordinator_status":coord.get("status"),"model_startup":"PENDING","model_quality_certification":"NOT_GRANTED","mission_completion_claim":False})
        chain=queue.verify_event_chain()
        report={"schema":SCHEMA,"timestamp_utc":utc(),"task_id":task_id,"mission_sha256":EXPECTED_MISSION_SHA,
          "mission_spec_sha256":EXPECTED_SPEC_SHA,"v9_sha256":sha_file(V9),"worker_sha256":sha_file(WORKER),
          "runtime_sha256":sha_file(RUNTIME),"source_inventory":source,"preflight_checks":checks,
          "coordinator_result":coord,"queue_path":str(qpath),"queue_final_state":state,"queue_event_chain":chain,
          "target_bytes":CAP,"github":{"repository":REPO,"branch":BRANCH},"source_files_modified":False,
          "model_startup":"PENDING","model_quality_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED",
          "canonical_promotion":"NOT_AUTHORIZED","mission_completion_claim":False}
        rp=OUT/("DOCLING_30MB_V9_DISPATCH_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
        atomic(rp,report,exclusive=True)
        print(json.dumps({"status":state,"task_id":task_id,"coordinator_status":coord.get("status"),
          "queue_event_chain":chain.get("status"),"report_path":str(rp),"report_sha256":sha_file(rp),
          "worker_launch_status":coord.get("actions"),"target_bytes":CAP,"certification":"NOT_GRANTED"},indent=2),flush=True)
        return 0 if state=="COMPLETED" and chain.get("status")=="PASS" else 2
    finally:
        os.close(fd)
if __name__=="__main__":
    raise SystemExit(main())
