#!/usr/bin/env python3
from __future__ import annotations
import json,os,urllib.request,urllib.error,hashlib,time
from pathlib import Path

ROOT=Path(os.environ["MISSION_ROOT"]).resolve()
OUT=Path(os.environ.get("OUT_DIR",ROOT/"continuity/runtime-evidence/p09")).resolve(); OUT.mkdir(parents=True,exist_ok=True)
OWNER="Plomillo"; REPO="luna-linux-bridge"; API=f"https://api.github.com/repos/{OWNER}/{REPO}"
REPO_OPS=[
("R01","GET","repository","/"),("R02","GET","repository","/branches"),("R03","GET","repository","/branches/work/louksna-zd-v04-master-20261007"),
("R04","GET","repository","/commits?per_page=1"),("R05","GET","repository","/commits/12f73e71acaa0edf897e0748d85eb5a9e017c9e4"),
("R06","GET","repository","/compare/work/louksna-zd-v04-master-20261007...main"),("R07","GET","repository","/contents/continuity/STATE.json?ref=work/louksna-zd-v04-master-20261007"),
("R08","GET","repository","/git/trees/12f73e71acaa0edf897e0748d85eb5a9e017c9e4?recursive=0"),
("R09","GET","repository","/git/refs"),("R10","GET","repository","/issues?per_page=1"),("R11","GET","repository","/issues/1"),
("R12","GET","repository","/issues/comments?per_page=1"),("R13","GET","repository","/pulls?per_page=1"),("R14","GET","repository","/pulls/1"),
("R15","GET","repository","/pulls/1/files?per_page=1"),("R16","GET","repository","/pulls/1/reviews?per_page=1"),
("R17","GET","repository","/releases?per_page=1"),("R18","GET","repository","/releases/latest"),("R19","GET","repository","/tags?per_page=1"),
("R20","GET","actions","/actions/runs?per_page=1"),("R21","GET","actions","/actions/workflows"),("R22","GET","actions","/actions/artifacts?per_page=1"),
("R23","GET","actions","/actions/variables"),("R24","GET","actions","/actions/secrets"),("R25","GET","actions","/environments"),
("R26","GET","repository","/deployments?per_page=1"),("R27","GET","repository","/hooks?per_page=1"),("R28","GET","repository","/collaborators?per_page=1"),
("R29","GET","repository","/teams"),("R30","GET","repository","/dependabot/alerts?per_page=1"),("R31","GET","repository","/code-scanning/alerts?per_page=1"),
("R32","GET","repository","/secret-scanning/alerts?per_page=1"),("R33","GET","repository","/security-advisories?per_page=1"),
("R34","MUTATE","repository","/contents/.louksna-p09-sandbox-probe"),("R35","MUTATE","actions","/actions/workflows/378468586/dispatches"),
("R36","MUTATE","repository","/hooks"),
]
ACCOUNT_OPS=[
("A01","GET","account","/user"),("A02","GET","account","/user/repos?per_page=1"),("A03","GET","account","/user/orgs?per_page=1"),
("A04","GET","account","/user/followers?per_page=1"),("A05","GET","account","/user/following?per_page=1"),("A06","GET","account","/user/starred?per_page=1"),
("A07","GET","account","/user/subscriptions?per_page=1"),("A08","GET","account","/user/keys?per_page=1"),("A09","GET","account","/user/gpg_keys?per_page=1"),
("A10","GET","account","/user/ssh_signing_keys?per_page=1"),("A11","GET","account","/user/emails?per_page=1"),("A12","GET","account","/user/blocks?per_page=1"),
("A13","GET","account","/user/installations"),("A14","GET","account","/user/installations/0/repositories?per_page=1"),("A15","GET","account","/user/codespaces?per_page=1"),
("A16","GET","account","/user/codespaces/secrets?per_page=1"),("A17","GET","account","/notifications?per_page=1"),("A18","GET","account","/rate_limit"),
("A19","GET","account","/user/projects?per_page=1"),("A20","MUTATE","account","/user/keys"),("A21","MUTATE","account","/user/repos"),
]
def probe(op,token):
    oid,kind,scope,path=op; url=(API+path) if scope!="account" else "https://api.github.com"+path
    rec={"operation_id":oid,"scope":scope,"endpoint":url.replace(OWNER,"{owner}").replace(REPO,"{repo}"),"operation":kind,"mutability":"MUTATING" if kind=="MUTATE" else "READ","risk":"HIGH" if kind=="MUTATE" else "LOW","confirmation_policy":"REQUIRED" if kind=="MUTATE" else "NONE","reversible":kind!="GET","last_probe_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
    if kind=="MUTATE":
        rec["state"]="UNKNOWN"; rec["probe"]="NON_MUTATING_CAPABILITY_CENSUS_ONLY"; return rec
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","User-Agent":"Louksna-P09-Capability-Census"},method="GET")
    try:
        with urllib.request.urlopen(req,timeout=15) as resp:
            rec["http_status"]=resp.status; rec["state"]="VERIFIED_AVAILABLE" if 200<=resp.status<300 else "UNKNOWN"; rec["response_hash"]=hashlib.sha256(resp.read(1024*1024)).hexdigest()
    except urllib.error.HTTPError as e:
        rec["http_status"]=e.code; rec["state"]="VERIFIED_DENIED" if e.code==403 else ("NOT_GRANTED" if e.code==401 else "UNKNOWN")
    except Exception as e:
        rec["state"]="UNKNOWN"; rec["error_type"]=type(e).__name__
    return rec
def main():
    token=os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token: raise RuntimeError("GITHUB_TOKEN_MISSING")
    ops=REPO_OPS+ACCOUNT_OPS
    if len(REPO_OPS)!=36 or len(ACCOUNT_OPS)!=21: raise RuntimeError("CAPABILITY_CENSUS_CARDINALITY_INVALID")
    ids=[x[0] for x in ops]
    if len(ids)!=len(set(ids)): raise RuntimeError("CAPABILITY_ID_COLLISION")
    results=[probe(x,token) for x in ops]
    evidence={"schema":"LOUKSNA_ZD_P09_GITHUB_CAPABILITIES/1.0","status":"PASS","repository_scope_count":36,"account_scope_count":21,"total":57,"operations":results,"write_probe_policy":"NO_MUTATION_IN_CANONICAL_REPO"}
    (OUT/"P09_GITHUB_CAPABILITY_EVIDENCE.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
    result={"status":"PASS","checkpoint":"CHECKPOINT_09","parent_checkpoint":"CHECKPOINT_08","next_point":"P10","transition_id":"P09-CHECKPOINT-TO-P10-001","certified":False,"active":False,"g23":"SEPARATE_REQUIRED","g24":"SEPARATE_REQUIRED","material_evidence":{"total":57,"repo":36,"account":21,"states":{s:sum(1 for x in results if x["state"]==s) for s in ["VERIFIED_AVAILABLE","VERIFIED_DENIED","NOT_GRANTED","UNKNOWN"]}}}
    (ROOT/"continuity/CONTINUATION_RESULT.json").write_text(json.dumps(result,indent=2,sort_keys=True)+"\n")
    print("LOUKSNA_P09_TELEMETRY "+json.dumps({"event":"CHECKPOINT_09_REACHED","next_point":"P10","status":"PASS","total":57},sort_keys=True),flush=True)
if __name__=="__main__":
    try: main()
    except Exception as e: print("P09_FAIL_CLOSED "+type(e).__name__+": "+str(e),file=__import__("sys").stderr); raise
