#!/usr/bin/env python3
import argparse, ast, json, zipfile
from pathlib import Path

TARGETS={"SemanticOverlapAnalyzer","AntiDuplicationEngine","GapProofEngine","EvolutionAdmissionEngine","PlacementEngine","CompositionEngine","CapabilityGapEvolutionEngine"}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--pyz",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    with zipfile.ZipFile(q.pyz) as z:
        names=[n for n in z.namelist() if n.endswith("custosz_v07_families.py")]
        if len(names)!=1:
            raise SystemExit("FAMILIES_SOURCE_NOT_UNIQUE:"+repr(names))
        src=z.read(names[0]).decode("utf-8")
    tree=ast.parse(src,filename=names[0])
    lines=src.splitlines()
    out={"schema":"CUSTOSZ_F09_INTERFACE/1.0","source_entry":names[0],"classes":{}}
    for node in tree.body:
        if isinstance(node,ast.ClassDef) and node.name in TARGETS:
            methods=[]
            for m in node.body:
                if isinstance(m,(ast.FunctionDef,ast.AsyncFunctionDef)):
                    args=[a.arg for a in m.args.args]
                    methods.append({
                      "name":m.name,
                      "args":args,
                      "defaults_count":len(m.args.defaults),
                      "lineno":m.lineno,
                      "end_lineno":getattr(m,"end_lineno",m.lineno)
                    })
            lo=node.lineno
            hi=getattr(node,"end_lineno",lo)
            out["classes"][node.name]={
              "lineno":lo,
              "end_lineno":hi,
              "methods":methods,
              "source":"\n".join(lines[lo-1:hi])
            }
    missing=sorted(TARGETS-set(out["classes"]))
    out["missing"]=missing
    Path(q.out).write_text(json.dumps(out,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({k:v["methods"] for k,v in out["classes"].items()},sort_keys=True))
    if missing:
        raise SystemExit(3)

if __name__=="__main__":
    main()
