#!/bin/sh
set -eu
if [ "${XDG_SESSION_TYPE:-}" != "wayland" ] && [ "${LOUKSNA_ALLOW_NON_WAYLAND:-}" != "1" ]; then
  echo "WAYLAND_REQUIRED session=${XDG_SESSION_TYPE:-unset}" >&2
  exit 3
fi
STATE=${LOUKSNA_STATE:-"$HOME/.local/share/louksna"}
BIN=$(CDPATH= cd -- "$(dirname "$0")" && pwd)/louksna-session
if [ ! -x "$BIN" ]; then
  BIN=/usr/bin/louksna-session
fi
"$BIN" --serve --bind 127.0.0.1:47321 --state "$STATE" &
PID=$!
i=0
while [ "$i" -lt 50 ]; do
  if command -v curl >/dev/null 2>&1 && curl -sf -o /dev/null --max-time 1 http://127.0.0.1:47321/; then
    break
  fi
  i=$((i+1))
  sleep 0.1
done
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://127.0.0.1:47321/ >/dev/null 2>&1 || true
fi
wait "$PID"
