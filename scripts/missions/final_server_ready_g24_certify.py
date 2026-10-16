#!/usr/bin/env python3
import argparse,hashlib,json
from datetime import datetime,timezone
from pathlib import Path
MISSION_SHA="8191840debd98f8775e530a37d3d23770f148693af64689f8e0d187be037cb21"
AUTHORITY_SHA="5270c3d643339c283edf13b414f335f23f921c4dac023b06d38de62927e29bf9"
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
 g23=json.loads(find(q.bundle,"G23_RESULT.json").read_text());gates=json.loads(find(q.bundle,"TERMINAL_GATES.json").read_text());nr=json.loads(find(q.bundle,"NON_REGRESSION_REPORT.json").read_text());rb=json.loads(find(q.bundle,"ROLLBACK_EVIDENCE.json").read_text())
 if g23.get("result")!="PASS":findings.append("G23_NOT_PASS")
 if not gates.get("server_technical_ready"):findings.append("SERVER_TECHNICAL_READY_FALSE")
 if not all(v=="PASS" for v in gates.get("gates",{}).values()):findings.append("SERVER_READY_GATES_NOT_ALL_PASS")
 if nr.get("authority_sha256_preserved") is not True or nr.get("protected_scopes_mutated") is not False or nr.get("result")!="PASS":findings.append("NON_REGRESSION_INVARIANT_FAIL")
 if rb.get("verified") is not True:findings.append("ROLLBACK_NOT_VERIFIED")
 result="PASS" if not findings else "HOLD"
 obj={"schema":"G24_CERTIFICATION/1.0","utc":utc(),"mission_sha256":MISSION_SHA,"authority_sha256":AUTHORITY_SHA,"result":result,"g23":g23.get("result"),"server_technical_ready":gates.get("server_technical_ready"),"server_certified":result=="PASS","server_ready_final":result,"findings":findings,"certification_propagated":False}
 (out/"G24_RESULT.json").write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n")
 md="# G24 — FINAL CERTIFICATION\n\nG24 = "+result+"\nSERVER_CERTIFIED = "+str(result=="PASS").upper()+"\nSERVER_READY_FINAL = "+result+"\nG23 = "+str(g23.get("result"))+"\nCERTIFICATION_PROPAGATED = FALSE\n\nFINDINGS:\n"+("\n".join("- "+x for x in findings) if findings else "- NONE")+"\n"
 (out/"G24_CERTIFICATION.md").write_text(md)
 (out/"README_SERVER_READY_TERMINAL.md").write_text("# SERVER_READY TERMINAL\n\nG08 = "+("PASS" if gates["gates"].get("GATE_08_SERVICE_PERSISTENCE")=="PASS" else "HOLD")+"\nG09 = "+("PASS" if gates["gates"].get("GATE_09_FAILURE_RECOVERY")=="PASS" else "HOLD")+"\nG23 = "+str(g23.get("result"))+"\nG24 = "+result+"\nSERVER_CERTIFIED = "+str(result=="PASS").upper()+"\nSERVER_READY_FINAL = "+result+"\n")
 print(json.dumps({"G24":result,"server_certified":result=="PASS","findings":findings},sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
