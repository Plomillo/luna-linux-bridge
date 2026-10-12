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
voice_impl_path = root / "scripts" / "missions" / "v03_templates" / "voice.rs"
voice_impl = voice_impl_path.read_text(encoding="utf-8") if voice_impl_path.is_file() else ""
legacy_audio_workflow_path = workflow_path.parent / "louksna-cp07-physical-audio.yml"
legacy_audio_workflow = legacy_audio_workflow_path.read_text(encoding="utf-8") if legacy_audio_workflow_path.is_file() else ""

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
    "automated_stimulus_is_explicitly_required": 'LOUKSNA_VOICE_STIMULUS_REQUIRED: "1"' in physical_workflow,
    "automated_stimulus_is_hash_pinned": "LOUKSNA_VOICE_STIMULUS_SHA256" in physical_workflow and "VOICE_STIMULUS_SHA256_MISMATCH" in voice_impl and "ratio < 0.80" in voice_impl,
    "stimulus_provenance_is_required": "LOUKSNA_VOICE_STIMULUS_SOURCE_URL" in physical_workflow and "VOICE_STIMULUS_PROVENANCE_OR_REFERENCE_MISSING" in voice_impl,
    "fixture_source_is_cc0_and_sha_pinned": "CC0-1.0" in physical_workflow and "1aa9fcf9a210c256a15a6f8682eeda65b17fd86ba3e37873303d5b9a60b972cf" in physical_workflow,
    "fixture_is_normalized_and_manifested": "ffmpeg -nostdin" in physical_workflow and "stimulus-manifest.json" in physical_workflow and "normalized_fixture_sha256" in physical_workflow,
    "fixture_manifest_is_verified_before_audio": "CP-07 HOLD: human stimulus provenance/hash manifest failed" in physical_workflow,
    "fixture_is_played_and_recaptured_physically": 'run_bounded("aplay", &["-q","-D",&playback_device,stimulus]' in voice_impl and "VOICE_STIMULUS_PHYSICAL_CAPTURE_FAILED" in voice_impl,
    "fixture_stt_uses_reference_content_gate": "VOICE_STIMULUS_TRANSCRIPTION_MISMATCH" in voice_impl and "expected_tokens.is_empty()" in voice_impl,
    "legacy_live_operator_gate_is_preserved": "VOICE_TRANSCRIPTION_TEST_PHRASE_MISMATCH" in voice_impl and "voice_test_anchors_present(&phrase_tokens)" in voice_impl,
    "automated_mode_suppresses_live_operator_countdown": 'if std::env::var("LOUKSNA_VOICE_STIMULUS_REQUIRED")' in voice_template and "PHYSICAL_VOICE_STIMULUS_MODE=HUMAN_RECORDED_PHYSICAL_ACOUSTIC" in voice_template,
    "physical_audio_workflow_is_manual_only": "workflow_dispatch:" in legacy_audio_workflow and "\\n  push:" not in legacy_audio_workflow,
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
