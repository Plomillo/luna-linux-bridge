"""Command-line interface for CUSTOSZV8."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from .core import (
    CapabilityRegistry, EvidenceJournal, GitHubBridge, MissionStateMachine, TranslationEngine,
    V8Error, inspect_wasm, load_resource_json, run_native_readonly, selftest,
    validate_manifest, verify_component, utc_now, MissionWatchdog, RetryController,
    RecoveryCoordinator, ChangeImpactAnalyzer, RuntimeV1Adapter, MetaOSAdapter
)

def emit(value, pretty=True):
    print(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2 if pretty else None))
 
def build_parser():
    p = argparse.ArgumentParser(prog="CUSTOSZV8.pyz", description="Governed CUSTOSZ V8 candidate")
    p.add_argument("--version", action="version", version="CUSTOSZ V8 " + "8.0.0-candidate")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("selftest", help="run deterministic built-in checks")
    sub.add_parser("status", help="show component and certification status")
    sub.add_parser("manifest", help="show embedded build manifest")
    val = sub.add_parser("validate-manifest", help="validate a manifest JSON file")
    val.add_argument("path", type=Path); val.add_argument("--release", action="store_true")
    insp = sub.add_parser("inspect-component", help="hash and statically inspect a ZIPAPP or component")
    insp.add_argument("path", type=Path); insp.add_argument("--expected-sha256")
    wasm = sub.add_parser("inspect-wasm", help="read WASM import/export names without executing it")
    wasm.add_argument("path", type=Path)
    tr = sub.add_parser("translate", help="deterministic phrase translation with uncertainty reporting")
    tr.add_argument("--from", dest="source", choices=["es", "en"], required=True)
    tr.add_argument("--to", dest="target", choices=["es", "en"], required=True)
    choice = tr.add_mutually_exclusive_group(required=True)
    choice.add_argument("--text"); choice.add_argument("--file", type=Path)
    code = sub.add_parser("code-to-english", help="describe Python source statically; never executes it")
    code.add_argument("path", type=Path)
    jv = sub.add_parser("journal-verify", help="verify append-only event chain")
    jv.add_argument("path", type=Path)
    ja = sub.add_parser("journal-append", help="append a governed JSON event")
    ja.add_argument("path", type=Path); ja.add_argument("event_type")
    ja.add_argument("--payload", required=True, help="JSON object"); ja.add_argument("--actor", default="local-user")
    ja.add_argument("--mission-id")
    cap = sub.add_parser("capability-validate", help="check unique ownership records")
    cap.add_argument("path", type=Path)
    native = sub.add_parser("native-readonly", help="explicitly invoke one allowlisted native V7 read-only command")
    native.add_argument("path", type=Path); native.add_argument("native_command", choices=["v07-status", "v07-selftest"])
    native.add_argument("--expected-sha256", required=True); native.add_argument("--authorization-ref", required=True)
    native.add_argument("--timeout", type=float, default=10.0)
    gh = sub.add_parser("github-repo", help="read repository metadata through HTTPS")
    gh.add_argument("owner"); gh.add_argument("repo")
    branch = sub.add_parser("github-branch", help="read branch metadata through HTTPS")
    branch.add_argument("owner"); branch.add_argument("repo"); branch.add_argument("branch")
    runs = sub.add_parser("github-runs", help="read GitHub Actions runs")
    runs.add_argument("owner"); runs.add_argument("repo"); runs.add_argument("--branch")
    dispatch = sub.add_parser("github-dispatch", help="dispatch an authorized workflow")
    dispatch.add_argument("owner"); dispatch.add_argument("repo"); dispatch.add_argument("workflow_id")
    dispatch.add_argument("ref"); dispatch.add_argument("--inputs", default="{}")
    dispatch.add_argument("--authorization-ref", required=True)
    mission = sub.add_parser("mission-validate", help="validate mission envelope preconditions")
    mission.add_argument("path", type=Path)
    wd = sub.add_parser("watchdog-evaluate", help="evaluate finite mission deadline and progress state")
    wd.add_argument("--mission-id", required=True); wd.add_argument("--deadline-utc", required=True)
    wd.add_argument("--last-progress-epoch", type=float, required=True)
    wd.add_argument("--threshold-seconds", type=float, default=60); wd.add_argument("--now-epoch", type=float)
    wd.add_argument("--waiting-on"); wd.add_argument("--resume-condition"); wd.add_argument("--wait-deadline-utc")
    retry = sub.add_parser("retry-decision", help="evaluate bounded idempotency-aware retry policy")
    retry.add_argument("--class", dest="idempotency_class", choices=["READ_ONLY","IDEMPOTENT","NON_IDEMPOTENT","UNKNOWN"], required=True)
    retry.add_argument("--attempts-used", type=int, required=True); retry.add_argument("--max-attempts", type=int, required=True)
    retry.add_argument("--transient", action="store_true"); retry.add_argument("--authorization-ref"); retry.add_argument("--idempotency-key")
    checkpoint = sub.add_parser("checkpoint-verify", help="verify checkpoint bytes without claiming system restoration")
    checkpoint.add_argument("path", type=Path); checkpoint.add_argument("--expected-sha256", required=True)
    impact = sub.add_parser("impact-analyze", help="analyze claim dependencies for a change")
    impact.add_argument("path", type=Path)
    runtime = sub.add_parser("runtime-preflight", help="inspect exact Runtime identity; native call remains blocked until interface is verified")
    runtime.add_argument("path", type=Path); runtime.add_argument("--expected-sha256"); runtime.add_argument("--native-interface-verified", action="store_true")
    metaos = sub.add_parser("metaos-preflight", help="inspect WASM/component metadata without invoking it")
    metaos.add_argument("path", type=Path); metaos.add_argument("--export", default=""); metaos.add_argument("--signature-verified", action="store_true")
    metaos.add_argument("--authorization-ref")
    invoke = sub.add_parser("metaos-invoke", help="invoke one exact-digest MetaOS pure-policy export in a hostless bounded sandbox")
    invoke.add_argument("export", choices=[
        "architecture-version", "terminal-success", "knowledge-gate", "formalization-gate",
        "implementation-gate", "implementation-authorized", "active-allowed", "checkpoint-trusted",
        "provider-failure-is-mission-failure", "resource-red-is-mission-failure",
        "unknown-effect-retry-allowed", "network-default-deny"
    ])
    invoke.add_argument("--args-json", required=True, help="JSON array of typed component arguments")
    invoke.add_argument("--expected-sha256", required=True)
    invoke.add_argument("--authorization-ref", required=True)
    invoke.add_argument("--allow-execution", action="store_true", help="explicit opt-in for the hostless pure-policy probe only")
    invoke.add_argument("--journal", type=Path, required=True, help="append-only evidence journal path")
    invoke.add_argument("--path", type=Path, help="explicit component path; defaults to the bundled versioned candidate")
    invoke.add_argument("--fuel", type=int, default=100000)
    return p

def _load_json(path):
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            return json.load(stream)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise V8Error("V8E001", f"cannot read JSON {path}: {exc}") from exc

def validate_mission(m):
    required = {"mission_id", "scope", "capability_plan", "deadline_utc", "authorization_ref",
                "acceptance_criteria", "target_candidate"}
    missing = sorted(required - m.keys())
    issues = [f"missing field: {x}" for x in missing]
    if not isinstance(m.get("scope"), dict) or not m.get("scope", {}).get("environment_id"):
        issues.append("scope.environment_id required")
    if not isinstance(m.get("capability_plan"), list) or not m.get("capability_plan"):
        issues.append("capability_plan must be non-empty")
    if not isinstance(m.get("acceptance_criteria"), list) or not m.get("acceptance_criteria"):
        issues.append("acceptance_criteria must be non-empty")
    if not m.get("authorization_ref"):
        issues.append("authorization_ref required")
    if not isinstance(m.get("target_candidate"), dict) or not m.get("target_candidate", {}).get("artifact_sha256"):
        issues.append("target_candidate.artifact_sha256 required")
    from datetime import datetime
    try:
        dt = datetime.fromisoformat(str(m.get("deadline_utc", "")).replace("Z", "+00:00"))
        if dt.tzinfo is None:
            issues.append("deadline_utc must include a timezone")
    except ValueError:
        issues.append("deadline_utc must be ISO-8601 with timezone")
    return {"status": "PASS" if not issues else "BLOCKED", "issues": issues,
            "mission_id": m.get("mission_id"), "validated_at_utc": utc_now(),
            "execution_authorized": False}

def main(argv=None):
    args = build_parser().parse_args(argv)
    try:
        if args.command == "selftest":
            result = selftest(); emit(result); return 0 if result["status"] == "PASS" else 1
        if args.command == "status":
            manifest = load_resource_json("build_manifest.json")
            emit({"artifact":"CUSTOSZV8","version":"8.0.0-candidate",
                  "package_status":manifest.get("package_status","CANDIDATE"),
                  "components":manifest.get("components",{}),
                  "certification":manifest.get("certification",{"g23":"NOT_GRANTED","g24":"NOT_GRANTED"}),
                  "limitations":manifest.get("limitations",[]),
                  "generated_at_utc":manifest.get("generated_at_utc")})
            return 0
        if args.command == "manifest":
            emit(load_resource_json("build_manifest.json")); return 0
        if args.command == "validate-manifest":
            m = _load_json(args.path); issues = validate_manifest(m, require_final_identity=args.release)
            emit({"status":"PASS" if not issues else "FAIL","issues":issues,
                  "release_eligible":not issues and args.release})
            return 0 if not issues else 2
        if args.command == "inspect-component":
            result = verify_component(args.path, args.expected_sha256); emit(result)
            return 0 if result.get("status","").startswith("PASS") else 2
        if args.command == "inspect-wasm":
            emit(inspect_wasm(args.path)); return 0
        if args.command == "translate":
            text = args.text if args.text is not None else args.file.read_text(encoding="utf-8")
            result = TranslationEngine().translate(text, args.source, args.target); emit(result)
            return 0 if result["validation_state"] in {"PASS","PARTIAL"} else 2
        if args.command == "code-to-english":
            emit(TranslationEngine.code_to_english(args.path.read_text(encoding="utf-8"), str(args.path))); return 0
        if args.command == "journal-verify":
            emit(EvidenceJournal(args.path).verify()); return 0
        if args.command == "journal-append":
            payload = json.loads(args.payload)
            if not isinstance(payload, dict): raise V8Error("V8E019","payload must be a JSON object")
            emit(EvidenceJournal(args.path).append(args.event_type,payload,args.actor,args.mission_id)); return 0
        if args.command == "capability-validate":
            data = _load_json(args.path)
            records = data if isinstance(data, list) else data.get("capabilities", [])
            issues = CapabilityRegistry(records).validate()
            emit({"status":"PASS" if not issues else "CONFLICT","issues":issues})
            return 0 if not issues else 2
        if args.command == "native-readonly":
            emit(run_native_readonly(args.path,args.native_command,expected_sha256=args.expected_sha256,
                                     authorization_ref=args.authorization_ref,timeout_seconds=args.timeout))
            return 0
        if args.command == "github-repo":
            emit(GitHubBridge().inspect_repository(args.owner,args.repo)); return 0
        if args.command == "github-branch":
            emit(GitHubBridge().inspect_branch(args.owner,args.repo,args.branch)); return 0
        if args.command == "github-runs":
            emit(GitHubBridge().workflow_runs(args.owner,args.repo,args.branch)); return 0
        if args.command == "github-dispatch":
            inputs = json.loads(args.inputs)
            if not isinstance(inputs,dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in inputs.items()):
                raise V8Error("V8E021","workflow inputs must be a string-to-string object")
            emit(GitHubBridge().dispatch_workflow(args.owner,args.repo,args.workflow_id,args.ref,
                                                   inputs,args.authorization_ref)); return 0
        if args.command == "mission-validate":
            result = validate_mission(_load_json(args.path)); emit(result)
            return 0 if result["status"] == "PASS" else 2
        if args.command == "watchdog-evaluate":
            watcher = MissionWatchdog()
            watcher.start(args.mission_id, args.deadline_utc, args.threshold_seconds, args.last_progress_epoch)
            if args.waiting_on or args.resume_condition or args.wait_deadline_utc:
                if not (args.waiting_on and args.resume_condition and args.wait_deadline_utc):
                    raise V8Error("V8E012", "waiting_on, resume_condition and wait_deadline_utc are jointly required")
                watcher.wait_for(args.mission_id, args.waiting_on, args.resume_condition, args.wait_deadline_utc)
            result = watcher.observe(args.mission_id, args.now_epoch); emit(result)
            return 0 if result["state"] in {"ACTIVE","WAITING_FOR_DEPENDENCY"} else 2
        if args.command == "retry-decision":
            result = RetryController.decide(args.idempotency_class, args.attempts_used, args.max_attempts,
                args.transient, args.authorization_ref, args.idempotency_key); emit(result)
            return 0 if result["decision"] in {"RETRY_BOUNDED","HOLD"} else 2
        if args.command == "checkpoint-verify":
            result = RecoveryCoordinator.verify_checkpoint(args.path, args.expected_sha256); emit(result)
            return 0 if result["status"] == "PASS_CHECKPOINT_IDENTITY" else 2
        if args.command == "impact-analyze":
            payload = _load_json(args.path)
            result = ChangeImpactAnalyzer.analyze(payload.get("change_id",""),
                payload.get("changed_component_ids",[]), payload.get("claim_dependencies",{})); emit(result)
            return 0
        if args.command == "runtime-preflight":
            result = RuntimeV1Adapter(args.expected_sha256,args.native_interface_verified).preflight(args.path); emit(result)
            return 0 if result["status"] == "READY_FOR_AUTHORIZED_NATIVE_BINDING" else 2
        if args.command == "metaos-preflight":
            adapter = MetaOSAdapter(); inspection = adapter.inspect(args.path)
            result = {"inspection":inspection}
            if args.export:
                result["invocation_preflight"] = adapter.can_invoke(inspection,args.export,args.signature_verified,args.authorization_ref)
            emit(result)
            return 0 if inspection["status"].startswith("STATIC_") else 2
        if args.command == "metaos-invoke":
            try:
                arguments = json.loads(args.args_json)
            except json.JSONDecodeError as exc:
                raise V8Error("V8E022", f"--args-json must be valid JSON: {exc}") from exc
            if not isinstance(arguments, list):
                raise V8Error("V8E022", "--args-json must decode to an array")
            adapter = MetaOSAdapter()
            result = adapter.invoke(
                args.export, arguments, args.expected_sha256, args.authorization_ref,
                explicit_opt_in=args.allow_execution, path=args.path, fuel_limit=args.fuel
            )
            record = EvidenceJournal(args.journal).append(
                "METAOS_COMPONENT_INVOCATION",
                {
                    "artifact_id": result.get("artifact_id", "MetaOS_V8_CANDIDATE_1_0_1"),
                    "component_sha256": result.get("component_sha256", args.expected_sha256),
                    "export_name": args.export,
                    "arguments": arguments,
                    "result_status": result.get("status"),
                    "result_value": result.get("result"),
                    "expected_sha256": args.expected_sha256,
                    "authorization_ref": args.authorization_ref,
                    "authorization_ref_validation": result.get("authorization_ref_validation", "NOT_VALIDATED"),
                    "hostless": result.get("hostless", True),
                    "host_imports": result.get("host_imports", []),
                    "mission_dispatch": False,
                    "execution_authorized": False
                },
                actor="custoszv8-metaos-adapter", mission_id=None
            )
            result["evidence_event"] = record
            result["evidence_journal"] = EvidenceJournal(args.journal).verify()
            emit(result)
            return 0 if result.get("status") == "PASS_METAOS_EXPORT_INVOKED" else 2
        raise V8Error("V8E030", "unknown command")
    except V8Error as exc:
        emit({"status":"BLOCKED","error_code":exc.code,"message":exc.message,"timestamp_utc":utc_now()})
        return 2
    except (OSError, ValueError, TypeError) as exc:
        emit({"status":"FAIL","error_code":"V8E001","message":str(exc),"timestamp_utc":utc_now()})
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
