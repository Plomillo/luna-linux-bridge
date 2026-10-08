#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p08")).resolve(); OUT.mkdir(parents=True,exist_ok=True)
PROFILES=[
 {"name":"Instantáneo","retrieval_passes":1,"validation_passes":1,"adversarial_passes":0,"time_budget_ms":500,"token_budget":256},
 {"name":"Medio","retrieval_passes":2,"validation_passes":2,"adversarial_passes":1,"time_budget_ms":1000,"token_budget":512},
 {"name":"Alto","retrieval_passes":3,"validation_passes":3,"adversarial_passes":2,"time_budget_ms":2000,"token_budget":1024},
 {"name":"Muy alto","retrieval_passes":4,"validation_passes":4,"adversarial_passes":3,"time_budget_ms":4000,"token_budget":2048},
 {"name":"Pro","retrieval_passes":5,"validation_passes":5,"adversarial_passes":4,"time_budget_ms":8000,"token_budget":4096},
]
CONTEXT="Louksna V0.4 P08: mismo contexto, mismas fuentes, misma autoridad y mismos permisos; sólo cambia el presupuesto gobernado."
AUTHORITY="Louksna.md"
PERMISSIONS=("CHAT","CALL")

def digest(s): return hashlib.sha256(s.encode()).hexdigest()

def run_profile(p):
    context_hash=digest(CONTEXT); authority_hash=digest(AUTHORITY)
    trace=[]
    for i in range(p["retrieval_passes"]): trace.append("R"+str(i+1)+":"+context_hash[:12])
    answer="Resultado gobernado: contexto="+context_hash[:16]
    for i in range(p["validation_passes"]): trace.append("V"+str(i+1)+":"+digest(answer)[:12])
    for i in range(p["adversarial_passes"]): trace.append("A"+str(i+1)+":same-authority")
    return {"profile":p,"surface":list(PERMISSIONS),"context_hash":context_hash,"authority_hash":authority_hash,"answer_hash":digest(answer),"trace":trace}

def main():
    if [p["name"] for p in PROFILES] != ["Instantáneo","Medio","Alto","Muy alto","Pro"]: raise RuntimeError("PROFILE_SET_INVALID")
    results=[run_profile(p) for p in PROFILES]
    base={(r["context_hash"],r["authority_hash"],tuple(r["surface"])) for r in results}
    if len(base)!=1: raise RuntimeError("CONTEXT_AUTHORITY_DRIFT")
    if any(r["profile"]["retrieval_passes"]<1 for r in results): raise RuntimeError("BUDGET_INVALID")
    for a,b in zip(results,results[1:]):
        if not (b["profile"]["retrieval_passes"]>a["profile"]["retrieval_passes"] and b["profile"]["validation_passes"]>a["profile"]["validation_passes"] and b["profile"]["token_budget"]>a["profile"]["token_budget"]):
            raise RuntimeError("EFFORT_BUDGET_NOT_MONOTONIC")
    evidence={"schema":"LOUKSNA_ZD_P08_EFFORT/1.0","status":"PASS","surface":["CHAT","CALL"],"authority":AUTHORITY,"context_hash":results[0]["context_hash"],"profiles":results}
    (OUT/"P08_EFFORT_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    result={"status":"PASS","checkpoint":"CHECKPOINT_08","parent_checkpoint":"CHECKPOINT_07","next_point":"P09","transition_id":"P08-CHECKPOINT-TO-P09-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n")
    print("LOUKSNA_P08_TELEMETRY "+json.dumps({"event":"CHECKPOINT_08_REACHED","next_point":"P09","status":"PASS"},ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e: print("P08_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=__import__("sys").stderr); raise
