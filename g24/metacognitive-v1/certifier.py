#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, pathlib
from datetime import datetime, timezone

EXPECTED_DIGEST="b91d04bf79cd98eda846a8d0435f20323013f7ef647d9b288ab4cf29dcc35240"
EXPECTED_G23_RUN=36461879737
EXPECTED_G23_VALIDATOR_COMMIT="a4e3ca776f151b1fc3d61ef1bc884447cfadb203"
EXPECTED_PRODUCER_RUN=36459022140
EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}

def utc(): return datetime.now(timezone.utc).isoformat()
def load(path): return json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()
def digest_dir(root):
    root=pathlib.Path(root); rows=[]
    for f in sorted(x for x in root.rglob("*") if x.is_file() and x.name not in EXCLUDED):
        rows.append({"path":f.relative_to(root).as_posix(),"sha256":sha256_file(f),"size":f.stat().st_size})
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest()
def write(path,obj):
    p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--g23-dir",required=True)
    ap.add_argument("--authority",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--certifier-commit",required=True)
    ap.add_argument("--certifier-run-id",required=True)
    ap.add_argument("--authority-source-commit",required=True)
    q=ap.parse_args()

    c=pathlib.Path(q.candidate).resolve()
    gdir=pathlib.Path(q.g23_dir).resolve()
    authority=pathlib.Path(q.authority).resolve()
    out=pathlib.Path(q.out).resolve()
    failures=[]

    # Certifier itself must not be able to repair candidate or G23 evidence.
    write_denied_candidate=False
    try:
        with open(c/"READINESS.json","ab") as f: f.write(b"X")
    except (PermissionError,OSError):
        write_denied_candidate=True
    if not write_denied_candidate: failures.append("CANDIDATE_WRITE_NOT_DENIED")

    write_denied_g23=False
    try:
        with open(gdir/"G23_RECORD.json","ab") as f: f.write(b"X")
    except (PermissionError,OSError):
        write_denied_g23=True
    if not write_denied_g23: failures.append("G23_RECORD_WRITE_NOT_DENIED")

    token_absent=("GITHUB_TOKEN" not in os.environ and "GH_TOKEN" not in os.environ)
    if not token_absent: failures.append("CERTIFIER_PROCESS_HAS_GITHUB_CREDENTIAL")

    actual=digest_dir(c)
    frozen=load(c/"FROZEN_CANDIDATE.json")
    prov=load(c/"PROVENANCE.json")
    g23=load(gdir/"G23_RECORD.json")
    puac=load(gdir/"PUAC2_INDEPENDENT_EVALUATION.json")
    c27=load(gdir/"C27_INDEPENDENCE_EVIDENCE.json")

    if actual!=EXPECTED_DIGEST: failures.append("CANDIDATE_DIGEST_MISMATCH")
    if frozen.get("candidate_digest_sha256")!=actual: failures.append("FROZEN_DIGEST_MISMATCH")
    if g23.get("status")!="PASS": failures.append("G23_NOT_PASS")
    if g23.get("g24_authorized") is not True: failures.append("G23_DID_NOT_AUTHORIZE_G24")
    if g23.get("candidate_digest_sha256")!=actual: failures.append("G23_DIGEST_MISMATCH")
    if g23.get("validator_commit_sha")!=EXPECTED_G23_VALIDATOR_COMMIT: failures.append("G23_VALIDATOR_COMMIT_MISMATCH")
    if g23.get("candidate_source_run_id")!=EXPECTED_PRODUCER_RUN: failures.append("G23_PRODUCER_RUN_MISMATCH")
    if puac.get("status")!="PASS" or puac.get("certification_ready") is not True: failures.append("PUAC2_NOT_CERTIFICATION_READY")
    if any(v.get("status")!="PASS" for v in puac.get("controls",{}).values()): failures.append("PUAC2_CONTROL_NOT_PASS")
    if c27.get("status")!="PASS" or c27.get("distinct_evaluator_identity") is not True: failures.append("C27_NOT_PASS")

    authority_sha=sha256_file(authority)
    input_hashes=prov.get("input_hashes",{})
    candidate_authority_sha=input_hashes.get("Louksna.md")
    authority_ok=(
        prov.get("authority")=="Louksna.md"
        and candidate_authority_sha==authority_sha
        and q.certifier_commit!=EXPECTED_G23_VALIDATOR_COMMIT
    )
    if not authority_ok: failures.append("LOUKSNA_AUTHORITY_IDENTITY_MISMATCH")

    certifier_identity=f"GITHUB_ACTIONS_G24_CERTIFIER_V1@{q.certifier_commit}:run:{q.certifier_run_id}"
    authority_evidence={
      "schema":"G24_AUTHORITY_EVIDENCE/2.0",
      "status":"PASS" if authority_ok else "FAIL",
      "authority_id":f"LOUKSNA_MD_SHA256:{authority_sha}",
      "authority_name":"Louksna.md",
      "authority_authenticated":authority_ok,
      "authority_content_sha256":authority_sha,
      "candidate_provenance_authority_sha256":candidate_authority_sha,
      "authority_source_commit":q.authority_source_commit,
      "authority_blob_integrity":"CONTENT_SHA256_MATCH_TO_CANDIDATE_PROVENANCE",
      "certifier_identity":certifier_identity,
      "candidate_digest_sha256":actual,
      "certification_scope":"INTERNAL_PROJECT_CERTIFICATION",
      "external_regulatory_certification":False,
      "content_addressed_reference":f"sha256:{authority_sha}",
      "evaluated_utc":utc()
    }
    write(out/"AUTHORITY_EVIDENCE.json",authority_evidence)

    status="PASS" if not failures else "FAIL"
    cert={
      "schema":"G24_CERTIFICATION/2.0",
      "status":status,
      "candidate_digest_sha256":actual,
      "scope":"METACOGNITIVE_OPERATIONAL_ECOSYSTEM_V1_CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK",
      "authority":"Louksna.md",
      "authority_id":authority_evidence["authority_id"],
      "certifier_identity":certifier_identity,
      "producer_run_id":EXPECTED_PRODUCER_RUN,
      "g23_run_id":EXPECTED_G23_RUN,
      "g23_validator_commit":EXPECTED_G23_VALIDATOR_COMMIT,
      "g23_status":g23.get("status"),
      "puac2_status":puac.get("status"),
      "c27_status":c27.get("status"),
      "candidate_write_access":False if write_denied_candidate else True,
      "g23_record_write_access":False if write_denied_g23 else True,
      "repair_allowed":False,
      "certification_propagation":False,
      "canonical_mutation":False,
      "external_provider_integrations_certified":False,
      "training_executed":False,
      "scope_exclusions":g23.get("scope_exclusions",[]),
      "active_authorized":status=="PASS",
      "failures":failures,
      "certified_utc":utc()
    }
    write(out/"G24_CERTIFICATION.json",cert)
    write(out/"CERTIFICATION_CHAIN.json",{
      "schema":"CERTIFICATION_CHAIN/1.0",
      "candidate_digest_sha256":actual,
      "producer":{"run_id":EXPECTED_PRODUCER_RUN},
      "g23":{"run_id":EXPECTED_G23_RUN,"validator_commit":EXPECTED_G23_VALIDATOR_COMMIT,"status":g23.get("status")},
      "g24":{"certifier_commit":q.certifier_commit,"certifier_run_id":q.certifier_run_id,"status":status},
      "authority_evidence_sha256":sha256_file(out/"AUTHORITY_EVIDENCE.json"),
      "g23_record_sha256":sha256_file(gdir/"G23_RECORD.json"),
      "puac2_independent_evaluation_sha256":sha256_file(gdir/"PUAC2_INDEPENDENT_EVALUATION.json"),
      "automatic_certification_propagation":False
    })
    print(json.dumps({"status":status,"candidate_digest_sha256":actual,"authority_authenticated":authority_ok,"failures":failures},sort_keys=True))
    raise SystemExit(0 if status=="PASS" else 4)

if __name__=="__main__": main()
