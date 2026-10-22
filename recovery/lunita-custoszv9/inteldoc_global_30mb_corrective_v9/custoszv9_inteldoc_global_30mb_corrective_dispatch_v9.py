#!/usr/bin/env python3
"""CUSTOSZ V9 CRFU dispatch for corrective V9 structural candidate. No tests are dispatched."""
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, subprocess, sys, time, uuid
from dataclasses import replace

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
BASE=HOME/"PROYECTOS/1. PROYECTOS PRIORITARIOS"
OP=BASE/"5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT=OP/"CUSTOSZ_CONTINUITY_V1"; STATE=CONT/"state"; OUT=STATE/"worker_outputs"
V9=OP/"CUSTOSZV9.pyz"
LANE=STATE/"jobs/inteldoc_global_30mb_corrective_v9"
MISSION=LANE/"INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json"
WORKER=LANE/"inteldoc_five_artifact_corrective_worker_v7.py"
ADDENDUM=LANE/"GLOBAL_SCOPE_REPAIR_ADDENDUM_V9.json"
AUTH=CONT/"operator_authorization.json"; CONTRACT=CONT/"contract.json"; BINDING=CONT/"worker_binding_v2.json"
WORKER_ROOT=STATE/"jobs/inteldoc_global_30mb_corrective_worker_v9"
EXPECTED_V9_SHA="667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
EXPECTED_MISSION_SHA="2effd53160f5f43e7999feb4582e6002b0a7af170672b2b30fe7029ecb6f1ef0"
EXPECTED_WORKER_SHA="48bb8e82a1df5d83ef93f1658f60d1f4ef7db92fa01aca6a47940879e1cbcec7"
SCOPE_ID="INTELDOC_GLOBAL_30MB_CORRECTIVE_V9"
ADDENDUM_ID="GITHUB_INTELDOC_GLOBAL_30MB_CORRECTIVE_REPAIR_V9_SCOPE_20261021"
REPO="Plomillo/luna-linux-bridge"; BRANCH="recovery/lunita-custoszv9-operational-20261020"
GH_PREFIX="recovery/lunita-custoszv9/inteldoc_global_30mb_corrective_v9/"
PYTHON="/usr/bin/python3"
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
        result[x["id"]]={"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p),"read_only":True}
    return result
def verify_authorization(task):
    try:
        auth=readj(AUTH); con=readj(CONTRACT); bind=readj(BINDING); add=readj(ADDENDUM)
        aa=[x for x in auth.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
        ca=[x for x in con.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
        if len(aa)!=1 or len(ca)!=1 or aa[0]!=ca[0] or aa[0]!=add:
            return {"status":"DENIED","reason":"V9_SCOPE_MISSING_OR_MISMATCHED"}
        expected_paths={GH_PREFIX+n for n in [
          "INTELDOC_GLOBAL_30MB_CORRECTIVE_MISSION.json",
          "inteldoc_five_artifact_corrective_worker_v7.py",
          "custoszv9_inteldoc_five_artifact_corrective_dispatch_v9.py",
          "GLOBAL_SCOPE_REPAIR_ADDENDUM_V9.json",
          "INTELDOC_GLOBAL_30MB_CORRECTIVE_V9_LAUNCH_RECEIPT.json",
          "INTELDOC_GLOBAL_30MB_CORRECTIVE_V9_RESULT.json"]}
        if not expected_paths.issubset(set(add.get("allowed_paths",[]))):
            return {"status":"DENIED","reason":"V9_PATH_ALLOWLIST_MISMATCH"}
        expected={"repository":REPO,"branch":BRANCH,"mission_id":"CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V2",
            "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),
            "custoszv9_sha256":EXPECTED_V9_SHA}
        for k,v in expected.items():
            if add.get(k)!=v: return {"status":"DENIED","reason":"V9_PIN_MISMATCH","field":k,"expected":v,"actual":add.get(k)}
        checks={"v9_sha":sha(V9)==EXPECTED_V9_SHA,"mission_sha":sha(MISSION)==EXPECTED_MISSION_SHA,
          "worker_sha":sha(WORKER)==EXPECTED_WORKER_SHA,"binding_validated":bind.get("status")=="VALIDATED",
          "mission_scope":task.get("authorized_scope")==SCOPE_ID,"branch_scope":add.get("branch")==BRANCH}
        if not all(checks.values()): return {"status":"DENIED","reason":"V9_PIN_OR_BINDING_CHECK_FAILED","checks":checks}
        return {"status":"PASS","checks":checks,"task_id":task.get("task_id"),
          "no_canonical_promotion":True,"no_certification_authority":True}
    except Exception as e:
        return {"status":"DENIED","reason":type(e).__name__+":"+str(e)}
def launch_worker(task,inventory):
    if WORKER_ROOT.exists() and any(WORKER_ROOT.iterdir()):
        return {"status":"HOLD","reason":"V9_WORKER_ROOT_NONEMPTY_NO_OVERWRITE","path":str(WORKER_ROOT)}
    now=source_inventory()
    if now!=inventory: return {"status":"HOLD","reason":"SOURCE_INVENTORY_CHANGED_BEFORE_LAUNCH"}
    mem=ram_available()
    if mem < 512*1024**2: return {"status":"HOLD","reason":"RAM_HEADROOM_BELOW_512MIB","ram_available_bytes":mem}
    if shutil_disk_free(OP) < 512*1024**2: return {"status":"HOLD","reason":"DISK_HEADROOM_BELOW_512MIB"}
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    cp=STATE/"checkpoints"/("INTELDOC_GLOBAL_30MB_V9_PRESTART_"+stamp); cp.mkdir(parents=True,exist_ok=False,mode=0o700)
    checkpoint={"schema":"INTELDOC_GLOBAL_30MB_V9_PRESTART/1.0","timestamp_utc":utc(),
        "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),
        "custoszv9_sha256":EXPECTED_V9_SHA,"source_inventory":inventory,"source_files_modified":False,
        "resources":{"mem_available_bytes":mem,"disk_free_bytes":shutil_disk_free(OP),"max_concurrency":1},
        "functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","runtime_smoke":"NOT_RUN_BY_USER_INSTRUCTION",
        "canonical_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED"}
    atomic(cp/"MANIFEST.json",checkpoint,exclusive=True)
    guard={"schema":"INTELDOC_V9_LAUNCH_GUARD/1.0","created_at_utc":utc(),"task_id":task["task_id"],
        "mission_sha256":EXPECTED_MISSION_SHA,"source_inventory":inventory}
    atomic(WORKER_ROOT/"LAUNCH_GUARD.json",guard,exclusive=True)
    unit="custosz9-idoc-corrective-v9-"+stamp.lower()
    log=WORKER_ROOT.parent/"inteldoc_global_30mb_corrective_worker_v9_startup.log"
    with log.open("xb") as lf:
        proc=subprocess.Popen(["sudo","-n","systemd-run","--scope","--unit="+unit,
          "-p","MemoryHigh=768M","-p","MemoryMax=1G","-p","CPUQuota=35%","-p","TasksMax=24",
          PYTHON,"-B",str(WORKER)],cwd=str(OP),
          env={**os.environ,"OMP_NUM_THREADS":"1","OMP_THREAD_LIMIT":"1","OPENBLAS_NUM_THREADS":"1",
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
    result_path=WORKER_ROOT/"result.json"
    running=props.get("ActiveState") in {"active","activating"}
    finished=result_path.is_file()
    if not running and not finished:
        return {"status":"HOLD","reason":"SYSTEMD_WORKER_NOT_CONFIRMED","wrapper_pid":proc.pid,"unit":unit+".scope","properties":props,"log":str(log)}
    receipt={"schema":"INTELDOC_GLOBAL_30MB_CORRECTIVE_V9_LAUNCH_RECEIPT/1.0","timestamp_utc":utc(),
        "task_id":task["task_id"],"mission_id":task["mission_id"],"mission_sha256":EXPECTED_MISSION_SHA,
        "worker_sha256":EXPECTED_WORKER_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),"custoszv9_sha256":EXPECTED_V9_SHA,
        "source_inventory":inventory,"wrapper_pid":proc.pid,"systemd_unit":unit+".scope","systemd_properties":props,
        "systemd_resource_caps":{"MemoryHigh":"768M","MemoryMax":"1G","CPUQuota":"35%","TasksMax":"24"},
        "worker_state_dir":str(WORKER_ROOT),"worker_log":str(log),"prestart_checkpoint":str(cp),
        "functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","runtime_smoke":"NOT_RUN_BY_USER_INSTRUCTION",
        "certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED",
        "worker_execution_state":"RUNNING" if running else "FINISHED_RESULT_PRESENT"}
    path=OUT/"INTELDOC_GLOBAL_30MB_CORRECTIVE_V9_LAUNCH_RECEIPT.json"
    atomic(path,receipt,exclusive=True)
    return {"status":"PASS","worker_launch_status":"STARTED" if running else "FINISHED_RESULT_PRESENT",
        "receipt_path":str(path),"receipt_sha256":sha(path),"worker_result_path":str(result_path),
        "unit":unit+".scope","systemd_properties":props}
def shutil_disk_free(path):
    import shutil
    return shutil.disk_usage(path).free
def main():
    OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
    if sha(V9)!=EXPECTED_V9_SHA: raise RuntimeError("CUSTOSZ_V9_HASH_MISMATCH")
    spec=readj(MISSION)
    if spec.get("mission_id")!="CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V2" or spec.get("global_limit",{}).get("hard_cap_bytes")!=30000000:
        raise RuntimeError("MISSION_ID_OR_HARD_CAP_MISMATCH")
    src=source_inventory()
    sys.path.insert(0,str(V9))
    from custoszv9.crfu.coordinator import run_bounded_mission
    from custoszv9.crfu.event_queue import PersistentMissionQueue
    from custoszv9.crfu.planner import ActionSpec
    from custoszv9.crfu.resources import probe_host_resources
    task_id="CUSTOSZV9_INTELDOC_FIVE_ARTIFACT_CORRECTIVE_V2_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    task={"task_id":task_id,"mission_id":spec["mission_id"],"project_id":"CAJITA_DE_LUNA_INTELDOC_GLOBAL",
      "source_identity":"CUSTOSZV9.pyz:"+EXPECTED_V9_SHA,"target_identity":"GLOBAL_CANDIDATE_AND_REQUIRED_DEPENDENCIES_MAX_30000000_BYTES",
      "source_state_hash":EXPECTED_MISSION_SHA,"dependency_set":["MISSION:"+EXPECTED_MISSION_SHA,"WORKER:"+EXPECTED_WORKER_SHA,"V9:"+EXPECTED_V9_SHA],
      "authorized_scope":SCOPE_ID,"required_capabilities":["LOCAL_FILE_READ","HASH_STREAMING","CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE","V9_CRUF_PLANNING"],
      "inputs":{"mission_path":str(MISSION),"worker_path":str(WORKER),"worker_state":str(WORKER_ROOT),"hard_cap_bytes":30000000,"source_inventory":src},
      "preconditions":["pinned CUSTOSZ V9, mission, and worker verified","new exact-path local scope is present identically in auth and contract",
        "all five originals match byte and SHA-256 pins","fresh worker state is empty","RAM headroom at least 512 MiB","resource-limited systemd scope available"],
      "permitted_effects":["READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"],
      "resource_budget":{"ram_required_bytes":268435456,"ram_reserved_bytes":268435456,"disk_required_bytes":536870912,"max_concurrency":1},
      "execution_deadline":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=2)).isoformat(),
      "maximum_planning_budget":3,"maximum_retry_budget":0,
      "acceptance_criteria":spec["acceptance_criteria"],
      "expected_outputs":["fresh compact candidate payload","exact artifact and dependency byte sums","original SHA pins preserved","functional tests not run"],
      "validation_strategy":"source SHA-256 pins + exact authorization scope + resource-limited dispatch + exact filesystem byte accounting",
      "evidence_requirements":["mission/worker/dispatcher/V9 hashes","prelaunch checkpoint","resource scope","queue event chain","exact candidate size","source hashes unchanged"],
      "checkpoint_reference":str(STATE/"checkpoints"),"rollback_strategy":"fresh isolated candidate staging only; originals read-only",
      "completion_condition":"worker starts successfully and records a size-gated candidate without running functional tests",
      "escalation_condition":"HOLD on authorization/pin/resource failure or any source mutation","authorization_evidence_reference":str(AUTH)}
    qpath=STATE/"inteldoc_global_30mb_corrective_v9_queue.sqlite3"; q=PersistentMissionQueue(qpath)
    sub=q.submit(task)
    if sub.get("state")!="RECEIVED": raise RuntimeError("QUEUE_SUBMIT_FAIL:"+str(sub))
    q.transition(task_id,"RECEIVED","PREFLIGHT",event_type="INTELDOC_GLOBAL_30MB_V9_PREFLIGHT_STARTED",
        payload={"mission_sha256":EXPECTED_MISSION_SHA,"source_inventory":src})
    raw=probe_host_resources(OP); mem=ram_available()
    snapshot=replace(raw,ram_available_bytes=mem,source="proc:/proc/meminfo:MemAvailable",measured_at_utc=utc())
    checks={"v9_sha":sha(V9)==EXPECTED_V9_SHA,"mission_sha":sha(MISSION)==EXPECTED_MISSION_SHA,
      "worker_sha":sha(WORKER)==EXPECTED_WORKER_SHA,"source_hashes":True,
      "ram_headroom":mem>=int(task["resource_budget"]["ram_required_bytes"]),
      "scope_authorization":verify_authorization(task).get("status")=="PASS",
      "global_cap":spec["global_limit"]["hard_cap_bytes"]==30000000,
      "worker_state_fresh":WORKER_ROOT.exists() and not any(WORKER_ROOT.iterdir())}
    checks["resource_snapshot_valid"]=(snapshot.disk_available_bytes is not None and snapshot.disk_available_bytes>=int(task["resource_budget"]["disk_required_bytes"])
      and snapshot.cpu_count is not None and mem>=int(task["resource_budget"]["ram_required_bytes"]))
    if not all(checks.values()):
        q.transition(task_id,"PREFLIGHT","BLOCKED",event_type="INTELDOC_GLOBAL_30MB_V9_PREFLIGHT_BLOCKED",
          payload={"checks":checks,"resource_snapshot":snapshot.to_dict()})
        raise RuntimeError("V9_PREFLIGHT_BLOCKED:"+json.dumps(checks))
    q.transition(task_id,"PREFLIGHT","READY",event_type="INTELDOC_GLOBAL_30MB_V9_PREFLIGHT_PASS",payload={"checks":checks})
    claimed=q.claim_next_ready()
    if not isinstance(claimed,dict) or claimed.get("state")!="RUNNING": raise RuntimeError("QUEUE_CLAIM_FAIL:"+str(claimed))
    acts=[ActionSpec("verify_five_pinned_sources",(),("LOCAL_FILE_READ","HASH_STREAMING"),("READ_PROJECT_ARTIFACTS",),"READ_ONLY"),
      ActionSpec("launch_v9_structural_candidate_worker",("verify_five_pinned_sources",),
        ("CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE"),("WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"),"IDEMPOTENT")]
    def runner(payload):
        aid=payload["action"]["action_id"]
        if aid=="verify_five_pinned_sources":
            n=source_inventory()
            return {"status":"PASS","source_inventory":n,"original_total_bytes":sum(v["bytes"] for v in n.values()),
              "ram_available_bytes":ram_available(),"hard_cap_bytes":30000000}
        if aid=="launch_v9_structural_candidate_worker":
            try: return launch_worker(payload["task"],src)
            except Exception as e: return {"status":"HOLD","reason":type(e).__name__+":"+str(e)}
        return {"status":"DENIED","reason":"ACTION_NOT_REGISTERED"}
    coord=run_bounded_mission(task,acts,snapshot,
      available_capabilities=set(readj(BINDING).get("capabilities",[]))|{"LOCAL_FILE_READ","HASH_STREAMING"},
      admissible_effects={"READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"},
      authorization_verifier=verify_authorization,action_runner=runner,maximum_steps=2,planning_budget=3)
    final="COMPLETED" if coord.get("status")=="COMPLETED" else "BLOCKED"
    q.transition(task_id,"RUNNING",final,event_type="INTELDOC_GLOBAL_30MB_V9_LAUNCH_RECORDED" if final=="COMPLETED" else "INTELDOC_GLOBAL_30MB_V9_LAUNCH_BLOCKED",
      payload={"coordinator_status":coord.get("status"),"worker_mission_status":"RUNNING_OR_RESULT_PENDING","canonical_promotion":"NOT_AUTHORIZED"})
    chain=q.verify_event_chain()
    report={"schema":"INTELDOC_GLOBAL_30MB_V9_DISPATCH/1.0","timestamp_utc":utc(),"task_id":task_id,
      "mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),
      "custoszv9_sha256":EXPECTED_V9_SHA,"preflight_checks":checks,"raw_resource_probe":raw.to_dict(),"effective_resource_probe":snapshot.to_dict(),
      "coordinator_result":coord,"queue_path":str(qpath),"queue_final_state":final,"queue_event_chain":chain,
      "global_cap_bytes":30000000,"github_scope":{"repository":REPO,"branch":BRANCH,"path_prefix":GH_PREFIX},
      "original_sources_modified":False,"functional_tests":"NOT_RUN_BY_USER_INSTRUCTION","runtime_smoke":"NOT_RUN_BY_USER_INSTRUCTION",
      "certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
    p=OUT/("INTELDOC_GLOBAL_30MB_V9_DISPATCH_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
    atomic(p,report,exclusive=True)
    print(json.dumps({"status":final,"task_id":task_id,"coordinator_status":coord.get("status"),
      "queue_event_chain":chain.get("status"),"report_path":str(p),"report_sha256":sha(p),
      "launch_result":coord.get("actions"),"global_cap_bytes":30000000,"functional_tests":"NOT_RUN"},indent=2),flush=True)
    return 0 if final=="COMPLETED" and chain.get("status")=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())