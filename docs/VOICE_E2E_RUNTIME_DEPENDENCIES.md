# LOUKSNA ZD V0.3 — Voice E2E Runtime Dependencies

Status: IMPLEMENTED IN SOURCE / CP-07 OPEN / NOT CERTIFIED
Scope: Linux desktop candidate; no bundled model weights or hidden downloads.

## Data path

1. `arecord` captures mono signed 16-bit PCM at 16 kHz for at most 8 seconds.
2. `whisper-cli` from whisper.cpp transcribes the captured WAV with the configured local Whisper model.
3. The Rust backend sends the transcript to an Ollama-compatible `/api/chat` endpoint. Default endpoint is `http://127.0.0.1:11434/api/chat`; plain HTTP is restricted to loopback and HTTPS is permitted.
4. `piper` synthesizes the response into a WAV file with the configured Piper model.
5. `aplay` plays the generated WAV through the selected ALSA output.
6. The application writes a status-only event `EXECUTED_NOT_CERTIFIED` to its SQLite evidence ledger (never a certification PASS). It does not write audio, transcript, response text, or credentials to that ledger. Temporary audio/response working files are removed on scope exit (best-effort filesystem cleanup); the transcript remains in memory only.

## Required runtime components

| Component | Required executable/service | Purpose |
|---|---|---|
| ALSA utilities | `arecord`, `aplay` | Physical microphone capture and speaker/headphone playback |
| whisper.cpp | `whisper-cli` | Local speech-to-text |
| Whisper model | File at `LOUKSNA_WHISPER_MODEL` | STT model weights |
| Piper TTS | `piper` | Local text-to-speech |
| Piper voice model | File at `LOUKSNA_PIPER_MODEL` | TTS weights/configuration |
| Ollama | Local service, normally port 11434 | Response generation |
| Ollama model | `LOUKSNA_OLLAMA_MODEL` | Response model |
| Rust dependency | `wait-timeout = 0.2` | Bounded subprocess waits |

On Debian-based systems, `alsa-utils` provides the ALSA CLI utilities. Build/install whisper.cpp and Piper only from trusted upstream releases or source commits that the deployment record pins. Ollama and the required model must be installed/provisioned explicitly. Package names and availability for whisper.cpp/Piper vary by distribution; do not assume that a package name resolves to the intended upstream binary.

## Configuration

Set these environment variables for the process launching the desktop application:

- `LOUKSNA_WHISPER_MODEL=/absolute/path/to/whisper-model.bin`
- `LOUKSNA_PIPER_MODEL=/absolute/path/to/piper-voice.onnx`
- `LOUKSNA_OLLAMA_MODEL=<exact-model-tag-from-ollama-list>`
- Optional: `LOUKSNA_VOICE_OLLAMA_URL=http://127.0.0.1:11434/api/chat` (loopback HTTP only by default).

Piper model distributions may require a companion configuration file. Provision that file alongside the model according to the exact upstream release; if the selected Piper build requires a different invocation, adapt and test the integration explicitly rather than marking the preflight as passed.

## Preflight and physical test checklist

Run the app's **Comprobar dependencias** action. A `READY` preflight only means the expected executables, model paths, and endpoint configuration are present; it is not E2E evidence.

Before a physical test, record:

- candidate branch and full commit SHA;
- OS/kernel/desktop, audio server, ALSA capture/playback device identifiers;
- `arecord --version`, `aplay --version`, whisper.cpp version/commit, Piper version, Ollama version;
- exact Ollama model tag and SHA-256 of both model files and relevant config files;
- trusted upstream source URLs/release identifiers and SHA-256 of installed binaries where applicable;
- actual preflight output and status-only ledger event;
- capture success, non-empty transcription, successful response HTTP status, non-empty TTS WAV, successful playback exit status, elapsed times, and cleanup check;
- any failure, logs with secrets/transcript/audio excluded, rollback pointer, and independent reviewer.

Use only the **Grabar 8 s y responder por voz** action for the end-to-end test. Do not feed prerecorded or generated audio as if it were microphone evidence. The test passes only when a real microphone is captured and the generated response is audibly played through real output hardware.

## Governance

- CP-07 remains `OPEN / HOLD` until the complete pipeline above has been exercised and evidenced on physical audio hardware.
- Hosted CI, static checks, unit tests, and QEMU do not demonstrate microphone/speaker operation.
- No PASS is inferred from source presence or a `READY` preflight. A successful voice command records `EXECUTED_NOT_CERTIFIED`, not `PASS`; G23/G24 remain separate decisions.
- CP-10 and G23/G24 remain blocked while voice is mandatory and CP-07 is open.
- Any change to the candidate SHA invalidates evidence/checkpoints tied to the prior SHA.
