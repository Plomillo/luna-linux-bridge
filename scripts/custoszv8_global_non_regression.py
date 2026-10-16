#!/usr/bin/env python3
"""Trusted, read-only G22 gate for the registered CUSTOSZ V8 compatibility contract."""
from __future__ import annotations
import argparse, hashlib, json, os, re, subprocess, sys, tempfile
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

# Immutable Git object IDs established from the exact V7 compatibility inputs
# present in the candidate source commit audited on 2026-10-16.
V7_BASELINE = {
    "CUSTOSZ.v07.f04_b.pyz": ("41a52141820d6fb91ada9d51a90b25ffb482b8ad", 49379),
    "CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz": ("7268344859a3b2251fb42e71a6f8cab2f702f389", 10376),
    "MANIFEST_STAGING.md": ("da64c835873a0c1b649b5b7129ac9ce7fba6d43a", 1062),
    "MetaOS.wasm": ("86124d95a38264019a3f5260cbe4cca3d9cd9e69", 2442),
}

def utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")

def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()

def locate(root, name):
    found = [p for p in Path(root).rglob(name) if p.is_file()]
    if len(found) != 1:
        raise ValueError(f"{'MISSING' if not found else 'AMBIGUOUS'}:{name}:{len(found)}")
    return found[0]

def load(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_ROOT_NOT_OBJECT:" + str(path))
    return value

def run_cli(package, source, args):
    # Candidate execution occurs only in this isolated G22 job, with no write
    # permissions, no GitHub token, no OIDC token, and no repository secrets.
    clean = {k: v for k, v in os.environ.items()
             if not any(s in k.upper() for s in ("TOKEN", "SECRET", "PASSWORD", "CREDENTIAL"))}
    clean["PYTHONIOENCODING"] = "utf-8"
    result = subprocess.run(
        [sys.executable, str(package), *args],
        cwd=str(source), env=clean, capture_output=True, text=True,
        timeout=25, check=False,
    )
    return {
        "argv": ["python", package.name, *args],
        "exit_code": result.returncode,
        "stdout_sha256": hashlib.sha256(result.stdout.encode("utf-8", "replace")).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode("utf-8", "replace")).hexdigest(),
    }

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--candidate-dir", required=True)
    ap.add_argument("--source-dir", required=True)
    ap.add_argument("--candidate-sha", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    root, source = Path(args.candidate_dir).resolve(), Path(args.source_dir).resolve()
    failures = []
    files = {}
    objects = {}
    for name in REQUIRED:
        try:
            files[name] = locate(root, name)
        except (ValueError, OSError) as exc:
            failures.append(str(exc))
    if files:
        for name in JSON_FILES:
            if name in files:
                try:
                    objects[name] = load(files[name])
                except Exception as exc:
                    failures.append("INVALID_JSON:" + name + ":" + type(exc).__name__)
    try:
        checked_out_sha = subprocess.run(
            ["git", "-C", str(source), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10, check=True
        ).stdout.strip()
    except Exception:
        checked_out_sha = ""
        failures.append("SOURCE_COMMIT_UNAVAILABLE")
    if checked_out_sha != args.candidate_sha:
        failures.append("SOURCE_COMMIT_MISMATCH")

    baseline = []
    for name, (expected_blob, expected_size) in V7_BASELINE.items():
        try:
            path = locate(source / "artifacts/custosz-v7", name)
            blob = subprocess.run(
                ["git", "-C", str(source), "hash-object", str(path)],
                capture_output=True, text=True, timeout=10, check=True
            ).stdout.strip()
            row = {"path": "artifacts/custosz-v7/" + name, "git_blob_sha": blob,
                   "size_bytes": path.stat().st_size, "expected_git_blob_sha": expected_blob,
                   "expected_size_bytes": expected_size}
            baseline.append(row)
            if blob != expected_blob or path.stat().st_size != expected_size:
                failures.append("V7_BASELINE_MUTATION:" + name)
        except Exception as exc:
            failures.append("V7_BASELINE_MISSING_OR_INVALID:" + name + ":" + type(exc).__name__)

    package = files.get("CUSTOSZV8.pyz")
    pkg_sha = sha256(package) if package else ""
    pkg_size = package.stat().st_size if package else 0
    build = objects.get("custoszv8-build-report.json", {})
    selftest = objects.get("custoszv8-selftest.json", {})
    components = objects.get("custoszv8-component-checks.json", {})
    runtime = objects.get("custoszv8-runtime-v1-selftest.json", {})
    integration = objects.get("custoszv8-runtime-v1-integration.json", {})
    dispatch = objects.get("custoszv8-runtime-v1-material-dispatch.json", {})
    mb = objects.get("custoszv8-metaos-component.json", {})
    mx = objects.get("custoszv8-metaos-execution.json", {})
    repro = objects.get("custoszv8-reproducibility.json", {})
    case = objects.get("custoszv8-assurance-case.json", {})
    if build.get("source_commit") != args.candidate_sha: failures.append("BUILD_SOURCE_COMMIT_MISMATCH")
    if build.get("status") != "PASS_FOR_PACKAGE_BUILD_AND_INTERNAL_SELFTEST": failures.append("BUILD_NOT_PASS")
    if build.get("sha256") != pkg_sha or build.get("size_bytes") != pkg_size: failures.append("PACKAGE_HASH_OR_SIZE_MISMATCH")
    if selftest.get("status") != "PASS": failures.append("PACKAGE_SELFTEST_NOT_PASS")
    component_sha = components.get("candidate_commit") or components.get("source_commit")
    if component_sha != args.candidate_sha: failures.append("COMPONENT_REPORT_COMMIT_MISMATCH")
    if runtime.get("candidate_commit") != args.candidate_sha or runtime.get("result") != "PASS_RUNTIME_SELFTEST_ONLY":
        failures.append("RUNTIME_SELFTEST_NOT_PASS_OR_WRONG_COMMIT")
    if integration.get("candidate_commit") != args.candidate_sha or integration.get("status") != "PASS_BOUNDED_RUNTIME_V1_INTEGRATION":
        failures.append("RUNTIME_INTEGRATION_NOT_PASS_OR_WRONG_COMMIT")
    if integration.get("runtime_observed_sha256") != integration.get("expected_runtime_sha256"):
        failures.append("RUNTIME_INTEGRATION_DIGEST_MISMATCH")
    if integration.get("execution_authorized") is not False or integration.get("mission_dispatch_enabled") is not False:
        failures.append("RUNTIME_INTEGRATION_SCOPE_WIDENED")
    if dispatch.get("candidate_commit") != args.candidate_sha or dispatch.get("status") != "PASS_BOUNDED_SR_EXEC_MATERIAL_DISPATCH":
        failures.append("MATERIAL_DISPATCH_NOT_PASS_OR_WRONG_COMMIT")
    if dispatch.get("runtime_observed_sha256") != dispatch.get("expected_runtime_sha256"):
        failures.append("MATERIAL_DISPATCH_DIGEST_MISMATCH")
    if dispatch.get("execution_authorized") is not False or dispatch.get("production_mission_dispatch") != "NOT_AUTHORIZED":
        failures.append("MATERIAL_DISPATCH_SCOPE_WIDENED")
    probe = dispatch.get("probe", {})
    if probe.get("material_execution_proven") is not True or probe.get("fixture_rollback") != "PASS":
        failures.append("MATERIAL_DISPATCH_EXECUTION_OR_ROLLBACK_NOT_PROVEN")
    versioned = mb.get("versioned_candidate", {})
    if mb.get("candidate_commit") != args.candidate_sha or mb.get("result") != "PASS_VERSIONED_CANDIDATE_BUILT":
        failures.append("METAOS_BUILD_NOT_PASS_OR_WRONG_COMMIT")
    if versioned.get("original_preserved") is not True or versioned.get("abi_wit_unchanged") is not True:
        failures.append("METAOS_BASELINE_OR_ABI_MUTATION")
    if versioned.get("output_sha256") != mx.get("wasm_sha256"): failures.append("METAOS_DIGEST_MISMATCH")
    if mx.get("candidate_commit") != args.candidate_sha or mx.get("result") != "PASS_METAOS_BOUNDED_BEHAVIORAL_TEST":
        failures.append("METAOS_BEHAVIORAL_TEST_NOT_PASS_OR_WRONG_COMMIT")
    if mx.get("validated_export_count") != 12 or mx.get("v8_adapter_invocation_count") != 12 or mx.get("v8_adapter_invocations_passed") != 12:
        failures.append("METAOS_ADAPTER_COVERAGE_INCOMPLETE")
    if mx.get("production_cli_roundtrip", {}).get("assertion_pass") is not True:
        failures.append("PRODUCTION_CLI_ROUNDTRIP_NOT_PASS")
    test_log = files.get("custoszv8-unit-tests.log")
    log_text = test_log.read_text(encoding="utf-8", errors="replace") if test_log else ""
    match = re.search(r"Ran\s+(\d+)\s+tests?", log_text)
    if not match or int(match.group(1)) <= 0 or not re.search(r"^\s*OK\s*$", log_text, re.M) or "FAILED (" in log_text:
        failures.append("UNIT_TEST_LOG_NOT_PASS")
    if repro.get("candidate_commit") != args.candidate_sha or repro.get("status") != "PASS":
        failures.append("REPRODUCIBILITY_NOT_PASS_OR_WRONG_COMMIT")
    if repro.get("first_sha256") != pkg_sha or repro.get("second_sha256") != pkg_sha or repro.get("same_source_commit_two_builds") is not True:
        failures.append("REPRODUCIBILITY_DIGEST_MISMATCH")
    # The producer's dossier intentionally does not grant G22: G22 is issued
    # only here, by the trusted workflow after the independent baseline checks.
    if case.get("G22_global_non_regression") != "NOT_DEMONSTRATED":
        failures.append("PRODUCER_DOSSIER_G22_CLAIM_UNEXPECTED")
    if case.get("canonical_admission") != "NOT_GRANTED" or case.get("operational_authorization") != "NOT_GRANTED":
        failures.append("PRODUCER_DOSSIER_AUTHORIZATION_STATE_INVALID")

    cli = []
    if package and not failures:
        commands = [
            ["selftest"],
            ["status"],
            ["inspect-component", "artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"],
            ["inspect-component", "artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"],
            ["inspect-wasm", "artifacts/custosz-v7/MetaOS.wasm"],
        ]
        for argv in commands:
            try:
                result = run_cli(package, source, argv)
                cli.append(result)
                if result["exit_code"] != 0:
                    failures.append("INDEPENDENT_CLI_EXIT_NONZERO:" + " ".join(argv))
            except Exception as exc:
                failures.append("INDEPENDENT_CLI_EXECUTION_ERROR:" + " ".join(argv) + ":" + type(exc).__name__)

    bundle_rows = []
    if len(files) == len(REQUIRED):
        for name in sorted(REQUIRED):
            p = files[name]
            bundle_rows.append({"name": name, "sha256": sha256(p), "size_bytes": p.stat().st_size})
    bundle_digest = hashlib.sha256(json.dumps(bundle_rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    report = {
        "schema": "CUSTOSZV8_G22_GLOBAL_NON_REGRESSION/1.0",
        "issued_at_utc": utc(),
        "status": "PASS" if not failures else "FAIL",
        "gate": "G22",
        "scope": "CUSTOSZV8_REGISTERED_V7_RUNTIME_V1_METAOS_COMPATIBILITY_CONTRACT",
        "scope_limitation": "Covers the pinned V7 assets and the complete registered CI/CLI/Runtime V1/MetaOS contract enumerated here; does not assert untested hardware, network, or production behaviour.",
        "candidate_commit_sha": args.candidate_sha,
        "checked_out_source_commit_sha": checked_out_sha,
        "candidate_package_sha256": pkg_sha,
        "candidate_package_size_bytes": pkg_size,
        "evidence_bundle_sha256": bundle_digest,
        "immutable_v7_baseline": baseline,
        "unit_test_count": int(match.group(1)) if match else None,
        "independent_cli_checks": cli,
        "claims_validated": [
            "V7 compatibility artifacts and manifest match trusted Git object IDs and exact sizes",
            "candidate package, test reports, Runtime V1 and MetaOS reports are bound to the exact source commit and package digest",
            "unit tests and deterministic rebuild report pass",
            "all 12 MetaOS exports are validated through the V8 adapter",
            "independent candidate CLI commands pass for selftest, status, V7 component inspection, Runtime V1 inspection and MetaOS inspection",
            "bounded Runtime V1 dispatch/integration and fixture rollback tests pass without production authorization",
        ] if not failures else [],
        "claims_excluded": [
            "physical Linux hardware behavior not exercised by this workflow",
            "network-facing production behavior",
            "canonical admission and production activation",
            "any function not included in the registered baseline inventory or tests listed in this report",
        ],
        "global_release_status": "HOLD" if failures else "G22_PASS_G23_G24_PENDING",
        "canonical_admission": "NOT_GRANTED",
        "operational_authorization": "NOT_GRANTED",
        "failures": failures,
    }
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    raise SystemExit(0 if not failures else 3)

if __name__ == "__main__":
    main()
