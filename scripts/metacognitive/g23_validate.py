#!/usr/bin/env python3
import argparse, hashlib, json, pathlib

EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
REQUIRED_LANES={"debian13","android36_37","windows","rclone","remote_range","translation_scale","telemetry"}

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def digest_dir(root):
 root=pathlib.Path(root); rows=[]
 for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
  rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha(f),"size":f.stat().st_size})
 return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest(),rows

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--candidate",required=True); ap.add_argument("--out",required=True); q=ap.parse_args()
 root=pathlib.Path(q.candidate); frozen=json.loads((root/"FROZEN_CANDIDATE.json").read_text())
 actual,rows=digest_dir(root)
 readiness=json.loads((root/"READINESS.json").read_text())
 graph=json.loads((root/"ECOSYSTEM_GRAPH.json").read_text())
 binds=json.loads((root/"CAPABILITY_BINDINGS.json").read_text())
 lane=json.loads((root/"LANE_EVIDENCE.json").read_text())["lanes"]
 core=json.loads((root/"CORE_SELFTEST.json").read_text())
 present={k for k,v in lane.items() if isinstance(v,dict) and v.get("status")=="PASS"}
 failures=[]
 if actual!=frozen["candidate_digest_sha256"]: failures.append("CANDIDATE_DIGEST_MISMATCH")
 if readiness.get("status")!="PASS": failures.append("READINESS_NOT_PASS")
 if graph.get("capability_count")!=59 or binds.get("count")!=59: failures.append("MCAP59_INCOMPLETE")
 if core.get("status")!="PASS": failures.append("CORE_SELFTEST_NOT_PASS")
 if not REQUIRED_LANES.issubset(present): failures.append("REQUIRED_LANES_MISSING:"+",".join(sorted(REQUIRED_LANES-present)))
 status="PASS" if not failures else "FAIL"
 report={"schema":"G23_INDEPENDENT_VALIDATION/1.0","status":status,"candidate_digest_sha256":actual,
         "frozen_digest_sha256":frozen["candidate_digest_sha256"],"repair_allowed":False,
         "validator_mode":"FRESH_READ_ONLY_RECOMPUTE","required_lanes":sorted(REQUIRED_LANES),
         "present_pass_lanes":sorted(present),"failures":failures,"g24_authorized":status=="PASS"}
 pathlib.Path(q.out).write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
 print(json.dumps(report,sort_keys=True))
 raise SystemExit(0 if status=="PASS" else 3)
if __name__=="__main__": main()
