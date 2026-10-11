# CP-07 dedicated physical-audio runner

This runner is intentionally separate from the developer workstation. Never register a personal workstation under the CP-07 hardware label and never run the physical test on the workstation under test.

## Provisioning

1. Prepare a separate Linux x86_64 host with a physically connected microphone and speaker/headphone output. Keep a local interactive audio session available for PipeWire/PulseAudio.
2. Create a short-lived repository runner registration token in GitHub Settings → Actions → Runners → New self-hosted runner. Do not commit it, paste it into chat, or save it in shell history.
3. Copy the script `scripts/missions/provision_cp07_dedicated_runner.sh` to that separate host and run it as a dedicated non-root account. Supply the token only as an environment variable in that host's private shell:
   `export RUNNER_REGISTRATION_TOKEN='…'`
   `bash provision_cp07_dedicated_runner.sh`
4. The script installs the official GitHub Actions runner, Whisper.cpp v1.7.6 with multilingual `ggml-base.bin`, Piper with the Spanish `es_ES-sharvard-medium` voice, and local Ollama `smollm2:360m`; it refuses registration unless physical ALSA capture and playback cards are present and no loopback/null/dummy device is detected.
5. The runner registers only with label `louksna-voice-hw-dedicated`. CP-07 workflows no longer match the prior workstation label. The workflow discovers audio source/sink names and resolves model paths relative to the runner account instead of hardcoding a personal home directory.
6. Verify the runtime manifest and hashes under `~/.local/state/louksna-cp07/`. Do not approve operator attestation merely because the test process returned success; the reviewer must independently confirm audible playback from the dedicated host.

## Language and evidence

CP-07 now asks the operator in Spanish and forces Whisper language `es`. The generated evidence remains SHA-bound to the exact candidate commit. The physical job records preliminary evidence as `HOLD`; only the protected operator-attestation stage may promote it after approval. CP-10, G23, and G24 must consume evidence from that same candidate; no gate is bypassed by recorded-audio CI.

## Security boundary

- Do not run this script on the developer workstation or the PC under test.
- Do not store the registration token in the repository, a committed environment file, or public logs.
- Physical audio loopback, null, dummy, and virtual-only devices are rejected.
- No merge to `main` is performed by this workflow.
