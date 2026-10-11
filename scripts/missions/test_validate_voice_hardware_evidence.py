#!/usr/bin/env python3
"""Contract tests for the fail-closed physical voice evidence validator."""
import json
import hashlib
import pathlib
import subprocess
import sys
import tempfile

VALID = {
    "schema": "louksna.zd.v03.physical-voice-e2e.v1",
    "status": "PASS",
    "voice_gate": "PASS",
    "candidate_commit_sha": "a" * 40,
    "source_run_id": "123456",
    "os_kernel": "Linux test-kernel",
    "capture_device": "hw:1,0",
    "playback_device": "hw:1,0",
    "capture_source": "physical-usb-input",
    "playback_sink": "physical-analog-output",
    "arecord_version": "arecord test",
    "aplay_version": "aplay test",
    "whisper_version": "whisper test",
    "piper_version": "piper test",
    "ollama_version": "ollama test",
    "ollama_model": "local-test-model",
    "whisper_model_sha256": "b" * 64,
    "piper_model_sha256": "c" * 64,
    "evidence_log_sha256": "d" * 64,
    "whisper_binary_sha256": "e" * 64,
    "piper_binary_sha256": "f" * 64,
    "app_binary_sha256": "0" * 64,
    "voice_test_binary_sha256": "1" * 64,
    "build_manifest_sha256": "2" * 64,
    "acoustic_output_energy_detected": True,
    "acoustic_baseline_peak_rms": 100.0,
    "acoustic_playback_peak_rms": 400.0,
    "acoustic_speech_match_ratio": 0.75,
    "acoustic_transcription_match_count": 3,
    "operator_observation": "NOT_COLLECTED_OPTIONAL",
    "physical_audio_hardware_tested": True,
    "native_app_voice_command_executed": True,
    "microphone_capture": True,
    "transcription_nonempty": True,
    "response_http_success": True,
    "tts_audio_nonempty": True,
    "playback_exit_success": True,
    "temporary_audio_cleanup_verified": True,
}

def main():
    script = pathlib.Path(__file__).with_name("validate_voice_hardware_evidence.py")
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "CP-07-physical-voice-e2e.json"
        log_path = path.with_name("CP-07-physical-voice-e2e.log")
        log_path.write_text("\n".join([
            "PHYSICAL_VOICE_MIC_CAPTURE=PASS",
            "PHYSICAL_VOICE_TRANSCRIPTION=PASS",
            "PHYSICAL_VOICE_MODEL_RESPONSE=PASS",
            "PHYSICAL_VOICE_TTS=PASS",
            "PHYSICAL_VOICE_PLAYBACK=PASS",
            "PHYSICAL_VOICE_ACOUSTIC_OUTPUT=PASS",
            "PHYSICAL_VOICE_ACOUSTIC_TRANSCRIPTION_MATCH=PASS",
            "PHYSICAL_VOICE_E2E_RESULT=PASS",
            "PHYSICAL_VOICE_TEMP_CLEANUP=PASS",
        ]) + "\n", encoding="utf-8")
        valid = {**VALID, "evidence_log_sha256": hashlib.sha256(log_path.read_bytes()).hexdigest()}
        path.write_text(json.dumps(valid), encoding="utf-8")
        good = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "a" * 40], capture_output=True, text=True)
        if good.returncode != 0 or '"status": "PASS"' not in good.stdout:
            raise SystemExit("valid physical voice evidence should pass: " + good.stdout + good.stderr)
        mismatch = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "9" * 40], capture_output=True, text=True)
        if mismatch.returncode == 0 or "does not match current candidate" not in mismatch.stdout:
            raise SystemExit("candidate SHA mismatch must fail closed")
        path.write_text(json.dumps({**valid, "acoustic_output_energy_detected": False}), encoding="utf-8")
        no_audio = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "a" * 40], capture_output=True, text=True)
        if no_audio.returncode == 0 or "acoustic_output_energy_detected" not in no_audio.stdout:
            raise SystemExit("missing acoustic signal evidence must fail closed")
    print("PASS: valid acoustic evidence accepted; wrong SHA and missing acoustic signal rejected.")

if __name__ == "__main__":
    main()
