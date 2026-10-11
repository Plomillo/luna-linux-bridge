# CP-07 physical runner implementation record

**Record status:** runner provisioned; supplemental smoke checks passed; full CP-07 remains open pending exact-SHA workflow and operator attestation.  
**Authority:** this record is operational evidence only. It does not certify CP-07, CP-10, G23, or G24.

## 1. Runner discovery and label repair

- Repository: `Plomillo/luna-linux-bridge`
- Existing runner ID: `2`
- Runner name: `luna-linux`
- Platform: Linux x86_64
- Observed status before provisioning: online and idle
- Labels after additive repair: `self-hosted`, `Linux`, `X64`, `luna-aux`, `louksna-voice-hw`
- Mutation: added only `louksna-voice-hw`; preserved all pre-existing labels.
- Runner jobs are restricted to owner-triggered runs and same-repository pull requests. Fork PRs must never execute on this host.

## 2. Physical device route

PipeWire 1.4.2 owns the physical ALSA devices. Direct `plughw` access therefore returned `Device or resource busy`; bypassing PipeWire would be incorrect. The verified route is the ALSA Pulse plugin:

| Role | Exact endpoint |
|---|---|
| Capture | `alsa_input.usb-Generic_Blue_Microphones_2101BAB04QX8-00.pro-input-0` |
| Playback | `alsa_output.pci-0000_04_00.6.analog-stereo` |
| ALSA argument | `pulse` |
| Runtime socket | `unix:/run/user/1000/pulse/native` |

The capture endpoint is a physical Blue Microphones USB input; the playback endpoint is the physical HD-Audio Generic analog output. The workflow verifies these exact endpoints via `pactl`, in addition to listing physical ALSA cards. It rejects null, dummy, and loopback devices.

Supplemental hardware probes:
- Real microphone capture: 2 seconds, 16 kHz mono PCM, 64,044-byte WAV; file deleted immediately after checking.
- Piper output: 3.34-second WAV; physical playback command exited 0; WAV deleted.
- These checks do not establish that the operator heard the output; that confirmation remains pending.

## 3. Installed components and provenance

| Component | Version / identity | SHA-256 |
|---|---|---|
| Whisper.cpp source | tag `v1.7.6`, commit `a8d002cfd879315632a579e73f0148d06959de36` | — |
| Whisper CLI | local build | `955f6c121b718841d66eaef3424dcf4da3f92b90bd5199e3a361d5ccc9142768` |
| Whisper model | `ggml-base.en.bin` | `a03779c86df3323075f5e796cb2ce5029f00ec8869eee3fdfb897afe36c6d002` |
| Piper wheel | `piper-tts 1.8.0` | `25b4d3f31ff70c8fa7151908e00aaa5650cbdf16bca8fcf21299f3941b89a7d3` |
| Piper voice | `en_US-lessac-medium.onnx` | `5efe09e69902187827af646e1a6e9d269dee769f9877d17b16b1b46eeaaf019f` |
| Piper voice config | `en_US-lessac-medium.onnx.json` | `efe19c417bed055f2d69908248c6ba650fa135bc868b0e6abb3da181dab690a0` |
| Ollama archive | official Linux x86_64 archive; runtime reports `0.40.3` | `ce6f8b671a699bf1ebafb28d60dbbabf4f37b30b499145fa308a8ba72de021d6` |
| Ollama executable | `ollama` | `1c66ac15d93ba17f2abe47d93262a62290b2233fb3c9b745564b31fd94815bd7` |
| Local model | `smollm2:360m` | digest `297281b699fc51376006233ca400cd664c4f7b80ed88a47ef084f1e4b089803b` |

The Whisper model passed an offline transcription smoke test using the upstream `samples/jfk.wav`. Piper produced a non-empty PCM WAV. Ollama's local HTTP API returned the requested smoke response using `smollm2:360m`.

## 4. Resource containment

The physical host has approximately 5.7 GiB RAM. Native compilation was moved to the GitHub-hosted build job; only the compiled candidate app/test binary is downloaded to the physical runner. The Ollama server runs as a user systemd service with `TasksMax=256`, `OLLAMA_NUM_PARALLEL=1`, `OLLAMA_MAX_LOADED_MODELS=1`, `OLLAMA_CONTEXT_LENGTH=1024`, and `OLLAMA_KEEP_ALIVE=30s`. The service is outside the Desktop Commander process cgroup, whose 64-task limit had caused Ollama's inference worker to fail with `Resource temporarily unavailable`.

Service unit: `~/.config/systemd/user/louksna-cp07-ollama.service`  
Runtime/model root: `~/.local/share/louksna-cp07/`

## 5. Workflow architecture changes

1. Compile the exact candidate and its Rust voice test binary on `ubuntu-24.04`; do not execute the physical test on the hosted runner.
2. Upload both binaries and a manifest binding their SHA-256 values to the candidate commit.
3. Execute the compiled physical voice test only on runner label `louksna-voice-hw`.
4. Verify the exact PipeWire source/sink, Whisper/Piper models, and local Ollama API before the test.
5. Keep the operator attestation in the required-reviewer GitHub Environment. The operator must listen to the generated response and only then approve.
6. Keep CP-10, G23, and G24 as separate sequential gates. The configured environments are not themselves approvals or certifications.

## 6. Supplemental local result and current gate state

```json
{
  "whisper_sample_transcription": "PASS",
  "piper_synthesis": "PASS",
  "ollama_http_inference": "PASS",
  "physical_microphone_capture": "PASS",
  "physical_playback_command": "PASS",
  "operator_audible_confirmation": "PENDING",
  "exact_candidate_native_voice_e2e": "PENDING",
  "CP-07": "OPEN",
  "CP-10": "NOT_CERTIFIED",
  "G23": "NOT_CERTIFIED",
  "G24": "NOT_CERTIFIED"
}
```

No raw microphone recording or generated WAV is retained from the supplemental probes. The full workflow's SHA-bound artifact and the operator's explicit protected approval are still required for CP-07 PASS.


## 7. Additive acoustic-signal implementation — 2026-10-11

This addendum supersedes the prior statement that protected operator attestation is a prerequisite for the **technical CP-07 signal gate**. Historical operator-attestation requirements remain preserved above as historical rationale; the current candidate workflow uses automated acoustic measurements and keeps human observation optional.

- The production voice path now records a short microphone baseline, records the physical microphone during actual Piper WAV playback, and calculates the maximum 250 ms PCM16 RMS window for each recording.
- The technical gate requires the playback capture peak to be at least `max(250 RMS counts, baseline peak × 1.5)`. Missing/short/invalid capture, capture failure, playback failure, or a signal below threshold fails closed.
- The physical workflow requires `PHYSICAL_VOICE_ACOUSTIC_OUTPUT=PASS`, both numeric RMS measurements, exact candidate SHA, binary/model hashes, complete required log markers, and a matching evidence-log SHA-256 before it promotes CP-07 evidence to PASS.
- The application optionally asks **“¿Escuchaste el audio por los altavoces?”** with Sí/No/No estoy seguro. The response is stored as a separate `SUPPLEMENTAL` ledger event and never changes the technical gate.
- Acoustic energy detection is not a semantic speech-recognition test and does not certify audibility by itself. A missing or inconclusive measurement leaves CP-07 at HOLD. G23 independent validation and G24 certification remain separate.
- The physical workflow now targets the documented existing runner label `louksna-voice-hw`; the earlier `louksna-voice-hw-dedicated` label did not match the runner label recorded in this implementation document.
- No merge, main-branch mutation, CP-10 promotion, G23 validation, G24 certification, or application activation is implied by this source change. Fresh CI, real hardware execution, complete SHA-bound evidence, and independent gates are still required.

## 8. Additive runtime repair and preflight failure analysis — 2026-10-11

- The first exact-SHA physical job reached the dedicated runner but failed at preflight; the real microphone-to-response test was skipped. CP-07 therefore remains HOLD.
- Read-only inspection of runner `LOUKSNA` established the failure source: the workflow's default Spanish Whisper and Piper paths did not exist. The runner had only the English Whisper model and English Piper voice at those paths. The workflow also selected the first non-monitor sink, which was the Blue USB interface output rather than the documented laptop analog playback sink.
- Provisioned the Spanish Whisper base model from the official `ggerganov/whisper.cpp` Hugging Face repository and verified SHA-256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`.
- Provisioned the Spanish Piper `es_ES-sharvard-medium` voice from the official `rhasspy/piper-voices` repository and verified SHA-256 `40febfb1679c69a4505ff311dc136e121e3419a13a290ef264fdf43ddedd0fb1`. Its companion JSON was validated as `es_ES` at 22050 Hz; SHA-256 `7438c9b699c72b0c3388dae1b68d3f364dc66a2150fe554a1c11f03372957b2c`.
- The candidate workflow now selects the documented physical Blue USB microphone source and the laptop analog output sink explicitly, and checks both Spanish model hashes before proceeding. This prevents an English-only model, a missing file, or an unintended USB output sink from silently satisfying preflight.
- PipeWire, PipeWire-Pulse, and WirePlumber were observed active on the host. The initial read-only shell probe without `XDG_RUNTIME_DIR` could not connect to PulseAudio; a subsequent probe with `XDG_RUNTIME_DIR=/run/user/1000` and `PULSE_SERVER=unix:/run/user/1000/pulse/native` successfully enumerated the actual endpoints.
- This repair is a candidate change and runtime provisioning record only. It does not prove the physical E2E has passed. The next workflow must capture the prescribed Spanish phrase from the real microphone, exercise the model and Piper, play to the physical analog sink, re-capture the acoustic output, pass speech-overlap thresholds, and bind evidence to the exact candidate SHA before CP-07 can pass.
