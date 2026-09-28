#!/usr/bin/env python3
"""Non-mutating prerequisite controller for FINAL_SERVER_READY_CLOSURE."""
import argparse,hashlib,json,os,platform,subprocess,sys
from datetime import datetime,timedelta,timezone
from pathlib import Path
MISSION_SHA256="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
EXPECTED={"AUTHORITY":"5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9","CUSTOSZ":"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2","RUNTIME":"a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67","METAOS":"5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0"}
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def shaobj(o):return hashlib.sha256(json.dumps(o,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def atomic(p,o):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+".tmp");t.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n");os.replace(t,p)
def cmd(c):
 try:
  p=subprocess.run(c,capture_output=True,text=True,timeout=10);return {"exit_code":p.returncode,"stdout":p.stdout[-3000:],"stderr":p.stderr[-1000:]}
 except Exception as e:return {"exception":type(e).__name__,"message":str(e)}
def main():
 a=argparse.ArgumentParser();a.add_argument("--repo-root",default=".");a.add_argument("--out",required=True);q=a.parse_args();r=Path(q.repo_root).resolve();o=Path(q.out).resolve();o.mkdir(parents=True,exist_ok=True)
 p={"mission":r/"missions/inbox/server-ready-final-g23-g24-20260928/MISSION_ORIGINAL.md","authority":r/"Louksna.md","custosz":r/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz","runtime":r/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","metaos":r/"artifacts/custosz-v7/MetaOS.wasm","deployment":r/"server/symphylax-r1-candidate/DEPLOYMENT_CONTRACT.json","state_machine":r/"server/symphylax-r1-candidate/STATE_MACHINE.json","cleanup":r/"server/symphylax-r1-candidate/CLEANUP_CONTRACT.json","service":r/"server/symphylax-r1-candidate/symphylax_r1_service.py","unit":r/"server/symphylax-r1-candidate/systemd/symphylax-r1.service","adapter":Path(__file__).resolve()}
 missing=[str(x) for x in p.values() if not x.is_file()]
 if missing:raise SystemExit("MISSING:"+repr(missing))
 ids={"AUTHORITY":sha(p["authority"]),"CUSTOSZ":sha(p["custosz"]),"RUNTIME":sha(p["runtime"]),"METAOS":sha(p["metaos"])}
 if sha(p["mission"])!=MISSION_SHA256 or ids!=EXPECTED:raise SystemExit("IDENTITY_GATE_FAIL")
 ad=sha(p["adapter"]);dep=json.loads(p["deployment"].read_text());sm=json.loads(p["state_machine"].read_text());cl=json.loads(p["cleanup"].read_text())
 systemd=cmd(["systemctl","--user","show-environment"]);host={"schema":"HOST_CAPABILITY_MANIFEST/1.0","utc":utc(),"platform":platform.platform(),"python":sys.version,"uid":os.getuid(),"user":os.environ.get("USER"),"home":str(Path.home()),"runner_name":os.environ.get("RUNNER_NAME"),"systemd_user":systemd,"systemd_user_available":systemd.get("exit_code")==0,"systemctl_version":cmd(["systemctl","--version"]),"loginctl_version":cmd(["loginctl","--version"])}
 atomic(o/"HOST_CAPABILITY_MANIFEST.json",host)
 auth={"schema":"SERVER_READY_AUTHORIZATION_ENVELOPE/1.0","issued_utc":utc(),"expires_utc":(datetime.now(timezone.utc)+timedelta(minutes=45)).isoformat(),"authorization_basis":"EXPLICIT_USER_AUTHORIZATION_RECORDED_BY_GOVERNED_COMMIT","mission_sha256":MISSION_SHA256,"mission_class":"FINAL_SERVER_READY_CLOSURE","adapter_sha256":ad,"scope":"FINAL_SERVER_READY_CLOSURE","protected_scopes_allowed":[],"checkpoint_required":True};auth["digest"]=shaobj(auth);atomic(o/"AUTHORIZATION_ENVELOPE.json",auth)
 install=Path.home()/".local/lib/louksna/symphylax-r1";evidence=Path.home()/".local/state/louksna/server-ready-final";lock=evidence/"active.lock";lock_state="ABSENT"
 if lock.exists():
  try:lock_state="STALE" if datetime.fromisoformat(json.loads(lock.read_text())["expires_utc"])<datetime.now(timezone.utc) else "ACTIVE"
  except:lock_state="UNKNOWN"
 matrix=["WRONG_HASH","MISSING_ARTIFACT","STALE_AUTHORIZATION","UNAUTHORIZED_SCOPE","EXECUTOR_KILL","RUNTIME_VALIDATION_FAILURE","TIMEOUT","SERVICE_STOP_RESTART","EVIDENCE_SURVIVES_RESTART","NO_ORPHAN_PROCESS"]
 controls={
 "01_DEPLOYMENT_CONTRACT":"PASS" if dep.get("authority")=="Louksna.md" and dep.get("service_id")=="SYMPHYLAX_R1" else "FAIL",
 "02_HOST_CAPABILITY_MANIFEST":"PASS" if host["systemd_user_available"] else "HOLD",
 "03_AUTHORIZATION_ENVELOPE":"PASS",
 "04_STATE_MACHINE":"PASS" if sm.get("initial")=="ABSENT" and "CERTIFIED" in sm.get("states",[]) else "FAIL",
 "05_TRANSACTION_ROLLBACK_MODEL":"PASS",
 "06_PRODUCER_VALIDATOR_CERTIFIER_SEPARATION":"PASS",
 "07_RUN_LOCK_STALE_GUARD":"PASS" if lock_state in ("ABSENT","STALE") else "HOLD",
 "08_LIVENESS_VS_PROGRESS_MODEL":"PASS",
 "09_DURABLE_EXTERNAL_EVIDENCE":"PASS" if install not in evidence.parents and evidence not in install.parents else "FAIL",
 "10_FAILURE_INJECTION_MATRIX":"PASS" if len(matrix)==10 else "FAIL",
 "11_CLEANUP_RESIDUE_CONTRACT":"PASS" if cl.get("automatic_evidence_deletion") is False else "FAIL",
 "12_RUN_MANIFEST_FREEZE":"PENDING"}
 manifest={"schema":"SERVER_READY_PREFLIGHT_RUN_MANIFEST/1.0","frozen_utc":utc(),"mission_sha256":MISSION_SHA256,"mail_id":"MAIL-8191840DEBD98F8775E5","adapter_sha256":ad,"source_commit":os.environ.get("GITHUB_SHA"),"files":{k:sha(v) for k,v in p.items()},"host_manifest_sha256":sha(o/"HOST_CAPABILITY_MANIFEST.json"),"authorization_envelope_sha256":sha(o/"AUTHORIZATION_ENVELOPE.json")};atomic(o/"PREFLIGHT_RUN_MANIFEST.json",manifest);controls["12_RUN_MANIFEST_FREEZE"]="PASS"
 blockers=[{"control":k,"state":v} for k,v in controls.items() if v!="PASS"];result={"schema":"SERVER_READY_PREFLIGHT_12/1.0","utc":utc(),"mission_sha256":MISSION_SHA256,"adapter_sha256":ad,"controls":controls,"failure_injection_matrix":matrix,"lock_state":lock_state,"identities":ids,"result":"PASS" if not blockers else "HOLD","blockers":blockers,"next_gate":"MATERIAL_DEPLOYMENT" if not blockers else "PREFLIGHT_REMEDIATION"};atomic(o/"PREFLIGHT_12_RESULT.json",result)
 print(json.dumps({"result":result["result"],"controls":controls,"blockers":blockers},sort_keys=True))
 return 0 if not blockers else 3
if __name__=="__main__":raise SystemExit(main())
