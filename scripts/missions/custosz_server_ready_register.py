#!/usr/bin/env python3
"""Register SERVER_READY issue #7 as a real bounded CUSTOSZ V7 mission."""
import hashlib, json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
CUSTOSZ=ROOT/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
MISSION=ROOT/"docs/missions/CUSTOSZ_V7_SERVER_READY_20M/MISION_SERVER_READY_FINAL.md"
MAX_SECONDS=1200.0

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def find_workspace():
    home=Path.home()
    candidates=[]
    for parent in (home,home/"Proyectos",home/"PROYECTOS",Path("/mnt"),Path("/media")):
        if not parent.is_dir():
            continue
        candidates.append(parent)
        try:
            candidates.extend(list(parent.iterdir())[:120])
        except OSError:
            pass
    found=[]
    for p in candidates:
        try:
            q=p.resolve()
            if (q/"1. PROYECTOS PRIORITARIOS").is_dir() and ((q/"4. PENDIENTES").exists() or (q/"2. CORPUS").exists()) and q not in found:
                found.append(q)
        except OSError:
            pass
    if len(found)!=1:
        raise RuntimeError("REAL_WORKSPACE_NOT_UNIQUELY_RESOLVED:"+repr([str(x) for x in found]))
    return found[0]

def main():
    started=time.monotonic()
    if not MISSION.is_file() or not CUSTOSZ.is_file():
        raise SystemExit("MISSION_OR_CUSTOSZ_MISSING")
    ws=find_workspace()
    state=Path.home()/".local/state/louksna"/("custosz-server-ready-"+os.environ.get("GITHUB_RUN_ID","manual"))
    state.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"]=str(ws)
    os.environ["CUSTOSZ_STATE_DIR"]=str(state)
    sys.path.insert(0,str(CUSTOSZ))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}
    mission_hash=sha(MISSION)
    goal=(
      "SERVER_READY issue #7. Fuente exacta docs/missions/CUSTOSZ_V7_SERVER_READY_20M/"
      "MISION_SERVER_READY_FINAL.md sha256="+mission_hash+". "
      "CUSTOSZ V7 trabajador; SYMPHYLAX R1 supervisor; MetaOS gobernador; CUSTOSZ_RUNTIME_V1 ejecutor gobernado. "
      "Techo global 1200 segundos desde RECEIPT_VERIFIED. Cooperacion por dominio. "
      "Contenedor semantico fuera de alcance. Solo correcciones aditivas, reversibles y no destructivas. "
      "Prohibido Windows/EFI/GPT/particiones/PROYECTOS/F3-DISK. "
      "Resultado SERVER_TECHNICAL_READY PASS o HOLD con SINGLE_ROOT_BLOCKER exacto."
    )
    m=worker.mission_start(MAX_SECONDS/3600.0,"LUNA_PROJECT",goal,report_minutes=1)
    tick=worker.mission_tick(m["mission_id"])
    receipt={
      "schema":"CUSTOSZ_SERVER_READY_RECEIPT/1.0",
      "status":"RECEIPT_VERIFIED",
      "issue":7,
      "mission_id":m["mission_id"],
      "registered_utc":utc(),
      "deadline_utc":m["deadline_utc"],
      "global_wallclock_max_seconds":1200,
      "mission_sha256":mission_hash,
      "source_commit":os.environ.get("GITHUB_SHA"),
      "workspace_resolved":True,
      "workspace":str(ws),
      "heartbeat_state":tick.get("state"),
      "executor":m.get("executor"),
      "state_dir":str(state),
      "elapsed_registration_seconds":round(time.monotonic()-started,3),
      "host_installation_authorized":False,
      "disk_mutation_authorized":False,
      "container_work":"FROZEN"
    }
    out=Path(os.environ["RUNNER_TEMP"])/"SERVER_READY_RECEIPT.json"
    out.write_text(json.dumps(receipt,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(receipt,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    raise SystemExit(main())
