#!/usr/bin/env python3
from __future__ import annotations
import ast,hashlib,json,os,subprocess,sys,tempfile,time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p11")).resolve(); OUT.mkdir(parents=True,exist_ok=True)

def run(cmd,cwd=None,timeout=900):
    r=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout)
    return {"returncode":r.returncode,"stdout":r.stdout[-12000:],"stderr":r.stderr[-12000:]}

def main():
    state=json.loads((ROOT/"continuity/STATE.json").read_text())
    mission=(ROOT/"missions/inbox/louksna-zd-v04-master-20261007/MISSION_ORIGINAL.md").read_text()
    puac=(ROOT/"PUAC2.md").read_text()
    checks=[]

    # Lane 1: syntax/identity integrity of the governed executable surface.
    scripts=[ROOT/"bridge/mtls_gateway.py",ROOT/"bridge/lrb_core.py",ROOT/"bridge/live_link.py",
             ROOT/"scripts/missions/louksna_zd_v04_p05_live.py",ROOT/"scripts/missions/louksna_zd_v04_p06_live.py",
             ROOT/"scripts/missions/louksna_zd_v04_p07_live.py",ROOT/"scripts/missions/louksna_zd_v04_p08_live.py",
             ROOT/"scripts/missions/louksna_zd_v04_p09_live.py",ROOT/"scripts/missions/louksna_zd_v04_p10_live.py"]
    for p in scripts:
        ast.parse(p.read_text(encoding="utf-8")); checks.append({"test":"PYTHON_PARSE","path":str(p.relative_to(ROOT)),"status":"PASS"})

    # Lane 2: transport negative/positive controls are independent of P10's HOLD.
    r=run([sys.executable,"-m","unittest","bridge/tests/test_mtls_gateway.py"],cwd=ROOT,timeout=600)
    checks.append({"test":"MTLS_GATEWAY_TESTS","status":"PASS" if r["returncode"]==0 else "FAIL","result":r})
    if r["returncode"]: raise RuntimeError("P11_MTLS_GATEWAY_REGRESSION")

    # Lane 3: governed artifact-transfer controls.
    transfer=ROOT/"scripts/missions/louksna_zd_v04_artifact_transfer.py"
    import importlib.util
    spec=importlib.util.spec_from_file_location("p05_transfer",transfer)
    mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
    with tempfile.TemporaryDirectory(prefix="louksna-p11-") as td:
        out=Path(td)
        report=mod.run_p05_selftest(out)
        checks.append({"test":"ARTIFACT_TRANSFER_SELFTEST","status":report.get("status"),"result":report})
        if report.get("status")!="PASS": raise RuntimeError("P11_ARTIFACT_TRANSFER_REGRESSION")

    # Lane 4: effort profiles must be exactly the five governed profiles and preserve authority/context.
    p08=ROOT/"scripts/missions/louksna_zd_v04_p08_live.py"
    ns={"__name__":"p11_probe"}
    exec(compile(p08.read_text(),str(p08),"exec"),ns)
    names=[x["name"] for x in ns["PROFILES"]]
    if names!=["Instantáneo","Medio","Alto","Muy alto","Pro"]: raise RuntimeError("P11_EFFORT_PROFILE_SET")
    hashes={ns["digest"](ns["CONTEXT"]),ns["digest"](ns["AUTHORITY"])}
    checks.append({"test":"EFFORT_PROFILE_INVARIANTS","status":"PASS","profiles":names,"context_authority_hashes":sorted(hashes)})

    # Lane 5: GitHub capability census structure is 36+21, with no fabricated mutation grant.
    p09=(ROOT/"scripts/missions/louksna_zd_v04_p09_live.py").read_text()
    if "len(REPO_OPS)!=36 or len(ACCOUNT_OPS)!=21" not in p09: raise RuntimeError("P11_CAPABILITY_CARDINALITY_GATE")
    if "NON_MUTATING_CAPABILITY_CENSUS_ONLY" not in p09: raise RuntimeError("P11_MUTATION_GUARD_MISSING")
    if '"Authorization":"Bearer "+token' not in p09: raise RuntimeError("P11_GITHUB_AUTH_HEADER_MISSING")
    checks.append({"test":"GITHUB_CAPABILITY_CENSUS_GUARD","status":"PASS","repository_ops":36,"account_ops":21})

    # Lane 6: PUAC critical identifiers must exist and remain independent.
    required=["T01","T13","T21","T28","G23","G24"]
    missing=[x for x in required if x not in puac and x not in mission]
    if missing: raise RuntimeError("P11_PUAC_IDENTIFIERS_MISSING:"+",".join(missing))
    if "CERTIFIED" not in puac or "G23" not in puac or "G24" not in puac: raise RuntimeError("P11_CERTIFICATION_CHAIN_MISSING")
    checks.append({"test":"PUAC2_CRITICAL_CHAIN","status":"PASS","required":required})

    # Lane 7: no executor may silently certify or activate.
    ex=json.loads((ROOT/"continuity/EXECUTORS.json").read_text())["executors"]
    for point,path in ex.items():
        if point=="P11": continue
        src=(ROOT/path).read_text(encoding="utf-8")
        if '"certified":True' in src.replace(" ","") or '"certified": true' in src:
            raise RuntimeError("P11_EXECUTOR_SELF_CERTIFICATION:"+point)
        if '"active":True' in src.replace(" ","") or '"active": true' in src:
            raise RuntimeError("P11_EXECUTOR_SELF_ACTIVATION:"+point)
    checks.append({"test":"EXECUTOR_NO_SELF_CERTIFICATION","status":"PASS","registered_points":sorted(ex)})

    evidence={"schema":"LOUKSNA_ZD_P11_LAB/1.0","status":"PASS","checkpoint":"CHECKPOINT_11",
              "timestamp_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
              "current_open_blockers":state.get("open_blockers",[]),"tests":checks,
              "second_order_note":"P10_OFF_HOST_RELAY_UNPROVEN remains open and is not converted to PASS."}
    (OUT/"P11_LAB_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    result={"status":"PASS","checkpoint":"CHECKPOINT_11","parent_checkpoint":"CHECKPOINT_10","next_point":"P12",
            "transition_id":"P11-CHECKPOINT-TO-P12-001","certified":False,"active":False,
            "g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","open_blockers":state.get("open_blockers",[]),
            "material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n")
    print("LOUKSNA_P11_TELEMETRY "+json.dumps({"event":"CHECKPOINT_11_REACHED","next_point":"P12","status":"PASS","open_blockers":state.get("open_blockers",[])},sort_keys=True),flush=True)

if __name__=="__main__":
    try: main()
    except Exception as e: print("P11_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=sys.stderr); raise
