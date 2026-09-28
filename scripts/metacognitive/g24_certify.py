#!/usr/bin/env python3
import argparse, hashlib, json, pathlib

EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def digest_dir(root):
 root=pathlib.Path(root); rows=[]
 for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
  rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha(f),"size":f.stat().st_size})
 return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--candidate",required=True); ap.add_argument("--g23",required=True); ap.add_argument("--out",required=True); q=ap.parse_args()
 root=pathlib.Path(q.candidate); g23=json.loads(pathlib.Path(q.g23).read_text()); frozen=json.loads((root/"FROZEN_CANDIDATE.json").read_text())
 actual=digest_dir(root); failures=[]
 if g23.get("status")!="PASS": failures.append("G23_NOT_PASS")
 if not g23.get("g24_authorized"): failures.append("G23_DID_NOT_AUTHORIZE_G24")
 if actual!=g23.get("candidate_digest_sha256") or actual!=frozen.get("candidate_digest_sha256"): failures.append("DIGEST_IDENTITY_BROKEN")
 status="PASS" if not failures else "FAIL"
 cert={"schema":"G24_CERTIFICATION/1.0","status":status,"candidate_digest_sha256":actual,
       "scope":"METACOGNITIVE_OPERATIONAL_ECOSYSTEM_V1_CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK",
       "authority":"Louksna.md","certification_propagation":False,"canonical_mutation":False,
       "external_provider_integrations_certified":False,"training_executed":False,
       "failures":failures,"active_authorized":status=="PASS"}
 pathlib.Path(q.out).write_text(json.dumps(cert,indent=2,sort_keys=True)+"\n")
 print(json.dumps(cert,sort_keys=True))
 raise SystemExit(0 if status=="PASS" else 4)
if __name__=="__main__": main()
