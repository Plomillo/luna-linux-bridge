#!/usr/bin/env python3
import json, os, sys, time
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(os.environ["GITHUB_WORKSPACE"]).resolve()
MISSION_ROOT = ROOT / "mission"
CUSTOSZ = MISSION_ROOT / "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
MISSION_FILE = MISSION_ROOT / "missions/inbox/dropbox-transfer-live-recovery-20261007/MISSION_ORIGINAL.md"

def utc():
    return datetime.now(timezone.utc).isoformat()

def main():
    if not MISSION_FILE.is_file():
        raise SystemExit("MISSION_FILE_MISSING")
    mission_text = MISSION_FILE.read_text(encoding="utf-8")
    workspace = Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).expanduser().resolve()
    if not workspace.is_dir():
        raise SystemExit("CUSTOSZ_WORKSPACE_MISSING")
    if not (workspace / "1. PROYECTOS PRIORITARIOS").is_dir():
        raise SystemExit("CUSTOSZ_WORKSPACE_INVALID")

    state = Path.home()/".local/state/louksna"/("custosz-dropbox-transfer-"+os.environ.get("GITHUB_RUN_ID","manual"))
    state.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"] = str(workspace)
    os.environ["CUSTOSZ_STATE_DIR"] = str(state)
    sys.path.insert(0, str(CUSTOSZ))
    import custosz_v05_legacy as worker

    worker.PINS = {k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES = {k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}

    goal = (
        "EJECUTAR la misión byte-exact adjunta para recuperar y mantener viva la transferencia Dropbox->GitHub "
        "de los pendientes 1,5,8 desde el checkpoint durable existente, sin reiniciar 2,3,4,6,7. "
        "CUSTOSZ V7 es trabajador/orquestador, CUSTOSZ_RUNTIME_V1 ejecuta materialmente y MetaOS gobierna. "
        "Monitorear telemetría real de GitHub Actions y corregir causalmente fallos hasta observar flujo material nuevo. "
        "Criterio de éxito inmediato: MATERIAL_BYTE_FLOW=TRUE y observed_bytes>0 atribuibles a 1,5 u 8. "
        "En cuanto exista esa señal, detener modificaciones y dejar que la transferencia continúe. "
        "Bloqueo conocido: descendant identity 6af31081a3ae592c678a06396745f8f3d6a617223f2b9796f53c7828102c0722. "
        "Último checkpoint: CP-37653596452-000008 hash c10e2a15127576d9f0884a6e64b72ba4e897fd4037cfdb7b62d9828a11a91c04. "
        "Último run fallido: 37653596452. Estado preservado: 5/8. "
        "GitHub artifact quota está agotada: no usar artifacts como único canal de evidencia; usar logs, issue y commits de texto. "
        "REGLA RAR: si aparece cualquier .rar, no inferir ni tratar su contenido como evidencia hasta que se produzca un documento UTF-8 "
        "de texto con inventario, hashes, rutas y contenido legible pertinente; preservar hash del RAR y reconciliar texto contra el archivo. "
        "Desktop Commander y Codex quedan prohibidos. No reiniciar desde cero. Fail closed. No inventar PASS/G23/G24."
    )
    m = worker.mission_start(6.0, "LUNA_PROJECT", goal + "\n\n" + mission_text, report_minutes=1)
    tick = worker.mission_tick(m["mission_id"])
    result = {
        "schema":"CUSTOSZ_DROPBOX_TRANSFER_HANDOFF/1.0",
        "status":"MISSION_REGISTERED",
        "mission_id":m["mission_id"],
        "registered_utc":utc(),
        "deadline_utc":m.get("deadline_utc"),
        "executor":m.get("executor"),
        "heartbeat_state":tick.get("state"),
        "worker":"CUSTOSZ_V7",
        "runtime":"CUSTOSZ_RUNTIME_V1",
        "governor":"MetaOS",
        "transfer_branch":"staging/dropbox-github-cloud-partitioned-20261005",
        "preserved_progress":"5/8",
        "pending":[1,5,8],
        "last_failed_run":37653596452,
        "checkpoint_id":"CP-37653596452-000008",
        "checkpoint_hash":"c10e2a15127576d9f0884a6e64b72ba4e897fd4037cfdb7b62d9828a11a91c04",
        "blocker_identity":"6af31081a3ae592c678a06396745f8f3d6a617223f2b9796f53c7828102c0722",
        "success_gate":"MATERIAL_BYTE_FLOW_TRUE_AND_OBSERVED_BYTES_GT_0_FOR_PENDING_1_5_8",
        "stop_mutation_on_success":True,
        "rar_text_gate":True,
        "desktop_commander":"FORBIDDEN",
        "codex":"FORBIDDEN",
        "state_dir":str(state)
    }
    out = Path(os.environ["RUNNER_TEMP"])/"CUSTOSZ_DROPBOX_TRANSFER_HANDOFF.json"
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,sort_keys=True))

if __name__ == "__main__":
    main()
