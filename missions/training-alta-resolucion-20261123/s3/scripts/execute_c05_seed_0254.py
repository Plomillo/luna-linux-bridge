#!/usr/bin/env python3
"""Hosted CI authentic C05 seed execution; evidence only, no certification."""
from __future__ import annotations
import hashlib, json, os, re
from pathlib import Path
from metagente_luna_s4.runner import execute_isolated
ROOT=Path(__file__).resolve().parents[4]
SOURCE=ROOT/"PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt"
CASE="MGL5-INF-0254"
source=SOURCE.read_bytes(); text=source.decode("utf-8")
m=re.search(r"(?m)^\[MGL5-INF-0254\].*?(?=^\[MGL5-INF-|\Z)",text,re.S)
if not m: raise SystemExit("case source not found")
excerpt=m.group(0); lines=source.splitlines(keepends=True)
start=text[:m.start()].count("\n")+1; end=excerpt.count("\n")+start
exact=b"".join(lines[start-1:end])
if exact.decode("utf-8")!=excerpt: raise SystemExit("line excerpt mismatch")
blob=hashlib.sha1(f"blob {len(source)}\0".encode()+source).hexdigest()
fields={}
for label,pattern in (("operation",r"FUENTE/OPERACIÓN: (.*)"),("acceptance_criterion",r"PASS: (.*)"),("oracle_requirement",r"ORÁCULO: (.*)")):
 mm=re.search(pattern,excerpt)
 if not mm: raise SystemExit(f"missing {label}")
 fields[label]=mm.group(1).strip()
meta={"source_file":"PROGRAMA_DE_ENTRENAMIENTO_DE_ALTA_RESOLUCION.txt","line_start":start,"line_end":end,"file_sha256":hashlib.sha256(source).hexdigest(),"excerpt_sha256":hashlib.sha256(exact).hexdigest(),"source_blob":blob,**fields}
cases=[
 ("NORMAL",{"cidr":"192.0.2.130/26"},None),
 ("NORMAL",{"cidr":"192.0.2.130/26"},None),
 ("NORMAL",{"cidr":"192.0.2.130/26"},None),
 ("NEGATIVE",{"cidr":"192.0.2.130/33"},{"definition":"IPv4 prefix length above 32","expected_behavior":"reject input and do not produce a subnet result","source":"IPv4 prefix validity"}),
 ("BOUNDARY",{"cidr":"192.0.2.130/32"},{"definition":"IPv4 host-width prefix /32","expected_behavior":"network and broadcast equal the host address","source":"IPv4 CIDR boundary semantics"}),
]
out=Path("reports/C05_SEED_0254_EVIDENCE"); out.mkdir(parents=True,exist_ok=True)
results=[]
for idx,(kind,args,control) in enumerate(cases,1):
 rec=execute_isolated("cidr_bounds",args,CASE,str(out),run_kind=kind,control_metadata=control,source_metadata=meta,source_excerpt=excerpt,timeout_seconds=30)
 results.append({"index":idx,"kind":kind,"arguments":args,"result":rec})
 print(json.dumps({"index":idx,"kind":kind,"arguments":args,"execution_status":rec.get("execution_status"),"result_status":rec.get("result_status"),"observed":rec.get("observed"),"oracle_result":rec.get("oracle_result"),"error":rec.get("stderr")},sort_keys=True))
(out/"run-summary.json").write_text(json.dumps({"case_id":CASE,"source_metadata":meta,"runs":results,"evidence_status":"AUTHENTIC_HOSTED_EXECUTION_NON_CERTIFYING"},indent=2,sort_keys=True)+"\n")
if [r["result"].get("execution_status") for r in results[:3]] != ["EXECUTED"]*3: raise SystemExit("normal run failure")
if results[0]["result"].get("oracle_result",{}).get("ok") is not True: raise SystemExit("normal oracle mismatch")
if results[4]["result"].get("oracle_result",{}).get("ok") is not True: raise SystemExit("boundary oracle mismatch")
if results[3]["result"].get("execution_status") not in {"ERROR","REJECTED"}: raise SystemExit("invalid CIDR unexpectedly accepted")
print("Seed execution completed; evidence does not certify C05.")
