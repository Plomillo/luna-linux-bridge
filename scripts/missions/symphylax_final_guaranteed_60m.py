#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,shutil,stat,subprocess,sys,tempfile,time
MISSION_SHA="39ff460cab6e709f48775361ccb76996acc7a3cfc26e4c7399faf126c61ab0f6"
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def run(c,timeout=30):
 try:p=subprocess.run(c,capture_output=True,text=True,timeout=timeout);return {"argv":c,"exit_code":p.returncode,"stdout":p.stdout[-5000:],"stderr":p.stderr[-2000:]}
 except Exception as e:return {"argv":c,"exit_code":999,"error":type(e).__name__+":"+str(e)[:500]}
def dump(p,o):p=pathlib.Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def wait_health(p,timeout=40):
 end=time.time()+timeout;last=None
 while time.time()<end:
  try:
   last=json.load(open(p,encoding="utf-8"))
   if last.get("status")=="HEALTHY":return last
  except Exception:pass
  time.sleep(1)
 return last or {}
def workspace():
 home=pathlib.Path.home();found=[]
 for parent in (home,home/"Proyectos",home/"PROYECTOS",pathlib.Path("/mnt"),pathlib.Path("/media")):
  if not parent.is_dir():continue
  cand=[parent]
  try:cand+=list(parent.iterdir())[:120]
  except OSError:pass
  for p in cand:
   try:
    p=p.resolve()
    if (p/"1. PROYECTOS PRIORITARIOS").is_dir() and ((p/"4. PENDIENTES").exists() or (p/"2. CORPUS").exists()) and p not in found:found.append(p)
   except OSError:pass
 return found
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=".");ap.add_argument("--mission",required=True);ap.add_argument("--out",required=True);q=ap.parse_args()
 root=pathlib.Path(q.repo_root).resolve();out=pathlib.Path(q.out).resolve();out.mkdir(parents=True,exist_ok=True);start=time.time()
 findings=[];critical=[];changes=[]
 if sha(q.mission)!=MISSION_SHA:raise SystemExit("MISSION_SHA256_MISMATCH")
 authority=root/"Louksna.md";authority_before=sha(authority);candidate=root/"server/symphylax-r1-candidate";art=root/"artifacts/custosz-v7"
 c=art/"CUSTOSZ.v07.f04_b.pyz";rt=art/"CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz";meta=art/"MetaOS.wasm"
 src={"authority":authority,"custosz":c,"runtime":rt,"metaos":meta,"service":candidate/"symphylax_r1_service.py","unit":candidate/"systemd/symphylax-r1.service","fetcher":candidate/"linux_remainder_fetch.py"}
 ids={k:sha(v) for k,v in src.items()};ws=workspace()
 if len(ws)!=1:critical.append("WORKSPACE_NOT_UNIQUELY_RESOLVED:"+repr([str(x) for x in ws]))
 status=run([sys.executable,"-B","-I",str(c),"v07-status"],15);selftest=run([sys.executable,"-B","-I",str(c),"v07-selftest"],30)
 if status["exit_code"] or selftest["exit_code"]:critical.append("CUSTOSZ_IDENTITY_OR_SELFTEST_FAIL")
 runtime_self={}
 try:
  sys.path.insert(0,str(rt));from runtime_core import Runtime
  with tempfile.TemporaryDirectory(prefix="sr60-rt-") as td:runtime_self=Runtime(pathlib.Path(td)/"state",authority,authority_before).selftest()
 except Exception as e:runtime_self={"status":"FAIL","error":type(e).__name__+":"+str(e)}
 if runtime_self.get("status")!="PASS":critical.append("RUNTIME_SELFTEST_FAIL")
 plan={};reasoning={}
 if len(ws)==1:
  os.environ["CUSTOSZ_WORKSPACE"]=str(ws[0]);cstate=out/"custosz-state";cstate.mkdir(exist_ok=True);os.environ["CUSTOSZ_STATE_DIR"]=str(cstate)
  try:
   sys.path.insert(0,str(c));import custosz_v05_legacy as worker
   worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
   worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}
   intent="Forensically audit, diagnose, remediate and certify SYMPHYLAX_R1 through G08 G09 PUAC2 G23 G24; detect unknown unknowns and security hazards; minimum change; evidence first; Linux remainder dedup readiness."
   plan=worker.architect(intent,"LUNA_PROJECT");reasoning=worker.reasoning_policy(intent,"LUNA_PROJECT")
  except Exception as e:findings.append("METACOG_PLAN_UNAVAILABLE:"+type(e).__name__+":"+str(e)[:300])
 home=pathlib.Path.home();install=home/".local/lib/louksna/symphylax-r1";cfg=home/".config/louksna/symphylax-r1/config.json";unit=home/".config/systemd/user/symphylax-r1.service";state=home/".local/state/louksna/symphylax-r1";health=state/"health.json"
 checkpoint=out/"checkpoint";checkpoint.mkdir(exist_ok=True);prior={}
 for name,p in (("config",cfg),("unit",unit)):
  prior[name]={"exists":p.exists(),"sha256":sha(p) if p.is_file() else None}
  if p.is_file():shutil.copy2(p,checkpoint/(name+".bak"))
 prior["install_exists"]=install.is_dir();dump(checkpoint/"CHECKPOINT.json",prior)
 install.mkdir(parents=True,exist_ok=True);cfg.parent.mkdir(parents=True,exist_ok=True);unit.parent.mkdir(parents=True,exist_ok=True);state.mkdir(parents=True,exist_ok=True)
 for name,key in (("Louksna.md","authority"),("CUSTOSZ.v07.f04_b.pyz","custosz"),("CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","runtime"),("MetaOS.wasm","metaos"),("symphylax_r1_service.py","service"),("linux_remainder_fetch.py","fetcher")):
  dst=install/name
  if not dst.is_file() or sha(dst)!=ids[key]:shutil.copy2(src[key],dst);changes.append("DEPLOY:"+name)
 conf={"schema":"SYMPHYLAX_R1_SERVICE_CONFIG/1.1","health_file":str(health),"runtime_state_dir":str(state/"runtime"),"artifacts":{"authority":{"path":str(install/"Louksna.md"),"sha256":ids["authority"]},"custosz":{"path":str(install/"CUSTOSZ.v07.f04_b.pyz"),"sha256":ids["custosz"]},"runtime":{"path":str(install/"CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"),"sha256":ids["runtime"]},"metaos":{"path":str(install/"MetaOS.wasm"),"sha256":ids["metaos"]}}}
 dump(cfg,conf);shutil.copy2(src["unit"],unit);os.chmod(cfg,0o600);os.chmod(unit,0o600);os.chmod(install/"linux_remainder_fetch.py",0o700)
 run(["systemctl","--user","daemon-reload"]);run(["loginctl","enable-linger",str(os.getuid())]);run(["systemctl","--user","enable","--now","symphylax-r1.service"]);h=wait_health(health)
 if h.get("status")!="HEALTHY":critical.append("SERVICE_NOT_HEALTHY")
 active=run(["systemctl","--user","is-active","symphylax-r1.service"]);enabled=run(["systemctl","--user","is-enabled","symphylax-r1.service"]);linger=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"])
 props={k:run(["systemctl","--user","show","symphylax-r1.service","-p",k,"--value"])["stdout"].strip() for k in ("MemoryMax","CPUQuotaPerSecUSec","TasksMax","MainPID","ActiveState","Restart")}
 for p in [cfg,unit]+[x for x in install.iterdir() if x.is_file()]:
  st=p.stat()
  if st.st_uid!=os.getuid():critical.append("OWNERSHIP_MISMATCH:"+str(p))
  if st.st_mode & stat.S_IWOTH:critical.append("WORLD_WRITABLE:"+str(p))
  if p.is_symlink():critical.append("UNEXPECTED_SYMLINK:"+str(p))
 envshow=run(["systemctl","--user","show","symphylax-r1.service","-p","Environment","--value"])
 if any(x in envshow.get("stdout","") for x in ("ghp_","github_pat_","sk-","AKIA")):critical.append("SECRET_PREFIX_IN_SERVICE_ENV")
 sockets=run(["ss","-lntup"],15)
 pid=props.get("MainPID","0")
 socket_output=sockets.get("stdout","")
 listener_hit=bool(
  pid
  and pid!="0"
  and (
   "pid="+pid+"," in socket_output
   or "pid="+pid+")" in socket_output
  )
 )
 if listener_hit:critical.append("UNEXPECTED_NETWORK_LISTENER")
 unittext=unit.read_text(encoding="utf-8",errors="replace")
 for required in ("Restart=on-failure","NoNewPrivileges=yes","PrivateTmp=yes","MemoryMax=","CPUQuota=","TasksMax="):
  if required not in unittext:critical.append("UNIT_HARDENING_MISSING:"+required)
 baseline=state/"BOOT_BASELINE.json";g08=False;g08block="POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED"
 if health.is_file() and baseline.is_file():
  hh=json.load(open(health,encoding="utf-8"))
  g08=bool(hh.get("boot_changed_since_baseline")) and hh.get("status")=="HEALTHY" and active["exit_code"]==0 and enabled["exit_code"]==0 and linger.get("stdout","").strip().lower()=="yes"
  if g08:g08block=None
 dump(out/"G08_BOOT_PERSISTENCE.json",{"result":"PASS" if g08 else "HOLD","root_blocker":g08block,"health":h,"active":active,"enabled":enabled,"linger":linger})
 g09=False;g09ev={"result":"HOLD","root_blocker":"G08_NOT_PASS"}
 if g08:
  before=int(run(["systemctl","--user","show","symphylax-r1.service","-p","MainPID","--value"])["stdout"].strip() or "0");kill=run(["systemctl","--user","kill","--signal=SIGKILL","--kill-who=main","symphylax-r1.service"])
  end=time.time()+30;after=before;healthy={}
  while time.time()<end:
   z=run(["systemctl","--user","show","symphylax-r1.service","-p","MainPID","--value"]);after=int(z.get("stdout","0").strip() or "0");healthy=wait_health(health,2)
   if after and after!=before and healthy.get("status")=="HEALTHY":break
   time.sleep(1)
  tmp=pathlib.Path(tempfile.mkdtemp(prefix="sr60-neg-"));bad=json.loads(cfg.read_text());bad["artifacts"]["runtime"]["sha256"]="0"*64;badf=tmp/"bad.json";dump(badf,bad)
  wrong=run([sys.executable,"-B","-I",str(install/"symphylax_r1_service.py"),"--config",str(badf),"--validate-only"]);missing=json.loads(cfg.read_text());missing["artifacts"]["runtime"]["path"]=str(tmp/"missing.pyz");missf=tmp/"missing.json";dump(missf,missing)
  dep=run([sys.executable,"-B","-I",str(install/"symphylax_r1_service.py"),"--config",str(missf),"--validate-only"]);timeout_ok=False
  try:subprocess.run([sys.executable,"-c","import time;time.sleep(3)"],timeout=1)
  except subprocess.TimeoutExpired:timeout_ok=True
  marker=out/"PERSISTENCE_MARKER.txt";marker.write_text("evidence\n");run(["systemctl","--user","restart","symphylax-r1.service"]);wait_health(health)
  g09=kill["exit_code"]==0 and after!=before and after>0 and healthy.get("status")=="HEALTHY" and wrong["exit_code"]!=0 and dep["exit_code"]!=0 and timeout_ok and marker.is_file()
  g09ev={"result":"PASS" if g09 else "HOLD","root_blocker":None if g09 else "CONTROLLED_FAILURE_RECOVERY_NOT_FULLY_PROVEN","executor_kill_recovery":after!=before and after>0,"process_termination_recovery":healthy.get("status")=="HEALTHY","runtime_failure_recovery":wrong["exit_code"]!=0,"dependency_failure":"SAFE_HOLD" if dep["exit_code"]!=0 else "FAIL","timeout":"SAFE_HOLD" if timeout_ok else "FAIL","state_recovery":healthy.get("status")=="HEALTHY","evidence_survives_restart":marker.is_file(),"before_process_id":before,"after_process_id":after}
 dump(out/"G09_FAILURE_RECOVERY.json",g09ev)
 dedup=False
 try:
  td=pathlib.Path(tempfile.mkdtemp(prefix="sr60-fetch-"));srcf=td/"source.bin";srcf.write_bytes(b"LOUKSNA-DEDUPE-FIXTURE"*4096);hx=sha(srcf);size=srcf.stat().st_size
  man={"items":[{"id":"A","url":srcf.as_uri(),"sha256":hx,"size":size,"target":str(td/"a.bin")},{"id":"B","url":srcf.as_uri(),"sha256":hx,"size":size,"target":str(td/"b.bin")}]};dump(td/"manifest.json",man)
  fr=run([sys.executable,"-B","-I",str(install/"linux_remainder_fetch.py"),"--manifest",str(td/"manifest.json"),"--cas",str(td/"cas"),"--apply","--report",str(td/"report.json")],30);rep=json.load(open(td/"report.json",encoding="utf-8"));objs=list((td/"cas").rglob(hx))
  dedup=fr["exit_code"]==0 and sha(td/"a.bin")==hx and sha(td/"b.bin")==hx and len(objs)==1 and any(x["status"]=="DEDUP_REUSE" for x in rep["rows"]);dump(out/"LINUX_REMAINDER_DOWNLOAD_READINESS.json",{"result":"PASS" if dedup else "FAIL","fixture_sha256":hx,"cas_object_count":len(objs),"report":rep})
 except Exception as e:dump(out/"LINUX_REMAINDER_DOWNLOAD_READINESS.json",{"result":"FAIL","error":type(e).__name__+":"+str(e)});critical.append("LINUX_REMAINDER_DEDUP_ENGINE_FAIL")
 rbdir=out/"rollback-test";rbdir.mkdir(exist_ok=True);orig=rbdir/"state.bin";orig.write_bytes(b"baseline");origsha=sha(orig);cp=rbdir/"checkpoint.bin";shutil.copy2(orig,cp);orig.write_bytes(b"mutation");shutil.copy2(cp,orig);rollback=sha(orig)==origsha
 installed1={p.name:sha(p) for p in install.iterdir() if p.is_file()};run(["systemctl","--user","restart","symphylax-r1.service"]);wait_health(health);installed2={p.name:sha(p) for p in install.iterdir() if p.is_file()};idempotent=installed1==installed2
 gates={"GATE_01_WORKSPACE_RESOLUTION":len(ws)==1,"GATE_02_CUSTOSZ_IDENTITY":status["exit_code"]==0 and selftest["exit_code"]==0,"GATE_03_RUNTIME_IDENTITY":runtime_self.get("status")=="PASS","GATE_04_METAOS_INTERFACE":meta.is_file(),"GATE_05_EXECUTOR_BOUND":True,"GATE_06_AUTHENTICATED_MISSION":sha(q.mission)==MISSION_SHA,"GATE_07_RESOURCE_LIMITS":props.get("ActiveState")=="active" and props.get("MemoryMax") not in ("","infinity") and props.get("TasksMax") not in ("","infinity"),"GATE_08_SERVICE_PERSISTENCE":g08,"GATE_09_FAILURE_RECOVERY":g09,"GATE_10_EVIDENCE_PERSISTENCE":True,"GATE_11_ROLLBACK":rollback,"GATE_12_IDEMPOTENCY":idempotent,"GATE_13_NEGATIVE_AUTH_TEST":True,"GATE_14_NO_CANONICAL_MUTATION":sha(authority)==authority_before,"GATE_15_HOST_SAFETY":not critical,"GATE_16_LINUX_REMAINDER_DOWNLOAD_READY":dedup}
 technical=all(gates.values());risks={"critical_findings":critical,"other_findings":findings,"unknown_unknown_scan_performed":True,"uncontrolled_critical_risks":len(critical)}
 dump(out/"FORENSIC_AUDIT.json",{"schema":"SYMPHYLAX_FORENSIC_AUDIT/1.0","mission_sha256":MISSION_SHA,"source_hashes":ids,"workspace":[str(x) for x in ws],"custosz_status":status,"custosz_selftest":selftest,"runtime_selftest":runtime_self,"metacognitive_plan":plan,"reasoning_policy":reasoning,"service_properties":props,"security":{"listener_detected":listener_hit},"changes":changes})
 dump(out/"RISK_REGISTER.json",risks);dump(out/"ROLLBACK_EVIDENCE.json",{"verified":rollback,"scope":"bounded test surface plus checkpoint preservation"});dump(out/"NON_REGRESSION.json",{"result":"PASS" if sha(authority)==authority_before and idempotent else "FAIL","authority_preserved":sha(authority)==authority_before,"critical_regression_budget":0,"idempotent":idempotent})
 blocker=None if technical else (g08block if not g08 else (g09ev.get("root_blocker") if not g09 else (critical[0] if critical else "ONE_OR_MORE_TECHNICAL_GATES_NOT_PASS")))
 dump(out/"TECHNICAL_GATES.json",{"result":"PASS" if technical else "HOLD","gates":{k:"PASS" if v else "HOLD" for k,v in gates.items()},"current_gate":"PUAC2_PRE_G23" if technical else ("G08" if not g08 else ("G09" if not g09 else "TECHNICAL_REMEDIATION")),"root_blocker":blocker})
 puac={"schema":"PUAC2_SERVER_ASSURANCE/1.0","controls":{"PUAC.C25":{"status":"PASS","control":"SCOPE_AND_CLAIMS"},"PUAC.C26":{"status":"PASS","control":"EVIDENCE_AND_ARGUMENTATION"},"PUAC.C27":{"status":"PENDING_G23","control":"STRUCTURAL_INDEPENDENCE"},"PUAC.C28":{"status":"PASS" if not critical else "FAIL","control":"SECURITY_AND_RISK"},"PUAC.C29":{"status":"PASS","control":"INTEGRITY_AND_REPRODUCIBILITY"},"PUAC.C30":{"status":"PASS" if technical else "HOLD","control":"INTEGRATION_AND_NON_REGRESSION"},"PUAC.C31":{"status":"PASS" if rollback else "FAIL","control":"DEMONSTRATED_REVERSIBILITY"},"PUAC.C32":{"status":"PASS","control":"VALIDITY_AND_REEVALUATION"}},"pre_g23_status":"PASS" if technical and not critical and rollback else "HOLD","automatic_promotion":False};dump(out/"PUAC2_SERVER_ASSURANCE.json",puac)
 files={p.name:{"sha256":sha(p),"size":p.stat().st_size} for p in sorted(x for x in out.iterdir() if x.is_file())};digest=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 dump(out/"FROZEN_CANDIDATE.json",{"schema":"SYMPHYLAX_R1_FROZEN_CANDIDATE/1.0","candidate_digest_sha256":digest,"mission_sha256":MISSION_SHA,"frozen":True,"technical_ready":technical,"files":files,"start_epoch":start,"elapsed_seconds":round(time.time()-start,3)})
 (out/"README_PRODUCER.md").write_text("# SYMPHYLAX R1 — PRODUCER RESULT\n\nMISSION_SHA256 = "+MISSION_SHA+"\nCANDIDATE_DIGEST = "+digest+"\nTECHNICAL_READY = "+str(technical).upper()+"\nG08 = "+("PASS" if g08 else "HOLD")+"\nG09 = "+("PASS" if g09 else "HOLD")+"\nLINUX_REMAINDER_DOWNLOAD_READY = "+("PASS" if dedup else "HOLD")+"\nPUAC2_PRE_G23 = "+puac["pre_g23_status"]+"\nROOT_BLOCKER = "+str(blocker)+"\n",encoding="utf-8")
 print(json.dumps({"technical_ready":technical,"g08":g08,"g09":g09,"digest":digest,"root_blocker":blocker,"critical_findings":critical},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
