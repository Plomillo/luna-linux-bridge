#!/bin/bash
# Bring the pinned JASP app's runtime forward without moving the app commit.
# JASP 0.98.1 links libQt6HttpServer against Qt 6.11.2 private ABI. An older
# org.kde.Platform//6.11 in the cached rootfs does not export that symbol.
set -euo pipefail
: "${FLATPAK_SYSTEM_DIR:?FLATPAK_SYSTEM_DIR is required}"
PINNED_APP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
flatpak info --system org.jaspstats.JASP
runtime="$(flatpak info --system org.jaspstats.JASP | sed -n 's/^[[:space:]]*Runtime:[[:space:]]*//p' | head -n 1)"
if [ -z "$runtime" ]; then
  echo "JASP runtime id is missing" >&2
  exit 2
fi
echo "Refreshing $runtime"
flatpak update --system --noninteractive --assumeyes "$runtime"
app_commit="$(flatpak info --system --show-commit org.jaspstats.JASP)"
if [ "$app_commit" != "$PINNED_APP_COMMIT" ]; then
  echo "JASP app commit moved: $app_commit" >&2
  exit 2
fi
echo "JASP app commit remains $app_commit"
echo "Runtime commit $(flatpak info --system --show-commit "$runtime")"
