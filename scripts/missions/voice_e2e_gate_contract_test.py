#!/usr/bin/env python3
"""Executable CP-07 contract regression: never confuse voice-gate safety with voice E2E."""
from pathlib import Path
import sys

if len(sys.argv) != 3:
    raise SystemExit("usage: voice_e2e_gate_contract_test.py App.tsx governance-workflow.yml")

app = Path(sys.argv[1]).read_text(encoding="utf-8")
workflow = Path(sys.argv[2]).read_text(encoding="utf-8")

checks = {
    "voice_call_panel_present": 'label:"Chat / Llamada"' in app,
    "voice_is_explicitly_not_certified": "La pila de voz end-to-end todavia no esta certificada" in app,
    "microphone_control_disabled": "<button disabled>Microfono — gate abierto</button>" in app,
    "workflow_keeps_voice_gate_open": '"voice_gate":"OPEN"' in workflow,
    "workflow_never_marks_voice_active": '"voice_active":False' in workflow,
    "workflow_does_not_claim_voice_e2e": '"e2e_executed":False' in workflow,
    "certification_remains_blocked": "G23_G24_MUST_REMAIN_BLOCKED_WHILE_VOICE_IS_MANDATORY" in workflow,
}
for name, ok in checks.items():
    print(f"CP07_CONTRACT_CHECK {name}={'PASS' if ok else 'FAIL'}")
if not all(checks.values()):
    raise SystemExit("CP07_CONTRACT_REGRESSION_FAILED")
print("CP07_CONTRACT_REGRESSION=PASS")
print("VOICE_E2E=NOT_TESTED; VOICE_ACTIVE=FALSE; CERTIFICATION=BLOCKED")
