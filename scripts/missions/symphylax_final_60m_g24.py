#!/usr/bin/env python3
import argparse,json,pathlib,time
def dump(p,o):pathlib.Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--g23",required=True);ap.add_argument("--out",required=True);q=ap.parse_args();root=pathlib.Path(q.g23);out=pathlib.Path(q.out);out.mkdir(parents=True,exist_ok=True);find=[]
 g23=json.load(open(root/"G23_RESULT.json"));puac=json.load(open(root/"PUAC2_G23_APPROVAL.json"));frozen=json.load(open(root/"producer/FROZEN_CANDIDATE.json"));gates=json.load(open(root/"producer/TECHNICAL_GATES.json"));rb=json.load(open(root/"producer/ROLLBACK_EVIDENCE.json"));nr=json.load(open(root/"producer/NON_REGRESSION.json"));dl=json.load(open(root/"producer/LINUX_REMAINDER_DOWNLOAD_READINESS.json"))
 if g23.get("result")!="PASS":find.append("G23_NOT_PASS")
 if g23.get("candidate_digest_sha256")!=frozen.get("candidate_digest_sha256"):find.append("DIGEST_MISMATCH")
 if puac.get("status")!="PASS":find.append("PUAC2_NOT_PASS")
 if gates.get("result")!="PASS":find.append("TECHNICAL_GATES_NOT_PASS")
 if rb.get("verified") is not True:find.append("ROLLBACK_NOT_VERIFIED")
 if nr.get("result")!="PASS":find.append("NON_REGRESSION_NOT_PASS")
 if dl.get("result")!="PASS":find.append("LINUX_REMAINDER_DOWNLOAD_NOT_READY")
 if time.time()-float(frozen.get("start_epoch",time.time()))>3600:find.append("GLOBAL_60M_BUDGET_EXCEEDED")
 result="PASS" if not find else "HOLD";guaranteed=result=="PASS";obj={"schema":"G24_SYMPHYLAX_CERTIFICATION/1.0","result":result,"candidate_digest_sha256":frozen.get("candidate_digest_sha256"),"g23":g23.get("result"),"puac2":puac.get("status"),"server_guaranteed":guaranteed,"server_certified":guaranteed,"server_ready_final":result,"findings":find,"certification_propagated":False};dump(out/"G24_RESULT.json",obj)
 (out/"README_SERVER_READY_FINAL.md").write_text("# SYMPHYLAX R1 — FINAL\n\nPUAC2 = "+str(puac.get("status"))+"\nG23 = "+str(g23.get("result"))+"\nG24 = "+result+"\nSERVER_GUARANTEED = "+str(guaranteed).upper()+"\nSERVER_CERTIFIED = "+str(guaranteed).upper()+"\nSERVER_READY_FINAL = "+result+"\nFINAL_DIGEST = "+str(frozen.get("candidate_digest_sha256"))+"\nLINUX_REMAINDER_DOWNLOAD_READY = "+str(dl.get("result"))+"\nFINDINGS = "+repr(find)+"\n",encoding="utf-8");print(json.dumps(obj,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
