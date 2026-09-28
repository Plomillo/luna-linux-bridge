#!/usr/bin/env python3
"""Read-only post-boot verifier for SYMPHYLAX R1."""
import argparse,json,subprocess
from datetime import datetime,timezone
from pathlib import Path

def utc(): return datetime.now(timezone.utc).isoformat()
def run(cmd):
 p=subprocess.run(cmd,capture_output=True,text=True,timeout=15)
 return {"exit_code":p.returncode,"stdout":p.stdout.strip(),"stderr":p.stderr.strip()}
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--out",required=True);q=ap.parse_args()
 home=Path.home();health=home/".local/state/louksna/symphylax-r1/health.json";baseline=home/".local/state/louksna/symphylax-r1/BOOT_BASELINE.json"
 out=Path(q.out);out.parent.mkdir(parents=True,exist_ok=True)
 evidence={"schema":"BOOT_PERSISTENCE_EVIDENCE/1.0","utc":utc(),"health_file":str(health),"baseline_file":str(baseline)}
 if not health.is_file() or not baseline.is_file():
  evidence.update({"result":"HOLD","root_blocker":"BOOT_EVIDENCE_FILES_MISSING"})
 else:
  h=json.loads(health.read_text(encoding="utf-8"));b=json.loads(baseline.read_text(encoding="utf-8"))
  active=run(["systemctl","--user","is-active","symphylax-r1.service"])
  enabled=run(["systemctl","--user","is-enabled","symphylax-r1.service"])
  linger=run(["loginctl","show-user",str(__import__("os").getuid()),"-p","Linger","--value"])
  changed=bool(h.get("boot_changed_since_baseline"))
  healthy=h.get("status")=="HEALTHY"
  evidence.update({"health":h,"baseline":b,"service_active":active,"service_enabled":enabled,"linger":linger,
                   "boot_id_changed":changed,"service_healthy":healthy})
  passed=changed and healthy and active["exit_code"]==0 and enabled["exit_code"]==0 and linger["stdout"].strip().lower()=="yes"
  evidence["result"]="PASS" if passed else "HOLD"
  evidence["root_blocker"]=None if passed else "POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED"
 out.write_text(json.dumps(evidence,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps({"result":evidence["result"],"root_blocker":evidence.get("root_blocker")},sort_keys=True))
 return 0 if evidence["result"]=="PASS" else 3
if __name__=="__main__":raise SystemExit(main())
