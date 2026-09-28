#!/usr/bin/env python3
import argparse,hashlib,json,pathlib,time,shutil
BUDGET=360
def sha(p):
 h=hashlib.sha256()
 with open(p,"rb") as f:
  for b in iter(lambda:f.read(1024*1024),b""):h.update(b)
 return h.hexdigest()
def dump(p,o):pathlib.Path(p).write_text(json.dumps(o,indent=2,sort_keys=True)+"\n",encoding="utf-8")
def main():
 a=argparse.ArgumentParser();a.add_argument("--candidate",required=True);a.add_argument("--mission",required=True);a.add_argument("--out",required=True);q=a.parse_args()
 src=pathlib.Path(q.candidate);out=pathlib.Path(q.out);out.mkdir(parents=True,exist_ok=True);f=[]
 c=json.load(open(src/"FINAL_CANDIDATE.json"));g=json.load(open(src/"TECHNICAL_GATES.json"));p=json.load(open(src/"PUAC2_RESULT.json"));r=json.load(open(src/"RISK_REGISTER.json"));rb=json.load(open(src/"ROLLBACK_EVIDENCE.json"));nr=json.load(open(src/"NON_REGRESSION_REPORT.json"));dl=json.load(open(src/"LINUX_REMAINDER_DOWNLOAD_READINESS.json"))
 if sha(q.mission)!=c.get("mission_sha256"):f.append("MISSION_SHA_MISMATCH")
 for n,m in c.get("files",{}).items():
  x=src/n
  if not x.is_file() or sha(x)!=m.get("sha256"):f.append("FROZEN_HASH_MISMATCH:"+n)
 if not c.get("technical_ready"):f.append("TECHNICAL_READY_FALSE")
 if g.get("result")!="PASS":f.append("TECHNICAL_GATES_NOT_PASS")
 if r.get("uncontrolled_critical_risks")!=0:f.append("UNCONTROLLED_CRITICAL_RISK")
 if rb.get("verified") is not True:f.append("ROLLBACK_NOT_VERIFIED")
 if nr.get("result")!="PASS":f.append("NON_REGRESSION_NOT_PASS")
 if dl.get("result")!="PASS":f.append("DOWNLOAD_READINESS_NOT_PASS")
 if p.get("pre_g23_status")!="PASS":f.append("PUAC2_PRE_G23_NOT_PASS")
 if time.time()-float(c.get("start_epoch",time.time()))>BUDGET:f.append("GLOBAL_360S_BUDGET_EXHAUSTED")
 result="PASS" if not f else "HOLD";controls=dict(p.get("controls",{}));controls["PUAC.C27"]={"status":"PASS" if result=="PASS" else "HOLD","distinct_evaluator_identity":"GITHUB_HOSTED_G23","write_access_to_candidate":False,"repair_allowed":False}
 puac="PASS" if result=="PASS" and all(x.get("status")=="PASS" for x in controls.values()) else "HOLD"
 obj={"schema":"G23_SYMPHYLAX_6M/1.0","result":result,"candidate_digest_sha256":c.get("candidate_digest_sha256"),"puac2":puac,"controls":controls,"findings":f,"read_only_candidate":True,"repair_performed":False,"producer_mutated":False}
 dump(out/"G23_RESULT.json",obj);dump(out/"PUAC2_RESULT.json",{"status":puac,"candidate_digest_sha256":c.get("candidate_digest_sha256"),"controls":controls});shutil.copytree(src,out/"candidate",dirs_exist_ok=True)
 print(json.dumps(obj,sort_keys=True));return 0
if __name__=="__main__":raise SystemExit(main())
