#!/usr/bin/env python3
"""Protected G23/G24 trust root for the registered CUSTOSZ V8 assurance scope.

The candidate artifact is consumed as data only. G23 validates the exact
G22 record and the registered CI/V7/Runtime V1/MetaOS compatibility evidence.
The certificate never authorizes untested hardware/network behavior, production
dispatch, canonical admission, activation, or release.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REQUIRED = (
    "CUSTOSZV8.pyz",
    "custoszv8-selftest.json",
    "custoszv8-build-report.json",
    "custoszv8-component-checks.json",
    "custoszv8-runtime-v1-selftest.json",
    "custoszv8-runtime-v1-integration.json",
    "custoszv8-runtime-v1-material-dispatch.json",
    "custoszv8-metaos-component.json",
    "custoszv8-metaos-execution.json",
    "custoszv8-unit-tests.log",
    "custoszv8-reproducibility.json",
    "custoszv8-assurance-case.json",
)
JSON_FILES = set(REQUIRED) - {"CUSTOSZV8.pyz", "custoszv8-unit-tests.log"}
SCOPE = "CUSTOSZV8_REGISTERED_V7_RUNTIME_V1_METAOS_COMPATIBILITY_CONTRACT"
EXCLUDED_CLAIMS = [
    "Non-regression outside the pinned V7, Runtime V1 and MetaOS contracts validated by G22.",
    "CP-01 through CP-10 as a complete canonical stage sequence.",
    "Canonical Louksna.md authority binding in the production Runtime.",
    "Production mission dispatch or production restore.",
    "Operational release, activation, or authorization.",
    "Physical hardware, network-facing production behavior, or any claim not covered by the registered G22/G23 evidence.",
]


def utc() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path: str | Path, value: dict) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict:
    obj = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(obj, dict):
        raise ValueError(f"{path.name}: JSON root must be an object")
    return obj


def locate(root: Path, name: str) -> Path:
    matches = [p for p in root.rglob(name) if p.is_file()]
    if len(matches) != 1:
        raise ValueError(f"{'MISSING' if not matches else 'AMBIGUOUS'}:{name}:{len(matches)}")
    return matches[0]


def main_candidate_facts(root: Path, candidate_sha: str, producer: dict) -> tuple[dict, list[str]]:
    failures: list[str] = []
    paths: dict[str, Path] = {}
    objects: dict[str, dict] = {}
    for name in REQUIRED:
        try:
            paths[name] = locate(root, name)
        except ValueError as exc:
            failures.append(str(exc))

    if failures:
        return {}, failures

    for name in JSON_FILES:
        try:
            objects[name] = read_json(paths[name])
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            failures.append(f"INVALID_JSON:{name}:{type(exc).__name__}")
    if failures:
        return {}, failures

    package = paths["CUSTOSZV8.pyz"]
    package_sha = sha256_file(package)
    package_size = package.stat().st_size
    build = objects["custoszv8-build-report.json"]
    selftest = objects["custoszv8-selftest.json"]
    components = objects["custoszv8-component-checks.json"]
    runtime = objects["custoszv8-runtime-v1-selftest.json"]
    integration = objects["custoszv8-runtime-v1-integration.json"]
    dispatch = objects["custoszv8-runtime-v1-material-dispatch.json"]
    metaos_build = objects["custoszv8-metaos-component.json"]
    metaos_run = objects["custoszv8-metaos-execution.json"]
    repro = objects["custoszv8-reproducibility.json"]
    case = objects["custoszv8-assurance-case.json"]
    unit_log = paths["custoszv8-unit-tests.log"].read_text(encoding="utf-8", errors="replace")

    if not re.fullmatch(r"[0-9a-f]{40}", candidate_sha):
        failures.append("CANDIDATE_COMMIT_SHA_INVALID")
    if build.get("status") != "PASS_FOR_PACKAGE_BUILD_AND_INTERNAL_SELFTEST":
        failures.append("PACKAGE_BUILD_REPORT_NOT_PASS")
    if build.get("source_commit") != candidate_sha:
        failures.append("BUILD_SOURCE_COMMIT_MISMATCH")
    if build.get("sha256") != package_sha:
        failures.append("BUILD_REPORT_PACKAGE_HASH_MISMATCH")
    if build.get("size_bytes") != package_size:
        failures.append("BUILD_REPORT_PACKAGE_SIZE_MISMATCH")
    if selftest.get("status") != "PASS":
        failures.append("PACKAGE_SELFTEST_NOT_PASS")
    component_commit = components.get("candidate_commit") or components.get("source_commit")
    if component_commit != candidate_sha:
        failures.append("COMPONENT_REPORT_COMMIT_MISMATCH")
    if runtime.get("candidate_commit") != candidate_sha or runtime.get("result") != "PASS_RUNTIME_SELFTEST_ONLY":
        failures.append("RUNTIME_SELFTEST_SCOPE_OR_COMMIT_INVALID")

    if integration.get("candidate_commit") != candidate_sha:
        failures.append("RUNTIME_INTEGRATION_COMMIT_MISMATCH")
    if integration.get("status") != "PASS_BOUNDED_RUNTIME_V1_INTEGRATION":
        failures.append("RUNTIME_BOUNDED_INTEGRATION_NOT_PASS")
    if integration.get("runtime_observed_sha256") != integration.get("expected_runtime_sha256"):
        failures.append("RUNTIME_INTEGRATION_HASH_MISMATCH")
    if integration.get("execution_authorized") is not False or integration.get("mission_dispatch_enabled") is not False:
        failures.append("RUNTIME_INTEGRATION_SCOPE_WIDENED")
    if integration.get("g23") != "NOT_GRANTED" or integration.get("g24") != "NOT_GRANTED":
        failures.append("RUNTIME_INTEGRATION_CERTIFICATION_PROPAGATION")

    if dispatch.get("candidate_commit") != candidate_sha:
        failures.append("MATERIAL_DISPATCH_COMMIT_MISMATCH")
    if dispatch.get("status") != "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH":
        failures.append("MATERIAL_DISPATCH_PROBE_NOT_PASS")
    if dispatch.get("runtime_observed_sha256") != dispatch.get("expected_runtime_sha256"):
        failures.append("MATERIAL_DISPATCH_RUNTIME_HASH_MISMATCH")
    if dispatch.get("execution_authorized") is not False or dispatch.get("production_mission_dispatch") != "NOT_AUTHORIZED":
        failures.append("MATERIAL_DISPATCH_SCOPE_WIDENED")
    if dispatch.get("g23") != "NOT_GRANTED" or dispatch.get("g24") != "NOT_GRANTED":
        failures.append("MATERIAL_DISPATCH_CERTIFICATION_PROPAGATION")
    probe = dispatch.get("probe", {})
    if probe.get("material_execution_proven") is not True or probe.get("fixture_rollback") != "PASS":
        failures.append("MATERIAL_DISPATCH_FIXTURE_OR_ROLLBACK_NOT_PASS")

    if metaos_build.get("candidate_commit") != candidate_sha:
        failures.append("METAOS_BUILD_COMMIT_MISMATCH")
    versioned = metaos_build.get("versioned_candidate", {})
    if metaos_build.get("result") != "PASS_VERSIONED_CANDIDATE_BUILT":
        failures.append("METAOS_CANDIDATE_BUILD_NOT_PASS")
    if versioned.get("output_sha256") != metaos_run.get("wasm_sha256"):
        failures.append("METAOS_WASM_DIGEST_MISMATCH")
    if versioned.get("original_preserved") is not True or versioned.get("abi_wit_unchanged") is not True:
        failures.append("METAOS_PRESERVATION_OR_ABI_INVARIANT_NOT_PASS")
    if metaos_run.get("candidate_commit") != candidate_sha:
        failures.append("METAOS_EXECUTION_COMMIT_MISMATCH")
    if metaos_run.get("result") != "PASS_METAOS_BOUNDED_BEHAVIORAL_TEST":
        failures.append("METAOS_BOUNDED_BEHAVIOR_NOT_PASS")
    if metaos_run.get("validated_export_count") != 12 or metaos_run.get("v8_adapter_invocation_count") != 12:
        failures.append("METAOS_EXPECTED_EXPORT_OR_ADAPTER_COUNT_MISMATCH")
    if metaos_run.get("v8_adapter_invocations_passed") != 12:
        failures.append("METAOS_ADAPTER_VALIDATION_NOT_PASS")
    if metaos_run.get("production_cli_roundtrip", {}).get("assertion_pass") is not True:
        failures.append("METAOS_CLI_ROUNDTRIP_NOT_PASS")

    match = re.search(r"Ran\s+(\d+)\s+tests?", unit_log)
    tests_ok = bool(re.search(r"^\s*OK\s*$", unit_log, re.MULTILINE)) and "FAILED (" not in unit_log
    if match is None or int(match.group(1)) <= 0 or not tests_ok:
        failures.append("UNIT_TEST_LOG_NOT_PASS")
    test_count = int(match.group(1)) if match else None

    if repro.get("candidate_commit") != candidate_sha or repro.get("status") != "PASS":
        failures.append("REPRODUCIBILITY_REPORT_NOT_PASS_OR_COMMIT_MISMATCH")
    if repro.get("first_sha256") != package_sha or repro.get("second_sha256") != package_sha:
        failures.append("REPRODUCIBILITY_HASH_MISMATCH")
    if repro.get("same_source_commit_two_builds") is not True:
        failures.append("REPRODUCIBILITY_TWO_BUILD_INVARIANT_NOT_PASS")

    cand = case.get("candidate", {})
    if cand.get("commit_sha") != candidate_sha:
        failures.append("ASSURANCE_CASE_COMMIT_MISMATCH")
    if cand.get("package_sha256") != package_sha or cand.get("package_size_bytes") != package_size:
        failures.append("ASSURANCE_CASE_PACKAGE_IDENTITY_MISMATCH")
    if case.get("tested_subscope_status") != "PASS" or case.get("consistency_checks_pass") is not True:
        failures.append("ASSURANCE_CASE_TESTED_SUBSCOPE_NOT_PASS")
    if case.get("decision") != "PASS_FOR_TESTED_SUBSCOPE; HOLD_FOR_CP10_G23_G24_AND_OPERATIONAL_RELEASE":
        failures.append("ASSURANCE_CASE_DECISION_UNEXPECTED")
    if case.get("G22_global_non_regression") != "NOT_DEMONSTRATED":
        failures.append("GLOBAL_NON_REGRESSION_STATE_MISMATCH")
    if case.get("CP10_evidence_freeze") != "HOLD":
        failures.append("CP10_HOLD_NOT_PRESERVED")
    if case.get("canonical_admission") != "NOT_GRANTED" or case.get("operational_authorization") != "NOT_GRANTED":
        failures.append("CANONICAL_OR_OPERATIONAL_AUTHORIZATION_STATE_MISMATCH")

    inventory = case.get("evidence_inventory", {})
    if not isinstance(inventory, dict) or not inventory:
        failures.append("ASSURANCE_EVIDENCE_INVENTORY_MISSING")
    else:
        for logical_path, record in inventory.items():
            name = Path(logical_path).name
            if name not in REQUIRED:
                failures.append("UNEXPECTED_INVENTORY_PATH:" + str(logical_path))
                continue
            if name not in paths:
                failures.append("INVENTORY_PATH_NOT_FOUND:" + str(logical_path))
                continue
            p = paths[name]
            if record.get("sha256") != sha256_file(p):
                failures.append("EVIDENCE_HASH_MISMATCH:" + str(logical_path))
            if record.get("size_bytes") != p.stat().st_size:
                failures.append("EVIDENCE_SIZE_MISMATCH:" + str(logical_path))
        for name in REQUIRED:
            if name == "custoszv8-assurance-case.json":
                continue
            if not any(Path(logical).name == name for logical in inventory):
                failures.append("INVENTORY_ENTRY_MISSING:" + name)

    rows = []
    for name in sorted(REQUIRED):
        p = paths[name]
        rows.append({"name": name, "sha256": sha256_file(p), "size_bytes": p.stat().st_size})
    bundle_digest = sha256_bytes(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    facts = {
        "candidate_commit_sha": candidate_sha,
        "candidate_package_path": str(package.relative_to(root)),
        "candidate_package_sha256": package_sha,
        "candidate_package_size_bytes": package_size,
        "evidence_bundle_sha256": bundle_digest,
        "evidence_files": rows,
        "unit_test_count": test_count,
        "producer_run_id": int(producer["run_id"]),
        "producer_run_url": producer["run_url"],
        "producer_workflow_path": producer["workflow_path"],
        "producer_artifact_name": producer["artifact_name"],
        "producer_artifact_id": int(producer["artifact_id"]),
        "producer_artifact_zip_digest": producer["artifact_zip_digest"],
        "candidate_tree_scope": "ARTIFACTS_FROM_EXACT_SUCCESSFUL_PRODUCER_RUN",
    }
    return facts, failures


def g23(args: argparse.Namespace) -> int:
    root = Path(args.candidate_dir).resolve()
    producer = {
        "run_id": os.environ["PRODUCER_RUN_ID"],
        "run_url": os.environ["PRODUCER_RUN_URL"],
        "workflow_path": os.environ["PRODUCER_WORKFLOW_PATH"],
        "artifact_name": os.environ["PRODUCER_ARTIFACT_NAME"],
        "artifact_id": os.environ["PRODUCER_ARTIFACT_ID"],
        "artifact_zip_digest": os.environ["PRODUCER_ARTIFACT_ZIP_DIGEST"],
    }
    facts, failures = main_candidate_facts(root, args.candidate_sha, producer)
    g22_path = Path(args.g22)
    g22 = read_json(g22_path)
    if g22.get("status") != "PASS" or g22.get("gate") != "G22":
        failures.append("G22_GLOBAL_NON_REGRESSION_NOT_PASS")
    if g22.get("candidate_commit_sha") != args.candidate_sha:
        failures.append("G22_SOURCE_COMMIT_MISMATCH")
    if facts and g22.get("candidate_package_sha256") != facts.get("candidate_package_sha256"):
        failures.append("G22_PACKAGE_DIGEST_MISMATCH")
    if facts and g22.get("evidence_bundle_sha256") != facts.get("evidence_bundle_sha256"):
        failures.append("G22_EVIDENCE_BUNDLE_DIGEST_MISMATCH")
    if g22.get("global_release_status") != "G22_PASS_G23_G24_PENDING":
        failures.append("G22_RELEASE_STATE_INVALID")
    independence = read_json(Path(args.independence))
    script_sha = sha256_file(Path(__file__))
    independent = (
        independence.get("status") == "PASS"
        and independence.get("structural_independence") == "PASS"
        and independence.get("write_access_to_candidate") is False
        and independence.get("repair_allowed") is False
        and independence.get("candidate_code_executed") is False
        and independence.get("candidate_artifact_consumed_as_data_only") is True
        and independence.get("candidate_commit_sha") == args.candidate_sha
        and independence.get("validator_trust_root_sha") == os.environ.get("TRUST_ROOT_SHA")
        and independence.get("validator_script_sha256") == script_sha
        and independence.get("producer_run_id") == int(producer["run_id"])
    )
    if not independent:
        failures.append("STRUCTURAL_INDEPENDENCE_EVIDENCE_INVALID")
    report = {
        "schema": "CUSTOSZV8_G23_INDEPENDENT_VALIDATION/1.0",
        "issued_at_utc": utc(),
        "status": "PASS" if not failures else "FAIL",
        "authority": "Louksna.md",
        "scope": SCOPE,
        "candidate_commit_sha": args.candidate_sha,
        "candidate_package_sha256": facts.get("candidate_package_sha256"),
        "evidence_bundle_sha256": facts.get("evidence_bundle_sha256"),
        "validator_identity": "G23::BASE_CONTROLLED_GITHUB_ACTIONS_WORKFLOW",
        "validator_trust_root_sha": os.environ.get("TRUST_ROOT_SHA"),
        "validator_script_sha256": script_sha,
        "producer": {k: facts.get(k) for k in (
            "producer_run_id", "producer_run_url", "producer_workflow_path",
            "producer_artifact_name", "producer_artifact_id", "producer_artifact_zip_digest"
        )},
        "structural_independence": "PASS" if independent else "FAIL",
        "organizational_independence": "NOT_CLAIMED",
        "candidate_code_executed_by_validator": False,
        "candidate_artifact_consumed_as_data_only": True,
        "g22_record_sha256": sha256_file(g22_path),
        "g22_status": g22.get("status"),
        "claims_validated": [
            "G22 global non-regression over the pinned V7, Runtime V1 and MetaOS registered contract",
            "exact source-commit binding",
            "package and evidence integrity",
            "unit-test log and reproducible-build results",
            "bounded Runtime V1 selftest, integration and fixture rollback evidence",
            "bounded MetaOS build and behavioral evidence",
            "Registered G22 contract and CI-tested sub-scope consistency",
        ] if not failures else [],
        "claims_excluded": EXCLUDED_CLAIMS,
        "global_release_status": "HOLD",
        "operational_authorization": "NOT_GRANTED",
        "certification_authorization_for_g24": not failures,
        "candidate_facts": facts,
        "failures": failures,
    }
    write_json(args.out, report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 3


def make_authority(args: argparse.Namespace) -> int:
    """Bind the G24 role to the protected Actions workflow identity.

    The resulting certificate is separately signed using GitHub artifact
    attestations in the workflow. No bearer token is read, printed, or stored.
    """
    root = Path(args.candidate_dir).resolve()
    pkg = locate(root, "CUSTOSZV8.pyz")
    digest = sha256_file(pkg)
    expected_audience = "louksna-custoszv8-g24:" + digest
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    repo_id = os.environ.get("GITHUB_REPOSITORY_ID", "")
    workflow_ref = os.environ.get("TRUSTED_WORKFLOW_REF", "")
    trust_sha = os.environ.get("TRUST_ROOT_SHA", "")
    event = os.environ.get("GITHUB_EVENT_NAME", "")
    run_id = os.environ.get("GITHUB_RUN_ID", "")
    run_attempt = os.environ.get("GITHUB_RUN_ATTEMPT", "")
    if repo != "Plomillo/luna-linux-bridge" or not repo_id.isdigit():
        raise SystemExit("TRUSTED_REPOSITORY_IDENTITY_MISMATCH")
    if not workflow_ref.endswith("/.github/workflows/custoszv8-independent-g22-g23-g24.yml@refs/heads/main"):
        raise SystemExit("TRUSTED_WORKFLOW_REF_MISMATCH")
    if not re.fullmatch(r"[0-9a-f]{40}", trust_sha):
        raise SystemExit("TRUST_ROOT_SHA_INVALID")
    if event not in {"workflow_run", "workflow_dispatch"}:
        raise SystemExit("G24_EVENT_NOT_AUTHORIZED")
    if not run_id.isdigit() or not run_attempt.isdigit():
        raise SystemExit("GITHUB_RUN_IDENTITY_MISSING")

    authority = {
        "schema": "CUSTOSZV8_G24_AUTHORITY_EVIDENCE/1.0",
        "status": "PASS",
        "authority_authenticated": True,
        "authority_id": (
            "LOUKSNA_CUSTOSZV8_G24::repo:" + repo_id + "/" + repo
            + "::workflow:" + workflow_ref
            + "::workflow_sha:" + trust_sha
            + "::run:" + run_id + "." + run_attempt
        ),
        "candidate_commit_sha": args.candidate_sha,
        "candidate_package_sha256": digest,
        "audience": expected_audience,
        "repository": repo,
        "repository_id": repo_id,
        "workflow_ref": workflow_ref,
        "workflow_sha": trust_sha,
        "workflow_run_id": run_id,
        "workflow_run_attempt": run_attempt,
        "event": event,
        "authentication_context": "BASE_CONTROLLED_GITHUB_ACTIONS_WORKFLOW_IDENTITY; SIGNED_ARTIFACT_ATTESTATION_REQUIRED",
        "raw_token_persisted": False,
        "active_authorized": False,
        "operational_authorization": "NOT_GRANTED",
    }
    write_json(args.out, authority)
    print(json.dumps(authority, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


def g24(args: argparse.Namespace) -> int:
    root = Path(args.candidate_dir).resolve()
    package = locate(root, "CUSTOSZV8.pyz")
    digest = sha256_file(package)
    bundle_rows = []
    for name in sorted(REQUIRED):
        p = locate(root, name)
        bundle_rows.append({"name": name, "sha256": sha256_file(p), "size_bytes": p.stat().st_size})
    bundle_digest = sha256_bytes(json.dumps(bundle_rows, sort_keys=True, separators=(",", ":")).encode("utf-8"))
    g23r = read_json(Path(args.g23))
    g22r = read_json(Path(args.g22))
    authority = read_json(Path(args.authority))
    failures = []
    if g22r.get("status") != "PASS" or g22r.get("gate") != "G22":
        failures.append("G22_NOT_PASS")
    if g22r.get("candidate_commit_sha") != args.candidate_sha:
        failures.append("G22_SOURCE_COMMIT_MISMATCH")
    if g22r.get("candidate_package_sha256") != digest:
        failures.append("G22_PACKAGE_DIGEST_MISMATCH")
    if g23r.get("g22_record_sha256") != sha256_file(Path(args.g22)):
        failures.append("G23_G22_RECORD_HASH_MISMATCH")

    if g23r.get("status") != "PASS" or g23r.get("certification_authorization_for_g24") is not True:
        failures.append("G23_NOT_PASS_OR_NOT_AUTHORIZING")
    if g23r.get("scope") != SCOPE:
        failures.append("G23_SCOPE_MISMATCH")
    if g23r.get("candidate_package_sha256") != digest:
        failures.append("G23_PACKAGE_DIGEST_MISMATCH")
    if g23r.get("evidence_bundle_sha256") != bundle_digest:
        failures.append("G23_EVIDENCE_BUNDLE_DIGEST_MISMATCH")
    if g23r.get("candidate_commit_sha") != args.candidate_sha:
        failures.append("G23_SOURCE_COMMIT_MISMATCH")
    if g23r.get("structural_independence") != "PASS":
        failures.append("G23_INDEPENDENCE_NOT_PASS")
    if authority.get("status") != "PASS" or authority.get("authority_authenticated") is not True:
        failures.append("G24_AUTHORITY_NOT_AUTHENTICATED")
    if authority.get("candidate_package_sha256") != digest:
        failures.append("AUTHORITY_PACKAGE_DIGEST_MISMATCH")
    if authority.get("candidate_commit_sha") != args.candidate_sha:
        failures.append("AUTHORITY_SOURCE_COMMIT_MISMATCH")
    if authority.get("repository") != os.environ.get("GITHUB_REPOSITORY"):
        failures.append("AUTHORITY_REPOSITORY_MISMATCH")
    if authority.get("repository_id") != str(os.environ.get("GITHUB_REPOSITORY_ID", "")):
        failures.append("AUTHORITY_REPOSITORY_ID_MISMATCH")
    if authority.get("workflow_ref") != os.environ.get("TRUSTED_WORKFLOW_REF"):
        failures.append("AUTHORITY_WORKFLOW_REF_MISMATCH")
    if authority.get("workflow_sha") != os.environ.get("TRUST_ROOT_SHA"):
        failures.append("AUTHORITY_WORKFLOW_SHA_MISMATCH")
    if authority.get("audience") != "louksna-custoszv8-g24:" + digest:
        failures.append("AUTHORITY_AUDIENCE_MISMATCH")
    if authority.get("raw_token_persisted") is not False:
        failures.append("RAW_TOKEN_PERSISTENCE_POLICY_VIOLATION")

    status = "PASS" if not failures else "FAIL"
    cert = {
        "schema": "CUSTOSZV8_G24_CERTIFICATION/1.0",
        "issued_at_utc": utc(),
        "status": status,
        "epistemic_state": "CERTIFIED_NOT_ACTIVE" if status == "PASS" else "NOT_CERTIFIED",
        "authority": "Louksna.md",
        "certification_authority_id": authority.get("authority_id"),
        "candidate": {
            "artifact_id": "CUSTOSZV8",
            "source_commit_sha": args.candidate_sha,
            "package_path": str(package.relative_to(root)),
            "package_sha256": digest,
            "evidence_bundle_sha256": bundle_digest,
        },
        "g22_record": {
            "status": g22r.get("status"),
            "candidate_commit_sha": g22r.get("candidate_commit_sha"),
            "candidate_package_sha256": g22r.get("candidate_package_sha256"),
            "record_sha256": sha256_file(Path(args.g22)),
        },
        "g23_record": {
            "status": g23r.get("status"),
            "validator_identity": g23r.get("validator_identity"),
            "validator_trust_root_sha": g23r.get("validator_trust_root_sha"),
            "record_sha256": sha256_file(Path(args.g23)),
        },
        "certification_scope": SCOPE,
        "claims_certified": g23r.get("claims_validated", []) if status == "PASS" else [],
        "claims_excluded": EXCLUDED_CLAIMS,
        "organizational_independence": "NOT_CLAIMED",
        "structural_independence": "PASS" if status == "PASS" else "FAIL",
        "external_or_regulatory_certification": False,
        "certification_propagation": False,
        "canonical_admission": "NOT_GRANTED",
        "operational_authorization": "NOT_GRANTED",
        "active_authorized": False,
        "global_release_status": "HOLD",
        "failures": failures,
    }
    write_json(args.out, cert)
    print(json.dumps(cert, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 4


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    g23p = sub.add_parser("g23")
    g23p.add_argument("--candidate-dir", required=True)
    g23p.add_argument("--candidate-sha", required=True)
    g23p.add_argument("--g22", required=True)
    g23p.add_argument("--independence", required=True)
    g23p.add_argument("--out", required=True)
    g23p.set_defaults(func=g23)
    ap = sub.add_parser("make-authority")
    ap.add_argument("--candidate-dir", required=True)
    ap.add_argument("--candidate-sha", required=True)
    ap.add_argument("--out", required=True)
    ap.set_defaults(func=make_authority)
    g24p = sub.add_parser("g24")
    g24p.add_argument("--candidate-dir", required=True)
    g24p.add_argument("--candidate-sha", required=True)
    g24p.add_argument("--g22", required=True)
    g24p.add_argument("--g23", required=True)
    g24p.add_argument("--authority", required=True)
    g24p.add_argument("--out", required=True)
    g24p.set_defaults(func=g24)
    return p


if __name__ == "__main__":
    parsed = parser().parse_args()
    sys.exit(parsed.func(parsed))
