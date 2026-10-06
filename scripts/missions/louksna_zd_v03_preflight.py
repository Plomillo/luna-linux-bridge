#!/usr/bin/env python3
from pathlib import Path
import json,sys,hashlib

if len(sys.argv)!=5:
    raise SystemExit("usage: preflight.py <candidate> <monolith> <mission> <out>")
candidate=Path(sys.argv[1])
monolith=Path(sys.argv[2])
mission=Path(sys.argv[3])
out=Path(sys.argv[4])

def sha(p):
    h=hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

ui=(candidate/"src"/"App.tsx").read_text(encoding="utf-8")
spec=monolith.read_text(encoding="utf-8")
mis=mission.read_text(encoding="utf-8")

required_spec=[
 "FASE 2 — BACKEND LOCAL",
 "FASE 3 — GITHUB READ-ONLY",
 "SQLite",
 "Secret Service / libsecret",
 "GitHub REST API",
 "config persistente",
 "read repositories",
 "read PRs",
 "evidence ledger writes"
]
missing=[x for x in required_spec if x not in spec]
if missing:
    raise SystemExit("SPEC_CONTRACT_MISSING:"+",".join(missing))

required_mission=[
 "V0.3 FUNCIONAL",
 "GitHub READ-ONLY real",
 "settings persistentes",
 "ledger de evidencia",
 "LOUKSNA_ONLY",
 "No declarar GitHub sincronizado salvo respuesta API real"
]
mm=[x for x in required_mission if x not in mis]
if mm:
    raise SystemExit("MISSION_CONTRACT_MISSING:"+",".join(mm))

static_signals={
 "github_static_sync":"SINCRONIZADO" in ui,
 "static_pr_g23":"PENDIENTE" in ui and "G23" in ui,
 "visible_worker":"CUSTOSZ V7" in ui,
 "visible_runtime":"CUSTOSZ_RUNTIME_V1" in ui,
 "no_tauri_invoke":"@tauri-apps/api/core" not in ui,
}
open_gates=[
 "LOCAL_SQLITE_BACKEND",
 "PERSISTENT_SETTINGS",
 "SECRET_SERVICE_TOKEN_STORE",
 "GITHUB_REAL_CONNECTION",
 "GITHUB_REAL_REPOSITORIES",
 "GITHUB_REAL_PULL_REQUESTS",
 "LIVE_EVIDENCE_LEDGER",
 "CHAT_REMOTE_ROUND_TRIP",
 "VOICE_END_TO_END"
]
obj={
 "schema":"LOUKSNA_ZD_V03_FUNCTIONAL_PREFLIGHT/1.0",
 "status":"PASS",
 "baseline_candidate_sha256":sha(candidate/"src"/"App.tsx"),
 "spec_sha256":sha(monolith),
 "mission_sha256":sha(mission),
 "observed_v02_static_signals":static_signals,
 "open_gates":open_gates,
 "next_authorized_stage":"IMPLEMENT_LOCAL_BACKEND_AND_GITHUB_READ_ONLY",
 "identity":"LOUKSNA_ONLY",
 "active":False,
 "certification_propagated":False
}
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
print("TELEMETRY V03_PREFLIGHT=PASS")
for k,v in static_signals.items():
    print("TELEMETRY V02_"+k.upper()+"="+str(v).upper())
print("TELEMETRY NEXT_STAGE=IMPLEMENT_LOCAL_BACKEND_AND_GITHUB_READ_ONLY")
print("TELEMETRY ACTIVE=FALSE")
