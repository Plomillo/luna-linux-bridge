#!/usr/bin/env python3
"""Fail-closed STATIC verifier for a proposed, INERT SYMPHYLAX mission lock.

This program has NO execution path for host installation, backup, partitioning,
authorization, credential acquisition, SSH, subprocesses or runner dispatch.
Passing its checks is NOT G23, G24 or operational readiness.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys

EXPECTED_SCHEMA = "SYMPHYLAX_R1_NIGHT_MISSION_LOCK_CANDIDATE_V1"
EXPECTED_TESTS = {"T" + str(n).zfill(2) for n in range(1, 21)}
FORBIDDEN_DESTRUCTIVE = {
    "DELETE_WINDOWS_11", "FORMAT", "REPARTITION", "EFI_MUTATION",
    "PROYECTOS_MIGRATION", "MOUNT_UNTRUSTED_DEVICE_RW",
    "DELETE_UNRELATED_USER_DATA", "REBOOT_UNATTENDED",
}
SOURCE_MAX_BYTES = 131072

class Denied(Exception):
    """The declared contract did not satisfy a mandatory static invariant."""

def require(condition: bool, reason: str) -> None:
    if not condition:
        raise Denied(reason)

def validate_inert_contract(record: object) -> dict:
    require(isinstance(record, dict), "ROOT_NOT_OBJECT")
    require(record.get("schema_id") == EXPECTED_SCHEMA, "UNKNOWN_SCHEMA")
    require(record.get("type") == "DECLARATIVE_CONTRACT_ONLY_NOT_WIRED_TO_LIVE_SERVER", "FALSE_EXECUTABLE_TYPE")
    require(record.get("state") == "PREPARATION_INERT", "STATE_NOT_INERT")
    require(record.get("canonical_authority") == "Louksna.md", "AUTHORITY_DRIFT")
    require(record.get("scope") == "R4_REVERSIBLE_NON_DESTRUCTIVE_INSTALLATION_ONLY", "SCOPE_CHANGED")
    for key in ("user_authorized", "automation_armed",
                "server_operations_authorized", "github_workflow_dispatch_enabled",
                "live_server_capability_certified"):
        require(record.get(key) is False, "MUST_REMAIN_FALSE:" + key)

    auth = record.get("authorization_binding")
    require(isinstance(auth, dict), "AUTH_BINDING_MISSING")
    for key in ("principal_identity_verified", "authorization_record_verified"):
        require(auth.get(key) is False, "AUTH_FALSE_POSITIVE:" + key)
    for key in ("mission_id", "manifest_sha256", "approved_git_commit",
                "one_time_nonce", "expires_at_utc"):
        require(auth.get(key) is None, "UNAUTHORIZED_BINDING_PRESENT:" + key)
    require(auth.get("revoked") is False, "REVOCATION_STATE_UNKNOWN")

    policy = record.get("execution_policy")
    require(isinstance(policy, dict), "POLICY_MISSING")
    required_true = (
        "no_automatic_triggers",
        "no_local_runner_jobs_before_authorized_scope",
        "no_install_without_live_g23_g24_when_mandatory",
        "no_privilege_escalation_by_readme_or_issues",
        "require_exact_commit_binding",
        "require_preflight_and_verified_checkpoint",
        "limit_to_one_host_mission",
        "deadline_enforced",
        "fail_closed_on_unknown",
        "no_install_on_plan_or_pr_merge",
        "no_auto_activate_from_research_pass",
        "no_claims_of_zero_data_loss_without_proven_recovery",
    )
    for key in required_true:
        require(policy.get(key) is True, "POLICY_MISSING_OR_WEAKENED:" + key)
    excluded = policy.get("prohibit_operations")
    require(isinstance(excluded, list) and FORBIDDEN_DESTRUCTIVE.issubset(set(excluded)),
            "DESTRUCTIVE_DENYLIST_WEAKENED")

    disk = record.get("destructive_scope")
    require(isinstance(disk, dict) and disk.get("state") == "DENIED", "DISK_GATE_OPEN")
    for key in ("requires_separate_mission", "requires_new_explicit_human_approval",
                "requires_manual_partitioning_per_skeleton_H2",
                "requires_two_independent_verified_backups",
                "requires_restoration_test", "requires_separate_host_scope_G23_G24"):
        require(disk.get(key) is True, "DISK_GATE_WEAK:" + key)

    research = record.get("research_stage")
    require(isinstance(research, dict), "RESEARCH_LEDGER_MISSING")
    require(research.get("source_conformity_independently_validated") is False,
            "UNSUPPORTED_INDEPENDENT_RESEARCH_PASS")
    require(research.get("runtime_use_proven") is False, "UNSUPPORTED_RUNTIME_PASS")
    require(record.get("research_addendum") ==
            "docs/architecture/ADITIVO_F2_EVIDENCIA_COMPARADA_Y_PRUEBAS.md",
            "SOURCE_DOCTRINE_MISSING")

    trials = record.get("test_families")
    require(isinstance(trials, list) and len(trials) == 20, "TEST_COUNT_INVALID")
    ids = [trial.get("test_id") for trial in trials if isinstance(trial, dict)]
    require(set(ids) == EXPECTED_TESTS and len(ids) == len(set(ids)),
            "TEST_IDS_MISSING_OR_DUPLICATE")
    for trial in trials:
        require(trial.get("status") == "NOT_EXECUTED" and
                trial.get("independent_validation") == "HOLD" and
                trial.get("evidence_reference") is None, "FAKE_TEST_PASS")

    ready = record.get("runtime_phase_requirements")
    require(isinstance(ready, dict), "READINESS_STATE_MISSING")
    require(ready.get("preparation_package_ready") is False, "UNPROVEN_PACKAGE_READY")
    require(ready.get("trigger_implementation_validated") is False, "UNPROVEN_TRIGGER_READY")
    require(ready.get("destructive_scope") == "SECOND_SEPARATE_AUTHORIZATION_REQUIRED",
            "AUTH_SCOPE_COLLISION")
    require(record.get("gates", {}).get("owner_explicit_authorization") == "NOT_RECEIVED",
            "OWNER_AUTHORIZATION_NOT_PENDING")
    return {"result": "INERT_STATIC_CONTRACT_VALID", "test_families_declared": 20,
            "tests_executed": 0, "host_executions": 0, "execution_permitted": False,
            "g23_granted": False, "g24_granted": False,
            "message": "Static parser result only, not operational certification."}

def load_contract(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "INVALID_FILE")
    require(path.stat().st_size <= SOURCE_MAX_BYTES, "UNBOUNDED_FILE")
    return json.loads(path.read_text(encoding="utf-8"))

def deny_execution_even_with_keyword(record: dict, supplied_keyword: str) -> None:
    """Deliberately no implementation of auth; the future trusted adapter must be reviewed."""
    raise Denied("NO_TRUSTED_AUTHENTICATION_ADAPTER_INSTALLED")

def self_test(src: dict) -> None:
    validate_inert_contract(src)
    mutation_tests = (
        ("user_authorized", True),
        ("automation_armed", True),
        ("server_operations_authorized", True),
        ("live_server_capability_certified", True),
    )
    cases = 0
    for key, value in mutation_tests:
        m = copy.deepcopy(src)
        m[key] = value
        try:
            validate_inert_contract(m)
            raise AssertionError("UNSAFE_ACCEPT:" + key)
        except Denied:
            cases += 1
    m = copy.deepcopy(src)
    m["execution_policy"]["prohibit_operations"].remove("FORMAT")
    try:
        validate_inert_contract(m)
        raise AssertionError("UNSAFE_ACCEPT:FORMAT_REMOVED")
    except Denied:
        cases += 1
    m = copy.deepcopy(src)
    m["test_families"][0]["status"] = "PASS"
    try:
        validate_inert_contract(m)
        raise AssertionError("UNSAFE_ACCEPT:FAKE_PASS")
    except Denied:
        cases += 1
    m = copy.deepcopy(src)
    m["authorization_binding"]["mission_id"] = "forged"
    try:
        validate_inert_contract(m)
        raise AssertionError("UNSAFE_ACCEPT:FAKE_MISSION")
    except Denied:
        cases += 1
    for keyword in ("AUTORIZO", "AUTO", "autorizo", "AUTORIZO F3-DISK"):
        try:
            deny_execution_even_with_keyword(src, keyword)
            raise AssertionError("UNSAFE_KEYWORD_ACCEPT")
        except Denied:
            cases += 1
    print(json.dumps({"self_tests_pass": cases, "static_contract_check": "PASS",
                      "execution_implemented": False, "g23": "HOLD", "g24": "HOLD"},
                     sort_keys=True))

def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--lock", required=True, type=Path,
                    help="candidate JSON lock (read-only)")
    ap.add_argument("--self-test", action="store_true",
                    help="run negative unit tests without execution capabilities")
    args = ap.parse_args()
    try:
        src = load_contract(args.lock)
        result = validate_inert_contract(src)
        if args.self_test:
            self_test(src)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Denied, ValueError, OSError, TypeError, AttributeError) as e:
        print(json.dumps({"result": "DENIED", "reason": str(e),
                          "execution_permitted": False}, sort_keys=True), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
