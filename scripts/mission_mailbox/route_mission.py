#!/usr/bin/env python3
"""Register a compiled mailbox mission in CUSTOSZ and evaluate Runtime compatibility.

No arbitrary mission text is executed here. Material execution remains fail-closed
until CUSTOSZ reports a bound executor and a reviewed SHA-256-pinned adapter exists.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

def utc():
    return datetime.now(timezone.utc).isoformat()

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def atomic_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, path)

def find_workspace():
    home = Path.home()
    candidates = []
    for parent in (home, home / "Proyectos", home / "PROYECTOS", Path("/mnt"), Path("/media")):
        if not parent.is_dir():
            continue
        candidates.append(parent)
        try:
            candidates.extend(list(parent.iterdir())[:120])
        except OSError:
            pass
    found = []
    for item in candidates:
        try:
            q = item.resolve()
            marker = (q / "1. PROYECTOS PRIORITARIOS").is_dir()
            secondary = (q / "4. PENDIENTES").exists() or (q / "2. CORPUS").exists()
            if marker and secondary and q not in found:
                found.append(q)
        except OSError:
            pass
    if len(found) != 1:
        raise RuntimeError("REAL_WORKSPACE_NOT_UNIQUELY_RESOLVED:" + repr([str(x) for x in found]))
    return found[0]

def worker_cmd(custosz, command):
    proc = subprocess.run(
        [sys.executable, "-B", "-I", str(custosz), command],
        text=True, capture_output=True, timeout=30
    )
    return {"exit_code": proc.returncode, "stdout": proc.stdout[-12000:], "stderr": proc.stderr[-3000:]}

def capability_inventory(status, census_path=None, custosz_sha256=None):
    if census_path:
        census_path = Path(census_path)
        if census_path.is_file():
            try:
                census = json.loads(census_path.read_text(encoding="utf-8"))
                records = census.get("capabilities", [])
                ids = sorted({x.get("capability_id") for x in records if isinstance(x, dict) and x.get("capability_id")})
                if (
                    census.get("capability_count") == 72
                    and census.get("unique_capability_count") == 72
                    and len(ids) == 72
                    and (not custosz_sha256 or census.get("pyz_sha256") == custosz_sha256)
                ):
                    return {
                        "dedup_evidence_available": True,
                        "capabilities": ids,
                        "reason": None,
                        "source": "PINNED_CUSTOSZ72_CENSUS",
                        "census_path": census_path.as_posix(),
                        "custosz_sha256": custosz_sha256,
                    }
            except Exception as exc:
                census_error = type(exc).__name__ + ":" + str(exc)[:300]
            else:
                census_error = "CENSUS_IDENTITY_OR_COUNT_MISMATCH"
        else:
            census_error = "CENSUS_FILE_MISSING"
    else:
        census_error = "CENSUS_PATH_UNCONFIGURED"
    text = status.get("stdout", "").strip()
    try:
        obj = json.loads(text.splitlines()[-1])
    except Exception:
        return {"dedup_evidence_available": False, "capabilities": [], "reason": "V07_STATUS_NOT_MACHINE_PARSEABLE;" + census_error}
    found = set()
    def walk(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if "capab" in key.lower() and isinstance(child, list):
                    found.update(x for x in child if isinstance(x, str))
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)
    walk(obj)
    return {
        "dedup_evidence_available": bool(found),
        "capabilities": sorted(found),
        "reason": None if found else "NO_CAPABILITY_LIST_IN_STATUS;" + census_error,
    }

def mission_directive(native, key):
    entries = native.get("mission_payload", {}).get("directives_observed", {}).get(key, [])
    if not entries:
        return None
    value = entries[0].get("value")
    return str(value).strip() if value is not None else None

def resolve_mission_class(binding_registry, native):
    source_sha256 = native["source"]["sha256"]
    direct = mission_directive(native, "MISSION_CLASS")
    bindings = [
        x for x in binding_registry.get("bindings", [])
        if x.get("source_sha256") == source_sha256
    ] if binding_registry else []
    if len(bindings) > 1:
        return {
            "result": "HOLD",
            "root_blocker": "AMBIGUOUS_SOURCE_CLASS_BINDING",
            "source_sha256": source_sha256,
            "direct_mission_class": direct,
            "matches": bindings,
            "mission_class": None,
            "origin": None,
        }
    bound = bindings[0].get("mission_class") if bindings else None
    if direct and bound and direct != bound:
        return {
            "result": "HOLD",
            "root_blocker": "MISSION_CLASS_SOURCE_BINDING_COLLISION",
            "source_sha256": source_sha256,
            "direct_mission_class": direct,
            "bound_mission_class": bound,
            "matches": bindings,
            "mission_class": None,
            "origin": None,
        }
    effective = direct or bound
    return {
        "result": "PASS" if effective else "UNRESOLVED",
        "root_blocker": None if effective else "MISSION_CLASS_UNRESOLVED",
        "source_sha256": source_sha256,
        "direct_mission_class": direct,
        "bound_mission_class": bound,
        "matches": bindings,
        "mission_class": effective,
        "origin": "MISSION_DIRECTIVE" if direct else ("SOURCE_BOUND_REGISTRY" if bound else None),
    }

def adapter_match(registry, native, root, executor_bound, route_location, mission_class_override=None):
    required = set(native["mission_payload"].get("required_capabilities_explicit", []))
    hints = set(native["mission_payload"].get("routing_hints", {}).get("values", []))
    source_sha256 = native["source"]["sha256"]
    mission_class = mission_class_override or mission_directive(native, "MISSION_CLASS")
    policy = registry.get("policy", {})
    allowed_root = (root / policy["allowed_root"]).resolve()
    allowed_statuses = set(policy.get("allowed_statuses", []))
    allowed_locations = set(policy.get("allowed_execution_locations", []))
    matches = []
    rejected = []

    for adapter in registry.get("adapters", []):
        path = (root / adapter.get("path", "")).resolve()
        reasons = []

        if allowed_root not in path.parents:
            reasons.append("PATH_OUTSIDE_ALLOWED_ROOT")
        if not path.is_file():
            reasons.append("FILE_MISSING")
        elif sha(path) != adapter.get("sha256"):
            reasons.append("SHA256_MISMATCH")

        if policy.get("require_source_sha256", False):
            declared_source = adapter.get("source_sha256")
            if not declared_source:
                reasons.append("SOURCE_SHA256_MISSING")
            elif declared_source != source_sha256:
                reasons.append("SOURCE_SHA256_MISMATCH")

        adapter_classes = set(adapter.get("mission_classes", []))
        if policy.get("require_mission_class", False):
            if not mission_class:
                reasons.append("MISSION_CLASS_MISSING")
            elif mission_class not in adapter_classes:
                reasons.append("MISSION_CLASS_MISMATCH")
        elif adapter_classes and mission_class not in adapter_classes:
            reasons.append("MISSION_CLASS_MISMATCH")

        status = adapter.get("status")
        if allowed_statuses and status not in allowed_statuses:
            reasons.append("STATUS_NOT_EXECUTABLE")

        execution_location = adapter.get("execution_location")
        if allowed_locations and execution_location not in allowed_locations:
            reasons.append("EXECUTION_LOCATION_NOT_ALLOWED")
        if execution_location and route_location and execution_location != route_location:
            reasons.append("EXECUTION_LOCATION_MISMATCH")

        if adapter.get("requires_prebound_executor", False) and not executor_bound:
            reasons.append("PREBOUND_EXECUTOR_REQUIRED")
        if not executor_bound and not adapter.get("provides_executor_binding", False):
            reasons.append("EXECUTOR_UNBOUND_AND_ADAPTER_CANNOT_BIND")

        adapter_caps = set(adapter.get("required_capabilities", []))
        if not adapter_caps.issubset(required):
            reasons.append("CAPABILITY_MISMATCH")

        backend = adapter.get("backend")
        if backend and hints and backend not in hints:
            reasons.append("BACKEND_MISMATCH")

        if not adapter.get("scope"):
            reasons.append("SCOPE_MISSING")

        if reasons:
            rejected.append({"adapter_id": adapter.get("adapter_id"), "reasons": sorted(set(reasons))})
        else:
            matches.append(adapter)

    return matches, rejected
def write_error(out, native, blocker, gate, observed, remediation, evidence):
    mission_id = native.get("declared_mission_id") or "UNDECLARED"
    mail_id = native["mail_id"]
    body = f"""# MISSION ERROR / HOLD

MISSION_ID = {mission_id}
MAIL_ID = {mail_id}
MISSION_STATUS = HOLD

ERROR_ID = {mail_id}-{gate}
ERROR_STATE = TRUE

EXPECTED_STATE = {gate}=PASS
OBSERVED_STATE = {observed}

ROOT_CAUSE = {blocker}
ROOT_CAUSE_CONFIDENCE = C3_VERIFIED

EVIDENCE = {evidence}
SOURCE = CUSTOSZ_MISSION_MAILBOX
RUN_ID = {os.environ.get("GITHUB_RUN_ID", "UNKNOWN")}
SOURCE_COMMIT = {os.environ.get("GITHUB_SHA", "UNKNOWN")}
SOURCE_HASH = {native["source"]["sha256"]}

AFFECTED_GATE = {gate}

EXACT_REMEDIATION = {remediation}

REMEDIATION_PRECONDITIONS = preserve original mission hash and Louksna authority
REMEDIATION_SCOPE = mailbox / CUSTOSZ routing / Runtime adapter layer only unless separately authorized
FORBIDDEN_SIDE_EFFECTS = no canonical mutation; no silent executor substitution; protected scopes remain denied

VERIFICATION_TEST = rerun the same native envelope and require {gate}=PASS
EXPECTED_VERIFICATION_RESULT = PASS

ROLLBACK = revert only the corrective mailbox/adapter change
ROLLBACK_VERIFICATION = original mission SHA-256 remains unchanged

NEXT_ROUTE = CUSTOSZ_ROUTER
NEXT_ACTION = apply exact remediation and rerun compatibility

RESOLVED = FALSE
"""
    (out / "README_ERROR.md").write_text(body, encoding="utf-8")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--compiled", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--policy", default="mission-mailbox/config/mailbox-policy.json")
    args = parser.parse_args()

    root = Path(args.repo_root).resolve()
    compiled = Path(args.compiled).resolve()
    out = Path(args.out).resolve()
    out.mkdir(parents=True, exist_ok=True)

    policy = json.loads((root / args.policy).read_text(encoding="utf-8"))
    registry = json.loads((root / policy["paths"]["adapter_registry"]).read_text(encoding="utf-8"))
    binding_path = policy.get("paths", {}).get("source_class_bindings")
    binding_registry = (
        json.loads((root / binding_path).read_text(encoding="utf-8"))
        if binding_path and (root / binding_path).is_file() else {"bindings": []}
    )
    native = json.loads((compiled / "MISSION_NATIVE.json").read_text(encoding="utf-8"))
    prior_state = json.loads((compiled / "MISSION_STATE.json").read_text(encoding="utf-8"))

    source = base64.b64decode(native["mission_payload"]["source_utf8_b64"])
    if hashlib.sha256(source).hexdigest() != native["source"]["sha256"]:
        raise SystemExit("NATIVE_SOURCE_HASH_MISMATCH")

    custosz = root / policy["paths"]["custosz"]
    runtime = root / policy["paths"]["runtime"]
    metaos = root / policy["paths"]["metaos"]
    authority = root / policy["paths"]["authority"]
    for required in (custosz, runtime, metaos, authority):
        if not required.is_file():
            raise SystemExit("REQUIRED_ARTIFACT_MISSING:" + str(required))

    identities = {
        "CUSTOSZ": sha(custosz),
        "RUNTIME": sha(runtime),
        "METAOS": sha(metaos),
        "AUTHORITY": sha(authority),
    }

    status = worker_cmd(custosz, "v07-status")
    selftest = worker_cmd(custosz, "v07-selftest")
    census_rel = policy.get("paths", {}).get("capability_census")
    census_path = (root / census_rel) if census_rel else None
    inventory = capability_inventory(status, census_path, identities["CUSTOSZ"])
    class_resolution = resolve_mission_class(binding_registry, native)
    atomic_json(out / "MISSION_CLASS_RESOLUTION.json", class_resolution)
    atomic_json(out / "CUSTOSZ_CAPABILITY_INVENTORY.json", inventory)

    if status["exit_code"] != 0 or selftest["exit_code"] != 0:
        compat = {
            "schema": "CUSTOSZ_RUNTIME_COMPATIBILITY/1.0",
            "result": "HOLD",
            "root_blocker": "CUSTOSZ_V7_SELFTEST_OR_STATUS_FAILED",
            "worker_status": status,
            "worker_selftest": selftest,
            "identities": identities,
        }
        atomic_json(out / "RUNTIME_COMPATIBILITY.json", compat)
        write_error(
            out, native, "CUSTOSZ_V7_SELFTEST_OR_STATUS_FAILED", "CUSTOSZ_IDENTITY",
            "v07-status or v07-selftest returned nonzero",
            "Repair CUSTOSZ V7 status/selftest through its governed provenance chain, then rerun.",
            "RUNTIME_COMPATIBILITY.json",
        )
        return 0

    if class_resolution["result"] == "HOLD":
        compat = {
            "schema": "CUSTOSZ_RUNTIME_COMPATIBILITY/1.0",
            "result": "HOLD",
            "root_blocker": class_resolution["root_blocker"],
            "mission_class_resolution": class_resolution,
            "identities": identities,
        }
        atomic_json(out / "RUNTIME_COMPATIBILITY.json", compat)
        write_error(
            out, native, class_resolution["root_blocker"], "MISSION_CLASS",
            "source/directive classification collision or ambiguity",
            "Correct only the explicit source-class binding registry; preserve original mission bytes and source SHA-256.",
            "MISSION_CLASS_RESOLUTION.json",
        )
        return 0

    workspace = find_workspace()
    state_dir = Path.home() / ".local/state/louksna/mission-mailbox" / (
        native["mail_id"] + "-" + os.environ.get("GITHUB_RUN_ID", "manual") + "-" + os.environ.get("GITHUB_RUN_ATTEMPT", "1")
    )
    state_dir.mkdir(parents=True, mode=0o700, exist_ok=False)
    os.environ["CUSTOSZ_WORKSPACE"] = str(workspace)
    os.environ["CUSTOSZ_STATE_DIR"] = str(state_dir)

    sys.path.insert(0, str(custosz))
    import custosz_v05_legacy as worker
    worker.PINS = {k: (v[0].replace(chr(92), "/") if v[0] else None, v[1], v[2], v[3]) for k, v in worker.PINS.items()}
    worker.PROFILES = {k: ([x.replace(chr(92), "/") for x in v[0]], [x.replace(chr(92), "/") for x in v[1]]) for k, v in worker.PROFILES.items()}

    goal = (
        "MISSION_MAILBOX_NATIVE " + native["mail_id"] +
        "; SOURCE_SHA256=" + native["source"]["sha256"] +
        "; AUTHORITY=" + policy["authority"] +
        "; preserve source byte-exact; route through CUSTOSZ; Runtime compatibility required; "
        "no silent executor substitution."
    )
    seconds = min(
        int(native["execution_contract"].get("wallclock_seconds", policy["mission"]["default_wallclock_seconds"])),
        int(policy["mission"]["maximum_wallclock_seconds"]),
    )
    mission = worker.mission_start(seconds / 3600.0, policy["mission"]["default_profile"], goal, report_minutes=1)
    tick = worker.mission_tick(mission["mission_id"])
    executor = mission.get("executor")
    executor_bound = bool(executor) and not str(executor).upper().startswith("UNBOUND")

    routing = {
        "schema": "CUSTOSZ_ROUTING_DECISION/1.0",
        "mail_id": native["mail_id"],
        "custosz_mission_id": mission["mission_id"],
        "registered_utc": utc(),
        "deadline_utc": mission.get("deadline_utc"),
        "heartbeat_state": tick.get("state"),
        "executor_reported": executor,
        "executor_bound": executor_bound,
        "workspace_resolved": True,
        "worker_identity_sha256": identities["CUSTOSZ"],
        "required_capabilities_explicit": native["mission_payload"].get("required_capabilities_explicit", []),
        "routing_hints_non_authoritative": native["mission_payload"].get("routing_hints", {}),
        "mission_class_resolution": class_resolution,
    }
    atomic_json(out / "ROUTING_DECISION.json", routing)

    with tempfile.TemporaryDirectory(prefix="mailbox-runtime-") as temp:
        sys.path.insert(0, str(runtime))
        try:
            from runtime_core import Runtime
            rt = Runtime(Path(temp) / "runtime", authority, sha(authority))
            runtime_selftest = rt.selftest()
        except Exception as exc:
            runtime_selftest = {"status": "FAIL", "exception": type(exc).__name__, "message": str(exc)[:2000]}

    runtime_ok = runtime_selftest.get("status") == "PASS"
    route_location = os.environ.get("ROUTE_EXECUTION_LOCATION", "UNKNOWN")
    matches, rejected = (
        adapter_match(
            registry, native, root, executor_bound, route_location,
            mission_class_override=class_resolution.get("mission_class")
        )
        if runtime_ok else ([], [])
    )
    adapter = matches[0] if len(matches) == 1 else None
    adapter_provides_binding = bool(adapter and adapter.get("provides_executor_binding", False))

    if not runtime_ok:
        blocker = "CUSTOSZ_RUNTIME_SELFTEST_FAILED"
        gate = "RUNTIME_COMPATIBILITY"
        observed = "Runtime selftest != PASS"
        remediation = "Repair the staged Runtime through the governed provenance chain and rerun."
    elif adapter is None:
        blocker = "NO_UNIQUE_PINNED_RUNTIME_ADAPTER"
        gate = "RUNTIME_ADAPTER"
        observed = (
            "executor_bound=" + str(executor_bound) +
            "; matching_adapters=" + str(len(matches)) +
            "; rejected_adapters=" + str(len(rejected))
        )
        remediation = (
            "Register exactly one reviewed SHA-256-pinned adapter for this source SHA-256, "
            "mission class, scope and execution location. If the executor is initially unbound, "
            "the adapter must explicitly declare provides_executor_binding=true."
        )
    else:
        blocker = None
        gate = None
        observed = None
        remediation = None

    compatibility = {
        "schema": "CUSTOSZ_RUNTIME_COMPATIBILITY/1.0",
        "mail_id": native["mail_id"],
        "result": "PASS" if blocker is None else "HOLD",
        "runtime_selftest": runtime_selftest,
        "executor_bound": executor_bound,
        "adapter_provides_binding": adapter_provides_binding,
        "route_execution_location": route_location,
        "adapter_selected": adapter,
        "adapter_rejections": rejected,
        "mission_class_resolution": class_resolution,
        "capability_inventory": inventory,
        "root_blocker": blocker,
        "identities": identities,
        "protected_scopes": policy["protected_scopes"],
    }
    atomic_json(out / "RUNTIME_COMPATIBILITY.json", compatibility)

    gaps = []
    if blocker:
        gaps.append({
            "gap_id": native["mail_id"] + "-" + gate,
            "observed_gap": blocker,
            "evidence": "RUNTIME_COMPATIBILITY.json",
            "dedup_evidence_available": inventory["dedup_evidence_available"],
            "promotion_to_suggestion": False,
            "reason": "Promotion requires evidence of non-duplication against CUSTOSZ capability inventory.",
        })
    atomic_json(out / "CANDIDATE_GAPS.json", {"schema": "CUSTOSZ_CAPABILITY_GAPS/1.0", "items": gaps})

    suggestions = [
        "# CUSTOSZ CAPABILITY SUGGESTIONS",
        "",
        "POLICY = SUGGESTIONS_ONLY",
        "SUPERVISION = FAMILY_9_REQUIRED",
        "IMPLEMENTATION_AUTHORIZED = FALSE",
        "CERTIFICATION_PROPAGATED = FALSE",
        "",
    ]
    if not inventory["dedup_evidence_available"]:
        suggestions += [
            "DEDUPLICATION_EVIDENCE = INSUFFICIENT",
            "SUGGESTIONS_EMITTED = 0",
            "REASON = v07-status did not expose a machine-readable capability inventory sufficient to prove non-duplication.",
            "CANDIDATE_GAPS_RECORDED = CANDIDATE_GAPS.json",
            "",
        ]
    (out / "CAPABILITY_SUGGESTIONS.md").write_text("\n".join(suggestions), encoding="utf-8")

    history = list(prior_state.get("history", []))
    history.append({"utc": utc(), "state": "ROUTED", "custosz_mission_id": mission["mission_id"]})

    if blocker:
        history.append({"utc": utc(), "state": "HOLD", "reason": blocker, "gate": gate})
        final_state = {
            **prior_state,
            "workflow_technical_status": "PASS",
            "mission_terminal_status": "HOLD",
            "current_state": "HOLD",
            "current_gate": gate,
            "root_blocker": blocker,
            "history": history,
        }
        atomic_json(out / "MISSION_STATE.json", final_state)
        write_error(out, native, blocker, gate, observed, remediation, "ROUTING_DECISION.json + RUNTIME_COMPATIBILITY.json")
        return 0

    # Execute only explicitly auto-authorized lightweight route adapters.
    # Heavy work remains outside the auxiliary runner and must continue in the declared cloud plane.
    adapter_execution = None
    if adapter.get("auto_execute_route_adapter", False):
        adapter_out = out / "ADAPTER_EXECUTION.json"
        adapter_cmd = [
            sys.executable, "-B", "-I", str((root / adapter["path"]).resolve()),
            "--repo-root", str(root),
            "--out", str(adapter_out),
        ]
        proc = subprocess.run(adapter_cmd, text=True, capture_output=True, timeout=120)
        if adapter_out.is_file():
            try:
                adapter_execution = json.loads(adapter_out.read_text(encoding="utf-8"))
            except Exception:
                adapter_execution = {
                    "status": "HOLD",
                    "root_blocker": "ADAPTER_OUTPUT_NOT_MACHINE_PARSEABLE",
                }
        else:
            adapter_execution = {
                "status": "HOLD",
                "root_blocker": "ADAPTER_OUTPUT_MISSING",
            }
        adapter_execution["process_exit_code"] = proc.returncode
        adapter_execution["stdout_tail"] = proc.stdout[-4000:]
        adapter_execution["stderr_tail"] = proc.stderr[-2000:]
        atomic_json(out / "ADAPTER_EXECUTION.json", adapter_execution)
        if proc.returncode != 0 or adapter_execution.get("status") != "PASS":
            blocker = adapter_execution.get("root_blocker") or "PINNED_ROUTE_ADAPTER_EXECUTION_FAILED"
            history = list(prior_state.get("history", []))
            history.append({"utc": utc(), "state": "ROUTED", "custosz_mission_id": mission["mission_id"]})
            history.append({"utc": utc(), "state": "RUNTIME_COMPATIBLE"})
            history.append({"utc": utc(), "state": "ADAPTER_SELECTED", "adapter_id": adapter.get("adapter_id")})
            history.append({"utc": utc(), "state": "HOLD", "reason": blocker, "gate": "MATERIAL_EXECUTION"})
            final_state = {
                **prior_state,
                "workflow_technical_status": "PASS",
                "mission_terminal_status": "HOLD",
                "current_state": "HOLD",
                "current_gate": "MATERIAL_EXECUTION",
                "root_blocker": blocker,
                "history": history,
            }
            atomic_json(out / "MISSION_STATE.json", final_state)
            write_error(
                out, native, blocker, "MATERIAL_EXECUTION",
                "Pinned route adapter did not produce PASS",
                "Repair only the pinned adapter or its declared evidence dependencies, repin SHA-256, then rerun.",
                "ADAPTER_EXECUTION.json",
            )
            return 0

    binding_mode = "PREBOUND" if executor_bound else "ADAPTER_PROVIDED_PENDING"
    plan = {
        "schema": "CUSTOSZ_EXECUTION_PLAN/1.1",
        "mail_id": native["mail_id"],
        "custosz_mission_id": mission["mission_id"],
        "adapter": adapter,
        "binding_mode": binding_mode,
        "observed_executor_bound": executor_bound,
        "status": "ROUTED_READY_NOT_YET_EXECUTED",
        "rule": (
            "Material execution must occur only through the pinned Runtime adapter and produce terminal evidence. "
            "Selecting a binding-providing adapter does not itself prove EXECUTOR_BINDING=PASS."
        ),
    }
    if adapter_execution:
        plan["route_adapter_execution"] = {
            "status": adapter_execution.get("status"),
            "next_gate": adapter_execution.get("next_gate"),
            "g16_precheck": adapter_execution.get("g16_precheck"),
        }
        plan["status"] = "ROUTE_ADAPTER_EXECUTED_READY_FOR_CLOUD"
    atomic_json(out / "EXECUTION_PLAN.json", plan)
    history.append({"utc": utc(), "state": "RUNTIME_COMPATIBLE"})
    history.append({"utc": utc(), "state": "ADAPTER_SELECTED", "adapter_id": adapter.get("adapter_id")})
    if adapter_execution:
        history.append({
            "utc": utc(),
            "state": "ROUTE_ADAPTER_EXECUTED",
            "adapter_id": adapter.get("adapter_id"),
            "next_gate": adapter_execution.get("next_gate"),
        })
        current_state = "ROUTE_ADAPTER_EXECUTED"
    elif executor_bound:
        history.append({"utc": utc(), "state": "EXECUTOR_BOUND"})
        current_state = "EXECUTOR_BOUND"
    else:
        history.append({"utc": utc(), "state": "BINDING_PROVIDER_SELECTED", "adapter_id": adapter.get("adapter_id")})
        current_state = "BINDING_PROVIDER_SELECTED"
    final_state = {
        **prior_state,
        "workflow_technical_status": "PASS",
        "mission_terminal_status": None,
        "current_state": current_state,
        "current_gate": ("CLOUD_CORE_MATERIALIZATION" if adapter_execution else "MATERIAL_EXECUTION"),
        "root_blocker": None,
        "history": history,
    }
    atomic_json(out / "MISSION_STATE.json", final_state)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
