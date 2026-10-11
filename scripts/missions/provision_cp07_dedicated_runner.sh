#!/usr/bin/env bash
# Provision a SEPARATE Linux host with physical microphone + speakers for Louksna CP-07.
# Never run this on the workstation under test. It registers a dedicated GitHub Actions runner.
set -Eeuo pipefail
umask 077

readonly REPO_URL="https://github.com/Plomillo/luna-linux-bridge"
readonly RUNNER_LABEL="louksna-voice-hw-dedicated"
readonly HOME_ROOT="${HOME:?Run as the dedicated, non-root runner account}"
readonly RUNNER_DIR="$HOME_ROOT/actions-runner-louksna-cp07"
readonly VOICE_ROOT="$HOME_ROOT/.local/share/louksna-cp07"
readonly EVIDENCE_DIR="$HOME_ROOT/.local/state/louksna-cp07"
: "${RUNNER_REGISTRATION_TOKEN:?Set a short-lived repository runner registration token in this separate host's shell; never commit or paste it}"
if [[ "$(id -u)" == 0 ]]; then echo "Run as a dedicated non-root user; sudo is used only for package installation/service setup." >&2; exit 2; fi
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then echo "Requires Linux x86_64." >&2; exit 2; fi

sudo -n true 2>/dev/null || { echo "Configure sudo for this dedicated host before provisioning." >&2; exit 2; }
export DEBIAN_FRONTEND=noninteractive
sudo -E apt-get -o Acquire::Retries=3 update
sudo -E apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
  ca-certificates curl jq git tar xz-utils build-essential cmake pkg-config \
  libssl-dev libasound2-dev python3 python3-venv pipx alsa-utils pulseaudio-utils \
  pipewire pipewire-pulse wireplumber

mkdir -p "$VOICE_ROOT/whisper.cpp/models" "$VOICE_ROOT/models" "$EVIDENCE_DIR"
chmod 700 "$VOICE_ROOT" "$EVIDENCE_DIR"
export PATH="$HOME_ROOT/.local/bin:$PATH"
grep -qxF 'export PATH="$HOME/.local/bin:$PATH"' "$HOME_ROOT/.profile" 2>/dev/null || echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME_ROOT/.profile"

# Install a versioned Whisper.cpp build and the multilingual model (Spanish is forced by CP-07).
if [[ ! -d "$VOICE_ROOT/whisper.cpp/.git" ]]; then
  git clone --depth 1 --branch v1.7.6 https://github.com/ggml-org/whisper.cpp.git "$VOICE_ROOT/whisper.cpp"
else
  git -C "$VOICE_ROOT/whisper.cpp" fetch --depth 1 origin tag v1.7.6
  git -C "$VOICE_ROOT/whisper.cpp" checkout --detach v1.7.6
fi
cmake -S "$VOICE_ROOT/whisper.cpp" -B "$VOICE_ROOT/whisper.cpp/build" -DCMAKE_BUILD_TYPE=Release
cmake --build "$VOICE_ROOT/whisper.cpp/build" --config Release -j2
install -m 0755 "$VOICE_ROOT/whisper.cpp/build/bin/whisper-cli" "$HOME_ROOT/.local/bin/whisper-cli"
curl --fail --location --retry 3 --output "$VOICE_ROOT/whisper.cpp/models/ggml-base.bin" \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-base.bin

# Piper is installed from its published Python package; model and config come from the official voice repository.
python3 -m pipx ensurepath
pipx install --force piper-tts
curl --fail --location --retry 3 --output "$VOICE_ROOT/models/es_ES-sharvard-medium.onnx" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx
curl --fail --location --retry 3 --output "$VOICE_ROOT/models/es_ES-sharvard-medium.onnx.json" \
  https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json

# Install local inference runtime without using a remote API during the voice test.
if ! command -v ollama >/dev/null 2>&1; then
  OLLAMA_INSTALLER="$(mktemp)"
  curl --fail --location --retry 3 https://ollama.com/install.sh --output "$OLLAMA_INSTALLER"
  bash "$OLLAMA_INSTALLER"
  rm -f "$OLLAMA_INSTALLER"
fi
sudo systemctl enable --now ollama
ollama pull smollm2:360m

# Start the user audio stack; require real capture and playback devices before runner registration.
systemctl --user enable --now pipewire pipewire-pulse wireplumber || true
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"
export PULSE_SERVER="${PULSE_SERVER:-unix:$XDG_RUNTIME_DIR/pulse/native}"
for _ in $(seq 1 20); do pactl info >/dev/null 2>&1 && break; sleep 1; done
arecord -l | tee "$EVIDENCE_DIR/arecord-devices.log"
aplay -l | tee "$EVIDENCE_DIR/aplay-devices.log"
pactl list short sources | tee "$EVIDENCE_DIR/pulse-sources.log"
pactl list short sinks | tee "$EVIDENCE_DIR/pulse-sinks.log"
grep -Eq 'card [0-9]+:' "$EVIDENCE_DIR/arecord-devices.log" || { echo "No physical capture card; refusing to register." >&2; exit 3; }
grep -Eq 'card [0-9]+:' "$EVIDENCE_DIR/aplay-devices.log" || { echo "No physical playback card; refusing to register." >&2; exit 3; }
if grep -Eiq 'loopback|null|dummy|snd-aloop' "$EVIDENCE_DIR/arecord-devices.log" "$EVIDENCE_DIR/aplay-devices.log"; then
  echo "Virtual/loopback audio detected; refusing to register." >&2; exit 3
fi
PULSE_SOURCE="$(pactl list short sources | awk '$2 !~ /\.monitor$/ {print $2; exit}')"
PULSE_SINK="$(pactl list short sinks | awk '$2 !~ /\.monitor$/ {print $2; exit}')"
test -n "$PULSE_SOURCE" && test -n "$PULSE_SINK"
{
  printf 'XDG_RUNTIME_DIR=%s\n' "$XDG_RUNTIME_DIR"
  printf 'PULSE_SERVER=%s\n' "$PULSE_SERVER"
  printf 'PULSE_SOURCE=%s\n' "$PULSE_SOURCE"
  printf 'PULSE_SINK=%s\n' "$PULSE_SINK"
  printf 'LOUKSNA_WHISPER_MODEL=%s\n' "$VOICE_ROOT/whisper.cpp/models/ggml-base.bin"
  printf 'LOUKSNA_PIPER_MODEL=%s\n' "$VOICE_ROOT/models/es_ES-sharvard-medium.onnx"
  printf 'LOUKSNA_OLLAMA_MODEL=smollm2:360m\n'
} > "$EVIDENCE_DIR/audio.env"
chmod 600 "$EVIDENCE_DIR/audio.env"

# Record versions and content digests for traceability before runner registration.
{
  date -u +'%Y-%m-%dT%H:%M:%SZ'
  uname -a
  whisper-cli --help 2>&1 | head -n 2 || true
  piper --help 2>&1 | head -n 2 || true
  ollama --version
  sha256sum "$VOICE_ROOT/whisper.cpp/models/ggml-base.bin" \
    "$VOICE_ROOT/models/es_ES-sharvard-medium.onnx" \
    "$VOICE_ROOT/models/es_ES-sharvard-medium.onnx.json"
} > "$EVIDENCE_DIR/runtime-manifest.txt"

# Download and verify the official GitHub Actions runner release selected by GitHub's latest-release API.
release_json="$(curl --fail --silent --show-error https://api.github.com/repos/actions/runner/releases/latest)"
runner_version="$(jq -r '.tag_name | ltrimstr("v")' <<<"$release_json")"
runner_url="$(jq -r --arg version "$runner_version" '.assets[] | select(.name == ("actions-runner-linux-x64-" + $version + ".tar.gz")) | .browser_download_url' <<<"$release_json" | head -n 1)"
test -n "$runner_version" && test -n "$runner_url"
mkdir -p "$RUNNER_DIR"
curl --fail --location --retry 3 "$runner_url" --output "$RUNNER_DIR/runner.tar.gz"
sha256sum "$RUNNER_DIR/runner.tar.gz" > "$EVIDENCE_DIR/actions-runner-sha256.txt"
tar -xzf "$RUNNER_DIR/runner.tar.gz" -C "$RUNNER_DIR"
rm -f "$RUNNER_DIR/runner.tar.gz"
printf '%s\n' "$runner_version" > "$EVIDENCE_DIR/actions-runner-version.txt"

# Do not print or persist the short-lived registration token.
(
  cd "$RUNNER_DIR"
  ./config.sh --url "$REPO_URL" --token "$RUNNER_REGISTRATION_TOKEN" \
    --name "$(hostname)-louksna-cp07" --labels "$RUNNER_LABEL" \
    --work "_work" --unattended --replace --disableupdate
)
unset RUNNER_REGISTRATION_TOKEN
sudo loginctl enable-linger "$(id -un)"
sudo "$RUNNER_DIR/svc.sh" install "$(id -un)"
sudo "$RUNNER_DIR/svc.sh" start
printf 'Dedicated CP-07 runner registered with label %s. Evidence: %s\n' "$RUNNER_LABEL" "$EVIDENCE_DIR"
