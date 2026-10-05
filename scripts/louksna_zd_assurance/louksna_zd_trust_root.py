#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, pathlib, sys
from datetime import datetime, timezone

EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
REQUIRED=[
  "FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt","BUILD_RESULT.json",
  "DEB_MANIFEST.json","INSTALL_RESULT.json","ROLLBACK_PROOF.json",
  "NON_REGRESSION.json","SECURITY_RISK.json","PROVENANCE.json",
  "CLAIMS.json","EVIDENCE_INDEX.json","ASSURANCE_CASE.json",
  "MONITORING_PROFILE.json","REPRODUCIBILITY.json","INDEPENDENCE_REQUIREMENT.json"
]

def utc(): return datetime.now(timezone.utc).isoformat()
def sha_bytes(b): return hashlib.sha256(b).hexdigest()
def sha_file(p): return sha_bytes(pathlib.Path(p).read_bytes())
def read(p): return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
def write(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def digest_candidate(root):
    root=pathlib.Path(root); rows=[]
    for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
        rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha_file(f),"size":f.stat().st_size})
    return sha_bytes(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()),rows

def fail_report(out,schema,failures,extra=None,code=3):
    obj={"schema":schema,"utc":utc(),"status":"FAIL","failures":failures}
    if extra: obj.update(extra)
    write(out,obj); print(json.dumps(obj,sort_keys=True)); raise SystemExit(code)

def g23(candidate,independence,out):
    root=pathlib.Path(candidate); failures=[]
    for name in REQUIRED:
        if not (root/name).is_file(): failures.append("MISSING:"+name)
    if failures: fail_report(out,"LOUKSNA_ZD_G23/1.0",failures,{"repair_allowed":False})

    frozen=read(root/"FROZEN_CANDIDATE.json")
    actual,rows=digest_candidate(root)
    expected=frozen.get("candidate_digest_sha256")
    if actual!=expected: failures.append("CANDIDATE_DIGEST_MISMATCH")
    if (root/"CANDIDATE_DIGEST.txt").read_text().strip()!=expected: failures.append("DIGEST_POINTER_MISMATCH")

    build=read(root/"BUILD_RESULT.json")
    deb=read(root/"DEB_MANIFEST.json")
    install=read(root/"INSTALL_RESULT.json")
    rollback=read(root/"ROLLBACK_PROOF.json")
    nonreg=read(root/"NON_REGRESSION.json")
    security=read(root/"SECURITY_RISK.json")
    prov=read(root/"PROVENANCE.json")
    claims=read(root/"CLAIMS.json")
    evidence=read(root/"EVIDENCE_INDEX.json")
    assurance=read(root/"ASSURANCE_CASE.json")
    monitoring=read(root/"MONITORING_PROFILE.json")
    repro=read(root/"REPRODUCIBILITY.json")
    indep_req=read(root/"INDEPENDENCE_REQUIREMENT.json")
    indep=read(independence)

    deb_rel=deb.get("path")
    deb_path=root/deb_rel if deb_rel else pathlib.Path("/nonexistent")
    if build.get("status")!="PASS": failures.append("BUILD_NOT_PASS")
    if build.get("frontend_build")!="PASS": failures.append("FRONTEND_BUILD_NOT_PASS")
    if build.get("tauri_rust_build")!="PASS": failures.append("TAURI_RUST_BUILD_NOT_PASS")
    if build.get("deb_build")!="PASS": failures.append("DEB_BUILD_NOT_PASS")
    if not deb_path.is_file(): failures.append("DEB_PAYLOAD_MISSING")
    else:
        if sha_file(deb_path)!=deb.get("sha256"): failures.append("DEB_SHA256_MISMATCH")
        if deb_path.stat().st_size!=deb.get("size_bytes"): failures.append("DEB_SIZE_MISMATCH")
        if deb_path.stat().st_size>479000000: failures.append("DEB_EXCEEDS_479000000_BYTES")
    if deb.get("dpkg_structural_validation")!="PASS": failures.append("DPKG_STRUCTURE_NOT_PASS")
    if install.get("status")!="PASS": failures.append("DEBIAN13_INSTALLABILITY_NOT_PASS")
    if rollback.get("status")!="PASS": failures.append("ROLLBACK_NOT_PASS")
    if nonreg.get("status")!="PASS": failures.append("NON_REGRESSION_NOT_PASS")
    if security.get("status")!="PASS": failures.append("SECURITY_RISK_GATE_NOT_PASS")
    if security.get("uncontrolled_critical_risks")!=0: failures.append("UNCONTROLLED_CRITICAL_RISK")
    if prov.get("authority")!="Louksna.md": failures.append("AUTHORITY_MISMATCH")
    if prov.get("canonical_mutation") is not False: failures.append("CANONICAL_MUTATION")
    if prov.get("main_mutation") is not False: failures.append("MAIN_MUTATION_CLAIM_INVALID")
    if monitoring.get("status")!="PASS": failures.append("MONITORING_NOT_PASS")
    if monitoring.get("second_order_anti_paralysis")!="PASS": failures.append("SECOND_ORDER_ANTI_PARALYSIS_NOT_PASS")
    if repro.get("status")!="PASS": failures.append("REPRODUCIBILITY_NOT_PASS")
    if indep_req.get("g23_required") is not True or indep_req.get("g24_required") is not True:
        failures.append("INDEPENDENCE_REQUIREMENT_INVALID")

    for item in evidence.get("items",[]):
        p=root/item.get("path","")
        if not p.is_file() or sha_file(p)!=item.get("sha256"):
            failures.append("EVIDENCE_HASH_INVALID:"+item.get("path","UNKNOWN"))

    declared_claims=claims.get("claims") or []
    if not declared_claims: failures.append("CLAIMS_EMPTY")
    for c in declared_claims:
        if c.get("required") is True and c.get("status")!="PASS":
            failures.append("REQUIRED_CLAIM_NOT_PASS:"+str(c.get("claim_id")))
    if assurance.get("status")!="READY_FOR_G23": failures.append("ASSURANCE_CASE_NOT_READY")

    c27=(
      indep.get("status")=="PASS"
      and indep.get("event")=="workflow_run"
      and indep.get("write_access_to_candidate") is False
      and indep.get("repair_allowed") is False
      and indep.get("candidate_code_executed") is False
      and indep.get("candidate_artifact_consumed_as_data_only") is True
      and indep.get("candidate_digest_sha256")==actual
      and bool(indep.get("validator_trust_root_sha"))
      and bool(indep.get("distinct_evaluator_identity"))
    )
    if not c27: failures.append("PUAC_C27_STRUCTURAL_INDEPENDENCE_NOT_PASS")

    controls={
      "PUAC.C25":{"control":"SCOPE_AND_CLAIMS","status":"PASS" if declared_claims and not any(x.startswith("REQUIRED_CLAIM_NOT_PASS") for x in failures) else "FAIL"},
      "PUAC.C26":{"control":"EVIDENCE_AND_ARGUMENTATION","status":"PASS" if not any(x.startswith("EVIDENCE_HASH_INVALID") for x in failures) else "FAIL"},
      "PUAC.C27":{"control":"STRUCTURAL_INDEPENDENCE","status":"PASS" if c27 else "FAIL"},
      "PUAC.C28":{"control":"SECURITY_AND_RISK","status":"PASS" if security.get("status")=="PASS" and security.get("uncontrolled_critical_risks")==0 else "FAIL"},
      "PUAC.C29":{"control":"INTEGRITY_AND_REPRODUCIBILITY","status":"PASS" if actual==expected and repro.get("status")=="PASS" else "FAIL"},
      "PUAC.C30":{"control":"INTEGRATION_AND_NON_REGRESSION","status":nonreg.get("status","FAIL")},
      "PUAC.C31":{"control":"DEMONSTRATED_REVERSIBILITY","status":rollback.get("status","FAIL")},
      "PUAC.C32":{"control":"VALIDITY_AND_REEVALUATION","status":monitoring.get("status","FAIL")}
    }
    for cid,val in controls.items():
        if val["status"]!="PASS" and cid+"_NOT_PASS" not in failures:
            failures.append(cid+"_NOT_PASS")

    status="PASS" if not failures else "FAIL"
    certified=[c.get("claim_id") for c in declared_claims if c.get("status")=="PASS" and c.get("certifiable") is True]
    excluded=list(claims.get("claims_excluded") or [])
    report={
      "schema":"LOUKSNA_ZD_G23_INDEPENDENT_VALIDATION/1.0",
      "utc":utc(),"status":status,"authority":"Louksna.md",
      "scope":"LOUKSNA_ZD_EXACT_DEB_CANDIDATE_BUILD_INSTALL_ROLLBACK_UI_SHELL",
      "candidate_head_sha":frozen.get("candidate_head_sha"),
      "candidate_digest_sha256":actual,
      "validator_mode":"MAIN_CONTROLLED_WORKFLOW_RUN_READ_ONLY_DATA_VALIDATION",
      "validator_trust_root_sha":indep.get("validator_trust_root_sha"),
      "validator_script_sha256":sha_file(__file__),
      "repair_allowed":False,"candidate_code_executed":False,
      "puac2_controls":controls,"claims_validated":certified,
      "claims_excluded":excluded,"failures":failures,
      "g24_authorized":status=="PASS"
    }
    write(out,report); print(json.dumps(report,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 3)

def g24(candidate,g23_path,authority_path,out):
    root=pathlib.Path(candidate); failures=[]
    actual,_=digest_candidate(root)
    frozen=read(root/"FROZEN_CANDIDATE.json")
    claims=read(root/"CLAIMS.json")
    g23r=read(g23_path); auth=read(authority_path)
    if actual!=frozen.get("candidate_digest_sha256"): failures.append("FROZEN_DIGEST_MISMATCH")
    if g23r.get("status")!="PASS" or g23r.get("g24_authorized") is not True: failures.append("G23_NOT_AUTHORIZING")
    if g23r.get("candidate_digest_sha256")!=actual: failures.append("G23_DIGEST_MISMATCH")
    if auth.get("status")!="PASS" or auth.get("authority_authenticated") is not True: failures.append("AUTHORITY_NOT_AUTHENTICATED")
    if auth.get("candidate_digest_sha256")!=actual: failures.append("AUTHORITY_DIGEST_MISMATCH")
    if auth.get("repository")!="Plomillo/luna-linux-bridge": failures.append("AUTHORITY_REPOSITORY_MISMATCH")
    if auth.get("event")!="workflow_run": failures.append("AUTHORITY_EVENT_MISMATCH")
    if not str(auth.get("signature_reference","")).startswith("GITHUB_OIDC_JWT_SHA256:"): failures.append("OIDC_SIGNATURE_REFERENCE_MISSING")
    if not auth.get("authority_id"): failures.append("AUTHORITY_ID_MISSING")
    status="PASS" if not failures else "FAIL"
    cert={
      "schema":"LOUKSNA_ZD_G24_CERTIFICATION/1.0","utc":utc(),"status":status,
      "authority":"Louksna.md",
      "g24_authority":auth.get("authority_id"),
      "authority_signature_reference":auth.get("signature_reference"),
      "candidate_head_sha":frozen.get("candidate_head_sha"),
      "candidate_digest_sha256":actual,
      "scope":"LOUKSNA_ZD_EXACT_DEB_CANDIDATE_BUILD_INSTALL_ROLLBACK_UI_SHELL",
      "claims_certified":g23r.get("claims_validated",[]),
      "claims_excluded":list(claims.get("claims_excluded") or []),
      "g23_record_sha256":sha_file(g23_path),
      "g23_validator_trust_root_sha":g23r.get("validator_trust_root_sha"),
      "certification_propagation":False,
      "canonical_mutation":False,
      "external_certification":False,
      "active_authorized":False,
      "operational_authorization":"NOT_GRANTED_BY_CERTIFICATION",
      "failures":failures
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

if __name__=="__main__":
    main()
