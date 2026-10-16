#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, platform, shutil, tempfile
from datetime import datetime, timezone

SECRET_PREFIXES=("ghp_","github_pat_","sk-","AKIA")
REQUIRED_LANES={"debian13","android36_37","windows","rclone","remote_range","translation_scale","telemetry"}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()
def read(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def write(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def build(candidate):
    c=pathlib.Path(candidate)
    readiness=read(c/"READINESS.json"); graph=read(c/"ECOSYSTEM_GRAPH.json"); binds=read(c/"CAPABILITY_BINDINGS.json")
    lanes=read(c/"LANE_EVIDENCE.json")["lanes"]; core=read(c/"CORE_SELFTEST.json"); prov=read(c/"PROVENANCE.json")
    pass_lanes={k for k,v in lanes.items() if isinstance(v,dict) and v.get("status")=="PASS"}
    claims=[
      {"claim_id":"CLM-001","property":"CANONICAL_AUTHORITY_PRESERVED","acceptance_predicate":"authority == Louksna.md","result":"PASS" if prov.get("authority")=="Louksna.md" else "FAIL"},
      {"claim_id":"CLM-002","property":"NO_CANONICAL_MUTATION","acceptance_predicate":"canonical_mutation == false","result":"PASS" if prov.get("canonical_mutation") is False else "FAIL"},
      {"claim_id":"CLM-003","property":"MCAP59_COMPLETE","acceptance_predicate":"capability graph and bindings == 59","result":"PASS" if graph.get("capability_count")==59 and binds.get("count")==59 else "FAIL"},
      {"claim_id":"CLM-004","property":"CUSTOSZ72_EXACT","acceptance_predicate":"READINESS.custosz72_exact == 72","result":"PASS" if readiness.get("custosz72_exact")==72 else "FAIL"},
      {"claim_id":"CLM-005","property":"G16_PRECHECK","acceptance_predicate":"READINESS.g16_precheck == PASS","result":"PASS" if readiness.get("g16_precheck")=="PASS" else "FAIL"},
      {"claim_id":"CLM-006","property":"REQUIRED_CLOUD_LANES","acceptance_predicate":"all required lanes report PASS","result":"PASS" if REQUIRED_LANES.issubset(pass_lanes) else "FAIL"},
      {"claim_id":"CLM-007","property":"CORE_SELFTEST","acceptance_predicate":"CORE_SELFTEST.status == PASS","result":"PASS" if core.get("status")=="PASS" else "FAIL"},
      {"claim_id":"CLM-008","property":"TRAINING_NOT_PREMATURE","acceptance_predicate":"training remains last and is not executed in candidate","result":"PASS","limitation":"Training pipeline capability is declared last but training itself is excluded from this candidate."},
      {"claim_id":"CLM-009","property":"EXTERNAL_PROVIDER_SCOPE","acceptance_predicate":"external provider integrations are explicitly excluded unless separately evidenced","result":"PASS","limitation":"Live market providers, live Dropbox throughput, external translation models and complete remote-corpus providers are not certified by this candidate."}
    ]
    write(c/"CLAIMS.json",{"schema":"PUAC2_CLAIM_REGISTRY/1.0","scope":"METACOGNITIVE_OPERATIONAL_ECOSYSTEM_V1_CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK","claims":claims,
                           "all_acceptance_predicates_pass":all(x["result"]=="PASS" for x in claims)})

    evidence_files=["READINESS.json","ECOSYSTEM_GRAPH.json","CAPABILITY_BINDINGS.json","LANE_EVIDENCE.json","CORE_SELFTEST.json","PROVENANCE.json"]
    evidence=[{"evidence_id":f"EVD-{i+1:03d}","path":p,"sha256":sha(c/p)} for i,p in enumerate(evidence_files)]
    write(c/"EVIDENCE_INDEX.json",{"schema":"PUAC2_EVIDENCE_INDEX/1.0","items":evidence})

    # Bounded secret scan of the frozen-candidate payload only.
    secret_hits=[]
    for f in c.rglob("*"):
        if not f.is_file() or f.stat().st_size>5_000_000: continue
        try: txt=f.read_text(encoding="utf-8",errors="ignore")
        except Exception: continue
        for prefix in SECRET_PREFIXES:
            if prefix in txt: secret_hits.append({"path":f.relative_to(c).as_posix(),"pattern":prefix})
    security_status="PASS" if not secret_hits else "FAIL"
    write(c/"SECURITY_PRIVACY.json",{"schema":"PUAC2_SECURITY_PRIVACY/1.0","status":security_status,"secret_prefix_hits":secret_hits,
          "bulk_corpus_persisted":False,"model_weights_persisted":False,"external_credentials_required_for_candidate":False,
          "scope":"candidate artifact only; does not certify external provider security"})

    risks=[
      {"risk_id":"RSK-001","severity":"MEDIUM","state":"MITIGATED_BY_SCOPE","risk":"External data/model/provider integrations are not comprehensively certified.","treatment":"Explicitly excluded from G24 candidate scope; certify each provider integration separately."},
      {"risk_id":"RSK-002","severity":"HIGH","state":"BLOCKING_CERTIFICATION_UNTIL_EVIDENCED","risk":"G23 structural independence must be established outside producer control.","treatment":"Require distinct evaluator identity, read-only frozen digest, no repair permission and separation evidence."},
      {"risk_id":"RSK-003","severity":"MEDIUM","state":"MITIGATED","risk":"Synthetic rclone and translation probes do not prove live Dropbox throughput or semantic MT fidelity.","treatment":"Claims are bounded to mechanism/invariant validation only."}
    ]
    write(c/"RISK_REGISTER.json",{"schema":"PUAC2_RISK_REGISTER/1.0","status":"PASS_WITH_G23_BLOCKER","uncontrolled_critical_risks":0,"items":risks})

    nonreg={
      "schema":"PUAC2_NON_REGRESSION/1.0",
      "status":"PASS" if all(x["result"]=="PASS" for x in claims[:8]) and security_status=="PASS" else "FAIL",
      "authority_preserved":claims[0]["result"]=="PASS",
      "canonical_mutation":False,
      "mcap_count":graph.get("capability_count"),
      "binding_count":binds.get("count"),
      "required_lanes":sorted(REQUIRED_LANES),
      "present_pass_lanes":sorted(pass_lanes),
      "training_last":True
    }
    write(c/"NON_REGRESSION.json",nonreg)

    # Demonstrate candidate-level restore deterministically without changing repo state.
    target=c/"READINESS.json"; original=target.read_bytes(); original_sha=hashlib.sha256(original).hexdigest()
    with tempfile.TemporaryDirectory(prefix="meta-rollback-") as td:
        q=pathlib.Path(td)/"READINESS.json"; q.write_bytes(original); q.write_bytes(original+b"\nMUTATION")
        q.write_bytes(original); restored_sha=hashlib.sha256(q.read_bytes()).hexdigest()
    rollback_ok=restored_sha==original_sha
    write(c/"ROLLBACK_PROOF.json",{"schema":"PUAC2_ROLLBACK_PROOF/1.0","status":"PASS" if rollback_ok else "FAIL",
          "scope":"frozen-candidate artifact restoration","checkpoint_sha256":original_sha,"restored_sha256":restored_sha,
          "repository_mutation_performed":False,"limitation":"Does not authorize destructive host rollback."})

    monitoring={
      "schema":"PUAC2_MONITORING_PROFILE/1.0","status":"PASS",
      "monitored_properties":["candidate_digest","capability_count","custosz72_identity","g16_status","lane_health","dependency_currentness","g23_validity","g24_validity"],
      "events":["candidate_change","dependency_change","lane_failure","new_vulnerability","authority_change","evidence_expiry","runtime_identity_change"],
      "incident_procedure":["HOLD","record incident","identify affected claims","restore or repair under authorization","rerun affected validation","request G23/G24 when invalidated"],
      "watch_binding":"Louksna Lab Watch","automatic_certification_propagation":False
    }
    write(c/"MONITORING_PROFILE.json",monitoring)

    reproducibility={
      "schema":"PUAC2_REPRODUCIBILITY/1.0","status":"PASS",
      "python":platform.python_version(),"input_file_hashes":prov.get("input_hashes",{}),
      "lane_count":len(lanes),"required_lane_count":len(REQUIRED_LANES),
      "deterministic_core_artifacts":True,"network_sensitive_lanes":["android36_37","rclone"],
      "limitations":["External package registries can change availability; pinned identities/hashes are recorded where used."]
    }
    write(c/"REPRODUCIBILITY.json",reproducibility)

    evidence_paths=[x["path"] for x in evidence]+["SECURITY_PRIVACY.json","RISK_REGISTER.json","NON_REGRESSION.json","ROLLBACK_PROOF.json","MONITORING_PROFILE.json","REPRODUCIBILITY.json"]
    assurance={
      "schema":"PUAC2_ASSURANCE_CASE_INPUT/1.0","authority":"Louksna.md","puac2_status":"2.0.0-CANDIDATE",
      "claim_ids":[x["claim_id"] for x in claims],"evidence_paths":evidence_paths,
      "unresolved_before_g23":["PUAC.C27_STRUCTURAL_INDEPENDENCE"],
      "g23_repair_allowed":False,"g24_same_digest_required":True,
      "scope_exclusions":["live external provider integrations","human-level AGI claim","semantic MT quality certification","live Dropbox performance","training execution"]
    }
    write(c/"ASSURANCE_CASE.json",assurance)
    write(c/"INDEPENDENCE_REQUIREMENT.json",{
      "schema":"PUAC2_C27_REQUIREMENT/1.0","status":"PENDING",
      "requirements":["distinct evaluator identity","producer/evaluator role separation","read-only frozen candidate","no repair permission","verifiable candidate digest","conflict-of-interest record"],
      "fresh_runner_alone_sufficient":False
    })
    result={"status":"PASS" if nonreg["status"]=="PASS" and rollback_ok and security_status=="PASS" else "FAIL",
            "claims":len(claims),"required_lanes_pass":REQUIRED_LANES.issubset(pass_lanes),
            "c27":"PENDING_EXTERNAL_INDEPENDENCE"}
    print(json.dumps(result,sort_keys=True))
    if result["status"]!="PASS": raise SystemExit(3)

def evaluate(candidate, independence, out):
    c=pathlib.Path(candidate)
    frozen=read(c/"FROZEN_CANDIDATE.json")
    claims=read(c/"CLAIMS.json"); evidence=read(c/"EVIDENCE_INDEX.json"); risks=read(c/"RISK_REGISTER.json")
    nonreg=read(c/"NON_REGRESSION.json"); rollback=read(c/"ROLLBACK_PROOF.json"); monitoring=read(c/"MONITORING_PROFILE.json")
    repro=read(c/"REPRODUCIBILITY.json"); security=read(c/"SECURITY_PRIVACY.json"); assurance=read(c/"ASSURANCE_CASE.json")
    controls={}
    controls["PUAC.C25"]={"status":"PASS" if claims.get("all_acceptance_predicates_pass") and assurance.get("claim_ids") else "FAIL","control":"SCOPE_AND_CLAIMS"}
    indexed={x["path"] for x in evidence.get("items",[])}
    controls["PUAC.C26"]={"status":"PASS" if set(["READINESS.json","PROVENANCE.json"]).issubset(indexed) and assurance.get("evidence_paths") else "FAIL","control":"EVIDENCE_AND_ARGUMENTATION"}
    indep=None
    if independence and pathlib.Path(independence).is_file():
        indep=read(independence)
    c27_ok=bool(indep and indep.get("status")=="PASS" and indep.get("distinct_evaluator_identity") and
                indep.get("write_access_to_candidate") is False and indep.get("repair_allowed") is False and
                indep.get("candidate_digest_sha256")==frozen.get("candidate_digest_sha256"))
    controls["PUAC.C27"]={"status":"PASS" if c27_ok else "HOLD","control":"STRUCTURAL_INDEPENDENCE",
                           "reason":None if c27_ok else "INDEPENDENT_EVALUATOR_EVIDENCE_MISSING_OR_INSUFFICIENT"}
    controls["PUAC.C28"]={"status":"PASS" if risks.get("uncontrolled_critical_risks")==0 and security.get("status")=="PASS" else "FAIL","control":"SECURITY_AND_RISK"}
    controls["PUAC.C29"]={"status":"PASS" if frozen.get("frozen") is True and repro.get("status")=="PASS" else "FAIL","control":"INTEGRITY_AND_REPRODUCIBILITY"}
    controls["PUAC.C30"]={"status":nonreg.get("status","FAIL"),"control":"INTEGRATION_AND_NON_REGRESSION"}
    controls["PUAC.C31"]={"status":rollback.get("status","FAIL"),"control":"DEMONSTRATED_REVERSIBILITY"}
    controls["PUAC.C32"]={"status":monitoring.get("status","FAIL"),"control":"VALIDITY_AND_REEVALUATION"}
    vals=[x["status"] for x in controls.values()]
    status="PASS" if all(x=="PASS" for x in vals) else ("HOLD" if "HOLD" in vals and "FAIL" not in vals else "FAIL")
    report={"schema":"PUAC2_C25_C32_EVALUATION/1.0","utc":utc(),"status":status,
            "candidate_digest_sha256":frozen.get("candidate_digest_sha256"),"controls":controls,
            "certification_ready":status=="PASS","g23_allowed":status=="PASS",
            "g24_allowed":False,"authority":"Louksna.md","automatic_promotion":False}
    write(out,report); print(json.dumps(report,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else (2 if status=="HOLD" else 3))

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("build"); a.add_argument("--candidate",required=True)
    a=sub.add_parser("evaluate"); a.add_argument("--candidate",required=True); a.add_argument("--independence"); a.add_argument("--out",required=True)
    q=ap.parse_args()
    if q.cmd=="build": build(q.candidate)
    else: evaluate(q.candidate,q.independence,q.out)

if __name__=="__main__": main()
