#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, os, pathlib
from datetime import datetime, timezone

EXPECTED_DIGEST="b91d04bf79cd98eda846a8d0435f20323013f7ef647d9b288ab4cf29dcc35240"
PRODUCER_RUN_ID=36459022140
PRODUCER_HEAD_SHA="d930e9220ee5ab2013afca4da4ad4c876c20d4f2"
EXCLUDED={"FROZEN_CANDIDATE.json","CANDIDATE_DIGEST.txt"}
REQUIRED_LANES={"debian13","android36_37","windows","rclone","remote_range","translation_scale","telemetry"}

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
    return hashlib.sha256(json.dumps(rows,sort_keys=True,separators=(",",":")).encode()).hexdigest(),rows
def write(path,obj):
    p=pathlib.Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--candidate",required=True)
    ap.add_argument("--out",required=True)
    ap.add_argument("--evaluator-commit",required=True)
    ap.add_argument("--evaluator-run-id",required=True)
    ap.add_argument("--workflow-ref",required=True)
    q=ap.parse_args()
    c=pathlib.Path(q.candidate).resolve()
    out=pathlib.Path(q.out).resolve()
    failures=[]

    probe=c/"READINESS.json"
    write_denied=False
    try:
        with open(probe,"ab") as f: f.write(b"X")
    except (PermissionError,OSError):
        write_denied=True
    if not write_denied:
        failures.append("CANDIDATE_WRITE_NOT_DENIED")

    actual,rows=digest_dir(c)
    frozen=load(c/"FROZEN_CANDIDATE.json")
    digest_txt=(c/"CANDIDATE_DIGEST.txt").read_text(encoding="utf-8").strip()
    if actual!=EXPECTED_DIGEST: failures.append("EXPECTED_CANDIDATE_DIGEST_MISMATCH")
    if actual!=frozen.get("candidate_digest_sha256"): failures.append("FROZEN_DIGEST_MISMATCH")
    if actual!=digest_txt: failures.append("DIGEST_TXT_MISMATCH")
    if frozen.get("frozen") is not True: failures.append("FROZEN_FLAG_NOT_TRUE")

    readiness=load(c/"READINESS.json")
    graph=load(c/"ECOSYSTEM_GRAPH.json")
    bindings=load(c/"CAPABILITY_BINDINGS.json")
    lanes=load(c/"LANE_EVIDENCE.json").get("lanes",{})
    core=load(c/"CORE_SELFTEST.json")
    prov=load(c/"PROVENANCE.json")
    claims=load(c/"CLAIMS.json")
    evidx=load(c/"EVIDENCE_INDEX.json")
    security=load(c/"SECURITY_PRIVACY.json")
    risk=load(c/"RISK_REGISTER.json")
    nonreg=load(c/"NON_REGRESSION.json")
    rollback=load(c/"ROLLBACK_PROOF.json")
    monitoring=load(c/"MONITORING_PROFILE.json")
    repro=load(c/"REPRODUCIBILITY.json")
    assurance=load(c/"ASSURANCE_CASE.json")

    c25=(claims.get("all_acceptance_predicates_pass") is True and bool(claims.get("scope"))
         and len(claims.get("claims",[]))>=1 and all(x.get("result")=="PASS" for x in claims.get("claims",[])))
    if not c25: failures.append("PUAC_C25_SCOPE_OR_CLAIMS")

    ev_fail=[]
    for item in evidx.get("items",[]):
        p=c/item.get("path","")
        if not p.is_file():
            ev_fail.append({"path":item.get("path"),"reason":"MISSING"})
            continue
        got=sha256_file(p)
        if got!=item.get("sha256"):
            ev_fail.append({"path":item.get("path"),"reason":"SHA256_MISMATCH","actual":got,"expected":item.get("sha256")})
    c26=(not ev_fail and bool(assurance.get("claim_ids")) and bool(assurance.get("evidence_paths")))
    if not c26: failures.append("PUAC_C26_EVIDENCE")

    evaluator_identity=f"GITHUB_ACTIONS_G23_ISOLATED_V1@{q.evaluator_commit}:run:{q.evaluator_run_id}"
    producer_identity=f"GITHUB_ACTIONS_R4_PRODUCER@{PRODUCER_HEAD_SHA}:run:{PRODUCER_RUN_ID}"
    distinct=(q.evaluator_commit!=PRODUCER_HEAD_SHA and evaluator_identity!=producer_identity)
    token_absent=("GITHUB_TOKEN" not in os.environ and "GH_TOKEN" not in os.environ)
    c27=(distinct and write_denied and token_absent and assurance.get("g23_repair_allowed") is False and actual==EXPECTED_DIGEST)
    if not c27: failures.append("PUAC_C27_STRUCTURAL_INDEPENDENCE")

    c28=(security.get("status")=="PASS" and risk.get("uncontrolled_critical_risks")==0)
    if not c28: failures.append("PUAC_C28_SECURITY_RISK")

    c29=(actual==EXPECTED_DIGEST and repro.get("status")=="PASS" and frozen.get("frozen") is True)
    if not c29: failures.append("PUAC_C29_INTEGRITY_REPRODUCIBILITY")

    pass_lanes={k for k,v in lanes.items() if isinstance(v,dict) and v.get("status")=="PASS"}
    c30=(nonreg.get("status")=="PASS" and readiness.get("status")=="PASS"
         and readiness.get("custosz72_exact")==72 and readiness.get("g16_precheck")=="PASS"
         and graph.get("capability_count")==59 and bindings.get("count")==59
         and core.get("status")=="PASS" and REQUIRED_LANES.issubset(pass_lanes))
    if not c30: failures.append("PUAC_C30_NON_REGRESSION")

    c31=(rollback.get("status")=="PASS" and rollback.get("checkpoint_sha256")==rollback.get("restored_sha256"))
    if not c31: failures.append("PUAC_C31_ROLLBACK")

    c32=(monitoring.get("status")=="PASS" and monitoring.get("automatic_certification_propagation") is False)
    if not c32: failures.append("PUAC_C32_MONITORING")

    controls={
      "PUAC.C25":{"status":"PASS" if c25 else "FAIL","control":"SCOPE_AND_CLAIMS"},
      "PUAC.C26":{"status":"PASS" if c26 else "FAIL","control":"EVIDENCE_AND_ARGUMENTATION","evidence_failures":ev_fail},
      "PUAC.C27":{"status":"PASS" if c27 else "FAIL","control":"STRUCTURAL_INDEPENDENCE"},
      "PUAC.C28":{"status":"PASS" if c28 else "FAIL","control":"SECURITY_AND_RISK"},
      "PUAC.C29":{"status":"PASS" if c29 else "FAIL","control":"INTEGRITY_AND_REPRODUCIBILITY"},
      "PUAC.C30":{"status":"PASS" if c30 else "FAIL","control":"INTEGRATION_AND_NON_REGRESSION"},
      "PUAC.C31":{"status":"PASS" if c31 else "FAIL","control":"DEMONSTRATED_REVERSIBILITY"},
      "PUAC.C32":{"status":"PASS" if c32 else "FAIL","control":"VALIDITY_AND_REEVALUATION"}
    }

    independence={
      "schema":"PUAC2_C27_INDEPENDENCE_EVIDENCE/1.0",
      "status":"PASS" if c27 else "FAIL",
      "candidate_digest_sha256":actual,
      "producer_identity":producer_identity,
      "evaluator_identity":evaluator_identity,
      "distinct_evaluator_identity":distinct,
      "producer_evaluator_role_separation":distinct,
      "write_access_to_candidate":False if write_denied else True,
      "repair_allowed":False,
      "github_token_present_in_evaluator_process":not token_absent,
      "candidate_mount_effectively_read_only":write_denied,
      "validator_commit_sha":q.evaluator_commit,
      "workflow_ref":q.workflow_ref,
      "candidate_source_run_id":PRODUCER_RUN_ID,
      "candidate_source_head_sha":PRODUCER_HEAD_SHA,
      "common_repository_administrator":True,
      "conflict_of_interest_declared":True,
      "assurance_profile":"INTERNAL_STRUCTURAL_INDEPENDENCE_SAME_REPOSITORY_V1",
      "residual_limitation":"Common repository administration remains a governance-level dependency. The executed evaluator is nevertheless bound to immutable producer/evaluator commits, has no candidate write/repair path, and receives no repository credential in the evaluator process. Scope is internal assurance, not external regulatory certification.",
      "network_calls_by_validator_code":False,
      "evaluated_utc":utc()
    }
    write(out/"C27_INDEPENDENCE_EVIDENCE.json",independence)

    puac_status="PASS" if all(x["status"]=="PASS" for x in controls.values()) else "FAIL"
    puac={"schema":"PUAC2_C25_C32_INDEPENDENT_EVALUATION/1.0","status":puac_status,
          "candidate_digest_sha256":actual,"controls":controls,"certification_ready":puac_status=="PASS",
          "g23_allowed":puac_status=="PASS","authority":"Louksna.md","automatic_promotion":False}
    write(out/"PUAC2_INDEPENDENT_EVALUATION.json",puac)

    g23_status="PASS" if puac_status=="PASS" and not failures else "FAIL"
    g23={"schema":"G23_INDEPENDENT_VALIDATION/2.0","status":g23_status,
         "candidate_digest_sha256":actual,"frozen_digest_sha256":frozen.get("candidate_digest_sha256"),
         "producer_identity":producer_identity,"evaluator_identity":evaluator_identity,
         "repair_allowed":False,"write_access_to_candidate":False if write_denied else True,
         "validator_commit_sha":q.evaluator_commit,"workflow_ref":q.workflow_ref,
         "candidate_source_run_id":PRODUCER_RUN_ID,
         "validation_mode":"IMMUTABLE_ARTIFACT_READ_ONLY_CREDENTIAL_FREE_RECOMPUTE",
         "puac2_status":puac_status,"failures":failures,"g24_authorized":g23_status=="PASS",
         "scope":"METACOGNITIVE_OPERATIONAL_ECOSYSTEM_V1_CONTROL_PLANE_AND_CLOUD_EXECUTION_FRAMEWORK",
         "scope_exclusions":assurance.get("scope_exclusions",[]),"validated_utc":utc()}
    write(out/"G23_RECORD.json",g23)
    write(out/"G23_FILE_MANIFEST.json",{"candidate_digest_sha256":actual,"candidate_files":rows,"validator_commit_sha":q.evaluator_commit})
    print(json.dumps({"status":g23_status,"candidate_digest_sha256":actual,"puac2_status":puac_status,"c27":controls["PUAC.C27"]["status"],"failures":failures},sort_keys=True))
    raise SystemExit(0 if g23_status=="PASS" else 3)

if __name__=="__main__": main()
