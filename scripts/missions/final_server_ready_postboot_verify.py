#!/usr/bin/env python3
"""Read-only post-boot verifier for SYMPHYLAX R1.

Safe when invoked by the GitHub Actions runner installed as a system service:
systemctl --user is explicitly bound to the target user's systemd bus.
"""
import argparse,json,os,subprocess
from datetime import datetime,timezone
from pathlib import Path

SERVICE="symphylax-r1.service"
def utc(): return datetime.now(timezone.utc).isoformat()
def user_env():
 env=os.environ.copy();uid=os.getuid();runtime=f"/run/user/{uid}"
 env["XDG_RUNTIME_DIR"]=runtime
 env["DBUS_SESSION_BUS_ADDRESS"]=f"unix:path={runtime}/bus"
 return env
def run(cmd,user=False):
 try:
  p=subprocess.run(cmd,capture_output=True,text=True,timeout=15,env=user_env() if user else None)
  return {"argv":cmd,"exit_code":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
 except Exception as e:
  return {"argv":cmd,"exit_code":999,"error":type(e).__name__+":"+str(e)}
def manual_preboot(path):
 if not path.is_file(): return None
 for line in path.read_text(encoding="utf-8",errors="replace").splitlines():
  if line.startswith("PREBOOT_BOOT_ID="): return line.split("=",1)[1].strip()
 return None
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);q=ap.parse_args()
 home=Path.home();state=home/".local/state/louksna/symphylax-r1"
 health=state/"health.json";baseline=state/"BOOT_BASELINE.json"
 checkpoint=home/".local/state/louksna/manual-g08-reboot/PREBOOT_CHECKPOINT.txt"
 out=Path(q.out);out.parent.mkdir(parents=True,exist_ok=True)
 evidence={"schema":"BOOT_PERSISTENCE_EVIDENCE/1.1","utc":utc(),"health_file":str(health),"baseline_file":str(baseline),"manual_checkpoint_file":str(checkpoint),"user_uid":os.getuid(),"user_systemd_runtime_dir":f"/run/user/{os.getuid()}"}
 if not health.is_file() or not baseline.is_file():
  evidence.update({"result":"HOLD","root_blocker":"BOOT_EVIDENCE_FILES_MISSING"})
 else:
  try:
   h=json.loads(health.read_text(encoding="utf-8"));b=json.loads(baseline.read_text(encoding="utf-8"))
  except Exception as e:
   evidence.update({"result":"HOLD","root_blocker":"BOOT_EVIDENCE_JSON_UNREADABLE","error":type(e).__name__+":"+str(e)})
  else:
   current=Path("/proc/sys/kernel/random/boot_id").read_text().strip()
   baseline_id=h.get("baseline_boot_id") or b.get("boot_id") or b.get("baseline_boot_id")
   manual_id=manual_preboot(checkpoint)
   active=run(["systemctl","--user","is-active",SERVICE],user=True)
   enabled=run(["systemctl","--user","is-enabled",SERVICE],user=True)
   linger=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"])
   bus=Path(f"/run/user/{os.getuid()}/bus").exists()
   changed=bool(baseline_id and current!=baseline_id and h.get("boot_changed_since_baseline") is True and h.get("boot_id")==current)
   manual_ok=(manual_id is None or manual_id!=current)
   healthy=h.get("status")=="HEALTHY"
   active_ok=active["exit_code"]==0;enabled_ok=enabled["exit_code"]==0
   linger_ok=linger.get("stdout","").strip().lower()=="yes"
   evidence.update({"health":h,"baseline":b,"current_boot_id":current,"baseline_boot_id":baseline_id,"manual_preboot_boot_id":manual_id,"boot_id_changed":changed,"manual_checkpoint_consistent":manual_ok,"service_active":active,"service_enabled":enabled,"linger":linger,"user_systemd_bus_available":bus,"service_healthy":healthy})
   passed=all((bus,changed,manual_ok,healthy,active_ok,enabled_ok,linger_ok))
   if passed: blocker=None
   elif not bus or active["exit_code"]==999 or enabled["exit_code"]==999: blocker="USER_SYSTEMD_CONTEXT_UNAVAILABLE"
   elif not changed: blocker="POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED"
   elif not healthy: blocker="SYMPHYLAX_POSTBOOT_NOT_HEALTHY"
   elif not active_ok: blocker="SYMPHYLAX_POSTBOOT_NOT_ACTIVE"
   elif not enabled_ok: blocker="SYMPHYLAX_POSTBOOT_NOT_ENABLED"
   elif not linger_ok: blocker="LINGER_NOT_ENABLED"
   else: blocker="POST_BOOT_EVIDENCE_INCONSISTENT"
   evidence["result"]="PASS" if passed else "HOLD";evidence["root_blocker"]=blocker
 out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"result":evidence["result"],"root_blocker":evidence.get("root_blocker")},sort_keys=True))
 return 0 if evidence["result"]=="PASS" else 3
if __name__=="__main__": raise SystemExit(main())
