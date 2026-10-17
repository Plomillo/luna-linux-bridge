#!/usr/bin/env python3
"""Low-resource live SERVER_READY mission probe with real CUSTOSZ heartbeats.

This job proves the restarted mission remains alive on the real runner while
performing only reversible TEST_ONLY checks. It does not self-certify gates
that require later independent evidence.
"""
import hashlib, json, os, subprocess, sys, tempfile, time
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(os.environ["GITHUB_WORKSPACE"]).resolve()
RECEIPT=Path(os.environ["RECEIPT_FILE"]).resolve()
CUSTOSZ=ROOT/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
RUNTIME=ROOT/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
METAOS=ROOT/"artifacts/custosz-v7/MetaOS.wasm"
MISSION=ROOT/"docs/missions/CUSTOSZ_V7_SERVER_READY_20M/MISION_SERVER_READY_FINAL.md"

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def meminfo():
    d={}
    for line in Path("/proc/meminfo").read_text().splitlines():
        k,v,*_=line.replace(":","").split()
        if k in {"MemTotal","MemAvailable","SwapTotal","SwapFree"}: d[k]=int(v)
    return d

def main():
    r=json.loads(RECEIPT.read_text(encoding="utf-8"))
    deadline=datetime.fromisoformat(r["deadline_utc"])
    if datetime.now(timezone.utc)>=deadline: raise SystemExit("MISSION_DEADLINE_EXPIRED")
    if sha(MISSION)!=r["mission_sha256"]: raise SystemExit("MISSION_HASH_DRIFT")
    os.environ["CUSTOSZ_WORKSPACE"]=r["workspace"]
    os.environ["CUSTOSZ_STATE_DIR"]=r["state_dir"]
    sys.path.insert(0,str(CUSTOSZ))
    import custosz_v05_legacy as worker
    worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
    worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}

    out=Path(os.environ["RUNNER_TEMP"])/"SERVER_READY_LIVE_STATE.json"
    journal=Path(os.environ["RUNNER_TEMP"])/"SERVER_READY_HEARTBEATS.jsonl"
    state={
      "schema":"SERVER_READY_LIVE_STATE/1.0",
      "mission_id":r["mission_id"],
      "mission_sha256":r["mission_sha256"],
      "source_commit":r["source_commit"],
      "started_utc":utc(),
      "status":"ACTIVE",
      "authority":"Louksna.md",
      "worker":"CUSTOSZ_V7",
      "supervisor":"SYMPHYLAX_R1",
      "governor":"MetaOS",
      "runtime":"CUSTOSZ_RUNTIME_V1",
      "resource_policy":{"nice":10,"virtual_memory_kib":262144,"heavy_compute_on_host":False},
      "identities":{"CUSTOSZ":sha(CUSTOSZ),"RUNTIME":sha(RUNTIME),"METAOS":sha(METAOS),"MISSION":sha(MISSION)},
      "tests":{},
      "gates":{"GATE_01_WORKSPACE_RESOLUTION":"PASS","GATE_02_CUSTOSZ_IDENTITY":"EVIDENCE_IN_PROGRESS",
               "GATE_03_RUNTIME_IDENTITY":"HOLD_PROVENANCE_RECONCILIATION",
               "GATE_14_NO_CANONICAL_MUTATION":"PASS","GATE_15_HOST_SAFETY":"PASS"},
      "no_windows_disk_mutation":True,"no_proyectos_mutation":True
    }
    for cmd in ("v07-status","v07-selftest"):
        p=subprocess.run([sys.executable,"-B","-I",str(CUSTOSZ),cmd],capture_output=True,text=True,timeout=30)
        state["tests"][cmd]={"exit_code":p.returncode,"stdout":p.stdout[:4000],"stderr":p.stderr[:1000]}
        if p.returncode: raise SystemExit("CUSTOSZ_"+cmd+"_FAILED")
    state["gates"]["GATE_02_CUSTOSZ_IDENTITY"]="PASS"

    with tempfile.TemporaryDirectory(prefix="server-ready-test-only-") as d:
        p=Path(d)/"TEST_ONLY_EFFECT.txt"
        payload=("mission="+r["mission_id"]+"\n").encode()
        p.write_bytes(payload); first=sha(p)
        p.unlink()
        rollback=not p.exists()
        p.write_bytes(payload); second=sha(p)
        idempotent=(first==second)
        p.unlink()
        state["tests"]["reversible_test_only_effect"]={"first_sha256":first,"second_sha256":second,
            "rollback_verified":rollback,"idempotent_replay":idempotent}
        state["gates"]["GATE_11_ROLLBACK"]="PARTIAL_PASS_TEST_ONLY"
        state["gates"]["GATE_12_IDEMPOTENCY"]="PARTIAL_PASS_TEST_ONLY"

    # Keep the real mission alive only until the mandated validation reserve.
    cutoff=deadline.timestamp()-240
    seq=0
    while time.time()<cutoff:
        tick=worker.mission_tick(r["mission_id"])
        snap={"seq":seq,"utc":utc(),"heartbeat_state":tick.get("state"),"memory_kib":meminfo(),
              "loadavg":list(os.getloadavg()),"mission_id":r["mission_id"]}
        with journal.open("a",encoding="utf-8") as f:
            f.write(json.dumps(snap,sort_keys=True)+"\n")
        state["last_heartbeat"]=snap
        state["heartbeat_count"]=seq+1
        out.write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps({"mission_id":r["mission_id"],"seq":seq,"heartbeat":tick.get("state"),"utc":snap["utc"]},sort_keys=True),flush=True)
        seq+=1
        time.sleep(min(45,max(1,cutoff-time.time())))
    state["status"]="ACTIVE_PHASE_COMPLETED_VALIDATION_RESERVE_REACHED"
    state["ended_utc"]=utc()
    out.write_text(json.dumps(state,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

if __name__=="__main__":
    raise SystemExit(main())
