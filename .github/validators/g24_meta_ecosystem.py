#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--g23",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    candidate=json.loads(Path(q.candidate).read_text(encoding="utf-8"))
    g23=json.loads(Path(q.g23).read_text(encoding="utf-8"))
    findings=[]
    if g23.get("gate")!="G23": findings.append("INVALID_G23_RECORD")
    if g23.get("candidate_digest")!=candidate.get("candidate_digest"): findings.append("DIGEST_MISMATCH_G23_VS_CANDIDATE")
    if g23.get("repair_performed") is not False: findings.append("G23_REPAIR_PATH_VIOLATION")
    if g23.get("result")!="PASS": findings.append("G23_NOT_PASS")
    result="PASS" if not findings else "HOLD"
    decision={
      "schema":"G24_META_ECOSYSTEM_CERTIFICATION_DECISION/1.0",
      "gate":"G24",
      "artifact_id":candidate.get("artifact_id"),
      "candidate_digest":candidate.get("candidate_digest"),
      "g23_candidate_digest":g23.get("candidate_digest"),
      "g23_result":g23.get("result"),
      "repair_performed":False,
      "decision":result,
      "findings":findings,
      "scope":candidate.get("scope"),
      "certification_propagation":False,
      "operational_authorization":"SEPARATE_NOT_IMPLIED",
      "canonical_admission":"SEPARATE_NOT_IMPLIED"
    }
    Path(q.out).write_text(json.dumps(decision,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(decision,sort_keys=True))
    raise SystemExit(0 if result=="PASS" else 3)

if __name__=="__main__":
    main()
