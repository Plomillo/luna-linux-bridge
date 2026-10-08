#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,os,subprocess,time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p10")).resolve(); OUT.mkdir(parents=True,exist_ok=True)
def sh(cmd,cwd=None):
    return subprocess.run(cmd,cwd=cwd,text=True,capture_output=True)
def main():
    tests=ROOT/"bridge/tests/test_mtls_gateway.py"
    if not tests.is_file(): raise RuntimeError("MTLS_TEST_SUITE_MISSING")
    r=sh(["python3","-m","unittest","bridge/tests/test_mtls_gateway.py"],cwd=ROOT)
    local={"returncode":r.returncode,"stdout":r.stdout[-6000:],"stderr":r.stderr[-6000:]}
    source=(ROOT/"bridge/mtls_gateway.py").read_text()
    tls13="ssl.TLSVersion.TLSv1_3" in source
    loopback='super().__init__(("127.0.0.1",port)' in source
    remote_host=os.environ.get("LOUKSNA_REMOTE_RELAY_HOST")
    evidence={"schema":"LOUKSNA_ZD_P10_TRANSPORT/1.0","status":"HOLD","local_mtls_test":local,"tls13_source_gate":tls13,"loopback_binding_source_gate":loopback,"off_host_relay_host_configured":bool(remote_host),"off_host_relay_materially_proven":False,"blocker":"P10_OFF_HOST_RELAY_UNPROVEN","reason":"Current governed gateway is loopback-only; no independently authenticated owner-managed off-host relay endpoint is configured in the runtime."}
    (OUT/"P10_TRANSPORT_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    result={"status":"HOLD_INDEPENDENT_CONTINUATION","checkpoint":"CHECKPOINT_10","parent_checkpoint":"CHECKPOINT_09","next_point":"P11","transition_id":"P10-HOLD-TO-P11-INDEPENDENT-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","open_blockers":["P10_OFF_HOST_RELAY_UNPROVEN"],"material_evidence":evidence}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P10_TELEMETRY "+json.dumps({"event":"CHECKPOINT_10_HOLD","next_point":"P11","status":"HOLD_INDEPENDENT_CONTINUATION","blocker":"P10_OFF_HOST_RELAY_UNPROVEN"},sort_keys=True),flush=True)
if __name__=="__main__":
    try: main()
    except Exception as e: print("P10_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=__import__("sys").stderr); raise
