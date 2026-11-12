#!/bin/bash
# Keep the pinned JASP app on the current KDE 6.11 runtime and replace
# libQt6HttpServer with one built against that runtime. The published app
# library asks for QtPrivate_6_11_2, which Qt 6.11.3 no longer exports.
set -euo pipefail
: "${FLATPAK_SYSTEM_DIR:?FLATPAK_SYSTEM_DIR is required}"
PINNED_APP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
flatpak info --system org.jaspstats.JASP
runtime="$(flatpak info --system org.jaspstats.JASP | sed -n 's/^[[:space:]]*Runtime:[[:space:]]*//p' | head -n 1)"
if [ -z "$runtime" ]; then
  echo "JASP runtime id is missing" >&2
  exit 2
fi
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
echo "SDK Qt version $qt_version"
src="/tmp/qthttpserver-src"
rm -rf "$src"
mkdir -p "$src"
curl --fail --location --retry 3 "https://github.com/qt/qthttpserver/archive/refs/tags/v${qt_version}.tar.gz" | tar -xz -C "$src" --strip-components=1
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
files="$FLATPAK_SYSTEM_DIR/app/org.jaspstats.JASP/x86_64/stable/active/files"
dest="$files/lib/x86_64-linux-gnu"
mkdir -p "$dest"
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
