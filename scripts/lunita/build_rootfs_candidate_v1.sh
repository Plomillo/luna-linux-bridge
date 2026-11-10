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
QWEN_REVISION="f9184d8b4c371cb52af5b8cb3d38e55e3cf0f4a0"
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
HOST_OS="$(. /etc/os-release; echo "${VERSION_ID:-unknown}")"
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
if ! debootstrap --arch=amd64 --variant=minbase \
  --components=main,restricted,universe,multiverse \
  --include=ca-certificates,curl,wget,gnupg,locales,python3-minimal,python3.12,python3.12-venv,python3.12-dev \
  noble "$ROOTFS" http://archive.ubuntu.com/ubuntu; then
  echo "DEBOOTSTRAP_FAILED: final log excerpt follows" >&2
  tail -n 160 "$ROOTFS/debootstrap/debootstrap.log" >&2 || true
  fail "Ubuntu Noble minimal bootstrap failed."
fi
# Ubuntu's /tmp must retain the standard root-owned sticky, world-writable mode.
# This is required by real runtime temporary-file operations after pivot_root.
[ -d "$ROOTFS/tmp" ] || fail "Ubuntu rootfs /tmp directory is missing."
chmod 1777 "$ROOTFS/tmp"
TMP_DIRECTORY_MODE="$(stat -c '%a' "$ROOTFS/tmp")"
[ "$TMP_DIRECTORY_MODE" = "1777" ] || fail "Ubuntu rootfs /tmp mode must be 1777, found $TMP_DIRECTORY_MODE."
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
  flatpak python3-minimal python3.12 python3.12-venv ca-certificates curl wget gnupg locales \
  libnss3 libgtk-3-0t64 libatk1.0-0t64 libatk-bridge2.0-0t64 libatspi2.0-0t64 \
  libcups2t64 libdrm2 libgbm1 libasound2t64 libdbus-1-3 libglib2.0-0t64 \
  libexpat1 libfontconfig1 libfreetype6 libx11-6 libx11-xcb1 libxcb1 libxext6 \
  libxi6 libxinerama1 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
  libxrender1 libxss1 libxtst6 libxkbcommon0 libxshmfence1 libudev1 libvulkan1 \
  libwayland-client0 libwayland-cursor0 libwayland-egl1 libwayland-server0 \
  libpango-1.0-0 libcairo2 fonts-liberation libstdc++6 libgomp1 \
  libreadline8t64 libpcre2-8-0 liblzma5 libbz2-1.0 zlib1g \
  libcurl4t64 libicu74 libtirpc3t64 libblas3 liblapack3 libgfortran5 libquadmath0 passwd util-linux
SYSTEM_PYTHON_ALIAS="$(readlink "$ROOTFS/usr/bin/python3")"
[ "$SYSTEM_PYTHON_ALIAS" = "python3.12" ] || fail "Ubuntu system python3 alias is not bound to python3.12: $SYSTEM_PYTHON_ALIAS"
SYSTEM_PYTHON_VERSION="$(chroot "$ROOTFS" /usr/bin/python3 --version)"
[[ "$SYSTEM_PYTHON_VERSION" == "Python 3.12."* ]] || fail "Ubuntu system python3 compatibility runtime mismatch: $SYSTEM_PYTHON_VERSION"
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  build-essential cmake pkg-config gfortran \
  libreadline-dev libpcre2-dev liblzma-dev libbz2-dev libcurl4-openssl-dev \
  libicu-dev libtirpc-dev libblas-dev liblapack-dev

# Desktop application smoke tests must execute as the candidate's regular user.
chroot "$ROOTFS" useradd --uid 1000 --create-home --user-group --shell /bin/bash lunita
# The XDG parent and every prepared child must belong to the runtime user.
# Otherwise later append-only audit creation fails with EACCES in the chroot.
chroot "$ROOTFS" install -d -o 1000 -g 1000 -m 0700 /tmp/lunita-xdg
chroot "$ROOTFS" install -d -o 1000 -g 1000 -m 0700 \
  /tmp/lunita-xdg/cache /tmp/lunita-xdg/config /tmp/lunita-xdg/data /tmp/lunita-xdg/audit
chroot "$ROOTFS" install -d -o 1000 -g 1000 -m 0700 /run/lunita-runtime-1000

# R 4.6.1 is compiled inside Ubuntu 24.04 to bind its ELF dependencies
# to Noble's glibc and runtime libraries, never to the GitHub host ABI.
R_ARCHIVE="$RUNNER_TEMP/lunita-build/R-$R_VERSION.tar.gz"
curl --fail --location --retry 3 --retry-all-errors \
  "https://cloud.r-project.org/src/base/R-4/R-$R_VERSION.tar.gz" -o "$R_ARCHIVE"
R_ARCHIVE_SHA256="$(sha256sum "$R_ARCHIVE" | awk '{print $1}')"
cp "$R_ARCHIVE" "$ROOTFS/tmp/R-$R_VERSION.tar.gz"
chroot "$ROOTFS" /bin/bash -euc "
  tar -xzf /tmp/R-$R_VERSION.tar.gz -C /tmp
  cd /tmp/R-$R_VERSION
  ./configure --prefix='$R_PREFIX' --with-x=no --with-tcltk=no \\
    --enable-R-shlib --with-readline=yes --with-blas --with-lapack
  make -j2
  make install
  rm -rf /tmp/R-$R_VERSION /tmp/R-$R_VERSION.tar.gz
"
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
NODE_PREFIX="$BROWSER_PREFIX/node"
mkdir -p "$NODE_PREFIX"
tar -xJf "$NODE_ARCHIVE" -C "$NODE_PREFIX" --strip-components=1
PATH="$NODE_PREFIX/bin:$PATH" PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=1 \
  "$NODE_PREFIX/bin/npm" install --prefix "$BROWSER_PREFIX" --no-audit --no-fund \
  "playwright@$PLAYWRIGHT_VERSION" "playwright-core@$PLAYWRIGHT_VERSION"
PLAYWRIGHT_ACTUAL="$("$NODE_PREFIX/bin/node" -p "require('$BROWSER_PREFIX/node_modules/playwright/package.json').version")"
PLAYWRIGHT_CORE_ACTUAL="$("$NODE_PREFIX/bin/node" -p "require('$BROWSER_PREFIX/node_modules/playwright-core/package.json').version")"
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
NODE_ACTUAL="$(chroot "$ROOTFS" "$BRUJULA_PREFIX/node/bin/node" --version)"
[ "$NODE_ACTUAL" = "v$NODE_VERSION" ] || fail "Node version mismatch."
CHROME_ACTUAL="$(chroot "$ROOTFS" "$BRUJULA_PREFIX/chrome/chrome" --version | awk '{print $NF}')"
[ "$CHROME_ACTUAL" = "$CHROME_VERSION" ] || fail "Chrome version mismatch: $CHROME_ACTUAL"
BROWSER_SMOKE="$(chroot "$ROOTFS" /usr/sbin/runuser -u lunita -- /usr/bin/env \
  HOME=/home/lunita \
  XDG_CACHE_HOME=/tmp/lunita-xdg/cache \
  XDG_CONFIG_HOME=/tmp/lunita-xdg/config \
  XDG_DATA_HOME=/tmp/lunita-xdg/data \
  XDG_RUNTIME_DIR=/run/lunita-runtime-1000 \
  "$BRUJULA_PREFIX/node/bin/node" "$BRUJULA_PREFIX/brujula.js" \
  'data:text/html,<title>LUNITA_BRUJULA_OK</title><body>OK</body>')"
grep -q "LUNITA_BRUJULA_OK" <<<"$BROWSER_SMOKE" || fail "Brújula Playwright smoke test failed."

# Build the pinned llama.cpp commit inside the Ubuntu 24.04 target. This
# prevents a runner-host glibc/toolchain ABI from leaking into the rootfs.
LLAMA_SRC="$RUNNER_TEMP/lunita-build/llama.cpp"
git clone --filter=blob:none --no-checkout https://github.com/ggml-org/llama.cpp.git "$LLAMA_SRC"
git -C "$LLAMA_SRC" checkout --detach "$LLAMA_CPP_COMMIT"
[ "$(git -C "$LLAMA_SRC" rev-parse HEAD)" = "$LLAMA_CPP_COMMIT" ] || fail "llama.cpp commit mismatch."
mkdir -p "$ROOTFS/tmp/llama.cpp-src"
git -C "$LLAMA_SRC" archive --format=tar "$LLAMA_CPP_COMMIT" | tar -xf - -C "$ROOTFS/tmp/llama.cpp-src"
chroot "$ROOTFS" cmake -S /tmp/llama.cpp-src -B /tmp/llama.cpp-build \
  -DCMAKE_BUILD_TYPE=Release -DGGML_NATIVE=OFF -DGGML_OPENMP=ON -DGGML_CUDA=OFF -DGGML_VULKAN=OFF
chroot "$ROOTFS" cmake --build /tmp/llama.cpp-build --target llama-cli -j2
mkdir -p "$RUNTIME_PREFIX"
cp "$ROOTFS/tmp/llama.cpp-build/bin/llama-cli" "$RUNTIME_PREFIX/llama-cli"
# Keep every shared library produced for llama-cli beside the executable.
# v0.9.0 uses libllama-cli-impl.so in addition to libllama/libggml;
# copying only the latter leaves a binary that works in the build tree but
# fails after the temporary CMake directory is removed.
find "$ROOTFS/tmp/llama.cpp-build/bin" -maxdepth 1 \
  \( -type f -o -type l \) \
  \( -name 'lib*.so' -o -name 'lib*.so.*' \) \
  -exec cp -a {} "$RUNTIME_PREFIX/" \;
chmod 0755 "$RUNTIME_PREFIX/llama-cli"
GUEST_RUNTIME_PREFIX="/opt/lunita/brain/runtime/llama.cpp-$LLAMA_CPP_TAG"
[ -x "$RUNTIME_PREFIX/llama-cli" ] || fail "llama-cli output missing."
CPU_BACKEND="$RUNTIME_PREFIX/libggml-cpu.so"
if [ ! -f "$CPU_BACKEND" ]; then
  CPU_BACKEND="$RUNTIME_PREFIX/libggml-cpu-x64.so"
fi
[ -f "$CPU_BACKEND" ] || fail "Pinned llama.cpp CPU backend library is missing (expected libggml-cpu.so or legacy libggml-cpu-x64.so)."
find "$RUNTIME_PREFIX" -maxdepth 1 -type f \
  \( -name 'lib*.so' -o -name 'lib*.so.*' \) -print -quit | grep -q . \
  || fail "llama.cpp runtime shared libraries were not packaged."

# Remove the build tree before verification: the packaged runtime must not
# accidentally resolve CMake build-tree libraries through an absolute RPATH.
rm -rf "$ROOTFS/tmp/llama.cpp-src" "$ROOTFS/tmp/llama.cpp-build"
LLAMA_LDD="$(chroot "$ROOTFS" /usr/bin/env -C /tmp \
  "LD_LIBRARY_PATH=$GUEST_RUNTIME_PREFIX" \
  /usr/bin/ldd "$GUEST_RUNTIME_PREFIX/llama-cli" 2>&1)" \
  || fail "Unable to inspect packaged llama-cli dependencies: $LLAMA_LDD"
if grep -Fq "not found" <<<"$LLAMA_LDD"; then
  fail "Packaged llama.cpp runtime has unresolved shared libraries: $LLAMA_LDD"
fi
LLAMA_VERSION="$(chroot "$ROOTFS" /usr/bin/env -C /tmp \
  "LD_LIBRARY_PATH=$GUEST_RUNTIME_PREFIX" \
  "GGML_BACKEND_PATH=$GUEST_RUNTIME_PREFIX/$(basename "$CPU_BACKEND")" \
  "$GUEST_RUNTIME_PREFIX/llama-cli" --version 2>&1 | head -n 1)"

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

# Remove temporary build toolchains only after the ABI-matched builds and checks.
chroot "$ROOTFS" env DEBIAN_FRONTEND=noninteractive apt-get purge -y --auto-remove \
  build-essential cmake pkg-config gfortran \
  libreadline-dev libpcre2-dev liblzma-dev libbz2-dev libcurl4-openssl-dev \
  libicu-dev libtirpc-dev libblas-dev liblapack-dev
# Clean only apt caches and temporary mount points; installed runtime files remain.
chroot "$ROOTFS" apt-get clean
rm -rf "$ROOTFS/var/lib/apt/lists/"* "$ROOTFS/var/cache/apt/archives/"*.deb
cleanup_mounts
trap - EXIT

NODE_TARBALL_SHA256="$NODE_SHA256"
CHROME_ZIP_SHA256="$(sha256sum "$CHROME_ZIP" | awk '{print $1}')"
PLAYWRIGHT_LOCK_SHA256="$(sha256sum "$BROWSER_PREFIX/package-lock.json" | awk '{print $1}')"
LLAMA_BINARY_SHA256="$(sha256sum "$RUNTIME_PREFIX/llama-cli" | awk '{print $1}')"
NODE_BINARY_SHA256="$(sha256sum "$NODE_PREFIX/bin/node" | awk '{print $1}')"
CHROME_BINARY_SHA256="$(sha256sum "$BROWSER_PREFIX/chrome/chrome" | awk '{print $1}')"
R_SCRIPT_SHA256="$(sha256sum "$ROOTFS$R_PREFIX/bin/Rscript" | awk '{print $1}')"
ROOTFS_LAUNCHER_SHA256="$(sha256sum "$ROOTFS/opt/lunita/agent/lunita.py" | awk '{print $1}')"
mkdir -p "$ROOTFS/opt/lunita/metadata"
# Add the requested identity hierarchy as separate metadata. The pre-existing
# instrument_labels receipt entries below are deliberately retained verbatim.
python3 - "$ROOTFS" <<'PY'
import hashlib, json, os, pathlib, sys
root = pathlib.Path(sys.argv[1])
metadata = root / "opt/lunita/metadata"
tree_text = """LA PIEZA
└── EL ESTUCHE
    └── UBUNTU 24.04 LTS MINIMAL
        └── LUNITA LA INVESTIGADORA
            ├── MOTOR COGNITIVO
            │   └── Qwen3-0.6B IQ3_XS GGUF
            │
            ├── BRÚJULA GIROSCÓPICA
            │   ├── Node.js 22.23.2
            │   ├── Playwright 1.63.0
            │   ├── playwright-core 1.63.0
            │   └── Chrome for Testing 153.0.8010.12
            │
            ├── LÁPIZ
            │   └── R 4.6.1
            │
            ├── SACAPUNTAS
            │   └── jamovi 2.7.27
            │
            └── LUPA
                └── JASP 0.98.1
"""
hierarchy = {
  "label": "LA PIEZA",
  "children": [{
    "label": "EL ESTUCHE",
    "children": [{
      "label": "UBUNTU 24.04 LTS MINIMAL",
      "children": [{
        "label": "LUNITA LA INVESTIGADORA",
        "children": [
          {"label": "MOTOR COGNITIVO", "children": [
            {"label": "Qwen3-0.6B IQ3_XS GGUF",
             "path": "/opt/lunita/brain/model/Qwen_Qwen3-0.6B-IQ3_XS.gguf"}
          ]},
          {"label": "BRÚJULA GIROSCÓPICA", "children": [
            {"label": "Node.js 22.23.2", "path": "/opt/lunita/instruments/brujula/node/bin/node"},
            {"label": "Playwright 1.63.0", "path": "/opt/lunita/instruments/brujula/node_modules/playwright"},
            {"label": "playwright-core 1.63.0", "path": "/opt/lunita/instruments/brujula/node_modules/playwright-core"},
            {"label": "Chrome for Testing 153.0.8010.12", "path": "/opt/lunita/instruments/brujula/chrome/chrome"}
          ]},
          {"label": "LÁPIZ", "children": [
            {"label": "R 4.6.1", "path": "/opt/lunita/instruments/lapiz/R-4.6.1/bin/Rscript"}
          ]},
          {"label": "SACAPUNTAS", "children": [
            {"label": "jamovi 2.7.27", "application_id": "org.jamovi.jamovi"}
          ]},
          {"label": "LUPA", "children": [
            {"label": "JASP 0.98.1", "application_id": "org.jaspstats.JASP"}
          ]}
        ]
      }]
    }]
  }]
}
document = {
  "schema": "LUNITA_LABEL_HIERARCHY/1.0",
  "candidate_id": "G06_REBUILD_CANDIDATE_R1",
  "version": "1.8.0",
  "preservation_policy": "APPEND_ONLY;DO_NOT_REWRITE_EXISTING_LABELS",
  "hierarchy": hierarchy,
  "rendered_tree": tree_text,
}
json_path = metadata / "LUNITA_LABEL_HIERARCHY.json"
text_path = metadata / "LUNITA_LABEL_HIERARCHY.txt"
json_payload = (json.dumps(document, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8")
text_payload = tree_text.encode("utf-8")
def create_or_preserve(path, payload, label):
    if path.exists():
        if not path.is_file() or path.is_symlink() or path.read_bytes() != payload:
            raise SystemExit(f"BLOCKED: existing {label} differs; it was not rewritten.")
        return
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
create_or_preserve(json_path, json_payload, "label hierarchy JSON")
create_or_preserve(text_path, text_payload, "label hierarchy tree")
print(json.dumps({
  "status": "PASS_LABEL_HIERARCHY_ADDED_OR_PRESERVED",
  "json_sha256": hashlib.sha256(json_payload).hexdigest(),
  "text_sha256": hashlib.sha256(text_payload).hexdigest(),
}, sort_keys=True))
PY
LABEL_HIERARCHY_SHA256="$(sha256sum "$ROOTFS/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.json" | awk '{print $1}')"
LABEL_HIERARCHY_TEXT_SHA256="$(sha256sum "$ROOTFS/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.txt" | awk '{print $1}')"
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
  "filesystem_permissions": {"tmp_directory": {"path": "/tmp", "uid": 0, "gid": 0, "mode_octal": "01777"}},
  "system_python": {"default_executable": "/usr/bin/python3", "symlink_target": "$SYSTEM_PYTHON_ALIAS", "version_output": "$SYSTEM_PYTHON_VERSION"},
  "legacy_launcher": {"version": "beta-v1.7", "sha256": "$ROOTFS_LAUNCHER_SHA256"},
  "qwen": {"repository": "$QWEN_REPO", "revision": "$QWEN_REVISION", "file": "$QWEN_FILE", "sha256": "$MODEL_SHA256", "bytes": int("$MODEL_BYTES"), "quantization": "IQ3_XS"},
  "llama_cpp": {"tag": "$LLAMA_CPP_TAG", "commit": "$LLAMA_CPP_COMMIT", "version_output": "$LLAMA_VERSION", "llama_cli_sha256": "$LLAMA_BINARY_SHA256"},
  "brujula": {"node": "$NODE_ACTUAL", "node_archive_sha256": "$NODE_TARBALL_SHA256", "playwright": "$PLAYWRIGHT_ACTUAL", "playwright_core": "$PLAYWRIGHT_CORE_ACTUAL", "package_lock_sha256": "$PLAYWRIGHT_LOCK_SHA256", "node_binary_sha256": "$NODE_BINARY_SHA256", "chrome_for_testing": "$CHROME_ACTUAL", "chrome_binary_sha256": "$CHROME_BINARY_SHA256", "chrome_archive_sha256": "$CHROME_ZIP_SHA256", "implementation": "REPOSITORY_LOCAL_PLAYWRIGHT_WRAPPER"},
  "lapiz": {"r_version": "$R_VERSION", "rscript_sha256": "$R_SCRIPT_SHA256", "source_archive_sha256": "$R_ARCHIVE_SHA256", "runtime_path": "$R_PREFIX"},
  "sacapuntas": {"version": "$JAMOVI_OBSERVED_VERSION", "version_source": "EXACT_PINNED_FLATPAK_COMMIT_MAPPING", "application_id": "org.jamovi.jamovi", "flatpak_commit": "$JAMOVI_OBSERVED_COMMIT"},
  "lupa": {"version": "$JASP_OBSERVED_VERSION", "version_source": "EXACT_PINNED_FLATPAK_COMMIT_MAPPING", "application_id": "org.jaspstats.JASP", "flatpak_commit": "$JASP_OBSERVED_COMMIT"},
  "instrument_labels": {"BRUJULA": "Brújula giroscópica", "JAMOVI": "Sacapuntas", "JASP": "Lupa", "R": "Lápiz", "QWEN": "Motor Cognitivo"},
  "label_hierarchy": {"schema": "LUNITA_LABEL_HIERARCHY/1.0", "json_path": "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.json", "json_sha256": "$LABEL_HIERARCHY_SHA256", "text_path": "/opt/lunita/metadata/LUNITA_LABEL_HIERARCHY.txt", "text_sha256": "$LABEL_HIERARCHY_TEXT_SHA256"},
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
