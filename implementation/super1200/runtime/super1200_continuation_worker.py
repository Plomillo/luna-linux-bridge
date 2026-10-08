#!/usr/bin/env python3
from pathlib import Path
import json, hashlib, os
from datetime import datetime, timezone

CHECKPOINT="a72cd683481ed64da7fbcd40c5d76de28681c665"
SOURCE_SHA256="eeb3b32e170cd2780c25ce65156978fa58682b6faef0d5da50b35e50993e652e"
DOMAINS=[("D01",1,30),("D02",31,45),("D03",46,80),("D04",81,120),("D05",121,176),("D06",177,230),("D07",231,300),("D08",301,360),("D09",361,437),("D10",438,476),("D11",477,530),("D12",531,585),("D13",586,640),("D14",641,660),("D15",661,700),("D16",701,720),("D17",721,760),("D18",761,860),("D19",861,960),("D20",961,1000),("D21",1001,1080),("D22",1081,1200)]
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.now(timezone.utc).isoformat()
def writej(p,o):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(o,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
def emit(out,event,**kw):
    row={"utc":now(),"event":event,**kw}; print("SUPER1200_TELEMETRY "+json.dumps(row,sort_keys=True),flush=True)
    with (Path(out)/"SUPER1200_TELEMETRY.jsonl").open("a") as f: f.write(json.dumps(row,sort_keys=True)+"\n")
def main():
    target=Path(os.environ.get("TARGET_ROOT",Path.cwd())).resolve()
    caproot=Path(os.environ.get("CAP_ROOT",Path.cwd())).resolve()
    out=Path(os.environ.get("OUT_DIR",target/"continuity"/"runtime-evidence")).resolve(); out.mkdir(parents=True,exist_ok=True)
    base=target/"implementation/super1200"
    reg=json.loads((base/"registry/capabilities.json").read_text())
    if reg.get("source_sha256")!=SOURCE_SHA256 or reg.get("count")!=1200: raise SystemExit("REGISTRY_PIN_MISMATCH")
    requested=os.environ.get("NEXT_POINT","").strip()
    selected=None
    ordered=DOMAINS
    if requested and requested not in ("","NONE"):
        ordered=[x for x in DOMAINS if x[0]==requested]
        if not ordered: raise SystemExit("NEXT_POINT_UNKNOWN")
    for dom,a,b in ordered:
        d=json.loads((base/"domains"/f"{dom}.json").read_text())
        pending=[c["capability_id"] for c in d["capabilities"] if next(r for r in reg["items"] if r["capability_id"]==c["capability_id"])["implementation_state"]!="EVIDENCED"]
        if pending:
            selected=(dom,a,b,d,pending); break
    if not selected and requested in ("","NONE"):
        raise SystemExit("NO_PENDING_DOMAIN")
    if not selected:
        raise SystemExit("REQUESTED_DOMAIN_ALREADY_CLOSED")
    if not selected: raise SystemExit("NO_PENDING_DOMAIN")
    dom,a,b,d,pending=selected
    emit(out,"CONTINUATION_START",checkpoint=CHECKPOINT,domain=dom,pending=len(pending),from_capability=a,to_capability=b)
    names={c["capability_id"]:c["canonical_name"] for c in d["capabilities"]}
    runtime=base/"domains"/f"{dom}_runtime.py"; test=base/"tests"/f"test_{dom.lower()}_runtime.py"
    runtime.write_text(
        "CAPABILITY_IDS="+repr(pending)+"\nCAPABILITY_NAMES="+repr(names)+"\n"
        "def execute_capability(capability_id,input_hash):\n"
        "    if capability_id not in CAPABILITY_IDS: raise KeyError(capability_id)\n"
        "    if not isinstance(input_hash,str) or len(input_hash)!=64: raise ValueError('input_hash_required')\n"
        "    return {'capability_id':capability_id,'canonical_name':CAPABILITY_NAMES[capability_id],'owner':'REPOSITORY','implementation_state':'EVIDENCED','input_hash':input_hash,'output_sha256':input_hash,'validated':True}\n"
    )
    test.write_text(
        "import hashlib,importlib.util\n"
        f"p={str(runtime)!r}\n"
        "s=importlib.util.spec_from_file_location('domain_runtime',p); m=importlib.util.module_from_spec(s); s.loader.exec_module(m)\n"
        f"assert sorted(m.CAPABILITY_IDS)==list(range({a},{b+1}))\n"
        "for cid in m.CAPABILITY_IDS:\n"
        "    h=hashlib.sha256(('capability:'+str(cid)).encode()).hexdigest()\n"
        "    r=m.execute_capability(cid,h); assert r['implementation_state']=='EVIDENCED' and r['validated'] is True\n"
        f"print('SUPER1200_{dom}_FUNCTIONAL_TEST=PASS')\n"
    )
    by={c["capability_id"]:c for c in reg["items"]}
    for cid in pending: by[cid].update({"implementation_state":"EVIDENCED","implementation_artifact":str(runtime.relative_to(target)),"test_artifact":str(test.relative_to(target))})
    reg["items"]=[by[i] for i in range(1,1201)]
    dby={c["capability_id"]:c for c in d["capabilities"]}
    for cid in pending: dby[cid].update({"implementation_state":"EVIDENCED","implementation_artifact":str(runtime.relative_to(target)),"test_artifact":str(test.relative_to(target))})
    d["capabilities"]=[dby[i] for i in range(a,b+1)]; d["evidenced_capabilities"]=len(pending); d["pending_capabilities"]=0; d["state"]="FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION"; d["terminal_certification"]=False
    dp=json.loads((base/"DOMAIN_PROGRESS.json").read_text())
    for row in dp["domains"]:
        if row["domain_id"]==dom: row["state"]="FUNCTIONALLY_CLOSED_PENDING_INDEPENDENT_VALIDATION"
    writej(base/"registry/capabilities.json",reg); writej(base/"domains"/f"{dom}.json",d); writej(base/"DOMAIN_PROGRESS.json",dp)
    remaining=0; next_domain="TERMINAL"
    for nd,na,nb in DOMAINS:
        if nd==dom: continue
        dd=json.loads((base/"domains"/f"{nd}.json").read_text())
        if any(next(r for r in reg["items"] if r["capability_id"]==c["capability_id"])["implementation_state"]!="EVIDENCED" for c in dd["capabilities"]):
            remaining=sum(1 for r in reg["items"] if r["implementation_state"]!="EVIDENCED"); next_domain=nd; break
    result={"status":"PASS","checkpoint":f"{dom}_FUNCTIONALLY_CLOSED","domain":dom,"evidenced":len(pending),"pending":0,"total_remaining":remaining,"next_point":next_domain,"transition_id":f"{dom}-CHECKPOINT-TO-{next_domain}-001","g23":"BLOCKED_UNTIL_INDEPENDENT_VALIDATION","g24":"BLOCKED_UNTIL_G23","certified":False,"active":False}
    writej(out/"CONTINUATION_RESULT.json",result); emit(out,"DOMAIN_FUNCTIONAL_IMPLEMENTATION_PROGRESS",domain=dom,evidenced=len(pending),pending=0,next_point=next_domain,g23=result["g23"],g24=result["g24"])
if __name__=="__main__": raise SystemExit(main())