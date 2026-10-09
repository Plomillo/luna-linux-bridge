#!/usr/bin/env bash
# Runs only on a disposable Debian 13 KDE runner in a real graphical session.
set -Eeuo pipefail
INPUT_DIR="${1:?usage: debian13_kde_host_runtime.sh PACKAGE_DIR OUTPUT_DIR EXPECTED_COMMIT}"
OUTPUT_DIR="${2:?usage: debian13_kde_host_runtime.sh PACKAGE_DIR OUTPUT_DIR EXPECTED_COMMIT}"
EXPECTED_COMMIT="${3:?expected candidate commit SHA required}"
mkdir -p "$OUTPUT_DIR"
REPORT="$OUTPUT_DIR/CP-09-debian13-kde-runtime.json"
LOG="$OUTPUT_DIR/CP-09-debian13-kde-runtime.log"
: > "$LOG"
PKG=""
PACKAGE=""
INSTALL_STATUS="NOT_RUN"
LAUNCH_STATUS="NOT_RUN"
ROLLBACK_STATUS="NOT_RUN"
FINAL_RC=1
cleanup() {
  rc=$?
  if [ -n "$PACKAGE" ] && dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null | grep -q 'install ok installed'; then
    if sudo -n apt-get remove -y "$PACKAGE" >>"$LOG" 2>&1; then
      if ! dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null | grep -q 'install ok installed'; then
        ROLLBACK_STATUS="PASS"
      else
        ROLLBACK_STATUS="FAIL"
      fi
    else
      ROLLBACK_STATUS="FAIL"
    fi
  elif [ "$ROLLBACK_STATUS" = "NOT_RUN" ] && [ "$INSTALL_STATUS" = "PASS" ]; then
    ROLLBACK_STATUS="PASS"
  fi
  if [ "$rc" -eq 0 ] && [ "$ROLLBACK_STATUS" != "PASS" ]; then rc=38; fi
  set +e
  python3 - "$REPORT" "$LOG" "$PKG" "$EXPECTED_COMMIT" "$INSTALL_STATUS" "$LAUNCH_STATUS" "$ROLLBACK_STATUS" "$rc" <<'PY'
import datetime,hashlib,json,os,pathlib,subprocess,sys
report,log_path,pkg,commit,install,launch,rollback,rc=sys.argv[1:]
log=pathlib.Path(log_path).read_bytes()
package=pathlib.Path(pkg) if pkg else None
def output(*cmd):
    try: return subprocess.check_output(cmd,text=True,stderr=subprocess.DEVNULL).strip()
    except Exception: return ""
osr={}
try:
    for line in pathlib.Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k,v=line.split("=",1); osr[k]=v.strip('"')
except Exception: pass
desktop=(os.environ.get("XDG_CURRENT_DESKTOP","")+" "+os.environ.get("DESKTOP_SESSION","")).upper()
physical=(osr.get("ID")=="debian" and osr.get("VERSION_ID")=="13" and
          "KDE" in desktop and bool(os.environ.get("DISPLAY")) and
          bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS")) and
          os.environ.get("KDE_FULL_SESSION","").lower() in ("true","1","yes"))
digest=hashlib.sha256(package.read_bytes()).hexdigest() if package and package.is_file() else None
status="PASS" if physical and install==launch==rollback=="PASS" and int(rc)==0 else "HOLD"
data={
 "schema":"louksna.zd.v03.cp09-runtime-gate.v1",
 "stage_id":"09","checkpoint_id":"CP-09",
 "timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
 "repository":os.environ.get("GITHUB_REPOSITORY"),
 "commit_sha":commit,"run_id":os.environ.get("GITHUB_RUN_ID"),
 "status":status,"result":status,"physical_runtime_verified":bool(physical),
 "os_id":osr.get("ID"),"os_version":osr.get("VERSION_ID"),
 "desktop":"KDE" if "KDE" in desktop else desktop or "UNKNOWN",
 "install_test":install,"launch_test":launch,"rollback_test":rollback,
 "candidate_sha256":digest,
 "evidence_sha256":[hashlib.sha256(log).hexdigest()],
 "log_sha256":hashlib.sha256(log).hexdigest(),
 "package_name":package.name if package else None,
 "reason":("Actual Debian 13 KDE session and package install/launch/rollback checks passed." if status=="PASS"
           else "HOLD: physical KDE session or one or more install/launch/rollback checks failed."),
 "limitations":["Requires a dedicated disposable self-hosted runner with an active KDE graphical session.",
                "A process-launch check is not a full interactive feature certification."]
}
pathlib.Path(report).write_text(json.dumps(data,indent=2,sort_keys=True)+"\n")
print(json.dumps(data,indent=2))
with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as out:
    out.write("status="+status+"\\n")
PY
  exit "$rc"
}
trap cleanup EXIT
mapfile -t PACKAGES < <(find "$INPUT_DIR" -type f -name '*.deb' -print | sort)
if [ "${#PACKAGES[@]}" -ne 1 ]; then
  echo "Expected exactly one package, found ${#PACKAGES[@]}" | tee -a "$LOG"
  exit 31
fi
PKG="$(realpath "${PACKAGES[0]}")"
if ! grep -q '^ID=debian$' /etc/os-release || ! grep -q '^VERSION_ID="13"$\|^VERSION_ID=13$' /etc/os-release; then
  echo "Runner is not Debian 13" | tee -a "$LOG"
  exit 32
fi
DESKTOP="$(printf '%s %s' "${XDG_CURRENT_DESKTOP:-}" "${DESKTOP_SESSION:-}" | tr '[:lower:]' '[:upper:]')"
if [[ "$DESKTOP" != *KDE* || "${KDE_FULL_SESSION:-}" != "true" || -z "${DISPLAY:-}" || -z "${DBUS_SESSION_BUS_ADDRESS:-}" ]]; then
  echo "No active KDE graphical session (DISPLAY/DBUS/KDE_FULL_SESSION required)" | tee -a "$LOG"
  exit 33
fi
PACKAGE="$(dpkg-deb -f "$PKG" Package)"
VERSION="$(dpkg-deb -f "$PKG" Version)"
if dpkg-query -W -f='${Status}' "$PACKAGE" 2>/dev/null | grep -q 'install ok installed'; then
  echo "Refusing to overwrite pre-existing package $PACKAGE" | tee -a "$LOG"
  exit 34
fi
printf 'package=%s\nversion=%s\ncommit=%s\n' "$PACKAGE" "$VERSION" "$EXPECTED_COMMIT" | tee -a "$LOG"
sha256sum "$PKG" | tee -a "$LOG"
if sudo -n apt-get update >>"$LOG" 2>&1 && sudo -n apt-get install -y "$PKG" >>"$LOG" 2>&1; then
  INSTALL_STATUS="PASS"
else
  INSTALL_STATUS="FAIL"
  exit 35
fi
DESKTOP_FILE="$(find /usr/share/applications -type f -iname '*louksna*.desktop' -print -quit || true)"
if [ -n "$DESKTOP_FILE" ]; then
  EXEC_LINE="$(sed -n 's/^Exec=//p' "$DESKTOP_FILE" | head -n 1)"
  BIN="${EXEC_LINE%% *}"
else
  BIN="$(find /usr/bin /usr/local/bin -maxdepth 1 -type f -iname '*louksna*' -print -quit || true)"
fi
if [ -z "${BIN:-}" ] || [ ! -x "$BIN" ]; then
  echo "Installed executable not discoverable" | tee -a "$LOG"
  LAUNCH_STATUS="FAIL"
  exit 36
fi
set +e
timeout --signal=TERM --kill-after=5s 20s "$BIN" >>"$LOG" 2>&1
RC=$?
set -e
if [ "$RC" -eq 124 ] || [ "$RC" -eq 0 ]; then
  LAUNCH_STATUS="PASS"
else
  LAUNCH_STATUS="FAIL"
  echo "Launch failed with exit code $RC" | tee -a "$LOG"
  exit 37
fi
# cleanup() performs and verifies the uninstall rollback; success is finalized there.
FINAL_RC=0
exit 0
