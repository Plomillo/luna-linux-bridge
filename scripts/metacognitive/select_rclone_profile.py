#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

LADDER=(8,16,32,48,64)

def choose(profiles):
    valid=[]
    for p in profiles:
        if p.get("workers") not in LADDER: continue
        if not p.get("checksum_pass",False): continue
        if p.get("corruption",False): continue
        if p.get("retry_rate",1)>0.05: continue
        if p.get("throttling",1)>0.10: continue
        if p.get("ram_safe",False) is not True: continue
        valid.append(p)
    if not valid: return None
    return max(valid,key=lambda p:(p.get("bytes_per_second",0),-p["workers"]))

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    profiles=json.loads(Path(q.input).read_text(encoding="utf-8"))
    selected=choose(profiles)
    if selected is None: raise SystemExit("NO_SAFE_RCLONE_PROFILE")
    result={
      "schema":"RCLONE_ADAPTIVE_PROFILE_SELECTION/1.0",
      "status":"PASS",
      "ladder":list(LADDER),
      "selected_workers":selected["workers"],
      "selected_bytes_per_second":selected["bytes_per_second"],
      "selection_rule":"MAX_VERIFIED_THROUGHPUT_SUBJECT_TO_SAFETY_CONSTRAINTS",
      "live_remote_benchmark":False
    }
    out=Path(q.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
