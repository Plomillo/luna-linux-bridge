#!/usr/bin/env python3
from __future__ import annotations
import argparse, base64, json, os, sys, urllib.error, urllib.parse, urllib.request

WORKFLOW_NAME="Metacognitive Ecosystem R4 — cloud materialization and PUAC2"
RELEASE_PATH="ecosystem/metacognitive-operational-v1/CERTIFIED_RELEASE_RECORD.json"

def api(repo,path,token):
    req=urllib.request.Request(
        f"https://api.github.com/repos/{repo}{path}",
        headers={
            "Authorization":f"Bearer {token}",
            "Accept":"application/vnd.github+json",
            "X-GitHub-Api-Version":"2022-11-28",
            "User-Agent":"louksna-metacognitive-trust-root"
        }
    )
    with urllib.request.urlopen(req,timeout=30) as r:
        return json.load(r)

def exact_head(repo,head,token):
    q=urllib.parse.urlencode({"head_sha":head,"status":"success","per_page":100})
    d=api(repo,f"/actions/runs?{q}",token)
    xs=[
        x for x in d.get("workflow_runs",[])
        if x.get("name")==WORKFLOW_NAME
        and x.get("head_sha")==head
        and x.get("conclusion")=="success"
    ]
    if not xs:
        return None
    xs.sort(key=lambda x:x.get("created_at",""),reverse=True)
    x=xs[0]
    return {
        "schema":"METACOGNITIVE_PRODUCER_RESOLUTION/1.0",
        "status":"PASS",
        "resolution_mode":"EXACT_PR_HEAD",
        "producer_run_id":x["id"],
        "candidate_head_sha":head,
        "release_head_sha":head,
        "expected_candidate_digest":"",
        "release_record_path":None
    }

def release_record(repo,head,token):
    quoted=urllib.parse.quote(RELEASE_PATH,safe="/")
    q=urllib.parse.urlencode({"ref":head})
    try:
        d=api(repo,f"/contents/{quoted}?{q}",token)
    except urllib.error.HTTPError as e:
        if e.code==404:
            return None
        raise
    if d.get("type")!="file" or d.get("encoding")!="base64":
        raise SystemExit("RELEASE_RECORD_CONTENTS_FORMAT_INVALID")
    raw=base64.b64decode(d.get("content",""))
    try:
        rec=json.loads(raw)
    except Exception as e:
        raise SystemExit(f"RELEASE_RECORD_JSON_INVALID:{e}")
    if rec.get("schema")!="LOUKSNA_METACOGNITIVE_RELEASE/1.0":
        raise SystemExit("RELEASE_RECORD_SCHEMA_INVALID")
    digest=str(rec.get("candidate_digest_sha256","")).strip()
    producer=rec.get("producer") or {}
    run_id=producer.get("run_id")
    source_commit=str(producer.get("source_commit","")).strip()
    if not digest or not isinstance(run_id,int) or not source_commit:
        raise SystemExit("RELEASE_RECORD_PRODUCER_BINDING_INCOMPLETE")
    run=api(repo,f"/actions/runs/{run_id}",token)
    if run.get("name")!=WORKFLOW_NAME:
        raise SystemExit("RELEASE_RECORD_WORKFLOW_NAME_MISMATCH")
    if run.get("conclusion")!="success":
        raise SystemExit("RELEASE_RECORD_PRODUCER_RUN_NOT_SUCCESS")
    if run.get("head_sha")!=source_commit:
        raise SystemExit("RELEASE_RECORD_SOURCE_COMMIT_MISMATCH")
    if producer.get("artifact_name")!="metacognitive-ecosystem-r4-frozen-candidate":
        raise SystemExit("RELEASE_RECORD_ARTIFACT_NAME_MISMATCH")
    return {
        "schema":"METACOGNITIVE_PRODUCER_RESOLUTION/1.0",
        "status":"PASS",
        "resolution_mode":"CONTENT_ADDRESSED_RELEASE",
        "producer_run_id":run_id,
        "candidate_head_sha":source_commit,
        "release_head_sha":head,
        "expected_candidate_digest":digest,
        "release_record_path":RELEASE_PATH,
        "release_id":rec.get("release_id"),
        "recorded_g23_status":(rec.get("g23") or {}).get("status"),
        "recorded_g24_status":(rec.get("g24") or {}).get("status")
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo",required=True)
    ap.add_argument("--pr-head",required=True)
    ap.add_argument("--token-env",default="GH_TOKEN")
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    token=os.environ.get(q.token_env,"")
    if not token:
        raise SystemExit("GITHUB_TOKEN_MISSING")
    result=exact_head(q.repo,q.pr_head,token)
    if result is None:
        result=release_record(q.repo,q.pr_head,token)
    if result is None:
        raise SystemExit("NO_SUCCESSFUL_PRODUCER_RUN_OR_VALID_RELEASE_RECORD")
    with open(q.out,"w",encoding="utf-8") as f:
        json.dump(result,f,indent=2,sort_keys=True)
        f.write("\n")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
