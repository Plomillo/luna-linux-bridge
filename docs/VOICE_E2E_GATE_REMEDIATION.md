# CP-07 physical voice evidence handoff

Status: additive gate-remediation contract; does not certify voice or activate the application.

## Root cause

The current hosted workflow executes browser UI checks with an explicit Tauri IPC test double and then unconditionally writes `voice_gate=OPEN`, `e2e_executed=false`, and `physical_audio_hardware_tested=false`. That is honest for hosted CI, but it leaves no promotion path for separately acquired physical-hardware evidence. The mission also declares `EXECUTION_LOCATION = GITHUB_HOSTED_ONLY`, which is incompatible with a requirement for real microphone and speaker hardware. Hosted runners cannot establish physical audio behavior.

## Corrected boundary

- Keep CP-01 through CP-06 and CP-08 through CP-12 on GitHub-hosted runners where appropriate.
- Keep the existing hosted CP-07 UI/security checks; they are useful but are not physical voice proof.
- Physical CP-07 evidence must originate from a self-hosted Linux runner with actual microphone/speaker devices, running the exact candidate SHA and its native application voice command.
- A self-hosted runtime preflight, shell-only pipeline, unit test, browser IPC test double, QEMU run, or successful process exit alone is not sufficient. The native app voice command must execute, and the operator must confirm audible playback.
- The evidence artifact must be named `louksna-zd-v03-cp07-physical-voice-e2e` and contain `CP-07-physical-voice-e2e.json`.
- Evidence must use schema `louksna.zd.v03.physical-voice-e2e.v1`, bind `candidate_commit_sha` to the exact candidate, and set `status=PASS` and `voice_gate=PASS` only when every required field is evidenced.
- The validator `scripts/missions/validate_voice_hardware_evidence.py` checks candidate binding, physical proof flags, provenance fields, and SHA-256 field shapes. It does not independently hear audio; G23 remains a separate decision.
- Record binary/model source URLs and exact versions, SHA-256 hashes, OS/kernel, ALSA device IDs, capture/transcription/response/TTS/playback outcomes, temporary-file cleanup, operator audible confirmation, source workflow run ID, and the app binary hash. Never store captured audio, transcript, response text, secrets, or tokens in the evidence artifact.
- Any code change after the physical run changes the candidate SHA and invalidates that evidence for the new candidate.

## Runner safety

Do not install large models or start model downloads automatically from CI. Provision binaries/models explicitly from trusted upstream sources, pin their versions and SHA-256 values, and use a dedicated runner label such as `louksna-voice-hw`. Limit runner repository access to this repository and avoid running untrusted fork pull-request code on it. Do not enable automatic merge, automatic certification, or automatic activation.

## Required artifact JSON fields

See `scripts/missions/validate_voice_hardware_evidence.py` for the authoritative required-field list. The minimum proof booleans are:

- `physical_audio_hardware_tested`
- `native_app_voice_command_executed`
- `microphone_capture`
- `transcription_nonempty`
- `response_http_success`
- `tts_audio_nonempty`
- `playback_exit_success`
- `audible_playback_confirmed_by_operator`
- `temporary_audio_cleanup_verified`

All must be literal JSON booleans `true`. A declaration is still subject to independent validation; it is not a self-issued G23/G24 certificate.
