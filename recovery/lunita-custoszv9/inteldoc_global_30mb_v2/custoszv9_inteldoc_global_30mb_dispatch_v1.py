#!/usr/bin/env python3
"""CUSTOSZ V9 CRFU dispatcher for the complete Intelligence Documental 30 MB mission."""
from __future__ import annotations
import datetime as dt,hashlib,json,os,pathlib,subprocess,sys,time,uuid

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
OP=HOME/"Proyectos/1. PROYECTOS PRIORITARIOS/5. CUSTOSZ/0. CUSTOSZ  - OPERADOR"
CONT=OP/"CUSTOSZ_CONTINUITY_V1"; STATE=CONT/"state"; OUT=STATE/"worker_outputs"
V9=OP/"CUSTOSZV9.pyz"; MISSION=STATE/"jobs/inteldoc_global_30mb_lane_v1/INTELDOC_GLOBAL_30MB_MISSION.json"
WORKER=STATE/"jobs/inteldoc_global_30mb_lane_v1/inteldoc_global_30mb_worker_v1.py"
TEST=STATE/"jobs/inteldoc_global_30mb_lane_v1/test_inteldoc_global_30mb_contract.py"
AUTH=CONT/"operator_authorization.json"; CONTRACT=CONT/"contract.json"; BINDING=CONT/"worker_binding_v2.json"
WORKER_ROOT=STATE/"jobs/inteldoc_global_30mb_worker_v1"
EXPECTED_V9_SHA="667ceac7d7e59682292c864777ec3e1c228074716dc5dba17fe150e4d826ccf3"
EXPECTED_MISSION_SHA="8fc05771b2c33980278adc830a5b0ddd7fb72767dc215f9c75cd4007b4ac5222"
EXPECTED_WORKER_SHA="ec12fcac87564c531bf6d0d0004b306b9bafc6ba1fa8ce64d3769f926caf82e8"
EXPECTED_TEST_SHA="827ae3966a394dbe4ef559a295ff1913da5d058a192dbc64fd9fe33324d81b4a"
SCOPE_ID="INTELDOC_GLOBAL_30MB_V2"
ADDENDUM_ID="GITHUB_INTELDOC_GLOBAL_30MB_SCOPE_20261021"
REPO="Plomillo/luna-linux-bridge"; BRANCH="recovery/lunita-custoszv9-operational-20261020"
GH_PREFIX="recovery/lunita-custoszv9/inteldoc_global_30mb_v2/"
PYTHON=CONT/"state/tools/venvs/llama-cpp-b10819-py313/bin/python"
def utc(): return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def canon(x): return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=False,allow_nan=False).encode()
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
 with tmp.open("x",encoding="utf-8") as f: json.dump(obj,f,sort_keys=True,indent=2,ensure_ascii=False); f.write("\n"); f.flush(); os.fsync(f.fileno())
 os.chmod(tmp,0o600); os.replace(tmp,p)
def ram_available():
 for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
  if line.startswith("MemAvailable:"): return int(line.split()[1])*1024
 return 0
def source_inventory():
 spec=readj(MISSION); root=pathlib.Path(spec["inventory"]["source_root"]); result={}
 for x in spec["inventory"]["pinned_originals"]:
  p=root/x["path"]
  if not p.is_file() or p.stat().st_size!=x["bytes"] or sha(p)!=x["sha256"]: raise RuntimeError("SOURCE_PIN_MISMATCH:"+x["id"])
  result[x["id"]]={"path":str(p),"bytes":x["bytes"],"sha256":x["sha256"],"read_only":True}
 return result
def verify_authorization(task):
 try:
  auth=readj(AUTH); con=readj(CONTRACT); bind=readj(BINDING)
  a=[x for x in auth.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
  c=[x for x in con.get("authorized_scope_addenda",[]) if x.get("addendum_id")==ADDENDUM_ID]
  if len(a)!=1 or len(c)!=1 or a[0]!=c[0]: return {"status":"DENIED","reason":"GLOBAL_SCOPE_ADDENDUM_MISSING_OR_MISMATCHED"}
  item=a[0]; paths=set(item.get("allowed_paths",[]))
  expected={GH_PREFIX+n for n in ["INTELDOC_GLOBAL_30MB_MISSION.json","inteldoc_global_30mb_worker_v1.py","custoszv9_inteldoc_global_30mb_dispatch_v1.py","test_inteldoc_global_30mb_contract.py","GLOBAL_SCOPE_ADDENDUM.json","INTELDOC_GLOBAL_30MB_LAUNCH_RECEIPT.json","INTELDOC_GLOBAL_30MB_RESULT.json"]}
  if not expected.issubset(paths) or item.get("branch")!=BRANCH or item.get("repository")!=REPO or item.get("mission_sha256")!=EXPECTED_MISSION_SHA: return {"status":"DENIED","reason":"GLOBAL_SCOPE_ADDENDUM_FIELDS_MISMATCH"}
  checks={"v9":sha(V9)==EXPECTED_V9_SHA,"mission":sha(MISSION)==EXPECTED_MISSION_SHA,"worker":sha(WORKER)==EXPECTED_WORKER_SHA,"test":sha(TEST)==EXPECTED_TEST_SHA,"binding":bind.get("status")=="VALIDATED","mission_scope":task.get("authorized_scope")==SCOPE_ID}
  if not all(checks.values()): return {"status":"DENIED","reason":"PIN_OR_BINDING_CHECK_FAILED","checks":checks}
  return {"status":"PASS","task_id":task.get("task_id"),"checks":checks,"scope":SCOPE_ID,"mission_sha256":EXPECTED_MISSION_SHA,"v9_sha256":EXPECTED_V9_SHA,"no_canonical_promotion":True,"no_certification_authority":True}
 except Exception as e: return {"status":"DENIED","reason":type(e).__name__+":"+str(e)}
def worker_active():
 p=WORKER_ROOT/"worker.lock"
 if not p.exists(): return False
 try: os.kill(int(p.read_text().strip()),0); return True
 except (ValueError,ProcessLookupError,PermissionError,FileNotFoundError): return False
def launch(task,inventory,qpath):
 if WORKER_ROOT.exists(): return {"status":"HOLD","reason":"GLOBAL_WORKER_STATE_ALREADY_EXISTS_NO_OVERWRITE","path":str(WORKER_ROOT)}
 if ram_available()<2*1024**3: return {"status":"HOLD","reason":"RAM_HEADROOM_BELOW_2_GIB","ram_available_bytes":ram_available()}
 if not PYTHON.is_file() or not WORKER.is_file(): return {"status":"HOLD","reason":"PINNED_RUNTIME_OR_WORKER_MISSING"}
 if worker_active(): return {"status":"HOLD","reason":"GLOBAL_WORKER_ALREADY_ACTIVE"}
 stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
 cp=STATE/"checkpoints"/("INTELDOC_GLOBAL_30MB_PRESTART_"+stamp); cp.mkdir(parents=True,exist_ok=False,mode=0o700)
 check={"schema":"INTELDOC_GLOBAL_30MB_PRESTART/1.0","timestamp_utc":utc(),"mission_sha256":EXPECTED_MISSION_SHA,
  "worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),
  "custoszv9_sha256":EXPECTED_V9_SHA,"source_inventory":inventory,"source_files_modified":False,
  "resource_limits":{"MemoryHigh":805306368,"MemoryMax":1073741824,"CPUQuotaPercent":35,"TasksMax":24,"concurrency":1},
  "github":{"repository":REPO,"branch":BRANCH,"path_prefix":GH_PREFIX},"functional_smoke":"DEFERRED_BY_USER",
  "certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
 atomic(cp/"MANIFEST.json",check,exclusive=True); cp_hash=sha(cp/"MANIFEST.json")
 unit="custosz-inteldoc30-"+stamp.lower()
 log=WORKER_ROOT.parent/"inteldoc_global_30mb_worker_v1_startup.log"
 WORKER_ROOT.mkdir(parents=True,exist_ok=False,mode=0o700)
 with log.open("ab") as lf:
  proc=subprocess.Popen(["sudo","-n","systemd-run","--scope","--unit="+unit,
   "-p","MemoryHigh=768M","-p","MemoryMax=1G","-p","CPUQuota=35%","-p","TasksMax=24",
   str(PYTHON),"-B",str(WORKER),"--run","--job-dir",str(WORKER_ROOT)],
   cwd=str(OP),env={**os.environ,"OMP_NUM_THREADS":"1","OMP_THREAD_LIMIT":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","TOKENIZERS_PARALLELISM":"false"},
   stdout=lf,stderr=subprocess.STDOUT,start_new_session=True,close_fds=True)
 props={}; active=None
 for _ in range(20):
  q=subprocess.run(["systemctl","show",unit+".scope","--property=ActiveState","--property=MainPID","--property=MemoryMax","--property=MemoryHigh","--property=CPUQuotaPerSecUSec","--no-pager"],capture_output=True,text=True,timeout=5,check=False)
  if q.returncode==0:
   for line in q.stdout.splitlines():
    if "=" in line: k,v=line.split("=",1); props[k]=v
   active=props.get("ActiveState")
   if active in {"active","activating"}: break
  time.sleep(.2)
 if active not in {"active","activating"}: return {"status":"HOLD","reason":"SYSTEMD_RESOURCE_SCOPE_NOT_CONFIRMED","wrapper_pid":proc.pid,"scope_properties":props,"log":str(log),"checkpoint":str(cp)}
 for _ in range(30):
  if worker_active(): break
  time.sleep(.2)
 if not worker_active(): return {"status":"HOLD","reason":"WORKER_LOCK_NOT_CONFIRMED","wrapper_pid":proc.pid,"unit":unit+".scope","properties":props,"log":str(log),"checkpoint":str(cp)}
 prog={}
 for _ in range(80):
  pp=WORKER_ROOT/"progress.json"
  childp=WORKER_ROOT/"docling_component_run"/"progress.json"
  if childp.is_file():
   try:
    childprog=readj(childp)
    if childprog.get("phase")=="QUANTIZING" and childprog.get("tensors_done",0)>=1:
     prog={"phase":"DOCLING_TENSOR_QUANTIZATION_STARTED","status":childprog.get("status"),
       "tensors_done":childprog.get("tensors_done"),"source_tensor_count":childprog.get("source_tensor_count")}
     break
   except Exception: pass
  if pp.is_file():
   try: prog=readj(pp)
   except Exception: pass
  time.sleep(.25)
 receipt={"schema":"INTELDOC_GLOBAL_30MB_LAUNCH_RECEIPT/1.0","timestamp_utc":utc(),"task_id":task["task_id"],
  "mission_id":task["mission_id"],"mission_sha256":EXPECTED_MISSION_SHA,"worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,
  "dispatcher_sha256":sha(pathlib.Path(__file__)),"custoszv9_sha256":EXPECTED_V9_SHA,"source_inventory":inventory,
  "worker_pid":int((WORKER_ROOT/"worker.lock").read_text().strip()),"wrapper_pid":proc.pid,"systemd_unit":unit+".scope",
  "systemd_properties":props,"resource_caps_confirmed":props.get("MemoryMax") in {"1073741824","1G"} and props.get("MemoryHigh") in {"805306368","768M"},
  "worker_state_dir":str(WORKER_ROOT),"worker_log":str(log),"prestart_checkpoint":str(cp),"prestart_checkpoint_sha256":cp_hash,
  "observed_phase":prog.get("phase","INITIALIZING"),"observed_status":prog.get("status","UNKNOWN"),
  "runtime_smoke":"DEFERRED_BY_USER","source_files_modified":False,"global_goal_bytes":30000000,
  "canonical_promotion":"NOT_AUTHORIZED","certification":"NOT_GRANTED","mission_completion_claim":False}
 dest=OUT/"INTELDOC_GLOBAL_30MB_LAUNCH_RECEIPT.json"
 atomic(dest,receipt,exclusive=True); receipt["launch_receipt_path"]=str(dest); receipt["launch_receipt_sha256"]=sha(dest)
 return {"status":"PASS","worker_launch_status":"STARTED_RESOURCE_LIMITED","receipt":receipt,"receipt_path":str(dest),"receipt_sha256":sha(dest)}
def main():
 OUT.mkdir(parents=True,exist_ok=True,mode=0o700)
 if sha(V9)!=EXPECTED_V9_SHA: raise RuntimeError("CUSTOSZ_V9_HASH_MISMATCH")
 spec=readj(MISSION)
 if spec.get("mission_id")!="CUSTOSZV9_INTELDOC_GLOBAL_30MB_V2" or spec.get("global_limit",{}).get("hard_cap_bytes")!=30000000: raise RuntimeError("GLOBAL_MISSION_ID_OR_CAP_MISMATCH")
 src=source_inventory()
 if WORKER_ROOT.exists(): raise RuntimeError("GLOBAL_WORKER_STATE_EXISTS_NO_OVERWRITE")
 if str(V9) not in sys.path: sys.path.insert(0,str(V9))
 from custoszv9.crfu.coordinator import run_bounded_mission
 from custoszv9.crfu.event_queue import PersistentMissionQueue
 from custoszv9.crfu.planner import ActionSpec
 from custoszv9.crfu.resources import probe_host_resources
 task_id="CUSTOSZV9_INTELDOC_GLOBAL_30MB_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
 task={"task_id":task_id,"mission_id":spec["mission_id"],"project_id":"CAJITA_DE_LUNA_INTELDOC_GLOBAL",
  "source_identity":"CUSTOSZV9.pyz:"+EXPECTED_V9_SHA,"target_identity":"INTELDOC_GLOBAL_OPERATIONAL_CANDIDATE_MAX_30000000_BYTES",
  "source_state_hash":EXPECTED_MISSION_SHA,"dependency_set":["MISSION:"+EXPECTED_MISSION_SHA,"WORKER:"+EXPECTED_WORKER_SHA,"TEST:"+EXPECTED_TEST_SHA,"V9:"+EXPECTED_V9_SHA],
  "authorized_scope":SCOPE_ID,"required_capabilities":["LOCAL_FILE_READ","HASH_STREAMING","CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE","V9_CRUF_PLANNING"],
  "inputs":{"mission_path":str(MISSION),"worker_path":str(WORKER),"worker_state":str(WORKER_ROOT),"hard_cap_bytes":30000000,"source_inventory":src,"github_repository":REPO,"github_branch":BRANCH},
  "preconditions":["pinned V9, mission, worker and test verified","scope addendum exists in local authorization and contract","all original sources match exact size and SHA-256","no existing global worker state","host RAM headroom at least 2 GiB","worker runs with MemoryMax 1 GiB, MemoryHigh 768 MiB, CPUQuota 35%"],
  "permitted_effects":["READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"],
  "resource_budget":{"ram_required_bytes":134217728,"ram_reserved_bytes":268435456,"disk_required_bytes":805306368,"max_concurrency":1},
  "execution_deadline":(dt.datetime.now(dt.timezone.utc)+dt.timedelta(hours=2)).isoformat(),"maximum_planning_budget":3,"maximum_retry_budget":0,
  "acceptance_criteria":["CUSTOSZ V9 CRFU starts bounded global worker","all artifacts are handled under one global byte budget","functional smoke remains deferred until all quantization/reduction work is complete","sources unchanged","hard global gate fails closed above 30000000 bytes"],
  "expected_outputs":["global worker lock and progress","Docling aggressive quantization candidate","Calibre minimized candidate","global gross size-gate report","CUSTOSZ V9 queue event chain"],
  "validation_strategy":"pinned_source_hashes+V9_CRUF_launch+systemd_resource_scope+live_worker_phase+global_gross_byte_gate",
  "evidence_requirements":["mission/source/worker SHA-256","resource scope properties","CUSTOSZ queue chain","launch receipt","global candidate measured bytes"],
  "rollback_strategy":"all changes remain in isolated worker candidates; originals are read-only",
  "completion_condition":"worker launched and confirmed active in the first explicit global optimization phase",
  "authorization_evidence_reference":str(AUTH)}
 queue_path=STATE/"inteldoc_global_30mb_v2_queue.sqlite3"; q=PersistentMissionQueue(queue_path)
 sub=q.submit(task)
 if sub.get("state")!="RECEIVED": raise RuntimeError("QUEUE_SUBMIT_FAIL:"+str(sub))
 q.transition(task_id,"RECEIVED","PREFLIGHT",event_type="INTELDOC_GLOBAL_30MB_PREFLIGHT_STARTED",payload={"mission_sha256":EXPECTED_MISSION_SHA,"source_inventory":src})
 snapshot=probe_host_resources(OP)
 checks={"v9_sha":sha(V9)==EXPECTED_V9_SHA,"mission_sha":sha(MISSION)==EXPECTED_MISSION_SHA,"worker_sha":sha(WORKER)==EXPECTED_WORKER_SHA,"test_sha":sha(TEST)==EXPECTED_TEST_SHA,
  "source_hashes":True,"ram_headroom":ram_available()>=2*1024**3,"scope_authorization":verify_authorization(task).get("status")=="PASS","global_cap":spec["global_limit"]["hard_cap_bytes"]==30000000}
 if not all(checks.values()):
  q.transition(task_id,"PREFLIGHT","BLOCKED",event_type="INTELDOC_GLOBAL_30MB_PREFLIGHT_BLOCKED",payload={"checks":checks})
  raise RuntimeError("GLOBAL_PREFLIGHT_BLOCKED:"+json.dumps(checks))
 q.transition(task_id,"PREFLIGHT","READY",event_type="INTELDOC_GLOBAL_30MB_PREFLIGHT_PASS",payload={"checks":checks})
 claimed=q.claim_next_ready()
 if not isinstance(claimed,dict) or claimed.get("state")!="RUNNING": raise RuntimeError("QUEUE_CLAIM_FAIL:"+str(claimed))
 acts=[ActionSpec("verify_global_scope_and_pins",(),("LOCAL_FILE_READ","HASH_STREAMING"),("READ_PROJECT_ARTIFACTS",),"READ_ONLY"),
  ActionSpec("launch_global_inteldoc_worker",("verify_global_scope_and_pins",),("CHECKPOINTED_SCOPED_ACTIONS","HASH_CHAIN_EVIDENCE"),("WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"),"IDEMPOTENT")]
 def runner(payload):
  aid=payload["action"]["action_id"]
  if aid=="verify_global_scope_and_pins":
   now=source_inventory()
   return {"status":"PASS","source_inventory":now,"ram_available_bytes":ram_available(),"global_cap":30000000}
  if aid=="launch_global_inteldoc_worker":
   try: return launch(payload["task"],src,queue_path)
   except Exception as e: return {"status":"HOLD","reason":type(e).__name__+":"+str(e),"certification":"NOT_GRANTED"}
  return {"status":"DENIED","reason":"ACTION_NOT_REGISTERED"}
 coord=run_bounded_mission(task,acts,snapshot,available_capabilities=set(readj(BINDING).get("capabilities",[]))|{"LOCAL_FILE_READ","HASH_STREAMING"},
  admissible_effects={"READ_PROJECT_ARTIFACTS","WRITE_LOCAL_AUDIT","WRITE_CAJITA_WITH_CHECKPOINTS"},authorization_verifier=verify_authorization,
  action_runner=runner,maximum_steps=2,planning_budget=3)
 state="COMPLETED" if coord.get("status")=="COMPLETED" else "BLOCKED"
 q.transition(task_id,"RUNNING",state,event_type="INTELDOC_GLOBAL_30MB_LAUNCH_RECORDED" if state=="COMPLETED" else "INTELDOC_GLOBAL_30MB_LAUNCH_BLOCKED",
  payload={"coordinator_status":coord.get("status"),"worker_mission_status":"RUNNING_OR_HELD","canonical_promotion":"NOT_AUTHORIZED"})
 chain=q.verify_event_chain()
 report={"schema":"INTELDOC_GLOBAL_30MB_DISPATCH/1.0","timestamp_utc":utc(),"task_id":task_id,"mission_sha256":EXPECTED_MISSION_SHA,
  "worker_sha256":EXPECTED_WORKER_SHA,"test_sha256":EXPECTED_TEST_SHA,"dispatcher_sha256":sha(pathlib.Path(__file__)),"custoszv9_sha256":sha(V9),
  "preflight_checks":checks,"coordinator_result":coord,"queue_path":str(queue_path),"queue_final_state":state,"queue_event_chain":chain,
  "global_cap_bytes":30000000,"github":{"repository":REPO,"branch":BRANCH,"path_prefix":GH_PREFIX},
  "original_sources_modified":False,"functional_smoke":"DEFERRED_BY_USER","certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
 p=OUT/("INTELDOC_GLOBAL_30MB_V9_DISPATCH_"+dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+".json")
 atomic(p,report,exclusive=True)
 print(json.dumps({"status":state,"task_id":task_id,"coordinator_status":coord.get("status"),"queue_event_chain":chain.get("status"),
  "report_path":str(p),"report_sha256":sha(p),"launch_result":coord.get("actions"),"global_cap_bytes":30000000,"certification":"NOT_GRANTED"},indent=2),flush=True)
 return 0 if state=="COMPLETED" and chain.get("status")=="PASS" else 2
if __name__=="__main__": raise SystemExit(main())
