from __future__ import annotations
import argparse
import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT=pathlib.Path(__file__).resolve().parent
ORCHESTRATOR=ROOT.parent
sys.path.insert(0,str(ROOT))
import cli_registry
CONTRACT=ROOT/"cli_contract.json"
MANIFEST=ORCHESTRATOR/"punto.json"
SENSITIVE=re.compile(r"(token|password|passwd|secret|api[_-]?key|authorization|credential)",re.I)
INSTALL_TOOLS={"npm","uv","pipx","apt-get","dnf"}
def utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def digest(data): return hashlib.sha256(data).hexdigest()
def read_json(path):
    obj=json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
    if not isinstance(obj,dict): raise ValueError("JSON_ROOT_NOT_OBJECT")
    return obj
def atomic_write(path,obj):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_name(path.name+".tmp")
    tmp.write_text(json.dumps(obj,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8")
    tmp.replace(path)
def build_plan():
    contract=read_json(CONTRACT); actions=[]
    for d in contract["domains"]:
        if d.get("id")=="CLI_PYTHON":
            status="AUDIT_ONLY_NO_INSTALL_MUTATION"
        elif not d.get("version_pin"):
            status="BLOCKED_VERSION_PIN_REQUIRED"
        elif d.get("status","").startswith("BLOCKED"):
            status="BLOCKED_OFFICIAL_SOURCE_UNVERIFIED"
        else:
            status="BLOCKED_SOURCE_INTEGRITY_EVIDENCE_REQUIRED"
        actions.append({"domain_id":d["id"],"package":d.get("package"),"version_pin":d.get("version_pin"),"status":status,"mutations_authorized":False})
    return {"schema":"CAJITA_CLI_INSTALL_PLAN/1.0","created_at_utc":utc(),"contract_sha256":digest(CONTRACT.read_bytes()),"manifest_sha256":digest(MANIFEST.read_bytes()),"domain_order":contract["domain_order"],"status":"BLOCKED_FAIL_CLOSED","actions":actions,"commands":[],"no_mutations":True,"reason":"No vendor install is run without exact contract pins, source-integrity evidence, rollback steps and an approved exact plan SHA-256.","certification":"NOT_GRANTED"}
def validate_argv(step,domain,rollback=False):
    if not isinstance(step,dict) or not isinstance(step.get("argv"),list) or not step["argv"] or any(not isinstance(x,str) or not x for x in step["argv"]):
        raise ValueError("INSTALL_STEP_ARGV_INVALID:"+domain)
    argv=step["argv"]; exe=pathlib.Path(argv[0]).name; args=argv[1:]
    if exe not in INSTALL_TOOLS: raise ValueError("INSTALL_EXECUTABLE_NOT_ALLOWLISTED:"+exe)
    if any(SENSITIVE.search(x) for x in argv): raise ValueError("POSSIBLE_SECRET_IN_ARGV_DENIED:"+domain)
    if any(x in {"upgrade","dist-upgrade","purge","autoremove","autoclean","clean"} for x in args):
        raise ValueError("DESTRUCTIVE_PACKAGE_OPERATION_DENIED")
    if exe=="npm":
        allowed={"install","uninstall"}
        if not args or args[0] not in ({"uninstall"} if rollback else {"install"}): raise ValueError("NPM_OPERATION_NOT_ALLOWLISTED")
        if "--global" not in args or "--prefix" not in args: raise ValueError("NPM_INSTALL_MUST_USE_EXPLICIT_USER_PREFIX")
        package_args=[x for x in args if not x.startswith("-") and x not in allowed]
        if not package_args: raise ValueError("NPM_PACKAGE_REQUIRED")
        if not rollback and not any(re.search(r"@(?:[0-9]+\.){1,2}[0-9]+",x) for x in package_args):
            raise ValueError("NPM_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="uv":
        if not args or args[0] not in ({"tool","uninstall"} if rollback else {"tool","install"}): raise ValueError("UV_OPERATION_NOT_ALLOWLISTED")
        if not rollback and not any(re.search(r"==[^=]+$",x) for x in args): raise ValueError("UV_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="pipx":
        expected="uninstall" if rollback else "install"
        if not args or args[0]!=expected: raise ValueError("PIPX_OPERATION_NOT_ALLOWLISTED")
        if not rollback and not any(re.search(r"==[^=]+$",x) for x in args): raise ValueError("PIPX_EXACT_VERSION_PIN_REQUIRED")
    elif exe=="apt-get":
        required="remove" if rollback else "install"
        if required not in args or (not rollback and not any(re.search(r"=[^=]+$",x) for x in args if not x.startswith("-"))):
            raise ValueError("APT_EXACT_VERSIONED_OPERATION_REQUIRED")
        if any(x in {"-y","--yes"} for x in args) is False: raise ValueError("APT_INTERACTIVE_OR_UNCONFIRMED_OPERATION_DENIED")
    elif exe=="dnf":
        required="remove" if rollback else "install"
        if required not in args or (not rollback and not any(re.search(r"=[^=]+$",x) for x in args if not x.startswith("-"))):
            raise ValueError("DNF_EXACT_VERSIONED_OPERATION_REQUIRED")
        if "-y" not in args and "--assumeyes" not in args: raise ValueError("DNF_INTERACTIVE_OR_UNCONFIRMED_OPERATION_DENIED")
    return argv
def verify_source_evidence(action,domain,version_pin,plan_dir,contract_domain):
    evidence=action.get("source_evidence")
    if not isinstance(evidence,dict): raise ValueError("SOURCE_INTEGRITY_EVIDENCE_REQUIRED:"+domain)
    raw_path=evidence.get("path")
    if not raw_path: raise ValueError("SOURCE_EVIDENCE_PATH_REQUIRED:"+domain)
    p=(plan_dir/raw_path).resolve(strict=True)
    try: p.relative_to(plan_dir.resolve())
    except ValueError: raise ValueError("SOURCE_EVIDENCE_PATH_ESCAPE:"+domain)
    raw=p.read_bytes()
    if digest(raw).lower()!=str(evidence.get("sha256","")).lower(): raise ValueError("SOURCE_EVIDENCE_HASH_MISMATCH:"+domain)
    doc=json.loads(raw.decode("utf-8"))
    official_source=evidence.get("official_source")
    if official_source not in contract_domain.get("official_sources",[]): raise ValueError("OFFICIAL_SOURCE_BINDING_MISMATCH:"+domain)
    if doc.get("official_source")!=official_source or doc.get("version_pin")!=version_pin or doc.get("source_integrity_status")!="PASS":
        raise ValueError("SOURCE_INTEGRITY_EVIDENCE_NOT_PASS:"+domain)
    if not re.fullmatch(r"[0-9a-fA-F]{64}",str(doc.get("artifact_sha256",""))): raise ValueError("SOURCE_ARTIFACT_SHA256_MISSING:"+domain)
    return {"path":str(p),"sha256":digest(raw),"artifact_sha256":doc["artifact_sha256"],"official_source":official_source,"version_pin":version_pin}
def verify_plan(path,approved):
    path=pathlib.Path(path).resolve(strict=True)
    raw=path.read_bytes()
    if not approved or digest(raw).lower()!=approved.lower(): raise ValueError("PLAN_SHA256_APPROVAL_MISMATCH")
    plan=json.loads(raw.decode("utf-8"))
    if plan.get("schema")!="CAJITA_CLI_INSTALL_PLAN/1.0" or plan.get("status")!="READY_TO_APPLY": raise ValueError("INSTALL_PLAN_NOT_READY_FAIL_CLOSED")
    if plan.get("no_mutations") is True: raise ValueError("READ_ONLY_PLAN_CANNOT_BE_APPLIED")
    if plan.get("contract_sha256")!=digest(CONTRACT.read_bytes()) or plan.get("manifest_sha256")!=digest(MANIFEST.read_bytes()): raise ValueError("INPUT_CHANGED_SINCE_PLAN")
    c=read_json(CONTRACT); cmap={d["id"]:d for d in c["domains"]}
    if plan.get("domain_order")!=c["domain_order"]: raise ValueError("INSTALL_PLAN_DOMAIN_ORDER_INVALID")
    actions=plan.get("actions")
    if not isinstance(actions,list) or not actions: raise ValueError("INSTALL_PLAN_HAS_NO_ACTIONS")
    seen=set(); validated=[]
    for action in actions:
        domain=action.get("domain_id")
        if domain not in cmap or domain in seen: raise ValueError("UNKNOWN_OR_DUPLICATE_DOMAIN:"+str(domain))
        seen.add(domain); d=cmap[domain]; pin=action.get("version_pin")
        if not pin or pin!=d.get("version_pin"): raise ValueError("VERSION_PIN_MISMATCH:"+domain)
        if action.get("mutations_authorized") is not True: raise ValueError("MUTATION_NOT_AUTHORIZED_IN_PLAN:"+domain)
        if not d.get("official_sources") or d.get("status","").startswith("BLOCKED"): raise ValueError("OFFICIAL_DISTRIBUTION_UNVERIFIED:"+domain)
        evidence=verify_source_evidence(action,domain,pin,path.parent,d)
        steps=action.get("steps"); rollback=action.get("rollback_steps")
        if not isinstance(steps,list) or not steps or not isinstance(rollback,list) or not rollback: raise ValueError("INSTALL_STEPS_OR_ROLLBACK_MISSING:"+domain)
        step_args=[validate_argv(x,domain,False) for x in steps]
        rollback_args=[validate_argv(x,domain,True) for x in rollback]
        validated.append((domain,steps,rollback,evidence))
    return plan,validated
def run_step(step,domain,rollback=False):
    argv=validate_argv(step,domain,rollback); started=time.monotonic()
    proc=subprocess.run(argv,shell=False,stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,timeout=min(900,max(1,int(step.get("timeout_seconds",300)))),check=False)
    return {"executable":pathlib.Path(argv[0]).name,"argv_sha256":digest(json.dumps(argv,separators=(",",":")).encode()),"returncode":proc.returncode,"elapsed_seconds":round(time.monotonic()-started,3),"stdout_sha256":digest((proc.stdout or "").encode()),"stderr_sha256":digest((proc.stderr or "").encode()),"stdout_bytes":len((proc.stdout or "").encode()),"stderr_bytes":len((proc.stderr or "").encode()),"status":"PASS" if proc.returncode==0 else "FAIL"}
def probe_one(domain):
    contract=read_json(CONTRACT)
    d=next(x for x in contract["domains"] if x["id"]==domain)
    module=(ROOT/d["module"]).resolve()
    module.relative_to(ROOT.resolve())
    spec=__import__("importlib.util",fromlist=["spec_from_file_location"]).spec_from_file_location("cajita_"+domain.lower(),module)
    if spec is None or spec.loader is None: raise RuntimeError("PROBE_MODULE_UNAVAILABLE")
    mod=__import__("importlib.util",fromlist=["module_from_spec"]).module_from_spec(spec); spec.loader.exec_module(mod)
    return mod.probe()
def apply_plan(path,approved,evidence_root=None):
    plan,actions=verify_plan(path,approved)
    before=cli_registry.run_registry()
    base=pathlib.Path(evidence_root or pathlib.Path.home()/".local/state/cajita-cli/checkpoints").resolve()
    base.mkdir(parents=True,exist_ok=True)
    operation=datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")+"-"+approved[:12]
    checkpoint=base/operation; checkpoint.mkdir(exist_ok=False)
    atomic_write(checkpoint/"before.json",before)
    action_results=[]; overall_ok=True
    for domain,steps,rollback_steps,evidence in actions:
        before_row=next((x for x in before["results"] if x.get("domain_id")==domain),{})
        step_results=[]; failed=False
        for step in steps:
            row=run_step(step,domain,False); step_results.append(row)
            if row["status"]!="PASS": failed=True; break
        post=None
        if not failed:
            post=probe_one(domain)
            if post.get("status")!="AVAILABLE": failed=True
        rollback_results=[]; rollback_verified=None
        if failed:
            overall_ok=False
            for step in reversed(rollback_steps):
                row=run_step(step,domain,True); rollback_results.append(row)
            after_rollback=probe_one(domain)
            rollback_verified=(all(x["status"]=="PASS" for x in rollback_results) and after_rollback.get("status")==before_row.get("status"))
            step_results.append({"post_install_status":None if post is None else post.get("status"),"status":"FAIL"})
        action_results.append({"domain_id":domain,"source_evidence":evidence,"status":"FAIL_ROLLED_BACK" if failed and rollback_verified else ("FAIL_ROLLBACK_UNVERIFIED" if failed else "PASS"),"steps":step_results,"rollback_steps":rollback_results,"rollback_verified":rollback_verified})
        if failed: break
    receipt={"schema":"CAJITA_CLI_INSTALL_EXECUTION/1.0","operation_id":operation,"created_at_utc":utc(),"plan_sha256":approved,"checkpoint_path":str(checkpoint),"pre_install_audit_sha256":digest(json.dumps(before,sort_keys=True).encode()),"status":"PASS" if overall_ok else "FAIL_ROLLBACK_ATTEMPTED","actions":action_results,"certification":"NOT_GRANTED"}
    atomic_write(checkpoint/"execution.json",receipt)
    return receipt
def main():
    p=argparse.ArgumentParser(description="Cajita CLI governance manager; audit/plan is read-only, installs require an approved immutable plan.")
    sub=p.add_subparsers(dest="command",required=True)
    a=sub.add_parser("audit"); a.add_argument("--output",type=pathlib.Path)
    b=sub.add_parser("plan"); b.add_argument("--output",type=pathlib.Path)
    c=sub.add_parser("apply-plan"); c.add_argument("--plan",required=True); c.add_argument("--approve-sha256",required=True); c.add_argument("--evidence-dir",type=pathlib.Path)
    x=p.parse_args()
    if x.command=="audit":
        result=cli_registry.run_registry(); result["manager"]={"status":"IMPLEMENTED","mode":"READ_ONLY_AUDIT","side_effects":False}
    elif x.command=="plan": result=build_plan()
    else:
        try: result=apply_plan(x.plan,x.approve_sha256,x.evidence_dir)
        except Exception as e: result={"status":"DENIED_FAIL_CLOSED","reason":str(e)[:700],"mutations_performed":False,"certification":"NOT_GRANTED"}
    if x.output: atomic_write(x.output,result)
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
    return 0 if (x.command=="plan" or (x.command=="audit" and result.get("infrastructure_status")=="PASS") or result.get("status")=="PASS") else 2
if __name__=="__main__": raise SystemExit(main())
