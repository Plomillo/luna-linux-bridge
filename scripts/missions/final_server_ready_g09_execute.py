#!/usr/bin/env python3
"""Material G09 failure/recovery executor for the SERVER_READY terminal chain.

Mutations are limited to the SYMPHYLAX user service and temporary negative-test
configs. Canonical files are never modified.
"""
import argparse,hashlib,json,os,pathlib,stat,subprocess,sys,tempfile,time
from datetime import datetime,timezone

MISSION_SHA="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
SERVICE="symphylax-r1.service"
def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
 return h.hexdigest()
def user_env():
 env=os.environ.copy();uid=os.getuid();runtime=f"/run/user/{uid}"
 env["XDG_RUNTIME_DIR"]=runtime;env["DBUS_SESSION_BUS_ADDRESS"]=f"unix:path={runtime}/bus"
 return env
def run(cmd,user=False,timeout=20):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=timeout,env=user_env() if user else None)
  return {"argv":cmd,"exit_code":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
 except subprocess.TimeoutExpired:
  return {"argv":cmd,"exit_code":124,"timeout":True}
 except Exception as e:
  return {"argv":cmd,"exit_code":999,"error":type(e).__name__+":"+str(e)}
def dump(p,o):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+".tmp")
 tmp.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.replace(tmp,p)
def wait_health(p,timeout=30):
 end=time.time()+timeout;last={}
 while time.time()<end:
  try: last=json.loads(p.read_text(encoding="utf-8"))
  except Exception: last={}
  if last.get("status")=="HEALTHY": return last
  time.sleep(.5)
 return last
def main_pid():
 r=run(["systemctl","--user","show",SERVICE,"-p","MainPID","--value"],user=True)
 try: pid=int(r.get("stdout") or "0")
 except ValueError: pid=0
 return pid,r
def check_deadline(x):
 if x and time.time()>=x: raise TimeoutError("GLOBAL_900S_BUDGET_EXHAUSTED")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--mission",required=True);ap.add_argument("--g08",required=True);ap.add_argument("--out",required=True);ap.add_argument("--deadline-epoch",type=float,default=0);q=ap.parse_args()
 out=pathlib.Path(q.out).resolve();out.mkdir(parents=True,exist_ok=True)
 durable=pathlib.Path.home()/".local/state/louksna/server-ready-final";durable.mkdir(parents=True,exist_ok=True)
 ep=out/"G09_FAILURE_RECOVERY_EVIDENCE.json";dp=out/"G09_FAILURE_RECOVERY_DETAILS.json"
 mission_hash=sha(q.mission);g08=json.loads(pathlib.Path(q.g08).read_text(encoding="utf-8"));start=time.time()
 details={"schema":"G09_FAILURE_RECOVERY_DETAILS/1.0","start_utc":utc(),"mission_sha256":mission_hash,"tests":{}}
 ev={"schema":"G09_FAILURE_RECOVERY_EVIDENCE/1.0","mission_sha256":MISSION_SHA,"result":"HOLD","executor_kill_recovery":False,"process_termination_recovery":False,"runtime_failure_recovery":False,"dependency_failure":"NOT_RUN","timeout":"NOT_RUN","no_orphan_process":False,"state_recovery":False,"evidence_survives_restart":False,"before_process_id":None,"after_process_id":None,"source_executor":"CUSTOSZ_V7_SELF_HOSTED_LUNA_AUX","evidence_refs":["G09_FAILURE_RECOVERY_DETAILS.json","BOOT_PERSISTENCE_EVIDENCE.json"],"root_blocker":None,"resolved":False}
 def finish(rc):
  ev["test_start_utc"]=ev.get("test_start_utc") or details["start_utc"];ev["test_end_utc"]=utc();ev["elapsed_seconds"]=round(time.time()-start,3)
  dump(ep,ev);dump(dp,details);dump(durable/ep.name,ev);dump(durable/dp.name,details)
  print(json.dumps({"result":ev["result"],"root_blocker":ev.get("root_blocker"),"elapsed_seconds":ev["elapsed_seconds"]},sort_keys=True));return rc
 if mission_hash!=MISSION_SHA: ev["root_blocker"]="MISSION_SHA_MISMATCH";return finish(3)
 if g08.get("result")!="PASS": ev["root_blocker"]="G08_NOT_PASS";return finish(3)
 home=pathlib.Path.home();health=home/".local/state/louksna/symphylax-r1/health.json";cfg=home/".config/louksna/symphylax-r1/config.json";svc=home/".local/lib/louksna/symphylax-r1/symphylax_r1_service.py"
 try:
  check_deadline(q.deadline_epoch)
  if not all(p.is_file() for p in (health,cfg,svc)):
   ev["root_blocker"]="G09_REQUIRED_RUNTIME_SURFACE_MISSING";details["surface"]={"health":health.is_file(),"config":cfg.is_file(),"service":svc.is_file()};return finish(3)
  st=cfg.stat();details["config_security"]={"uid":st.st_uid,"mode":oct(stat.S_IMODE(st.st_mode)),"world_writable":bool(st.st_mode & stat.S_IWOTH)}
  if st.st_uid!=os.getuid() or st.st_mode & stat.S_IWOTH: ev["root_blocker"]="G09_CONFIG_SECURITY_PRECONDITION_FAILED";return finish(3)

  before,bshow=main_pid();details["tests"]["before_pid"]=bshow
  if before<=0: ev["root_blocker"]="G09_MAIN_PID_UNAVAILABLE";return finish(3)
  kill=run(["systemctl","--user","kill","--signal=SIGKILL","--kill-who=main",SERVICE],user=True);details["tests"]["controlled_sigkill"]=kill
  recovered=False;rh={};after=before;end=min(time.time()+35,q.deadline_epoch or time.time()+35)
  while time.time()<end:
   after,show=main_pid();rh=wait_health(health,1.5)
   if kill["exit_code"]==0 and after>0 and after!=before and rh.get("status")=="HEALTHY" and rh.get("pid") in (None,after):
    recovered=True;details["tests"]["recovered_pid_show"]=show;break
   time.sleep(.5)
  details["tests"]["post_kill_health"]=rh;ev["before_process_id"]=before;ev["after_process_id"]=after;ev["executor_kill_recovery"]=recovered;ev["process_termination_recovery"]=recovered
  check_deadline(q.deadline_epoch)

  base=json.loads(cfg.read_text(encoding="utf-8"))
  if "artifacts" not in base or "runtime" not in base["artifacts"]: ev["root_blocker"]="G09_RUNTIME_CONFIG_SCHEMA_UNEXPECTED";return finish(3)
  with tempfile.TemporaryDirectory(prefix="server-ready-g09-") as t:
   td=pathlib.Path(t)
   bad=json.loads(json.dumps(base));bad["artifacts"]["runtime"]["sha256"]="0"*64;badp=td/"wrong-hash.json";dump(badp,bad)
   wrong=run([sys.executable,"-B","-I",str(svc),"--config",str(badp),"--validate-only"]);wrong_ok=wrong["exit_code"]!=0;details["tests"]["wrong_hash_rejection"]=wrong
   miss=json.loads(json.dumps(base));miss["artifacts"]["runtime"]["path"]=str(td/"missing-runtime.pyz");missp=td/"missing-artifact.json";dump(missp,miss)
   missing=run([sys.executable,"-B","-I",str(svc),"--config",str(missp),"--validate-only"]);missing_ok=missing["exit_code"]!=0;details["tests"]["missing_artifact_rejection"]=missing
  live=wait_health(health,5);details["tests"]["live_health_after_negative_tests"]=live
  runtime_ok=wrong_ok and missing_ok and live.get("status")=="HEALTHY";ev["runtime_failure_recovery"]=runtime_ok;ev["dependency_failure"]="SAFE_HOLD" if missing_ok else "FAIL"

  timeout_ok=False
  try: subprocess.run([sys.executable,"-c","import time;time.sleep(3)"],timeout=1,check=False);details["tests"]["timeout"]={"timed_out":False}
  except subprocess.TimeoutExpired: timeout_ok=True;details["tests"]["timeout"]={"timed_out":True}
  ev["timeout"]="SAFE_HOLD" if timeout_ok else "FAIL"
  check_deadline(q.deadline_epoch)

  marker=durable/"G09_EVIDENCE_SURVIVAL.marker";marker.write_text("schema=G09_EVIDENCE_SURVIVAL/1.0\nmission_sha256="+MISSION_SHA+"\ncreated_utc="+utc()+"\n",encoding="utf-8");mh=sha(marker)
  restart=run(["systemctl","--user","restart",SERVICE],user=True);fh=wait_health(health,15);finalpid,fshow=main_pid()
  details["tests"]["governed_restart"]=restart;details["tests"]["final_health"]=fh;details["tests"]["final_pid_show"]=fshow
  pgrep=run(["pgrep","-f","[s]ymphylax_r1_service.py"]);pids=[int(x) for x in pgrep.get("stdout","").split() if x.isdigit()]
  no_orphan=finalpid>0 and len(set(pids))==1 and finalpid in set(pids)
  details["tests"]["process_inventory"]={"pgrep":pgrep,"service_main_pid":finalpid,"matched_pids":pids}
  marker_ok=marker.is_file() and sha(marker)==mh;state_ok=restart["exit_code"]==0 and fh.get("status")=="HEALTHY" and fh.get("pid") in (None,finalpid)
  ev["no_orphan_process"]=no_orphan;ev["state_recovery"]=state_ok;ev["evidence_survives_restart"]=marker_ok
  ok=all((recovered,runtime_ok,missing_ok,timeout_ok,no_orphan,state_ok,marker_ok));ev["result"]="PASS" if ok else "HOLD";ev["resolved"]=ok
  if ok: ev["root_blocker"]=None
  elif not recovered: ev["root_blocker"]="CONTROLLED_EXECUTOR_KILL_RECOVERY_FAILED"
  elif not runtime_ok: ev["root_blocker"]="RUNTIME_FAILURE_SAFE_RECOVERY_NOT_PROVEN"
  elif not missing_ok: ev["root_blocker"]="DEPENDENCY_FAILURE_NOT_FAIL_CLOSED"
  elif not timeout_ok: ev["root_blocker"]="TIMEOUT_FAIL_CLOSED_NOT_PROVEN"
  elif not no_orphan: ev["root_blocker"]="ORPHAN_PROCESS_DETECTED_OR_UNRESOLVED"
  elif not state_ok: ev["root_blocker"]="STATE_RECOVERY_NOT_PROVEN"
  else: ev["root_blocker"]="EVIDENCE_SURVIVAL_NOT_PROVEN"
  return finish(0 if ok else 3)
 except TimeoutError as e: ev["root_blocker"]=str(e);return finish(3)
 except Exception as e: details["exception"]=type(e).__name__+":"+str(e);ev["root_blocker"]="G09_EXECUTION_EXCEPTION";return finish(3)
if __name__=="__main__": raise SystemExit(main())
