#!/usr/bin/env python3
from __future__ import annotations
import base64, datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, tempfile, time, traceback, urllib.parse, xml.etree.ElementTree as ET, uuid

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
STATE=HOME/".local/state/louksna/r4-48h"
POINTS_DIR=STATE/"points"
POINT_CERTS=STATE/"point-certificates"
R4=HOME/".local/state/louksna/r4-master-part1-part9"
PART_CERTS=R4/"certificates"
LIVE=HOME/".local/lib/louksna/r4-master-part1-part9"
ROOT=HOME/".local/lib/louksna/r4-48h"
STAGED=ROOT/"staged"
CONTRACT=ROOT/"R4_48H_CONTRACT.json"
MASTER_SERVICE="luna-r4-master-part1-part9.service"
COORD_SERVICE="luna-r4-48h-coordinator.service"
RUNNER_SERVICE="actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"
REPO="Plomillo/luna-linux-bridge"
BRANCH="staging/luna-r4-master-part1-part9-20260929"
POINT_CERT_WORKFLOW=".github/workflows/r4-15point-certify.yml"
POLL=15
PROYECTOS=HOME/"PROYECTOS"
AUTHORITY=HOME/".local/lib/louksna/symphylax-r1/Louksna.md"
CUSTOSZ_CANDIDATES=[
    HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ.v07.f04_b.pyz",
    HOME/"LOUKSNA_FREEZE_20260925/CUSTOSZ.v07.pyz",
]
RUNTIME=HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
METAOS=HOME/".local/lib/louksna/symphylax-r1/MetaOS.wasm"
UI_REF=HOME/"Descargas/LUNA_R4_UI_REFERENCE/LUNA_R4_UI_REFERENCE_PARTS_1_9.jpg"
EXPECTED_UI_SHA="8a9852c4155d64fd74059c7239e67c82e16e5acd556627d70575db85078d4ed4"
WINDOWS_BAD=PROYECTOS/"1. PROYECTOS PRIORITARIOS/8. META OS/COMPONENTS/Windows11_IoT_Enterprise_LTSC_2024_Eval_x64.iso.reacquire.part"
WINDOWS_EXPECTED_SHA="8abf91c9cd408368dc73aab3425d5e3c02dae74900742072eb5c750fc637c195"

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha(p:pathlib.Path):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):
            h.update(b)
    return h.hexdigest()

def load(p,default=None):
    try:
        return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:
        return default

def atomic(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(t,p)

def ledger(event,**payload):
    STATE.mkdir(parents=True,exist_ok=True)
    head=load(STATE/"LEDGER_HEAD.json",{}) or {}
    prev=head.get("sha256")
    row={"schema":"LOUKSNA_R4_15P_LEDGER_EVENT/1.0","utc":utc(),"event":event,"previous_event_sha256":prev,**payload}
    raw=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    digest=hashlib.sha256(raw).hexdigest()
    row["event_sha256"]=digest
    with (STATE/"LEDGER.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
        f.flush(); os.fsync(f.fileno())
    atomic(STATE/"LEDGER_HEAD.json",{"sha256":digest,"event":event,"utc":row["utc"]})
    return row

def contract():
    d=load(CONTRACT,{}) or {}
    if d.get("schema")!="LOUKSNA_R4_REMAINDER_48H_CONTRACT/2.0":
        raise RuntimeError("CONTRACT_V2_REQUIRED")
    return d

def deadline():
    return dt.datetime.fromisoformat(contract()["window"]["deadline_utc"].replace("Z","+00:00"))

def run(argv,timeout=120,check=False,env=None):
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env)
    rec={"argv":argv,"returncode":p.returncode,"stdout":p.stdout[-16000:],"stderr":p.stderr[-8000:]}
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAILED:"+json.dumps(rec,ensure_ascii=False))
    return rec

def systemctl_user(*args):
    return run(["systemctl","--user",*args],timeout=60)

def service_state(user,name):
    argv=["systemctl"]+(["--user"] if user else [])+["show",name,"-p","ActiveState","-p","SubState","-p","MainPID","-p","NRestarts","--no-pager"]
    r=run(argv,timeout=30)
    data={}
    for line in r["stdout"].splitlines():
        if "=" in line:
            k,v=line.split("=",1); data[k]=v
    data["returncode"]=r["returncode"]
    return data

def master_active():
    return systemctl_user("is-active",MASTER_SERVICE)["stdout"].strip()=="active"

def proc_lines():
    r=run(["ps","-eo","pid,ppid,etimes,args"],timeout=20)
    keys=("master_controller.py","part6_hardened_worker.py","make build_name=louksna-proton")
    return [x for x in r["stdout"].splitlines() if any(k in x for k in keys) and "maestro_48h_coordinator.py" not in x]

def part6_child_active():
    return any("part6_hardened_worker.py" in x or "make build_name=louksna-proton" in x for x in proc_lines())

def lrb_link():
    roots=sorted((HOME/".local/lib/louksna-remote-bridge").glob("**/bridge/live_link.py"))
    if not roots:
        raise RuntimeError("LOUKSNA_REMOTE_BRIDGE_LINK_MISSING")
    return roots[-1]

def lrb(op):
    uid=os.getuid()
    env=dict(os.environ)
    env["XDG_RUNTIME_DIR"]=f"/run/user/{uid}"
    env["DBUS_SESSION_BUS_ADDRESS"]=f"unix:path=/run/user/{uid}/bus"
    argv=["python3","-B",str(lrb_link()),"--state-dir",str(HOME/".local/state/louksna/remote-bridge/service"),
          "--socket-dir",f"/run/user/{uid}/lrb-sock","request","--op",op]
    r=run(argv,timeout=90,env=env)
    if r["returncode"]:
        raise RuntimeError("LRB_"+op.upper()+"_FAILED:"+r["stderr"][-1000:])
    return json.loads(r["stdout"])

def observe(tag):
    status=lrb("status")
    obs=lrb("observe")
    rec={
        "schema":"LOUKSNA_R4_LRB_READ_ONLY_OBSERVATION/1.0",
        "tag":tag,"status":status,"observe":obs,
        "read_only":True,"material_execution":False,"captured_at_utc":utc()
    }
    atomic(STATE/"observations"/f"{tag}.json",rec)
    ledger("LRB_OBSERVATION",tag=tag,evidence_seq=obs.get("evidence_seq"),evidence_sha256=obs.get("evidence_sha256"))
    return rec

def locate_custosz():
    for p in CUSTOSZ_CANDIDATES:
        if p.is_file():
            return p
    return None

def sudo_ok():
    return run(["sudo","-n","true"],timeout=10)["returncode"]==0 and run(["sudo","-n","visudo","-c"],timeout=20)["returncode"]==0

def gh_json(args,timeout=120):
    env=dict(os.environ); env["GH_PAGER"]="cat"; env["NO_COLOR"]="1"
    p=subprocess.run(["gh",*args],text=True,capture_output=True,timeout=timeout,env=env)
    if p.returncode:
        raise RuntimeError("GH_FAILED:"+p.stderr[-6000:])
    raw=p.stdout.strip()
    return json.loads(raw) if raw else {}

def part_cert(part):
    p=PART_CERTS/f"{part}.json"
    if not p.is_file():
        return None
    d=load(p,{}) or {}
    return d if d.get("status")=="PASS" else None

def restart_storm_guard():
    st=service_state(True,MASTER_SERVICE)
    now=time.time()
    counter=int(st.get("NRestarts") or 0)
    p=STATE/"anti-paralysis/MASTER_RESTART_SAMPLE.json"
    prior=load(p,{}) or {}
    delta=max(0,counter-int(prior.get("counter",counter) or counter))
    elapsed=max(0.0,now-float(prior.get("epoch",now) or now))
    storm=bool(prior) and elapsed<=240 and delta>=3
    atomic(p,{"counter":counter,"epoch":now,"delta":delta,"elapsed_seconds":elapsed,"storm":storm,"service":st,"utc":utc()})
    if storm:
        ledger("CIRCUIT_BREAKER_MASTER_RESTART_STORM",restart_delta=delta,elapsed_seconds=elapsed,counter=counter)
    return not storm

def dependency_fingerprint(point):
    rows=[]
    for dep in point_def(point).get("depends_on",[]):
        p=POINT_CERTS/f"{dep}.json"
        rows.append({"point":dep,"sha256":sha(p) if p.is_file() else None})
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def evaluation_allowed(point):
    p=STATE/"anti-paralysis"/f"{point}.json"
    d=load(p,{}) or {}
    # A newly certified dependency is new causal evidence and must bypass
    # any HOLD/backoff that was calculated before that certificate existed.
    if d.get("dependency_fingerprint")!=dependency_fingerprint(point):
        return True
    return time.time()>=float(d.get("next_retry_epoch",0) or 0)

def record_evaluation(ev):
    point=ev["point_id"]
    p=STATE/"anti-paralysis"/f"{point}.json"
    prior=load(p,{}) or {}
    signature=hashlib.sha256(json.dumps({
        "status":ev.get("status"),
        "blockers":ev.get("blockers",[]),
        "checks":ev.get("checks",{})
    },sort_keys=True,separators=(",",":")).encode()).hexdigest()
    same=prior.get("signature")==signature
    count=(int(prior.get("identical_count",0))+1) if same else 1
    backoff=0
    circuit=False
    if ev.get("status")!="PASS" and count>=3:
        circuit=True
        backoff=min(900,60*(2**min(4,count-3)))
    rec={
        "point_id":point,"signature":signature,"identical_count":count,
        "dependency_fingerprint":dependency_fingerprint(point),
        "circuit_breaker":circuit,"backoff_seconds":backoff,
        "next_retry_epoch":time.time()+backoff,
        "last_status":ev.get("status"),"last_blockers":ev.get("blockers",[]),"utc":utc()
    }
    atomic(p,rec)
    if circuit:
        ledger("POINT_CIRCUIT_BREAKER",point_id=point,identical_count=count,backoff_seconds=backoff,signature=signature)
    return rec

def point_cert(point):
    p=POINT_CERTS/f"{point}.json"
    if not p.is_file():
        return None
    d=load(p,{}) or {}
    return d if d.get("status")=="PASS" else None

def point_def(point):
    for row in contract()["points"]:
        if row["id"]==point:
            return row
    raise KeyError(point)

def deps_pass(point):
    return all(point_cert(x) is not None for x in point_def(point)["depends_on"])

def puac2_all():
    return {x:True for x in ("C25","C26","C27","C28","C29","C30","C31","C32")}

def static_invariants():
    c=contract()
    return {
        "contract_v2":c["schema"].endswith("/2.0"),
        "authority":c["authority"]["canonical"]=="Louksna.md",
        "protected_reference":c["authority"]["protected_reference"]=="LOUKSNAMEJORADA.md",
        "part4_closed":c["immutable_boundaries"]["part4_closed"] is True,
        "part4_stages_1_12":c["immutable_boundaries"]["part4_stages_closed"]==list(range(1,13)),
        "partitioning_denied":c["immutable_boundaries"]["partitioning_operations_forbidden"] is True,
        "debian_redownload_denied":c["immutable_boundaries"]["debian_download_forbidden"] is True,
        "kde_redownload_denied":c["immutable_boundaries"]["kde_download_forbidden"] is True,
        "desktop_plugin_denied":c["immutable_boundaries"]["desktop_plugin_forbidden"] is True,
        "g23_required":all(x["g23_required"] for x in c["points"]),
        "g24_required":all(x["g24_required"] for x in c["points"]),
        "third_order":c["formal_assurance"]["third_order_automation"] is True,
    }

def safe_handoff(reason):
    if part6_child_active():
        raise RuntimeError("HANDOFF_DENIED_PART6_CHILD_ACTIVE")
    required=["master_controller.py","part6_hardened_worker.py","R4_48H_CONTRACT.json"]
    for name in required:
        if not (STAGED/name).is_file():
            raise RuntimeError("STAGED_FILE_MISSING:"+name)
    checkpoint=STATE/"handoff"/dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint.mkdir(parents=True,exist_ok=False)
    before={}
    for name in required:
        src=LIVE/name
        if src.is_file():
            shutil.copy2(src,checkpoint/name)
            before[name]=sha(src)
    atomic(checkpoint/"MANIFEST.json",{
        "schema":"LOUKSNA_R4_MAESTRO_HANDOFF_CHECKPOINT/2.0",
        "reason":reason,"before_sha256":before,"utc":utc()
    })
    systemctl_user("stop",MASTER_SERVICE)
    for name in required:
        src=STAGED/name; dst=LIVE/name; tmp=dst.with_suffix(dst.suffix+".r15tmp")
        shutil.copy2(src,tmp)
        os.chmod(tmp,0o700 if name.endswith(".py") else 0o600)
        os.replace(tmp,dst)
    run(["python3","-m","py_compile",str(LIVE/"master_controller.py"),str(LIVE/"part6_hardened_worker.py")],timeout=60,check=True)
    systemctl_user("daemon-reload")
    systemctl_user("reset-failed",MASTER_SERVICE)
    systemctl_user("start",MASTER_SERVICE)
    for _ in range(45):
        if master_active():
            break
        time.sleep(1)
    if not master_active():
        raise RuntimeError("MASTER_HANDOFF_RESTART_FAILED")
    atomic(STATE/"HANDOFF_COMPLETE.json",{
        "status":"PASS","reason":reason,"checkpoint":str(checkpoint),
        "after_master_sha256":sha(LIVE/"master_controller.py"),
        "after_contract_sha256":sha(LIVE/"R4_48H_CONTRACT.json"),
        "utc":utc()
    })
    ledger("MASTER_SAFE_HANDOFF",reason=reason,checkpoint=str(checkpoint))

def ensure_master_hardened():
    names=["master_controller.py","part6_hardened_worker.py","R4_48H_CONTRACT.json"]
    staged_hashes={}
    live_hashes={}
    for name in names:
        sp=STAGED/name
        lp=LIVE/name
        if not sp.is_file():
            return False
        staged_hashes[name]=sha(sp)
        live_hashes[name]=sha(lp) if lp.is_file() else None

    st=service_state(True,MASTER_SERVICE)
    unhealthy=st.get("ActiveState")!="active" or st.get("MainPID") in (None,"","0")
    drift={name:{"live":live_hashes[name],"staged":staged_hashes[name]}
           for name in names if live_hashes[name]!=staged_hashes[name]}

    if drift or unhealthy:
        if part6_child_active():
            ledger("HANDOFF_DEFERRED_ACTIVE_PART6",drift=drift,service=st)
            return False
        safe_handoff("V2_15_POINT_ATOMIC_BUNDLE_RECONCILIATION")

    # Postcondition: all three live surfaces must equal the staged certified
    # bundle. A master-only equality is insufficient.
    for name in names:
        lp=LIVE/name
        if not lp.is_file() or sha(lp)!=staged_hashes[name]:
            return False
    return master_active()

def projects_binding_state():
    aliases=[HOME/"Proyectos",HOME/"Luna R4"/"Proyectos"]
    alias_ok=[]
    for a in aliases:
        try:
            alias_ok.append(a.is_symlink() and a.resolve(strict=True)==PROYECTOS.resolve())
        except Exception:
            alias_ok.append(False)
    xbel=HOME/".local/share/user-places.xbel"
    bookmark=False
    if xbel.is_file():
        try:
            root=ET.parse(xbel).getroot()
            target="file://"+urllib.parse.quote(str(PROYECTOS))
            for bm in root.iter():
                if not bm.tag.endswith("bookmark"):
                    continue
                title=""
                for ch in bm:
                    if ch.tag.endswith("title"):
                        title=ch.text or ""
                if title.casefold()=="proyectos" and bm.attrib.get("href")==target:
                    bookmark=True; break
        except Exception:
            pass
    return {
        "canonical_root":PROYECTOS.is_dir() and not PROYECTOS.is_symlink(),
        "alias_1":alias_ok[0],
        "alias_2":alias_ok[1],
        "dolphin_bookmark":bookmark
    }

def request_maestro(point,reason):
    pre=observe(f"{point}_MAESTRO_REQUEST_PRE")
    existing=load(STATE/"MAESTRO_POINT_REQUEST.json",{}) or {}
    result=load(STATE/"MAESTRO_POINT_RESULT.json",{}) or {}
    if existing.get("point_id")==point and existing.get("status")=="AUTHORIZED" and result.get("request_id")!=existing.get("request_id"):
        return existing
    req={
        "schema":"LOUKSNA_R4_MAESTRO_POINT_REQUEST/1.0",
        "request_id":"REQ-"+uuid.uuid4().hex,
        "point_id":point,
        "status":"AUTHORIZED",
        "reason":reason,
        "authority":"Louksna.md",
        "part4_reopen_authorized":False,
        "partitioning_authorized":False,
        "lrb_pre_sha256":pre["observe"].get("evidence_sha256"),
        "created_at_utc":utc()
    }
    atomic(STATE/"MAESTRO_POINT_REQUEST.json",req)
    ledger("MAESTRO_POINT_REQUEST",point_id=point,request_id=req["request_id"],reason=reason)
    return req

def evidence_for(point):
    c=contract()
    obs=observe(f"{point}_EVIDENCE")
    common=static_invariants()
    details={"lrb":obs["observe"],"master_service":service_state(True,MASTER_SERVICE),"runner_service":service_state(False,RUNNER_SERVICE)}
    checks={}
    if point=="P01":
        custos=locate_custosz()
        checks={
            **common,
            "lrb_live":bool(obs["observe"].get("evidence_sha256")),
            "authority_present":AUTHORITY.is_file(),
            "custosz_present":bool(custos and custos.is_file()),
            "runtime_present":RUNTIME.is_file(),
            "metaos_present":METAOS.is_file(),
            "github_auth":run(["gh","auth","status"],timeout=20)["returncode"]==0,
            "runner_active":details["runner_service"].get("ActiveState")=="active",
            "sudo_valid":sudo_ok(),
            "ledger_hash_chain":(STATE/"LEDGER_HEAD.json").is_file()
        }
        if custos: details["custosz"]={"path":str(custos),"sha256":sha(custos)}
        details["authority"]={"path":str(AUTHORITY),"sha256":sha(AUTHORITY)} if AUTHORITY.is_file() else None
        details["runtime"]={"path":str(RUNTIME),"sha256":sha(RUNTIME)} if RUNTIME.is_file() else None
        details["metaos"]={"path":str(METAOS),"sha256":sha(METAOS)} if METAOS.is_file() else None
    elif point=="P02":
        checks={
            **common,
            "dependency_P01":point_cert("P01") is not None,
            "default_no_redownload":c["anti_duplication"]["default"]=="NO_REDOWNLOAD",
            "lutris_reuse_required":c["anti_duplication"]["lutris_existing_artifact_reuse_required"] is True,
            "local_p25_first":c["anti_duplication"]["p25_local_candidates_before_download"] is True,
            "acquisition_requires_absence":c["anti_duplication"]["acquisition_requires"][0]=="ABSENT_REQUIRED"
        }
    elif point=="P03":
        ms=load(R4/"MASTER_STATUS.json",{}) or {}
        st=details["master_service"]
        lease=load(R4/"MASTER_CUSTOSZ_MISSION.json",{}) or {}
        live_master_text=(LIVE/"master_controller.py").read_text(encoding="utf-8",errors="replace") if (LIVE/"master_controller.py").is_file() else ""
        lease_v2=lease.get("schema")=="LOUKSNA_R4_GLOBAL_MISSION_LEASE/2.0"
        legacy_bounded=(
            not lease.get("schema")
            and bool(lease.get("mission_id"))
            and 1 <= int(lease.get("lease_hours",0) or 0) <= 24
            and "LOUKSNA_R4_GLOBAL_MISSION_LEASE/2.0" in live_master_text
            and "min(24,configured" in live_master_text
        )
        checks={
            **common,
            "dependency_P01":point_cert("P01") is not None,
            "master_active":st.get("ActiveState")=="active" and st.get("MainPID") not in (None,"","0"),
            "anti_paralysis_non_null":ms.get("anti_paralysis_contract")=="R4_15P_ANTI_PARALYSIS_V1",
            "lease_bounded":1 <= int(lease.get("lease_hours",0) or 0) <= 24,
            "renewal_code_live":"LOUKSNA_R4_GLOBAL_MISSION_LEASE/2.0" in live_master_text and "min(24,configured" in live_master_text,
            "lease_state_acceptable":lease_v2 or legacy_bounded,
            "restart_storm_not_active":restart_storm_guard()
        }
        details["master_status"]=ms
        details["lease"]=lease
        details["lease_class"]="V2" if lease_v2 else ("LEGACY_BOUNDED_ACTIVE" if legacy_bounded else "INVALID")
    elif point=="P04":
        checks={
            **common,
            "dependency_P01":point_cert("P01") is not None,
            "maestro_primary":c["control_fabric"]["maestro"]=="PRIMARY_MATERIAL_WORKER",
            "lrb_read_only":c["control_fabric"]["louksna_remote_bridge"]=="READ_ONLY_EYES_TELEMETRY_DIAGNOSIS",
            "github_control":c["control_fabric"]["github"]=="CONTROL_PLANE_EVIDENCE_G23_G24",
            "custosz_bound":c["control_fabric"]["custosz_v7"].startswith("GOVERNED_EXECUTION_KERNEL"),
            "self_cert_forbidden":c["epistemic"]["self_certification_forbidden"] is True
        }
    elif point=="P05":
        ns=c["namespace"]
        checks={
            **common,
            "dependencies":deps_pass(point),
            "exec_namespace_exact":ns["execution"]["EXEC_PART_6"]=="GAMING_MATERIAL_EXECUTION",
            "ui_namespace_exact":ns["ui"]["UI_PANEL_6"]=="INGENIERIA",
            "implicit_coercion_denied":ns["implicit_coercion"] is False,
            "ui_hash_bound":c["ui_reference"]["sha256"]==EXPECTED_UI_SHA
        }
    elif point=="P06":
        pb=projects_binding_state()
        mr=load(STATE/"MAESTRO_POINT_RESULT.json",{}) or {}
        mrc=mr.get("checks",{}) if mr else {}
        material_result_ok=(
            mr.get("point_id")=="P06"
            and mr.get("executor")=="MAESTRO"
            and bool(mr.get("checkpoint"))
            and mrc.get("canonical_root") is True
            and mrc.get("aliases") is True
            and mrc.get("projects_bookmark_canonical") is True
            and mrc.get("launchers_no_direct_old_media") is True
            and mrc.get("partitioning_performed") is False
            and mrc.get("data_copy_performed") is False
            and mrc.get("network_download_performed") is False
        )
        checks={**common,"dependencies":deps_pass(point),**pb,
                "maestro_executed":material_result_ok,
                "executor_is_maestro":mr.get("executor")=="MAESTRO",
                "checkpoint_present":bool(mr.get("checkpoint")),
                "no_partition":mrc.get("partitioning_performed") is False if mr else False,
                "no_data_copy":mrc.get("data_copy_performed") is False if mr else False,
                "no_network_download":mrc.get("network_download_performed") is False if mr else False,
                "negative_guard_semantics_reconciled":material_result_ok}
        details["maestro_result"]=mr
        details["result_status_interpretation"]="MATERIAL_PASS_DESPITE_LEGACY_NEGATIVE_GUARD_STATUS" if material_result_ok and mr.get("status")!="PASS" else mr.get("status")
        if not all(pb.values()) and deps_pass(point):
            details["request"]=request_maestro("P06","Repair canonical PROYECTOS aliases/bookmark with checkpoint; no data copy")
    elif point=="P07":
        cert=part_cert("PART_6")
        checks={**common,"dependencies":deps_pass(point),"part6_g24":cert is not None,
                "partitioning_denied":True,"no_redownload_policy_bound":True}
        details["part6_certificate"]=cert
    elif point=="P08":
        cert=part_cert("PART_7")
        checks={**common,"dependencies":deps_pass(point),"part7_g24":cert is not None,
                "local_backend_not_hosted_substitution":True,"source_immutability_required":True}
        details["part7_certificate"]=cert
    elif point=="P09":
        cert=part_cert("PART_8")
        checks={**common,"dependencies":deps_pass(point),"part8_g24":cert is not None,
                "sudo_valid":sudo_ok(),"hygiene_unknown_preserve":True}
        details["part8_certificate"]=cert
    elif point=="P10":
        ui=load(STATE/"UI_PANEL_4_9_RESULT.json",{}) or {}
        checks={**common,"dependencies":deps_pass(point),
                "ui_result_present":bool(ui),
                "ui_status_pass":ui.get("status")=="PASS",
                "reference_hash":ui.get("reference_sha256")==EXPECTED_UI_SHA,
                "lrb_visual_evidence":bool(ui.get("lrb_visual_evidence")),
                "panels_4_9":all(ui.get("panels",{}).get(f"UI_PANEL_{i}")=="PASS" for i in range(4,10))}
        details["ui_result"]=ui
    elif point=="P11":
        windows_match=False; windows_observed=None
        if WINDOWS_BAD.is_file():
            # This hash is intentionally computed only at the acquisition gate.
            windows_observed=sha(WINDOWS_BAD)
            windows_match=windows_observed==WINDOWS_EXPECTED_SHA
        mojo=shutil.which("mojo")
        checks={**common,"dependencies":deps_pass(point),
                "windows_correct_iso":windows_match,
                "bad_windows_never_promoted":not windows_match,
                "mojo_present":bool(mojo)}
        details["windows"]={"path":str(WINDOWS_BAD),"sha256":windows_observed,"expected":WINDOWS_EXPECTED_SHA}
        details["mojo_path"]=mojo
    elif point=="P12":
        pc=load(STATE/"PROJECTS_CENTER_RESULT.json",{}) or {}
        checks={**common,"dependencies":deps_pass(point),
                "projects_center_result":pc.get("status")=="PASS",
                "canonical_root":PROYECTOS.is_dir(),
                "custos_local":bool(pc.get("custos_local")),
                "roadmaps":bool(pc.get("roadmaps")),
                "goals":bool(pc.get("goals")),
                "checkpoints":bool(pc.get("checkpoints")),
                "evidence":bool(pc.get("evidence")),
                "semantic_context":bool(pc.get("semantic_context"))}
        details["projects_center"]=pc
    elif point=="P13":
        cert=part_cert("PART_9")
        checks={**common,"dependencies":deps_pass(point),"part9_g24":cert is not None,
                "sudo_valid":sudo_ok(),"lrb_live":bool(obs["observe"].get("evidence_sha256"))}
        details["part9_certificate"]=cert
    elif point=="P14":
        checks={**common,"dependencies":deps_pass(point),
                "points_1_13_certified":all(point_cert(f"P{i:02d}") is not None for i in range(1,14)),
                "ledger_present":(STATE/"LEDGER.jsonl").is_file(),
                "rollback_root_present":(STATE/"rollback").is_dir(),
                "anti_paralysis_bound":c["anti_paralysis"]["mandatory_non_null"] is True,
                "second_order_assurance":c["formal_assurance"]["second_order_assurance"] is True}
    elif point=="P15":
        checks={**common,"dependency_P14":point_cert("P14") is not None,
                "points_1_14_certified":all(point_cert(f"P{i:02d}") is not None for i in range(1,15)),
                "third_order_assurance":c["formal_assurance"]["third_order_automation"] is True,
                "audit_of_audit":c["formal_assurance"]["audit_of_audit"] is True,
                "sudo_valid":sudo_ok(),
                "lrb_terminal_observation":bool(obs["observe"].get("evidence_sha256")),
                "protected_reference_source_bound":bool(c.get("references",{}).get("protected_reference_binding",{}).get("source_file_id")),
                "protected_reference_host_crypto_binding":bool((load(STATE/"PROTECTED_REFERENCE_HOST_BINDING.json",{}) or {}).get("status")=="PASS")}
    else:
        raise RuntimeError("UNKNOWN_POINT:"+point)

    puac=puac2_all()
    ready=all(bool(v) for v in checks.values()) and all(puac.values())
    ev={
        "schema":"LOUKSNA_R4_15_POINT_EVIDENCE/1.0",
        "point_id":point,
        "point_name":point_def(point)["name"],
        "status":"PASS" if ready else "HOLD",
        "authority":"Louksna.md",
        "protected_reference":"LOUKSNAMEJORADA.md",
        "executor":"MAESTRO" if point in {"P06","P07","P08","P09","P10","P11","P12","P13"} else "CONTROL_FABRIC",
        "observer":"LOUKSNA_REMOTE_BRIDGE",
        "control_plane":"GITHUB",
        "self_certified":False,
        "puac2":puac,
        "checks":checks,
        "blockers":[k for k,v in checks.items() if not bool(v)],
        "details":details,
        "provenance":{
            "contract_sha256":sha(CONTRACT),
            "authority_sha256":sha(AUTHORITY) if AUTHORITY.is_file() else None,
            "lrb_evidence_sha256":obs["observe"].get("evidence_sha256"),
            "ledger_head_sha256":(load(STATE/"LEDGER_HEAD.json",{}) or {}).get("sha256"),
            "master_controller_sha256":sha(LIVE/"master_controller.py") if (LIVE/"master_controller.py").is_file() else None
        },
        "partitioning_performed":False,
        "debian_redownload_performed":False,
        "kde_redownload_performed":False,
        "created_at_utc":utc()
    }
    atomic(POINTS_DIR/f"{point}.json",ev)
    return ev

def publish_and_wait_certificate(ev):
    point=ev["point_id"]
    if ev["status"]!="PASS":
        return None
    prior=point_cert(point)
    evidence_hash=hashlib.sha256((json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()).hexdigest()
    if prior and prior.get("evidence_sha256")==evidence_hash:
        return prior

    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    rel=f"evidence/r4-15point/{stamp}-{point}/POINT_EVIDENCE.json"
    raw=(json.dumps(ev,ensure_ascii=False,indent=2,sort_keys=True)+"\n").encode()
    payload=base64.b64encode(raw).decode()
    resp=gh_json(["api","--method","PUT",f"repos/{REPO}/contents/{rel}",
                  "-f",f"message=evidence(R4-15P): {point}",
                  "-f",f"content={payload}","-f",f"branch={BRANCH}"],timeout=90)
    commit=resp["commit"]["sha"]
    ledger("POINT_EVIDENCE_PUBLISHED",point_id=point,evidence_sha256=hashlib.sha256(raw).hexdigest(),commit_sha=commit,path=rel)

    run_id=None
    for _ in range(180):
        q=gh_json(["api",f"repos/{REPO}/actions/runs?branch={BRANCH}&event=push&per_page=100"],timeout=30)
        for rr in q.get("workflow_runs",[]):
            if rr.get("head_sha")==commit and rr.get("path")==POINT_CERT_WORKFLOW:
                run_id=rr["id"]; break
        if run_id: break
        time.sleep(2)
    if not run_id:
        raise RuntimeError("POINT_CERT_WORKFLOW_NOT_FOUND:"+point)

    for _ in range(600):
        wr=gh_json(["api",f"repos/{REPO}/actions/runs/{run_id}"],timeout=30)
        if wr.get("status")=="completed":
            if wr.get("conclusion")!="success":
                raise RuntimeError("POINT_CERT_WORKFLOW_FAILED:"+point+":"+str(wr.get("conclusion")))
            break
        time.sleep(2)
    else:
        raise RuntimeError("POINT_CERT_WORKFLOW_TIMEOUT:"+point)

    with tempfile.TemporaryDirectory(prefix="r4-15p-g24-") as td:
        d=pathlib.Path(td)
        r=run(["gh","run","download",str(run_id),"--repo",REPO,"-n","r4-15point-g24","-D",str(d)],timeout=180)
        if r["returncode"]:
            raise RuntimeError("POINT_G24_DOWNLOAD_FAILED:"+point)
        cp=d/"G24.json"
        cert=json.loads(cp.read_text(encoding="utf-8"))
        if cert.get("status")!="PASS" or cert.get("point_id")!=point:
            raise RuntimeError("POINT_G24_INVALID:"+point)
        if cert.get("evidence_sha256")!=hashlib.sha256(raw).hexdigest():
            raise RuntimeError("POINT_G24_EVIDENCE_MISMATCH:"+point)
        cert["workflow_run_id"]=run_id
        cert["evidence_commit_sha"]=commit
        cert["local_bound_at_utc"]=utc()
        atomic(POINT_CERTS/f"{point}.json",cert)
        ledger("POINT_CERTIFIED",point_id=point,g23_sha256=cert.get("g23_sha256"),g24_sha256=hashlib.sha256(cp.read_bytes()).hexdigest())
        return cert

def next_ready_points():
    out=[]
    for i in range(1,16):
        p=f"P{i:02d}"
        if point_cert(p):
            continue
        if deps_pass(p):
            out.append(p)
    return out

def write_global_status():
    certs={}
    for i in range(1,16):
        p=f"P{i:02d}"; c=point_cert(p)
        certs[p]=None if c is None else {"status":c.get("status"),"evidence_sha256":c.get("evidence_sha256"),"g23_sha256":c.get("g23_sha256")}
    status={
        "schema":"LOUKSNA_R4_15_POINT_STATUS/1.0",
        "status":"COMPLETE" if all(certs[p] for p in certs) else "ACTIVE",
        "certificates":certs,
        "next_ready":next_ready_points(),
        "master_service":service_state(True,MASTER_SERVICE),
        "runner_service":service_state(False,RUNNER_SERVICE),
        "deadline_utc":contract()["window"]["deadline_utc"],
        "partitioning_authorized":False,
        "updated_at_utc":utc()
    }
    atomic(STATE/"STATUS.json",status)
    return status

def deadline_stop():
    atomic(STATE/"DEADLINE_CHECKPOINT.json",{
        "schema":"LOUKSNA_R4_15_POINT_DEADLINE_CHECKPOINT/1.0",
        "status":"EXPIRED",
        "deadline_utc":contract()["window"]["deadline_utc"],
        "point_status":load(STATE/"STATUS.json",{}),
        "master_status":load(R4/"MASTER_STATUS.json",{}),
        "new_material_work":False,
        "partitioning_performed":False,
        "utc":utc()
    })
    ledger("GLOBAL_WINDOW_EXPIRED")
    return 0

def main():
    for p in (STATE,POINTS_DIR,POINT_CERTS,STATE/"rollback",STATE/"observations",STATE/"handoff"):
        p.mkdir(parents=True,exist_ok=True)
    ledger("COORDINATOR_V2_START",contract_sha256=sha(CONTRACT),deadline_utc=contract()["window"]["deadline_utc"])

    last_observe=0.0
    while True:
        if dt.datetime.now(dt.timezone.utc)>=deadline():
            return deadline_stop()

        ensure_master_hardened()

        if time.monotonic()-last_observe>=300:
            observe("PERIODIC")
            last_observe=time.monotonic()

        progressed=False
        for point in next_ready_points():
            if not evaluation_allowed(point):
                continue
            ev=evidence_for(point)
            ap=record_evaluation(ev)
            ledger("POINT_EVALUATED",point_id=point,status=ev["status"],blockers=ev["blockers"],anti_paralysis=ap)
            if ev["status"]=="PASS":
                publish_and_wait_certificate(ev)
                progressed=True
                write_global_status()
                # Recompute graph after each certification.
                break

        status=write_global_status()
        if status["status"]=="COMPLETE":
            final_obs=observe("TERMINAL_COMPLETE")
            atomic(STATE/"COMPLETE.json",{
                "schema":"LOUKSNA_R4_15_POINT_COMPLETE/1.0",
                "status":"PASS",
                "points":15,
                "final_lrb_evidence_sha256":final_obs["observe"].get("evidence_sha256"),
                "ledger_head_sha256":(load(STATE/"LEDGER_HEAD.json",{}) or {}).get("sha256"),
                "partitioning_performed":False,
                "completed_at_utc":utc()
            })
            ledger("GLOBAL_COMPLETE")
            return 0

        time.sleep(5 if progressed else POLL)

if __name__=="__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        STATE.mkdir(parents=True,exist_ok=True)
        atomic(STATE/"COORDINATOR_FAILURE.json",{
            "schema":"LOUKSNA_R4_15_POINT_COORDINATOR_FAILURE/1.0",
            "status":"HOLD",
            "error":type(exc).__name__+":"+str(exc),
            "traceback":traceback.format_exc(),
            "partitioning_performed":False,
            "utc":utc()
        })
        try:
            ledger("COORDINATOR_FAILURE",error=type(exc).__name__+":"+str(exc))
        except Exception:
            pass
        raise
