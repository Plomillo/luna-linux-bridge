#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys
from datetime import datetime, timezone

EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
REQUIRED_LANES={"debian13","android36_37","windows","rclone","remote_range","translation_scale","telemetry"}

def utc(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(pathlib.Path(p).read_bytes())
def read(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def write(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def candidate_digest(root):
    root=pathlib.Path(root); rows=[]
    for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
        rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha_file(f),"size":f.stat().st_size})
    return sha_bytes(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()),rows

def require_files(root,names,failures):
    for name in names:
        if not (root/name).is_file(): failures.append("MISSING:"+name)

def g23(candidate, independence, out):
    root=pathlib.Path(candidate); failures=[]
    required=[
      "FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt","READINESS.json","ECOSYSTEM_GRAPH.json",
      "CAPABILITY_BINDINGS.json","LANE_EVIDENCE.json","CORE_SELFTEST.json","PROVENANCE.json",
      "CLAIMS.json","EVIDENCE_INDEX.json","SECURITY_PRIVACY.json","RISK_REGISTER.json",
      "NON_REGRESSION.json","ROLLBACK_PROOF.json","MONITORING_PROFILE.json","REPRODUCIBILITY.json",
      "ASSURANCE_CASE.json","INDEPENDENCE_REQUIREMENT.json"
    ]
    require_files(root,required,failures)
    if failures:
        report={"schema":"G23_TRUST_ROOT/1.0","utc":utc(),"status":"FAIL","failures":failures,"repair_allowed":False}
        write(out,report); print(json.dumps(report,sort_keys=True)); raise SystemExit(3)

    frozen=read(root/"FROZEN_CANDIDATE.json")
    actual,rows=candidate_digest(root)
    expected=frozen.get("candidate_digest_sha256")
    if actual!=expected: failures.append("CANDIDATE_DIGEST_MISMATCH")
    if (root/"CANDIDATE_DIGEST.txt").read_text().strip()!=expected: failures.append("DIGEST_POINTER_MISMATCH")

    readiness=read(root/"READINESS.json"); graph=read(root/"ECOSYSTEM_GRAPH.json")
    binds=read(root/"CAPABILITY_BINDINGS.json"); lanes=read(root/"LANE_EVIDENCE.json").get("lanes",{})
    core=read(root/"CORE_SELFTEST.json"); prov=read(root/"PROVENANCE.json")
    claims=read(root/"CLAIMS.json"); evidence=read(root/"EVIDENCE_INDEX.json")
    sec=read(root/"SECURITY_PRIVACY.json"); risks=read(root/"RISK_REGISTER.json")
    nonreg=read(root/"NON_REGRESSION.json"); rollback=read(root/"ROLLBACK_PROOF.json")
    monitoring=read(root/"MONITORING_PROFILE.json"); repro=read(root/"REPRODUCIBILITY.json")
    assurance=read(root/"ASSURANCE_CASE.json"); indep=read(independence)

    pass_lanes={k for k,v in lanes.items() if isinstance(v,dict) and v.get("status")=="PASS"}
    if readiness.get("status")!="PASS": failures.append("READINESS_NOT_PASS")
    if graph.get("capability_count")!=59 or binds.get("count")!=59: failures.append("MCAP59_NOT_COMPLETE")
    if core.get("status")!="PASS": failures.append("CORE_SELFTEST_NOT_PASS")
    if prov.get("authority")!="Louksna.md" or prov.get("canonical_mutation") is not False: failures.append("AUTHORITY_OR_CANONICAL_MUTATION")
    if not REQUIRED_LANES.issubset(pass_lanes): failures.append("REQUIRED_LANES_MISSING:"+",".join(sorted(REQUIRED_LANES-pass_lanes)))

    controls={}
    c25=claims.get("all_acceptance_predicates_pass") is True and bool(assurance.get("claim_ids"))
    controls["PUAC.C25"]={"control":"SCOPE_AND_CLAIMS","status":"PASS" if c25 else "FAIL"}

    evidence_ok=True
    for item in evidence.get("items",[]):
        p=root/item.get("path","")
        if not p.is_file() or sha_file(p)!=item.get("sha256"): evidence_ok=False
    c26=evidence_ok and bool(assurance.get("evidence_paths"))
    controls["PUAC.C26"]={"control":"EVIDENCE_AND_ARGUMENTATION","status":"PASS" if c26 else "FAIL"}

    c27=(
      indep.get("status")=="PASS"
      and bool(indep.get("distinct_evaluator_identity"))
      and indep.get("write_access_to_candidate") is False
      and indep.get("repair_allowed") is False
      and indep.get("candidate_code_executed") is False
      and indep.get("candidate_digest_sha256")==actual
      and bool(indep.get("validator_trust_root_sha"))
      and indep.get("event")=="pull_request_target"
    )
    controls["PUAC.C27"]={"control":"STRUCTURAL_INDEPENDENCE","status":"PASS" if c27 else "FAIL",
      "evaluator":indep.get("distinct_evaluator_identity"),"trust_root":indep.get("validator_trust_root_sha")}

    c28=risks.get("uncontrolled_critical_risks")==0 and sec.get("status")=="PASS"
    controls["PUAC.C28"]={"control":"SECURITY_AND_RISK","status":"PASS" if c28 else "FAIL"}
    c29=frozen.get("frozen") is True and repro.get("status")=="PASS"
    controls["PUAC.C29"]={"control":"INTEGRITY_AND_REPRODUCIBILITY","status":"PASS" if c29 else "FAIL"}
    controls["PUAC.C30"]={"control":"INTEGRATION_AND_NON_REGRESSION","status":nonreg.get("status","FAIL")}
    controls["PUAC.C31"]={"control":"DEMONSTRATED_REVERSIBILITY","status":rollback.get("status","FAIL")}
    controls["PUAC.C32"]={"control":"VALIDITY_AND_REEVALUATION","status":monitoring.get("status","FAIL")}

    for cid,v in controls.items():
        if v["status"]!="PASS": failures.append(cid+"_NOT_PASS")

    status="PASS" if not failures else "FAIL"
    report={
      "schema":"G23_INDEPENDENT_VALIDATION/2.0",
      "utc":utc(),"status":status,"authority":"Louksna.md",
      "candidate_digest_sha256":actual,"frozen_digest_sha256":expected,
      "validator_trust_root_sha":indep.get("validator_trust_root_sha"),
      "validator_script_sha256":sha_file(__file__),
      "validator_mode":"BASE_BRANCH_PULL_REQUEST_TARGET_READ_ONLY_DATA_VALIDATION",
      "repair_allowed":False,"candidate_code_executed":False,
      "required_lanes":sorted(REQUIRED_LANES),"present_pass_lanes":sorted(pass_lanes),
      "puac2_controls":controls,"failures":failures,
      "g24_authorized":status=="PASS"
    }
    write(out,report); print(json.dumps(report,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 3)

def g24(candidate,g23_path,authority_path,out):
    root=pathlib.Path(candidate); failures=[]
    actual,_=candidate_digest(root); frozen=read(root/"FROZEN_CANDIDATE.json")
    g23r=read(g23_path); auth=read(authority_path)
    if actual!=frozen.get("candidate_digest_sha256"): failures.append("FROZEN_DIGEST_MISMATCH")
    if g23r.get("status")!="PASS" or g23r.get("g24_authorized") is not True: failures.append("G23_NOT_AUTHORIZING")
    if g23r.get("candidate_digest_sha256")!=actual: failures.append("G23_DIGEST_MISMATCH")
    if auth.get("status")!="PASS" or auth.get("authority_authenticated") is not True: failures.append("AUTHORITY_NOT_AUTHENTICATED")
    if auth.get("candidate_digest_sha256")!=actual: failures.append("AUTHORITY_DIGEST_MISMATCH")
    if auth.get("repository")!="Plomillo/luna-linux-bridge": failures.append("AUTHORITY_REPOSITORY_MISMATCH")
    if auth.get("event")!="pull_request_target": failures.append("AUTHORITY_EVENT_MISMATCH")
    if not str(auth.get("base_ref","")).startswith("refs/heads/staging/custosz-mission-mailbox-20260928"): failures.append("AUTHORITY_BASE_REF_MISMATCH")
    if not auth.get("signature_reference"): failures.append("AUTHORITY_SIGNATURE_REFERENCE_MISSING")
    if not auth.get("authority_id"): failures.append("AUTHORITY_ID_MISSING")
    status="PASS" if not failures else "FAIL"
    cert={
      "schema":"G24_CERTIFICATION/2.0","utc":utc(),"status":status,
      "candidate_digest_sha256":actual,
      "scope":"METACOGNITIVE_OPERATIONAL_ECOSYSTEM_V1_CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK",
      "authority":"Louksna.md","certification_authority_id":auth.get("authority_id"),
      "authority_signature_reference":auth.get("signature_reference"),
      "g23_validator_trust_root_sha":g23r.get("validator_trust_root_sha"),
      "certification_propagation":False,"canonical_mutation":False,
      "external_provider_integrations_certified":False,
      "training_executed":False,
      "active_authorized":status=="PASS","failures":failures
    }
    write(out,cert); print(json.dumps(cert,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 4)

def main():
    ap=argparse.ArgumentParser(); sub=ap.add_subparsers(dest="cmd",required=True)
    a=sub.add_parser("g23"); a.add_argument("--candidate",required=True); a.add_argument("--independence",required=True); a.add_argument("--out",required=True)
    a=sub.add_parser("g24"); a.add_argument("--candidate",required=True); a.add_argument("--g23",required=True); a.add_argument("--authority",required=True); a.add_argument("--out",required=True)
    q=ap.parse_args()
    if q.cmd=="g23": g23(q.candidate,q.independence,q.out)
    else: g24(q.candidate,q.g23,q.authority,q.out)

if __name__=="__main__": main()
