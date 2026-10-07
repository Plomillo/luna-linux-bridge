#!/usr/bin/env python3
"""Pinned mailbox admission adapter for SR_TERMINAL_10M_20260928."""
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
MISSION_SHA256="db0b882d55ca6d4b62639cd451f0795c6f2e245732b631001816a8a937401983"
MISSION_PATH="missions/inbox/server-ready-terminal-10m-20260928/MISSION_ORIGINAL.md"
CONTRACT_PATH="server/terminal-chain/SERVER_READY_TERMINAL_10M_CONTRACT.json"
CONTRACT_SHA256="018f71a2de595076b02c290d563b4a27df8725b8dab35cbbf389762d9fde9904"
EXPECTED={"authority":"5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9","custosz":"dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2","runtime":"a79e13869601d68fe801b85ad421719b79d4afa5520ae34b91b419bd8834ae67","metaos":"5d8f1239e3a0b452be722078760b000afc22af0a64f93ffb0a1f74024f15aed0"}
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def utc():return datetime.now(timezone.utc).isoformat()
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--repo-root",default=".");ap.add_argument("--out");q=ap.parse_args();r=Path(q.repo_root).resolve()
 p={"mission":r/MISSION_PATH,"contract":r/CONTRACT_PATH,"authority":r/"Louksna.md","custosz":r/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz","runtime":r/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz","metaos":r/"artifacts/custosz-v7/MetaOS.wasm"}
 missing=[k for k,v in p.items() if not v.is_file()]
 if missing:report={"status":"HOLD","root_blocker":"MISSING_REQUIRED_ARTIFACT","missing":missing}
 else:
  actual={k:sha(v) for k,v in p.items()}
  expected={"mission":MISSION_SHA256,"contract":CONTRACT_SHA256,**EXPECTED}
  mismatches={k:{"expected":expected[k],"actual":actual[k]} for k in expected if actual[k]!=expected[k]}
  c=json.loads(p["contract"].read_text(encoding="utf-8"))
  semantic_ok=c.get("mission_sha256")==MISSION_SHA256 and c.get("time_budget",{}).get("hard_ceiling_per_attempt_seconds")==600 and c.get("invariants",{}).get("NO_EXIT_WITHOUT_GENUINE_PASS")==1 and c.get("invariants",{}).get("NO_ARTIFICIAL_PASS")==1
  status="PASS" if not mismatches and semantic_ok else "HOLD"
  report={"schema":"SERVER_READY_TERMINAL_10M_ADMISSION/1.0","utc":utc(),"status":status,"mission_sha256":MISSION_SHA256,"contract_sha256":CONTRACT_SHA256,"identity_hashes":actual,"mismatches":mismatches,"semantic_contract_ok":semantic_ok,"grants_g08":False,"grants_g09":False,"grants_g23":False,"grants_g24":False,"next_gate":"G08_SERVICE_PERSISTENCE" if status=="PASS" else "ADMISSION_REMEDIATION"}
 if q.out:
  o=Path(q.out);o.parent.mkdir(parents=True,exist_ok=True);o.write_text(json.dumps(report,indent=2,sort_keys=True)+"\n",encoding="utf-8")
 print(json.dumps(report,sort_keys=True));return 0 if report["status"]=="PASS" else 3
if __name__=="__main__":raise SystemExit(main())
