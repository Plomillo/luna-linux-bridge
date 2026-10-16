#!/usr/bin/env python3
"""Build a digest-bound CUSTOSZ V8 assurance dossier; never grant G23/G24."""
from __future__ import annotations
import hashlib, json, os, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EV = ROOT / "evidence"
REQUIRED = [
    "custoszv8-selftest.json", "custoszv8-build-report.json",
    "custoszv8-component-checks.json", "custoszv8-runtime-v1-selftest.json",
    "custoszv8-runtime-v1-integration.json",
    "custoszv8-runtime-v1-material-dispatch.json",
    "custoszv8-metaos-component.json", "custoszv8-metaos-execution.json",
    "custoszv8-unit-tests.log", "custoszv8-reproducibility.json",
]
def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()
def load(name):
    v = json.loads((EV / name).read_text(encoding="utf-8"))
    if not isinstance(v, dict):
        raise ValueError(name + ": JSON root is not an object")
    return v
def main():
    EV.mkdir(parents=True, exist_ok=True)
    missing = [name for name in REQUIRED if not (EV / name).is_file()]
    pkg = ROOT / "dist/CUSTOSZV8.pyz"
    if not pkg.is_file():
        missing.append("dist/CUSTOSZV8.pyz")
    commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                            text=True, timeout=10, check=True).stdout.strip()
    declared = os.environ.get("CUSTOSZV8_CANDIDATE_SHA") or os.environ.get("GITHUB_SHA") or commit
    if declared != commit:
        raise SystemExit("candidate commit mismatch: " + declared + " != " + commit)
    out = EV / "custoszv8-assurance-case.json"
    mdout = EV / "custoszv8-assurance-case.md"
    if missing:
        out.write_text(json.dumps({"schema":"custoszv8.assurance-case.v1","status":"HOLD",
            "candidate_commit":commit,"missing_evidence":missing,"g23":"NOT_GRANTED","g24":"NOT_GRANTED"},
            indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return 1

    build = load("custoszv8-build-report.json")
    selftest = load("custoszv8-selftest.json")
    components = load("custoszv8-component-checks.json")
    runtime = load("custoszv8-runtime-v1-selftest.json")
    runtime_integration = load("custoszv8-runtime-v1-integration.json")
    runtime_material_dispatch = load("custoszv8-runtime-v1-material-dispatch.json")
    mb = load("custoszv8-metaos-component.json")
    mx = load("custoszv8-metaos-execution.json")
    repro = load("custoszv8-reproducibility.json")
    testlog = (EV / "custoszv8-unit-tests.log").read_text(encoding="utf-8",errors="replace")
    match = re.search(r"Ran\s+(\d+)\s+tests?",testlog)
    test_count = int(match.group(1)) if match else None
    tests_pass = bool(re.search(r"^\s*OK\s*$",testlog,re.M)) and "FAILED (" not in testlog
    pkg_hash, pkg_size = sha(pkg), pkg.stat().st_size
    cand = mb.get("versioned_candidate",{})
    build_pass = build.get("status") == "PASS_FOR_PACKAGE_BUILD_AND_INTERNAL_SELFTEST"
    selftest_pass = selftest.get("status") == "PASS"
    package_hash_bound = build.get("sha256") == pkg_hash
    repro_pass = repro.get("status") == "PASS" and repro.get("first_sha256") == repro.get("second_sha256") == pkg_hash
    runtime_pass = runtime.get("result") == "PASS_RUNTIME_SELFTEST_ONLY"
    runtime_integration_pass = (
        runtime_integration.get("status") == "PASS_BOUNDED_RUNTIME_V1_INTEGRATION"
        and runtime_integration.get("runtime_observed_sha256") == runtime_integration.get("expected_runtime_sha256")
        and runtime_integration.get("execution_authorized") is False
        and runtime_integration.get("mission_dispatch_enabled") is False
        and runtime_integration.get("g23") == "NOT_GRANTED"
        and runtime_integration.get("g24") == "NOT_GRANTED"
    )
    runtime_material_dispatch_pass = (
        runtime_material_dispatch.get("status") == "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH"
        and runtime_material_dispatch.get("runtime_observed_sha256") == runtime_material_dispatch.get("expected_runtime_sha256")
        and runtime_material_dispatch.get("execution_authorized") is False
        and runtime_material_dispatch.get("production_mission_dispatch") == "NOT_AUTHORIZED"
        and runtime_material_dispatch.get("g23") == "NOT_GRANTED"
        and runtime_material_dispatch.get("g24") == "NOT_GRANTED"
        and runtime_material_dispatch.get("probe", {}).get("material_execution_proven") is True
        and runtime_material_dispatch.get("probe", {}).get("fixture_rollback") == "PASS"
    )
    metaos_build_pass = (
        mb.get("result") == "PASS_VERSIONED_CANDIDATE_BUILT"
        and cand.get("output_sha256") == mx.get("wasm_sha256")
        and cand.get("original_preserved") is True and cand.get("abi_wit_unchanged") is True
    )
    metaos_runtime_pass = (
        mx.get("result") == "PASS_METAOS_BOUNDED_BEHAVIORAL_TEST"
        and mx.get("validated_export_count") == 12
        and mx.get("v8_adapter_invocation_count") == 12
        and mx.get("v8_adapter_invocations_passed") == 12
        and mx.get("production_cli_roundtrip",{}).get("assertion_pass") is True
    )
    component_commit = components.get("candidate_commit") or components.get("source_commit")
    identity = {
        "build_report_package_sha256_matches": package_hash_bound,
        "build_report_commit_matches": build.get("source_commit") == commit,
        "component_report_has_commit_binding": bool(component_commit),
        "component_report_commit_matches": component_commit == commit,
        "runtime_report_commit_matches": runtime.get("candidate_commit") == commit,
        "runtime_integration_report_commit_matches": runtime_integration.get("candidate_commit") == commit,
        "runtime_material_dispatch_report_commit_matches": runtime_material_dispatch.get("candidate_commit") == commit,
        "metaos_build_report_commit_matches": mb.get("candidate_commit") == commit,
        "metaos_behavior_report_commit_matches": mx.get("candidate_commit") == commit,
    }
    tests_subscope = all([build_pass,selftest_pass,tests_pass,test_count is not None,repro_pass,
                          runtime_pass,runtime_integration_pass,runtime_material_dispatch_pass,metaos_build_pass,metaos_runtime_pass,all(identity.values())])
    evidence = {}
    for name in REQUIRED:
        p=EV/name
        evidence["evidence/"+name]={"sha256":sha(p),"size_bytes":p.stat().st_size}
    evidence["dist/CUSTOSZV8.pyz"]={"sha256":pkg_hash,"size_bytes":pkg_size}
    run_id=os.environ.get("GITHUB_RUN_ID")
    repo=os.environ.get("GITHUB_REPOSITORY","Plomillo/luna-linux-bridge")
    run_url=f"https://github.com/{repo}/actions/runs/{run_id}" if run_id else None
    blockers=[
        "G22 global non-regression for the fully integrated system is not demonstrated.",
        "Runtime V1 now has bounded sandbox evidence for selftest, ProcessSupervisor, and an SRExecBoundFME01 material-dispatch fixture with ACK/FME and rollback; canonical Louksna.md binding, production dispatch, and production restore remain unverified.",
        "MetaOS has bounded hostless behavioral evidence for 12 policy exports; full V8/Runtime/MetaOS mission integration is not demonstrated.",
        "Canonical CP-01 through CP-10 sequence is not evidenced for this exact CUSTOSZV8 package digest.",
        "No independent G23 validator identity or favorable independent report bound to this exact digest is registered.",
        "No authorized G24 certifier or signed certification decision exists for this exact digest."
    ]
    case={
        "schema":"custoszv8.assurance-case.v1",
        "observed_at_utc":datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z"),
        "candidate":{"artifact_id":"CUSTOSZV8","version":"8.0.0-candidate","commit_sha":commit,
            "branch":os.environ.get("GITHUB_HEAD_REF") or os.environ.get("GITHUB_REF_NAME"),
            "package_path":"dist/CUSTOSZV8.pyz","package_sha256":pkg_hash,"package_size_bytes":pkg_size,
            "workflow_run_id":run_id,"workflow_run_url":run_url},
        "evidence_chain":{
            "source_commit":"PASS_EXACT_CHECKED_OUT_HEAD",
            "package_build":"PASS" if build_pass and selftest_pass else "FAIL",
            "unit_tests":{"status":"PASS" if tests_pass else "FAIL","count":test_count},
            "reproducible_build":"PASS" if repro_pass else "FAIL",
            "runtime_v1":{"status":"PASS_NARROW_SELFTEST" if runtime_pass else "FAIL",
                "canonical_binding":runtime.get("canonical_binding","NOT_REPORTED"),
                "scope":runtime.get("execution_scope","NOT_REPORTED")},
            "runtime_v1_bounded_integration":{"status":"PASS_BOUNDED_SCOPE" if runtime_integration_pass else "FAIL",
                "runtime_sha256":runtime_integration.get("runtime_observed_sha256"),
                "checkpoint_roundtrip":runtime_integration.get("probe",{}).get("checkpoint_roundtrip",{}).get("status"),
                "process_supervisor":runtime_integration.get("probe",{}).get("process_supervisor",{}).get("status"),
                "canonical_binding":runtime_integration.get("probe",{}).get("canonical_authority_binding"),
                "mission_dispatch":"NOT_PERFORMED"},
            "runtime_v1_material_dispatch":{"status":"PASS_BOUNDED_FIXTURE" if runtime_material_dispatch_pass else "FAIL",
                "runtime_sha256":runtime_material_dispatch.get("runtime_observed_sha256"),
                "result":runtime_material_dispatch.get("probe",{}).get("mission_result"),
                "dispatch_id":runtime_material_dispatch.get("probe",{}).get("dispatch_id"),
                "material_execution_proven":runtime_material_dispatch.get("probe",{}).get("material_execution_proven"),
                "fixture_rollback":runtime_material_dispatch.get("probe",{}).get("fixture_rollback"),
                "canonical_authority_binding":"NOT_TESTED_SYNTHETIC_AUTHORITY_ONLY",
                "production_mission_dispatch":"NOT_AUTHORIZED"},
            "metaos":{"artifact_id":cand.get("artifact_id"),"original_sha256":cand.get("source_sha256"),
                "candidate_sha256":cand.get("output_sha256"),"versioned_build":"PASS" if metaos_build_pass else "FAIL",
                "validated_exports":mx.get("validated_export_count"),"adapter_calls_passed":mx.get("v8_adapter_invocations_passed"),
                "cli_roundtrip":mx.get("production_cli_roundtrip",{}),
                "behavioral_test":"PASS_BOUNDED_SCOPE" if metaos_runtime_pass else "FAIL"},
            "G23":"NOT_GRANTED","G24":"NOT_GRANTED"},
        "consistency_checks":identity,"consistency_checks_pass":all(identity.values()),
        "tested_subscope_status":"PASS" if tests_subscope else "HOLD",
        "CP10_evidence_freeze":"HOLD","G22_global_non_regression":"NOT_DEMONSTRATED",
        "G23":{"status":"NOT_GRANTED","independent_validator_identity":None,"independent_report_sha256":None},
        "G24":{"status":"NOT_GRANTED","certification_authority_identity":None,"decision_signature":None},
        "canonical_admission":"NOT_GRANTED","operational_authorization":"NOT_GRANTED",
        "blockers":blockers,"evidence_inventory":evidence,
        "scope_limitations":[
            "CI success is not independent validation.",
            "Reproducibility does not establish functional completeness.",
            "The Runtime selftest and bounded integration probe use a synthetic authority, explicitly not Louksna.md.",
            "Runtime V1 evidence proves only bounded synthetic-fixture dispatch and file rollback; canonical authority binding, production mission dispatch, and production system restoration remain untested.",
            "MetaOS probes grant no host capabilities and do not dispatch missions.",
            "G23/G24 are not inferred, auto-promoted, or self-issued."
        ],
        "decision":"PASS_FOR_TESTED_SUBSCOPE; HOLD_FOR_CP10_G23_G24_AND_OPERATIONAL_RELEASE"
    }
    out.write_text(json.dumps(case,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=[
        "# CUSTOSZ V8 assurance case","",
        "Candidate commit: "+commit,
        "Package SHA-256: "+pkg_hash,
        "Package size: "+str(pkg_size)+" bytes",
        "Workflow run: "+str(run_url),
        "Tested sub-scope: "+case["tested_subscope_status"],
        "CP-10 evidence freeze: HOLD",
        "G23 independent validation: NOT GRANTED",
        "G24 certification: NOT GRANTED",
        "Operational authorization: NOT GRANTED","",
        "## Demonstrated",
        f"- Unit tests: {test_count}; {'PASS' if tests_pass else 'FAIL'}.",
        f"- Package build and internal selftest: {'PASS' if build_pass and selftest_pass else 'FAIL'}.",
        f"- Reproducible build: {'PASS' if repro_pass else 'FAIL'}.",
        f"- Runtime V1 selftest: {'PASS' if runtime_pass else 'FAIL'} (isolated synthetic-authority fixture).",
        f"- Runtime V1 bounded integration: {'PASS' if runtime_integration_pass else 'FAIL'} (sandbox checkpoint/restore and benign ProcessSupervisor probe only).",
        f"- SRExecBoundFME01 material-dispatch fixture: {'PASS' if runtime_material_dispatch_pass else 'FAIL'} (synthetic authority, temporary effect, ACK/FME, and rollback).",
        f"- MetaOS derived component: {'PASS' if metaos_build_pass else 'FAIL'}; original bytes separately preserved.",
        f"- MetaOS bounded behavioral probes: {'PASS' if metaos_runtime_pass else 'FAIL'}; 12 exports and {mx.get('v8_adapter_invocations_passed')} adapter calls passed.","",
        "## Blocking evidence gaps"
    ]+["- "+x for x in blockers]+["","## Evidence inventory"]
    lines += [f"- {name}: SHA-256 {value['sha256']}, {value['size_bytes']} bytes" for name,value in sorted(evidence.items())]
    lines += ["","This dossier records evidence for the exact candidate. It does not issue or simulate G23/G24."]
    mdout.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps({"dossier_json":str(out.relative_to(ROOT)),"dossier_markdown":str(mdout.relative_to(ROOT)),
        "candidate_commit":commit,"candidate_sha256":pkg_hash,"tested_subscope_status":case["tested_subscope_status"],
        "consistency_checks_pass":case["consistency_checks_pass"],"G23":"NOT_GRANTED","G24":"NOT_GRANTED",
        "decision":case["decision"]},indent=2,sort_keys=True))
    return 0 if tests_subscope else 1
if __name__=="__main__":
    raise SystemExit(main())
