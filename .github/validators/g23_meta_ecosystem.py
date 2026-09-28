#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from collections import Counter
from pathlib import Path

def h(p): return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--bundle",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--external-evaluator",default="")
    q=ap.parse_args()
    root=Path(q.bundle).resolve()
    manifest=json.loads((root/"CANDIDATE_MANIFEST.json").read_text(encoding="utf-8"))
    payload=root/"payload"
    findings=[]
    for rec in manifest["files"]:
        p=payload/rec["path"]
        if not p.is_file():
            findings.append("MISSING:"+rec["path"]); continue
        if p.stat().st_size!=rec["size_bytes"]: findings.append("SIZE_MISMATCH:"+rec["path"])
        if h(p)!=rec["sha256"]: findings.append("SHA_MISMATCH:"+rec["path"])
    canonical="".join(f'{x["path"]}\0{x["role"]}\0{x["size_bytes"]}\0{x["sha256"]}\n' for x in sorted(manifest["files"],key=lambda x:x["path"])).encode()
    recomputed=hashlib.sha256(canonical).hexdigest()
    if recomputed!=manifest["candidate_digest"]: findings.append("CANDIDATE_DIGEST_MISMATCH")

    caps=json.loads((payload/"ecosystem/metacognitive-operational-v1/CAPABILITIES.json").read_text(encoding="utf-8"))
    census=json.loads((payload/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_CENSUS.json").read_text(encoding="utf-8"))
    dedup=json.loads((payload/"ecosystem/metacognitive-operational-v1/CUSTOSZ72_DEDUP_EVIDENCE.json").read_text(encoding="utf-8"))
    graph=json.loads((payload/"ecosystem/metacognitive-operational-v1/ECOSYSTEM_GRAPH.json").read_text(encoding="utf-8"))
    claims=json.loads((payload/"ecosystem/metacognitive-operational-v1/CLAIM_REGISTRY.json").read_text(encoding="utf-8"))
    indep=json.loads((payload/"ecosystem/metacognitive-operational-v1/INDEPENDENCE_PLAN.json").read_text(encoding="utf-8"))
    risk=json.loads((payload/"ecosystem/metacognitive-operational-v1/RISK_REGISTER.json").read_text(encoding="utf-8"))
    validity=json.loads((payload/"ecosystem/metacognitive-operational-v1/VALIDITY_POLICY.json").read_text(encoding="utf-8"))

    if caps.get("authority")!="Louksna.md" or caps.get("canonical_mutation") is not False: findings.append("AUTHORITY_OR_CANONICAL_MUTATION")
    cs=caps.get("capabilities",[])
    if len(cs)!=59 or len({x["id"] for x in cs})!=59 or [x["ordinal"] for x in cs]!=list(range(1,60)): findings.append("MCAP59_INVALID")
    if not cs or cs[-1].get("name")!="GOVERNED_TRAINING_AND_CONTINUOUS_LEARNING": findings.append("TRAINING_NOT_LAST")
    if census.get("capability_count")!=72 or census.get("unique_capability_count")!=72: findings.append("CUSTOSZ72_INVALID")
    if census.get("pyz_sha256")!="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2": findings.append("CUSTOSZ_IDENTITY_DRIFT")
    if len(dedup.get("rows",[]))!=59 or {x["mcap_id"] for x in dedup.get("rows",[])}!={x["id"] for x in cs}: findings.append("DEDUP_COVERAGE_INVALID")
    cover=Counter(x["coverage"] for x in dedup.get("rows",[]))
    if dict(cover)!={"composable":22,"full":1,"novel":13,"partial":23}: findings.append("DEDUP_DISTRIBUTION_INVALID")

    node_ids=[x["id"] for x in graph.get("nodes",[])]
    if len(node_ids)!=len(set(node_ids)): findings.append("GRAPH_DUPLICATE_NODE")
    if any(e.get("from") not in set(node_ids) or e.get("to") not in set(node_ids) for e in graph.get("edges",[])): findings.append("GRAPH_DANGLING_EDGE")
    if not any(e.get("from")=="SYS:G23" and e.get("to")=="SYS:G24" and e.get("relation")=="PRECEDES_ON_SAME_FROZEN_DIGEST" for e in graph.get("edges",[])): findings.append("G23_G24_CHAIN_MISSING")

    if len(claims.get("claims",[]))<13: findings.append("CLAIM_COVERAGE_TOO_SMALL")
    for cl in claims.get("claims",[]):
        if not cl.get("acceptance_predicate") or not cl.get("evidence"): findings.append("UNTYPED_CLAIM:"+str(cl.get("claim_id")))
    critical_open=[x["id"] for x in risk.get("risks",[]) if x.get("severity")=="CRITICAL" and "OPEN" in str(x.get("residual",""))]
    if "RISK-005" not in critical_open: findings.append("INDEPENDENCE_RISK_NOT_EXPLICIT")
    if validity.get("on_invalidation") is None or validity.get("monitoring_profile",{}).get("automatic_certification_propagation") is not False: findings.append("VALIDITY_POLICY_INVALID")

    c27_plan=indep.get("assessment",{}).get("puac_c27")
    external=None
    external_ok=False
    external_findings=[]
    if q.external_evaluator:
        ep=Path(q.external_evaluator)
        if not ep.is_file():
            external_findings.append("EXTERNAL_EVALUATOR_RECORD_MISSING")
        else:
            try:
                external=json.loads(ep.read_text(encoding="utf-8"))
            except Exception:
                external_findings.append("EXTERNAL_EVALUATOR_RECORD_UNPARSEABLE")
            if external is not None:
                if external.get("schema")!="EXTERNAL_EVALUATOR_RECORD/1.0": external_findings.append("EXTERNAL_EVALUATOR_SCHEMA_INVALID")
                if external.get("artifact_id")!=manifest["artifact_id"]: external_findings.append("EXTERNAL_EVALUATOR_ARTIFACT_MISMATCH")
                if external.get("candidate_digest")!=manifest["candidate_digest"]: external_findings.append("EXTERNAL_EVALUATOR_DIGEST_MISMATCH")
                ev=external.get("evaluator",{})
                ind=external.get("independence",{})
                eva=external.get("evaluation",{})
                prov=external.get("provenance",{})
                prohibited={"ACTOR:PRODUCER:CUSTOSZ_V7","ACTOR:GOVERNOR:METAOS","ACTOR:GITHUB_PRODUCER_JOB","Plomillo","ChatGPT"}
                if not ev.get("evaluator_id") or ev.get("evaluator_id") in prohibited: external_findings.append("EXTERNAL_EVALUATOR_IDENTITY_NOT_INDEPENDENT")
                if ev.get("role")!="SECOND_INDEPENDENT_EVALUATOR": external_findings.append("EXTERNAL_EVALUATOR_ROLE_INVALID")
                if not ev.get("provider"): external_findings.append("EXTERNAL_EVALUATOR_PROVIDER_MISSING")
                if ind.get("not_candidate_builder") is not True: external_findings.append("EXTERNAL_EVALUATOR_IS_CANDIDATE_BUILDER")
                if ind.get("not_material_worker") is not True: external_findings.append("EXTERNAL_EVALUATOR_IS_MATERIAL_WORKER")
                if ind.get("read_only_candidate") is not True: external_findings.append("EXTERNAL_EVALUATOR_NOT_READ_ONLY")
                if ind.get("repair_performed") is not False: external_findings.append("EXTERNAL_EVALUATOR_REPAIR_PERFORMED")
                if ind.get("can_modify_candidate") is not False: external_findings.append("EXTERNAL_EVALUATOR_CAN_MODIFY_CANDIDATE")
                if not ind.get("conflict_disclosure"): external_findings.append("EXTERNAL_EVALUATOR_CONFLICT_DISCLOSURE_MISSING")
                if eva.get("result")!="PASS": external_findings.append("EXTERNAL_EVALUATOR_NOT_PASS")
                if not eva.get("claims_reviewed"): external_findings.append("EXTERNAL_EVALUATOR_NO_CLAIMS_REVIEWED")
                required_prov=("issued_at","source_system","source_record_id","source_record_uri","immutable_or_signed_proof")
                if any(not prov.get(k) for k in required_prov): external_findings.append("EXTERNAL_EVALUATOR_PROVENANCE_INCOMPLETE")
                external_ok=not external_findings
    else:
        external_findings.append("EXTERNAL_EVALUATOR_RECORD_NOT_SUPPLIED")

    # The candidate records the independence requirement. External evidence is deliberately
    # out-of-candidate so PUAC.C27 can be satisfied without mutating the already frozen bytes.
    independence_ok=external_ok
    if not independence_ok:
        findings.extend(external_findings)
        findings.append("PUAC_C27_NOT_PASS:"+str(c27_plan))

    hard=[x for x in findings if not x.startswith("PUAC_C27_NOT_PASS:") and x not in external_findings]
    status="PASS" if not hard and independence_ok else "HOLD"
    record={
      "schema":"G23_META_ECOSYSTEM_INDEPENDENT_VALIDATION/1.0",
      "gate":"G23",
      "artifact_id":manifest["artifact_id"],
      "candidate_digest":manifest["candidate_digest"],
      "evaluation_mode":"FRESH_READ_ONLY_INDEPENDENT_IMPLEMENTATION",
      "repair_performed":False,
      "candidate_hash_verification":"PASS" if not any("MISMATCH" in x or x.startswith("MISSING:") for x in findings) else "FAIL",
      "puac_c27_plan":c27_plan,
      "puac_c27_effective":"PASS" if independence_ok else "HOLD",
      "external_evaluator_record_supplied":bool(q.external_evaluator),
      "external_evaluator_identity":(external or {}).get("evaluator",{}).get("evaluator_id") if external else None,
      "external_evaluator_provider":(external or {}).get("evaluator",{}).get("provider") if external else None,
      "external_evaluator_provenance":(external or {}).get("provenance") if external else None,
      "result":status,
      "findings":findings,
      "limitations":[
        "This validator does not infer operational status for external domain lanes excluded by the candidate scope.",
        "G23 cannot PASS without a valid external evaluator record bound to the exact frozen candidate digest."
      ]
    }
    Path(q.out).write_text(json.dumps(record,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(record,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 3)

if __name__=="__main__":
    main()
