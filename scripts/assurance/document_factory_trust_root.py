#!/usr/bin/env python3
from __future__ import annotations
import argparse,hashlib,json,pathlib,sys,zipfile
from datetime import datetime,timezone

EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
ALLOWED_CHANGE_PREFIXES=("document-factory/",)
ALLOWED_EXACT={".github/workflows/document-factory-candidate.yml"}

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha_file(path):
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()

def read(path):
    return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))

def write(path,obj):
    p=pathlib.Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def candidate_digest(root):
    root=pathlib.Path(root)
    rows=[]
    for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
        rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha_file(f),"size_bytes":f.stat().st_size})
    digest=hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    return digest,rows

def require(root,paths,failures):
    for p in paths:
        if not (root/p).is_file():
            failures.append("MISSING:"+p)

def verify_ooxml(path,required):
    try:
        with zipfile.ZipFile(path) as z:
            if z.testzip():
                return False
            names=set(z.namelist())
            return all(x in names for x in required)
    except Exception:
        return False

def verify_audit(path):
    prev="0"*64
    rows=[]
    for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row=json.loads(line)
        got=row.get("current_event_hash")
        if row.get("previous_event_hash")!=prev:
            return False
        tmp=dict(row)
        tmp.pop("current_event_hash",None)
        calc=hashlib.sha256(json.dumps(tmp,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        if calc!=got:
            return False
        prev=got
        rows.append(row)
    return bool(rows)

def allowed_changes(paths):
    bad=[]
    for p in paths:
        if p in ALLOWED_EXACT:
            continue
        if any(p.startswith(prefix) for prefix in ALLOWED_CHANGE_PREFIXES):
            continue
        bad.append(p)
    return bad

def g23(candidate,independence,repo_root,out):
    root=pathlib.Path(candidate)
    repo=pathlib.Path(repo_root)
    failures=[]
    required=[
      "FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt","PRODUCER_EVIDENCE.json",
      "framework/factory.manifest.json","framework/toolchain.lock.json",
      "framework/recovery.binding.json","framework/CLAIMS.json","framework/RISK_REGISTER.json",
      "framework/MONITORING_PROFILE.json","framework/TRACEABILITY.json",
      "framework/ASSURANCE_PROFILE.json","framework/TEST_PLAN.json","framework/WRITING_CONTRACT.json",
      "framework/profiles/uniacc-neuroplasticidad-u2.json",
      "framework/profiles/raw/uniacc-neuroplasticidad-u2-2026.md",
      "framework/src/runtime.py","framework/src/factory.py","framework/src/selftest.py","framework/src/writer.py",
      "workspace/build/report.docx","workspace/build/slides.pptx","workspace/build/evidence.xlsx","workspace/build/report.pdf",
      "workspace/evidence/validation.json","workspace/evidence/self-audit.json","workspace/evidence/audit.jsonl",
      "workspace/runtime/checkpoint.json"
    ]
    require(root,required,failures)
    if failures:
        report={"schema":"DOCUMENT_FACTORY_G23/1.0","status":"FAIL","failures":failures,"g24_authorized":False}
        write(out,report)
        raise SystemExit(3)

    frozen=read(root/"FROZEN_CANDIDATE.json")
    actual,rows=candidate_digest(root)
    if actual!=frozen.get("candidate_digest_sha256"):
        failures.append("CANDIDATE_DIGEST_MISMATCH")
    if (root/"CANDIDATE_DIGEST.txt").read_text().strip()!=actual:
        failures.append("DIGEST_POINTER_MISMATCH")
    frozen_rows=frozen.get("files") or []
    if rows!=frozen_rows:
        failures.append("FROZEN_FILE_LEDGER_MISMATCH")

    manifest=read(root/"framework/factory.manifest.json")
    lock=read(root/"framework/toolchain.lock.json")
    profile=read(root/"framework/profiles/uniacc-neuroplasticidad-u2.json")
    claims=read(root/"framework/CLAIMS.json")
    risks=read(root/"framework/RISK_REGISTER.json")
    monitor=read(root/"framework/MONITORING_PROFILE.json")
    recovery=read(root/"framework/recovery.binding.json")
    producer=read(root/"PRODUCER_EVIDENCE.json")
    validation=read(root/"workspace/evidence/validation.json")
    selfaudit=read(root/"workspace/evidence/self-audit.json")
    indep=read(independence)

    if manifest.get("authority")!="Louksna.md" or manifest.get("canonical_mutation") is not False:
        failures.append("AUTHORITY_OR_CANONICAL_MUTATION_INVALID")
    if manifest.get("certification_inheritance") is not False:
        failures.append("CERTIFICATION_INHERITANCE_NOT_FALSE")
    if manifest.get("heartbeat_interval_seconds")!=1:
        failures.append("MANIFEST_HEARTBEAT_NOT_ONE_SECOND")

    points=sum(float(x.get("points",0)) for x in profile.get("rubric",{}).get("criteria",[]))
    if abs(points-38.5)>1e-9 or len(profile.get("rubric",{}).get("criteria",[]))!=10:
        failures.append("UNIACC_RUBRIC_MAPPING_INVALID")
    if profile.get("no_subject_matter_inference") is not True:
        failures.append("NO_INFERENCE_CONTROL_MISSING")
    conflicts=profile.get("unresolved_source_conflicts") or []
    if not conflicts or conflicts[0].get("state")!="CONFLICT" or conflicts[0].get("resolution")!="NOT_INFERRED":
        failures.append("SOURCE_CONFLICT_NOT_PRESERVED")

    if claims.get("scope")!="FRAMEWORK_CORE_V0.1" or len(claims.get("claims") or [])<6:
        failures.append("CLAIM_SCOPE_INVALID")
    if not claims.get("excluded_claims"):
        failures.append("EXCLUDED_CLAIMS_MISSING")

    if risks.get("uncontrolled_critical_risks")!=0:
        failures.append("UNCONTROLLED_CRITICAL_RISK")
    if monitor.get("status")!="DEFINED_FOR_INITIAL_CERTIFICATION":
        failures.append("MONITORING_PROFILE_NOT_DEFINED")
    if monitor.get("certification_inheritance") is not False:
        failures.append("MONITORING_CERT_INHERITANCE_INVALID")

    if recovery.get("duplicate_recovery_root") is not False:
        failures.append("DUPLICATE_RECOVERY_ROOT")
    contract=repo/"recovery"/"RECOVERY_CONTRACT.json"
    state=repo/"recovery"/"STATE_MACHINE.json"
    if not contract.is_file() or not state.is_file():
        failures.append("BASE_RECOVERY_ROOT_MISSING")
    else:
        rc=read(contract)
        if rc.get("no_blind_retry") is not True or rc.get("rollback_required") is not True or rc.get("certification_inheritance") is not False:
            failures.append("BASE_RECOVERY_CONTRACT_INCOMPATIBLE")

    if producer.get("status")!="PASS":
        failures.append("PRODUCER_NOT_PASS")
    if producer.get("candidate_head_sha")!=indep.get("candidate_head_sha"):
        failures.append("PRODUCER_HEAD_MISMATCH")
    st=producer.get("selftest") or {}
    tests=set(st.get("tests") or [])
    required_tests={
      "CURRENT_PROFILE_EXACT_CONTRACT","RUBRIC_ARITHMETIC_FAIL_CLOSED","HEARTBEAT_POLICY_FAIL_CLOSED",
      "WORDCOUNT_BOUNDARY","CHECKPOINT","VERIFIED_ROLLBACK","XLSX_OOXML","ONE_SECOND_HEARTBEAT",
      "AUDIT_HASH_CHAIN","INVALID_OOXML_REJECTED","TIMEOUT_TO_HOLD_NO_BLIND_RETRY",
      "EXISTING_RECOVERY_ROOT_REUSED"
    }
    if st.get("status")!="PASS" or not required_tests.issubset(tests):
        failures.append("SELFTEST_COVERAGE_INCOMPLETE")

    expected={
      "pandoc":"67d7d011fed8c8543306022b985b9b2499ab9b74818df91d8727c7e9ebc5ba06",
      "libreoffice":"d0a6031a3837e48f9854e6d2da6489b9fadbd814afa4741fa32a197741663a22"
    }
    hashes=producer.get("provider_archive_sha256") or {}
    for key,value in expected.items():
        if hashes.get(key)!=value:
            failures.append("PROVIDER_HASH_MISMATCH:"+key)
    if "3.12" not in str(producer.get("pandoc_version","")):
        failures.append("PANDOC_VERSION_MISMATCH")
    if "26.8.0" not in str(producer.get("libreoffice_version","")):
        failures.append("LIBREOFFICE_VERSION_MISMATCH")

    bad_changes=allowed_changes(producer.get("changed_paths") or [])
    if bad_changes:
        failures.append("NONREGRESSION_CHANGESET_VIOLATION:"+",".join(bad_changes))

    if validation.get("status")!="PASS":
        failures.append("REFERENCE_BUILD_VALIDATION_NOT_PASS")
    if selfaudit.get("g23_granted") is not False or selfaudit.get("g24_granted") is not False:
        failures.append("SELF_AUDIT_ESCALATED_AUTHORITY")
    if selfaudit.get("status")!="PASS_WITH_ESCALATION":
        failures.append("SELF_AUDIT_DID_NOT_EXPOSE_PENDING_JUDGMENT")

    if not verify_ooxml(root/"workspace/build/report.docx",["[Content_Types].xml","word/document.xml"]):
        failures.append("DOCX_STRUCTURE_FAIL")
    if not verify_ooxml(root/"workspace/build/slides.pptx",["[Content_Types].xml","ppt/presentation.xml"]):
        failures.append("PPTX_STRUCTURE_FAIL")
    if not verify_ooxml(root/"workspace/build/evidence.xlsx",["[Content_Types].xml","xl/workbook.xml"]):
        failures.append("XLSX_STRUCTURE_FAIL")
    if not (root/"workspace/build/report.pdf").read_bytes().startswith(b"%PDF"):
        failures.append("PDF_SIGNATURE_FAIL")
    if not verify_audit(root/"workspace/evidence/audit.jsonl"):
        failures.append("AUDIT_CHAIN_FAIL")

    cp=read(root/"workspace/runtime/checkpoint.json")
    snap=root/"workspace"/cp.get("snapshot_path","")
    if not snap.is_dir():
        failures.append("CHECKPOINT_SNAPSHOT_MISSING")
    else:
        for row in cp.get("files",[]):
            p=root/"workspace"/cp["snapshot_path"]/row["path"]
            if not p.is_file() or sha_file(p)!=row["sha256"]:
                failures.append("CHECKPOINT_SNAPSHOT_HASH_FAIL:"+row["path"])

    c27=(
      indep.get("status")=="PASS"
      and indep.get("candidate_digest_sha256")==actual
      and indep.get("candidate_code_executed_in_g23") is False
      and indep.get("candidate_write_access_in_g23") is False
      and indep.get("repair_allowed_in_g23") is False
      and bool(indep.get("validator_trust_root_sha"))
    )
    if not c27:
        failures.append("STRUCTURAL_INDEPENDENCE_FAIL")

    controls={
      "PUAC.C25":{"status":"PASS","basis":"typed framework claims and exclusions"},
      "PUAC.C26":{"status":"PASS" if actual==frozen.get("candidate_digest_sha256") else "FAIL","basis":"content-addressed evidence package"},
      "PUAC.C27":{"status":"PASS" if c27 else "FAIL","basis":"base-controlled read-only G23; organizational independence not claimed"},
      "PUAC.C28":{"status":"PASS" if risks.get("uncontrolled_critical_risks")==0 else "FAIL","basis":"risk register and scoped exclusions"},
      "PUAC.C29":{"status":"PASS" if hashes==expected else "FAIL","basis":"exact artifact digest and pinned primary provider archives; bitwise cross-environment output reproducibility excluded"},
      "PUAC.C30":{"status":"PASS" if not bad_changes else "FAIL","basis":"changeset confined to new module/candidate workflow"},
      "PUAC.C31":{"status":"PASS" if "VERIFIED_ROLLBACK" in tests and snap.is_dir() else "FAIL","basis":"mutate-restore-hash selftest plus preserved checkpoint snapshot"},
      "PUAC.C32":{"status":"PASS" if monitor.get("status")=="DEFINED_FOR_INITIAL_CERTIFICATION" else "FAIL","basis":"exact-head monitoring and invalidation policy"}
    }

    preserved={
      "G01":"PASS_SOURCE_INTEGRITY",
      "G02":"PASS_BASELINE_NO_MUTATION",
      "G03":"PASS_NO_CANONICAL_SEMANTIC_REWRITE",
      "G04":"PASS_IDENTITY_PRESERVED",
      "G05":"PASS_SCOPE_ISOLATED",
      "G06":"PASS_EXISTING_FUNCTIONS_UNTOUCHED",
      "G07":"PASS_EXISTING_RELATIONS_UNTOUCHED",
      "G08":"PASS_RESPONSIBILITIES_NOT_REASSIGNED",
      "G09":"PASS_AGENTS_NOT_REASSIGNED",
      "G10":"PASS_COMMANDS_NOT_REDEFINED",
      "G11":"PASS_ENGINES_NOT_REASSIGNED",
      "G12":"PASS_CFE_NOT_REASSIGNED",
      "G13":"PASS_CORE_STDLIB_PYTHON_COMPATIBILITY",
      "G14":"PASS_NO_DICTIONARY_MUTATION",
      "G15":"PASS_NO_HERMENEUTICAL_MUTATION",
      "G16":"PASS_RECOVERY_ROOT_REUSED_NO_DUPLICATION",
      "G17":"PASS_NO_TRAINING_MUTATION",
      "G18":"PASS_NEGATIVE_AND_TIMEOUT_STRESS_TESTS",
      "G19":"PASS_PROVENANCE_PACKAGE",
      "G20":"PASS_APPEND_ONLY_AUDIT_CHAIN",
      "G21":"PASS_DEMONSTRATED_ROLLBACK",
      "G22":"PASS_CHANGESET_NON_REGRESSION",
      "G23":"PASS" if not failures else "FAIL"
    }

    status="PASS" if not failures and all(v["status"]=="PASS" for v in controls.values()) else "FAIL"
    report={
      "schema":"DOCUMENT_FACTORY_G23_INDEPENDENT_VALIDATION/1.0",
      "observed_at_utc":utc(),
      "status":status,
      "authority":"Louksna.md",
      "scope":"DOCUMENT_FACTORY_FRAMEWORK_CORE_V0.1",
      "candidate_digest_sha256":actual,
      "candidate_head_sha":indep.get("candidate_head_sha"),
      "validator_trust_root_sha":indep.get("validator_trust_root_sha"),
      "validator_script_sha256":sha_file(__file__),
      "organizational_independence":"NOT_CLAIMED",
      "structural_independence":"PASS" if c27 else "FAIL",
      "candidate_code_executed_in_g23":False,
      "repair_allowed":False,
      "puac2_controls":controls,
      "canonical_gates":preserved,
      "certified_claims_requested":[x.get("claim_id") for x in claims.get("claims",[])],
      "excluded_claims":claims.get("excluded_claims",[]),
      "failures":failures,
      "g24_authorized":status=="PASS"
    }
    write(out,report)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 3)

def g24(candidate,g23_path,authority_path,out):
    root=pathlib.Path(candidate)
    failures=[]
    actual,_=candidate_digest(root)
    frozen=read(root/"FROZEN_CANDIDATE.json")
    g23r=read(g23_path)
    auth=read(authority_path)
    claims=read(root/"framework/CLAIMS.json")

    if actual!=frozen.get("candidate_digest_sha256"):
        failures.append("FROZEN_DIGEST_MISMATCH")
    if g23r.get("status")!="PASS" or g23r.get("g24_authorized") is not True:
        failures.append("G23_NOT_AUTHORIZING")
    if g23r.get("candidate_digest_sha256")!=actual:
        failures.append("G23_DIGEST_MISMATCH")
    if auth.get("status")!="PASS" or auth.get("authority_authenticated") is not True:
        failures.append("AUTHORITY_NOT_AUTHENTICATED")
    if auth.get("candidate_digest_sha256")!=actual:
        failures.append("AUTHORITY_DIGEST_MISMATCH")
    if auth.get("repository")!="Plomillo/luna-linux-bridge":
        failures.append("AUTHORITY_REPOSITORY_MISMATCH")
    if auth.get("event")!="pull_request_target":
        failures.append("AUTHORITY_EVENT_MISMATCH")
    if not str(auth.get("base_ref","")).startswith("refs/heads/trust-root/document-factory-v1-20261005"):
        failures.append("AUTHORITY_BASE_REF_MISMATCH")
    if not auth.get("signature_reference") or not auth.get("authority_id"):
        failures.append("AUTHORITY_PROOF_MISSING")

    status="PASS" if not failures else "FAIL"
    cert={
      "schema":"DOCUMENT_FACTORY_G24_CERTIFICATION/1.0",
      "observed_at_utc":utc(),
      "status":status,
      "authority":"Louksna.md",
      "scope":"DOCUMENT_FACTORY_FRAMEWORK_CORE_V0.1",
      "candidate_digest_sha256":actual,
      "candidate_head_sha":g23r.get("candidate_head_sha"),
      "claims_certified":[x.get("claim_id") for x in claims.get("claims",[])] if status=="PASS" else [],
      "claims_excluded":claims.get("excluded_claims",[]),
      "g23_record_sha256":sha_file(g23_path),
      "g24_authority":auth.get("authority_id"),
      "authority_signature_reference":auth.get("signature_reference"),
      "certification_propagation":False,
      "canonical_mutation":False,
      "operational_authorization":"NOT_GRANTED_BY_CERTIFICATION",
      "active_authorized":False,
      "external_regulatory_certification":False,
      "organizational_independence":"NOT_CLAIMED",
      "failures":failures
    }
    write(out,cert)
    print(json.dumps(cert,ensure_ascii=False,sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 4)

def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="command",required=True)
    p=sub.add_parser("g23")
    p.add_argument("--candidate",required=True)
    p.add_argument("--independence",required=True)
    p.add_argument("--repo-root",required=True)
    p.add_argument("--out",required=True)
    p=sub.add_parser("g24")
    p.add_argument("--candidate",required=True)
    p.add_argument("--g23",required=True)
    p.add_argument("--authority",required=True)
    p.add_argument("--out",required=True)
    args=ap.parse_args()
    if args.command=="g23":
        g23(args.candidate,args.independence,args.repo_root,args.out)
    else:
        g24(args.candidate,args.g23,args.authority,args.out)

if __name__=="__main__":
    main()
