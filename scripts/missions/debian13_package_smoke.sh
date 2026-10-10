#!/usr/bin/env bash
# Debian 13 container smoke test for the exact CP-08 package.
# This is not evidence of a physical KDE desktop; it is a repeatable CI runtime probe.
set -Eeuo pipefail
INPUT_DIR="${1:?usage: debian13_package_smoke.sh INPUT_DIR OUTPUT_DIR}"
OUTPUT_DIR="${2:?usage: debian13_package_smoke.sh INPUT_DIR OUTPUT_DIR}"
mkdir -p "$OUTPUT_DIR"
REPORT="$OUTPUT_DIR/CP-09-debian13-container-smoke.json"
LOG="$OUTPUT_DIR/CP-09-debian13-container-smoke.log"
mapfile -t PACKAGES < <(find "$INPUT_DIR" -type f -name '*.deb' -print | sort)
if [ "${#PACKAGES[@]}" -ne 1 ]; then
  python3 - "$REPORT" "${#PACKAGES[@]}" <<'PY'
import json,sys
json.dump({"schema":"louksna.zd.v03.debian13-smoke.v1","status":"HOLD","reason":"Expected exactly one CP-08 .deb; found "+sys.argv[2],"package_count":int(sys.argv[2])},open(sys.argv[1],"w"),indent=2)
PY
  echo "CP-09 Debian 13 smoke HOLD: expected one .deb, found ${#PACKAGES[@]}"
  exit 0
fi
PKG="$(realpath "${PACKAGES[0]}")"
set +e
docker run --rm \
  -v "$(realpath "$INPUT_DIR"):/input:ro" \
  -v "$(realpath "$OUTPUT_DIR"):/out" \
  debian:13-slim bash -s >"$LOG" 2>&1 <<'IN_CONTAINER'
set -Eeuo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get -o Acquire::Retries=3 update
apt-get -o Acquire::Retries=3 install -y --no-install-recommends \
  ca-certificates dbus-x11 xvfb file \
  libwebkit2gtk-4.1-0 libgtk-3-0t64 libayatana-appindicator3-1 \
  libssl3t64 libsecret-1-0 librsvg2-2 libxdo3 libnotify4 libgbm1
DEB="$(find /input -type f -name "*.deb" -print -quit)"
test -n "$DEB"
PACKAGE="$(dpkg-deb -f "$DEB" Package)"
VERSION="$(dpkg-deb -f "$DEB" Version)"
ARCH="$(dpkg-deb -f "$DEB" Architecture)"
SHA256="$(sha256sum "$DEB" | awk '{print $1}')"
printf 'PACKAGE=%s\nVERSION=%s\nARCH=%s\nSHA256=%s\n' "$PACKAGE" "$VERSION" "$ARCH" "$SHA256"
apt-get -o Acquire::Retries=3 install -y "$DEB"
echo "INSTALL_STATUS=PASS"
DESKTOP="$(find /usr/share/applications -type f -iname '*louksna*.desktop' -print -quit || true)"
if [ -n "$DESKTOP" ]; then
  EXEC_LINE="$(sed -n 's/^Exec=//p' "$DESKTOP" | head -n 1)"
  BIN="${EXEC_LINE%% *}"
else
  BIN="$(find /usr/bin /usr/local/bin -maxdepth 1 -type f -iname '*louksna*' -print -quit || true)"
fi
if [ -z "${BIN:-}" ] || [ ! -x "$BIN" ]; then
  echo "LAUNCH_STATUS=FAIL; executable not discoverable"
  exit 22
fi
set +e
timeout 15s dbus-run-session -- xvfb-run -a "$BIN" >/tmp/louksna-runtime.log 2>&1
RC=$?
set -e
cat /tmp/louksna-runtime.log
if [ "$RC" -eq 124 ]; then
  echo "LAUNCH_STATUS=PASS; process remained alive until bounded timeout"
elif [ "$RC" -eq 0 ]; then
  echo "LAUNCH_STATUS=PASS; process exited cleanly"
else
  echo "LAUNCH_STATUS=FAIL; exit_code=$RC"
  exit 23
fi
if apt-get remove -y "$PACKAGE"; then
  if dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null | grep -q 'install ok installed'; then
    echo "ROLLBACK_STATUS=FAIL; package remains installed"
    exit 24
  fi
  echo "ROLLBACK_STATUS=PASS"
else
  echo "ROLLBACK_STATUS=FAIL; package removal failed"
  exit 25
fi
IN_CONTAINER
RC=$?
set -e
python3 - "$REPORT" "$LOG" "$RC" "$PKG" <<'PY'
import datetime,hashlib,json,pathlib,sys
report_path,log_path=map(pathlib.Path,sys.argv[1:3])
rc=int(sys.argv[3]); package=pathlib.Path(sys.argv[4])
log=log_path.read_text(errors="replace") if log_path.exists() else ""
def value(prefix):
    for line in log.splitlines():
        if line.startswith(prefix+"="): return line.split("=",1)[1].strip()
    return None
install="PASS" if "INSTALL_STATUS=PASS" in log else "FAIL"
launch="PASS" if "LAUNCH_STATUS=PASS" in log else "FAIL"
rollback="PASS" if "ROLLBACK_STATUS=PASS" in log else "FAIL"
status="PASS_WITH_SCOPE_LIMITS" if rc==0 and install==launch==rollback=="PASS" else "HOLD"
d={
 "schema":"louksna.zd.v03.debian13-smoke.v1",
 "stage_id":"09","checkpoint_id":"CP-09",
 "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "repository":__import__("os").getenv("GITHUB_REPOSITORY"),
 "commit_sha":__import__("os").getenv("GITHUB_SHA"),
 "run_id":__import__("os").getenv("GITHUB_RUN_ID"),
 "status":status,"container_image":"debian:13-slim","desktop":"headless-xvfb-not-KDE",
 "install_test":install,"launch_test":launch,"rollback_test":rollback,
 "package":{"name":value("PACKAGE"),"version":value("VERSION"),"architecture":value("ARCH"),
            "size_bytes":package.stat().st_size if package.exists() else None,
            "sha256":hashlib.sha256(package.read_bytes()).hexdigest() if package.exists() else None},
 "container_exit_code":rc,"log_sha256":hashlib.sha256(log.encode()).hexdigest(),
 "physical_runtime_verified":False,
 "limitations":["Debian 13 container smoke test only; not a physical host or KDE desktop test.",
                "A passing process-launch probe does not prove interactive feature behavior or independent certification."]
}
report_path.write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print(json.dumps(d,indent=2))
PY
echo "CP-09 Debian 13 container smoke report: $REPORT"
