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

## VirtualBox execution: permitted with physical audio passthrough

A VirtualBox guest is an acceptable execution environment for CP-07 only when the guest can access the real microphone and real playback device, and the operator can hear the generated response. A VM with a virtual/null audio sink, prerecorded input, generated test audio, or CI-only audio simulation is not physical voice evidence.

### Required VM checks

1. Configure VirtualBox audio input and output to the host's actual devices; enable USB controller and pass the actual USB microphone through to the guest when host-audio forwarding does not expose it as a capture device.
2. In the Linux guest, verify `arecord -l`, `aplay -l`, `ls -l /dev/snd`, and `lsusb` where applicable. Record the exact capture/playback device IDs. A listed device alone is not sufficient.
3. Run the exact candidate build in the guest and invoke the application's native **Grabar 8 s y responder por voz** action. Do not substitute a shell-only transcription or an IPC test double.
4. Speak a fresh prompt into the real microphone. Verify non-empty STT, successful local response endpoint, non-empty Piper WAV, successful ALSA playback, and temporary-file cleanup.
5. The operator must hear the generated response from the host's actual speakers/headphones and explicitly record that observation. Do not claim audible playback from an exit code alone.
6. Record VM/VirtualBox version, guest OS/kernel, audio configuration, actual devices, app/binary/model hashes, versions/source provenance, candidate SHA, and a hash-bound evidence log. Do not include raw audio, transcripts, responses, credentials, or tokens.
7. Run the evidence validator against the exact candidate SHA. Any subsequent source commit invalidates the evidence for that candidate. G23 independent validation and G24 certification remain separate gates.

### Fail-closed rule

If VirtualBox does not expose a working physical capture and playback path, report the VM run as a software/integration test only and leave CP-07 OPEN. Do not change the gate to PASS merely because the VM starts, the app builds, or audio commands return success. A dedicated self-hosted runner inside the VM is an execution option, not proof by itself; it must be isolated, trusted, and bound to the exact candidate.

## GitHub runner inventory and protected-environment API permissions

The repository Actions token with `actions: read` cannot list repository self-hosted runners: GitHub requires repository `Administration: read` for `GET /repos/{owner}/{repo}/actions/runners`. The previous implementation called this endpoint with `secrets.GITHUB_TOKEN` and received HTTP 403 `Resource not accessible by integration`; that failure did **not** establish whether a physical runner exists or is online.

Before running the physical CP-07 path or G23/G24 environment-protection checks, configure a repository secret named `LOUKSNA_REPO_ADMIN_READ_TOKEN` containing a fine-grained credential scoped only to this repository with **Administration: read** permission. Do not put the token in source, workflow inputs, PR comments, logs, or chat. The workflows now fail fast with an explicit diagnostic if the secret is absent or the API denies access. This credential only enables inventory/protection inspection; it does not create a runner, prove physical audio hardware, approve an environment, or grant certification.

CP-07 additionally requires an actual registered, online Linux self-hosted runner labeled `louksna-voice-hw`, pre-provisioned pinned dependencies/models, non-virtual ALSA capture/playback devices, and protected operator confirmation after audible playback. A green recorded-audio test, a runner inventory response, or an API permission fix alone is insufficient. CP-10, G23, and G24 remain blocked until exact-SHA evidence and independent/protected approvals exist.


## Corrective addendum — 2026-10-11 (supersedes the earlier token prerequisite for current workflows)

This addendum is append-only and preserves the earlier diagnosis as historical evidence. For the current branch implementation, the operational method below supersedes the preceding section that required `LOUKSNA_REPO_ADMIN_READ_TOKEN` to run CP-07 and verify G23/G24 environments.

### Runner found and corrected

- The repository already had runner ID `2`, name `luna-linux`, online and idle on Linux x86_64.
- The missing capability was the required label, not the existence of a runner. The label `louksna-voice-hw` was added additively; the existing `luna-aux` and default labels were preserved.
- CP-07 preflight now executes on the actual labeled runner and verifies hardware/runtime directly instead of querying the admin-only runner inventory API with a workflow token.
- Physical runner jobs are restricted to owner-triggered runs from the same repository; fork pull requests cannot execute on the hardware runner.
- The candidate application and Rust voice test binary are compiled on GitHub-hosted Linux, then transferred as an artifact bound to the exact candidate SHA. Only the physical voice test executes on the self-hosted host. This avoids a native build burden on the 5.7-GiB physical host.

### Physical audio routing

Direct ALSA `plughw` access failed because PipeWire already owns the real devices. This was not evidence of absent hardware. The correct route is the ALSA Pulse plugin with explicit physical endpoints:

- Capture source: `alsa_input.usb-Generic_Blue_Microphones_2101BAB04QX8-00.pro-input-0`
- Playback sink: `alsa_output.pci-0000_04_00.6.analog-stereo`
- ALSA device argument: `pulse`
- Runtime socket: `/run/user/1000/pulse/native`

The endpoints were confirmed through PipeWire/PulseAudio. A two-second physical microphone capture produced a 64,044-byte WAV and the temporary file was deleted. Piper synthesized a 3.34-second WAV; physical playback through the selected sink exited successfully and the temporary WAV was deleted. These are supplemental device/runtime smoke checks, not a substitute for the exact-SHA CP-07 application workflow or the operator's audible confirmation.

### Provisioned runtime and content hashes

- Whisper.cpp: tag `v1.7.6`, commit `a8d002cfd879315632a579e73f0148d06959de36`; binary SHA-256 `955f6c121b718841d66eaef3424dcf4da3f92b90bd5199e3a361d5ccc9142768`.
- Whisper English model `ggml-base.en.bin`: SHA-256 `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002`. Offline transcription of the official `samples/jfk.wav` completed and matched the expected phrase.
- Piper TTS: version `1.8.0`; PyPI wheel SHA-256 `25b4d3f31ff70c8fa7151908e00aaa5650cbdf16bca8fcf21299f3941b89a7d3`.
- Voice model `en_US-lessac-medium.onnx`: SHA-256 `5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f`; config SHA-256 `efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0`.
- Ollama: version `0.40.3`; official archive SHA-256 `ce6f8b671a699bf1ebafb28d60dbbabf4f37b30b499145fa308a8ba72de021d6`; binary SHA-256 `1c66ac15d93ba17f2abe47d93262a62290b2233fb3c9b745564b31fd94815bd7`.
- Local model `smollm2:360m`: digest `297281b699fc51376006233ca400cd664c4f7b80ed88a47ef084f1e4b089803b`; HTTP inference smoke returned the requested response.
- Ollama runs as a user systemd service with `TasksMax=256`, one parallel request, one loaded model, 1,024-token context, and a 30-second keep-alive. The service is separated from the Desktop Commander process cgroup, whose task limit had prevented Ollama's inference worker from creating threads.

### Protected approvals

The following GitHub Environments now have a required-reviewer protection rule for repository owner `Plomillo`, with `prevent_self_review=false`:

- `voice-hardware-operator-attestation`
- `louksna-g23-independent-validation`
- `louksna-g24-certification`

The workflow no longer depends on the unavailable `LOUKSNA_REPO_ADMIN_READ_TOKEN` secret for these gates. GitHub's environment approval mechanism blocks each job until the configured reviewer approves it. Approval is not pre-recorded by this addendum: the operator must hear the CP-07 response before approving the operator-attestation environment; G23 and G24 remain separate subsequent approvals.

### Current status rule

The physical runner and local components passed supplemental smoke checks. CP-07 is still OPEN until the exact-candidate workflow proves the full native microphone → STT → local model → TTS → physical playback path, the temporary files are cleaned, and the operator confirms audible playback through the protected environment. CP-10 cannot be declared passed until its own current-SHA gates pass. G23/G24 are not certified by runner provisioning or environment creation alone.


## Addendum — authorized unattended human-recorded acoustic stimulus (2026-10-12)

The repository owner explicitly authorized an append-only CP-07 amendment. This adds a second execution mode; it does not delete the live-operator mode or change CP-01–CP-06/CP-08–CP-12.

### Required behavior

- Use a human-recorded speech fixture with verified public source, language, license, reference transcript, release/version, and pinned SHA-256. Prefer CC0. Never use TTS-generated input.
- Play the fixture through a verified physical speaker while capturing through the verified physical microphone. Run STT on the captured microphone WAV, not the fixture file. Compare the recognized text with the fixture reference transcript using a conservative content threshold.
- Pass recognized text through the configured local response model, then synthesize with the preserved es_ES-sharvard-medium.onnx and speaker_id=1.
- Play the generated answer through the physical speaker, recapture it through the physical microphone, and require both acoustic energy and STT content overlap. A successful aplay exit alone is not proof.
- Reject virtual, null, dummy, monitor, or loopback endpoints. If physical routing cannot be established, stop with HOLD.
- Enforce a hard combined project-workload ceiling of 1 GiB. Missing/disappearing memory telemetry is a HOLD and must abort inference rather than be treated as success.
- Keep temporary audio/transcript/response files out of the evidence artifact and verify cleanup. Record candidate SHA, run, timestamps, source/license/hash, device IDs, versions, binary/model hashes, numeric acoustic measures, log hash, and cleanup outcome.
- Label this mode HUMAN_RECORDED_PHYSICAL_ACOUSTIC; explicitly state that no live user utterance occurred. It must not impersonate operator confirmation or independent G23 validation.
- Preserve the existing live-operator route. No main mutation, merge, auto-certification, or downstream gate promotion is authorized.

### Acceptance rule

The automated fixture is a physical acoustic stimulus, not a synthetic or virtual audio substitute. CP-07 remains OPEN/HOLD until the full candidate-bound route passes all content, hardware, memory, provenance, cleanup, and security checks. Any code or contract change invalidates evidence tied to a prior candidate SHA. The first run is non-certifying; G23 and G24 remain separate.


### Pinned initial fixture and attribution

The initial fixture is **Hola_fer.wav** by **leoncillo**, licensed CC0-1.0. Source page: https://freesound.org/people/leoncillo/sounds/423843/. Downloaded preview: https://cdn.freesound.org/previews/423/423843_3215099-lq.mp3. The verified MP3 preview SHA-256 is `1aa9fcf9a210c256a15a6f8682eeda65b17fd86ba3e37873303d5b9a60b972cf`. The reference token is `hola`; it is a minimal content anchor from the clip title/description, not a claim of full transcription. Hosted CI verifies the source hash, normalizes to PCM16 mono 16 kHz WAV, calculates the normalized-fixture hash, and binds the manifest to the candidate SHA/run before transfer to the physical runner.


### Acoustic threshold consistency note (2026-10-12)

The runtime's acoustic-energy floor is `max(250 RMS, baseline_peak_rms × 1.10)`, followed by the unchanged output-speech recognition gate requiring at least two matching tokens and overlap ratio ≥ 0.30. The independent evidence validator and workflow post-validation now use the same 1.10× energy floor; their prior 1.5× check was stale relative to the already-implemented runtime. Acoustic energy alone is never sufficient to pass the gate.
