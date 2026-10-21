#!/usr/bin/env python3
"""CUSTOSZ V9 CRFU dispatcher: corrective five-file quantization, exact path scope, fail-closed."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, subprocess, sys, time, uuid
from dataclasses import replace

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
BASE=HOME/"PROYECTOS/1. PROYECTOS PRIORITARIOS"
OP=BASE/"5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT=OP/"CUSTOSZ_CONTINUITY_V1"; STATE=CONT/"state"; OUT=STATE/"worker_outputs"
V9=OP/"CUSTOSZV9.pyz"
LANE=STATE/"jobs/inteldoc_global_30mb_corrective_v8"
MISSION=LANE/"INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json"
WORKER=LANE/"inteldoc_five_artifact_corrective_worker_v6.py"
TEST=LANE/"test_inteldoc_five_artifact_corrective_contract_v6.py"
ADDENDUM=LANE/"GLOBAL_SCOPE_REPAIR_ADDENDUM_V8.json"
AUTH=CONT/"operator_authorization.json"; CONTRACT=CONT/"contract.json"; BINDING=CONT/"worker_binding_v2.json"
WORKER_ROOT=STATE/"jobs/inteldoc_global_30mb_corrective_worker_v8"
EXPECTED_V9_SHA="667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
EXPECTED_MISSION_SHA="c928111ddc323b38c4943c56e5b40769768e0a892fbe4ab0746fbc84022ad399"
EXPECTED_WORKER_SHA="3c2d7660959ae399f9df62af4051745a3ba808cab62e120183d3a7962158f59a"
EXPECTED_TEST_SHA="d346558d42a301359808631276f5b9bc330317f486db0251acc53559678604f3"
SCOPE_ID="INTELDOC_GLOBAL_30MB_CORRECTIVE_V8"
ADDENDUM_ID="GITHUB_INTELDOC_GLOBAL_30MB_CORRECTIVE_REPAIR_V8_SCOPE_20261021"
REPO="Plomillo/luna-linux-bridge"; BRANCH="recovery/lunita-custoszv9-operational-20261020"
GH_PREFIX="recovery/lunita-custoszv9/inteldoc_global_30mb_corrective_v8/"
PYTHON=CONT/"state/tools/venvs/llama-cpp-b10819-py313/bin/python"

def utc(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def sha(p):
    h=hashlib.sha256()
    with pathlib.Path(p).open("rb") as f:
        for b in iter(lambda:f.read(4*1024*1024),b""): h.update(b)
    return h.hexdigest()
def readj(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def atomic(p,obj,exclusive=False):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    if exclusive and p.exists(): raise RuntimeError("APPEND_ONLY_COLLISION:"+str(p))
    tmp=p.with_name(p.name+"."+uuid.uuid4().hex+".tmp")
    with tmp.open("x",encoding="utf-8") as f:
        json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
    os.chmod(tmp,0o600); os.replace(tmp,p)
def ram_available():
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"): return int(line.split()[1])*1024
    return 0
def source_inventory():
    spec=readj(MISSION); root=pathlib.Path(spec["inventory"]["source_root"]); result={}
    for x in spec["inventory"]["pinned_originals"]:
        p=root/x["path"]
        if not p.is_file() or p.stat().st_size!=x["bytes"] or sha(p)!=x["sha256"]:
            raise RuntimeError("SOURCE_PIN_MISMATCH:"+x["id"])
        result[x["id"]]={"path":str(p),"bytes":x["bytes"],"sha256":x["sha256"],"read_only":True}
    return result
def verify_authorization(task):
    try:
        auth=readj(AUTH); con=readj(CONTRACT); bind=readj(BINDING); add=readj(ADDENDUM)
        aa=[x for x in auth.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
        ca=[x for x in con.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
        if len(aa)!=1 or len(ca)!=1 or aa[0]!=ca[0] or aa[0]!=add:
            return {"status":"DENIED","reason":"CORRECTIVE_SCOPE_ADDENDUM_MISSING_OR_MISMATCHED"}
        expected_paths={GH_PREFIX+n for n in [
            "INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json",
            "inteldoc_five_artifact_corrective_worker_v6.py",
            "custoszv9_inteldoc_five_artifact_corrective_dispatch_v7.py",
            "test_inteldoc_five_artifact_corrective_contract_v6.py",
            "GLOBAL_SCOPE_REPAIR_ADDENDUM_V8.json",
            "INTELDOC_GLOBAL_30MB_CORRECTIVE_V8_LAUNCH_RECEIPT.json",
            "INTELDOC_GLOBAL_30MB_CORRECTIVE_V8_RESULT.json"]}
        if not expected_paths.issubset(set(add.get("allowed_paths",[]))):
            return {"status":"DENIED","reason":"CORRECTIVE_PATH_ALLOWLIST_MISMATCH"}
        fields={
            "repository":REPO,"branch":BRANCH,"mission_id":"CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V1",
            "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,
            "test_sha256":EXPECTED_TEST_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__))}
        for k,v in fields.items():
            if add.get(k)!=v: return {"status":"DENIED","reason":"CORRECTIVE_PIN_MISMATCH","field":k,"expected":v,"actual":add.get(k)}
        checks={"v9_sha":sha(V9)==EXPECTED_V9_SHA,"mission_sha":sha(MISSION)==EXPECTED_MISSION_SHA,
            "worker_sha":sha(WORKER)==EXPECTED_WORKER_SHA,"test_sha":sha(TEST)==EXPECTED_TEST_SHA,
            "binding_validated":bind.get("status")=="VALIDATED","mission_scope":task.get("authorized_scope")==SCOPE_ID,
            "addendum_on_assigned_branch":add.get("branch")==BRANCH}
        if not all(checks.values()): return {"status":"DENIED","reason":"PIN_OR_BINDING_CHECK_FAILED","checks":checks}
        return {"status":"PASS","checks":checks,"task_id":task.get("task_id"),"scope":SCOPE_ID,
                "no_canonical_promotion":True,"no_certification_authority":True}
    except Exception as e:
        return {"status":"DENIED","reason":type(e).__name__+":"+str(e)}
def worker_active():
    p=WORKER_ROOT/"worker.lock"
    if not p.exists(): return False
    try: os.kill(int(p.read_text().strip()),0); return True
    except (ValueError,ProcessLookupError,PermissionError,FileNotFoundError): return False
def launch(task,inventory):
    if WORKER_ROOT.exists() and any(WORKER_ROOT.iterdir()):
        return {"status":"HOLD","reason":"CORRECTIVE_WORKER_ROOT_NONEMPTY_NO_OVERWRITE","path":str(WORKER_ROOT)}
    if ram_available()<2*1024**3:
        return {"status":"HOLD","reason":"RAM_HEADROOM_BELOW_2_GIB","ram_available_bytes":ram_available()}
    now=source_inventory()
    if now!=inventory: return {"status":"HOLD","reason":"SOURCE_INVENTORY_CHANGED_BEFORE_LAUNCH"}
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    cp=STATE/"checkpoints"/("INTELDOC_CORRECTIVE_PRESTART_"+stamp); cp.mkdir(parents=True,exist_ok=False,mode=0o700)
    manifest={"schema":"INTELDOC_CORRECTIVE_PRESTART/1.0","timestamp_utc":utc(),
        "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,
        "dispatcher_sha256":sha(pathlib.Path(__file__)),"custoszv9_sha256":EXPECTED_V9_SHA,"source_inventory":inventory,
        "source_files_modified":False,"resource_limits":{"MemoryHigh":805306368,"MemoryMax":1073741824,"CPUQuotaPercent":35,"TasksMax":24},
        "github":{"repository":REPO,"branch":BRANCH,"path_prefix":GH_PREFIX},"runtime_smoke":"DEFERRED_BY_USER",
        "certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
    atomic(cp/"MANIFEST.json",manifest,exclusive=True); cp_hash=sha(cp/"MANIFEST.json")
    unit="custosz9-idoc-corrective-"+stamp.lower()
    log=WORKER_ROOT.parent/"inteldoc_global_30mb_corrective_worker_v7_startup.log"
    WORKER_ROOT.mkdir(parents=True,exist_ok=True,mode=0o700)
    with log.open("ab") as lf:
        proc=subprocess.Popen(["sudo","-n","systemd-run","--scope","--unit="+unit,
            "-p","MemoryHigh=768M","-p","MemoryMax=1G","-p","CPUQuota=35%","-p","TasksMax=24",
            str(PYTHON),"-B",str(WORKER),"--run","--job-dir",str(WORKER_ROOT)],
            cwd=str(OP),env={**os.environ,"OMP_NUM_THREADS":"1","OMP_THREAD_LIMIT":"1","OPENBLAS_NUM_THREADS":"1",
            "MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false"},
            stdout=lf,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
    props={}
    for _ in range(20):
        q=subprocess.run(["systemctl","show",unit+".scope","--property=ActiveState","--property=MainPID",
            "--property=MemoryMax","--property=MemoryHigh","--property=CPUQuotaPerSecUSec","--no-pager"],
            capture_output=True,text=True,timeout=5,check=False)
        if q.returncode==0:
            for line in q.stdout.splitlines():
                if "=" in line: k,v=line.split("=",1); props[k]=v
            if props.get("ActiveState") in {"active","activating"}: break
        time.sleep(.2)
    if props.get("ActiveState") not in {"active","activating"}:
        return {"status":"HOLD","reason":"SYSTEMD_RESOURCE_SCOPE_NOT_CONFIRMED","wrapper_pid":proc.pid,"scope_properties":props,"log":str(log)}
    for _ in range(30):
        if worker_active(): break
        time.sleep(.2)
    if not worker_active():
        return {"status":"HOLD","reason":"WORKER_LOCK_NOT_CONFIRMED","wrapper_pid":proc.pid,"unit":unit+".scope","properties":props,"log":str(log)}
    receipt={"schema":"INTELDOC_GLOBAL_30MB_CORRECTIVE_LAUNCH_RECEIPT/5.0","timestamp_utc":utc(),
        "task_id":task["task_id"],"mission_id":task["mission_id"],"mission_sha256":EXPECTED_MISSION_SHA,
        "worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),
        "custoszv9_sha256":EXPECTED_V9_SHA,"source_inventory":inventory,"worker_pid":int((WORKER_ROOT/"worker.lock").read_text().strip()),
        "wrapper_pid":proc.pid,"systemd_unit":unit+".scope","systemd_properties":props,
        "resource_caps_confirmed":props.get("MemoryMax") in {"1073741824","1G"} and props.get("MemoryHigh") in {"805306368","768M"},
        "worker_state_dir":str(WORKER_ROOT),"worker_log":str(log),"prestart_checkpoint":str(cp),
        "prestart_checkpoint_sha256":cp_hash,"observed_phase":"INITIALIZING","observed_status":"RUNNING",
        "runtime_smoke":"DEFERRED_BY_USER","source_files_modified":False,"global_goal_bytes":30000000,
        "canonical_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED","mission_completion_claim":False}
    path=OUT/"INTELDOC_GLOBAL_30MB_CORRECTIVE_V8_LAUNCH_RECEIPT.json"
    atomic(path,receipt,exclusive=True)
    receipt["launch_receipt_path"]=str(path); receipt["launch_receipt_sha256"]=sha(path)
    return {"status":"PASS","worker_launch_status":"STARTED_RESOURCE_LIMITED","receipt":receipt,"receipt_path":str(path),"receipt_sha256":sha(path)}
def main():
    OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
    if sha(V9)!=EXPECTED_V9_SHA: raise RuntimeError("CUSTOSZ_V9_HASH_MISMATCH")
    spec=readj(MISSION)
    if spec.get("mission_id")!="CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V1" or spec.get("global_limit",{}).get("hard_cap_bytes")!=30000000:
        raise RuntimeError("MISSION_ID_OR_HARD_CAP_MISMATCH")
    src=source_inventory()
    if WORKER_ROOT.exists() and any(WORKER_ROOT.iterdir()): raise RuntimeError("CORRECTIVE_WORKER_ROOT_NONEMPTY_NO_OVERWRITE")
    sys.path.insert(0,str(V9))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.event_queue import PersistentMissionQueue
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    task_id="CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V8_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    task={"task_id":task_id,"mission_id":spec["mission_id"],"project_id":"CAJITA_DE_LUNA_INTELDOC_GLOBAL",
        "source_identity":"CUSTOSZV9.pyz:"+EXPECTED_V9_SHA,"target_identity":"FIVE_SOURCE_ARTIFACT_CANDIDATES_GLOBAL_MAX_30000000_BYTES",
        "source_state_hash":EXPECTED_MISSION_SHA,"dependency_set":["MISSION:"+EXPECTED_MISSION_SHA,"WORKER:"+EXPECTED_WORKER_SHA,"TEST:"+EXPECTED_TEST_SHA,"V9:"+EXPECTED_V9_SHA],
        "authorized_scope":SCOPE_ID,"required_capabilities":["LOCAL_FILE_READ","HASH_STREAMING","CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE","V9_CRUF_PLANNING"],
        "inputs":{"mission_path":str(MISSION),"worker_path":str(WORKER),"worker_state":str(WORKER_ROOT),"hard_cap_bytes":30000000,
            "source_inventory":src,"github_repository":REPO,"github_branch":BRANCH,"github_prefix":GH_PREFIX},
        "preconditions":["pinned CUSTOSZ V9, mission, worker, and test verified","new exact-path scope is present identically in auth and contract",
            "all five sources match pinned size and SHA-256","no previous corrective worker state","RAM headroom at least 2 GiB",
            "worker runs with MemoryMax 1 GiB, MemoryHigh 768 MiB, CPUQuota 35%"],
        "permitted_effects":["READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"],
        "resource_budget":{"ram_required_bytes":134217728,"ram_reserved_bytes":268435456,"disk_required_bytes":805306368,"max_concurrency":1},
        "execution_deadline":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=2)).isoformat(),
        "maximum_planning_budget":3,"maximum_retry_budget":0,
        "acceptance_criteria":spec["acceptance_criteria"],
        "expected_outputs":["five-source candidate reduction evidence","direct per-file GGUF quantization alternatives","compact combined Docling replacement comparison","global gross-byte gate","CUSTOSZ V9 queue event chain"],
        "validation_strategy":"pinned_original_hashes+append_only_scope+V9_CRUF+systemd_resource_scope+exact_candidate_byte_sums",
        "evidence_requirements":["mission/source/worker/test SHA-256","prelaunch checkpoint","resource scope","queue hash chain","exact candidate sizes","source hashes unchanged"],
        "checkpoint_reference":str(STATE/"checkpoints"),"rollback_strategy":"all writes isolated to a fresh candidate staging path; source originals remain read-only",
        "completion_condition":"all five source entries have an explicit candidate or recorded failure and the global size gate is measured",
        "escalation_condition":"HOLD_FAIL_CLOSED on source pin mismatch, missing scope, resource cap failure, original mutation, or any selected bundle above 30000000 bytes",
        "authorization_evidence_reference":str(AUTH)}
    qpath=STATE/"inteldoc_global_30mb_corrective_v7_queue.sqlite3"
    q=PersistentMissionQueue(qpath)
    sub=q.submit(task)
    if sub.get("state")!="RECEIVED": raise RuntimeError("QUEUE_SUBMIT_FAIL:"+str(sub))
    q.transition(task_id,"RECEIVED","PREFLIGHT",event_type="INTELDOC_CORRECTIVE_PREFLIGHT_STARTED",
        payload={"mission_sha256":EXPECTED_MISSION_SHA,"source_inventory":src})
    raw_resource_probe=probe_host_resources(OP)
    mem_available_bytes=ram_available()
    # ResourceSnapshot is an immutable dataclass; preserve its interface for the V9 coordinator and override only the RAM metric with Linux MemAvailable.
    snapshot=replace(raw_resource_probe,
        ram_available_bytes=mem_available_bytes,
        source="proc:/proc/meminfo:MemAvailable (raw SC_AVPHYS_PAGES="+str(raw_resource_probe.ram_available_bytes)+")",
        measured_at_utc=utc())
    resource_probe_ok=(mem_available_bytes is not None and mem_available_bytes >= int(task["resource_budget"]["ram_required_bytes"])
        and snapshot.disk_available_bytes is not None and snapshot.disk_available_bytes >= int(task["resource_budget"]["disk_required_bytes"])
        and snapshot.cpu_count is not None)
    checks={"v9_sha":sha(V9)==EXPECTED_V9_SHA,"mission_sha":sha(MISSION)==EXPECTED_MISSION_SHA,
        "worker_sha":sha(WORKER)==EXPECTED_WORKER_SHA,"test_sha":sha(TEST)==EXPECTED_TEST_SHA,
        "source_hashes":True,"ram_headroom":ram_available()>=int(task["resource_budget"]["ram_required_bytes"]),
        "scope_authorization":verify_authorization(task).get("status")=="PASS","global_cap":spec["global_limit"]["hard_cap_bytes"]==30000000}
    checks["resource_snapshot_valid"]=resource_probe_ok
    if not all(checks.values()):
        q.transition(task_id,"PREFLIGHT","BLOCKED",event_type="INTELDOC_CORRECTIVE_PREFLIGHT_BLOCKED",payload={"checks":checks,
            "effective_resource_probe":snapshot.to_dict(),"raw_resource_probe":raw_resource_probe.to_dict()})
        raise RuntimeError("CORRECTIVE_PREFLIGHT_BLOCKED:"+json.dumps(checks))
    q.transition(task_id,"PREFLIGHT","READY",event_type="INTELDOC_CORRECTIVE_PREFLIGHT_PASS",payload={"checks":checks})
    claimed=q.claim_next_ready()
    if not isinstance(claimed,dict) or claimed.get("state")!="RUNNING": raise RuntimeError("QUEUE_CLAIM_FAIL:"+str(claimed))
    acts=[ActionSpec("verify_all_five_pinned_sources",(),("LOCAL_FILE_READ","HASH_STREAMING"),("READ_PROJECT_ARTIFACTS",),"READ_ONLY"),
          ActionSpec("launch_bounded_five_artifact_worker",("verify_all_five_pinned_sources",),
             ("CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE"),("WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"),"IDEMPOTENT")]
    def runner(payload):
        aid=payload["action"]["action_id"]
        if aid=="verify_all_five_pinned_sources":
            now=source_inventory()
            return {"status":"PASS","source_inventory":now,"original_total_bytes":sum(v["bytes"] for v in now.values()),
                "ram_available_bytes":ram_available(),"global_cap_bytes":30000000}
        if aid=="launch_bounded_five_artifact_worker":
            try: return launch(payload["task"],src)
            except Exception as e: return {"status":"HOLD","reason":type(e).__name__+":"+str(e),"certification":"NOT_GRANTED"}
        return {"status":"DENIED","reason":"ACTION_NOT_REGISTERED"}
    coord=run_bounded_mission(task,acts,snapshot,
        available_capabilities=set(readj(BINDING).get("capabilities",[]))|{"LOCAL_FILE_READ","HASH_STREAMING"},
        admissible_effects={"READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"},
        authorization_verifier=verify_authorization,action_runner=runner,maximum_steps=2,planning_budget=3)
    final="COMPLETED" if coord.get("status")=="COMPLETED" else "BLOCKED"
    q.transition(task_id,"RUNNING",final,event_type="INTELDOC_CORRECTIVE_LAUNCH_RECORDED" if final=="COMPLETED" else "INTELDOC_CORRECTIVE_LAUNCH_BLOCKED",
        payload={"coordinator_status":coord.get("status"),"worker_mission_status":"RUNNING_OR_HELD","canonical_promotion":"NOT_AUTHORIZED"})
    chain=q.verify_event_chain()
    report={"schema":"INTELDOC_FIVE_ARTIFACT_CORRECTIVE_DISPATCH/1.0","timestamp_utc":utc(),"task_id":task_id,
        "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,
        "dispatcher_sha256":sha(pathlib.Path(__file__)),"custoszv9_sha256":EXPECTED_V9_SHA,
        "preflight_checks":checks,"raw_resource_probe":raw_resource_probe.to_dict(),"effective_resource_probe":snapshot.to_dict(),
        "coordinator_result":coord,"queue_path":str(qpath),"queue_final_state":final,
        "queue_event_chain":chain,"global_cap_bytes":30000000,"github":{"repository":REPO,"branch":BRANCH,"path_prefix":GH_PREFIX},
        "original_sources_modified":False,"functional_smoke":"DEFERRED_BY_USER","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
    p=OUT/("INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V8_DISPATCH_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
    atomic(p,report,exclusive=True)
    print(json.dumps({"status":final,"task_id":task_id,"coordinator_status":coord.get("status"),
        "queue_event_chain":chain.get("status"),"report_path":str(p),"report_sha256":sha(p),
        "launch_result":coord.get("actions"),"global_cap_bytes":30000000,"certification":"NOT_GRANTED"},indent=2),flush=True)
    return 0 if final=="COMPLETED" and chain.get("status")=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
