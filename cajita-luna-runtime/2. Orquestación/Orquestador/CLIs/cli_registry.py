from __future__ import annotations
import argparse, hashlib, importlib.util, json, os, pathlib, sys
from datetime import datetime, timezone
ROOT=pathlib.Path(__file__).resolve().parent
ORCHESTRATOR=ROOT.parent
sys.path.insert(0,str(ROOT))
ORDER=["CLI_MOJO","CLI_CPP23_TOOLCHAIN","CLI_CLAUDE_CODE","CLI_PYTHON","CLI_GITHUB","CLI_GEMINI","CLI_GROK","CLI_HUGGING_FACE"]
def utc(): return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read_json(p):
    v=json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    if not isinstance(v,dict): raise ValueError("JSON_ROOT_NOT_OBJECT")
    return v
def load_inputs(manifest_path=None,contract_path=None):
    mp=pathlib.Path(manifest_path or ORCHESTRATOR/"punto.json")
    cp=pathlib.Path(contract_path or ROOT/"cli_contract.json")
    m=read_json(mp); c=read_json(cp)
    if m.get("domain_order")!=ORDER or c.get("domain_order")!=ORDER: raise ValueError("DOMAIN_ORDER_MISMATCH")
    if m.get("role")!="DECLARATIVE_ENTRYPOINT_NOT_MONOLITHIC_IMPLEMENTATION": raise ValueError("MANIFEST_ROLE_INVALID")
    if len(m.get("domains",[]))!=8 or [x.get("id") for x in m["domains"]]!=ORDER: raise ValueError("MANIFEST_DOMAIN_COUNT_OR_ORDER_INVALID")
    if [x.get("id") for x in c.get("domains",[])]!=ORDER: raise ValueError("CONTRACT_DOMAIN_COUNT_OR_ORDER_INVALID")
    if any(m["domains"][i].get("module","").split("/")[-1]!=c["domains"][i].get("module") for i in range(8)): raise ValueError("MODULE_BINDING_MISMATCH")
    return mp,cp,m,c
def selftest(manifest_path=None,contract_path=None):
    mp,cp,m,c=load_inputs(manifest_path,contract_path)
    missing=[]
    for d in c["domains"]:
        p=(ROOT/pathlib.Path(d["module"]).name).resolve()
        try: p.relative_to(ROOT.resolve())
        except ValueError: missing.append({"id":d["id"],"status":"MODULE_PATH_ESCAPE"}); continue
        if not p.is_file(): missing.append({"id":d["id"],"status":"MODULE_ABSENT"})
    legacy_absent = not (ORCHESTRATOR/"CLIS.txt").exists()
    return {"schema":"CAJITA_CLI_INFRASTRUCTURE_SELFTEST/1.0","status":"PASS" if not missing and legacy_absent else "FAIL","domain_count":8,"unique_domain_count":len(set(ORDER)),"contract_present":cp.is_file(),"manifest_present":mp.is_file(),"all_adapters_present":not missing,"missing_adapters":missing,"legacy_spec_git_blob_sha":c.get("legacy_specification",{}).get("git_blob_sha"),"legacy_spec_absent_after_migration":legacy_absent,"side_effects":False,"certification":"NOT_GRANTED"}
def run_registry(manifest_path=None,contract_path=None):
    mp,cp,m,c=load_inputs(manifest_path,contract_path)
    cmap={d["id"]:d for d in c["domains"]}; rows=[]
    for d in m["domains"]:
        p=(ROOT/d["module"]).resolve()
        try: p.relative_to(ROOT.resolve())
        except ValueError: rows.append({"domain_id":d["id"],"status":"MODULE_PATH_ESCAPE"}); continue
        if not p.is_file(): rows.append({"domain_id":d["id"],"status":"ADAPTER_ABSENT"}); continue
        try:
            spec=importlib.util.spec_from_file_location("cajita_"+d["id"].lower(),p)
            if spec is None or spec.loader is None: raise ImportError("MODULE_LOADER_UNAVAILABLE")
            mod=importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
            row=mod.probe(); row["official_sources"]=cmap[d["id"]].get("official_sources",[]); row["installation_policy_status"]=cmap[d["id"]].get("status"); rows.append(row)
        except Exception as e: rows.append({"domain_id":d["id"],"status":"PROBE_ERROR","error_type":type(e).__name__,"reason":str(e)[:400]})
    infrastructure="PASS" if len(rows)==8 and all(r.get("status") not in {"PROBE_ERROR","ADAPTER_ABSENT","MODULE_PATH_ESCAPE"} for r in rows) else "FAIL"
    counts={}
    for r in rows: counts[r.get("status","UNKNOWN")]=counts.get(r.get("status","UNKNOWN"),0)+1
    available=sum(1 for r in rows if r.get("status")=="AVAILABLE")
    return {"schema":"CAJITA_CLI_HOST_AUDIT/1.0","captured_at_utc":utc(),"repository":"Plomillo/luna-linux-bridge","source_commit":os.getenv("GITHUB_SHA"),"runtime_relative_path":"2. Orquestación/Orquestador/CLIs","manifest_sha256":sha(mp),"contract_sha256":sha(cp),"legacy_specification":{"path":"2. Orquestación/Orquestador/CLIS.txt","git_blob_sha":c.get("legacy_specification",{}).get("git_blob_sha"),"working_tree_present":(ORCHESTRATOR/"CLIS.txt").exists()},"domain_order":ORDER,"domain_count":len(rows),"available_domain_count":available,"status_counts":counts,"infrastructure_status":infrastructure,"provider_host_readiness":"ALL_REQUIRED_PROBES_PASS" if available==8 else "PARTIAL","results":rows,"read_only":True,"mutations_performed":False,"shell_invoked":False,"credential_values_logged":False,"certification":"NOT_GRANTED"}
def write(path,value):
    p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True); t=p.with_name(p.name+".tmp"); t.write_text(json.dumps(value,indent=2,sort_keys=True,ensure_ascii=False)+"\n",encoding="utf-8"); t.replace(p)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--manifest",type=pathlib.Path,default=ORCHESTRATOR/"punto.json"); ap.add_argument("--contract",type=pathlib.Path,default=ROOT/"cli_contract.json"); ap.add_argument("--output",type=pathlib.Path); ap.add_argument("--self-test",action="store_true"); a=ap.parse_args()
    try: result=selftest(a.manifest,a.contract) if a.self_test else run_registry(a.manifest,a.contract)
    except Exception as e: result={"status":"ERROR","infrastructure_status":"FAIL","reason":str(e)[:700],"certification":"NOT_GRANTED"}
    if a.output: write(a.output,result)
    print(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False))
    return 0 if (result.get("status")=="PASS" if a.self_test else result.get("infrastructure_status")=="PASS") else 2
if __name__=="__main__": raise SystemExit(main())
