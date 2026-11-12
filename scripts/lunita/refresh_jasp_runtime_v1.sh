#!/bin/bash
# Pin org.kde.Platform//6.11 to the Qt 6.11.2 commit that JASP 0.98.1 was built against.
# The current Flathub runtime (fb23e178, Qt 6.11.3) drops QtPrivate_6_11_2, so
# libQt6HttpServer.so.6 fails at startup. The JASP app commit stays pinned.
set -euo pipefail
: "${FLATPAK_SYSTEM_DIR:?FLATPAK_SYSTEM_DIR is required}"
PINNED_APP_COMMIT="83ec9d24365269942539c2d1f1af806c475e6320e5bdff2aced4e28479de3df7"
QT6112_RUNTIME_COMMIT="76fa01ac42ecf45d2c5020ef80de1c474c0c2ae86a51a79e8fec44c48f9dc473"
flatpak info --system org.jaspstats.JASP
runtime="$(flatpak info --system org.jaspstats.JASP | sed -n 's/^[[:space:]]*Runtime:[[:space:]]*//p' | head -n 1)"
if [ -z "$runtime" ]; then
  echo "JASP runtime id is missing" >&2
  exit 2
fi
echo "Pinning $runtime to Qt 6.11.2 commit $QT6112_RUNTIME_COMMIT"
flatpak update --system --noninteractive --assumeyes --commit="$QT6112_RUNTIME_COMMIT" "$runtime"
app_commit="$(flatpak info --system --show-commit org.jaspstats.JASP)"
runtime_commit="$(flatpak info --system --show-commit "$runtime")"
if [ "$app_commit" != "$PINNED_APP_COMMIT" ]; then
  echo "JASP app commit moved: $app_commit" >&2
  exit 2
fi
if [ "$runtime_commit" != "$QT6112_RUNTIME_COMMIT" ]; then
  echo "Runtime commit is $runtime_commit, expected $QT6112_RUNTIME_COMMIT" >&2
  exit 2
fi
echo "JASP app commit remains $app_commit"
echo "Runtime commit $runtime_commit"
