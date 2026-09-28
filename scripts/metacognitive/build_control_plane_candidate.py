#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path

CONTROL_FILES=[
 "ecosystem/metacognitive-operational-v1/README.md",
 "ecosystem/metacognitive-operational-v1/CAPABILITIES.json",
 "ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json",
 "ecosystem/metacognitive-operational-v1/CUSTOSZ72_DEDUP_EVIDENCE.json",
 "ecosystem/metacognitive-operational-v1/ECOSYSTEM_GRAPH.json",
 "ecosystem/metacognitive-operational-v1/CLAIM_REGISTRY.json",
 "ecosystem/metacognitive-operational-v1/INDEPENDENCE_PLAN.json",
 "ecosystem/metacognitive-operational-v1/RISK_REGISTER.json",
 "ecosystem/metacognitive-operational-v1/VALIDITY_POLICY.json",
 "ecosystem/metacognitive-operational-v1/ECOSYSTEM_CONTRACT.md",
 "ecosystem/metacognitive-operational-v1/PROHIBITIONS.md",
 "ecosystem/metacognitive-operational-v1/INFRASTRUCTURE.md",
 "ecosystem/metacognitive-operational-v1/REMOTE_CORPUS_TRANSLATION.md",
 "ecosystem/metacognitive-operational-v1/ASSURANCE_G23_G24.md",
 "ecosystem/metacognitive-operational-v1/LAB_PREFLIGHT.json",
 "ecosystem/metacognitive-operational-v1/validate.py",
 "scripts/metacognitive/extract_custosz_v7_census.py",
 "scripts/metacognitive/inspect_custosz_family9.py",
 "scripts/metacognitive/validate_custosz72_mcap59_dedup.py",
 "scripts/metacognitive/validate_ecosystem_graph.py",
 "scripts/metacognitive/test_meta_ecosystem_mailbox_binding.py",
 "scripts/mission_mailbox/compile_mission.py",
 "scripts/mission_mailbox/route_mission.py",
 "scripts/mission_mailbox/adapters/metacognitive_ecosystem_v1.py",
 "mission-mailbox/config/mailbox-policy.json",
 "mission-mailbox/runtime-adapters/registry.json",
 "mission-mailbox/source-class-bindings/registry.json",
 "mission-mailbox/schemas/MISSION_NATIVE.schema.json",
 "missions/inbox/metacognitive-ecosystem-v1-20260928/MISSION_ORIGINAL.md",
]
DEPENDENCIES=[
 "Louksna.md",
 "PUAC2.md",
 "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz",
 "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz",
 "artifacts/custosz-v7/MetaOS.wasm",
]

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--repo-root",default=".")
    ap.add_argument("--out",required=True)
    q=ap.parse_args()
    root=Path(q.repo_root).resolve()
    records=[]
    for role,paths in (("CONTROL_PLANE",CONTROL_FILES),("PINNED_DEPENDENCY",DEPENDENCIES)):
        for rel in paths:
            p=root/rel
            if not p.is_file():
                raise SystemExit("MISSING_CANDIDATE_FILE:"+rel)
            records.append({"path":rel,"role":role,"size_bytes":p.stat().st_size,"sha256":sha(p)})
    records.sort(key=lambda x:x["path"])
    canonical="".join(f'{x["path"]}\0{x["role"]}\0{x["size_bytes"]}\0{x["sha256"]}\n' for x in records).encode()
    digest=hashlib.sha256(canonical).hexdigest()
    manifest={
      "schema":"META_ECOSYSTEM_FROZEN_CANDIDATE/1.0",
      "artifact_id":"META_ECOSYSTEM_CONTROL_PLANE_V1",
      "scope":"CONTROL_PLANE_AND_GOVERNED_BINDINGS_ONLY",
      "authority":"Louksna.md",
      "candidate_digest_algorithm":"sha256(sorted(path\\0role\\0size\\0sha256\\n))",
      "candidate_digest":digest,
      "file_count":len(records),
      "files":records,
      "canonical_mutation":False,
      "authority_transfer":False,
      "heavy_compute_on_user_host":False,
      "external_domain_lanes_certified":False,
      "human_level_agi_claimed":False,
      "g23":"NOT_PERFORMED",
      "g24":"NOT_PERFORMED",
      "mutation_rule":"Any change to any listed byte/size/path invalidates this candidate digest and all downstream validation records."
    }
    out=Path(q.out); out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps({"status":"PASS","candidate_digest":digest,"file_count":len(records),"scope":manifest["scope"]},sort_keys=True))

if __name__=="__main__":
    main()
