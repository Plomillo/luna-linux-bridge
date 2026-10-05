#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib

def compile_rubric(profile):
    rubric=profile.get("rubric") or {}
    criteria=rubric.get("criteria") or []
    obligations=[]
    total=0.0
    for row in criteria:
        cid=str(row.get("id","")).strip()
        if not cid:
            raise ValueError("RUBRIC_CRITERION_ID_MISSING")
        points=float(row.get("points",0))
        total+=points
        validation=str(row.get("validation","UNKNOWN"))
        obligations.append({
          "criterion_id":cid,
          "points":points,
          "requirement_text":row.get("text"),
          "validation_class":validation,
          "automated_assist":("AUTOMATED" in validation),
          "independent_or_human_required":("G23" in validation or "HUMAN" in validation),
          "claim_status":"UNKNOWN",
          "evidence_ref":None
        })
    declared=float(rubric.get("declared_total_points",-1))
    if abs(total-declared)>1e-9:
        raise ValueError(f"RUBRIC_TOTAL_MISMATCH:{total}!={declared}")
    return {
      "schema":"DOCUMENT_FACTORY_RUBRIC_OBLIGATIONS/1.0",
      "profile_id":profile.get("profile_id"),
      "profile_version":profile.get("profile_version"),
      "declared_total_points":declared,
      "criterion_count":len(obligations),
      "obligations":obligations,
      "certification_authority":False
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("profile")
    ap.add_argument("--out")
    args=ap.parse_args()
    profile=json.loads(pathlib.Path(args.profile).read_text(encoding="utf-8"))
    result=compile_rubric(profile)
    text=json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n"
    if args.out:
        pathlib.Path(args.out).write_text(text,encoding="utf-8")
    else:
        print(text,end="")

if __name__=="__main__":
    main()
