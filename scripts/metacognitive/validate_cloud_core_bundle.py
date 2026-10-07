#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from pathlib import Path

REQUIRED={
 "GRAPH_VALIDATION.json",
 "DEBIAN13_PROBE.json",
 "ANDROID_API_PROBE.json",
 "WINDOWS_PROBE.json",
 "REMOTE_CORPUS_PROBE.json",
 "RCLONE_GOVERNOR_PROBE.json",
}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    root=Path(q.root)
    files={p.name:p for p in root.rglob("*.json")}
    missing=sorted(REQUIRED-set(files))
    failures=[]
    details={}
    for name in sorted(REQUIRED & set(files)):
        d=json.loads(files[name].read_text(encoding="utf-8"))
        details[name]=d
        if d.get("status")!="PASS":
            failures.append({"file":name,"status":d.get("status")})
    if missing or failures:
        result={"schema":"CLOUD_CORE_BUNDLE/1.0","status":"FAIL","missing":missing,"failures":failures}
        Path(q.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        print(json.dumps(result,sort_keys=True))
        raise SystemExit(3)
    result={
      "schema":"CLOUD_CORE_BUNDLE/1.0",
      "status":"PASS",
      "required_evidence_count":len(REQUIRED),
      "evidence_files":sorted(REQUIRED),
      "heavy_compute_on_user_host":False,
      "github_hosted":True,
      "remote_corpus_full_materialization":False,
      "rclone_live_remote_benchmark":False,
      "g23":"NOT_PERFORMED",
      "g24":"NOT_PERFORMED"
    }
    Path(q.out).write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
