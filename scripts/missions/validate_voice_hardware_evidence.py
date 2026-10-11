#!/usr/bin/env python3
"""Fail-closed validator for physical voice E2E evidence artifacts.

This validates evidence structure and candidate binding. It cannot independently
hear audio; audible playback must be confirmed by the on-device operator.
"""
from __future__ import annotations
import argparse
import json
import pathlib
import sys

REQUIRED_TRUE = (
    "physical_audio_hardware_tested",
    "native_app_voice_command_executed",
    "microphone_capture",
    "transcription_nonempty",
    "response_http_success",
    "tts_audio_nonempty",
    "playback_exit_success",
    "acoustic_output_energy_detected",
    "temporary_audio_cleanup_verified",
)
REQUIRED_TEXT = (
    "candidate_commit_sha",
    "source_run_id",
    "os_kernel",
    "capture_device",
    "playback_device",
    "capture_source",
    "playback_sink",
    "arecord_version",
    "aplay_version",
    "whisper_version",
    "piper_version",
    "ollama_version",
    "ollama_model",
    "whisper_model_sha256",
    "piper_model_sha256",
    "evidence_log_sha256",
)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("evidence", type=pathlib.Path)
    parser.add_argument("--candidate-sha", required=True)
    args = parser.parse_args()
    try:
        data = json.loads(args.evidence.read_text(encoding="utf-8"))
    except Exception as exc:
        print(json.dumps({"status": "HOLD", "reason": f"invalid evidence JSON: {exc}"}))
        return 1

    errors = []
    if data.get("schema") != "louksna.zd.v03.physical-voice-e2e.v1":
        errors.append("schema mismatch")
    if data.get("status") != "PASS":
        errors.append("evidence status is not PASS")
    if data.get("voice_gate") != "PASS":
        errors.append("voice_gate is not PASS")
    if data.get("candidate_commit_sha") != args.candidate_sha:
        errors.append("evidence SHA does not match current candidate")
    for field in REQUIRED_TRUE:
        if data.get(field) is not True:
            errors.append(f"required physical proof missing: {field}")
    for field in REQUIRED_TEXT:
        value = data.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"required provenance field missing: {field}")
    for field in ("whisper_binary_sha256", "piper_binary_sha256", "app_binary_sha256", "voice_test_binary_sha256", "build_manifest_sha256"):
        value = data.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
            errors.append(f"invalid or missing SHA-256: {field}")
    for field in ("whisper_model_sha256", "piper_model_sha256", "evidence_log_sha256"):
        value = data.get(field)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdefABCDEF" for c in value):
            errors.append(f"invalid or missing SHA-256: {field}")
    baseline = data.get("acoustic_baseline_peak_rms")
    playback = data.get("acoustic_playback_peak_rms")
    if not isinstance(baseline, (int, float)) or baseline < 0:
        errors.append("invalid or missing acoustic_baseline_peak_rms")
    if not isinstance(playback, (int, float)) or playback < 0:
        errors.append("invalid or missing acoustic_playback_peak_rms")
    if isinstance(baseline, (int, float)) and isinstance(playback, (int, float)):
        if playback < max(250.0, baseline * 1.5):
            errors.append("measured acoustic output does not exceed baseline threshold")
    match_ratio = data.get("acoustic_speech_match_ratio")
    match_count = data.get("acoustic_transcription_match_count")
    if not isinstance(match_ratio, (int, float)) or not 0.30 <= match_ratio <= 1.0:
        errors.append("acoustic speech overlap ratio is missing or below 0.30")
    if not isinstance(match_count, int) or match_count < 2:
        errors.append("acoustic speech overlap requires at least two matching tokens")
    if data.get("audible_playback_confirmed_by_operator") is not True and data.get("operator_observation") != "NOT_COLLECTED_OPTIONAL":
        errors.append("operator observation must be explicit: affirmative or optional-not-collected")

    log_path = args.evidence.with_name("CP-07-physical-voice-e2e.log")
    expected_log_hash = data.get("evidence_log_sha256")
    if not log_path.is_file():
        errors.append("physical voice evidence log file missing")
    elif isinstance(expected_log_hash, str):
        import hashlib
        actual_log_hash = hashlib.sha256(log_path.read_bytes()).hexdigest()
        if actual_log_hash.lower() != expected_log_hash.lower():
            errors.append("physical voice evidence log SHA-256 mismatch")
        log_text = log_path.read_text(encoding="utf-8", errors="replace")
        required_markers = (
            "PHYSICAL_VOICE_MIC_CAPTURE=PASS",
            "PHYSICAL_VOICE_TRANSCRIPTION=PASS",
            "PHYSICAL_VOICE_MODEL_RESPONSE=PASS",
            "PHYSICAL_VOICE_TTS=PASS",
            "PHYSICAL_VOICE_PLAYBACK=PASS",
            "PHYSICAL_VOICE_ACOUSTIC_OUTPUT=PASS",
            "PHYSICAL_VOICE_ACOUSTIC_TRANSCRIPTION_MATCH=PASS",
            "PHYSICAL_VOICE_E2E_RESULT=PASS",
            "PHYSICAL_VOICE_TEMP_CLEANUP=PASS",
        )
        for marker in required_markers:
            if marker not in log_text:
                errors.append(f"required evidence log marker missing: {marker}")

    report = {
        "schema": "louksna.zd.v03.physical-voice-validation.v1",
        "status": "PASS" if not errors else "HOLD",
        "candidate_commit_sha": args.candidate_sha,
        "source_run_id": data.get("source_run_id"),
        "checks": {"required_physical_proof": not any("required physical proof" in e for e in errors),
                   "candidate_binding": data.get("candidate_commit_sha") == args.candidate_sha,
                   "provenance_complete": not errors},
        "errors": errors,
        "note": "Acoustic energy is automated signal evidence, not proof of semantic audibility; G23 remains a separate gate."
    }
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if not errors else 1

if __name__ == "__main__":
    raise SystemExit(main())
