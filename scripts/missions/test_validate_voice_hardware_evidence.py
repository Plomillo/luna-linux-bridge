#!/usr/bin/env python3
"""Contract tests for the fail-closed physical voice evidence validator."""
import json
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
    "physical_audio_hardware_tested": True,
    "native_app_voice_command_executed": True,
    "microphone_capture": True,
    "transcription_nonempty": True,
    "response_http_success": True,
    "tts_audio_nonempty": True,
    "playback_exit_success": True,
    "audible_playback_confirmed_by_operator": True,
    "temporary_audio_cleanup_verified": True,
}

def main():
    script = pathlib.Path(__file__).with_name("validate_voice_hardware_evidence.py")
    with tempfile.TemporaryDirectory() as td:
        path = pathlib.Path(td) / "evidence.json"
        path.write_text(json.dumps(VALID), encoding="utf-8")
        good = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "a" * 40], capture_output=True, text=True)
        if good.returncode != 0 or '"status": "PASS"' not in good.stdout:
            raise SystemExit("valid physical voice evidence should pass: " + good.stdout + good.stderr)
        mismatch = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "9" * 40], capture_output=True, text=True)
        if mismatch.returncode == 0 or "candidate SHA" not in mismatch.stdout:
            raise SystemExit("candidate SHA mismatch must fail closed")
        path.write_text(json.dumps({**VALID, "audible_playback_confirmed_by_operator": False}), encoding="utf-8")
        no_audio = subprocess.run([sys.executable, str(script), str(path), "--candidate-sha", "a" * 40], capture_output=True, text=True)
        if no_audio.returncode == 0 or "audible_playback_confirmed_by_operator" not in no_audio.stdout:
            raise SystemExit("missing audible playback confirmation must fail closed")
    print("PASS: valid evidence accepted; wrong SHA and missing audible confirmation rejected.")

if __name__ == "__main__":
    main()
