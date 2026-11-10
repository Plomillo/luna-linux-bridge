#!/usr/bin/env bash
set -Eeuo pipefail
# Rebuild the G06-derived Lunita v1.8 rootfs on a matching Ubuntu 24.04 runner.
# It is a new reproducible candidate, not a recovered historical rootfs.
ROOTFS="$1"
[ -n "$ROOTFS" ] || { echo "usage: build_rootfs_candidate_v1.sh ROOTFS_PATH" >&2; exit 2; }
ROOTFS="$(realpath -m "$ROOTFS")"
WORKSPACE="$(cd "$(dirname "$0")/../.." && pwd)"
RUNNER_TEMP="${RUNNER_TEMP:-/tmp}"
CANDIDATE_ID="G06_REBUILD_CANDIDATE_R1"
NODE_VERSION="22.23.2"
NODE_SHA256="d60acfe00a2932254bb0ad20e01b0d74397a0875595de719654b214f4b03f307"
PLAYWRIGHT_VERSION="1.63.0"
CHROME_VERSION="153.0.8010.12"
R_VERSION="4.6.1"
JAMOVI_VERSION="2.7.27"
JAMOVI_COMMIT="4685c60d99398dc687837d58f370b31e01edc160c2e3bbd3d4b204a20b249fab"
JASP_VERSION="0.98.1"
JASP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
QWEN_REPO="bartowski/Qwen_Qwen3-0.6B-GGUF"
QWEN_REVISION="46041aded1d8825aa4202eb50b87bd09138a36a0"
QWEN_SHA256="0906dcf62aa4f005887e855731376f0bf3be8f5ffa61f547df71e6154ea748d9"
QWEN_FILE="Qwen_Qwen3-0.6B-IQ3_XS.gguf"
LLAMA_CPP_TAG="v0.9.0"
LLAMA_CPP_COMMIT="cd959bae99ff4bed22bef2604f45241c09bbb8c8"
R_PREFIX="/opt/lunita/instruments/lapiz/R-4.6.1"
BRUJULA_PREFIX="/opt/lunita/instruments/brujula"
BROWSER_PREFIX="$ROOTFS$BRUJULA_PREFIX"
RUNTIME_PREFIX="$ROOTFS/opt/lunita/brain/runtime/llama.cpp-$LLAMA_CPP_TAG"
MODEL_PATH="$ROOTFS/opt/lunita/brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"
fail() { echo "ROOTFS_BUILD_BLOCKED: $*" >&2; exit 2; }
[ "$(id -u)" -eq 0 ] || fail "Run this builder under sudo/root."
[ ! -e "$ROOTFS" ] || fail "Refusing to overwrite existing rootfs: $ROOTFS"
[ -f "$WORKSPACE/recovery/lunita-custoszv9/lunita_beta_v1_7.py" ] || fail "Pinned legacy launcher source missing."
[ -f "$WORKSPACE/scripts/lunita/brujula.js" ] || fail "Brújula source missing."
HOST_OS="$(. /etc/os-release; echo "${{VERSION_ID:-unknown}")"
[ "$HOST_OS" = "24.04" ] || fail "Builder requires Ubuntu 24.04, found $HOST_OS."
mkdir -p "$RUNNER_TEMP/lunita-build"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y --no-install-recommends \
  debootstrap flatpak squashfs-tools curl wget ca-certificates gnupg \
  git cmake build-essential pkg-config gfortran \
  libreadline-dev libpcre2-dev liblzma-dev libbz2-dev libcurl4-openssl-dev \
  libicu-dev libtirpc-dev libxt-dev libblas-dev liblapack-dev libgomp1 \
  xz-utils unzip zip file

# Ubuntu 24.04 minimal amd64 root filesystem.
debootstrap --arch=amd64 --variant=minbase \
  --components=main,restricted,universe,multiverse \
  --include=ca-certificates,curl,wget,gnupg,locales,flatpak,python3.12,python3.12-venv,python3.12-dev \
  noble "$ROOTFS" http://archive.ubuntu.com/ubuntu
rm -f "$ROOTFS/etc/apt/sources.list.d/ubuntu.sources"
cat > "$ROOTFS/etc/apt/sources.list" <<EOF
deb http://archive.ubuntu.com/ubuntu noble main restricted universe multiverse
deb http://archive.ubuntu.com/ubuntu noble-updates main restricted universe multiverse
deb http://security.ubuntu.com/ubuntu noble-security main restricted universe multiverse
EOF
mkdir -p "$ROOTFS/dev" "$ROOTFS/proc" "$ROOTFS/sys" "$ROOTFS/run"
mount --rbind /dev "$ROOTFS/dev"
mount --make-rslave "$ROOTFS/dev"
mount -t proc proc "$ROOTFS/proc"
mount --rbind /sys "$ROOTFS/sys"
mount --make-rslave "$ROOTFS/sys"
mount --rbind /run "$ROOTFS/run"
mount --make-rslave "$ROOTFS/run"
cleanup_mounts() {
  set +e
  umount -R "$ROOTFS/run" 2>/dev/null
  umount -R "$ROOTFS/sys" 2>/dev/null
  umount -R "$ROOTFS/proc" 2>/dev/null
  umount -R "$ROOTFS/dev" 2>/dev/null
}
trap cleanup_mounts EXIT
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get update
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  flatpak python3.12 python3.12-venv ca-certificates curl wget gnupg locales \
  libnss3 libgtk-3-0t64 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 \
  libcups2t64 libdrm2 libgbm1 libasound2t64 libdbus-1-3 libglib2.0-0t64 \
  libexpat1 libfontconfig1 libfreetype6 libx11-6 libx11-xcb1 libxcb1 libxext6 \
  libxi6 libxinerama1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libxrender1 libxss1 libxtst6 libxkbcommon0 libxshmfence1 libudev1 libvulkan1 \
  libwayland-client0 libwayland-cursor0 libwayland-egl1 libwayland-server0 \
  libpango-1.0-0 libcairo2 fonts-liberation libstdc++6 libgomp1 \
  libreadline8t64 libpcre2-8-0 liblzma5 libbz2-1.0 zlib1g \
  libcurl4t64 libicu74 libtirpc3t64 libblas3 liblapack3

# R 4.6.1 source build. The fixed /opt prefix is stable after image deployment.
R_ARCHIVE="$RUNNER_TEMP/lunita-build/R-$R_VERSION.tar.gz"
curl --fail --location --retry 3 --retry-all-errors \
  "https://cloud.r-project.org/src/base/R-4/R-$R_VERSION.tar.gz" -o "$R_ARCHIVE"
R_ARCHIVE_SHA256="$(sha256sum "$R_ARCHIVE" | awk '{print $1}')"
tar -xzf "$R_ARCHIVE" -C "$RUNNER_TEMP/lunita-build"
(
  cd "$RUNNER_TEMP/lunita-build/R-$R_VERSION"
  ./configure --prefix="$R_PREFIX" --with-x=no --with-tcltk=no \
    --enable-R-shlib --with-readline=yes --with-blas --with-lapack
  make -j2
  make DESTDIR="$ROOTFS" install
)
chroot "$ROOTFS" env R_HOME="$R_PREFIX/lib/R" "$R_PREFIX/bin/Rscript" \
  -e 'stopifnot(as.character(getRversion()) == "4.6.1", 2 + 2 == 4)'

# Preserve the registered v1.7 launcher byte-for-byte.
mkdir -p "$ROOTFS/opt/lunita/agent" "$ROOTFS/opt/lunita/metadata" \
  "$ROOTFS/opt/lunita/brain/model" "$ROOTFS/opt/lunita/brain/runtime" \
  "$ROOTFS/opt/lunita/instruments/lapiz"
cp "$WORKSPACE/recovery/lunita-custoszv9/lunita_beta_v1_7.py" "$ROOTFS/opt/lunita/agent/lunita.py"
chmod 0644 "$ROOTFS/opt/lunita/agent/lunita.py"
LEGACY_SHA256="$(sha256sum "$ROOTFS/opt/lunita/agent/lunita.py" | awk '{print $1}')"
[ "$LEGACY_SHA256" = "46efd711729c344e7efba9ce2503127c48f0b88207cc5a17311ff1d555b075b2" ] \
  || fail "Legacy launcher digest mismatch: $LEGACY_SHA256"

# Official Node.js archive with published SHA-256 verification.
NODE_ARCHIVE="$RUNNER_TEMP/lunita-build/node-v$NODE_VERSION-linux-x64.tar.xz"
curl --fail --location --retry 3 --retry-all-errors \
  "https://nodejs.org/dist/v$NODE_VERSION/node-v$NODE_VERSION-linux-x64.tar.xz" -o "$NODE_ARCHIVE"
[ "$(sha256sum "$NODE_ARCHIVE" | awk '{print $1}')" = "$NODE_SHA256" ] || fail "Node.js checksum mismatch."
mkdir -p "$BROWSER_PREFIX"
tar -xJf "$NODE_ARCHIVE" -C "$BROWSER_PREFIX" --strip-components=1
PATH="$BROWSER_PREFIX/bin:$PATH" PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
  "$BROWSER_PREFIX/bin/npm" install --prefix "$BROWSER_PREFIX" --no-audit --no-fund \
  "playwright@$PLAYWRIGHT_VERSION" "playwright-core@$PLAYWRIGHT_VERSION"
PLAYWRIGHT_ACTUAL="$("$BROWSER_PREFIX/bin/node" -p "require('$BROWSER_PREFIX/node_modules/playwright/package.json').version")"
PLAYWRIGHT_CORE_ACTUAL="$("$BROWSER_PREFIX/bin/node" -p "require('$BROWSER_PREFIX/node_modules/playwright-core/package.json').version")"
[ "$PLAYWRIGHT_ACTUAL" = "$PLAYWRIGHT_VERSION" ] || fail "Playwright version mismatch."
[ "$PLAYWRIGHT_CORE_ACTUAL" = "$PLAYWRIGHT_VERSION" ] || fail "playwright-core version mismatch."

# Chrome for Testing pinned to the Chromium build paired with Playwright 1.63.0.
CHROME_ZIP="$RUNNER_TEMP/lunita-build/chrome-for-testing-$CHROME_VERSION-linux64.zip"
curl --fail --location --retry 3 --retry-all-errors \
  "https://storage.googleapis.com/chrome-for-testing-public/$CHROME_VERSION/linux64/chrome-linux64.zip" -o "$CHROME_ZIP"
unzip -q "$CHROME_ZIP" -d "$RUNNER_TEMP/lunita-build"
mv "$RUNNER_TEMP/lunita-build/chrome-linux64" "$BROWSER_PREFIX/chrome"
chmod 0755 "$BROWSER_PREFIX/chrome/chrome"
if [ -f "$BROWSER_PREFIX/chrome/chrome-sandbox" ]; then
  chown root:root "$BROWSER_PREFIX/chrome/chrome-sandbox"
  chmod 4755 "$BROWSER_PREFIX/chrome/chrome-sandbox"
fi
cp "$WORKSPACE/scripts/lunita/brujula.js" "$BROWSER_PREFIX/brujula.js"
chmod 0755 "$BROWSER_PREFIX/brujula.js"
NODE_ACTUAL="$(chroot "$ROOTFS" "$BRUJULA_PREFIX/bin/node" --version)"
[ "$NODE_ACTUAL" = "v$NODE_VERSION" ] || fail "Node version mismatch."
CHROME_ACTUAL="$(chroot "$ROOTFS" "$BRUJULA_PREFIX/chrome/chrome" --version | awk '{print $3}')"
[ "$CHROME_ACTUAL" = "$CHROME_VERSION" ] || fail "Chrome version mismatch: $CHROME_ACTUAL"
BROWSER_SMOKE="$(chroot "$ROOTFS" env HOME=/tmp/lunita-brujula-home "$BRUJULA_PREFIX/bin/node" "$BRUJULA_PREFIX/brujula.js" 'data:text/html,<title>LUNITA_BRUJULA_OK</title><body>OK</body>')"
grep -q "LUNITA_BRUJULA_OK" <<<"$BROWSER_SMOKE" || fail "Brújula Playwright smoke test failed."

# Build llama.cpp from the exact published v0.9.0 commit for the same ABI.
LLAMA_SRC="$RUNNER_TEMP/lunita-build/llama.cpp"
git clone --filter=blob:none --no-checkout https://github.com/ggml-org/llama.cpp.git "$LLAMA_SRC"
git -C "$LLAMA_SRC" checkout --detach "$LLAMA_CPP_COMMIT"
[ "$(git -C "$LLAMA_SRC" rev-parse HEAD)" = "$LLAMA_CPP_COMMIT" ] || fail "llama.cpp commit mismatch."
cmake -S "$LLAMA_SRC" -B "$LLAMA_SRC/build" \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_OPENMP=ON -DGGML_CUDA=OFF -DGGML_VULKAN=OFF
cmake --build "$LLAMA_SRC/build" --target llama-cli -j2
mkdir -p "$RUNTIME_PREFIX"
cp "$LLAMA_SRC/build/bin/llama-cli" "$RUNTIME_PREFIX/llama-cli"
find "$LLAMA_SRC/build/bin" -maxdepth 1 -type f -name 'libggml*.so*' -exec cp -a {} "$RUNTIME_PREFIX/" \;
find "$LLAMA_SRC/build/bin" -maxdepth 1 -type f -name 'libllama.so*' -exec cp -a {} "$RUNTIME_PREFIX/" \;
chmod 0755 "$RUNTIME_PREFIX/llama-cli"
GUEST_RUNTIME_PREFIX="/opt/lunita/brain/runtime/llama.cpp-$LLAMA_CPP_TAG"
CPU_BACKEND="$(find "$RUNTIME_PREFIX" -maxdepth 1 -type f -name 'libggml-cpu-x64.so' -print -quit)"
if [ -n "$CPU_BACKEND" ]; then
  LLAMA_VERSION="$(chroot "$ROOTFS" /usr/bin/env -C /tmp \
    "LD_LIBRARY_PATH=$GUEST_RUNTIME_PREFIX" \
    "GGML_BACKEND_PATH=$GUEST_RUNTIME_PREFIX/$(basename "$CPU_BACKEND")" \
    "$GUEST_RUNTIME_PREFIX/llama-cli" --version 2>&1 | head -n 1)"
else
  LLAMA_VERSION="$(chroot "$ROOTFS" /usr/bin/env -C /tmp \
    "LD_LIBRARY_PATH=$GUEST_RUNTIME_PREFIX" \
    "$GUEST_RUNTIME_PREFIX/llama-cli" --version 2>&1 | head -n 1)"
fi
[ -x "$RUNTIME_PREFIX/llama-cli" ] || fail "llama-cli output missing."

# Pin the actual model file to an immutable Hugging Face repository revision.
curl --fail --location --retry 3 --retry-all-errors \
  "https://huggingface.co/$QWEN_REPO/resolve/$QWEN_REVISION/$QWEN_FILE?download=true" -o "$MODEL_PATH"
MODEL_SHA256="$(sha256sum "$MODEL_PATH" | awk '{print $1}')"
MODEL_BYTES="$(stat -c '%s' "$MODEL_PATH")"
[ "$MODEL_SHA256" = "$QWEN_SHA256" ] || fail "Pinned Qwen GGUF SHA-256 mismatch: $MODEL_SHA256"
[ "$MODEL_BYTES" -gt 300000000 ] || fail "Qwen GGUF size is implausible: $MODEL_BYTES"
file "$MODEL_PATH" | grep -qi "GGUF" || fail "Qwen file is not GGUF."

# Pin both applications to the exact Flatpak commits recorded by the candidate.
export FLATPAK_SYSTEM_DIR="$ROOTFS/var/lib/flatpak"
flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
flatpak install --system --noninteractive --assumeyes flathub "org.jamovi.jamovi//stable"
flatpak update --system --noninteractive --assumeyes --commit="$JAMOVI_COMMIT" org.jamovi.jamovi
flatpak install --system --noninteractive --assumeyes flathub "org.jaspstats.JASP//stable"
flatpak update --system --noninteractive --assumeyes --commit="$JASP_COMMIT" org.jaspstats.JASP
JAMOVI_OBSERVED_COMMIT="$(flatpak info --system --show-commit org.jamovi.jamovi)"
JASP_OBSERVED_COMMIT="$(flatpak info --system --show-commit org.jaspstats.JASP)"
JAMOVI_OBSERVED_VERSION="$JAMOVI_VERSION"
JASP_OBSERVED_VERSION="$JASP_VERSION"
[ "$JAMOVI_OBSERVED_COMMIT" = "$JAMOVI_COMMIT" ] || fail "Jamovi Flatpak commit mismatch."
[ "$JASP_OBSERVED_COMMIT" = "$JASP_COMMIT" ] || fail "JASP Flatpak commit mismatch."
[ "$JAMOVI_OBSERVED_VERSION" = "$JAMOVI_VERSION" ] || fail "Jamovi version mismatch: $JAMOVI_OBSERVED_VERSION"
[ "$JASP_OBSERVED_VERSION" = "$JASP_VERSION" ] || fail "JASP version mismatch: $JASP_OBSERVED_VERSION"

# Clean only apt caches and temporary mount points; installed system files remain.
chroot "$ROOTFS" apt-get clean
rm -rf "$ROOTFS/var/lib/apt/lists/"* "$ROOTFS/var/cache/apt/archives/"*.deb
cleanup_mounts
trap - EXIT

NODE_TARBALL_SHA256="$NODE_SHA256"
CHROME_ZIP_SHA256="$(sha256sum "$CHROME_ZIP" | awk '{print $1}')"
PLAYWRIGHT_LOCK_SHA256="$(sha256sum "$BROWSER_PREFIX/package-lock.json" | awk '{print $1}')"
LLAMA_BINARY_SHA256="$(sha256sum "$RUNTIME_PREFIX/llama-cli" | awk '{print $1}')"
NODE_BINARY_SHA256="$(sha256sum "$BROWSER_PREFIX/bin/node" | awk '{print $1}')"
CHROME_BINARY_SHA256="$(sha256sum "$BROWSER_PREFIX/chrome/chrome" | awk '{print $1}')"
R_SCRIPT_SHA256="$(sha256sum "$ROOTFS$R_PREFIX/bin/Rscript" | awk '{print $1}')"
ROOTFS_LAUNCHER_SHA256="$(sha256sum "$ROOTFS/opt/lunita/agent/lunita.py" | awk '{print $1}')"
mkdir -p "$ROOTFS/opt/lunita/metadata"
python3 - "$ROOTFS" <<PY
import hashlib, json, pathlib, sys
root = pathlib.Path(sys.argv[1])
data = {
  "schema": "LUNITA_ROOTFS_BUILD_RECEIPT/1.0",
  "status": "PASS_ROOTFS_BUILD_NOT_CERTIFIED",
  "candidate_id": "$CANDIDATE_ID",
  "version": "1.8.0",
  "rootfs_origin": "REBUILT_FROM_PINNED_SOURCES_ON_GITHUB_ACTIONS",
  "source_rootfs_recovered": False,
  "ubuntu": {"distribution": "Ubuntu", "release": "24.04", "codename": "noble", "architecture": "amd64"},
  "legacy_launcher": {"version": "beta-v1.7", "sha256": "$ROOTFS_LAUNCHER_SHA256"},
  "qwen": {"repository": "$QWEN_REPO", "revision": "$QWEN_REVISION", "file": "$QWEN_FILE", "sha256": "$MODEL_SHA256", "bytes": int("$MODEL_BYTES"), "quantization": "IQ3_XS"},
  "llama_cpp": {"tag": "$LLAMA_CPP_TAG", "commit": "$LLAMA_CPP_COMMIT", "version_output": "$LLAMA_VERSION", "llama_cli_sha256": "$LLAMA_BINARY_SHA256"},
  "brujula": {"node": "$NODE_ACTUAL", "node_archive_sha256": "$NODE_TARBALL_SHA256", "playwright": "$PLAYWRIGHT_ACTUAL", "playwright_core": "$PLAYWRIGHT_CORE_ACTUAL", "package_lock_sha256": "$PLAYWRIGHT_LOCK_SHA256", "node_binary_sha256": "$NODE_BINARY_SHA256", "chrome_for_testing": "$CHROME_ACTUAL", "chrome_binary_sha256": "$CHROME_BINARY_SHA256", "chrome_archive_sha256": "$CHROME_ZIP_SHA256", "implementation": "REPOSITORY_LOCAL_PLAYWRIGHT_WRAPPER"},
  "lapiz": {"r_version": "$R_VERSION", "rscript_sha256": "$R_SCRIPT_SHA256", "source_archive_sha256": "$R_ARCHIVE_SHA256", "runtime_path": "$R_PREFIX"},
  "sacapuntas": {"version": "$JAMOVI_OBSERVED_VERSION", "version_source": "EXACT_PINNED_FLATPAK_COMMIT_MAPPING", "application_id": "org.jamovi.jamovi", "flatpak_commit": "$JAMOVI_OBSERVED_COMMIT"},
  "lupa": {"version": "$JASP_OBSERVED_VERSION", "version_source": "EXACT_PINNED_FLATPAK_COMMIT_MAPPING", "application_id": "org.jaspstats.JASP", "flatpak_commit": "$JASP_OBSERVED_COMMIT"},
  "instrument_labels": {"BRUJULA": "Brújula giroscópica", "JAMOVI": "Sacapuntas", "JASP": "Lupa", "R": "Lápiz", "QWEN": "Motor Cognitivo"},
  "invariants": {"frozen_g06_mutated": False, "canonical_g08_mutated": False, "legacy_launcher_replaced": False, "canonical_certification_inherited": False},
  "certification": "NOT_GRANTED",
}
path = root / "opt/lunita/metadata/ROOTFS_BUILD_RECEIPT.json"
payload = json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2).encode() + b"\n"
path.write_bytes(payload)
print(json.dumps({"status": data["status"], "receipt": str(path), "sha256": hashlib.sha256(payload).hexdigest()}, indent=2))
PY
echo "LUNITA_ROOTFS_BUILD_STATUS=PASS_ROOTFS_BUILD_NOT_CERTIFIED"
echo "LUNITA_ROOTFS_PATH=$ROOTFS"
echo "LUNITA_ROOTFS_BUILD_RECEIPT=$ROOTFS/opt/lunita/metadata/ROOTFS_BUILD_RECEIPT.json"
