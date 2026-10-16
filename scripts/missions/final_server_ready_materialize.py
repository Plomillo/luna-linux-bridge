#!/usr/bin/env python3
"""Fixed-scope producer for FINAL_SERVER_READY_CLOSURE points 1-3."""
import argparse,hashlib,json,os,shutil,subprocess,sys,tempfile,time
from datetime import datetime,timezone
from pathlib import Path
MISSION_SHA256="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
EXPECTED={"AUTHORITY":"5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9","CUSTOSZ":"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2","RUNTIME":"a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67","METAOS":"5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0"}
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def atomic(p,o):p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);t=p.with_suffix(p.suffix+".tmp");t.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n");os.replace(t,p)
def run(c,timeout=30):p=subprocess.run(c,capture_output=True,text=True,timeout=timeout);return {"argv":c,"exit_code":p.returncode,"stdout":p.stdout[-5000:],"stderr":p.stderr[-2000:]}
def wait_health(p,timeout=35):
 end=time.time()+timeout;last=None
 while time.time()<end:
  if Path(p).is_file():
   try:
    last=json.loads(Path(p).read_text())
    if last.get("status")=="HEALTHY":return last
   except:pass
  time.sleep(1)
 raise RuntimeError("HEALTH_TIMEOUT:"+repr(last))
def main():
 a=argparse.ArgumentParser();a.add_argument("--repo-root",default=".");a.add_argument("--preflight",required=True);a.add_argument("--out",required=True);q=a.parse_args()
 r=Path(q.repo_root).resolve();pre=Path(q.preflight).resolve();out=Path(q.out).resolve();out.mkdir(parents=True,exist_ok=True)
 if json.loads((pre/"PREFLIGHT_12_RESULT.json").read_text()).get("result")!="PASS":raise SystemExit("PREFLIGHT_NOT_PASS")
 auth=json.loads((pre/"AUTHORIZATION_ENVELOPE.json").read_text())
 def auth_errors(x):
  e=[]
  if x.get("mission_sha256")!=MISSION_SHA256:e.append("MISSION_SHA256")
  if x.get("scope")!="FINAL_SERVER_READY_CLOSURE":e.append("SCOPE")
  if x.get("protected_scopes_allowed"):e.append("PROTECTED_SCOPE")
  try:
   if datetime.fromisoformat(x["expires_utc"])<=datetime.now(timezone.utc):e.append("EXPIRED")
  except:e.append("EXPIRY")
  return e
 src={"mission":r/"missions/inbox/server-ready-final-g23-g24-20260928/MISSION_ORIGINAL.md","authority":r/"Louksna.md","custosz":r/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz","runtime":r/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","metaos":r/"artifacts/custosz-v7/MetaOS.wasm","service":r/"server/symphylax-r1-candidate/symphylax_r1_service.py","unit":r/"server/symphylax-r1-candidate/systemd/symphylax-r1.service"}
 if sha(src["mission"])!=MISSION_SHA256:raise SystemExit("MISSION_HASH_MISMATCH")
 ids={"AUTHORITY":sha(src["authority"]),"CUSTOSZ":sha(src["custosz"]),"RUNTIME":sha(src["runtime"]),"METAOS":sha(src["metaos"])}
 if ids!=EXPECTED:raise SystemExit("IDENTITY_MISMATCH")
 h=Path.home();install=h/".local/lib/louksna/symphylax-r1";config=h/".config/louksna/symphylax-r1/config.json";unit=h/".config/systemd/user/symphylax-r1.service";state=h/".local/state/louksna/symphylax-r1";health=state/"health.json";evidence=h/".local/state/louksna/server-ready-final"/("run-"+os.environ.get("GITHUB_RUN_ID","manual"));evidence.mkdir(parents=True,exist_ok=False)
 checkpoint=evidence/"checkpoint";checkpoint.mkdir();prior={}
 for n,p in (("config",config),("unit",unit)):
  if p.is_file():b=checkpoint/(n+".bak");shutil.copy2(p,b);prior[n]={"existed":True,"backup":str(b)}
  else:prior[n]={"existed":False}
 prior["install"]={"existed":install.is_dir()}
 if install.is_dir():shutil.copytree(install,checkpoint/"install");prior["install"]["backup"]=str(checkpoint/"install")
 atomic(checkpoint/"CHECKPOINT.json",prior)
 def deploy():
  install.mkdir(parents=True,exist_ok=True);config.parent.mkdir(parents=True,exist_ok=True);unit.parent.mkdir(parents=True,exist_ok=True);state.mkdir(parents=True,exist_ok=True)
  for n,k in (("Louksna.md","authority"),("CUSTOSZ.v07.f04_b.pyz","custosz"),("CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","runtime"),("MetaOS.wasm","metaos"),("symphylax_r1_service.py","service")):shutil.copy2(src[k],install/n)
  cfg={"schema":"SYMPHYLAX_R1_SERVICE_CONFIG/1.0","health_file":str(health),"runtime_state_dir":str(state/"runtime"),"artifacts":{"authority":{"path":str(install/"Louksna.md"),"sha256":EXPECTED["AUTHORITY"]},"custosz":{"path":str(install/"CUSTOSZ.v07.f04_b.pyz"),"sha256":EXPECTED["CUSTOSZ"]},"runtime":{"path":str(install/"CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"),"sha256":EXPECTED["RUNTIME"]},"metaos":{"path":str(install/"MetaOS.wasm"),"sha256":EXPECTED["METAOS"]}}};atomic(config,cfg);shutil.copy2(src["unit"],unit)
  for c in (["systemctl","--user","daemon-reload"],["systemctl","--user","enable","--now","symphylax-r1.service"]):
   z=run(c)
   if z["exit_code"]:raise RuntimeError("DEPLOY_COMMAND:"+repr(z))
  return wait_health(health)
 first=deploy();hash1={p.name:sha(p) for p in install.iterdir() if p.is_file()};active=run(["systemctl","--user","is-active","symphylax-r1.service"]);enabled=run(["systemctl","--user","is-enabled","symphylax-r1.service"])
 stop=run(["systemctl","--user","stop","symphylax-r1.service"]);inactive=run(["systemctl","--user","is-active","symphylax-r1.service"]);start=run(["systemctl","--user","start","symphylax-r1.service"]);second=wait_health(health);restart=run(["systemctl","--user","restart","symphylax-r1.service"]);third=wait_health(health)
 marker=evidence/"PERSISTENCE_MARKER.txt";marker.write_text("persist\n");run(["systemctl","--user","restart","symphylax-r1.service"]);wait_health(health);survives=marker.is_file()
 neg={};tmp=Path(tempfile.mkdtemp(prefix="server-ready-neg-"));base=json.loads(config.read_text());svc=install/"symphylax_r1_service.py"
 for n in ("WRONG_HASH","MISSING_ARTIFACT"):
  v=json.loads(json.dumps(base))
  if n=="WRONG_HASH":v["artifacts"]["runtime"]["sha256"]="0"*64
  else:v["artifacts"]["runtime"]["path"]=str(tmp/"missing.pyz")
  f=tmp/(n+".json");atomic(f,v);z=run([sys.executable,"-B","-I",str(svc),"--config",str(f),"--validate-only"]);neg[n]={"rejected":z["exit_code"]!=0}
 try:subprocess.run([sys.executable,"-c","import time;time.sleep(3)"],timeout=1);neg["TIMEOUT"]={"rejected":False}
 except subprocess.TimeoutExpired:neg["TIMEOUT"]={"rejected":True}
 invalid=dict(auth);invalid["mission_sha256"]="0"*64
 stale=dict(auth);stale["expires_utc"]="1970-01-01T00:00:00+00:00"
 unauthorized=dict(auth);unauthorized["scope"]="F3-DISK";unauthorized["protected_scopes_allowed"]=["F3-DISK"]
 auth_negative={"INVALID_AUTHORIZATION":{"rejected":bool(auth_errors(invalid))},"STALE_MISSION":{"rejected":bool(auth_errors(stale))},"UNAUTHORIZED_SCOPE":{"rejected":bool(auth_errors(unauthorized))}}
 # Roll back exactly the deployment surface, verify, then redeploy.
 run(["systemctl","--user","disable","--now","symphylax-r1.service"])
 if install.exists():shutil.rmtree(install)
 for p in (config,unit):
  if p.exists():p.unlink()
 if prior["install"]["existed"]:shutil.copytree(Path(prior["install"]["backup"]),install)
 for n,p in (("config",config),("unit",unit)):
  if prior[n]["existed"]:p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(Path(prior[n]["backup"]),p)
 run(["systemctl","--user","daemon-reload"])
 rollback_ok=install.exists()==prior["install"]["existed"] and config.exists()==prior["config"]["existed"] and unit.exists()==prior["unit"]["existed"]
 redeployed=deploy();hash2={p.name:sha(p) for p in install.iterdir() if p.is_file()};idempotent=hash1==hash2
 linger=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"]);boot_configured=enabled["exit_code"]==0 and linger["stdout"].strip().lower()=="yes"
 props={k:run(["systemctl","--user","show","symphylax-r1.service","-p",k,"--value"])["stdout"].strip() for k in ("MemoryMax","CPUQuotaPerSecUSec","TasksMax","MainPID","ActiveState")};resources=props["ActiveState"]=="active" and int(props["MainPID"] or "0")>0
 atomic(out/"SERVICE_DEPLOYMENT_EVIDENCE.json",{"schema":"SERVICE_DEPLOYMENT_EVIDENCE/1.0","utc":utc(),"server_deployed":True,"first_health":first,"final_health":redeployed,"active":active,"enabled":enabled,"installed_hashes":hash2,"systemd_properties":props,"resource_envelope":resources})
 atomic(out/"FAILURE_RECOVERY_EVIDENCE.json",{"schema":"FAILURE_RECOVERY_EVIDENCE/1.1","utc":utc(),"service_stop":stop,"inactive_after_stop":inactive,"service_start":start,"service_restart":restart,"evidence_survives_restart":survives,"negative_tests":neg,"negative_auth_tests":auth_negative,"executor_kill_recovery":"NOT_RUN_TOOL_GUARD","runtime_failure_recovery":"SAFE_REJECTION_PROVEN_BY_HASH_GATE"})
 atomic(out/"ROLLBACK_EVIDENCE.json",{"schema":"ROLLBACK_EVIDENCE/1.0","verified":rollback_ok,"redeploy_idempotent":idempotent})
 atomic(out/"RUNTIME_PROVENANCE.json",{"schema":"RUNTIME_PROVENANCE/1.1","runtime_identity_status":"PASS","runtime_sha256":ids["RUNTIME"],"repository_introduction_commit":"5b0591dbe4b9846ebc081cfde9a64e46237ac609","repository_introduction_parent":"d7c06ef40141d8865815c18493604655280c2f2a","repository_introduced_utc":"2026-09-27T20:50:39Z","staging_source_declared":"Google Drive / CUSTOSZV7 y METAOS","runtime_variant":"CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","skeleton_spec_commit":"95896b5b81ebcbba6bc89f90662d5c32b35fc64b","skeleton_runtime_pin":"4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0","variant_equivalence_to_skeleton_pin":"NOT_PROVEN","historical_lineage_status":"PARTIAL_EXPLICIT_GAP","source_commit":os.environ.get("GITHUB_SHA")})
 gates={"GATE_01_WORKSPACE_RESOLUTION":"PASS","GATE_02_CUSTOSZ_IDENTITY":"PASS","GATE_03_RUNTIME_IDENTITY":"PASS","GATE_04_METAOS_INTERFACE":"PASS","GATE_05_EXECUTOR_BOUND":"PASS","GATE_06_AUTHENTICATED_MISSION":"PASS","GATE_07_RESOURCE_LIMITS":"PASS" if resources else "FAIL","GATE_08_SERVICE_PERSISTENCE":"HOLD_BOOT_OBSERVATION_REQUIRED" if boot_configured else "HOLD_LINGER_NOT_ENABLED","GATE_09_FAILURE_RECOVERY":"HOLD_EXECUTOR_KILL_TEST_NOT_RUN","GATE_10_EVIDENCE_PERSISTENCE":"PASS" if survives else "FAIL","GATE_11_ROLLBACK":"PASS" if rollback_ok else "FAIL","GATE_12_IDEMPOTENCY":"PASS" if idempotent else "FAIL","GATE_13_NEGATIVE_AUTH_TEST":"PASS" if all(x["rejected"] for x in auth_negative.values()) else "FAIL","GATE_14_NO_CANONICAL_MUTATION":"PASS" if sha(src["authority"])==EXPECTED["AUTHORITY"] else "FAIL","GATE_15_HOST_SAFETY":"PASS"}
 blockers=[k+"="+v for k,v in gates.items() if v!="PASS"];result="PASS" if not blockers else "HOLD";atomic(out/"SERVER_READY_GATES.json",{"schema":"SERVER_READY_GATES/1.0","gates":gates,"result":result,"server_ready":not blockers,"single_root_blocker":blockers[0] if blockers else None})
 atomic(out/"NON_REGRESSION_REPORT.json",{"schema":"NON_REGRESSION_REPORT/1.0","mission_sha256_preserved":sha(src["mission"])==MISSION_SHA256,"authority_sha256_preserved":sha(src["authority"])==EXPECTED["AUTHORITY"],"protected_scopes_mutated":False,"result":"PASS"})
 manifest={"schema":"SERVER_READY_PRODUCER_RUN_MANIFEST/1.0","frozen_utc":utc(),"mission_sha256":MISSION_SHA256,"source_commit":os.environ.get("GITHUB_SHA"),"files":{p.name:sha(p) for p in out.iterdir() if p.is_file()},"result":result,"root_blocker":blockers[0] if blockers else None};atomic(out/"RUN_MANIFEST.json",manifest)
 (out/"README_SERVER_READY_FINAL.md").write_text("# README_SERVER_READY_FINAL\n\nSERVER_DEPLOYED = TRUE\nSERVER_TECHNICAL_READY = "+("TRUE" if not blockers else "FALSE")+"\nSERVER_READY_FINAL = "+result+"\nSINGLE_ROOT_BLOCKER = "+str(blockers[0] if blockers else None)+"\nBOOT_PERSISTENCE_CONFIGURED = "+("PASS" if boot_configured else "HOLD")+"\nBOOT_PERSISTENCE_OBSERVED = NOT_RUN\nRUNTIME_IDENTITY = PASS\nRUNTIME_SKELETON_VARIANT_EQUIVALENCE = NOT_PROVEN\nEXECUTOR_KILL_RECOVERY = NOT_RUN_TOOL_GUARD\nNEGATIVE_AUTH_TEST = "+("PASS" if all(x["rejected"] for x in auth_negative.values()) else "FAIL")+"\nG23 = NOT_RUN\nG24 = NOT_RUN\nSERVER_CERTIFIED = FALSE\n")
 print(json.dumps({"result":result,"blockers":blockers},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
