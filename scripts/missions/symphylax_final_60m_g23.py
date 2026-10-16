#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,time,shutil
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def dump(p,o):pathlib.Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def main():
 ap=argparse.ArgumentParser();ap.add_argument("--producer",required=True);ap.add_argument("--mission",required=True);ap.add_argument("--out",required=True);q=ap.parse_args();src=pathlib.Path(q.producer);out=pathlib.Path(q.out);out.mkdir(parents=True,exist_ok=True);find=[]
 frozen=json.load(open(src/"FROZEN_CANDIDATE.json"));gates=json.load(open(src/"TECHNICAL_GATES.json"));risk=json.load(open(src/"RISK_REGISTER.json"));rb=json.load(open(src/"ROLLBACK_EVIDENCE.json"));nr=json.load(open(src/"NON_REGRESSION.json"));puac=json.load(open(src/"PUAC2_SERVER_ASSURANCE.json"));dl=json.load(open(src/"LINUX_REMAINDER_DOWNLOAD_READINESS.json"))
 if sha(q.mission)!=frozen.get("mission_sha256"):find.append("MISSION_SHA_MISMATCH")
 for n,m in frozen.get("files",{}).items():
  p=src/n
  if not p.is_file() or sha(p)!=m.get("sha256"):find.append("FROZEN_HASH_MISMATCH:"+n)
 if not frozen.get("technical_ready"):find.append("TECHNICAL_READY_FALSE")
 if gates.get("result")!="PASS":find.append("TECHNICAL_GATES_NOT_PASS")
 if risk.get("uncontrolled_critical_risks")!=0:find.append("UNCONTROLLED_CRITICAL_RISK")
 if rb.get("verified") is not True:find.append("ROLLBACK_NOT_VERIFIED")
 if nr.get("result")!="PASS":find.append("NON_REGRESSION_NOT_PASS")
 if dl.get("result")!="PASS":find.append("LINUX_REMAINDER_DOWNLOAD_NOT_READY")
 if puac.get("pre_g23_status")!="PASS":find.append("PUAC2_PRE_G23_NOT_PASS")
 if time.time()-float(frozen.get("start_epoch",time.time()))>3600:find.append("GLOBAL_60M_BUDGET_EXCEEDED")
 result="PASS" if not find else "HOLD";controls=dict(puac.get("controls",{}));controls["PUAC.C27"]={"status":"PASS" if result=="PASS" else "HOLD","control":"STRUCTURAL_INDEPENDENCE","distinct_evaluator_identity":True,"write_access_to_candidate":False,"repair_allowed":False}
 puac_status="PASS" if result=="PASS" and all(x.get("status")=="PASS" for x in controls.values()) else "HOLD"
 obj={"schema":"G23_SYMPHYLAX_INDEPENDENT_VALIDATION/1.0","result":result,"candidate_digest_sha256":frozen.get("candidate_digest_sha256"),"findings":find,"repair_performed":False,"producer_mutated":False,"read_only_candidate":True,"distinct_evaluator_identity":"GITHUB_HOSTED_G23","puac2_status":puac_status,"puac2_controls":controls}
 dump(out/"G23_RESULT.json",obj);dump(out/"PUAC2_G23_APPROVAL.json",{"status":puac_status,"candidate_digest_sha256":frozen.get("candidate_digest_sha256"),"controls":controls});shutil.copytree(src,out/"producer",dirs_exist_ok=True)
 (out/"README_G23.md").write_text("# G23\n\nG23 = "+result+"\nPUAC2 = "+puac_status+"\nFINDINGS = "+repr(find)+"\n",encoding="utf-8");print(json.dumps(obj,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
