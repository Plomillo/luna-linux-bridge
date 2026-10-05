#!/usr/bin/env python3
from __future__ import annotations
import argparse,json,pathlib,re,shutil,sys
sys.path.insert(0,str(pathlib.Path(__file__).parent))
from runtime import checkpoint,restore_checkpoint,run_stage,sha256_file,sha256_bytes,write_json,write_xlsx,verify_ooxml,append_audit,utc,hold

def load(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

def validate_profile(path,repo_root=None):
    data=load(path)
    failures=[]
    for key in ("profile_id","profile_version","raw_instruction_ref","deliverables","constraints","rubric","runtime_policy"):
        if key not in data:
            failures.append("MISSING_REQUIRED_FIELD:"+key)
    rubric=data.get("rubric") or {}
    criteria=rubric.get("criteria") or []
    declared=rubric.get("declared_total_points")
    if declared is None:
        failures.append("RUBRIC_DECLARED_TOTAL_MISSING")
    else:
        total=sum(float(x.get("points",0)) for x in criteria)
        if abs(total-float(declared))>1e-9:
            failures.append(f"RUBRIC_TOTAL_MISMATCH:{total}!={declared}")
    rp=data.get("runtime_policy") or {}
    if rp.get("heartbeat_interval_seconds")!=1:
        failures.append("HEARTBEAT_INTERVAL_NOT_ONE_SECOND")
    for name,stage in (rp.get("stages") or {}).items():
        if not isinstance(stage.get("timeout_seconds"),int) or stage["timeout_seconds"]<=0:
            failures.append("INVALID_TIMEOUT:"+name)
        if not isinstance(stage.get("max_attempts"),int) or stage["max_attempts"]<1:
            failures.append("INVALID_MAX_ATTEMPTS:"+name)
    if repo_root:
        raw=pathlib.Path(repo_root)/str(data.get("raw_instruction_ref",""))
        if not raw.is_file():
            failures.append("RAW_INSTRUCTION_SOURCE_NOT_FOUND:"+str(raw))
    return data,failures

def body_word_count(markdown_path):
    text=pathlib.Path(markdown_path).read_text(encoding="utf-8")
    match=re.search(r"<!-- BODY_START -->(.*?)<!-- BODY_END -->",text,re.S)
    if not match:
        raise ValueError("BODY_MARKERS_MISSING")
    body=match.group(1)
    body=re.sub(r"\[[^\]]+\]\([^\)]+\)"," ",body)
    body=re.sub(r"[@#*_>|{}\[\]()]"," ",body)
    return len(re.findall(r"\b[\wÀ-ÿ'-]+\b",body,flags=re.UNICODE))

def validate_sources(workspace,profile):
    workspace=pathlib.Path(workspace)
    ledger=workspace/"data"/"source-ledger.json"
    required=int((profile.get("required_research") or {}).get("minimum_distinct_sources",0))
    if not ledger.is_file():
        return {"check":"source_ledger","status":"FAIL" if required else "PASS","detail":"MISSING_SOURCE_LEDGER"}
    data=load(ledger)
    items=data.get("sources") or []
    verified=[x for x in items if x.get("verified") is True and x.get("source_id")]
    unique={x["source_id"] for x in verified}
    return {"check":"source_ledger","status":"PASS" if len(unique)>=required else "FAIL","required":required,"verified_distinct_sources":len(unique)}

def validate_workspace(workspace,profile_path,repo_root=None):
    root=pathlib.Path(workspace)
    profile,pfail=validate_profile(profile_path,repo_root)
    results=[{"check":"profile","status":"FAIL","detail":x} for x in pfail]
    out=root/"build"
    for kind,name in (("docx","report.docx"),("pptx","slides.pptx"),("xlsx","evidence.xlsx")):
        try:
            verify_ooxml(out/name,kind)
            results.append({"check":kind,"status":"PASS","sha256":sha256_file(out/name)})
        except Exception as exc:
            results.append({"check":kind,"status":"FAIL","detail":str(exc)})
    pdf=out/"report.pdf"
    results.append({"check":"pdf","status":"PASS" if pdf.is_file() and pdf.stat().st_size>4 else "FAIL","sha256":sha256_file(pdf) if pdf.is_file() else None})
    try:
        count=body_word_count(root/"source"/"report.md")
        rule=(profile.get("constraints") or {}).get("report_word_count")
        ok=True if not rule else int(rule["min"])<=count<=int(rule["max"])
        results.append({"check":"word_count","status":"PASS" if ok else "FAIL","value":count,"rule":rule})
    except Exception as exc:
        results.append({"check":"word_count","status":"FAIL","detail":str(exc)})
    results.append(validate_sources(root,profile))
    failures=[x for x in results if x.get("status")!="PASS"]
    report={"schema":"DOCUMENT_FACTORY_VALIDATION/1.0","observed_at_utc":utc(),"status":"PASS" if not failures else "FAIL","results":results}
    write_json(root/"evidence"/"validation.json",report)
    append_audit(root,{"event_type":"VALIDATION","status":report["status"],"failure_count":len(failures)})
    return report

def build(workspace,profile_path,repo_root):
    root=pathlib.Path(workspace)
    profile,pfail=validate_profile(profile_path,repo_root)
    if pfail:
        hold(root,"PROFILE_VALIDATE","PROFILE_INVALID",pfail)
        raise RuntimeError("PROFILE_INVALID")
    checkpoint(root)
    stages=profile["runtime_policy"]["stages"]
    out=root/"build"
    out.mkdir(parents=True,exist_ok=True)
    pandoc=shutil.which("pandoc")
    office=shutil.which("soffice") or shutil.which("libreoffice")
    if not pandoc:
        hold(root,"BUILD_DOCX","PROVIDER_MISSING","pandoc")
        raise RuntimeError("PANDOC_MISSING")
    if not office:
        hold(root,"BUILD_PDF","PROVIDER_MISSING","libreoffice")
        raise RuntimeError("LIBREOFFICE_MISSING")
    run_stage(root,"BUILD_DOCX",[pandoc,str(root/"source"/"report.md"),"--standalone","-o",str(out/"report.docx")],stages["BUILD_DOCX"]["timeout_seconds"])
    run_stage(root,"BUILD_PPTX",[pandoc,str(root/"source"/"slides.md"),"--standalone","-o",str(out/"slides.pptx")],stages["BUILD_PPTX"]["timeout_seconds"])
    with open(root/"data"/"sheets.json",encoding="utf-8") as f:
        write_xlsx(out/"evidence.xlsx",json.load(f))
    append_audit(root,{"event_type":"BUILD_XLSX","status":"PASS","sha256":sha256_file(out/"evidence.xlsx")})
    run_stage(root,"BUILD_PDF",[office,"--headless","--convert-to","pdf","--outdir",str(out),str(out/"report.docx")],stages["BUILD_PDF"]["timeout_seconds"])
    return validate_workspace(root,profile_path,repo_root)

def self_audit(workspace,profile_path):
    root=pathlib.Path(workspace)
    profile,_=validate_profile(profile_path)
    validation=load(root/"evidence"/"validation.json") if (root/"evidence"/"validation.json").is_file() else {"status":"UNKNOWN"}
    rubric=profile.get("rubric",{}).get("criteria",[])
    independent=[x["id"] for x in rubric if "G23" in str(x.get("validation",""))]
    unresolved=[]
    if validation.get("status")!="PASS":
        unresolved.append("FIRST_ORDER_VALIDATION_NOT_PASS")
    if independent:
        unresolved.append("INDEPENDENT_OR_HUMAN_RUBRIC_JUDGMENT_PENDING")
    if profile.get("unresolved_source_conflicts"):
        unresolved.append("SOURCE_CONFLICT_REQUIRES_GOVERNED_RESOLUTION")
    status="PASS"
    if "FIRST_ORDER_VALIDATION_NOT_PASS" in unresolved:
        status="HOLD"
    elif unresolved:
        status="PASS_WITH_ESCALATION"
    obj={"schema":"DOCUMENT_FACTORY_METACOGNITIVE_SELF_AUDIT/1.0","observed_at_utc":utc(),"status":status,"first_order_validation":validation.get("status"),"rubric_criteria_requiring_independent_or_human_judgment":independent,"unresolved":unresolved,"g23_granted":False,"g24_granted":False,"certification_authority":False}
    write_json(root/"evidence"/"self-audit.json",obj)
    append_audit(root,{"event_type":"SELF_AUDIT","status":status,"unresolved":unresolved})
    return obj

def freeze(workspace):
    root=pathlib.Path(workspace)
    rows=[]
    for base in ("source","data","build","evidence","runtime"):
        p=root/base
        if not p.exists():
            continue
        for f in sorted(x for x in p.rglob("*") if x.is_file()):
            rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha256_file(f),"size_bytes":f.stat().st_size})
    digest=sha256_bytes(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())
    obj={"schema":"DOCUMENT_FACTORY_FROZEN_WORKSPACE/1.0","frozen":True,"candidate_digest_sha256":digest,"files":rows,"g23":"NOT_EXECUTED","g24":"NOT_EXECUTED"}
    write_json(root/"FROZEN_CANDIDATE.json",obj)
    (root/"CANDIDATE_DIGEST.txt").write_text(digest+"\n",encoding="utf-8")
    append_audit(root,{"event_type":"FREEZE","candidate_digest_sha256":digest})
    return obj

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="command",required=True)
    p=sub.add_parser("validate-profile"); p.add_argument("profile"); p.add_argument("--repo-root",default=".")
    p=sub.add_parser("build"); p.add_argument("workspace"); p.add_argument("profile"); p.add_argument("--repo-root",default=".")
    p=sub.add_parser("validate"); p.add_argument("workspace"); p.add_argument("profile"); p.add_argument("--repo-root",default=".")
    p=sub.add_parser("self-audit"); p.add_argument("workspace"); p.add_argument("profile")
    p=sub.add_parser("freeze"); p.add_argument("workspace")
    p=sub.add_parser("rollback"); p.add_argument("workspace"); p.add_argument("checkpoint_digest")
    args=ap.parse_args()
    if args.command=="validate-profile":
        _,failures=validate_profile(args.profile,args.repo_root)
        print(json.dumps({"status":"PASS" if not failures else "FAIL","failures":failures},ensure_ascii=False,sort_keys=True))
        raise SystemExit(0 if not failures else 2)
    if args.command=="build":
        print(json.dumps(build(args.workspace,args.profile,args.repo_root),ensure_ascii=False,sort_keys=True)); return
    if args.command=="validate":
        print(json.dumps(validate_workspace(args.workspace,args.profile,args.repo_root),ensure_ascii=False,sort_keys=True)); return
    if args.command=="self-audit":
        print(json.dumps(self_audit(args.workspace,args.profile),ensure_ascii=False,sort_keys=True)); return
    if args.command=="rollback":
        print(json.dumps(restore_checkpoint(args.workspace,args.checkpoint_digest),ensure_ascii=False,sort_keys=True)); return
    print(json.dumps(freeze(args.workspace),ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
