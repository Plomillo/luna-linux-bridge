#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt, hashlib, json, os, pathlib, shutil, subprocess, time, traceback

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
STATE=HOME/".local/state/louksna/r4-48h"
R4=HOME/".local/state/louksna/r4-master-part1-part9"
CERTS=R4/"certificates"
LIVE=HOME/".local/lib/louksna/r4-master-part1-part9"
ROOT=HOME/".local/lib/louksna/r4-48h"
STAGED=ROOT/"staged"
CONTRACT=ROOT/"R4_48H_CONTRACT.json"
COMPANION=ROOT/"lrb_companion_worker.py"
MASTER_SERVICE="luna-r4-master-part1-part9.service"
POLL=10

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def load(p,default=None):
    try:return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:return default

def atomic(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(t,p)

def ledger(event,**kw):
    STATE.mkdir(parents=True,exist_ok=True)
    row={"utc":utc(),"event":event,**kw}
    with (STATE/"COORDINATOR.jsonl").open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n")
        f.flush(); os.fsync(f.fileno())
    return row

def contract():
    d=load(CONTRACT,{}) or {}
    if d.get("schema")!="LOUKSNA_R4_REMAINDER_48H_CONTRACT/1.0": raise RuntimeError("CONTRACT_INVALID")
    return d

def deadline():
    return dt.datetime.fromisoformat(contract()["window"]["deadline_utc"].replace("Z","+00:00"))

def cert(part):
    p=CERTS/f"{part}.json"
    if not p.is_file(): return False
    d=load(p,{}) or {}
    return d.get("status")=="PASS"

def proc_lines():
    p=subprocess.run(["ps","-eo","pid,ppid,etimes,args"],text=True,capture_output=True,timeout=20)
    return [x for x in p.stdout.splitlines() if any(k in x for k in ("master_controller.py","part6_hardened_worker.py","make build_name=louksna-proton")) and "maestro_48h_coordinator.py" not in x]

def part6_active():
    rows=proc_lines()
    return any("part6_hardened_worker.py" in x for x in rows) or any("make build_name=louksna-proton" in x for x in rows)

def systemctl_user(*args,check=False):
    p=subprocess.run(["systemctl","--user",*args],text=True,capture_output=True,timeout=60)
    if check and p.returncode: raise RuntimeError("SYSTEMCTL_FAILED:"+p.stderr[-1000:])
    return p

def master_active():
    return systemctl_user("is-active",MASTER_SERVICE).stdout.strip()=="active"

def run_companion(op):
    p=subprocess.run(["python3","-B",str(COMPANION),op],text=True,capture_output=True,timeout=1800)
    rec={"operation":op,"returncode":p.returncode,"stdout":p.stdout[-12000:],"stderr":p.stderr[-4000:]}
    ledger("COMPANION",**rec)
    return rec

def staged_digest(path):
    h=hashlib.sha256()
    with pathlib.Path(path).open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
    return h.hexdigest()

def safe_handoff(reason):
    if part6_active(): raise RuntimeError("HANDOFF_DENIED_PART6_CHILD_ACTIVE")
    required=["master_controller.py","part6_hardened_worker.py","R4_48H_CONTRACT.json"]
    for name in required:
        if not (STAGED/name).is_file(): raise RuntimeError("STAGED_FILE_MISSING:"+name)
    before={name:staged_digest(STAGED/name) for name in required}
    checkpoint=STATE/"handoff"/dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    checkpoint.mkdir(parents=True,exist_ok=False)
    for name in ["master_controller.py","part6_hardened_worker.py","R4_48H_CONTRACT.json"]:
        src=LIVE/name
        if src.is_file(): shutil.copy2(src,checkpoint/name)
    atomic(checkpoint/"MANIFEST.json",{"schema":"LOUKSNA_R4_48H_MASTER_HANDOFF_CHECKPOINT/1.0","reason":reason,"staged_sha256":before,"utc":utc()})
    systemctl_user("stop",MASTER_SERVICE,check=True)
    for name in required:
        src=STAGED/name; dst=LIVE/name; tmp=dst.with_suffix(dst.suffix+".r48tmp")
        shutil.copy2(src,tmp)
        os.chmod(tmp,0o700 if name.endswith(".py") else 0o600)
        os.replace(tmp,dst)
    subprocess.run(["python3","-m","py_compile",str(LIVE/"master_controller.py"),str(LIVE/"part6_hardened_worker.py")],check=True,timeout=60)
    systemctl_user("daemon-reload",check=True)
    systemctl_user("reset-failed",MASTER_SERVICE)
    systemctl_user("start",MASTER_SERVICE,check=True)
    for _ in range(30):
        if master_active():break
        time.sleep(1)
    if not master_active(): raise RuntimeError("MASTER_RESTART_FAILED")
    atomic(STATE/"HANDOFF_COMPLETE.json",{"status":"PASS","reason":reason,"checkpoint":str(checkpoint),"staged_sha256":before,"utc":utc()})
    ledger("MASTER_SAFE_HANDOFF",reason=reason,checkpoint=str(checkpoint),staged_sha256=before)

def deadline_stop():
    ms=load(R4/"MASTER_STATUS.json",{}) or {}
    rows=proc_lines()
    atomic(STATE/"DEADLINE_CHECKPOINT.json",{
      "schema":"LOUKSNA_R4_48H_DEADLINE_CHECKPOINT/1.0","status":"EXPIRED",
      "deadline_utc":contract()["window"]["deadline_utc"],"master_status":ms,
      "processes":rows,"certificates":sorted(p.name for p in CERTS.glob("PART_*.json")),
      "new_material_work":False,"partitioning_performed":False,"utc":utc()
    })
    if master_active():
        systemctl_user("stop",MASTER_SERVICE)
    ledger("DEADLINE_STOP",master_was_active=master_active(),processes=rows)

def action_once(name,op,prereq=None):
    stamp=STATE/"actions"/(name+".json")
    if stamp.is_file() and (load(stamp,{}) or {}).get("status")=="PASS": return True
    if prereq and not prereq(): return False
    rec=run_companion(op)
    status="PASS" if rec["returncode"]==0 else "HOLD"
    atomic(stamp,{"status":status,"operation":op,"returncode":rec["returncode"],"utc":utc()})
    return status=="PASS"

def main():
    STATE.mkdir(parents=True,exist_ok=True)
    c=contract()
    ledger("COORDINATOR_START",deadline_utc=c["window"]["deadline_utc"],roles=c["roles"],part4_closed=True)
    part6_idle_since=None
    hardened=False
    last_telemetry=0.0
    while True:
        now=dt.datetime.now(dt.timezone.utc)
        if now>=deadline():
            deadline_stop()
            return 0

        if time.monotonic()-last_telemetry>=600:
            run_companion("telemetry")
            last_telemetry=time.monotonic()

        # Never interrupt the active Proton build.
        p6child=part6_active()
        c6=cert("PART_6")
        if p6child:
            part6_idle_since=None
            ledger("PART6_BUILD_PRESERVED",processes=proc_lines())
            time.sleep(POLL)
            continue

        if c6 and not hardened:
            safe_handoff("PART6_G24_SAFE_TRANSITION")
            hardened=True
            action_once("references","references")
            action_once("projects_ui","repair_projects_ui",lambda:cert("PART_6"))
            action_once("part7_evidence","part7_evidence",lambda:cert("PART_6"))
            time.sleep(POLL)
            continue

        if not c6:
            # Worker disappeared without certification. Give the old Maestro a grace period
            # to ingest RESULT/G23/G24 before any safe restart.
            if part6_idle_since is None:
                part6_idle_since=time.monotonic()
                ledger("PART6_IDLE_GRACE_START")
            elif time.monotonic()-part6_idle_since>=180 and not hardened:
                safe_handoff("PART6_WORKER_EXITED_WITHOUT_G24_REUSE_EXISTING_BYTES")
                hardened=True
                part6_idle_since=None
            time.sleep(POLL)
            continue

        # If this coordinator was restarted after the handoff, infer hardened state
        # from the durable marker rather than restarting Maestro again.
        if not hardened and (STATE/"HANDOFF_COMPLETE.json").is_file():
            hardened=True

        if c6 and not cert("PART_7"):
            action_once("projects_ui","repair_projects_ui",lambda:cert("PART_6"))
            action_once("part7_evidence","part7_evidence",lambda:cert("PART_6"))
        elif cert("PART_7") and not cert("PART_8"):
            action_once("part8_evidence","part8_evidence",lambda:cert("PART_7"))
        elif cert("PART_8") and not cert("PART_9"):
            action_once("part9_matrix","part9_matrix",lambda:cert("PART_8"))
        elif cert("PART_9"):
            atomic(STATE/"COMPLETE.json",{
              "schema":"LOUKSNA_R4_48H_COMPLETE/1.0","status":"PASS",
              "completed_before_deadline":now<deadline(),"deadline_utc":c["window"]["deadline_utc"],
              "certificates":sorted(p.name for p in CERTS.glob("PART_*.json")),
              "partitioning_performed":False,"utc":utc()
            })
            ledger("COMPLETE")
            return 0
        time.sleep(POLL)

if __name__=="__main__":
    try: raise SystemExit(main())
    except Exception as exc:
        STATE.mkdir(parents=True,exist_ok=True)
        atomic(STATE/"COORDINATOR_FAILURE.json",{
          "status":"HOLD","error":type(exc).__name__+":"+str(exc),
          "traceback":traceback.format_exc(),"utc":utc()
        })
        ledger("COORDINATOR_FAILURE",error=type(exc).__name__+":"+str(exc))
        raise
