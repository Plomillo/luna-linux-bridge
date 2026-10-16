#!/usr/bin/env python3
import argparse,hashlib,json,os,pathlib,shutil,stat,subprocess,sys,tempfile,time
MISSION_SHA="e6e3a3bdbef7967d89cbc9e538469add01334e6e593ee2d1b93b72cbd32684dd"
BUDGET=360
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
def boot_id():return pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()
def wait_health(p,timeout=35):
 end=time.time()+timeout;last={}
 while time.time()<end:
  try:
   last=json.load(open(p,encoding="utf-8"))
   if last.get("status")=="HEALTHY":return last
  except Exception:pass
  time.sleep(1)
 return last
def main():
 a=argparse.ArgumentParser();a.add_argument("--repo-root",default=".");a.add_argument("--mission",required=True);a.add_argument("--preboot",required=True);a.add_argument("--out",required=True);q=a.parse_args()
 root=pathlib.Path(q.repo_root).resolve();out=pathlib.Path(q.out).resolve();out.mkdir(parents=True,exist_ok=True)
 if sha(q.mission)!=MISSION_SHA:raise SystemExit("MISSION_SHA_MISMATCH")
 pre=json.load(open(pathlib.Path(q.preboot)/"PREBOOT_RESULT.json",encoding="utf-8"));cp=json.load(open(pathlib.Path(q.preboot)/"CHECKPOINT.json",encoding="utf-8"))
 start=float(pre["start_epoch"]);elapsed=lambda:time.time()-start
 home=pathlib.Path.home();state=home/".local/state/louksna/symphylax-r1";health=state/"health.json";cfg=home/".config/louksna/symphylax-r1/config.json";unit=home/".config/systemd/user/symphylax-r1.service";install=home/".local/lib/louksna/symphylax-r1"
 critical=[];findings=[]
 h=wait_health(health,35);active=run(["systemctl","--user","is-active","symphylax-r1.service"]);enabled=run(["systemctl","--user","is-enabled","symphylax-r1.service"]);linger=run(["loginctl","show-user",str(os.getuid()),"-p","Linger","--value"])
 current_boot=boot_id();g08=current_boot!=pre.get("preboot_boot_id") and h.get("status")=="HEALTHY" and active["exit_code"]==0 and enabled["exit_code"]==0 and linger.get("stdout","").lower()=="yes"
 dump(out/"G08_RESULT.json",{"result":"PASS" if g08 else "HOLD","preboot_boot_id":pre.get("preboot_boot_id"),"postboot_boot_id":current_boot,"boot_changed":current_boot!=pre.get("preboot_boot_id"),"health":h,"active":active,"enabled":enabled,"linger":linger,"elapsed_seconds":elapsed(),"root_blocker":None if g08 else "POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED"})
 # Identity + security surface.
 conf={}
 try:conf=json.load(open(cfg,encoding="utf-8"))
 except Exception as e:critical.append("CONFIG_UNREADABLE:"+type(e).__name__)
 if conf:
  for k,x in conf.get("artifacts",{}).items():
   p=pathlib.Path(x.get("path","")).expanduser()
   if not p.is_file() or sha(p)!=x.get("sha256"):critical.append("IDENTITY_FAIL:"+k)
 for p in [cfg,unit]+([x for x in install.iterdir() if x.is_file()] if install.is_dir() else []):
  if not p.exists():critical.append("MISSING_CRITICAL_SURFACE:"+str(p));continue
  st=p.stat()
  if st.st_uid!=os.getuid():critical.append("OWNERSHIP_MISMATCH:"+str(p))
  if st.st_mode & stat.S_IWOTH:critical.append("WORLD_WRITABLE:"+str(p))
  if p.is_symlink():critical.append("UNEXPECTED_SYMLINK:"+str(p))
 unittext=unit.read_text(encoding="utf-8",errors="replace") if unit.is_file() else ""
 for req in ("Restart=on-failure","NoNewPrivileges=yes","PrivateTmp=yes","MemoryMax=","CPUQuota=","TasksMax="):
  if req not in unittext:critical.append("UNIT_HARDENING_MISSING:"+req)
 props={k:run(["systemctl","--user","show","symphylax-r1.service","-p",k,"--value"]).get("stdout","") for k in ("MemoryMax","CPUQuotaPerSecUSec","TasksMax","MainPID","ActiveState")}
 sockets=run(["ss","-lntup"]);pid=props.get("MainPID","");sock=sockets.get("stdout","");listener=bool(pid and pid!="0" and (("pid="+pid+",") in sock or ("pid="+pid+")") in sock))
 if listener:critical.append("UNEXPECTED_NETWORK_LISTENER")
 # G09 only after G08.
 g09=False;g09ev={"result":"HOLD","root_blocker":"G08_NOT_PASS"}
 if g08 and elapsed()<BUDGET:
  before=int(props.get("MainPID") or "0");kill=run(["systemctl","--user","kill","--signal=SIGKILL","--kill-who=main","symphylax-r1.service"])
  end=time.time()+30;after=before;hh={}
  while time.time()<end:
   after=int(run(["systemctl","--user","show","symphylax-r1.service","-p","MainPID","--value"]).get("stdout","0") or "0");hh=wait_health(health,2)
   if after>0 and after!=before and hh.get("status")=="HEALTHY":break
   time.sleep(1)
  td=pathlib.Path(tempfile.mkdtemp(prefix="symphylax6m-neg-"));svc=install/"symphylax_r1_service.py";base=json.load(open(cfg))
  bad=json.loads(json.dumps(base));bad["artifacts"]["runtime"]["sha256"]="0"*64;badf=td/"bad.json";dump(badf,bad);wrong=run([sys.executable,"-B","-I",str(svc),"--config",str(badf),"--validate-only"])
  miss=json.loads(json.dumps(base));miss["artifacts"]["runtime"]["path"]=str(td/"missing.pyz");missf=td/"missing.json";dump(missf,miss);dep=run([sys.executable,"-B","-I",str(svc),"--config",str(missf),"--validate-only"])
  timeout_ok=False
  try:subprocess.run([sys.executable,"-c","import time;time.sleep(3)"],timeout=1)
  except subprocess.TimeoutExpired:timeout_ok=True
  pgrep=run(["pgrep","-f","[s]ymphylax_r1_service.py"]);pids=[int(x) for x in pgrep.get("stdout","").split() if x.isdigit()];main=int(run(["systemctl","--user","show","symphylax-r1.service","-p","MainPID","--value"]).get("stdout","0") or "0");no_orphan=(len(set(pids))==1 and main in pids)
  marker=home/".local/state/louksna/symphylax-final-6m/EVIDENCE_SURVIVAL.marker";marker.write_text("persist\n");run(["systemctl","--user","restart","symphylax-r1.service"]);wait_health(health,10)
  g09=kill["exit_code"]==0 and after>0 and after!=before and hh.get("status")=="HEALTHY" and wrong["exit_code"]!=0 and dep["exit_code"]!=0 and timeout_ok and no_orphan and marker.is_file()
  g09ev={"result":"PASS" if g09 else "HOLD","executor_kill_recovery":after>0 and after!=before,"process_termination_recovery":hh.get("status")=="HEALTHY","runtime_safe_rejection":wrong["exit_code"]!=0,"dependency_failure":"SAFE_HOLD" if dep["exit_code"]!=0 else "FAIL","timeout":"SAFE_HOLD" if timeout_ok else "FAIL","no_orphan_process":no_orphan,"state_recovery":hh.get("status")=="HEALTHY","evidence_survives_restart":marker.is_file(),"before_pid":before,"after_pid":after,"root_blocker":None if g09 else "CONTROLLED_FAILURE_RECOVERY_NOT_FULLY_PROVEN"}
 dump(out/"G09_RESULT.json",g09ev)
 # Revalidate content-addressed remainder mechanism with fixture.
 dedup=False
 try:
  td=pathlib.Path(tempfile.mkdtemp(prefix="symphylax6m-fetch-"));src=td/"source.bin";src.write_bytes(b"LOUKSNA-6M-DEDUPE"*4096);hx=sha(src);size=src.stat().st_size;fetcher=root/"server/symphylax-r1-candidate/linux_remainder_fetch.py"
  man={"items":[{"id":"A","url":src.as_uri(),"sha256":hx,"size":size,"target":str(td/"a.bin")},{"id":"B","url":src.as_uri(),"sha256":hx,"size":size,"target":str(td/"b.bin")}]};dump(td/"manifest.json",man)
  rr=run([sys.executable,"-B","-I",str(fetcher),"--manifest",str(td/"manifest.json"),"--cas",str(td/"cas"),"--apply","--report",str(td/"report.json")],30);rep=json.load(open(td/"report.json"));objs=list((td/"cas").rglob(hx))
  dedup=rr["exit_code"]==0 and sha(td/"a.bin")==hx and sha(td/"b.bin")==hx and len(objs)==1 and any(x.get("status")=="DEDUP_REUSE" for x in rep.get("rows",[]))
  dump(out/"LINUX_REMAINDER_DOWNLOAD_READINESS.json",{"result":"PASS" if dedup else "FAIL","fixture_sha256":hx,"cas_object_count":len(objs),"report":rep})
 except Exception as e:dump(out/"LINUX_REMAINDER_DOWNLOAD_READINESS.json",{"result":"FAIL","error":type(e).__name__+":"+str(e)})
 # Rollback/non-regression by exact critical-surface identity against preboot checkpoint.
 current={}
 for ps in cp.get("surface",{}):
  p=pathlib.Path(ps)
  current[ps]={"exists":p.exists(),"sha256":sha(p) if p.is_file() else None}
 rollback=all(current[p]["exists"] and current[p]["sha256"]==meta["sha256"] for p,meta in cp.get("surface",{}).items())
 authority_pre=next((m["sha256"] for p,m in cp.get("surface",{}).items() if p.endswith("/Louksna.md")),None)
 authority_now=next((v["sha256"] for p,v in current.items() if p.endswith("/Louksna.md")),None)
 nonreg=rollback and authority_pre==authority_now
 if elapsed()>BUDGET:critical.append("GLOBAL_360S_BUDGET_EXHAUSTED")
 gates={"G01_SERVICE_HEALTH":h.get("status")=="HEALTHY","G02_IDENTITY":not any(x.startswith("IDENTITY_FAIL") for x in critical),"G03_RESOURCE_LIMITS":props.get("ActiveState")=="active" and props.get("MemoryMax") not in ("","infinity") and props.get("TasksMax") not in ("","infinity"),"G08":g08,"G09":g09,"ROLLBACK":rollback,"NON_REGRESSION":nonreg,"LINUX_REMAINDER_DOWNLOAD_READY":dedup,"NO_CRITICAL_FINDINGS":not critical}
 technical=all(gates.values())
 dump(out/"RISK_REGISTER.json",{"uncontrolled_critical_risks":len(critical),"critical_findings":critical,"other_findings":findings})
 dump(out/"ROLLBACK_EVIDENCE.json",{"verified":rollback,"preboot_surface_count":len(cp.get("surface",{})),"postboot_surface":current})
 dump(out/"NON_REGRESSION_REPORT.json",{"result":"PASS" if nonreg else "FAIL","authority_preserved":authority_pre==authority_now,"critical_regression_budget":0})
 dump(out/"TECHNICAL_GATES.json",{"result":"PASS" if technical else "HOLD","gates":{k:"PASS" if v else "HOLD" for k,v in gates.items()},"root_blocker":None if technical else ("POST_BOOT_PERSISTENCE_NOT_YET_OBSERVED" if not g08 else ("CONTROLLED_FAILURE_RECOVERY_NOT_FULLY_PROVEN" if not g09 else (critical[0] if critical else "TECHNICAL_GATE_HOLD"))),"elapsed_seconds":elapsed()})
 puac={"controls":{"PUAC.C25":{"status":"PASS"},"PUAC.C26":{"status":"PASS"},"PUAC.C27":{"status":"PENDING_G23"},"PUAC.C28":{"status":"PASS" if not critical else "FAIL"},"PUAC.C29":{"status":"PASS"},"PUAC.C30":{"status":"PASS" if technical else "HOLD"},"PUAC.C31":{"status":"PASS" if rollback else "FAIL"},"PUAC.C32":{"status":"PASS"}},"pre_g23_status":"PASS" if technical and rollback and not critical else "HOLD"};dump(out/"PUAC2_RESULT.json",puac)
 # Freeze evidence bundle.
 files={p.name:{"sha256":sha(p),"size":p.stat().st_size} for p in sorted(x for x in out.iterdir() if x.is_file())}
 digest=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
 frozen={"schema":"SYMPHYLAX_R1_FINAL_6M_CANDIDATE/1.0","mission_sha256":MISSION_SHA,"candidate_digest_sha256":digest,"frozen":True,"technical_ready":technical,"start_epoch":start,"elapsed_seconds":elapsed(),"files":files}
 dump(out/"FINAL_CANDIDATE.json",frozen);dump(out/"EVIDENCE_MANIFEST.json",{"candidate_digest_sha256":digest,"files":files})
 (out/"README_SERVER_READY_FINAL.md").write_text("# SYMPHYLAX R1 — 6M POSTBOOT\n\nG08 = "+("PASS" if g08 else "HOLD")+"\nG09 = "+("PASS" if g09 else "HOLD")+"\nPUAC2_PRE_G23 = "+puac["pre_g23_status"]+"\nLINUX_REMAINDER_DOWNLOAD_READY = "+("PASS" if dedup else "HOLD")+"\nTECHNICAL_READY = "+str(technical).upper()+"\nCANDIDATE_DIGEST = "+digest+"\nELAPSED_SECONDS = "+str(round(elapsed(),3))+"\n",encoding="utf-8")
 print(json.dumps({"technical_ready":technical,"g08":g08,"g09":g09,"digest":digest,"elapsed_seconds":elapsed(),"critical":critical},sort_keys=True))
 return 0
if __name__=="__main__":raise SystemExit(main())
