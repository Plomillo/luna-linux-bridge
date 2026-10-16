#!/usr/bin/env python3
"""Passive SYMPHYLAX R1 service payload candidate.

It exposes no network listener and no arbitrary command interface. It only
verifies pinned identities, runs CUSTOSZ/Runtime self-tests and emits a local
health heartbeat.
"""
import argparse,hashlib,json,os,signal,subprocess,sys,time
from datetime import datetime,timezone
from pathlib import Path
STOP=False
def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic_json(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+".tmp")
 t.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8");os.replace(t,p)
def validate(c):
 e=[]
 for k in ("authority","custosz","runtime","metaos"):
  x=c["artifacts"][k];p=Path(x["path"]).expanduser()
  if not p.is_file(): e.append(k.upper()+"_MISSING");continue
  if sha(p)!=x["sha256"]:e.append(k.upper()+"_SHA256_MISMATCH")
 return e
def boot_id():
 try:return Path("/proc/sys/kernel/random/boot_id").read_text(encoding="utf-8").strip()
 except Exception:return "UNKNOWN"
def boot_baseline(health):
 p=Path(health).parent/"BOOT_BASELINE.json";current=boot_id()
 if not p.exists():
  atomic_json(p,{"schema":"SYMPHYLAX_BOOT_BASELINE/1.0","first_boot_id":current,"first_observed_utc":utc()})
 try:base=json.loads(p.read_text(encoding="utf-8"))
 except Exception:base={"first_boot_id":"UNKNOWN","first_observed_utc":None}
 return p,base,current
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--config",required=True);ap.add_argument("--validate-only",action="store_true");q=ap.parse_args()
 c=json.loads(Path(q.config).read_text(encoding="utf-8"));h=Path(c["health_file"]).expanduser();baseline_path,baseline,current_boot=boot_baseline(h);errors=validate(c)
 if errors:atomic_json(h,{"schema":"SYMPHYLAX_R1_HEALTH/1.0","status":"FAIL","utc":utc(),"errors":errors});return 20
 if q.validate_only: print(json.dumps({"status":"PASS"}));return 0
 worker=Path(c["artifacts"]["custosz"]["path"]).expanduser()
 for cmd in ("v07-status","v07-selftest"):
  r=subprocess.run([sys.executable,"-B","-I",str(worker),cmd],capture_output=True,text=True,timeout=30)
  if r.returncode:atomic_json(h,{"schema":"SYMPHYLAX_R1_HEALTH/1.0","status":"FAIL","utc":utc(),"error":"CUSTOSZ_"+cmd});return 21
 runtime=Path(c["artifacts"]["runtime"]["path"]).expanduser();authority=Path(c["artifacts"]["authority"]["path"]).expanduser()
 sys.path.insert(0,str(runtime));from runtime_core import Runtime
 rt=Runtime(Path(c["runtime_state_dir"]).expanduser(),authority,sha(authority)).selftest()
 if rt.get("status")!="PASS":atomic_json(h,{"schema":"SYMPHYLAX_R1_HEALTH/1.0","status":"FAIL","utc":utc(),"error":"RUNTIME_SELFTEST"});return 22
 def stop(*_):
  global STOP;STOP=True
 signal.signal(signal.SIGTERM,stop);signal.signal(signal.SIGINT,stop);seq=0;started=utc()
 while not STOP:
  atomic_json(h,{"schema":"SYMPHYLAX_R1_HEALTH/1.1","status":"HEALTHY","service_id":"SYMPHYLAX_R1","authority":"Louksna.md","governor":"MetaOS","worker":"CUSTOSZ_V7","runtime":"CUSTOSZ_RUNTIME_V1","heartbeat_utc":utc(),"heartbeat_seq":seq,"progress_seq":1,"current_gate":"SERVICE_RUNNING","started_utc":started,"pid":os.getpid(),"boot_id":current_boot,"boot_baseline_file":str(baseline_path),"baseline_boot_id":baseline.get("first_boot_id"),"boot_changed_since_baseline":current_boot!="UNKNOWN" and baseline.get("first_boot_id") not in (None,"UNKNOWN",current_boot)});seq+=1;time.sleep(5)
 return 0
if __name__=="__main__":raise SystemExit(main())
