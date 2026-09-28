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

def capability_inventory(status):
    text = status.get("stdout", "").strip()
    try:
        obj = json.loads(text.splitlines()[-1])
    except Exception:
        return {"dedup_evidence_available": False, "capabilities": [], "reason": "V07_STATUS_NOT_MACHINE_PARSEABLE"}
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
        "reason": None if found else "NO_CAPABILITY_LIST_IN_STATUS",
    }

def adapter_match(registry, native, root):
    required = set(native["mission_payload"].get("required_capabilities_explicit", []))
    hints = set(native["mission_payload"].get("routing_hints", {}).get("values", []))
    allowed_root = (root / registry["policy"]["allowed_root"]).resolve()
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
        adapter_caps = set(adapter.get("required_capabilities", []))
        if not adapter_caps.issubset(required):
            reasons.append("CAPABILITY_MISMATCH")
        backend = adapter.get("backend")
        if backend and hints and backend not in hints:
            reasons.append("BACKEND_MISMATCH")
        if reasons:
            rejected.append({"adapter_id": adapter.get("adapter_id"), "reasons": reasons})
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
    inventory = capability_inventory(status)
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
    matches, rejected = adapter_match(registry, native, root) if executor_bound and runtime_ok else ([], [])
    adapter = matches[0] if len(matches) == 1 else None

    if not runtime_ok:
        blocker = "CUSTOSZ_RUNTIME_SELFTEST_FAILED"
        gate = "RUNTIME_COMPATIBILITY"
        observed = "Runtime selftest != PASS"
        remediation = "Repair the staged Runtime through the governed provenance chain and rerun."
    elif not executor_bound:
        blocker = "CUSTOSZ_EXECUTOR_UNBOUND"
        gate = "EXECUTOR_BINDING"
        observed = "executor_reported=" + str(executor)
        remediation = "Bind a governed executor in CUSTOSZ/Runtime for this mission class; do not substitute Desktop or an implicit shell."
    elif adapter is None:
        blocker = "NO_UNIQUE_PINNED_RUNTIME_ADAPTER"
        gate = "RUNTIME_ADAPTER"
        observed = "matching_adapters=" + str(len(matches))
        remediation = "Add one reviewed SHA-256-pinned adapter under scripts/mission_mailbox/adapters and register it without changing the source mission."
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
        "adapter_selected": adapter,
        "adapter_rejections": rejected,
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

    plan = {
        "schema": "CUSTOSZ_EXECUTION_PLAN/1.0",
        "mail_id": native["mail_id"],
        "custosz_mission_id": mission["mission_id"],
        "adapter": adapter,
        "status": "ROUTED_READY_NOT_YET_EXECUTED",
        "rule": "Material execution must occur only through the pinned Runtime adapter and produce terminal evidence.",
    }
    atomic_json(out / "EXECUTION_PLAN.json", plan)
    history.append({"utc": utc(), "state": "RUNTIME_COMPATIBLE"})
    history.append({"utc": utc(), "state": "EXECUTOR_BOUND"})
    final_state = {
        **prior_state,
        "workflow_technical_status": "PASS",
        "mission_terminal_status": None,
        "current_state": "EXECUTOR_BOUND",
        "current_gate": "MATERIAL_EXECUTION",
        "root_blocker": None,
        "history": history,
    }
    atomic_json(out / "MISSION_STATE.json", final_state)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
