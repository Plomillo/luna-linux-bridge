#!/usr/bin/env python3
from __future__ import annotations
import argparse, json
from collections import Counter
from pathlib import Path

EXPECTED_ACTIONS={
    "REUSE":1,
    "COMPOSE_VIA_CONTRACT":22,
    "EXTEND_OWNER_FAMILY":23,
    "GAP_PROOF_THEN_CREATE":13,
}

def die(code,detail):
    print(json.dumps({"status":"FAIL","code":code,"detail":detail},sort_keys=True))
    raise SystemExit(2)

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--graph",required=True)
    ap.add_argument("--out")
    q=ap.parse_args()
    g=json.loads(Path(q.graph).read_text(encoding="utf-8"))
    nodes=g.get("nodes",[])
    edges=g.get("edges",[])
    ids=[n.get("id") for n in nodes]
    if None in ids or len(ids)!=len(set(ids)): die("NODE_IDENTITY","missing/duplicate node id")
    node_ids=set(ids)
    dangling=[e for e in edges if e.get("from") not in node_ids or e.get("to") not in node_ids]
    if dangling: die("DANGLING_EDGE",dangling[:10])
    mcaps=sorted((n for n in nodes if n.get("type")=="MCAP"),key=lambda x:x["ordinal"])
    custosz=[n for n in nodes if n.get("type")=="CUSTOSZ_CAPABILITY"]
    if len(mcaps)!=59: die("MCAP_COUNT",len(mcaps))
    if [x["ordinal"] for x in mcaps]!=list(range(1,60)): die("MCAP_ORDINALS","not 1..59")
    if mcaps[-1]["id"]!="MCAP-059" or mcaps[-1]["name"]!="GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING":
        die("TRAINING_LAST",mcaps[-1])
    if len(custosz)!=72 or len({x["name"] for x in custosz})!=72: die("CUSTOSZ72",len(custosz))
    actions=Counter(x.get("f09_action") for x in mcaps)
    if dict(actions)!=EXPECTED_ACTIONS: die("F09_ACTION_COUNTS",dict(actions))
    if any(x.get("creates_authority") is not False or x.get("self_certifies") is not False for x in mcaps):
        die("AUTHORITY_OR_SELF_CERTIFICATION","forbidden")
    governed={e["to"] for e in edges if e.get("from")=="SYS:LOUKSNA" and e.get("relation")=="GOVERNS_AUTHORITY_BOUNDARY"}
    required={"SYS:METAOS","SYS:CUSTOSZ_V7","SYS:CUSTOSZ_RUNTIME_V1","SYS:PUAC2","SYS:GITHUB","SYS:G23","SYS:G24","SYS:FUTURE_CANONICAL_ARCHITECTURE"}
    if not required.issubset(governed): die("AUTHORITY_GRAPH",sorted(required-governed))
    g23g24=[e for e in edges if e.get("from")=="SYS:G23" and e.get("to")=="SYS:G24" and e.get("relation")=="PRECEDES_ON_SAME_FROZEN_DIGEST"]
    if len(g23g24)!=1: die("G23_G24_CHAIN",len(g23g24))
    served=Counter(e["from"] for e in edges if e.get("relation")=="SERVES_CONSUMER")
    orphans=[x["id"] for x in mcaps if served[x["id"]]==0]
    if orphans: die("ORPHAN_MCAP",orphans)
    result={
      "schema":"META_ECOSYSTEM_GRAPH_VALIDATION/1.0",
      "status":"PASS",
      "graph_id":g.get("graph_id"),
      "node_count":len(nodes),
      "edge_count":len(edges),
      "mcap_count":len(mcaps),
      "custosz_capability_count":len(custosz),
      "f09_action_counts":dict(sorted(actions.items())),
      "dangling_edges":0,
      "orphan_mcaps":0,
      "authority_chain":"PASS",
      "training_last":"PASS",
      "g23_before_g24":"PASS",
      "scope":"FEDERATED_CONTROL_PLANE_GRAPH"
    }
    print(json.dumps(result,sort_keys=True))
    if q.out:
        p=Path(q.out); p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(result,indent=2,sort_keys=True)+"\n",encoding="utf-8")

if __name__=="__main__":
    main()
