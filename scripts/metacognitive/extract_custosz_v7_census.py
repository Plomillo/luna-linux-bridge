#!/usr/bin/env python3
from __future__ import annotations
import argparse, ast, hashlib, json, zipfile
from pathlib import Path

def literal(node):
    return ast.literal_eval(node)

def parse_target(target):
    # CAPABILITY_IMPLEMENTATIONS["F01"]["cap"]
    if not isinstance(target, ast.Subscript):
        return None
    outer = target
    if not isinstance(outer.value, ast.Subscript):
        return None
    inner = outer.value
    if not isinstance(inner.value, ast.Name) or inner.value.id != "CAPABILITY_IMPLEMENTATIONS":
        return None
    try:
        fam = literal(inner.slice)
        cap = literal(outer.slice)
    except Exception:
        return None
    if not isinstance(fam,str) or not isinstance(cap,str):
        return None
    return fam,cap

def extract(pyz: Path):
    with zipfile.ZipFile(pyz) as z:
        names=z.namelist()
        native=[n for n in names if n.endswith("custosz_v07_native.py")]
        if len(native)!=1:
            raise RuntimeError(f"CUSTOSZ_V07_NATIVE_NOT_UNIQUE:{native}")
        src=z.read(native[0]).decode("utf-8")
    tree=ast.parse(src, filename=native[0])
    caps=None
    families=None
    events=[]
    for node in tree.body:
        if isinstance(node,(ast.Assign,ast.AnnAssign)):
            targets=node.targets if isinstance(node,ast.Assign) else [node.target]
            for t in targets:
                if isinstance(t,ast.Name) and t.id=="FAMILIES":
                    families=list(literal(node.value))
                    events.append({"op":"SET_FAMILIES","count":len(families),"line":node.lineno})
                elif isinstance(t,ast.Name) and t.id=="CAPABILITY_IMPLEMENTATIONS":
                    raw=literal(node.value)
                    caps={str(k):dict(v) for k,v in raw.items()}
                    events.append({"op":"SET_CAPABILITY_IMPLEMENTATIONS","count":sum(len(v) for v in caps.values()),"line":node.lineno})
                else:
                    parsed=parse_target(t)
                    if parsed and caps is not None:
                        fam,cap=parsed
                        value=literal(node.value)
                        caps.setdefault(fam,{})[cap]=value
                        events.append({"op":"SET_CAPABILITY","family":fam,"capability":cap,"implementation":value,"line":node.lineno})
        elif isinstance(node,ast.Expr) and isinstance(node.value,ast.Call):
            call=node.value
            fn=call.func
            # CAPABILITY_IMPLEMENTATIONS["Fxx"].update({...})
            if (
                isinstance(fn,ast.Attribute) and fn.attr=="update"
                and isinstance(fn.value,ast.Subscript)
                and isinstance(fn.value.value,ast.Name)
                and fn.value.value.id=="CAPABILITY_IMPLEMENTATIONS"
                and caps is not None and len(call.args)==1
            ):
                fam=literal(fn.value.slice)
                patch=literal(call.args[0])
                if not isinstance(fam,str) or not isinstance(patch,dict):
                    raise RuntimeError(f"UNSUPPORTED_UPDATE_AT_LINE:{node.lineno}")
                caps.setdefault(fam,{}).update(patch)
                events.append({"op":"UPDATE_FAMILY","family":fam,"added_or_replaced":sorted(patch),"line":node.lineno})
    if caps is None or families is None:
        raise RuntimeError("REGISTRY_LITERALS_NOT_FOUND")
    records=[]
    for fam in families:
        for cid,impl in sorted(caps.get(fam,{}).items()):
            records.append({"family":fam,"capability_id":cid,"implementation":impl})
    return {
      "schema":"CUSTOSZ_V7_CAPABILITY_CENSUS/1.0",
      "source_entry":native[0],
      "family_count":len(families),
      "families":families,
      "capability_count":len(records),
      "unique_capability_count":len({r["capability_id"] for r in records}),
      "capabilities":records,
      "events":events,
    }

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pyz",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--expect",type=int,default=72)
    q=ap.parse_args()
    pyz=Path(q.pyz)
    result=extract(pyz)
    result["pyz_sha256"]=hashlib.sha256(pyz.read_bytes()).hexdigest()
    result["expected_capability_count"]=q.expect
    result["count_check"]="PASS" if result["capability_count"]==q.expect and result["unique_capability_count"]==q.expect else "FAIL"
    out=Path(q.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({
      "family_count":result["family_count"],
      "capability_count":result["capability_count"],
      "unique_capability_count":result["unique_capability_count"],
      "count_check":result["count_check"],
      "pyz_sha256":result["pyz_sha256"]
    },sort_keys=True))
    if result["count_check"]!="PASS":
        raise SystemExit(3)

if __name__=="__main__":
    main()
