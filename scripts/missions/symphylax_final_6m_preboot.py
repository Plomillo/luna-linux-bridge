#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,subprocess,time,getpass
MISSION_SHA="e6e3a3bdbef7967d89cbc9e538469add01334e6e593ee2d1b93b72cbd32684dd"
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def run(c,timeout=20):
 try:
  p=subprocess.run(c,capture_output=True,text=True,timeout=timeout)
  return {"argv":c,"exit_code":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
 except Exception as e:return {"argv":c,"exit_code":999,"error":type(e).__name__+":"+str(e)}
def dump(p,o):
 p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def boot_id():
 return pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()
def main():
 a=argparse.ArgumentParser();a.add_argument("--mission",required=True);a.add_argument("--out",required=True);q=a.parse_args()
 out=pathlib.Path(q.out);out.mkdir(parents=True,exist_ok=True)
 if sha(q.mission)!=MISSION_SHA:raise SystemExit("MISSION_SHA_MISMATCH")
 start=time.time();home=pathlib.Path.home();state=home/".local/state/louksna/symphylax-r1";health=state/"health.json"
 cfg=home/".config/louksna/symphylax-r1/config.json";unit=home/".config/systemd/user/symphylax-r1.service";install=home/".local/lib/louksna/symphylax-r1"
 durable=home/".local/state/louksna/symphylax-final-6m";durable.mkdir(parents=True,exist_ok=True)
 changes=[];blockers=[]
 active=run(["systemctl","--user","is-active","symphylax-r1.service"]);enabled=run(["systemctl","--user","is-enabled","symphylax-r1.service"])
 linger=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"])
 sudo=run(["sudo","-n","true"])
 health_obj={}
 if health.is_file():
  try:health_obj=json.load(open(health,encoding="utf-8"))
  except Exception:pass
 surface={}
 for p in [cfg,unit]+([x for x in install.iterdir() if x.is_file()] if install.is_dir() else []):
  surface[str(p)]={"sha256":sha(p),"mode":oct(p.stat().st_mode & 0o777),"uid":p.stat().st_uid}
 checkpoint={"schema":"SYMPHYLAX_6M_PREBOOT_CHECKPOINT/1.0","mission_sha256":MISSION_SHA,"start_epoch":start,"preboot_boot_id":boot_id(),"health":health_obj,"active":active,"enabled":enabled,"linger":linger,"surface":surface}
 dump(durable/"CHECKPOINT.json",checkpoint);dump(out/"CHECKPOINT.json",checkpoint)
 # Minimal repair before reboot.
 if enabled["exit_code"]!=0 or active["exit_code"]!=0:
  z=run(["systemctl","--user","enable","--now","symphylax-r1.service"])
  changes.append({"action":"ENABLE_START_SYMPHYLAX","result":z})
 if linger.get("stdout","").lower()!="yes":
  if sudo["exit_code"]==0:
   z=run(["sudo","-n","loginctl","enable-linger",getpass.getuser()])
   changes.append({"action":"ENABLE_LINGER","result":z})
  else:blockers.append("LINGER_NOT_ENABLED_AND_NO_NONINTERACTIVE_PRIVILEGE")
 # Runner must have a persistent enabled service before reboot.
 ru=run(["systemctl","list-unit-files","--type=service","--no-legend","--no-pager","actions.runner.*"])
 runner_lines=[x for x in ru.get("stdout","").splitlines() if x.strip()]
 enabled_runner=[x for x in runner_lines if " enabled" in (" "+x+" ")]
 if not enabled_runner:
  ruu=run(["systemctl","--user","list-unit-files","--type=service","--no-legend","--no-pager","actions.runner.*"])
  runner_lines += [x for x in ruu.get("stdout","").splitlines() if x.strip()]
  enabled_runner += [x for x in ruu.get("stdout","").splitlines() if " enabled" in (" "+x+" ")]
 if not enabled_runner:blockers.append("SELF_HOSTED_RUNNER_AUTORETURN_NOT_PROVEN")
 active2=run(["systemctl","--user","is-active","symphylax-r1.service"]);enabled2=run(["systemctl","--user","is-enabled","symphylax-r1.service"])
 linger2=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"])
 h2={}
 if health.is_file():
  try:h2=json.load(open(health,encoding="utf-8"))
  except Exception:pass
 if active2["exit_code"]!=0:blockers.append("SYMPHYLAX_NOT_ACTIVE")
 if enabled2["exit_code"]!=0:blockers.append("SYMPHYLAX_NOT_ENABLED")
 if h2.get("status")!="HEALTHY":blockers.append("SYMPHYLAX_NOT_HEALTHY")
 if linger2.get("stdout","").lower()!="yes":blockers.append("LINGER_NOT_ENABLED")
 if sudo["exit_code"]!=0:blockers.append("NONINTERACTIVE_REBOOT_PRIVILEGE_UNAVAILABLE")
 result="PASS" if not blockers else "HOLD"
 obj={"schema":"SYMPHYLAX_6M_PREBOOT_RESULT/1.0","result":result,"mission_sha256":MISSION_SHA,"start_epoch":start,"preboot_boot_id":checkpoint["preboot_boot_id"],"changes":changes,"blockers":blockers,"runner_units":runner_lines,"runner_autoreturn_proven":bool(enabled_runner),"sudo_noninteractive":sudo["exit_code"]==0,"service_active":active2["exit_code"]==0,"service_enabled":enabled2["exit_code"]==0,"linger":linger2.get("stdout"),"health":h2}
 dump(durable/"PREBOOT_RESULT.json",obj);dump(out/"PREBOOT_RESULT.json",obj)
 print(json.dumps(obj,sort_keys=True))
 return 0 if result=="PASS" else 3
if __name__=="__main__":raise SystemExit(main())
