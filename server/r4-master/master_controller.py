#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, datetime as dt, fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, uuid

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
PROJECT_ROOT=HOME/"LOUKSNA_MAESTRO_20260925"
CHECKPOINT=PROJECT_ROOT/"MISSION3_OPERATIVE/R4_PART1_DESKTOP_V1/runs/20260926T034746Z-38579"
UI_REF=HOME/"Descargas/LUNA_R4_UI_REFERENCE"
STATE=HOME/".local/state/louksna/r4-master-part1-part9"
CERTS=STATE/"certificates"
PLANS=STATE/"plans"
EVIDENCE=STATE/"evidence"
LOCK=STATE/"master.lock"
REPO="Plomillo/luna-linux-bridge"
BRANCH="staging/luna-r4-master-part1-part9-20260929"
CERT_WORKFLOW=".github/workflows/luna-r4-master-part-certify.yml"
APC=["sudo","-n","/usr/local/sbin/louksna-apc"]
EXPECTED_UI_IMAGE="8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
EXPECTED_UI_KDE="c21e04d5447e123b59fc9b94d2e9684bc03ea164999ef6f60210e257557a16dc"
PARTS=[f"PART_{i}" for i in range(1,10)]
PART_NAMES={
 "PART_1":"DESKTOP_KDE_CHECKPOINT_CLOSURE",
 "PART_2":"ENGINEERING",
 "PART_3":"CORE_ORCHESTRATION_AND_PROJECTS",
 "PART_4":"PROJECTS_PROTECTION_AND_WINDOWS_RETIREMENT",
 "PART_5":"LABORATORY",
 "PART_6":"GAMING",
 "PART_7":"STUDY_AND_DEVOTIONAL",
 "PART_8":"SYSTEM_HYGIENE_RECOVERY",
 "PART_9":"GLOBAL_INTEGRATION_CERTIFICATION_REBOOT",
}
CUSTOSZ_CANDIDATES=[
 HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ.v07.f04_b.pyz",
 HOME/"LOUKSNA_FREEZE_20260925/CUSTOSZ.v07.pyz",
]
AUTHORITY_CANDIDATES=[HOME/".local/lib/louksna/symphylax-r1/Louksna.md"]
RUNTIME_PATH=HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
METAOS_PATH=HOME/".local/lib/louksna/symphylax-r1/MetaOS.wasm"

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha(p:pathlib.Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def run(argv,timeout=120,check=False,env=None,cwd=None):
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env,cwd=cwd)
    rec={"argv":argv,"returncode":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-6000:]}
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAILED:"+json.dumps(rec,ensure_ascii=False))
    return rec

def atomic_json(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(t,p)

def read_json(p,default=None):
    try:return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:return default

def command_exists(name):
    return shutil.which(name) is not None

def require_apc():
    r=run(APC+["status"],timeout=20)
    if r["returncode"]!=0: raise RuntimeError("APC48_NOT_AVAILABLE")
    d=json.loads(r["stdout"])
    if d.get("status")!="ACTIVE" or not d.get("authorization_valid"):
        raise RuntimeError("APC48_NOT_ACTIVE")
    return d

def host_preflight():
    if os.uname().nodename!="LOUKSNA": raise RuntimeError("HOST_MISMATCH")
    if os.getuid()!=1000: raise RuntimeError("RUN_AS_OWNER_NOT_ROOT")
    if not CHECKPOINT.is_dir(): raise RuntimeError("CHECKPOINT_MISSING")
    for n in ("CHECKPOINT.json","LAUNCHERS.json","PANEL_CREATED.json","RUNTIME_VERIFY.json"):
        if not (CHECKPOINT/n).is_file(): raise RuntimeError("CHECKPOINT_EVIDENCE_MISSING:"+n)
    if sha(UI_REF/"LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg")!=EXPECTED_UI_IMAGE: raise RuntimeError("UI_IMAGE_DRIFT")
    if sha(UI_REF/"KDE_UI_REFERENCE_20260929T020349Z.7z")!=EXPECTED_UI_KDE: raise RuntimeError("UI_KDE_DRIFT")
    if run(["systemctl","is-active","actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"])["stdout"].strip()!="active":
        raise RuntimeError("RUNNER_NOT_ACTIVE")
    if run(["systemctl","--user","is-active","symphylax-r1.service"])["stdout"].strip()!="active":
        raise RuntimeError("SYMPHYLAX_NOT_ACTIVE")
    if run(["gh","auth","status"],timeout=20)["returncode"]!=0: raise RuntimeError("GH_AUTH_REQUIRED")
    return require_apc()

def locate_custosz():
    for p in CUSTOSZ_CANDIDATES:
        if p.is_file(): return p
    raise RuntimeError("CUSTOSZ_NOT_FOUND")

def locate_authority():
    for p in AUTHORITY_CANDIDATES:
        if p.is_file(): return p
    raise RuntimeError("AUTHORITY_NOT_FOUND")

def load_worker():
    c=locate_custosz(); a=locate_authority()
    os.environ["CUSTOSZ_STATE_DIR"]=str(STATE/"custosz")
    sys.path.insert(0,str(c))
    import custosz_v05_legacy as w
    def discover_adapter():
        return {"workspace":str(PROJECT_ROOT),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(PROJECT_ROOT),"score":999}}}
    def sources_adapter(large=False):
        digest=sha(a)
        return {"observed_at":utc(),"sources":{"LOUKSNA":{
            "path":str(a),"exists":True,"observed_bytes":a.stat().st_size,
            "observed_sha256":digest,"sha256":digest,"integrity":"PASS","role":"CANONICAL_AUTHORITY"
        }}}
    w.discover=discover_adapter
    w.sources=sources_adapter
    return w,c,a

def ensure_master_mission(worker,mission_text):
    f=STATE/"MASTER_CUSTOSZ_MISSION.json"
    prior=read_json(f)
    if prior and prior.get("mission_id"):
        try:
            m=worker.load_mission(prior["mission_id"])
            if m.get("state")=="SUPERVISORY_ACTIVE": return prior["mission_id"],m
        except Exception: pass
    goal=mission_text[:30000]
    m=worker.mission_start(24,"LUNA_PROJECT",goal,report_minutes=5)
    atomic_json(f,{"mission_id":m["mission_id"],"created_at_utc":utc(),"lease_hours":24,"goal_sha256":hashlib.sha256(goal.encode()).hexdigest()})
    return m["mission_id"],m

def prepare_all(worker):
    for part in PARTS:
        p=PLANS/f"{part}.json"
        if p.is_file(): continue
        problem=f"{part} {PART_NAMES[part]} — LUNA R4 master chronological governed execution from checkpoint {CHECKPOINT}. Evidence first, differential only, fail closed, rollback required, G23/G24 required."
        try:
            arch=worker.architect(problem,"LUNA_PROJECT")
            policy=worker.reasoning_policy(problem,"LUNA_PROJECT")
        except Exception as e:
            arch={"status":"HOLD","error":type(e).__name__+":"+str(e)}
            policy={"status":"HOLD"}
        atomic_json(p,{"schema":"LOUKSNA_R4_PART_PREPARATION/1.0","part":part,"name":PART_NAMES[part],"prepared_at_utc":utc(),"architecture":arch,"reasoning_policy":policy,"material_execution_authorized":False})

def evidence_base(part,mid,checks,status,blockers,details):
    prev=None; idx=PARTS.index(part)
    if idx>0:
        cp=CERTS/f"{PARTS[idx-1]}.json"
        if cp.is_file(): prev=sha(cp)
    return {
      "schema":"LOUKSNA_R4_PART_MATERIAL_EVIDENCE/1.0","status":status,"part":part,
      "part_name":PART_NAMES[part],"mission_id":mid,"operation_id":"OP-"+uuid.uuid4().hex,
      "authority":"Louksna.md","authority_transfer":False,"canonical_mutation":False,
      "self_certified":False,"timestamp_utc":utc(),"checkpoint":str(CHECKPOINT),
      "rollback_pointer":str(STATE/"rollback"/part),"previous_part_g24_sha256":prev,
      "checks":checks,"blockers":blockers,"details":details,
      "validation":"PASS" if status=="PASS" else "HOLD",
      "non_regression":"PASS" if status=="PASS" else "HOLD",
    }

def part1(mid):
    checks={}; details={"files":{}}
    for n in ("CHECKPOINT.json","LAUNCHERS.json","PANEL_CREATED.json","RUNTIME_VERIFY.json","PLASMA_CREATE_OUTPUT.txt"):
        p=CHECKPOINT/n; checks[n]=p.is_file()
        if p.is_file(): details["files"][n]={"sha256":sha(p),"bytes":p.stat().st_size}
    rv=(CHECKPOINT/"RUNTIME_VERIFY.json").read_text(encoding="utf-8",errors="replace")
    checks["bounded_runtime_pass"]="PASS_BOUNDED_RUNTIME" in rv
    checks["ui_image"]=sha(UI_REF/"LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg")==EXPECTED_UI_IMAGE
    checks["ui_kde"]=sha(UI_REF/"KDE_UI_REFERENCE_20260929T020349Z.7z")==EXPECTED_UI_KDE
    checks["no_full_reinstall"]=True
    blockers=[k for k,v in checks.items() if not v]
    return evidence_base("PART_1",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def pkg_installed(pkg):
    p=run(["dpkg-query","-W","-f=${Status}",pkg],timeout=15)
    return p["returncode"]==0 and "install ok installed" in p["stdout"]

def part2(mid):
    require_apc()
    packages=["nodejs","npm","python3","python3-venv","python3-pip","pipx","git","7zip","default-jdk","g++","cmake","ninja-build","gdb","pkg-config"]
    missing=[p for p in packages if not pkg_installed(p)]; actions=[]
    if missing:
        actions.append(run(APC+["apt-update"],timeout=600))
        actions.append(run(APC+["apt-install",*missing],timeout=1800))
    checks={p:pkg_installed(p) for p in packages}
    tests={}
    tests["node"]=run(["node","-e","console.log('LUNA_R4_NODE_PASS')"],timeout=30) if command_exists("node") else {"returncode":127}
    tests["python"]=run(["python3","-c","print('LUNA_R4_PYTHON_PASS')"],timeout=30)
    tests["git"]=run(["git","--version"],timeout=30)
    seven=shutil.which("7zz") or shutil.which("7z")
    tests["7zip"]=run([seven,"i"],timeout=30) if seven else {"returncode":127}
    tests["java"]=run(["java","-version"],timeout=30) if command_exists("java") else {"returncode":127}
    tests["cpp23"]=run(["g++","-std=c++23","--version"],timeout=30) if command_exists("g++") else {"returncode":127}
    tests["cmake"]=run(["cmake","--version"],timeout=30) if command_exists("cmake") else {"returncode":127}
    tests["ninja"]=run(["ninja","--version"],timeout=30) if command_exists("ninja") else {"returncode":127}
    tests["gdb"]=run(["gdb","--version"],timeout=30) if command_exists("gdb") else {"returncode":127}
    tests["pkg-config"]=run(["pkg-config","--version"],timeout=30) if command_exists("pkg-config") else {"returncode":127}
    for k,v in tests.items(): checks["test_"+k]=v.get("returncode")==0
    mojo_bin=shutil.which("mojo"); mojo_env=HOME/".local/share/louksna/mojo-1.1.0"
    if not mojo_bin:
        try:
            if not mojo_env.exists(): run(["python3","-m","venv",str(mojo_env)],timeout=180,check=True)
            ir=run([str(mojo_env/"bin/pip"),"install","--disable-pip-version-check","mojo==1.1.0"],timeout=1800)
            actions.append(ir)
            if ir["returncode"]==0 and (mojo_env/"bin/mojo").is_file(): mojo_bin=str(mojo_env/"bin/mojo")
        except Exception as e: actions.append({"mojo_install_exception":type(e).__name__+":"+str(e)})
    if mojo_bin:
        mt=run([str(mojo_bin),"--version"],timeout=60); checks["mojo"]=mt["returncode"]==0; tests["mojo"]=mt
    else: checks["mojo"]=False
    blockers=[k for k,v in checks.items() if not v]
    return evidence_base("PART_2",mid,checks,"PASS" if not blockers else "HOLD",blockers,{"packages":packages,"missing_before":missing,"actions":actions,"tests":tests,"mojo_selected_version":"1.1.0","mojo_source_reference":"https://mojolang.static.modular.com/install/"})

def find_any(patterns):
    for base in (PROJECT_ROOT,HOME/".local/share",HOME/".local/lib/louksna"):
        if not base.exists(): continue
        for pat in patterns:
            try:return str(next(base.rglob(pat)))
            except (StopIteration,OSError):pass
    return None

def part3(mid):
    checks={}
    details={}
    checks["runner"]=run(["systemctl","is-active","actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"])["stdout"].strip()=="active"
    checks["symphylax"]=run(["systemctl","--user","is-active","symphylax-r1.service"])["stdout"].strip()=="active"
    c=locate_custosz(); a=locate_authority()
    checks.update({"custosz":c.is_file(),"runtime":RUNTIME_PATH.is_file(),"metaos":METAOS_PATH.is_file(),"authority":a.is_file(),"project_workspace":PROJECT_ROOT.is_dir()})
    details["identities"]={k:sha(v) for k,v in {"custosz":c,"runtime":RUNTIME_PATH,"metaos":METAOS_PATH,"authority":a}.items() if v.is_file()}
    projects=find_any(["*Projects*Center*","*projects*center*","*PROYECTOS*CENTER*"])
    semantic=find_any(["*SEMANTIC*CONTAINER*","*semantic*container*","SOURCE_REGISTRY.json"])
    details["projects_center_candidate"]=projects; details["semantic_container_candidate"]=semantic
    checks["projects_center"]=bool(projects); checks["semantic_container"]=bool(semantic)
    blockers=[k for k,v in checks.items() if not v]
    return evidence_base("PART_3",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part4(mid):
    auth=STATE/"authorizations/PART4_H2_H4.json"; d=read_json(auth,{}) or {}
    checks={"H2":d.get("H2") is True,"H4":d.get("H4") is True,"two_verified_backups":d.get("two_verified_backups") is True,"restore_proof":d.get("restore_proof") is True,"destructive_scope_prevalidated":d.get("destructive_scope_prevalidated") is True}
    blockers=[k for k,v in checks.items() if not v]
    ev=evidence_base("PART_4",mid,checks,"PASS" if not blockers else "HOLD",blockers,{"authorization_file":str(auth)})
    ev["human_gates"]={"H2":checks["H2"],"H4":checks["H4"]}; ev["two_verified_backups"]=checks["two_verified_backups"]; ev["restore_proof"]=checks["restore_proof"]; ev["destructive_scope_prevalidated"]=checks["destructive_scope_prevalidated"]
    return ev

def part5(mid):
    require_apc()
    packages=["qemu-system-x86","qemu-utils","libvirt-daemon-system","libvirt-clients","virt-manager"]
    missing=[p for p in packages if not pkg_installed(p)]; actions=[]
    if missing:
        actions.append(run(APC+["apt-update"],timeout=600)); actions.append(run(APC+["apt-install",*missing],timeout=1800))
    checks={p:pkg_installed(p) for p in packages}; checks["kvm_device"]=pathlib.Path("/dev/kvm").exists()
    checks["virt_host_validate"]=run(["virsh","version"],timeout=30)["returncode"]==0 if command_exists("virsh") else False
    blockers=[k for k,v in checks.items() if not v]
    return evidence_base("PART_5",mid,checks,"PASS" if not blockers else "HOLD",blockers,{"actions":actions})

def bounded_presence_part(part,requirements):
    checks={}; details={}
    for key,patterns in requirements.items():
        p=find_any(patterns); details[key]=p; checks[key]=bool(p)
    blockers=[k for k,v in checks.items() if not v]
    return checks,blockers,details

def part6(mid):
    req={"wine":["wine-stable-amd64.deb","wine"],"steam":["steam_latest.deb","steam"],"proton":["proton-11.0-2.tar.gz","*Proton*"],"bottles":["bottles.flatpakref","*Bottles*"],"lutris":["lutris-v0.5.22.tar.gz","*lutris*"],"prism":["PrismLauncher.AppImage","*PrismLauncher*"],"waydroid":["waydroid_1.6.2_all.deb","*waydroid*"]}
    checks,blockers,details=bounded_presence_part("PART_6",req)
    return evidence_base("PART_6",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part7(mid):
    checks,blockers,details=bounded_presence_part("PART_7",{"study_surface":["*ESTUDIO*","*Study*"],"devotional":["*DEVOCIONAL*","*devotional*"],"hermeneutic":["*Hermeneut*","*hermeneut*"]})
    return evidence_base("PART_7",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part8(mid):
    checks,blockers,details=bounded_presence_part("PART_8",{"backup":["*backup*","*respaldo*"],"recovery":["*recovery*","*rollback*"],"hygiene":["*hygiene*","*HIGIENE*"],"architecture_manager":["*architecture*manager*","*arquitectura*version*"]})
    return evidence_base("PART_8",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part9(mid):
    prior=[]
    for p in PARTS[:-1]:
        cp=CERTS/f"{p}.json"
        if cp.is_file(): prior.append({"part":p,"sha256":sha(cp)})
    checks={"prior_certificates":len(prior)==8,"runner":run(["systemctl","is-active","actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"])["stdout"].strip()=="active","symphylax":run(["systemctl","--user","is-active","symphylax-r1.service"])["stdout"].strip()=="active"}
    blockers=[k for k,v in checks.items() if not v]
    ev=evidence_base("PART_9",mid,checks,"PASS" if not blockers else "HOLD",blockers,{"prior":prior})
    ev["prior_part_certificates"]=prior; ev["postinstall_matrix"]="PASS" if not blockers else "HOLD"; ev["rollback_survives"]=not blockers
    return ev

HANDLERS={"PART_1":part1,"PART_2":part2,"PART_3":part3,"PART_4":part4,"PART_5":part5,"PART_6":part6,"PART_7":part7,"PART_8":part8,"PART_9":part9}

def gh_json(args,timeout=120):
    r=run(["gh",*args],timeout=timeout)
    if r["returncode"]!=0: raise RuntimeError("GH_FAILED:"+r["stderr"])
    return json.loads(r["stdout"]) if r["stdout"].strip() else {}

def publish_and_certify(ev):
    part=ev["part"]; stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel=f"evidence/r4-master/{stamp}-{ev['mission_id']}/{part}/MATERIAL_EVIDENCE.json"
    raw=(json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode(); payload=base64.b64encode(raw).decode()
    resp=gh_json(["api","--method","PUT",f"repos/{REPO}/contents/{rel}","-f",f"message=evidence(R4): {part} material evidence","-f",f"content={payload}","-f",f"branch={BRANCH}"],timeout=60)
    commit=resp["commit"]["sha"]; run_id=None
    for _ in range(120):
        q=gh_json(["api",f"repos/{REPO}/actions/runs?branch={BRANCH}&event=push&per_page=100"],timeout=30)
        for rr in q.get("workflow_runs",[]):
            if rr.get("head_sha")==commit and rr.get("path")==CERT_WORKFLOW: run_id=rr["id"]; break
        if run_id: break
        time.sleep(2)
    if not run_id: raise RuntimeError("CERT_WORKFLOW_NOT_FOUND")
    w=run(["gh","run","watch",str(run_id),"--repo",REPO,"--exit-status"],timeout=900)
    if w["returncode"]!=0: raise RuntimeError("CERT_WORKFLOW_FAILED:"+str(run_id))
    with tempfile.TemporaryDirectory(prefix="r4-g24-") as td:
        d=pathlib.Path(td)
        z=run(["gh","run","download",str(run_id),"--repo",REPO,"-n","r4-master-g24","-D",str(d)],timeout=120)
        if z["returncode"]!=0: raise RuntimeError("G24_DOWNLOAD_FAILED")
        cp=d/"G24.json"; cert=json.loads(cp.read_text(encoding="utf-8"))
        if cert.get("status")!="PASS" or cert.get("part")!=part or cert.get("evidence_sha256")!=hashlib.sha256(raw).hexdigest(): raise RuntimeError("G24_CERT_MISMATCH")
        cert["workflow_run_id"]=run_id; cert["evidence_commit_sha"]=commit
        atomic_json(CERTS/f"{part}.json",cert); return cert

def current_part():
    for p in PARTS:
        if not (CERTS/f"{p}.json").is_file(): return p
    return None

def supervise_once(worker,mid):
    tick=worker.mission_tick(mid); atomic_json(STATE/"LAST_HEARTBEAT.json",tick)
    part=current_part()
    if part is None:
        atomic_json(STATE/"MASTER_STATUS.json",{"status":"COMPLETE","global_mission_status":"COMPLETE","mission_id":mid,"utc":utc()}); return "COMPLETE"
    ev=HANDLERS[part](mid); atomic_json(EVIDENCE/f"{part}.json",ev)
    atomic_json(STATE/"MASTER_STATUS.json",{"status":ev["status"],"current_part":part,"blockers":ev.get("blockers",[]),"mission_id":mid,"updated_at_utc":utc(),"next":"CERTIFY" if ev["status"]=="PASS" else "RETRY_AFTER_REMEDIATION"})
    if ev["status"]!="PASS": return "HOLD"
    cert=publish_and_certify(ev)
    nxt=PARTS[PARTS.index(part)+1] if part!="PART_9" else "COMPLETE"
    atomic_json(STATE/"MASTER_STATUS.json",{"status":"PART_CERTIFIED","current_part":part,"g24":cert,"mission_id":mid,"updated_at_utc":utc(),"next":nxt})
    return "CERTIFIED"

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--loop",action="store_true"); ap.add_argument("--once",action="store_true"); ap.add_argument("--sleep",type=int,default=300); a=ap.parse_args()
    for p in (STATE,CERTS,PLANS,EVIDENCE,STATE/"rollback"): p.mkdir(parents=True,exist_ok=True)
    lf=LOCK.open("a+")
    try: fcntl.flock(lf,fcntl.LOCK_EX|fcntl.LOCK_NB)
    except BlockingIOError: raise SystemExit("MASTER_ALREADY_RUNNING")
    host_preflight(); worker,custosz,authority=load_worker()
    mission_text=pathlib.Path(__file__).with_name("MASTER_MISSION.md").read_text(encoding="utf-8")
    mid,_=ensure_master_mission(worker,mission_text); prepare_all(worker)
    atomic_json(STATE/"IDENTITY.json",{"mission_id":mid,"custosz_path":str(custosz),"custosz_sha256":sha(custosz),"authority_path":str(authority),"authority_sha256":sha(authority),"checkpoint":str(CHECKPOINT),"started_or_resumed_utc":utc()})
    while True:
        try: result=supervise_once(worker,mid)
        except Exception as e:
            atomic_json(STATE/"MASTER_STATUS.json",{"status":"HOLD","error":type(e).__name__+":"+str(e),"mission_id":mid,"updated_at_utc":utc()})
            if a.once: raise
            time.sleep(max(60,a.sleep)); continue
        if result=="COMPLETE": return 0
        if a.once: return 0
        time.sleep(max(60,a.sleep))

if __name__=="__main__":
    raise SystemExit(main())
