#!/bin/bash
# Keep the pinned JASP app on the current KDE 6.11 runtime and replace
# libQt6HttpServer with one built against that runtime. The published app
# library asks for QtPrivate_6_11_2, which Qt 6.11.3 no longer exports.
set -euo pipefail
: "${FLATPAK_SYSTEM_DIR:?FLATPAK_SYSTEM_DIR is required}"
: "${LUNITA_JASP_MUTATION_RECEIPT:?LUNITA_JASP_MUTATION_RECEIPT is required}"
PINNED_APP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
flatpak info --system org.jaspstats.JASP
runtime="$(flatpak info --system org.jaspstats.JASP | sed -n 's/^[[:space:]]*Runtime:[[:space:]]*//p' | head -n 1)"
if [ -z "$runtime" ]; then
  echo "JASP runtime id is missing" >&2
  exit 2
fi
files="$FLATPAK_SYSTEM_DIR/app/org.jaspstats.JASP/x86_64/stable/active/files"
dest="$files/lib/x86_64-linux-gnu"
jasp_bin="$files/bin/JASP"
if [ ! -f "$jasp_bin" ]; then
  echo "JASP executable is missing: $jasp_bin" >&2
  exit 2
fi
mkdir -p "$dest"
src="/tmp/qthttpserver-src"
rm -rf "$src"
mkdir -p "$src"
app_commit_before="$(flatpak info --system --show-commit org.jaspstats.JASP)"
runtime_commit_before="$(flatpak info --system --show-commit "$runtime")"
jasp_binary_before_sha256="$(sha256sum "$jasp_bin" | awk '{print $1}')"
pre_qt_snapshot="$src/qt-libraries-before.sha256"
find "$dest" -type f -name 'libQt6HttpServer.so*' -print0 | sort -z | xargs -0 -r sha256sum > "$pre_qt_snapshot"
python3.12 scripts/lunita/record_jasp_runtime_mutation_receipt_v1.py --self-test

echo "Updating $runtime to the published tip"
flatpak update --system --noninteractive --assumeyes "$runtime"
app_commit="$(flatpak info --system --show-commit org.jaspstats.JASP)"
if [ "$app_commit" != "$PINNED_APP_COMMIT" ]; then
  echo "JASP app commit moved: $app_commit" >&2
  exit 2
fi
echo "JASP app commit remains $app_commit"
echo "Runtime commit $(flatpak info --system --show-commit "$runtime")"

host_flatpak() {
  env -u FLATPAK_SYSTEM_DIR flatpak "$@"
}
host_flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
host_flatpak install --system --noninteractive --assumeyes flathub org.kde.Sdk//6.11
qt_version="$(host_flatpak run --system --command=bash org.kde.Sdk//6.11 -c 'pkg-config --modversion Qt6Core')"
sdk_commit="$(host_flatpak info --system --show-commit org.kde.Sdk//6.11)"
echo "SDK Qt version $qt_version"
source_url="https://github.com/qt/qthttpserver/archive/refs/tags/v${qt_version}.tar.gz"
source_archive="$src/qthttpserver-v${qt_version}.tar.gz"
curl --fail --location --retry 3 "$source_url" -o "$source_archive"
tar -xzf "$source_archive" -C "$src" --strip-components=1
host_flatpak run --system --command=bash --filesystem="$src" org.kde.Sdk//6.11 -c "
set -eu
cd '$src'
cmake -G Ninja -S . -B build -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX='$src/out'
cmake --build build
cmake --install build
"
built="$(find "$src/out" -name 'libQt6HttpServer.so*' -print)"
if [ -z "$built" ]; then
  echo "qthttpserver build produced no libQt6HttpServer" >&2
  exit 2
fi
echo "$built"
find "$src/out" -name 'libQt6HttpServer.so*' -exec cp -a {} "$dest/" \;
echo "Replaced HttpServer libraries in $dest"

mkdir -p "$files/lunita-fixtures"
link_fixture() {
  relative="$1"
  name="$2"
  if [ ! -f "$files/$relative" ]; then
    echo "Missing JASP fixture: $files/$relative" >&2
    exit 2
  fi
  ln -sfn "../$relative" "$files/lunita-fixtures/$name"
}
link_fixture "Resources/Data Sets/Data Library/5. Frequencies/Death Penalty.jasp" DeathPenalty.jasp
link_fixture "Resources/Data Sets/Data Library/13. Reliability/Interrater Data from Shrout and Fleiss (1979).jasp" Reliability.jasp
link_fixture "Resources/Data Sets/Data Library/2. T-Tests/Weight Gain.jasp" WeightGain.jasp

patch_script="$(dirname "$0")/patch_jasp_certification_runtime_v1.py"
patch_log="$src/jasp-formatter-patch.log"
python3.12 "$patch_script" --self-test
python3.12 "$patch_script" --jasp-files "$files" | tee "$patch_log"
app_commit_after="$(flatpak info --system --show-commit org.jaspstats.JASP)"
runtime_commit_after="$(flatpak info --system --show-commit "$runtime")"
python3.12 scripts/lunita/record_jasp_runtime_mutation_receipt_v1.py \
  --output "$LUNITA_JASP_MUTATION_RECEIPT" \
  --app-commit-before "$app_commit_before" --app-commit-after "$app_commit_after" \
  --runtime-ref "$runtime" --runtime-commit-before "$runtime_commit_before" \
  --runtime-commit-after "$runtime_commit_after" \
  --sdk-ref "org.kde.Sdk//6.11" --sdk-commit "$sdk_commit" \
  --qt-version "$qt_version" --source-url "$source_url" \
  --source-archive "$source_archive" --build-dir "$src/out" \
  --qt-library-dir "$dest" --jasp-binary "$jasp_bin" \
  --jasp-binary-before-sha256 "$jasp_binary_before_sha256" \
  --pre-qt-snapshot "$pre_qt_snapshot" --patch-script "$patch_script" --patch-log "$patch_log"
