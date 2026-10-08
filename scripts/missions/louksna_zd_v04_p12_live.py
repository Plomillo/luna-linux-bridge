#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p12")).resolve(); OUT.mkdir(parents=True,exist_ok=True)

def sh(cmd,timeout=900):
    r=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=timeout)
    return {"returncode":r.returncode,"stdout":r.stdout[-12000:],"stderr":r.stderr[-12000:]}

def sha256_text(s): return hashlib.sha256(s.encode()).hexdigest()

def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    mission=(ROOT/"missions/inbox/louksna-zd-v04-master-20261007/MISSION_ORIGINAL.md").read_text()
    puac=(ROOT/"PUAC2.md").read_text()
    blockers=list(state.get("open_blockers",[]))
    checks=[]

    if "G23" not in mission or "G24" not in mission: raise RuntimeError("P12_CERTIFICATION_CHAIN_NOT_DECLARED")
    if "ACTIVE únicamente" not in mission: raise RuntimeError("P12_ACTIVE_GATE_MISSING")

    # Exact-source and repository integrity gate.
    for path,expected in [("Louksna.md","1a399ab7494d6df5582436819eee557083e753ed"),
                          ("PUAC2.md","da3b216888c86e588685d384c34dd3c481414b22")]:
        r=sh(["git","rev-parse","HEAD:"+path])
        if r["returncode"] or r["stdout"].strip()!=expected: raise RuntimeError("P12_FROZEN_SOURCE_MISMATCH:"+path)
        checks.append({"test":"FROZEN_SOURCE","path":path,"status":"PASS","blob":expected})

    # Release substrate: no canonical mutation and exact branch identity.
    head=sh(["git","rev-parse","HEAD"]); branch=sh(["git","branch","--show-current"])
    if head["returncode"] or branch["stdout"].strip()!="work/louksna-zd-v04-master-20261007": raise RuntimeError("P12_BRANCH_IDENTITY")
    checks.append({"test":"RELEASE_SOURCE_IDENTITY","status":"PASS","commit":head["stdout"].strip(),"branch":branch["stdout"].strip()})

    # Build-system presence is checked without inventing a package.
    build_files=[p for p in ["Cargo.toml","debian/control","packaging","scripts/build"] if (ROOT/p).exists()]
    checks.append({"test":"BUILD_SUBSTRATE_DISCOVERY","status":"PASS" if build_files else "HOLD","paths":build_files})
    if not build_files: blockers.append("P12_BUILD_SUBSTRATE_NOT_PRESENT")

    # Independent G23/G24 trigger contract is a separate workflow; this point may not
    # mark either gate as passed. It records the prerequisites only.
    cert_chain_ok=all(x in mission for x in ["G23","G24","CERTIFIED","INDEPENDENTLY_VALIDATED"])
    checks.append({"test":"G23_G24_SEPARATION","status":"PASS" if cert_chain_ok else "FAIL","g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED"})
    if not cert_chain_ok: blockers.append("P12_CERTIFICATION_CHAIN_DECLARATION_INVALID")

    if blockers:
        blockers=list(dict.fromkeys(blockers))
        evidence={"schema":"LOUKSNA_ZD_P12_RELEASE_GATE/1.0","status":"HOLD","timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
                  "checks":checks,"open_blockers":blockers,
                  "reason":"Release, G23 and G24 remain forbidden until all material prerequisites are satisfied."}
        (OUT/"P12_RELEASE_GATE_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        result={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"CHECKPOINT_12_PREPARED","parent_checkpoint":"CHECKPOINT_11",
                "next_point":"P12","transition_id":"P12-HOLD-RETRY-001","certified":False,"active":False,
                "g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","open_blockers":blockers,"material_evidence":evidence}
    else:
        evidence={"schema":"LOUKSNA_ZD_P12_RELEASE_GATE/1.0","status":"READY_FOR_INDEPENDENT_GATES",
                  "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"checks":checks,
                  "source_digest":sha256_text(head["stdout"].strip())}
        (OUT/"P12_RELEASE_GATE_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        result={"status":"PASS","checkpoint":"CHECKPOINT_12","parent_checkpoint":"CHECKPOINT_11","next_point":"G23",
                "transition_id":"P12-TO-G23-001","certified":False,"active":False,
                "g23":"REQUIRED","g24":"REQUIRED","material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P12_TELEMETRY "+json.dumps({"event":"P12_GATE","status":result["status"],"next_point":result["next_point"],"open_blockers":result.get("open_blockers",[])},sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e: print("P12_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=__import__("sys").stderr); raise
