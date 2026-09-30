#!/usr/bin/env python3
"""Pinned CUSTOSZ V7 source/security review for the frozen non-model LRB."""
import argparse, hashlib, json, os, subprocess, sys
from pathlib import Path

TARGET = "c961a198f524a128dba6374290e2abe73dfaece6"
LOUKSNA_SHA = "5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9"
PUAC2_SHA = "c872ab8d31e0e301de93ab06047294424d309d947f225e62148cee8265b15869"
CUSTOSZ_SHA = "dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"
RUNTIME_SHA = "a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67"
METAOS_SHA = "5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0"

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def run(cmd, timeout=45):
    p=subprocess.run(cmd,text=True,capture_output=True,timeout=timeout)
    return {"exit_code":p.returncode,"stdout":p.stdout[-8000:],"stderr":p.stderr[-3000:]}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate-root",required=True)
    ap.add_argument("--out",required=True)
    a=ap.parse_args()
    root=Path(a.candidate_root).resolve()
    checks={}
    blockers=[]
    git=run(["git","-C",str(root),"rev-parse","HEAD"],5)
    checks["git_head"]=git
    if git["exit_code"] or git["stdout"].strip()!=TARGET:
        blockers.append("TARGET_SOURCE_COMMIT_MISMATCH")
    forbidden=[
      "bridge/virtual_brain.py","bridge/VIRTUAL_BRAIN.json","bridge/VIRTUAL_BRAIN.md",
      "bridge/benchmarks/qwen_puac2_benchmark.py",".github/workflows/lrb-qwen-puac2-benchmark.yml"
    ]
    present=[p for p in forbidden if (root/p).exists()]
    checks["forbidden_model_surface_present"]=present
    if present: blockers.append("MODEL_SURFACE_OUTSIDE_FROZEN_SCOPE")
    required=[
      "bridge/lrb_core.py","bridge/live_link.py","bridge/mtls_gateway.py",
      "bridge/external_gates.py","bridge/one_time_scope.py","bridge/global_scope_register.py",
      "bridge/continuous_assurance.py","bridge/ASSURANCE_MATRIX.json",
      "bridge/deploy/louksna-live-socket.service.in","bridge/deploy/louksna-mtls-readonly.service.in"
    ]
    missing=[p for p in required if not (root/p).is_file()]
    checks["required_missing"]=missing
    if missing: blockers.append("REQUIRED_LRB_SOURCE_MISSING")
    ids={
      "Louksna.md":LOUKSNA_SHA,"PUAC2.md":PUAC2_SHA,
      "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz":CUSTOSZ_SHA,
      "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz":RUNTIME_SHA,
      "artifacts/custosz-v7/MetaOS.wasm":METAOS_SHA
    }
    actual={}
    for rel,exp in ids.items():
        p=root/rel
        actual[rel]=sha(p) if p.is_file() else None
        if actual[rel]!=exp: blockers.append("IDENTITY_MISMATCH:"+rel)
    checks["identity_sha256"]=actual
    custosz=root/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    checks["custosz_status"]=run([sys.executable,"-B","-I",str(custosz),"v07-status"],15)
    checks["custosz_selftest"]=run([sys.executable,"-B","-I",str(custosz),"v07-selftest"],20)
    if checks["custosz_status"]["exit_code"]!=0: blockers.append("CUSTOSZ_STATUS_FAIL")
    if checks["custosz_selftest"]["exit_code"]!=0: blockers.append("CUSTOSZ_SELFTEST_FAIL")
    pyfiles=[str(p) for p in (root/"bridge").rglob("*.py")]
    checks["py_compile"]=run([sys.executable,"-m","py_compile",*pyfiles],25)
    if checks["py_compile"]["exit_code"]!=0: blockers.append("PY_COMPILE_FAIL")
    checks["unit_tests"]=run([sys.executable,"-B","-m","unittest","discover","-s",str(root/"bridge/tests"),"-p","test_*.py","-v"],55)
    if checks["unit_tests"]["exit_code"]!=0: blockers.append("UNIT_TESTS_FAIL")
    ext=(root/"bridge/external_gates.py").read_text(encoding="utf-8")
    checks["gate_roles_present"]=all(x in ext for x in ('"OWNER"','"G23"','"G24"','"G23_2"','"G24_2"'))
    checks["verifier_cannot_self_certify"]="execution_authorized_by_this_verifier" in ext and '"certified": False' in ext
    if not checks["gate_roles_present"]: blockers.append("GATE_ROLE_CONTRACT_DRIFT")
    if not checks["verifier_cannot_self_certify"]: blockers.append("SELF_CERTIFICATION_GUARD_MISSING")
    service=(root/"bridge/deploy/louksna-mtls-readonly.service.in").read_text(encoding="utf-8")
    checks["resource_caps_present"]=("MemoryMax=" in service and "CPUQuota=" in service)
    if not checks["resource_caps_present"]: blockers.append("SERVICE_RESOURCE_CAPS_MISSING")
    report={
      "schema":"LRB_CUSTOSZ_SOURCE_SECURITY_REVIEW/1.0",
      "target_source_commit":TARGET,
      "worker":"CUSTOSZ_V7",
      "scope":"LOUKSNA_REMOTE_BRIDGE_NON_MODEL_ONLY",
      "status":"PASS" if not blockers else "HOLD",
      "blockers":sorted(set(blockers)),
      "checks":checks,
      "canonical_mutation":False,
      "certification_issued":False
    }
    out=Path(a.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":report["status"],"blockers":report["blockers"]},sort_keys=True))
    return 0 if not blockers else 3

if __name__=="__main__":
    raise SystemExit(main())
