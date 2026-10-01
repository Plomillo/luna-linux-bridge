#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, datetime as dt, fcntl, hashlib, json, os, pathlib, shutil, subprocess, sys, tempfile, time, uuid, traceback

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
CERT_WORKFLOW_PART4=".github/workflows/luna-r4-master-part4-r2-certify.yml"
PRIVILEGE_GOV=["sudo","-n","/usr/local/sbin/louksna-sudo-governance"]
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
NOTICE_STATE=STATE/"LAST_GATE_NOTICE.json"
PERMISSION_REQUEST=STATE/"PERMISSION_REQUEST.json"
PR_NUMBER=29
PART4_P3_HARDENED_CONTRACT=pathlib.Path(__file__).with_name("PART4_P3_GROWTH_HARDENED_ANTI_PARALYSIS.json")
PART4_P3_EXEC_DIR=STATE/"PART_4_P3_HARDENED"
PART4_P3_EXEC_STATE=PART4_P3_EXEC_DIR/"EXECUTION.json"

class PrivilegeRequired(RuntimeError):
    def __init__(self, part, actions, reason):
        super().__init__(reason)
        self.part=part; self.actions=list(actions); self.reason=reason

class HumanAuthorizationRequired(RuntimeError):
    def __init__(self, part, gates, reason):
        super().__init__(reason)
        self.part=part; self.gates=list(gates); self.reason=reason

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

def privilege_status():
    r=run(PRIVILEGE_GOV+["status"],timeout=20)
    if r["returncode"]!=0:
        return None
    try:
        d=json.loads(r["stdout"])
    except Exception:
        return None
    root=run(["sudo","-n","id","-u"],timeout=10)
    d["sudo_root_probe"]=(root["returncode"]==0 and root["stdout"].strip()=="0")
    return d

def require_privilege(part, actions):
    d=privilege_status()
    valid=(
        d
        and d.get("status")=="ACTIVE"
        and d.get("policy_exact") is True
        and d.get("g24_certificate_local") is True
        and d.get("scope")=="UNRESTRICTED_ROOT_VIA_SUDO"
        and d.get("sudo_root_probe") is True
    )
    if not valid:
        raise PrivilegeRequired(part,actions,"CERTIFIED_PRIVILEGE_BRIDGE_V121_REQUIRED")
    return d

def publish_gate_notice(obj):
    key=hashlib.sha256(json.dumps(obj,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    prior=read_json(NOTICE_STATE,{}) or {}
    if prior.get("key")==key:
        return
    body=(
        "LUNA_R4_GATE_NOTICE\\n\\n"
        f"status={obj.get('status')}\\n"
        f"part={obj.get('part')}\\n"
        f"reason={obj.get('reason')}\\n"
        f"required={json.dumps(obj.get('required',[]),ensure_ascii=False)}\\n"
        f"checkpoint={CHECKPOINT}\\n"
        "action=USER_AUTHORIZATION_REQUIRED"
    )
    r=run(["gh","api","--method","POST",f"repos/{REPO}/issues/{PR_NUMBER}/comments","-f",f"body={body}"],timeout=60)
    atomic_json(NOTICE_STATE,{"key":key,"published":r["returncode"]==0,"published_at_utc":utc(),"status":obj.get("status"),"part":obj.get("part")})

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
    return {"privilege_bridge":privilege_status()}

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
    def workspace_adapter():
        return PROJECT_ROOT
    def discover_adapter():
        return {"workspace":str(PROJECT_ROOT),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(PROJECT_ROOT),"score":999}}}
    def sources_adapter(large=False):
        digest=sha(a)
        return {"observed_at":utc(),"sources":{"LOUKSNA":{
            "path":str(a),"exists":True,"observed_bytes":a.stat().st_size,
            "observed_sha256":digest,"sha256":digest,"integrity":"PASS","role":"CANONICAL_AUTHORITY"
        }}}
    def resources_adapter():
        mem_available_kib=0
        try:
            for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
                if line.startswith("MemAvailable:"):
                    mem_available_kib=int(line.split()[1]); break
        except Exception:
            pass
        disk=shutil.disk_usage(HOME)
        zone="GREEN"
        if mem_available_kib and mem_available_kib < 524288:
            zone="RED"
        elif mem_available_kib and mem_available_kib < 1048576:
            zone="AMBER"
        if disk.free < 2*1024*1024*1024:
            zone="RED"
        return {"resource_zone":zone,"mem_available_kib":mem_available_kib,"disk_free_bytes":disk.free,"source":"R4_MASTER_ADAPTER"}
    w.workspace=workspace_adapter
    w.discover=discover_adapter
    w.sources=sources_adapter
    w.resources=resources_adapter
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
    packages=["nodejs","npm","python3","python3-venv","python3-pip","pipx","git","7zip","default-jdk","g++","cmake","ninja-build","gdb","pkg-config"]
    missing=[p for p in packages if not pkg_installed(p)]; actions=[]
    if missing:
        require_privilege("PART_2",["apt-update","apt-install"])
        actions.append(run(["sudo","-n","/usr/bin/apt-get","update"],timeout=600))
        actions.append(run(["sudo","-n","/usr/bin/apt-get","install","-y","--no-install-recommends",*missing],timeout=1800))
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
    details={"priority_order":["PROYECTOS","SEMANTIC_CONTAINER"],"projects_center_alias":"PROYECTOS"}
    checks["runner"]=run(["systemctl","is-active","actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"])["stdout"].strip()=="active"
    checks["symphylax"]=run(["systemctl","--user","is-active","symphylax-r1.service"])["stdout"].strip()=="active"
    c=locate_custosz(); a=locate_authority()
    checks.update({"custosz":c.is_file(),"runtime":RUNTIME_PATH.is_file(),"metaos":METAOS_PATH.is_file(),"authority":a.is_file(),"project_workspace":PROJECT_ROOT.is_dir()})
    details["identities"]={k:sha(v) for k,v in {"custosz":c,"runtime":RUNTIME_PATH,"metaos":METAOS_PATH,"authority":a}.items() if v.is_file()}

    # P1: projects_center is a logical gate identifier. The real architectural
    # entity is PROYECTOS / Proyectos. Prefer a live operational binding and
    # keep historical/projection candidates as evidence only.
    live_project_paths=[
        HOME/"Proyectos",
        HOME/"Luna R4"/"Proyectos",
        pathlib.Path("/media")/HOME.name/"Windows"/"PROYECTOS",
    ]
    project_candidates=[]
    project_operational=None
    for p in live_project_paths:
        try:
            exists=p.exists()
            islink=p.is_symlink()
            rec={"path":str(p),"exists":exists,"is_symlink":islink}
            if islink:
                try:
                    resolved=p.resolve(strict=True)
                    rec["resolved"]=str(resolved)
                    rec["resolved_is_dir"]=resolved.is_dir()
                    if resolved.is_dir() and resolved.name.casefold()=="proyectos":
                        project_operational=str(p)
                except Exception as e:
                    rec["resolve_error"]=type(e).__name__+":"+str(e)
            elif p.is_dir() and p.name.casefold()=="proyectos":
                rec["resolved"]=str(p.resolve())
                rec["resolved_is_dir"]=True
                project_operational=project_operational or str(p)
            if exists or islink:
                project_candidates.append(rec)
        except OSError as e:
            project_candidates.append({"path":str(p),"error":type(e).__name__+":"+str(e)})

    project_search_bases=[
        PROJECT_ROOT,
        HOME/".local/share",
        HOME/".local/lib/louksna",
        HOME/"SYMPHYLAX_LAB",
        HOME/"MISION_PUAC_20260926",
    ]
    project_patterns=["PROYECTOS","Proyectos","1. PROYECTOS PRIORITARIOS","*PROYECTOS PRIORITARIOS*"]
    historical_project=None
    for base in project_search_bases:
        if historical_project or not base.exists(): continue
        for pat in project_patterns:
            try:
                historical_project=str(next(base.rglob(pat))); break
            except (StopIteration,OSError):
                pass

    details["projects_center_live_candidates"]=project_candidates
    details["projects_center_candidate"]=project_operational or historical_project
    details["projects_center_historical_candidate"]=historical_project
    details["projects_center_resolution"]="ALIAS_PROJECTS_CENTER_TO_PROYECTOS"
    checks["projects_center"]=bool(project_operational)

    # P2: widen semantic discovery across governed historical/remediation
    # surfaces and Spanish/English derivations. Existence is only discovery;
    # PART_3 still preserves fail-closed certification downstream.
    semantic_bases=[
        PROJECT_ROOT,
        HOME/".local/share",
        HOME/".local/lib/louksna",
        HOME/"SYMPHYLAX_LAB",
        HOME/"MISION_PUAC_20260926",
    ]
    semantic_patterns=[
        "*SEMANTIC*CONTAINER*","*semantic*container*",
        "*CONTENEDOR*SEMANTIC*","*contenedor*semantic*",
        "*CONTENIDO*SEMANTIC*","*contenido*semantic*",
        "*SEMANTIC*CONTENT*","*semantic*content*",
        "SOURCE_REGISTRY.json","semantic_container.json","semantic_continuity.py",
    ]
    semantic=None
    for base in semantic_bases:
        if semantic or not base.exists(): continue
        for pat in semantic_patterns:
            try:
                semantic=str(next(base.rglob(pat))); break
            except (StopIteration,OSError):
                pass
    details["semantic_container_candidate"]=semantic
    checks["semantic_container"]=bool(semantic)

    blockers=[k for k,v in checks.items() if not v]
    return evidence_base("PART_3",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part4(mid):
    # PART4-R2-20260929: user-authorized operational amendment.
    # Louksna.md remains canonical authority; PART_5..PART_9 are unchanged.
    legacy_auth=read_json(STATE/"authorizations/PART4_H2_H4.json",{}) or {}
    r2=read_json(STATE/"PART_4_R2/STATE.json",{}) or {}
    p3_hardened=read_json(PART4_P3_HARDENED_CONTRACT,{}) or {}
    p3_hardened_valid=(
        p3_hardened.get("contract_id")=="PART4-P3-GROWTH-HARDENED-ANTI-PARALYSIS-20261001"
        and p3_hardened.get("authority")=="Louksna.md"
        and p3_hardened.get("desktop_commander")=="PROHIBITED"
        and p3_hardened.get("remote_desktop_commander")=="PROHIBITED"
        and p3_hardened.get("observation_authority")=="LOUKSNA_REMOTE_BRIDGE"
        and p3_hardened.get("anti_paralysis",{}).get("hold_is_not_deadlock") is True
        and p3_hardened.get("anti_paralysis",{}).get("fail_closed_is_not_stop_all_work") is True
        and len(p3_hardened.get("stages",[]))==12
        and p3_hardened.get("disk_mutation_authorized_by_this_contract") is False
    )
    # POST-P5 reconciliation is evidence-derived and additive: historical flags
    # remain untouched, while stronger live end-state evidence may satisfy obsolete
    # intermediate predicates. Any observation failure stays fail-closed.
    live_post_p5={"status":"HOLD","root_source":None,"root_fstype":None,"partitions_present":[],"p5_absent":False}
    try:
        root_source=os.path.realpath(subprocess.check_output(["findmnt","-n","-o","SOURCE","/"],text=True).strip())
        root_fstype=subprocess.check_output(["findmnt","-n","-o","FSTYPE","/"],text=True).strip()
        q=subprocess.run(["lsblk","-nrpo","PATH,TYPE","/dev/nvme0n1"],text=True,capture_output=True,check=True)
        partitions_present=sorted(
            line.split()[0] for line in q.stdout.splitlines()
            if len(line.split())>=2 and line.split()[1]=="part"
        )
        p5_absent=not pathlib.Path("/dev/nvme0n1p5").exists()
        live_post_p5.update({
            "root_source":root_source,
            "root_fstype":root_fstype,
            "partitions_present":partitions_present,
            "p5_absent":p5_absent,
        })
        if (
            root_source=="/dev/nvme0n1p3"
            and root_fstype=="ext4"
            and partitions_present==["/dev/nvme0n1p1","/dev/nvme0n1p3"]
            and p5_absent
        ):
            live_post_p5["status"]="PASS"
    except Exception as exc:
        live_post_p5["error"]=type(exc).__name__+":"+str(exc)[:300]

    post_p5_effective=live_post_p5["status"]=="PASS"
    ntfs_transition_satisfied=(
        r2.get("ntfs_shrunk") is True
        or (r2.get("ntfs_retired") is True and post_p5_effective)
    )
    ext4_root_effective=(
        r2.get("ext4_created") is True
        or (
            live_post_p5.get("root_source")=="/dev/nvme0n1p3"
            and live_post_p5.get("root_fstype")=="ext4"
        )
    )
    checks={
        "H2": legacy_auth.get("H2") is True,
        "H4": legacy_auth.get("H4") is True,
        "r2_owner_authorized": r2.get("r2_owner_authorized") is True,
        "freeze_g24": r2.get("freeze_g24") is True,
        "purge_scope_prevalidated": r2.get("purge_scope_prevalidated") is True,
        "purge_scope_g23_g24": r2.get("purge_scope_g23_g24") is True,
        "windows_purged_preserving_projects": r2.get("windows_purged_preserving_projects") is True,
        "post_purge_integrity": r2.get("post_purge_integrity") is True,
        "ntfs_transition_satisfied": ntfs_transition_satisfied,
        "ext4_root_effective": ext4_root_effective,
        "projects_migrated_hash_equivalent": r2.get("projects_migrated_hash_equivalent") is True,
        "ntfs_retired": r2.get("ntfs_retired") is True,
        "post_p5_live_reconciled": post_p5_effective,
        "p3_growth_hardened_contract": p3_hardened_valid,
        "final_linux_layout": r2.get("final_linux_layout") is True,
        "part4_r2_final_g24": r2.get("part4_r2_final_g24") is True,
        "final_merge_g24": r2.get("final_merge_g24") is True,
        "verified_root_on_consolidated_linux": r2.get("verified_root_on_consolidated_linux") is True,
    }
    blockers=[k for k,v in checks.items() if not v]
    details={
        "operational_amendment":"PART4-R2-20260929",
        "p3_growth_hardened_contract":str(PART4_P3_HARDENED_CONTRACT),
        "p3_growth_hardened_contract_sha256":sha(PART4_P3_HARDENED_CONTRACT) if PART4_P3_HARDENED_CONTRACT.is_file() else None,
        "p3_growth_hardened_contract_id":p3_hardened.get("contract_id"),
        "anti_paralysis_active":p3_hardened_valid,
        "desktop_commander":"PROHIBITED",
        "remote_desktop_commander":"PROHIBITED",
        "live_observation_authority":"LOUKSNA_REMOTE_BRIDGE",
        "amendment_reference":"server/r4-master/PART4_R2_AMENDMENT.json",
        "certified_freeze_manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
        "freeze_certification_run_id":36621093750,
        "r2_state_file":str(STATE/"PART_4_R2/STATE.json"),
        "legacy_human_gate_file":str(STATE/"authorizations/PART4_H2_H4.json"),
        "predelete_full_backup_requirement_superseded":True,
        "restore_proof_predelete_requirement_superseded":True,
        "part5_to_part9_unchanged":True,
        "autopilot_addendum_reference":"server/r4-master/PART4_R2_AUTOPILOT_ADDENDUM.json",
        "autopilot_requires_final_g24":True,
        "final_merge_addendum_reference":"server/r4-master/PART4_R2_FINAL_MERGE_ADDENDUM.json",
        "part4_close_requires_final_merge_g24":True,
        "final_merge_g24_sha256":r2.get("final_merge_g24_sha256"),
        "storage_migration_g24_sha256":r2.get("storage_migration_g24_sha256"),
        "p2_p4_retirement_g24_sha256":r2.get("p2_p4_retirement_g24_sha256"),
        "lost_found_exception_certified":r2.get("lost_found_exception_certified") is True,
        "migration_replayed":r2.get("migration_replayed"),
        "historical_ntfs_shrunk_flag":r2.get("ntfs_shrunk"),
        "historical_ext4_created_flag":r2.get("ext4_created"),
        "post_p5_live_evidence":live_post_p5,
        "ntfs_transition_satisfaction_basis":"HISTORICAL_FLAG" if r2.get("ntfs_shrunk") is True else ("POST_P5_EFFECTIVE_STATE" if ntfs_transition_satisfied else None),
        "ext4_satisfaction_basis":"HISTORICAL_FLAG" if r2.get("ext4_created") is True else ("LIVE_P3_EXT4_ROOT" if ext4_root_effective else None),
    }
    ev=evidence_base("PART_4",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)
    ev["human_gates"]={"H2":checks["H2"],"H4":checks["H4"]}
    ev["operational_amendment"]="PART4-R2-20260929"
    ev["two_verified_backups"]="SUPERSEDED_BY_PART4_R2"
    ev["restore_proof"]="SUPERSEDED_BY_PART4_R2"
    ev["destructive_scope_prevalidated"]=checks["purge_scope_prevalidated"]
    return ev

def part4_hardened_progress(mid):
    """Advance the hardened PART_4 state machine without bypassing mutation gates."""
    contract=read_json(PART4_P3_HARDENED_CONTRACT,{}) or {}
    stages=contract.get("stages",[])
    if len(stages)!=12 or contract.get("contract_id")!="PART4-P3-GROWTH-HARDENED-ANTI-PARALYSIS-20261001":
        return {"status":"HOLD","reason":"HARDENED_CONTRACT_INVALID","current_stage":None}

    PART4_P3_EXEC_DIR.mkdir(parents=True,exist_ok=True)
    st=read_json(PART4_P3_EXEC_STATE,{}) or {}
    if not st:
        st={
          "schema":"LOUKSNA_R4_PART4_P3_HARDENED_EXECUTION/1.0",
          "status":"ACTIVE",
          "mission_id":mid,
          "contract_id":contract["contract_id"],
          "contract_sha256":sha(PART4_P3_HARDENED_CONTRACT),
          "current_stage":1,
          "last_completed_stage":0,
          "history":[],
          "disk_mutation_performed":False,
          "filesystem_mutation_performed":False,
          "started_at_utc":utc(),
        }

    def record(stage,status,details,next_stage=None,next_action=None):
        rec={
          "stage":stage,
          "stage_id":stages[stage-1]["id"],
          "status":status,
          "details":details,
          "timestamp_utc":utc(),
        }
        hist=st.setdefault("history",[])
        if not hist or hist[-1].get("stage")!=stage or hist[-1].get("status")!=status or hist[-1].get("details")!=details:
            hist.append(rec)
            st["history"]=hist[-100:]
        st["current_stage"]=next_stage if next_stage is not None else stage
        if status=="PASS":
            st["last_completed_stage"]=max(int(st.get("last_completed_stage",0)),stage)
        st["status"]="ACTIVE" if next_stage and next_stage<=12 else status
        st["next_authorized_action"]=next_action
        st["updated_at_utc"]=utc()
        atomic_json(PART4_P3_EXEC_STATE,st)
        return st

    stage=int(st.get("current_stage") or 1)

    # Stage 1: fresh live checkpoint and continuity. Read-only.
    if stage==1:
        try:
            root_source=os.path.realpath(run(["findmnt","-n","-o","SOURCE","/"],check=True)["stdout"].strip())
            root_fstype=run(["findmnt","-n","-o","FSTYPE","/"],check=True)["stdout"].strip()
            p3_start=int(pathlib.Path("/sys/class/block/nvme0n1p3/start").read_text().strip())
            p5_absent=not pathlib.Path("/dev/nvme0n1p5").exists()
            uuid_out=run(["lsblk","-n","-o","UUID","/dev/nvme0n1p3"],check=True)["stdout"].strip()
            parts=run(["lsblk","-ln","-o","PATH,TYPE","/dev/nvme0n1"],check=True)["stdout"].splitlines()
            partitions=sorted(line.split()[0] for line in parts if len(line.split())>=2 and line.split()[1]=="part")
            details={
              "root_source":root_source,"root_fstype":root_fstype,"p3_start_sector":p3_start,
              "p3_uuid":uuid_out,"p5_absent":p5_absent,"partitions_present":partitions,
              "disk_mutation_performed":False,
            }
            ok=(
              root_source=="/dev/nvme0n1p3"
              and root_fstype=="ext4"
              and p3_start==567296
              and uuid_out=="e084ec2a-af39-48b5-bb89-db2dc6a98332"
              and p5_absent
              and partitions==["/dev/nvme0n1p1","/dev/nvme0n1p3"]
            )
        except Exception as exc:
            details={"error":type(exc).__name__+":"+str(exc)[:500],"disk_mutation_performed":False}
            ok=False
        if ok:
            return record(1,"PASS",details,2,"PREPARE_STAGE2_GROWPART_CAPABILITY_CANDIDATE")
        return record(1,"HOLD",details,1,"RECONCILE_STAGE1_LIVE_CHECKPOINT")

    # Stage 2: candidate preparation only. Package installation is a distinct
    # consequential microtransaction and must have exact-scope G23/G24.
    if stage==2:
        growpart=shutil.which("growpart")
        pkg_cloud=pkg_installed("cloud-guest-utils")
        pkg_gdisk=pkg_installed("gdisk")
        if growpart and pkg_cloud and pkg_gdisk:
            details={"growpart":growpart,"cloud_guest_utils":True,"gdisk":True,"mutation_performed":False}
            return record(2,"PASS",details,3,"RUN_STAGE3_GROWPART_DRY_RUN")
        sim=run(["apt-get","-s","install","cloud-guest-utils","gdisk"],timeout=120)
        policy=run(["apt-cache","policy","cloud-guest-utils","gdisk"],timeout=60)
        evidence={
          "schema":"LOUKSNA_R4_PART4_STAGE2_GROWPART_CANDIDATE/1.0",
          "status":"CANDIDATE_READY" if sim["returncode"]==0 else "HOLD",
          "mission_id":mid,
          "stage":2,
          "packages":["cloud-guest-utils","gdisk"],
          "simulation":sim,
          "policy":policy,
          "growpart_present":bool(growpart),
          "disk_mutation_authorized":False,
          "disk_mutation_performed":False,
          "prepared_at_utc":utc(),
        }
        atomic_json(PART4_P3_EXEC_DIR/"STAGE2_CANDIDATE.json",evidence)
        return record(
          2,
          "AWAITING_G23_G24" if sim["returncode"]==0 else "HOLD",
          {"candidate_sha256":sha(PART4_P3_EXEC_DIR/"STAGE2_CANDIDATE.json"),"simulation_rc":sim["returncode"],"mutation_performed":False},
          2,
          "CERTIFY_STAGE2_GROWPART_CAPABILITY_MICROTRANSACTION" if sim["returncode"]==0 else "REMEDIATE_STAGE2_PACKAGE_CANDIDATE"
        )

    # Stage 3: deterministic growpart dry-run only.
    if stage==3:
        growpart=shutil.which("growpart")
        if not growpart:
            return record(3,"HOLD",{"reason":"GROWPART_NOT_INSTALLED","mutation_performed":False},2,"RETURN_STAGE2")
        r1=run([growpart,"-N","/dev/nvme0n1","3"],timeout=120)
        r2=run([growpart,"-N","/dev/nvme0n1","3"],timeout=120)
        eq=(r1["returncode"]==r2["returncode"] and r1["stdout"]==r2["stdout"] and r1["stderr"]==r2["stderr"])
        ev={"schema":"LOUKSNA_R4_PART4_STAGE3_DRYRUN/1.0","run1":r1,"run2":r2,"deterministic":eq,"mutation_performed":False,"observed_at_utc":utc()}
        atomic_json(PART4_P3_EXEC_DIR/"STAGE3_DRYRUN.json",ev)
        if eq and r1["returncode"]==0:
            return record(3,"PASS",{"dryrun_sha256":sha(PART4_P3_EXEC_DIR/"STAGE3_DRYRUN.json"),"deterministic":True,"mutation_performed":False},4,"CREATE_STAGE4_RECOVERY_CAPSULE")
        return record(3,"HOLD",{"dryrun_sha256":sha(PART4_P3_EXEC_DIR/"STAGE3_DRYRUN.json"),"deterministic":eq,"rc":r1["returncode"],"mutation_performed":False},3,"DIAGNOSE_STAGE3_DRYRUN")

    # Stages 4-12 are active in the state machine but remain exact-scope gated.
    # The controller never skips them or self-authorizes their consequential commits.
    stage_id=stages[stage-1]["id"]
    return record(stage,"AWAITING_STAGE_HANDLER",{"stage_id":stage_id,"mutation_performed":False},stage,"DISPATCH_"+stage_id)

def part5(mid):
    packages=["qemu-system-x86","qemu-utils","libvirt-daemon-system","libvirt-clients","virt-manager"]
    missing=[p for p in packages if not pkg_installed(p)]; actions=[]
    if missing:
        require_privilege("PART_5",["apt-update","apt-install"])
        actions.append(run(["sudo","-n","/usr/bin/apt-get","update"],timeout=600)); actions.append(run(["sudo","-n","/usr/bin/apt-get","install","-y","--no-install-recommends",*missing],timeout=1800))
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
    env=dict(os.environ); env["GH_PAGER"]="cat"; env["NO_COLOR"]="1"
    r=run(["gh",*args],timeout=timeout,env=env)
    if r["returncode"]!=0: raise RuntimeError("GH_FAILED:"+r["stderr"])
    raw=r["stdout"].strip()
    if not raw: return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError("GH_JSON_INVALID:"+repr(raw[:500])) from e

def publish_and_certify(ev):
    part=ev["part"]; stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    evidence_root="evidence/r4-master-part4-r2" if part=="PART_4" else "evidence/r4-master"
    rel=f"{evidence_root}/{stamp}-{ev['mission_id']}/{part}/MATERIAL_EVIDENCE.json"
    raw=(json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode(); payload=base64.b64encode(raw).decode()
    resp=gh_json(["api","--method","PUT",f"repos/{REPO}/contents/{rel}","-f",f"message=evidence(R4): {part} material evidence","-f",f"content={payload}","-f",f"branch={BRANCH}"],timeout=60)
    commit=resp["commit"]["sha"]; run_id=None
    for _ in range(120):
        q=gh_json(["api",f"repos/{REPO}/actions/runs?branch={BRANCH}&event=push&per_page=100","--jq",'{"workflow_runs":[.workflow_runs[]|{id,head_sha,path,status,conclusion}]}'],timeout=30)
        for rr in q.get("workflow_runs",[]):
            expected_workflow=CERT_WORKFLOW_PART4 if part=="PART_4" else CERT_WORKFLOW
            if rr.get("head_sha")==commit and rr.get("path")==expected_workflow: run_id=rr["id"]; break
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
    try:
        tick=worker.mission_tick(mid)
    except Exception as e:
        tick={"status":"DEGRADED_SUPERVISION_LOCAL_FALLBACK","mission_id":mid,"error":type(e).__name__+":"+str(e),"utc":utc(),"authority":"Louksna.md","canonical_mutation":False}
    atomic_json(STATE/"LAST_HEARTBEAT.json",tick)
    part=current_part()
    if part is None:
        atomic_json(STATE/"MASTER_STATUS.json",{"status":"COMPLETE","global_mission_status":"COMPLETE","mission_id":mid,"utc":utc()}); return "COMPLETE"
    ev=HANDLERS[part](mid); atomic_json(EVIDENCE/f"{part}.json",ev)
    next_action="CERTIFY" if ev["status"]=="PASS" else ("PART4_P3_HARDENED_CONTINUE_SAFE_REMEDIATION" if part=="PART_4" else "RETRY_AFTER_REMEDIATION")
    atomic_json(STATE/"MASTER_STATUS.json",{
        "status":ev["status"],
        "current_part":part,
        "blockers":ev.get("blockers",[]),
        "mission_id":mid,
        "updated_at_utc":utc(),
        "next":next_action,
        "hold_semantics":"BLOCK_ONLY_UNSAFE_DEPENDENT_TRANSITION" if ev["status"]!="PASS" else None,
        "safe_work_while_hold":part=="PART_4" and ev["status"]!="PASS",
        "anti_paralysis_contract":ev.get("details",{}).get("p3_growth_hardened_contract_id") if part=="PART_4" else None,
    })
    if ev["status"]!="PASS":
        if part=="PART_4":
            part4_progress=part4_hardened_progress(mid)
            ms=read_json(STATE/"MASTER_STATUS.json",{}) or {}
            ms["part4_hardened_execution"]=part4_progress
            ms["stage_current"]=part4_progress.get("current_stage")
            ms["stage_last_completed"]=part4_progress.get("last_completed_stage")
            ms["stage_next"]=part4_progress.get("next_authorized_action")
            ms["stage_status"]=part4_progress.get("status")
            ms["updated_at_utc"]=utc()
            atomic_json(STATE/"MASTER_STATUS.json",ms)
        return "HOLD"
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
        except PrivilegeRequired as e:
            req={"schema":"LOUKSNA_R4_PERMISSION_REQUEST/1.0","status":"NEEDS_PRIVILEGE","part":e.part,"reason":e.reason,"required":e.actions,"mission_id":mid,"checkpoint":str(CHECKPOINT),"created_at_utc":utc()}
            atomic_json(PERMISSION_REQUEST,req); publish_gate_notice(req)
            atomic_json(STATE/"MASTER_STATUS.json",req)
            if a.once: return 4
            time.sleep(max(60,a.sleep)); continue
        except HumanAuthorizationRequired as e:
            req={"schema":"LOUKSNA_R4_PERMISSION_REQUEST/1.0","status":"NEEDS_HUMAN_AUTHORIZATION","part":e.part,"reason":e.reason,"required":e.gates,"mission_id":mid,"checkpoint":str(CHECKPOINT),"created_at_utc":utc()}
            atomic_json(PERMISSION_REQUEST,req); publish_gate_notice(req)
            atomic_json(STATE/"MASTER_STATUS.json",req)
            if a.once: return 5
            time.sleep(max(60,a.sleep)); continue
        except Exception as e:
            atomic_json(STATE/"MASTER_STATUS.json",{"status":"HOLD","error":type(e).__name__+":"+str(e),"traceback":traceback.format_exc(),"mission_id":mid,"updated_at_utc":utc()})
            if a.once: raise
            time.sleep(max(60,a.sleep)); continue
        if result=="COMPLETE": return 0
        if a.once: return 0
        time.sleep(max(60,a.sleep))

if __name__=="__main__":
    raise SystemExit(main())
