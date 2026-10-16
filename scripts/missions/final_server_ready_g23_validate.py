#!/usr/bin/env python3
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
MISSION_SHA="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
def utc():return datetime.now(timezone.utc).isoformat()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def find(root,name):
 xs=list(Path(root).rglob(name))
 if len(xs)!=1:raise RuntimeError(f"{name}:EXPECTED_ONE_FOUND_{len(xs)}")
 return xs[0]
def main():
 a=argparse.ArgumentParser();a.add_argument("--bundle",required=True);a.add_argument("--mission",required=True);a.add_argument("--out",required=True);q=a.parse_args();out=Path(q.out);out.mkdir(parents=True,exist_ok=True)
 findings=[]
 if sha(q.mission)!=MISSION_SHA:findings.append("MISSION_SOURCE_SHA256_MISMATCH")
 state=json.loads(find(q.bundle,"CHAIN_STATE.json").read_text());gates=json.loads(find(q.bundle,"TERMINAL_GATES.json").read_text());manifest=json.loads(find(q.bundle,"FROZEN_BUNDLE_MANIFEST.json").read_text())
 if state.get("G08")!=1:findings.append("G08_NOT_PASS")
 if state.get("G09")!=1:findings.append("G09_NOT_PASS")
 if not gates.get("server_technical_ready"):findings.append("SERVER_TECHNICAL_READY_FALSE")
 if not all(v=="PASS" for v in gates.get("gates",{}).values()):findings.append("ONE_OR_MORE_SERVER_READY_GATES_NOT_PASS")
 evidence_dir=find(q.bundle,"SERVER_READY_GATES.json").parent
 for n,h in manifest.get("files",{}).items():
  matches=list(Path(q.bundle).rglob(n))
  if len(matches)!=1 or sha(matches[0])!=h:findings.append("FROZEN_HASH_MISMATCH:"+n)
 rb=json.loads(find(q.bundle,"ROLLBACK_EVIDENCE.json").read_text());nr=json.loads(find(q.bundle,"NON_REGRESSION_REPORT.json").read_text());prov=json.loads(find(q.bundle,"RUNTIME_PROVENANCE.json").read_text())
 if rb.get("verified") is not True:findings.append("ROLLBACK_NOT_VERIFIED")
 if nr.get("result")!="PASS" or nr.get("protected_scopes_mutated") is not False:findings.append("NON_REGRESSION_NOT_PASS")
 if prov.get("runtime_identity_status")!="PASS":findings.append("RUNTIME_IDENTITY_NOT_PASS")
 result="PASS" if not findings else "HOLD"
 obj={"schema":"G23_INDEPENDENT_VALIDATION/1.0","utc":utc(),"mission_sha256":MISSION_SHA,"result":result,"independent_validation":result,"evidence_chain_complete":not findings,"reproducibility":"PASS" if not findings else "HOLD","no_unresolved_critical_findings":not findings,"findings":findings,"repair_performed":False,"producer_mutated":False}
 (out/"G23_RESULT.json").write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
 md="# G23 — INDEPENDENT VALIDATION\n\nG23 = "+result+"\nINDEPENDENT_VALIDATION = "+result+"\nEVIDENCE_CHAIN_COMPLETE = "+str(not findings).upper()+"\nREPRODUCIBILITY = "+("PASS" if not findings else "HOLD")+"\nNO_UNRESOLVED_CRITICAL_FINDINGS = "+str(not findings).upper()+"\nREPAIR_PERFORMED = FALSE\n\nFINDINGS:\n"+("\n".join("- "+x for x in findings) if findings else "- NONE")+"\n"
 (out/"G23_INDEPENDENT_VALIDATION.md").write_text(md)
 print(json.dumps({"G23":result,"findings":findings},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
