from __future__ import annotations
import argparse, hashlib, json, pathlib, re, subprocess, sys
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parent
ORCHESTRATOR=ROOT.parent
sys.path.insert(0,str(ROOT))
import cli_registry
CONTRACT=ROOT/"cli_contract.json"; MANIFEST=ORCHESTRATOR/"punto.json"
ALLOWED={"npm","uv","python","python3","pipx","pixi","apt-get","dnf","brew"}
SENSITIVE=re.compile(r"(token|password|passwd|secret|api[_-]?key|authorization|credential)",re.I)
def utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def digest(b): return hashlib.sha256(b).hexdigest()
def read(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def write(p,x):
 p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp"); t.write_text(json.dumps(x,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); t.replace(p)
def build_plan():
 c=read(CONTRACT); actions=[]
 for d in c["domains"]:
  status="BLOCKED_OFFICIAL_DISTRIBUTION_UNVERIFIED" if d.get("status","").startswith("BLOCKED") else ("AUDIT_ONLY_NO_INSTALL_MUTATION" if d["id"]=="CLI_PYTHON" else "BLOCKED_VERSION_PIN_REQUIRED")
  actions.append({"domain_id":d["id"],"package":d.get("package"),"status":status,"version_pin":None,"mutations_authorized":False})
 return {"schema":"CAJITA_CLI_INSTALL_PLAN/1.0","created_at_utc":utc(),"contract_sha256":digest(CONTRACT.read_bytes()),"manifest_sha256":digest(MANIFEST.read_bytes()),"domain_order":c["domain_order"],"status":"BLOCKED_FAIL_CLOSED","actions":actions,"commands":[],"no_mutations":True,"reason":"A plan cannot mutate the host until every executable install has an exact pin, official-source integrity proof, checkpoint, rollback, post-validation, and explicit exact-plan SHA approval.","certification":"NOT_GRANTED"}
def validate_step(step,domain):
 argv=step.get("argv") if isinstance(step,dict) else None
 if not isinstance(argv,list) or not argv or any(not isinstance(x,str) or not x for x in argv): raise ValueError("INSTALL_STEP_ARGV_INVALID:"+domain)
 exe=pathlib.Path(argv[0]).name
 if exe not in ALLOWED: raise ValueError("INSTALL_EXECUTABLE_NOT_ALLOWLISTED:"+exe)
 if any(SENSITIVE.search(x) for x in argv): raise ValueError("POSSIBLE_SECRET_IN_ARGV_DENIED:"+domain)
 if any(x in {"upgrade","dist-upgrade","remove","purge","autoremove","clean"} for x in argv[1:]): raise ValueError("DESTRUCTIVE_PACKAGE_OPERATION_DENIED")
 return argv
def apply_plan(path,approved):
 raw=pathlib.Path(path).read_bytes()
 if not approved or digest(raw).lower()!=approved.lower(): raise ValueError("PLAN_SHA256_APPROVAL_MISMATCH")
 plan=json.loads(raw); c=read(CONTRACT)
 if plan.get("schema")!="CAJITA_CLI_INSTALL_PLAN/1.0" or plan.get("status")!="READY_TO_APPLY": raise ValueError("PLAN_NOT_READY_FAIL_CLOSED")
 if plan.get("contract_sha256")!=digest(CONTRACT.read_bytes()) or plan.get("manifest_sha256")!=digest(MANIFEST.read_bytes()): raise ValueError("INPUT_CHANGED_SINCE_PLAN")
 cmap={d["id"]:d for d in c["domains"]}
 for a in plan.get("actions",[]):
  d=cmap.get(a.get("domain_id"))
  if not d or not a.get("version_pin") or a.get("version_pin")!=d.get("version_pin"): raise ValueError("VERSION_PIN_MISMATCH")
  if a.get("official_source") not in d.get("official_sources",[]) or a.get("source_integrity_status")!="PASS": raise ValueError("SOURCE_INTEGRITY_NOT_PASS")
  if not a.get("checkpoint_id") or not a.get("rollback_steps") or not a.get("steps"): raise ValueError("CHECKPOINT_ROLLBACK_OR_STEPS_MISSING")
  for s in a["steps"]+a["rollback_steps"]: validate_step(s,d["id"])
 return {"status":"DENIED_FAIL_CLOSED","reason":"Host mutation is disabled in this release; execute only a versioned, independently reviewed installer implementation with the approved evidence chain.","mutations_performed":False,"certification":"NOT_GRANTED"}
def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest="command",required=True)
 a=sub.add_parser("audit"); a.add_argument("--output",type=pathlib.Path)
 q=sub.add_parser("plan"); q.add_argument("--output",type=pathlib.Path)
 x=sub.add_parser("apply-plan"); x.add_argument("--plan",required=True); x.add_argument("--approve-sha256",required=True)
 z=p.parse_args()
 if z.command=="audit": result=cli_registry.run_registry(); result["manager"]={"status":"IMPLEMENTED","mode":"READ_ONLY_AUDIT"}
 elif z.command=="plan": result=build_plan()
 else:
  try: result=apply_plan(z.plan,z.approve_sha256)
  except Exception as e: result={"status":"DENIED_FAIL_CLOSED","reason":str(e)[:500],"mutations_performed":False,"certification":"NOT_GRANTED"}
 if z.output: write(z.output,result)
 print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
 return 0 if (z.command=="plan" or (z.command=="audit" and result.get("infrastructure_status")=="PASS") or result.get("status")=="PASS") else 2
if __name__=="__main__": raise SystemExit(main())
