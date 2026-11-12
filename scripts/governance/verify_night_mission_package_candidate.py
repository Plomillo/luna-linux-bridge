#!/usr/bin/env python3
"""Static, fail-closed verifier for the inert SYMPHYLAX R1 night mission package.

This verifier NEVER dispatches a runner, never authenticates a user, never installs,
never calls subprocess, never opens network connections and never writes host state.
A PASS only means the candidate JSON obeys the declared static invariants.
"""
from __future__ import annotations
import argparse
import copy
import json
from pathlib import Path
import sys

SCHEMA = "SYMPHYLAX_R1_R4_NIGHT_MISSION_PACKAGE_CANDIDATE_V1"
FORBIDDEN = {
    "DELETE_WINDOWS_11","FORMAT","REPARTITION","GPT_MUTATION","EFI_MUTATION",
    "PROYECTOS_MIGRATION","DELETE_UNRELATED_USER_DATA","UNATTENDED_REBOOT",
    "DISABLE_SECURITY_CONTROLS","EXPOSE_BITLOCKER_OR_OTHER_SECRETS",
}
EXPECTED_LOTS = {f"L{i:02d}" for i in range(12)}
MAX_BYTES = 256 * 1024

class Denied(Exception):
    pass

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise Denied(msg)

def load(path: Path) -> dict:
    require(path.is_file() and not path.is_symlink(), "INVALID_PACKAGE_FILE")
    require(path.stat().st_size <= MAX_BYTES, "PACKAGE_TOO_LARGE")
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), "ROOT_NOT_OBJECT")
    return value

def validate_dag(lots: list[dict]) -> None:
    ids = {x.get("id") for x in lots}
    require(ids == EXPECTED_LOTS, "LOT_SET_MISMATCH")
    graph = {}
    for lot in lots:
        lid = lot.get("id")
        deps = lot.get("depends_on")
        require(isinstance(deps, list), f"DEP_LIST_MISSING:{lid}")
        require(all(d in ids for d in deps), f"UNKNOWN_DEP:{lid}")
        require(lid not in deps, f"SELF_DEP:{lid}")
        graph[lid] = deps
    state: dict[str, int] = {}
    def visit(node: str) -> None:
        if state.get(node) == 1:
            raise Denied("DAG_CYCLE")
        if state.get(node) == 2:
            return
        state[node] = 1
        for dep in graph[node]:
            visit(dep)
        state[node] = 2
    for node in graph:
        visit(node)

def validate(pkg: dict) -> dict:
    require(pkg.get("schema_id") == SCHEMA, "SCHEMA_MISMATCH")
    require(pkg.get("type") == "DECLARATIVE_PREAUTHORIZATION_MISSION_PACKAGE_NOT_EXECUTABLE", "EXECUTABLE_TYPE_FORBIDDEN")
    require(pkg.get("state") == "DESIGN_PACKAGE_MATERIALIZED_INERT", "STATE_NOT_INERT")
    require(pkg.get("canonical_authority") == "Louksna.md", "AUTHORITY_DRIFT")
    require(pkg.get("scope") == "R4_REVERSIBLE_NON_DESTRUCTIVE_INSTALLATION_ONLY", "SCOPE_DRIFT")
    require(pkg.get("f3_disk_scope") == "EXCLUDED_AND_SEPARATELY_AUTHORIZED", "F3_DISK_SCOPE_COLLISION")
    for k in ("user_authorized","automation_armed","dispatch_enabled","live_server_ready","certified_for_host_scope"):
        require(pkg.get(k) is False, "MUST_REMAIN_FALSE:" + k)

    pins = pkg.get("pinned_inputs")
    require(isinstance(pins, dict), "PINNED_INPUTS_MISSING")
    for k in ("A0","A1","PUAC2","SKELETON_R4","CAS_MANIFEST","SYMPHYLAX_INVENTORY","F2_RESEARCH","F2_2_HANDOFF","INERT_LOCK"):
        require(k in pins, "PIN_MISSING:" + k)
    for k in ("A0","A1","PUAC2","SKELETON_R4","CAS_MANIFEST"):
        require(bool(pins[k].get("git_blob_sha")), "BLOB_PIN_MISSING:" + k)
    require(pins["A0"].get("role") == "CANONICAL_AUTHORITY", "A0_ROLE_DRIFT")
    require(pins["A1"].get("role") == "DERIVATIVE_REFERENCE_NOT_AUTHORITY", "A1_AUTHORITY_ESCALATION")

    auth = pkg.get("authorization_contract")
    require(isinstance(auth, dict), "AUTH_CONTRACT_MISSING")
    require(auth.get("trusted_adapter_status") == "ABSENT_OR_UNVERIFIED", "UNPROVEN_AUTH_ADAPTER")
    require(auth.get("literal_keyword_alone_is_authorization") is False, "KEYWORD_AUTH_FORBIDDEN")
    require(auth.get("single_use") is True, "NON_SINGLE_USE_AUTH")
    require(auth.get("replay_protection_required") is True, "REPLAY_PROTECTION_MISSING")
    require(auth.get("general_authorization_may_include_f3_disk") is False, "GENERAL_AUTH_COVERS_DISK")
    require(auth.get("f3_disk_requires_second_separate_authorization") is True, "SECOND_DISK_AUTH_MISSING")
    require(int(auth.get("nonce_bits_min", 0)) >= 256, "NONCE_TOO_WEAK")
    require(0 < int(auth.get("max_authorization_ttl_minutes", 0)) <= 15, "AUTH_TTL_OUT_OF_BOUNDS")

    forb = set(pkg.get("forbidden_operations", []))
    require(FORBIDDEN.issubset(forb), "FORBIDDEN_OPERATION_REMOVED")

    lots = pkg.get("lots")
    require(isinstance(lots, list), "LOTS_MISSING")
    validate_dag(lots)
    for lot in lots:
        require(lot.get("destructive") is False, "DESTRUCTIVE_LOT:" + str(lot.get("id")))
        require(lot.get("status") in {"BLOCKED_NO_AUTHORIZATION","NOT_EXECUTED"}, "UNEXECUTED_STATUS_DRIFT:" + str(lot.get("id")))
    l00 = next(x for x in lots if x["id"] == "L00")
    require(l00["status"] == "BLOCKED_NO_AUTHORIZATION", "AUTH_GATE_NOT_BLOCKED")
    require(l00["mode"] == "GATE_ONLY", "AUTH_GATE_MODE_DRIFT")

    gates = pkg.get("gates", {})
    require(gates.get("sandbox_T01_T20") == "NOT_EXECUTED", "FAKE_SANDBOX_PASS")
    require(gates.get("authorization_adapter_review") == "HOLD", "AUTH_REVIEW_NOT_HOLD")
    require(gates.get("G23_design_independent") == "HOLD", "FAKE_G23")
    require(gates.get("G24_design_decision") == "HOLD", "FAKE_G24")
    require(gates.get("owner_authorization") == "NOT_RECEIVED", "FALSE_OWNER_AUTH")
    require(gates.get("f3_disk") == "DENIED", "F3_DISK_NOT_DENIED")

    release = pkg.get("release_state", {})
    require(release.get("design_capsule_materialized") is True, "DESIGN_CAPSULE_NOT_MATERIALIZED")
    for k in ("static_validation_pass","sandbox_validated","independently_validated","certified","server_ready_waiting_for_authorizo","execution_permitted"):
        require(release.get(k) is False, "FALSE_READINESS:" + k)

    resource = pkg.get("resource_policy", {})
    require(resource.get("unattended_reboot") is False, "UNATTENDED_REBOOT_ALLOWED")
    require(resource.get("deadline_prediction") == "FORBIDDEN_UNTIL_SANDBOX_DURATION_BENCHMARKS", "UNMEASURED_DEADLINE_CLAIM")
    require(int(resource.get("heavy_parallelism_max", 0)) == 1, "HEAVY_PARALLELISM_DRIFT")

    return {
        "result":"STATIC_MISSION_PACKAGE_VALID",
        "execution_permitted":False,
        "lots_declared":len(lots),
        "lots_executed":0,
        "g23":"HOLD","g24":"HOLD",
        "server_ready":False,
        "message":"Design/package consistency only; not operational certification."
    }

def self_test(src: dict) -> int:
    validate(src)
    tests = []
    def denied(mutator, label):
        x = copy.deepcopy(src)
        mutator(x)
        try:
            validate(x)
        except Denied:
            tests.append(label)
            return
        raise AssertionError("UNSAFE_ACCEPT:" + label)
    denied(lambda x: x.__setitem__("user_authorized", True), "FAKE_AUTH")
    denied(lambda x: x.__setitem__("dispatch_enabled", True), "FAKE_DISPATCH")
    denied(lambda x: x.__setitem__("live_server_ready", True), "FAKE_SERVER_READY")
    denied(lambda x: x["release_state"].__setitem__("certified", True), "FAKE_CERTIFIED")
    denied(lambda x: x["gates"].__setitem__("G23_design_independent", "PASS"), "FAKE_G23")
    denied(lambda x: x["gates"].__setitem__("G24_design_decision", "PASS"), "FAKE_G24")
    denied(lambda x: x["gates"].__setitem__("f3_disk", "ALLOWED"), "DISK_SCOPE_ESCALATION")
    denied(lambda x: x["forbidden_operations"].remove("FORMAT"), "FORMAT_GUARD_REMOVED")
    denied(lambda x: x["authorization_contract"].__setitem__("literal_keyword_alone_is_authorization", True), "KEYWORD_AUTH")
    denied(lambda x: x["authorization_contract"].__setitem__("nonce_bits_min", 64), "WEAK_NONCE")
    denied(lambda x: x["lots"][4].__setitem__("destructive", True), "DESTRUCTIVE_LOT")
    denied(lambda x: x["lots"][1]["depends_on"].append("L11"), "DAG_CYCLE")
    return len(tests)

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", required=True, type=Path)
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()
    try:
        pkg = load(args.package)
        result = validate(pkg)
        if args.self_test:
            result["negative_self_tests_pass"] = self_test(pkg)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Denied, ValueError, OSError, TypeError, AttributeError, AssertionError) as exc:
        print(json.dumps({"result":"DENIED","reason":str(exc),"execution_permitted":False}, sort_keys=True), file=sys.stderr)
        return 2

if __name__ == "__main__":
    raise SystemExit(main())
