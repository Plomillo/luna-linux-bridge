#!/usr/bin/env python3
"""Register a bounded continuation mission in the real CUSTOSZ V7 state.
Tiny host-side operation only: no installation, no disk mutation, no research workload.
Heavy research is delegated to GitHub-hosted compute by a separate workflow.
"""
import json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
CUSTOSZ=ROOT/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
PARENT="MIS-31e208fc59964c059f03"
ACTIVE_SECONDS_ALREADY=2.198
REMAINING=max(1.0,1200.0-ACTIVE_SECONDS_ALREADY-5.0)

def utc():
    return datetime.now(timezone.utc).isoformat()

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
    ws=find_workspace()
    state=Path.home()/".local/state/louksna"/("custosz-r4-cont-"+os.environ.get("GITHUB_RUN_ID","manual"))
    state.mkdir(parents=True,mode=0o700,exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"]=str(ws)
    os.environ["CUSTOSZ_STATE_DIR"]=str(state)
    sys.path.insert(0,str(CUSTOSZ))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]) for k,v in worker.PROFILES.items()}
    goal=(
      "CONTINUACION AUTORIZADA de "+PARENT+
      ": completar la investigacion maestra LUNA R4 enviada en GitHub issue #5. "
      "CUSTOSZ V7 supervisa; el trabajo pesado se ejecuta en GitHub-hosted mediante CUSTOSZ_RUNTIME_V1. "
      "Maximo activo acumulado 20 minutos. Sin instalacion, sin F3-DISK, sin Windows/EFI/GPT/PROYECTOS mutation. "
      "Publicar resultados exactos y pendientes en README."
    )
    m=worker.mission_start(REMAINING/3600.0,"LUNA_PROJECT",goal,report_minutes=1)
    tick=worker.mission_tick(m["mission_id"])
    result={
      "status":"CONTINUATION_MISSION_REGISTERED",
      "parent_mission_id":PARENT,
      "mission_id":m["mission_id"],
      "registered_utc":utc(),
      "deadline_utc":m["deadline_utc"],
      "active_budget_seconds_remaining":round(REMAINING,3),
      "elapsed_registration_seconds":round(time.monotonic()-started,3),
      "workspace_resolved":True,
      "heartbeat_state":tick.get("state"),
      "executor":m.get("executor"),
      "heavy_research_location":"GITHUB_HOSTED_ONLY",
      "host_installation_authorized":False,
      "disk_mutation_authorized":False,
      "state_dir":str(state)
    }
    out=Path(os.environ["RUNNER_TEMP"])/"CUSTOSZ_CONTINUATION.json"
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
