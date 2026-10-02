#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, datetime as dt, fcntl, hashlib, json, os, pathlib, re, shutil, subprocess, sys, tempfile, time, uuid, traceback, urllib.parse, xml.etree.ElementTree as ET

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
PART4_P3_TEN_POINT_DIRECTIVE=pathlib.Path(__file__).with_name("PART4_P3_TEN_POINT_HARDENED_CONTINUATION.json")
PART4_P3_EXEC_DIR=STATE/"PART_4_P3_HARDENED"
PART4_P3_EXEC_STATE=PART4_P3_EXEC_DIR/"EXECUTION.json"
R48_CONTRACT=pathlib.Path(__file__).with_name("R4_48H_CONTRACT.json")
R48_STATE=HOME/".local/state/louksna/r4-48h"
R48_EVID=R48_STATE/"evidence"
R48_POINT_REQUEST=R48_STATE/"MAESTRO_POINT_REQUEST.json"
R48_POINT_RESULT=R48_STATE/"MAESTRO_POINT_RESULT.json"
PROYECTOS=HOME/"PROYECTOS"

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

def r48_contract():
    d=read_json(R48_CONTRACT,{}) or {}
    if d.get("schema")!="LOUKSNA_R4_REMAINDER_48H_CONTRACT/2.0":
        raise RuntimeError("R4_48H_CONTRACT_INVALID")
    return d

def r48_deadline():
    c=r48_contract()
    return dt.datetime.fromisoformat(c["window"]["deadline_utc"].replace("Z","+00:00"))

def r48_expired():
    return dt.datetime.now(dt.timezone.utc) >= r48_deadline()

def r48_aux(name,schema):
    p=R48_EVID/name
    if not p.is_file(): return None,{"present":False,"path":str(p)}
    d=read_json(p,{}) or {}
    meta={"present":True,"path":str(p),"sha256":sha(p),"schema":d.get("schema"),"status":d.get("status")}
    if d.get("schema")!=schema: return None,{**meta,"error":"SCHEMA_MISMATCH"}
    return d,meta

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

def remaining_global_hours():
    remaining=(r48_deadline()-dt.datetime.now(dt.timezone.utc)).total_seconds()/3600.0
    return max(0.0,remaining)

def ensure_master_mission(worker,mission_text):
    """
    Preserve one global user mission window while binding CUSTOSZ to bounded,
    renewable runtime leases. Lease renewal never resets checkpoint, evidence,
    provenance, or global mission identity.
    """
    f=STATE/"MASTER_CUSTOSZ_MISSION.json"
    prior=read_json(f,{}) or {}
    if prior.get("mission_id"):
        try:
            m=worker.load_mission(prior["mission_id"])
            if m.get("state")=="SUPERVISORY_ACTIVE":
                return prior["mission_id"],m
        except Exception:
            pass

    remaining=remaining_global_hours()
    if remaining<=0:
        raise RuntimeError("R4_GLOBAL_WINDOW_EXPIRED")

    c=r48_contract()
    configured=int(c.get("window",{}).get("default_max_internal_lease_hours",24) or 24)
    lease=max(1,min(24,configured,int(remaining+0.999999)))
    goal=mission_text[:30000]
    m=worker.mission_start(lease,"LUNA_PROJECT",goal,report_minutes=5)

    lineage=list(prior.get("lease_lineage",[])) if isinstance(prior,dict) else []
    if prior.get("mission_id"):
        lineage.append({
            "mission_id":prior.get("mission_id"),
            "lease_hours":prior.get("lease_hours"),
            "closed_or_replaced_at_utc":utc()
        })

    atomic_json(f,{
        "schema":"LOUKSNA_R4_GLOBAL_MISSION_LEASE/2.0",
        "global_window_hours":48,
        "mission_id":m["mission_id"],
        "created_or_renewed_at_utc":utc(),
        "lease_hours":lease,
        "deadline_utc":c["window"]["deadline_utc"],
        "parent_mission_id":prior.get("mission_id"),
        "lease_lineage":lineage[-20:],
        "goal_sha256":hashlib.sha256(goal.encode()).hexdigest(),
        "checkpoint_preserved":True,
        "evidence_chain_preserved":True
    })
    return m["mission_id"],m

def _r48_checkpoint_user_paths(paths,tag):
    root=R48_STATE/"rollback"/(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+tag)
    root.mkdir(parents=True,exist_ok=False)
    rows=[]
    for p in map(pathlib.Path,paths):
        row={"path":str(p),"exists":p.exists() or p.is_symlink(),"is_symlink":p.is_symlink()}
        if p.is_symlink():
            row["symlink_target"]=os.readlink(p)
        elif p.is_file():
            dst=root/(hashlib.sha256(str(p).encode()).hexdigest()[:16]+"-"+p.name)
            shutil.copy2(p,dst)
            row.update({"backup":str(dst),"sha256":sha(p),"backup_sha256":sha(dst)})
        rows.append(row)
    atomic_json(root/"MANIFEST.json",{
        "schema":"LOUKSNA_R4_MAESTRO_CHECKPOINT/1.0",
        "tag":tag,"files":rows,"created_at_utc":utc()
    })
    return root,rows

def maestro_projects_repair(mid,request):
    if not PROYECTOS.is_dir() or PROYECTOS.is_symlink():
        raise RuntimeError("CANONICAL_PROJECTS_ROOT_INVALID")

    aliases=[HOME/"Proyectos",HOME/"Luna R4"/"Proyectos"]
    xbel=HOME/".local/share/user-places.xbel"
    launchers=[
        HOME/".local/share/applications/luna-r4-part1-proyectos.desktop",
        HOME/".local/share/applications/luna-r4-v7-proyectos.desktop",
    ]
    checkpoint,manifest=_r48_checkpoint_user_paths([*aliases,xbel,*launchers],"P06_PROJECTS")
    actions=[]

    for a in aliases:
        if a.exists() and not a.is_symlink():
            raise RuntimeError("PROJECTS_ALIAS_COLLISION_NON_SYMLINK:"+str(a))
        if a.is_symlink():
            try:
                if a.resolve(strict=True)==PROYECTOS.resolve():
                    actions.append({"path":str(a),"action":"REUSE_CORRECT"})
                    continue
            except Exception:
                pass
        a.parent.mkdir(parents=True,exist_ok=True)
        tmp=a.with_name(a.name+".louksna-maestro-tmp")
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass
        os.symlink(str(PROYECTOS),tmp)
        os.replace(tmp,a)
        actions.append({"path":str(a),"action":"REPOINT","target":str(PROYECTOS)})

    xbel_action="ABSENT"
    if xbel.is_file():
        tree=ET.parse(xbel)
        root=tree.getroot()
        target_uri="file://"+urllib.parse.quote(str(PROYECTOS))
        changed=0
        for bm in root.iter():
            if not bm.tag.endswith("bookmark"):
                continue
            title=""
            for ch in bm:
                if ch.tag.endswith("title"):
                    title=ch.text or ""
            href=bm.attrib.get("href","")
            if title.casefold()=="proyectos" or "proyectos" in urllib.parse.unquote(href).casefold():
                if href!=target_uri:
                    bm.set("href",target_uri)
                    changed+=1
        if changed:
            tmp=xbel.with_suffix(".xbel.louksna-maestro-tmp")
            tree.write(tmp,encoding="utf-8",xml_declaration=True)
            ET.parse(tmp)
            os.replace(tmp,xbel)
            xbel_action=f"UPDATED_{changed}"
        else:
            xbel_action="REUSE"

    launcher_audit=[]
    for p in launchers:
        if not p.is_file():
            continue
        text=p.read_text(encoding="utf-8",errors="replace")
        execs=[line for line in text.splitlines() if line.startswith("Exec=")]
        launcher_audit.append({
            "path":str(p),
            "sha256":sha(p),
            "exec":execs,
            "old_media_projects_reference":any("/media/" in x and "PROYECTOS" in x for x in execs)
        })

    bookmark_ok=False
    if xbel.is_file():
        verify=ET.parse(xbel).getroot()
        target_uri="file://"+urllib.parse.quote(str(PROYECTOS))
        for bm in verify.iter():
            if not bm.tag.endswith("bookmark"):
                continue
            title=""
            for ch in bm:
                if ch.tag.endswith("title"):
                    title=ch.text or ""
            if title.casefold()=="proyectos" and bm.attrib.get("href")==target_uri:
                bookmark_ok=True
                break

    checks={
        "canonical_root":PROYECTOS.is_dir() and not PROYECTOS.is_symlink(),
        "aliases":all(a.is_symlink() and a.resolve(strict=True)==PROYECTOS.resolve() for a in aliases),
        "xbel_parse":xbel.is_file() and ET.parse(xbel) is not None,
        "projects_bookmark_canonical":bookmark_ok,
        "launchers_no_direct_old_media":all(not x["old_media_projects_reference"] for x in launcher_audit),
        "partitioning_performed":False,
        "data_copy_performed":False,
        "network_download_performed":False
    }

    return {
        "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0",
        "request_id":request["request_id"],
        "point_id":"P06",
        "status":"PASS" if all(checks.values()) else "HOLD",
        "mission_id":mid,
        "executor":"MAESTRO",
        "custosz_bound":True,
        "checkpoint":str(checkpoint),
        "checkpoint_manifest":manifest,
        "actions":actions,
        "xbel_action":xbel_action,
        "launcher_audit":launcher_audit,
        "checks":checks,
        "blockers":[k for k,v in checks.items() if not v],
        "completed_at_utc":utc()
    }

def _p11_heavy_part6_active():
    p=run(["ps","-eo","args"],timeout=20)
    text=p.get("stdout","")
    return ("part6_hardened_worker.py" in text or "part789_hardened_worker.py" in text or "llama-cli" in text or "make build_name=louksna-proton" in text)

def _p11_cpu_flags():
    flags=set()
    try:
        for line in pathlib.Path("/proc/cpuinfo").read_text(encoding="utf-8",errors="replace").splitlines():
            if line.startswith("flags"):
                flags.update(line.split(":",1)[1].strip().split())
                break
    except Exception:
        pass
    required={"avx","avx2","bmi1","bmi2","f16c","fma","movbe","xsave"}
    # Linux normally exposes LZCNT as abm.
    lzcnt=("abm" in flags or "lzcnt" in flags)
    return {"required":sorted(required|{"lzcnt"}),"present":sorted(flags),
            "x86_64_v3":required.issubset(flags) and lzcnt,
            "missing":sorted(required-flags)+([] if lzcnt else ["lzcnt/abm"])}

def _p11_mem_total_bytes():
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemTotal:"):
                return int(line.split()[1])*1024
    except Exception:
        pass
    return 0

def _p11_find_correct_windows(expected_sha):
    roots=[
        PROYECTOS/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS",
        HOME/"Descargas",
        HOME/"Downloads",
        HOME/".local/share/louksna/r4-p11",
    ]
    names=[
        "26100.1.240331-1435.ge_release_CLIENT_IOT_LTSC_EVAL_x64FRE_en-us.iso",
        "Windows11_IoT_Enterprise_LTSC_2024_Eval_x64.iso",
    ]
    rows=[]
    for root in roots:
        if not root.exists():
            continue
        for name in names:
            p=root/name
            if not p.is_file():
                continue
            h=sha(p)
            rows.append({"path":str(p),"bytes":p.stat().st_size,"sha256":h})
            if h==expected_sha:
                return p,rows
    return None,rows

def _p11_windows(mid):
    expected_sha="8abf91c9cd408368dc73aab3425d5e3c02dae74900742072eb5c750fc637c195"
    expected_size=4428627968
    source_url=("https://software-static.download.prss.microsoft.com/dbazure/"
                "888969d5-f34g-4e03-ac9d-1f9786c66749/"
                "26100.1.240331-1435.ge_release_CLIENT_IOT_LTSC_EVAL_x64FRE_en-us.iso")
    bad_path=PROYECTOS/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/Windows11_IoT_Enterprise_LTSC_2024_Eval_x64.iso.reacquire.part"
    bad_expected="2cee70bd183df42b92a2e0da08cc2bb7a2a9ce3a3841955a012c0f77aeb3cb29"
    target_dir=PROYECTOS/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS"
    target=target_dir/"26100.1.240331-1435.ge_release_CLIENT_IOT_LTSC_EVAL_x64FRE_en-us.iso"
    part=target.with_suffix(target.suffix+".louksna.part")
    receipt=part.with_suffix(part.suffix+".source.json")

    existing,scan=_p11_find_correct_windows(expected_sha)
    bad=None
    if bad_path.is_file():
        bad={"path":str(bad_path),"bytes":bad_path.stat().st_size,"sha256":sha(bad_path)}
        bad["known_refresh_hash"]=bad["sha256"]==bad_expected
        bad["matches_required_hash"]=bad["sha256"]==expected_sha

    actions=[]
    if existing is None:
        target_dir.mkdir(parents=True,exist_ok=True)
        if part.exists():
            src=read_json(receipt,{}) or {}
            if src.get("url")!=source_url or src.get("expected_sha256")!=expected_sha:
                raise RuntimeError("P11_WINDOWS_PARTIAL_PROVENANCE_MISMATCH")
        else:
            atomic_json(receipt,{
                "schema":"LOUKSNA_R4_P11_WINDOWS_SOURCE/1.0",
                "url":source_url,
                "source_owner":"MICROSOFT",
                "source_domain":"software-static.download.prss.microsoft.com",
                "target_build":"26100.1",
                "expected_bytes":expected_size,
                "expected_sha256":expected_sha,
                "official_hash_document":"Windows11IoTEnterpriseLTSC2024EvalHashValues.pdf",
                "created_at_utc":utc()
            })

        free=shutil.disk_usage(target_dir).free
        if free < expected_size + 2*1024*1024*1024:
            raise RuntimeError("P11_WINDOWS_INSUFFICIENT_FREE_SPACE:"+str(free))

        curl=shutil.which("curl")
        if not curl:
            raise RuntimeError("P11_WINDOWS_CURL_MISSING")
        dl=run([
            curl,"--location","--fail","--show-error","--silent",
            "--retry","5","--retry-delay","5","--retry-all-errors",
            "--connect-timeout","30","--continue-at","-",
            "--output",str(part),source_url
        ],timeout=21600)
        actions.append({"operation":"MICROSOFT_OFFICIAL_CDN_DOWNLOAD","result":dl,"resumable":True})
        if dl["returncode"]!=0:
            return {"status":"HOLD","reason":"WINDOWS_DOWNLOAD_INCOMPLETE","source_url":source_url,
                    "partial_path":str(part),"partial_bytes":part.stat().st_size if part.exists() else 0,
                    "existing_scan":scan,"known_bad_refresh":bad,"actions":actions}
        actual_size=part.stat().st_size
        actual_sha=sha(part)
        if actual_size!=expected_size or actual_sha!=expected_sha:
            quarantine=part.with_name(part.name+".quarantine-"+actual_sha[:16])
            os.replace(part,quarantine)
            return {"status":"HOLD","reason":"WINDOWS_IDENTITY_MISMATCH","source_url":source_url,
                    "expected_bytes":expected_size,"actual_bytes":actual_size,
                    "expected_sha256":expected_sha,"actual_sha256":actual_sha,
                    "quarantine":str(quarantine),"known_bad_refresh":bad,"actions":actions}
        os.replace(part,target)
        existing=target

    iso_test={"returncode":127,"stdout":"","stderr":"7z missing"}
    seven=shutil.which("7z") or shutil.which("7zz")
    if seven:
        iso_test=run([seven,"t","-bd",str(existing)],timeout=1800)
    return {
        "status":"PASS" if existing.is_file() and sha(existing)==expected_sha and existing.stat().st_size==expected_size and iso_test["returncode"]==0 else "HOLD",
        "path":str(existing),"bytes":existing.stat().st_size if existing.is_file() else None,
        "sha256":sha(existing) if existing.is_file() else None,
        "expected_sha256":expected_sha,"expected_bytes":expected_size,
        "source_url":source_url,"source_owner":"MICROSOFT",
        "official_hash_document_sha256_value":expected_sha,
        "media_test":iso_test,"known_bad_refresh":bad,"existing_scan":scan,"actions":actions
    }

def _p11_mojo(mid):
    version="1.1.0"
    root=HOME/".local/share/louksna/mojo-1.1.0-p11"
    wheelhouse=HOME/".local/share/louksna/r4-p11/mojo-wheelhouse-1.1.0"
    bindir=HOME/".local/bin"
    link=bindir/"mojo"
    cpu=_p11_cpu_flags()
    mem=_p11_mem_total_bytes()
    vendor_ram_min=8*1024**3
    glibc=run(["getconf","GNU_LIBC_VERSION"],timeout=20)
    gcc=shutil.which("gcc") or shutil.which("cc") or shutil.which("clang")

    existing=shutil.which("mojo")
    actions=[]
    selected=pathlib.Path(existing) if existing else root/"bin/mojo"
    if selected.is_file():
        vt=run([str(selected),"--version"],timeout=60)
        if vt["returncode"]!=0 or "1.1.0" not in (vt["stdout"]+vt["stderr"]):
            if existing:
                raise RuntimeError("P11_MOJO_EXISTING_COMMAND_VERSION_CONFLICT:"+str(existing))
    else:
        if not cpu["x86_64_v3"]:
            return {"status":"HOLD","reason":"MOJO_CPU_X86_64_V3_NOT_MET","cpu":cpu}
        if not gcc:
            return {"status":"HOLD","reason":"MOJO_C_LINKER_MISSING","cpu":cpu}
        if not root.exists():
            rr=run(["python3","-m","venv",str(root)],timeout=300)
            actions.append({"operation":"CREATE_MOJO_VENV","result":rr})
            if rr["returncode"]!=0:
                return {"status":"HOLD","reason":"MOJO_VENV_CREATE_FAILED","actions":actions}
        pip=root/"bin/pip"
        if not pip.is_file():
            return {"status":"HOLD","reason":"MOJO_VENV_PIP_MISSING","actions":actions}
        wheelhouse.mkdir(parents=True,exist_ok=True)
        # Download once into a version-pinned local wheelhouse, then install only
        # from those local artifacts. Official Mojo docs publish the Python package.
        dr=run([str(pip),"download","--disable-pip-version-check",
                "--dest",str(wheelhouse),f"mojo=={version}"],timeout=3600)
        actions.append({"operation":"MODULAR_MOJO_1_1_0_WHEELHOUSE_ACQUIRE","result":dr})
        if dr["returncode"]!=0:
            return {"status":"HOLD","reason":"MOJO_WHEELHOUSE_ACQUIRE_FAILED","actions":actions}
        wheels=[]
        for p in sorted(wheelhouse.iterdir()):
            if p.is_file():
                wheels.append({"path":str(p),"bytes":p.stat().st_size,"sha256":sha(p)})
        ir=run([str(pip),"install","--disable-pip-version-check","--no-index",
                "--find-links",str(wheelhouse),f"mojo=={version}"],timeout=3600)
        actions.append({"operation":"MOJO_INSTALL_FROM_LOCAL_WHEELHOUSE","result":ir,"wheelhouse":wheels})
        if ir["returncode"]!=0:
            return {"status":"HOLD","reason":"MOJO_LOCAL_INSTALL_FAILED","actions":actions,"wheelhouse":wheels}
        selected=root/"bin/mojo"
        if not selected.is_file():
            return {"status":"HOLD","reason":"MOJO_EXECUTABLE_MISSING_AFTER_INSTALL","actions":actions}
        bindir.mkdir(parents=True,exist_ok=True)
        if link.exists() or link.is_symlink():
            try:
                if link.resolve(strict=True)!=selected.resolve(strict=True):
                    return {"status":"HOLD","reason":"MOJO_BIN_LINK_CONFLICT","existing":str(link.resolve(strict=False)),
                            "selected":str(selected),"actions":actions}
            except Exception:
                return {"status":"HOLD","reason":"MOJO_BIN_LINK_BROKEN_CONFLICT","selected":str(selected),"actions":actions}
        else:
            tmp=bindir/(".mojo-louksna-"+uuid.uuid4().hex)
            os.symlink(str(selected),tmp)
            os.replace(tmp,link)
            actions.append({"operation":"ACTIVATE_MOJO_USER_BIN","path":str(link),"target":str(selected)})

    testdir=R48_STATE/"p11/mojo-functional"
    testdir.mkdir(parents=True,exist_ok=True)
    src=testdir/"hello.mojo"
    src.write_text('def main():\n    print("LOUKSNA_MOJO_1_1_0_PASS")\n',encoding="utf-8")
    run_test=run([str(selected),str(src)],timeout=300)
    out=testdir/"hello"
    build_test=run([str(selected),"build",str(src),"-o",str(out)],timeout=600)
    exec_test=run([str(out)],timeout=60) if out.is_file() else {"returncode":127,"stdout":"","stderr":"build output missing"}
    ver_test=run([str(selected),"--version"],timeout=60)
    functional=(ver_test["returncode"]==0 and "1.1.0" in (ver_test["stdout"]+ver_test["stderr"]) and
                run_test["returncode"]==0 and "LOUKSNA_MOJO_1_1_0_PASS" in run_test["stdout"] and
                build_test["returncode"]==0 and exec_test["returncode"]==0 and
                "LOUKSNA_MOJO_1_1_0_PASS" in exec_test["stdout"])
    return {
        "status":"PASS" if functional else "HOLD",
        "version_required":version,"selected":str(selected),
        "version_test":ver_test,"run_test":run_test,"build_test":build_test,"executable_test":exec_test,
        "cpu":cpu,"glibc":glibc,"c_linker":gcc,
        "mem_total_bytes":mem,"vendor_minimum_ram_bytes":vendor_ram_min,
        "vendor_ram_minimum_met":mem>=vendor_ram_min,
        "compatibility_state":("OFFICIAL_RAM_MINIMUM_MET_AND_FUNCTIONAL" if mem>=vendor_ram_min and functional
                               else "FUNCTIONAL_ON_ACTUAL_HOST_WITH_VENDOR_RAM_MINIMUM_DEVIATION" if functional
                               else "HOLD"),
        "official_release":"MOJO_1_1_0_STABLE_2026_09_17",
        "actions":actions
    }

def maestro_p11_materialize(mid,request):
    part7_cert=CERTS/"PART_7.json"
    part7=read_json(part7_cert,{}) or {}
    if not part7_cert.is_file() or part7.get("status")!="PASS":
        return {
            "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0",
            "request_id":request["request_id"],"point_id":"P11","status":"HOLD",
            "mission_id":mid,"executor":"MAESTRO",
            "blockers":["PART7_G24_REQUIRED_BEFORE_P11"],
            "partial_bytes_preserved":True,
            "redownload_from_zero_performed":False,
            "partitioning_performed":False,"completed_at_utc":utc()
        }
    if _p11_heavy_part6_active():
        return {
            "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0",
            "request_id":request["request_id"],"point_id":"P11","status":"HOLD",
            "mission_id":mid,"executor":"MAESTRO",
            "blockers":["RESOURCE_GOVERNOR_SERIALIZES_P11_WHILE_PART6_HEAVY_ACTIVE"],
            "partitioning_performed":False,"completed_at_utc":utc()
        }
    checkpoint=R48_STATE/"rollback"/(dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-P11")
    checkpoint.mkdir(parents=True,exist_ok=False)
    baseline={
        "schema":"LOUKSNA_R4_P11_CHECKPOINT/1.0",
        "bad_windows_path":str(PROYECTOS/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/Windows11_IoT_Enterprise_LTSC_2024_Eval_x64.iso.reacquire.part"),
        "mojo_before":shutil.which("mojo"),
        "sudo_valid":privilege_status() is not None,
        "partitioning_authorized":False,
        "created_at_utc":utc()
    }
    atomic_json(checkpoint/"CHECKPOINT.json",baseline)

    windows=_p11_windows(mid)
    mojo=_p11_mojo(mid)
    checks={
        "windows_exact":windows.get("status")=="PASS",
        "mojo_functional":mojo.get("status")=="PASS",
        "mojo_exact_version":mojo.get("version_required")=="1.1.0",
        "mojo_actual_host_test":mojo.get("compatibility_state") in {
            "OFFICIAL_RAM_MINIMUM_MET_AND_FUNCTIONAL",
            "FUNCTIONAL_ON_ACTUAL_HOST_WITH_VENDOR_RAM_MINIMUM_DEVIATION"
        },
        "checkpoint":(checkpoint/"CHECKPOINT.json").is_file(),
        "partitioning_performed":False,
        "debian_redownload_performed":False,
        "kde_redownload_performed":False
    }
    success=(checks["windows_exact"] and checks["mojo_functional"] and checks["mojo_exact_version"] and
             checks["mojo_actual_host_test"] and checks["checkpoint"])
    result={
        "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0",
        "request_id":request["request_id"],"point_id":"P11",
        "status":"PASS" if success else "HOLD",
        "mission_id":mid,"executor":"MAESTRO","custosz_bound":True,
        "checkpoint":str(checkpoint),"windows":windows,"mojo":mojo,
        "checks":checks,
        "blockers":[k for k,v in checks.items() if k not in {"partitioning_performed","debian_redownload_performed","kde_redownload_performed"} and not v],
        "partitioning_performed":False,
        "debian_redownload_performed":False,
        "kde_redownload_performed":False,
        "completed_at_utc":utc()
    }
    atomic_json(R48_STATE/"P11_MATERIAL_RESULT.json",result)
    return result

def maestro_ui_point(mid,request):
    worker=pathlib.Path(__file__).with_name("ui_p10_p12_hardened_worker.py")
    point=request.get("point_id")
    outname={"P10":"UI_PANEL_4_9_RESULT.json","P12":"PROJECTS_CENTER_RESULT.json"}.get(point)
    if not worker.is_file() or not outname:
        return {
          "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0","request_id":request.get("request_id"),
          "point_id":point,"status":"HOLD","mission_id":mid,"executor":"MAESTRO",
          "blockers":["UI_P10_P12_WORKER_MISSING_OR_POINT_INVALID"],"completed_at_utc":utc()
        }
    rr=run([sys.executable,"-B",str(worker),"--point",point,"--mission-id",mid],timeout=1800)
    material=read_json(R48_STATE/outname,{}) or {}
    return {
      "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0","request_id":request.get("request_id"),
      "point_id":point,"status":material.get("status","HOLD"),"mission_id":mid,"executor":"MAESTRO",
      "worker":str(worker),"worker_sha256":sha(worker),"material_result_path":str(R48_STATE/outname),
      "material_result_sha256":sha(R48_STATE/outname) if (R48_STATE/outname).is_file() else None,
      "checks":material.get("checks",{}),"blockers":[k for k,v in material.get("checks",{}).items() if not bool(v)],
      "worker_returncode":rr.get("returncode"),"partitioning_performed":False,
      "debian_redownload_performed":False,"kde_redownload_performed":False,
      "completed_at_utc":utc()
    }

def handle_r48_point_request(mid):
    req=read_json(R48_POINT_REQUEST,{}) or {}
    if not req or req.get("status")!="AUTHORIZED":
        return None
    prior=read_json(R48_POINT_RESULT,{}) or {}
    if prior.get("request_id")==req.get("request_id"):
        return prior

    point=req.get("point_id")
    if point=="P06":
        result=maestro_projects_repair(mid,req)
    elif point=="P11":
        result=maestro_p11_materialize(mid,req)
    elif point in {"P10","P12"}:
        result=maestro_ui_point(mid,req)
    else:
        result={
            "schema":"LOUKSNA_R4_MAESTRO_POINT_RESULT/1.0",
            "request_id":req.get("request_id"),
            "point_id":point,
            "status":"HOLD",
            "mission_id":mid,
            "executor":"MAESTRO",
            "blockers":["NO_MATERIAL_HANDLER_REQUIRED_OR_IMPLEMENTED_FOR_THIS_POINT"],
            "completed_at_utc":utc()
        }
    atomic_json(R48_POINT_RESULT,result)
    return result

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

    directive=read_json(PART4_P3_TEN_POINT_DIRECTIVE,{}) or {}
    directive_ok=(
        directive.get("directive_id")=="PART4-P3-TEN-POINT-HARDENED-CONTINUATION-20261001"
        and directive.get("authority")=="Louksna.md"
        and directive.get("mission_id")==mid
        and directive.get("subordinate_to_contract",{}).get("contract_id")==contract.get("contract_id")
        and directive.get("disk_mutation_authorized_by_this_directive") is False
        and directive.get("filesystem_mutation_authorized_by_this_directive") is False
    )
    if stage>=4 and not directive_ok:
        return record(stage,"HOLD",{"reason":"TEN_POINT_DIRECTIVE_INVALID_OR_UNBOUND","mutation_performed":False},stage,"RECONCILE_TEN_POINT_DIRECTIVE")

    # Stage 4: build one local forensic recovery capsule, then wait for
    # independent off-host verification/certification. The disk is read only.
    if stage==4:
        capsule=PART4_P3_EXEC_DIR/"STAGE4_CAPSULE"
        manifest=capsule/"CAPSULE_MANIFEST.json"
        cert=PART4_P3_EXEC_DIR/"STAGE4_G24.json"
        if cert.is_file() and manifest.is_file():
            g24=read_json(cert,{}) or {}
            manifest_sha=sha(manifest)
            ok=(
                g24.get("status")=="PASS"
                and g24.get("scope")=="RECOVERY_CAPSULE_VALID_FOR_PRE_GROWTH_STATE"
                and g24.get("capsule_manifest_sha256")==manifest_sha
                and g24.get("disk_geometry_mutation_authorized") is False
                and g24.get("filesystem_mutation_authorized") is False
                and g24.get("certification_propagated") is False
            )
            if ok:
                return record(4,"PASS",{
                    "directive_id":directive["directive_id"],
                    "capsule_manifest_sha256":manifest_sha,
                    "stage4_g24_sha256":sha(cert),
                    "off_host_verified":True,
                    "mutation_performed":False,
                },5,"BUILD_STAGE5_EXACT_P3_GROWTH_CANDIDATE")
            return record(4,"HOLD",{"reason":"STAGE4_G24_MISMATCH","mutation_performed":False},4,"REVALIDATE_STAGE4_G24")

        if manifest.is_file():
            return record(4,"AWAITING_G23_G24",{
                "directive_id":directive["directive_id"],
                "capsule_manifest_sha256":sha(manifest),
                "local_capsule_ready":True,
                "off_host_verification_required":True,
                "mutation_performed":False,
            },4,"CERTIFY_STAGE4_CAPSULE_OFF_HOST")

        try:
            require_privilege("PART_4",["READ_ONLY_PARTITION_TABLE_RECOVERY_CAPSULE"])
            capsule.mkdir(parents=True,exist_ok=True)
            disk="/dev/nvme0n1"
            sfdisk=shutil.which("sfdisk") or "/usr/sbin/sfdisk"
            sgdisk=shutil.which("sgdisk") or "/usr/sbin/sgdisk"
            parted=shutil.which("parted") or "/usr/sbin/parted"
            blkid=shutil.which("blkid") or "/usr/sbin/blkid"
            commands={
                "SFDISK_DUMP.txt":["sudo","-n",sfdisk,"--dump",disk],
                "LSBLK.json":["lsblk","-J","-b","-o","NAME,PATH,TYPE,SIZE,START,FSTYPE,UUID,PARTUUID,MOUNTPOINTS",disk],
                "PARTED_PRINT_FREE.txt":["sudo","-n",parted,"-sm",disk,"unit","s","print","free"],
                "BLKID.txt":["sudo","-n",blkid,disk,"/dev/nvme0n1p1","/dev/nvme0n1p3"],
                "SGDISK_PRINT.txt":["sudo","-n",sgdisk,"-p",disk],
            }
            command_results={}
            for name,argv in commands.items():
                rr=run(argv,timeout=120)
                command_results[name]={"returncode":rr["returncode"],"argv":argv}
                if rr["returncode"]!=0:
                    raise RuntimeError("CAPSULE_COMMAND_FAILED:"+name+":"+rr["stderr"][:500])
                (capsule/name).write_text(rr["stdout"],encoding="utf-8")
            gpt=capsule/"GPT_BACKUP.bin"
            rr=run(["sudo","-n",sgdisk,f"--backup={gpt}",disk],timeout=120)
            if rr["returncode"]!=0:
                raise RuntimeError("SGDISK_BACKUP_FAILED:"+rr["stderr"][:500])
            run(["sudo","-n","chown",f"{os.getuid()}:{os.getgid()}",str(gpt)],timeout=30,check=True)
            p3_start=int(pathlib.Path("/sys/class/block/nvme0n1p3/start").read_text().strip())
            p3_size=int(pathlib.Path("/sys/class/block/nvme0n1p3/size").read_text().strip())
            boot_id=pathlib.Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            root_source=os.path.realpath(run(["findmnt","-n","-o","SOURCE","/"],check=True)["stdout"].strip())
            root_fstype=run(["findmnt","-n","-o","FSTYPE","/"],check=True)["stdout"].strip()
            uuid_out=run(["lsblk","-n","-o","UUID","/dev/nvme0n1p3"],check=True)["stdout"].strip()
            partuuid_out=run(["lsblk","-n","-o","PARTUUID","/dev/nvme0n1p3"],check=True)["stdout"].strip()
            tool_versions={}
            for name,argv in {
                "sfdisk":[sfdisk,"--version"],"sgdisk":[sgdisk,"--version"],
                "parted":[parted,"--version"],"lsblk":["lsblk","--version"]
            }.items():
                vr=run(argv,timeout=30)
                tool_versions[name]=(vr["stdout"]+"\n"+vr["stderr"]).strip()[:1000]
            files={}
            for p in sorted(capsule.iterdir()):
                if p.is_file() and p.name!="CAPSULE_MANIFEST.json":
                    files[p.name]={"sha256":sha(p),"bytes":p.stat().st_size}
            checks={
                "p3_start_immutable":p3_start==567296,
                "root_p3":root_source=="/dev/nvme0n1p3",
                "root_ext4":root_fstype=="ext4",
                "p5_absent":not pathlib.Path("/dev/nvme0n1p5").exists(),
                "p3_uuid":uuid_out=="e084ec2a-af39-48b5-bb89-db2dc6a98332",
                "gpt_backup_nonempty":gpt.stat().st_size>0,
                "required_files":all(x in files for x in ["SFDISK_DUMP.txt","LSBLK.json","PARTED_PRINT_FREE.txt","BLKID.txt","SGDISK_PRINT.txt","GPT_BACKUP.bin"]),
            }
            q={
                "schema":"LOUKSNA_R4_PART4_STAGE4_RECOVERY_CAPSULE/1.0",
                "status":"LOCAL_READY" if all(checks.values()) else "HOLD",
                "scope":"RECOVERY_CAPSULE_PRE_GROWTH_READ_ONLY",
                "mission_id":mid,
                "directive_id":directive["directive_id"],
                "contract_id":contract["contract_id"],
                "contract_sha256":sha(PART4_P3_HARDENED_CONTRACT),
                "directive_sha256":sha(PART4_P3_TEN_POINT_DIRECTIVE),
                "disk":disk,
                "p3_start_sector":p3_start,
                "p3_size_sectors":p3_size,
                "p3_uuid":uuid_out,
                "p3_partuuid":partuuid_out,
                "root_source":root_source,
                "root_fstype":root_fstype,
                "boot_id":boot_id,
                "checks":checks,
                "tool_versions":tool_versions,
                "command_results":command_results,
                "files":files,
                "disk_mutation_performed":False,
                "filesystem_mutation_performed":False,
                "off_host_verified":False,
                "created_at_utc":utc(),
            }
            atomic_json(manifest,q)
            if not all(checks.values()):
                return record(4,"HOLD",{"reason":"STAGE4_LOCAL_CAPSULE_CHECK_FAILED","checks":checks,"mutation_performed":False},4,"REMEDIATE_STAGE4_CAPSULE")
            return record(4,"AWAITING_G23_G24",{
                "directive_id":directive["directive_id"],
                "capsule_manifest_sha256":sha(manifest),
                "local_capsule_ready":True,
                "off_host_verification_required":True,
                "mutation_performed":False,
            },4,"CERTIFY_STAGE4_CAPSULE_OFF_HOST")
        except Exception as exc:
            return record(4,"HOLD",{
                "reason":"STAGE4_CAPSULE_EXCEPTION",
                "error":type(exc).__name__+":"+str(exc)[:1000],
                "mutation_performed":False,
            },4,"DIAGNOSE_STAGE4_CAPSULE")

    # Stage 5: derive the exact growth candidate from the deterministic Stage 3
    # evidence and current live geometry. No partition mutation is performed.
    if stage==5:
        candidate=PART4_P3_EXEC_DIR/"STAGE5_CANDIDATE.json"
        g23p=PART4_P3_EXEC_DIR/"STAGE5_G23.json"
        if g23p.is_file() and candidate.is_file():
            g23=read_json(g23p,{}) or {}
            ok=(
                g23.get("status")=="PASS"
                and g23.get("scope")=="P3_TRAILING_END_EXTENSION_CANDIDATE_ONLY"
                and g23.get("candidate_sha256")==sha(candidate)
                and g23.get("g24_allowed") is True
            )
            if ok:
                return record(5,"PASS",{
                    "candidate_sha256":sha(candidate),
                    "stage5_g23_sha256":sha(g23p),
                    "mutation_performed":False,
                },6,"CERTIFY_STAGE6_EXACT_P3_TRAILING_END_EXTENSION")
            return record(5,"HOLD",{"reason":"STAGE5_G23_MISMATCH","mutation_performed":False},5,"REVALIDATE_STAGE5_G23")
        if candidate.is_file():
            return record(5,"AWAITING_G23",{"candidate_sha256":sha(candidate),"mutation_performed":False},5,"G23_VALIDATE_STAGE5_CANDIDATE")
        dry=PART4_P3_EXEC_DIR/"STAGE3_DRYRUN.json"
        cap=PART4_P3_EXEC_DIR/"STAGE4_CAPSULE"/"CAPSULE_MANIFEST.json"
        if not dry.is_file() or not cap.is_file():
            return record(5,"HOLD",{"reason":"STAGE5_PREREQUISITE_MISSING","mutation_performed":False},4,"RETURN_STAGE4")
        d=read_json(dry,{}) or {}
        text=(d.get("run1",{}).get("stdout","")+"\n"+d.get("run1",{}).get("stderr",""))
        m=re.search(r"start=(\d+).*?old:\s*size=(\d+)\s*end=(\d+).*?new:\s*size=(\d+)\s*end=(\d+)",text,re.S)
        if not m:
            return record(5,"HOLD",{"reason":"STAGE3_DRYRUN_PARSE_FAILED","dryrun_sha256":sha(dry),"mutation_performed":False},5,"DIAGNOSE_STAGE3_DRYRUN_FORMAT")
        start,old_size,old_end,new_size,new_end=map(int,m.groups())
        live_start=int(pathlib.Path("/sys/class/block/nvme0n1p3/start").read_text().strip())
        live_size=int(pathlib.Path("/sys/class/block/nvme0n1p3/size").read_text().strip())
        sgdisk=shutil.which("sgdisk") or "/usr/sbin/sgdisk"
        gp=run(["sudo","-n",sgdisk,"-p","/dev/nvme0n1"],timeout=60)
        lm=re.search(r"last usable sector is\s+(\d+)",gp["stdout"]+"\n"+gp["stderr"],re.I)
        last_usable=int(lm.group(1)) if lm else None
        checks={
            "stage3_deterministic":d.get("deterministic") is True,
            "start_exact":start==live_start==567296,
            "old_size_exact":old_size==live_size,
            "old_end_exact":old_end==live_start+live_size-1,
            "growth_positive":new_size>old_size and new_end>old_end,
            "new_geometry_consistent":new_end==start+new_size-1,
            "last_usable_known":last_usable is not None,
            "target_within_last_usable":last_usable is not None and new_end<=last_usable,
            "p5_absent":not pathlib.Path("/dev/nvme0n1p5").exists(),
        }
        q={
            "schema":"LOUKSNA_R4_PART4_STAGE5_P3_GROWTH_CANDIDATE/1.0",
            "status":"CANDIDATE_READY" if all(checks.values()) else "HOLD",
            "scope":"P3_TRAILING_END_EXTENSION_CANDIDATE_ONLY",
            "mission_id":mid,
            "directive_id":directive["directive_id"],
            "disk":"/dev/nvme0n1",
            "partition":3,
            "old_start_sector":start,
            "old_end_sector":old_end,
            "old_size_sectors":old_size,
            "target_start_sector":start,
            "target_end_sector":new_end,
            "target_size_sectors":new_size,
            "delta_sectors":new_size-old_size,
            "delta_bytes":(new_size-old_size)*512,
            "gpt_last_usable_sector":last_usable,
            "stage3_dryrun_sha256":sha(dry),
            "stage4_capsule_manifest_sha256":sha(cap),
            "checks":checks,
            "disk_mutation_performed":False,
            "filesystem_mutation_performed":False,
            "prepared_at_utc":utc(),
        }
        atomic_json(candidate,q)
        if not all(checks.values()):
            return record(5,"HOLD",{"reason":"STAGE5_CANDIDATE_CHECK_FAILED","checks":checks,"mutation_performed":False},5,"DIAGNOSE_STAGE5_CANDIDATE")
        return record(5,"AWAITING_G23",{"candidate_sha256":sha(candidate),"mutation_performed":False},5,"G23_VALIDATE_STAGE5_CANDIDATE")

    # Stage 6: consume only a fresh exact-scope G24 certificate bound to the
    # Stage 5 candidate. This stage itself never mutates disk or filesystem.
    if stage==6:
        candidate=PART4_P3_EXEC_DIR/"STAGE5_CANDIDATE.json"
        cert=PART4_P3_EXEC_DIR/"STAGE6_G24.json"
        if not candidate.is_file():
            return record(6,"HOLD",{"reason":"STAGE5_CANDIDATE_MISSING","mutation_performed":False},5,"RETURN_STAGE5")
        if not cert.is_file():
            return record(6,"AWAITING_G24",{"candidate_sha256":sha(candidate),"mutation_performed":False},6,"G24_CERTIFY_EXACT_P3_TRAILING_END_EXTENSION")
        cand=read_json(candidate,{}) or {}
        g24=read_json(cert,{}) or {}
        checks={
            "status":g24.get("status")=="PASS",
            "scope":g24.get("scope")=="P3_TRAILING_END_EXTENSION_ONLY",
            "candidate_bound":g24.get("candidate_sha256")==sha(candidate),
            "device":g24.get("authorized_device")=="/dev/nvme0n1",
            "partition":int(g24.get("authorized_partition",0))==3,
            "start":int(g24.get("authorized_start_sector",-1))==567296==int(cand.get("target_start_sector",-2)),
            "old_end":int(g24.get("authorized_old_end_sector",-1))==int(cand.get("old_end_sector",-2)),
            "new_end":int(g24.get("authorized_new_end_sector",-1))==int(cand.get("target_end_sector",-2)),
            "format_false":g24.get("format_authorized") is False,
            "shrink_false":g24.get("shrink_authorized") is False,
            "move_false":g24.get("move_start_authorized") is False,
            "fs_false":g24.get("filesystem_resize_authorized") is False,
            "p5_false":g24.get("p5_recreation_authorized") is False,
            "migration_false":g24.get("migration_replay_authorized") is False,
            "no_propagation":g24.get("certification_propagated") is False,
        }
        if all(checks.values()):
            return record(6,"PASS",{
                "candidate_sha256":sha(candidate),
                "stage6_g24_sha256":sha(cert),
                "checks":checks,
                "mutation_performed":False,
            },7,"EXECUTE_STAGE7_SINGLE_P3_GEOMETRY_COMMIT")
        return record(6,"HOLD",{"reason":"STAGE6_G24_SCOPE_MISMATCH","checks":checks,"mutation_performed":False},6,"REVALIDATE_STAGE6_G24")

    # Stage 7: consume externally executed single-commit evidence. The
    # controller itself never retries or replays the geometry mutation.
    if stage==7:
        result=PART4_P3_EXEC_DIR/"STAGE7_RESULT.json"
        if not result.is_file():
            return record(7,"AWAITING_EXACT_COMMIT",{
                "directive_id":directive["directive_id"],
                "stage6_g24_sha256":sha(PART4_P3_EXEC_DIR/"STAGE6_G24.json") if (PART4_P3_EXEC_DIR/"STAGE6_G24.json").is_file() else None,
                "mutation_performed":False,
            },7,"EXECUTE_STAGE7_SINGLE_P3_GEOMETRY_COMMIT")
        q=read_json(result,{}) or {}
        checks={
            "status":q.get("status")=="PASS",
            "scope":q.get("scope")=="P3_TRAILING_END_EXTENSION_ONLY",
            "attempt_count":int(q.get("attempt_count",0))==1,
            "start_preserved":int(q.get("post_start_sector",-1))==567296,
            "target_end":int(q.get("post_end_sector",-1))==int(q.get("authorized_new_end_sector",-2)),
            "p1_unchanged":q.get("p1_unchanged") is True,
            "p5_absent":q.get("p5_absent") is True,
            "uuid_preserved":q.get("uuid_preserved") is True,
            "partuuid_preserved":q.get("partuuid_preserved") is True,
            "blind_retry":q.get("blind_retry_performed") is False,
            "stage6_bound":q.get("stage6_g24_sha256")==sha(PART4_P3_EXEC_DIR/"STAGE6_G24.json"),
        }
        if all(checks.values()):
            st["disk_mutation_performed"]=True
            return record(7,"PASS",{
                "stage7_result_sha256":sha(result),
                "checks":checks,
                "mutation_performed":True,
            },8,"RECONCILE_STAGE8_GPT_AND_KERNEL")
        return record(7,"HOLD",{"reason":"STAGE7_RESULT_NOT_PROVEN","checks":checks,"mutation_performed":q.get("physical_change_observed",False)},7,"OBSERVE_STAGE7_PHYSICAL_REALITY")

    # Stage 8: reconcile on-disk GPT and kernel-visible partition geometry.
    if stage==8:
        rec=PART4_P3_EXEC_DIR/"STAGE8_RECONCILIATION.json"
        if not rec.is_file():
            return record(8,"AWAITING_RECONCILIATION",{"mutation_performed":False},8,"RUN_STAGE8_GPT_KERNEL_RECONCILIATION")
        q=read_json(rec,{}) or {}
        if q.get("status")=="PASS" and q.get("gpt_target") is True and q.get("kernel_target") is True and q.get("p3_start_sector")==567296:
            return record(8,"PASS",{"stage8_sha256":sha(rec),"kernel_current":True,"mutation_performed":False},9,"EVALUATE_STAGE9_REBOOT_REQUIREMENT")
        if q.get("gpt_target") is True and q.get("kernel_target") is False:
            return record(8,"HOLD",{"reason":"GPT_CORRECT_KERNEL_STALE","stage8_sha256":sha(rec),"mutation_performed":False},8,"SAFE_KERNEL_VISIBILITY_REMEDIATION")
        return record(8,"HOLD",{"reason":"GEOMETRY_RECONCILIATION_FAILED","stage8_sha256":sha(rec),"mutation_performed":False},8,"DIAGNOSE_STAGE8_PHYSICAL_REALITY")

    # Stage 9: skip reboot when kernel already exposes the certified geometry.
    if stage==9:
        rec=PART4_P3_EXEC_DIR/"STAGE8_RECONCILIATION.json"
        q=read_json(rec,{}) or {}
        if q.get("status")=="PASS" and q.get("kernel_target") is True:
            return record(9,"PASS",{
                "reboot_required":False,
                "reason":"KERNEL_ALREADY_CURRENT",
                "stage8_sha256":sha(rec),
                "mutation_performed":False,
            },10,"RUN_STAGE10_PROYECTOS_FULL_NON_REGRESSION")
        token=PART4_P3_EXEC_DIR/"STAGE9_RESUME_TOKEN.json"
        if token.is_file():
            return record(9,"AWAITING_CONTROLLED_REBOOT",{"resume_token_sha256":sha(token),"mutation_performed":False},9,"CONTROLLED_REBOOT_AND_RESUME")
        return record(9,"HOLD",{"reason":"STAGE9_RESUME_TOKEN_REQUIRED","mutation_performed":False},9,"CREATE_STAGE9_RESUME_TOKEN")

    # Stage 10: consume a fresh full read-only PROYECTOS non-regression
    # verification bound to the certified freeze manifest. No filesystem or
    # geometry mutation is authorized by this handler.
    if stage==10:
        rec=PART4_P3_EXEC_DIR/"STAGE10_PROYECTOS_NON_REGRESSION.json"
        if not rec.is_file():
            return record(10,"AWAITING_FULL_VERIFY",{
                "manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
                "expected_records":498092,
                "mutation_performed":False,
            },10,"RUN_STAGE10_PROYECTOS_FULL_NON_REGRESSION")
        q=read_json(rec,{}) or {}
        checks={
            "status":q.get("status")=="PASS",
            "scope":q.get("scope")=="PROYECTOS_FORENSIC_NON_REGRESSION_BARRIER",
            "manifest":q.get("manifest_sha256")=="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
            "records":int(q.get("records",-1))==498092,
            "dirs":int(q.get("dirs",-1))==62016,
            "files":int(q.get("files",-1))==436072,
            "symlinks":int(q.get("symlinks",-1))==4,
            "other":int(q.get("other",-1))==0,
            "bytes":int(q.get("regular_file_bytes",-1))==200490852057,
            "missing_zero":int(q.get("missing", -1))==0,
            "unexpected_zero":int(q.get("unexpected", -1))==0,
            "hash_mismatch_zero":int(q.get("hash_mismatch", -1))==0,
            "type_mismatch_zero":int(q.get("type_mismatch", -1))==0,
            "size_mismatch_zero":int(q.get("size_mismatch", -1))==0,
            "disk_false":q.get("disk_mutation_performed") is False,
            "fs_false":q.get("filesystem_mutation_performed") is False,
        }
        if all(checks.values()):
            return record(10,"PASS",{
                "stage10_sha256":sha(rec),
                "checks":checks,
                "resize2fs_authorization_eligible":True,
                "mutation_performed":False,
            },11,"PREPARE_STAGE11_EXT4_G23_G24")
        return record(10,"HOLD",{
            "reason":"PROYECTOS_NON_REGRESSION_NOT_PROVEN",
            "stage10_sha256":sha(rec),
            "checks":checks,
            "mutation_performed":False,
        },10,"DIAGNOSE_STAGE10_PROYECTOS")

    # Stage 11: consume the independently certified, filesystem-only ext4
    # transaction result. This handler never executes resize2fs itself and
    # therefore cannot replay the consequential mutation.
    if stage==11:
        result=PART4_P3_EXEC_DIR/"STAGE11_RESULT.json"
        g23p=PART4_P3_EXEC_DIR/"STAGE11_G23.json"
        g24p=PART4_P3_EXEC_DIR/"STAGE11_G24.json"
        if not result.is_file() or not g23p.is_file() or not g24p.is_file():
            return record(11,"AWAITING_EXT4_RESULT",{
                "stage11_result_present":result.is_file(),
                "stage11_g23_present":g23p.is_file(),
                "stage11_g24_present":g24p.is_file(),
                "mutation_performed":False,
            },11,"COMPLETE_STAGE11_CERTIFIED_EXT4_TRANSACTION")
        q=read_json(result,{}) or {}
        g23=read_json(g23p,{}) or {}
        g24=read_json(g24p,{}) or {}
        checks={
            "status":q.get("status")=="PASS",
            "scope":q.get("scope")=="ONE_ONLINE_EXT4_GROW_ONLY",
            "result_checks":all(q.get("checks",{}).values()),
            "one_resize":int(q.get("resize2fs_attempts_performed",0))==1,
            "filesystem_mutated":q.get("filesystem_mutation_performed") is True,
            "no_geometry_mutation":q.get("disk_geometry_mutation_performed") is False,
            "no_partition_mutation":q.get("partition_table_mutation_performed") is False,
            "no_format":q.get("format_performed") is False,
            "no_shrink":q.get("shrink_performed") is False,
            "no_reboot":q.get("reboot_performed") is False,
            "filesystem_grew":int(q.get("filesystem_bytes_after",0))>int(q.get("filesystem_bytes_before",0)),
            "device_bound":0 <= int(q.get("block_device_bytes",0))-int(q.get("filesystem_bytes_after",0)) < 4096,
            "proyectos_records":int(q.get("post_proyectos_records",-1))==498092,
            "proyectos_mismatch_zero":int(q.get("post_proyectos_mismatch_count",-1))==0,
            "g23_hash_bound":q.get("g23_sha256")==sha(g23p),
            "g24_hash_bound":q.get("g24_sha256")==sha(g24p),
            "g23_pass":g23.get("status")=="PASS" and g23.get("scope")=="ONE_ONLINE_EXT4_GROW_ONLY",
            "g24_pass":g24.get("status")=="PASS" and g24.get("scope")=="ONE_ONLINE_EXT4_GROW_ONLY",
            "g23_g24_bound":g24.get("g23_sha256")==sha(g23p),
            "candidate_chain":q.get("candidate_sha256")==g23.get("candidate_sha256")==g24.get("candidate_sha256"),
            "g24_fs_only":g24.get("filesystem_mutation_authorized") is True
                and g24.get("disk_geometry_mutation_authorized") is False
                and g24.get("partition_table_mutation_authorized") is False
                and g24.get("format_authorized") is False
                and g24.get("shrink_authorized") is False
                and int(g24.get("resize2fs_attempts_authorized",0))==1,
        }
        if all(checks.values()):
            st["filesystem_mutation_performed"]=True
            return record(11,"PASS",{
                "stage11_result_sha256":sha(result),
                "stage11_g23_sha256":sha(g23p),
                "stage11_g24_sha256":sha(g24p),
                "filesystem_bytes_before":q.get("filesystem_bytes_before"),
                "filesystem_bytes_after":q.get("filesystem_bytes_after"),
                "block_device_bytes":q.get("block_device_bytes"),
                "checks":checks,
                "mutation_performed":True,
            },12,"PREPARE_STAGE12_TERMINAL_G23_G24")
        return record(11,"HOLD",{
            "reason":"STAGE11_CERTIFIED_RESULT_NOT_PROVEN",
            "stage11_result_sha256":sha(result),
            "checks":checks,
            "mutation_performed":q.get("filesystem_mutation_performed",False),
        },11,"DIAGNOSE_STAGE11_CERTIFIED_RESULT")

    # Stage 12: consume fresh terminal evidence with separate G24 scopes.
    # Only after both certificates and the live effective state agree may the
    # controller close the four terminal PART_4_R2 state flags. No disk or
    # filesystem mutation is authorized here.
    if stage==12:
        candidate=PART4_P3_EXEC_DIR/"STAGE12_CANDIDATE.json"
        g23p=PART4_P3_EXEC_DIR/"STAGE12_G23.json"
        mergeg24p=PART4_P3_EXEC_DIR/"STAGE12_FINAL_MERGE_G24.json"
        part4g24p=PART4_P3_EXEC_DIR/"STAGE12_PART4_G24.json"
        result=PART4_P3_EXEC_DIR/"STAGE12_RESULT.json"
        required=[candidate,g23p,mergeg24p,part4g24p,result]
        if not all(p.is_file() for p in required):
            return record(12,"AWAITING_TERMINAL_CERTIFICATION",{
                "candidate_present":candidate.is_file(),
                "g23_present":g23p.is_file(),
                "final_merge_g24_present":mergeg24p.is_file(),
                "part4_final_g24_present":part4g24p.is_file(),
                "result_present":result.is_file(),
                "mutation_performed":False,
            },12,"COMPLETE_STAGE12_TERMINAL_G23_G24")

        c=read_json(candidate,{}) or {}
        g23=read_json(g23p,{}) or {}
        mg24=read_json(mergeg24p,{}) or {}
        pg24=read_json(part4g24p,{}) or {}
        q=read_json(result,{}) or {}
        stage11=PART4_P3_EXEC_DIR/"STAGE11_RESULT.json"
        expected_blockers={
            "final_linux_layout",
            "part4_r2_final_g24",
            "final_merge_g24",
            "verified_root_on_consolidated_linux",
        }
        try:
            root_source=os.path.realpath(run(["findmnt","-n","-o","SOURCE","/"],check=True)["stdout"].strip())
            root_fstype=run(["findmnt","-n","-o","FSTYPE","/"],check=True)["stdout"].strip()
            efi_source=os.path.realpath(run(["findmnt","-n","-o","SOURCE","/boot/efi"],check=True)["stdout"].strip())
            efi_fstype=run(["findmnt","-n","-o","FSTYPE","/boot/efi"],check=True)["stdout"].strip()
            p3_start=int(pathlib.Path("/sys/class/block/nvme0n1p3/start").read_text().strip())
            p3_size=int(pathlib.Path("/sys/class/block/nvme0n1p3/size").read_text().strip())
            uuid_now=run(["lsblk","-n","-o","UUID","/dev/nvme0n1p3"],check=True)["stdout"].strip()
            partuuid_now=run(["lsblk","-n","-o","PARTUUID","/dev/nvme0n1p3"],check=True)["stdout"].strip()
            parts=run(["lsblk","-ln","-o","PATH,TYPE","/dev/nvme0n1"],check=True)["stdout"].splitlines()
            partitions=sorted(line.split()[0] for line in parts if len(line.split())>=2 and line.split()[1]=="part")
            live_ok=True
        except Exception:
            root_source=root_fstype=efi_source=efi_fstype=uuid_now=partuuid_now=None
            p3_start=p3_size=None
            partitions=[]
            live_ok=False

        checks={
            "result_status":q.get("status")=="PASS",
            "result_scope":q.get("scope")=="PART4_TERMINAL_CERTIFICATION_AND_MONOTONIC_HANDOFF",
            "result_checks":all(q.get("checks",{}).values()),
            "close_eligible":q.get("four_final_blockers_close_eligible") is True,
            "result_no_disk_mutation":q.get("disk_mutation_performed") is False,
            "result_no_fs_mutation":q.get("filesystem_mutation_performed") is False,
            "result_no_state_mutation":q.get("state_flags_mutated") is False,
            "candidate_ready":c.get("status")=="CANDIDATE_READY" and all(c.get("checks",{}).values()),
            "candidate_scope":c.get("scope")=="PART4_TERMINAL_EFFECTIVE_STATE_CERTIFICATION_ONLY",
            "candidate_blockers":set(c.get("four_final_blockers_before",[]))==expected_blockers,
            "candidate_hash_bound":q.get("candidate_sha256")==sha(candidate)==g23.get("candidate_sha256")==mg24.get("candidate_sha256")==pg24.get("candidate_sha256"),
            "g23_pass":g23.get("status")=="PASS" and g23.get("scope")=="PART4_TERMINAL_EFFECTIVE_STATE_INDEPENDENT_VALIDATION",
            "g23_hash_bound":q.get("g23_sha256")==sha(g23p)==mg24.get("g23_sha256")==pg24.get("g23_sha256"),
            "merge_g24_pass":mg24.get("status")=="PASS" and mg24.get("scope")=="PART4_R2_FINAL_MERGE_EFFECTIVE_STATE_ONLY",
            "merge_g24_hash_bound":q.get("final_merge_g24_sha256")==sha(mergeg24p)==pg24.get("final_merge_g24_sha256"),
            "merge_flags_exact":set(mg24.get("certified_state_flags",[]))=={
                "final_linux_layout","final_merge_g24","verified_root_on_consolidated_linux"
            },
            "part4_g24_pass":pg24.get("status")=="PASS" and pg24.get("scope")=="PART4_TERMINAL_CERTIFICATION_ONLY",
            "part4_g24_hash_bound":q.get("part4_final_g24_sha256")==sha(part4g24p),
            "part4_flag_exact":pg24.get("certified_state_flags")==["part4_r2_final_g24"],
            "no_certification_propagation":mg24.get("certification_propagated") is False and pg24.get("certification_propagated") is False,
            "certs_no_disk_auth":mg24.get("disk_mutation_authorized") is False and pg24.get("disk_mutation_authorized") is False,
            "certs_no_fs_auth":mg24.get("filesystem_mutation_authorized") is False and pg24.get("filesystem_mutation_authorized") is False,
            "stage11_bound":stage11.is_file() and q.get("stage11_result_sha256")==sha(stage11)==c.get("stage11_result_sha256"),
            "live_read_ok":live_ok,
            "live_root":root_source=="/dev/nvme0n1p3" and root_fstype=="ext4",
            "live_efi":efi_source=="/dev/nvme0n1p1" and efi_fstype=="vfat",
            "live_partitions":partitions==["/dev/nvme0n1p1","/dev/nvme0n1p3"],
            "live_p5_absent":not pathlib.Path("/dev/nvme0n1p5").exists(),
            "live_p3_start":p3_start==567296,
            "live_p3_size":p3_size==999647887,
            "live_uuid":uuid_now=="e084ec2a-af39-48b5-bb89-db2dc6a98332",
            "live_partuuid":partuuid_now=="8e0b4274-21ff-4b16-8180-495381efb1d9",
        }
        if not all(checks.values()):
            return record(12,"HOLD",{
                "reason":"STAGE12_TERMINAL_CHAIN_OR_LIVE_STATE_NOT_PROVEN",
                "checks":checks,
                "mutation_performed":False,
            },12,"DIAGNOSE_STAGE12_TERMINAL_EVIDENCE")

        r2path=STATE/"PART_4_R2/STATE.json"
        if not r2path.is_file():
            return record(12,"HOLD",{
                "reason":"PART4_R2_STATE_MISSING",
                "checks":checks,
                "mutation_performed":False,
            },12,"RESTORE_PART4_R2_STATE_CHECKPOINT")
        try:
            r2_before=read_json(r2path,{}) or {}
            before_sha=sha(r2path)
            checkpoint=PART4_P3_EXEC_DIR/"STAGE12_R2_STATE_BEFORE.json"
            if not checkpoint.is_file():
                shutil.copy2(r2path,checkpoint)
            r2_after=dict(r2_before)
            r2_after.update({
                "final_linux_layout":True,
                "verified_root_on_consolidated_linux":True,
                "final_merge_g24":True,
                "final_merge_g24_sha256":sha(mergeg24p),
                "part4_r2_final_g24":True,
                "part4_r2_final_g24_sha256":sha(part4g24p),
                "stage12_terminal_candidate_sha256":sha(candidate),
                "stage12_terminal_g23_sha256":sha(g23p),
                "stage12_terminal_result_sha256":sha(result),
                "stage12_terminal_state_update_scope":"FOUR_FINAL_BLOCKERS_ONLY",
                "stage12_terminal_state_updated_at_utc":utc(),
            })
            atomic_json(r2path,r2_after)
            verified=read_json(r2path,{}) or {}
            state_checks={
                "final_linux_layout":verified.get("final_linux_layout") is True,
                "verified_root":verified.get("verified_root_on_consolidated_linux") is True,
                "final_merge_g24":verified.get("final_merge_g24") is True,
                "final_merge_hash":verified.get("final_merge_g24_sha256")==sha(mergeg24p),
                "part4_final_g24":verified.get("part4_r2_final_g24") is True,
                "part4_final_hash":verified.get("part4_r2_final_g24_sha256")==sha(part4g24p),
                "candidate_hash":verified.get("stage12_terminal_candidate_sha256")==sha(candidate),
                "g23_hash":verified.get("stage12_terminal_g23_sha256")==sha(g23p),
                "result_hash":verified.get("stage12_terminal_result_sha256")==sha(result),
            }
            state_update={
                "schema":"LOUKSNA_R4_PART4_STAGE12_STATE_UPDATE/1.0",
                "status":"PASS" if all(state_checks.values()) else "HOLD",
                "scope":"FOUR_FINAL_BLOCKERS_ONLY",
                "before_sha256":before_sha,
                "checkpoint_sha256":sha(checkpoint),
                "after_sha256":sha(r2path),
                "final_merge_g24_sha256":sha(mergeg24p),
                "part4_final_g24_sha256":sha(part4g24p),
                "checks":state_checks,
                "disk_mutation_performed":False,
                "filesystem_mutation_performed":False,
                "updated_at_utc":utc(),
            }
            atomic_json(PART4_P3_EXEC_DIR/"STAGE12_STATE_UPDATE.json",state_update)
        except Exception as exc:
            return record(12,"HOLD",{
                "reason":"STAGE12_STATE_UPDATE_FAILED",
                "error":type(exc).__name__+":"+str(exc)[:1000],
                "checks":checks,
                "mutation_performed":False,
            },12,"RESTORE_STAGE12_R2_STATE_CHECKPOINT")

        if not all(state_checks.values()):
            return record(12,"HOLD",{
                "reason":"STAGE12_STATE_UPDATE_VERIFY_FAILED",
                "checks":checks,
                "state_checks":state_checks,
                "mutation_performed":False,
            },12,"VERIFY_STAGE12_R2_STATE")

        return record(12,"PASS",{
            "stage12_result_sha256":sha(result),
            "stage12_g23_sha256":sha(g23p),
            "stage12_final_merge_g24_sha256":sha(mergeg24p),
            "stage12_part4_final_g24_sha256":sha(part4g24p),
            "stage12_state_update_sha256":sha(PART4_P3_EXEC_DIR/"STAGE12_STATE_UPDATE.json"),
            "four_final_blockers_closed":True,
            "checks":checks,
            "state_checks":state_checks,
            "mutation_performed":False,
        },None,"HANDOFF_PART4_TO_PART5")

    stage_id=stages[stage-1]["id"]
    return record(stage,"AWAITING_STAGE_HANDLER",{
        "stage_id":stage_id,
        "directive_id":directive["directive_id"],
        "directive_sha256":sha(PART4_P3_TEN_POINT_DIRECTIVE),
        "mutation_performed":False,
    },stage,"DISPATCH_"+stage_id)

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
    # PART_6 is certification-gated by hardened functional evidence. Legacy
    # filename discovery remains supporting evidence only and can never cause
    # PASS by itself.
    req={
        "wine":["wine-stable-amd64.deb","wine"],
        "steam":["steam_latest.deb","steam"],
        "proton":["proton-11.0-2.tar.gz","*Proton*"],
        "bottles":["bottles.flatpakref","*Bottles*"],
        "lutris":["lutris-v0.5.22.tar.gz","*lutris*"],
        "prism":["PrismLauncher.AppImage","*PrismLauncher*"],
        "waydroid":["waydroid_1.6.2_all.deb","*waydroid*"],
    }
    _,_,presence_details=bounded_presence_part("PART_6",req)
    d=STATE/"PART_6_HARDENED"
    resultp=d/"RESULT.json"
    component_names=("wine","steam","proton","bottles","lutris","prism","waydroid")

    worker_path=pathlib.Path(__file__).with_name("part6_hardened_worker.py")
    worker_dispatch=None
    if not resultp.is_file() and worker_path.is_file():
        try:
            worker_dispatch=run(
                [sys.executable,"-B",str(worker_path),"--mission-id",mid],
                timeout=21600,
            )
        except Exception as exc:
            worker_dispatch={
                "argv":[sys.executable,"-B",str(worker_path),"--mission-id",mid],
                "returncode":999,
                "stdout":"",
                "stderr":type(exc).__name__+":"+str(exc),
            }

    if not resultp.is_file():
        checks={k:False for k in component_names}
        details={
            "hardened_result_present":False,
            "hardened_result_path":str(resultp),
            "worker_path":str(worker_path),
            "worker_present":worker_path.is_file(),
            "worker_dispatch":worker_dispatch,
            "presence_support_only":presence_details,
            "certification_basis":"HARDENED_RESULT_REQUIRED; PRESENCE_ONLY_FORBIDDEN",
        }
        return evidence_base("PART_6",mid,checks,"HOLD",list(component_names),details)

    q=read_json(resultp,{}) or {}
    candidate=d/"FULL_CANDIDATE_V2.json"
    g23p=d/"FULL_G23_V2.json"
    g24p=d/"FULL_G24_V2.json"
    precommit=d/"FULL_PRECOMMIT_V2.json"
    chain_files=(candidate,g23p,g24p,precommit)
    components=q.get("components",{}) if isinstance(q.get("components"),dict) else {}

    component_checks={}
    for name in component_names:
        item=components.get(name,{}) if isinstance(components.get(name),dict) else {}
        component_checks[name]=(
            item.get("status")=="PASS"
            and item.get("functional_test_pass") is True
            and bool(item.get("provenance"))
        )

    checkpoint_path=q.get("rollback_checkpoint_path")
    checkpoint_ok=False
    if isinstance(checkpoint_path,str) and checkpoint_path:
        try:
            cp=pathlib.Path(checkpoint_path)
            checkpoint_ok=(
                cp.is_file()
                and str(cp.resolve()).startswith(str(d.resolve())+os.sep)
                and q.get("rollback_checkpoint_sha256")==sha(cp)
            )
        except Exception:
            checkpoint_ok=False

    chain_present=all(p.is_file() for p in chain_files)
    chain_checks={
        "schema":q.get("schema")=="LOUKSNA_R4_PART6_HARDENED_RESULT/1.0",
        "result_status":q.get("status")=="PASS",
        "mission_id":q.get("mission_id")==mid,
        "chain_present":chain_present,
        "candidate_bound":chain_present and q.get("candidate_sha256")==sha(candidate),
        "g23_bound":chain_present and q.get("g23_sha256")==sha(g23p),
        "g24_bound":chain_present and q.get("g24_sha256")==sha(g24p),
        "precommit_pass":chain_present and (read_json(precommit,{}) or {}).get("status")=="PASS",
        "g23_pass":chain_present and (read_json(g23p,{}) or {}).get("status")=="PASS",
        "g24_pass":chain_present and (read_json(g24p,{}) or {}).get("status")=="PASS",
        "result_checks":isinstance(q.get("checks"),dict) and bool(q.get("checks")) and all(q.get("checks",{}).values()),
        "rollback_checkpoint":checkpoint_ok,
        "no_partition_mutation":q.get("disk_partition_mutation_performed") is False,
        "no_fs_format_resize":q.get("filesystem_format_or_resize_performed") is False,
        "no_unrelated_delete":q.get("unrelated_user_data_deleted") is False,
        "no_certification_propagation":q.get("certification_propagated") is False,
        "component_set_exact":set(components)==set(component_names),
    }
    checks={**component_checks,**{"hardened_"+k:v for k,v in chain_checks.items()}}
    blockers=[k for k,v in component_checks.items() if not v]
    blockers += ["hardened_"+k for k,v in chain_checks.items() if not v]
    details={
        "hardened_result_path":str(resultp),
        "hardened_result_sha256":sha(resultp),
        "component_evidence":components,
        "chain_checks":chain_checks,
        "presence_support_only":presence_details,
        "certification_basis":"FUNCTIONAL_EVIDENCE_PLUS_G23_G24_CHAIN",
    }
    return evidence_base("PART_6",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def run_part789_material(part,mid):
    names={
      "PART_7":("PART7_AUX_EVIDENCE.json","LOUKSNA_R4_PART7_AUX_EVIDENCE/1.0"),
      "PART_8":("PART8_AUX_EVIDENCE.json","LOUKSNA_R4_PART8_AUX_EVIDENCE/1.0"),
      "PART_9":("PART9_MATRIX.json","LOUKSNA_R4_PART9_TERMINAL_MATRIX/1.0"),
    }
    name,schema=names[part]
    p=R48_EVID/name
    prior=read_json(p,{}) or {}
    worker=pathlib.Path(__file__).with_name("part789_hardened_worker.py")
    expected_revision="2026-10-02.PART789.3-P25-P26-OPERATIONAL"
    expected_worker_sha=sha(worker) if worker.is_file() else None
    # Idempotence is byte-bound. Reuse evidence only when the exact material
    # producer bytes that generated it are still the current certified worker.
    # Any real worker delta is new causal evidence and permits one revalidation.
    if (prior.get("schema")==schema and prior.get("executor")=="MAESTRO"
        and expected_worker_sha
        and prior.get("producer_sha256")==expected_worker_sha):
        return {"status":"REUSE_EXISTING","evidence_path":str(p),"evidence_sha256":sha(p),
                "producer_revision":expected_revision,"producer_sha256":expected_worker_sha}
    if not worker.is_file():
        return {"status":"HOLD","error":"PART789_WORKER_MISSING","worker":str(worker)}
    timeout={"PART_7":7200,"PART_8":1800,"PART_9":600}[part]
    try:
        r=run([sys.executable,"-B",str(worker),"--part",part,"--mission-id",mid],timeout=timeout)
    except Exception as e:
        return {"status":"HOLD","error":type(e).__name__+":"+str(e),"worker":str(worker)}
    return {"status":"PASS" if r["returncode"]==0 else "HOLD","worker":str(worker),"result":r}

def part7(mid):
    dispatch=run_part789_material("PART_7",mid)
    d,meta=r48_aux("PART7_AUX_EVIDENCE.json","LOUKSNA_R4_PART7_AUX_EVIDENCE/1.0")
    checks={
      "aux_present":d is not None,
      "aux_pass":bool(d and d.get("status")=="PASS"),
      "source_count":bool(d and int(d.get("source_count",0))>0),
      "unknown_zero":bool(d and int(d.get("unknown_count",-1))==0),
      "classification":bool(d and d.get("checks",{}).get("classification") is True),
      "index_reproducible":bool(d and d.get("checks",{}).get("index_reproducible") is True),
      "retrieval":bool(d and d.get("checks",{}).get("retrieval") is True),
      "hermeneutic_controls":bool(d and d.get("checks",{}).get("hermeneutic_controls") is True),
      "unknown_negative_test":bool(d and d.get("checks",{}).get("unknown_negative_test") is True),
      "adversarial_unknown_holds":bool(d and d.get("checks",{}).get("adversarial_unknown_holds") is True),
      "source_output_separation":bool(d and d.get("checks",{}).get("generated_analysis_separate") is True),
      "originals_immutable":bool(d and d.get("checks",{}).get("originals_immutable_by_operation") is True),
      "p25_local_backend":bool(
          d and d.get("p25_local_cognitive_backend",{}).get("status")=="PASS"
          and d.get("p25_local_cognitive_backend",{}).get("operational") is True
          and d.get("p25_local_cognitive_backend",{}).get("hosted_backend_used") is False
      ),
      "p25_not_hosted_substitution":bool(d and d.get("p25_local_cognitive_backend",{}).get("qwen_substitution") is False),
      "p26_document_ingestion":bool(
          d and d.get("p26_document_ingestion_stack",{}).get("status")=="PASS"
          and d.get("p26_document_ingestion_stack",{}).get("operational") is True
          and d.get("p26_document_ingestion_stack",{}).get("source_immutable") is True
      ),
      "no_p25_model_download":bool(d and d.get("p25_local_cognitive_backend",{}).get("downloads_performed") is False),
      "no_p26_docling_download":bool(d and d.get("p26_document_ingestion_stack",{}).get("docling_assets_downloaded") is False),
      "audit_trace":bool(d and d.get("checks",{}).get("audit_trace") is True),
      "non_regression":bool(d and d.get("checks",{}).get("non_regression") is True),
    }
    blockers=[k for k,v in checks.items() if not v]
    details={"aux":meta,"aux_blockers":d.get("blockers",[]) if d else ["AUX_EVIDENCE_MISSING"],"material_dispatch":dispatch}
    return evidence_base("PART_7",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part8(mid):
    dispatch=run_part789_material("PART_8",mid)
    d,meta=r48_aux("PART8_AUX_EVIDENCE.json","LOUKSNA_R4_PART8_AUX_EVIDENCE/1.0")
    required=("backup_artifact","backup_hash","backup_manifest","restore_test","recovery_proof",
              "hygiene_dry_run_first","unknown_preserve","protected_paths_denied","no_cleanup_performed",
              "resource_governor_observed","heavy_work_serialization_policy","quality_floor_not_reduced",
              "metaos","runtime","evidence_audit_trace","rollback_proof","non_regression")
    checks={"aux_present":d is not None,"aux_pass":bool(d and d.get("status")=="PASS")}
    for k in required: checks[k]=bool(d and d.get("checks",{}).get(k) is True)
    blockers=[k for k,v in checks.items() if not v]
    details={"aux":meta,"aux_blockers":d.get("blockers",[]) if d else ["AUX_EVIDENCE_MISSING"],"material_dispatch":dispatch}
    return evidence_base("PART_8",mid,checks,"PASS" if not blockers else "HOLD",blockers,details)

def part9(mid):
    dispatch=run_part789_material("PART_9",mid)
    prior=[]
    for p in PARTS[:-1]:
        cp=CERTS/f"{p}.json"
        if cp.is_file(): prior.append({"part":p,"sha256":sha(cp)})
    d,meta=r48_aux("PART9_MATRIX.json","LOUKSNA_R4_PART9_TERMINAL_MATRIX/1.0")
    matrix_checks=d.get("checks",{}) if d else {}
    cert_bind_ok=bool(d and len(prior)==8 and all(
        d.get("certificates",{}).get(row["part"],{}).get("sha256")==row["sha256"] for row in prior
    ))
    checks={
      "prior_certificates":len(prior)==8,
      "matrix_present":d is not None,
      "matrix_pass":bool(d and d.get("status")=="PASS"),
      "certificate_digest_binding":cert_bind_ok,
      "runner":run(["systemctl","is-active","actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"])["stdout"].strip()=="active",
      "symphylax":run(["systemctl","--user","is-active","symphylax-r1.service"])["stdout"].strip()=="active",
      "remote_bridge_live_telemetry":bool(matrix_checks.get("REMOTE_BRIDGE_LIVE_TELEMETRY")),
      "cross_domain_isolation":bool(matrix_checks.get("cross_domain_isolation")),
      "validator_independence":bool(matrix_checks.get("validator_independence_required")),
      "global_non_regression":bool(matrix_checks.get("global_non_regression")),
      "rollback_continuity":bool(matrix_checks.get("rollback_continuity")),
      "trace_complete":bool(matrix_checks.get("trace_completeness")),
      "audit_complete":bool(matrix_checks.get("audit_completeness")),
      "provenance_complete":bool(matrix_checks.get("provenance_completeness")),
    }
    blockers=[k for k,v in checks.items() if not v]
    ev=evidence_base("PART_9",mid,checks,"PASS" if not blockers else "HOLD",blockers,{"prior":prior,"matrix":meta,"matrix_blockers":d.get("blockers",[]) if d else ["MATRIX_MISSING"],"material_dispatch":dispatch})
    ev["prior_part_certificates"]=prior
    ev["postinstall_matrix"]="PASS" if not blockers else "HOLD"
    ev["rollback_survives"]=checks["rollback_continuity"]
    ev["part9_exit"]="PART9_CERTIFIED_CANDIDATE" if not blockers else "HOLD"
    return ev

HANDLERS={"PART_1":part1,"PART_2":part2,"PART_3":part3,"PART_4":part4,"PART_5":part5,"PART_6":part6,"PART_7":part7,"PART_8":part8,"PART_9":part9}

def gh_json(args,timeout=120):
    # GitHub JSON must never pass through run(), whose bounded stdout is
    # intentionally truncated for ordinary command evidence. Truncating a
    # large Actions response destroys the leading JSON and causes false
    # GH_JSON_INVALID failures during certificate discovery.
    env=dict(os.environ); env["GH_PAGER"]="cat"; env["NO_COLOR"]="1"
    p=subprocess.run(["gh",*args],text=True,capture_output=True,timeout=timeout,env=env)
    if p.returncode!=0:
        raise RuntimeError("GH_FAILED:"+p.stderr[-6000:])
    raw=p.stdout.strip()
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
    completed=False
    for _ in range(450):
        wr=gh_json(["api",f"repos/{REPO}/actions/runs/{run_id}"],timeout=30)
        status=wr.get("status")
        if status=="completed":
            conclusion=wr.get("conclusion")
            if conclusion!="success":
                raise RuntimeError("CERT_WORKFLOW_FAILED:"+str(run_id)+":"+str(conclusion))
            completed=True
            break
        time.sleep(2)
    if not completed:
        raise RuntimeError("CERT_WORKFLOW_TIMEOUT:"+str(run_id))
    with tempfile.TemporaryDirectory(prefix="r4-g24-") as td:
        d=pathlib.Path(td)
        z=run(["gh","run","download",str(run_id),"--repo",REPO,"-n","r4-master-g24","-D",str(d)],timeout=120)
        if z["returncode"]!=0: raise RuntimeError("G24_DOWNLOAD_FAILED")
        cp=d/"G24.json"; cert=json.loads(cp.read_text(encoding="utf-8"))
        if cert.get("status")!="PASS" or cert.get("part")!=part or cert.get("evidence_sha256")!=hashlib.sha256(raw).hexdigest(): raise RuntimeError("G24_CERT_MISMATCH")
        cert["workflow_run_id"]=run_id; cert["evidence_commit_sha"]=commit
        atomic_json(CERTS/f"{part}.json",cert); return cert

def current_part():
    contract=r48_contract()
    for p in PARTS:
        if not (CERTS/f"{p}.json").is_file():
            if p=="PART_4" and contract.get("immutable_boundaries",{}).get("part4_closed") is True:
                raise RuntimeError("PART4_CERT_MISSING_REOPEN_DENIED")
            return p
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
        "anti_paralysis_contract":"R4_15P_ANTI_PARALYSIS_V1",
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
        if r48_expired():
            atomic_json(STATE/"MASTER_STATUS.json",{
              "status":"EXPIRED_48H","mission_id":mid,"deadline_utc":r48_contract()["window"]["deadline_utc"],
              "current_part":current_part(),"updated_at_utc":utc(),"new_material_work":False
            })
            return 0
        try:
            mid,_=ensure_master_mission(worker,mission_text)
            point_result=handle_r48_point_request(mid)
            if point_result is not None:
                atomic_json(R48_STATE/"LAST_MAESTRO_POINT_RESULT.json",point_result)
            result=supervise_once(worker,mid)
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
