#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

def die(code,detail):
    print(json.dumps({"status":"FAIL","code":code,"detail":detail},sort_keys=True))
    raise SystemExit(3)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--graph",required=True)
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    p=Path(q.graph)
    g=json.loads(p.read_text(encoding="utf-8"))
    nodes=g.get("nodes",[])
    edges=g.get("edges",[])
    ids=[n["id"] for n in nodes]
    if len(ids)!=len(set(ids)): die("DUPLICATE_NODE_ID","node IDs must be unique")
    node_ids=set(ids)
    for e in edges:
        if e["from"] not in node_ids or e["to"] not in node_ids:
            die("DANGLING_EDGE",e)
    mcaps=sorted((n for n in nodes if n.get("type")=="MCAP"),key=lambda x:x["ordinal"])
    custosz=[n for n in nodes if n.get("type")=="CUSTOSZ_CAPABILITY"]
    systems=[n for n in nodes if n.get("type")=="SYSTEM"]
    if [x["ordinal"] for x in mcaps]!=list(range(1,60)): die("MCAP_ORDINALS","must be 1..59")
    if len(custosz)!=72: die("CUSTOSZ_COUNT",len(custosz))
    if len({x["name"] for x in custosz})!=72: die("CUSTOSZ_DUPLICATE","capability names must be unique")
    if len(systems)!=8: die("SYSTEM_COUNT",len(systems))
    if mcaps[-1]["name"]!="GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING":
        die("TRAINING_LAST",mcaps[-1]["name"])
    allowed={"REUSE","EXTEND_OWNER_FAMILY","COMPOSE_VIA_CONTRACT","PLACE_IN_F08_COMMON_CORE","GAP_PROOF_THEN_CREATE"}
    for m in mcaps:
        if m.get("family9_action") not in allowed:
            die("F9_ACTION",m["id"])
        if m.get("self_certifies") is not False or m.get("creates_authority") is not False:
            die("AUTHORITY_OR_SELF_CERTIFICATION",m["id"])
        consumers=[e for e in edges if e["from"]==m["id"] and e["relation"]=="CONSUMED_BY"]
        if len(consumers)<1: die("ORPHAN_MCAP",m["id"])
        if m["family9_action"]=="REUSE" and not m.get("existing_capabilities"):
            die("REUSE_WITHOUT_BINDING",m["id"])
        if m["family9_action"]=="COMPOSE_VIA_CONTRACT":
            components=set(m.get("existing_capabilities",[]))|set(m.get("runtime_components",[]))
            if len(components)<2: die("COMPOSE_WITHOUT_COMPONENTS",m["id"])
        if m["family9_action"]=="GAP_PROOF_THEN_CREATE" and m.get("coverage")!="novel":
            die("NOVELTY_MISMATCH",m["id"])
    if g.get("authority")!="Louksna.md" or g.get("canonical_mutation") is not False or g.get("authority_transfer") is not False:
        die("AUTHORITY_INVARIANT","authority/canonical mutation mismatch")
    sha=hashlib.sha256(p.read_bytes()).hexdigest()
    result={
      "schema":"ECOSYSTEM_GRAPH_VALIDATION/1.0",
      "status":"PASS",
      "graph_sha256":sha,
      "system_nodes":len(systems),
      "mcap_nodes":len(mcaps),
      "custosz_capability_nodes":len(custosz),
      "edge_count":len(edges),
      "training_last":True,
      "no_dangling_edges":True,
      "no_duplicate_node_ids":True,
      "authority_transfer":False,
      "canonical_mutation":False,
      "g23":"NOT_PERFORMED",
      "g24":"NOT_PERFORMED"
    }
    out=Path(q.out)
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(result,sort_keys=True))

if __name__=="__main__":
    main()
