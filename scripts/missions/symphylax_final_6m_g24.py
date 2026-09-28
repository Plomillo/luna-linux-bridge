#!/usr/bin/env python3
import argparse,json,pathlib,time
BUDGET=360
def dump(p,o):pathlib.Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def main():
 a=argparse.ArgumentParser();a.add_argument("--g23",required=True);a.add_argument("--out",required=True);q=a.parse_args();root=pathlib.Path(q.g23);out=pathlib.Path(q.out);out.mkdir(parents=True,exist_ok=True);f=[]
 g23=json.load(open(root/"G23_RESULT.json"));puac=json.load(open(root/"PUAC2_RESULT.json"));c=json.load(open(root/"candidate/FINAL_CANDIDATE.json"));g=json.load(open(root/"candidate/TECHNICAL_GATES.json"));rb=json.load(open(root/"candidate/ROLLBACK_EVIDENCE.json"));nr=json.load(open(root/"candidate/NON_REGRESSION_REPORT.json"))
 if g23.get("result")!="PASS":f.append("G23_NOT_PASS")
 if puac.get("status")!="PASS":f.append("PUAC2_NOT_PASS")
 if g23.get("candidate_digest_sha256")!=c.get("candidate_digest_sha256"):f.append("DIGEST_G23_G24_MISMATCH")
 if g.get("result")!="PASS":f.append("TECHNICAL_GATES_NOT_PASS")
 if rb.get("verified") is not True:f.append("ROLLBACK_NOT_PASS")
 if nr.get("result")!="PASS":f.append("NON_REGRESSION_NOT_PASS")
 if time.time()-float(c.get("start_epoch",time.time()))>BUDGET:f.append("GLOBAL_360S_BUDGET_EXHAUSTED")
 result="PASS" if not f else "HOLD";ok=result=="PASS";obj={"schema":"G24_SYMPHYLAX_6M/1.0","result":result,"candidate_digest_sha256":c.get("candidate_digest_sha256"),"g23":g23.get("result"),"puac2":puac.get("status"),"server_guaranteed":ok,"server_certified":ok,"server_ready_final":result,"certification_propagated":False,"findings":f}
 dump(out/"G24_RESULT.json",obj)
 (out/"README_SERVER_READY_FINAL.md").write_text("# SYMPHYLAX R1 — FINAL 6M\n\nPUAC2 = "+str(puac.get("status"))+"\nG23 = "+str(g23.get("result"))+"\nG24 = "+result+"\nSERVER_GUARANTEED = "+str(ok).upper()+"\nSERVER_CERTIFIED = "+str(ok).upper()+"\nSERVER_READY_FINAL = "+result+"\nFINAL_DIGEST = "+str(c.get("candidate_digest_sha256"))+"\nFINDINGS = "+repr(f)+"\n",encoding="utf-8")
 print(json.dumps(obj,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
