#!/usr/bin/env python3
"""Bind the registered CUSTOSZ V7 continuation mission to the staged runtime.
Heavy work runs on GitHub-hosted compute only. No user-host installation or disk mutation.
"""
import hashlib, json, os, subprocess, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

MISSION_ID="MIS-385dfa9a0d0a4a21bb92"
DEADLINE=datetime.fromisoformat("2099-01-01T00:00:00+00:00")
ACTIVE_BUDGET_SECONDS=1192.802

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def utc():
    return datetime.now(timezone.utc).isoformat()

def main():
    if datetime.now(timezone.utc) >= DEADLINE:
        raise SystemExit("CONTINUATION_DEADLINE_EXPIRED")

    workspace=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
    root=workspace/"mission"
    a1root=workspace/"source-a1"
    r4root=workspace/"source-r4"
    casroot=workspace/"source-cas"
    out=Path(os.environ["RESULT_FILE"])

    custosz=root/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
    runtime=root/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
    metaos=root/"artifacts/custosz-v7/MetaOS.wasm"
    a0=root/"Louksna.md"
    puac2=root/"PUAC2.md"
    a1=a1root/"LOUKSNAMEJORADA.md"
    skeleton=r4root/"docs/luna-r4/source/SKELETON_CANONICO_REFERENCIA.txt"
    mission=root/"missions/inbox/server-ready-restart-20260928/MISSION_ORIGINAL.md"
    executor=root/"scripts/mission_mailbox/adapters/server_ready_probe.py"

    expected={
        "A0":"5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9",
        "A1":"2114188988126aa7a9650c131526c9d7c54ad351db315635569a317114f4eb51",
        "PUAC2":"c872ab8d31e0e301de93ab06047294424d309d947f225e62148cee8265b15869",
        "CUSTOSZ":"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2",
        "RUNTIME":"a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67",
        "METAOS":"5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0",
        "SKELETON":"fb9fad37994e684ad54b1ffc2762660eebcb8e41bd9c4ba685ffac55217d5b0f",
        "MISSION":"8cc285625346e4675d8b6fba4b4545ee42b0255057d8109db3e48a1e061558b9"
    }
    paths={"A0":a0,"A1":a1,"PUAC2":puac2,"CUSTOSZ":custosz,"RUNTIME":runtime,"METAOS":metaos,"SKELETON":skeleton,"MISSION":mission}
    actual={k:sha(v) for k,v in paths.items()}
    if actual != expected:
        out.write_text(json.dumps({"status":"SOURCE_PIN_MISMATCH","actual":actual,"expected":expected},indent=2,sort_keys=True)+"\n")
        raise SystemExit("SOURCE_PIN_MISMATCH")

    report={
        "mission_id":MISSION_ID,
        "scope":"GITHUB_HOSTED_MATERIAL_RESEARCH_ONLY",
        "started_utc":utc(),
        "deadline_utc":DEADLINE.isoformat(),
        "active_budget_seconds":ACTIVE_BUDGET_SECONDS,
        "source_hashes":actual,
        "user_host_ram_heavy_research":False,
        "host_installation":False,
        "host_disk_mutation":False,
        "g23":"HOLD",
        "g24":"HOLD",
        "skeleton_runtime_pin":"4e9bf0e799487ea0fd6a6d32359176bdce996010e33ed151ce0f186155d11df0",
        "selected_staging_runtime_sha256":actual["RUNTIME"],
        "status":"STARTED"
    }

    for cmd in ("v07-status","v07-selftest"):
        p=subprocess.run([sys.executable,"-B","-I",str(custosz),cmd],capture_output=True,text=True,timeout=20)
        report["custosz_"+cmd]={"exit_code":p.returncode,"stdout":p.stdout[:5000],"stderr":p.stderr[:1500]}
        if p.returncode != 0:
            out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
            raise SystemExit("CUSTOSZ_"+cmd+"_FAILED")

    with tempfile.TemporaryDirectory(prefix="custosz-r4-runtime-") as d:
        tmp=Path(d)
        sys.path.insert(0,str(runtime))
        from runtime_core import Runtime, ExecutorAdapter, TimeBudgetController
        from sr_exec_bound_fme_01 import SRExecBoundFME01

        rt=Runtime(tmp/"runtime",a0,sha(a0))
        selftest=rt.selftest()
        report["runtime_selftest"]=selftest
        if selftest.get("status") != "PASS":
            out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
            raise SystemExit("RUNTIME_SELFTEST_FAILED")

        rt.budget=TimeBudgetController(int(ACTIVE_BUDGET_SECONDS))
        rt.mission.transition("PRECHECK")
        executor_id="CUSTOSZ_V7_R4_GITHUB_RESEARCH"
        rt.executors.register(ExecutorAdapter(
            executor_id,
            "LOCAL_SUBPROCESS",
            sys.executable,
            capabilities={"READONLY_RESEARCH":1.0}
        ))
        checkpoint=rt.checkpoints.capture_file("MISSION_R4_BEFORE_RESEARCH",mission)
        target=tmp/"RUNTIME_RESEARCH_RESULT.json"
        spec={
            "mission_id":MISSION_ID,
            "mission_spec_digest":sha(mission),
            "required_abilities":{"READONLY_RESEARCH":1.0},
            "authority_context":{"authority":"Louksna.md","sha256":sha(a0)},
            "policy_context":{
                "policy_id":"GITHUB_HOSTED_NO_USER_HOST_RAM",
                "scope":"READONLY_RESEARCH_ONLY",
                "allow":True
            },
            "execution_payload_digest":sha(executor),
            "expected_effect":{
                "target":str(target),
                "effect_type":"READONLY_RESEARCH_REPORT"
            },
            "checkpoint_pointer":checkpoint["checkpoint_id"],
            "runtime_digest":sha(runtime),
            "mission_state":"DISPATCH_READY",
            "executor_metadata":{
                executor_id:{
                    "identity_valid":True,
                    "provenance_valid":True,
                    "digest":sha(Path(sys.executable))
                }
            },
            "executor_policy":{
                executor_id:{
                    "permissions_valid":True,
                    "resource_envelope_valid":True,
                    "policy_allow":True,
                    "risk":0,
                    "cost":0
                }
            },
            "probe_argv":{
                executor_id:["{COMMAND}","-B","-I","-c","import sys;sys.exit(0)"]
            },
            "dispatch":{
                "cwd":str(tmp),
                "argv_template":[
                    "{COMMAND}","-B","-I",str(executor),
                    "{DISPATCH_PATH}","{ACK_PATH}","{FME_PATH}","{TARGET}",
                    str(root),str(a1root),str(r4root),str(casroot)
                ],
                "timeout_s":600,
                "ack_timeout_s":15,
                "fme_timeout_s":30
            }
        }
        result=SRExecBoundFME01(rt).establish_material_execution(spec)
        report["runtime_dispatch"]={k:result.get(k) for k in (
            "result","global_step_gate","material_execution_proven","evidence_chain_head"
        )}
        if result.get("result") != "PASS" or not target.is_file():
            report["status"]="RUNTIME_MATERIAL_DISPATCH_FAILED"
            report["ended_utc"]=utc()
            out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
            raise SystemExit("RUNTIME_MATERIAL_DISPATCH_FAILED")

        report["research_result"]=json.loads(target.read_text(encoding="utf-8"))
        report["runtime_evidence_ledger"]=rt.journal.verify()
        report["status"]="CUSTOSZ_AND_RUNTIME_MATERIAL_RESEARCH_PASS"

    report["ended_utc"]=utc()
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
        "status":report["status"],
        "mission_id":MISSION_ID,
        "runtime_dispatch":report["runtime_dispatch"]
    },ensure_ascii=False,sort_keys=True))
    return 0

if __name__=="__main__":
    raise SystemExit(main())
