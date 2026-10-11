#!/usr/bin/env python3
"""Fail-closed contract checks: voice must remain explicitly unactivated."""
from pathlib import Path
import json
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: voice_e2e_gate_contract_test.py <App.tsx> <governance-workflow.yml>")

app_path = Path(sys.argv[1])
workflow_path = Path(sys.argv[2])
if not app_path.is_file() or not workflow_path.is_file():
    raise SystemExit("VOICE_GATE_INPUT_MISSING")

app = app_path.read_text(encoding="utf-8")
workflow = workflow_path.read_text(encoding="utf-8")
physical_workflow_path = workflow_path.with_name("louksna-zd-v03-physical-voice.yml")
physical_workflow = physical_workflow_path.read_text(encoding="utf-8") if physical_workflow_path.is_file() else ""
root = workflow_path.parent.parent.parent
voice_template_path = root / "scripts" / "missions" / "v03_templates" / "main.rs"
voice_template = voice_template_path.read_text(encoding="utf-8") if voice_template_path.is_file() else ""

checks = {
    "ui_keeps_voice_gate_open": "El gate de certificación permanece abierto" in app,
    "real_voice_handler_wired": 'call<{status:string;transcript:string;response:string;elapsed_ms:number;audio_played:boolean}>("voice_e2e")' in app,
    "voice_preflight_wired": '("voice_preflight")' in app,
    "no_synthetic_audio_claim": "captura y reproducción reales" in app,
    "workflow_gate_open": '"voice_gate": "OPEN", "voice_active": False' in workflow,
    "workflow_blocks_certification": '"certification_effect": "G23_G24_BLOCKED"' in workflow,
    "voice_e2e_not_claimed": '"voice_e2e_executed": False' in workflow,
    "voice_gate_artifact_preserved": "name: louksna-zd-v03-cp07-voice-gate" in workflow,
    "physical_workflow_is_reusable": "workflow_call:" in physical_workflow,
    "physical_job_uses_dedicated_audio_runner": "runs-on: [self-hosted, linux, x64, louksna-voice-hw]" in physical_workflow,
    "production_voice_command_is_exercised": "physical_voice_e2e_real_audio_path" in voice_template and "voice::voice_e2e()" in voice_template,
    "cp08_build_progress_is_independent": "stage-08-reproducible-build:\n    name:" in workflow and "needs: stage-06-functions-attachments" in workflow[workflow.index("stage-08-reproducible-build:"):workflow.index("stage-09-", workflow.index("stage-08-reproducible-build:"))],
    "terminal_evidence_requires_physical_voice": "stage-07-physical-voice.result == 'success'" in workflow and "louksna-zd-v03-cp07-physical-voice-e2e" in workflow,
}
report = {
    "schema": "louksna.zd.v03.voice-gate-contract-test.v1",
    "status": "PASS" if all(checks.values()) else "FAIL",
    "voice_gate": "OPEN",
    "voice_active": False,
    "g23_g24_effect": "BLOCKED",
    "checks": checks,
    "inputs": {"app": str(app_path), "workflow": str(workflow_path)},
}
print(json.dumps(report, indent=2, sort_keys=True))
if not all(checks.values()):
    raise SystemExit(1)
