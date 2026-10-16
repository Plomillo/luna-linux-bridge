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

checks = {
    "ui_discloses_voice_not_certified": "La pila de voz end-to-end todavia no esta certificada." in app,
    "microphone_control_disabled": "<button disabled>Microfono — gate abierto</button>" in app,
    "workflow_gate_open": '"voice_gate": "OPEN", "voice_active": False' in workflow,
    "workflow_blocks_certification": '"certification_effect": "G23_G24_BLOCKED"' in workflow,
    "voice_e2e_not_claimed": '"voice_e2e_executed": False' in workflow,
    "voice_gate_artifact_preserved": "name: louksna-zd-v03-cp07-voice-gate-open" in workflow,
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
