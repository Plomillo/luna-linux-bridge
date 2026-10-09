#!/usr/bin/env python3
"""Static, fail-closed readiness audit for the Louksna ZD V0.3 infrastructure.

This tool reports repository-observable controls only. It cannot prove that a
self-hosted runner is online, that voice hardware works, or that G23/G24 have
been performed by independent actors.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/louksna-zd-v03-governance.yml"
CONTRACT = ROOT / "governance/zona-directiva-v03/12_STAGE_GOVERNANCE_CONTRACT.md"
RUNNER_DOC = ROOT / "governance/zona-directiva-v03/CP-09-DISPOSABLE-KDE-RUNNER.md"

def finding(code: str, status: str, detail: str, evidence: list[str] | None = None) -> dict:
    return {"code": code, "status": status, "detail": detail, "evidence": evidence or []}

def audit(root: Path = ROOT) -> dict:
    wf_path = root / ".github/workflows/louksna-zd-v03-governance.yml"
    contract_path = root / "governance/zona-directiva-v03/12_STAGE_GOVERNANCE_CONTRACT.md"
    runner_path = root / "governance/zona-directiva-v03/CP-09-DISPOSABLE-KDE-RUNNER.md"
    runtime_script_path = root / "scripts/missions/debian13_kde_host_runtime.sh"
    findings: list[dict] = []
    required = [(wf_path, "governance workflow"), (contract_path, "governance contract"), (runner_path, "CP-09 runner runbook"), (runtime_script_path, "CP-09 host runtime script")]
    missing = [label for path, label in required if not path.is_file()]
    if missing:
        findings.append(finding("REPO_CONTROL_FILES", "FAIL", "Missing required control files: " + ", ".join(missing)))
        return make_report(root, findings)

    wf = wf_path.read_text(encoding="utf-8")
    contract = contract_path.read_text(encoding="utf-8")
    runner = runner_path.read_text(encoding="utf-8")
    runtime_script = runtime_script_path.read_text(encoding="utf-8")

    checks = [
        ("CP09_TARGET_RUNNER", all(x in wf for x in ["self-hosted", "debian-13", "kde", "disposable"]),
         "CP-09 targets a dedicated self-hosted Debian 13/KDE/disposable runner."),
        ("CP09_FAIL_CLOSED", "HOLD" in wf and "stage-09-physical-runtime" in wf,
         "The physical runtime stage and HOLD state are represented in the workflow."),
        ("CP09_REPORT_PATH_MATCH", "CP-09-debian13-kde-runtime.json" in wf and "CP-09-debian13-kde-runtime.json" in runtime_script and "CP-09-debian13-kde-runtime.log" in wf,
         "Workflow upload paths match the actual CP-09 report and log names."),
        ("CP10_BINDS_PHYSICAL_EVIDENCE", all(x in wf for x in ["physical_runtime_verified", "candidate_sha256", "log_sha256", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT"]),
         "CP-10 requires same-run CP-09 evidence and validates physical runtime, package digest, and log digest."),
        ("CP10_EVIDENCE_FREEZE", "stage-10-evidence-freeze" in wf and "CP-10-evidence-manifest.json" in wf,
         "CP-10 evidence-manifest stage exists."),
        ("G23_NO_SELF_CERTIFICATION", "independent validator identity" in wf and "exit 1" in wf,
         "G23 remains blocked when independent validator evidence is not configured."),
        ("G24_NO_AUTO_CERTIFICATION", "G23 evidence absent" in wf and "no automatic certification" in wf,
         "G24 remains blocked without G23."),
        ("CONTRACT_NO_MAIN_MUTATION", "NO_MAIN_MUTATION = TRUE" in contract and "No modificar `main`" in contract,
         "Governance contract preserves the no-main-mutation boundary."),
        ("RUNNER_DISPOSABLE", "disposable VM" in runner and "Do not register a daily-use workstation" in runner,
         "CP-09 runbook requires an isolated disposable host."),
        ("VOICE_SCOPE_DISCLOSED", "actual microphone capture/audio transport/remote response" in contract or "voz" in contract.lower(),
         "Voice requirement is explicitly represented in governance contract."),
    ]
    for code, ok, detail in checks:
        findings.append(finding(code, "PASS" if ok else "FAIL", detail, [str((wf_path if code.startswith("CP") or code.startswith("G") or code.startswith("VOICE") else contract_path).relative_to(root))]))

    # These are external/material gates and are never inferred from static files.
    findings.extend([
        finding("CP09_LIVE_RUNNER", "UNVERIFIED", "Runner online/idle state is external to repository contents; CP-09 run must provide host-generated evidence."),
        finding("VOICE_REAL_E2E", "BLOCKED", "Browser UI tests with a Tauri IPC test double do not prove microphone capture, audio transport, or a real remote voice response."),
        finding("CP10_DIGEST_FREEZE", "BLOCKED", "A same-run, complete evidence dossier must be generated and bound to the exact candidate commit and artifact digests."),
        finding("G23_INDEPENDENT_VALIDATION", "BLOCKED", "Requires an independent validator identity and digest-bound report; producer CI cannot self-approve."),
        finding("G24_CERTIFICATION", "BLOCKED", "Requires a favorable G23 report and a formal certification decision; this audit does not certify or activate."),
    ])
    return make_report(root, findings)

def make_report(root: Path, findings: list[dict]) -> dict:
    failed = sum(x["status"] == "FAIL" for x in findings)
    blocked = sum(x["status"] == "BLOCKED" for x in findings)
    unverified = sum(x["status"] == "UNVERIFIED" for x in findings)
    overall = "FAIL" if failed else ("HOLD" if blocked or unverified else "PASS")
    report = {
        "schema": "louksna.zd.v03.infrastructure-readiness.v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "repository": "Plomillo/luna-linux-bridge",
        "scope": "static repository controls plus explicitly disclosed external gates",
        "overall_status": overall,
        "counts": {"pass": sum(x["status"] == "PASS" for x in findings), "fail": failed, "blocked": blocked, "unverified": unverified},
        "findings": findings,
        "certification": "NOT_GRANTED",
        "activation": "FALSE",
        "main_mutation": "NOT_PERFORMED",
        "limitations": [
            "Static presence is not proof that a control passed at runtime.",
            "This audit cannot inspect self-hosted runner availability or physical KDE session state.",
            "This audit does not validate real voice hardware or remote voice service.",
            "This report is not G23 independent validation or G24 certification."
        ]
    }
    return report

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.root.resolve())
    rendered = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    # HOLD is a legitimate fail-closed outcome, not a tool crash. Structural FAIL
    # exits nonzero so CI can detect missing governance controls.
    return 1 if report["overall_status"] == "FAIL" else 0

if __name__ == "__main__":
    raise SystemExit(main())
