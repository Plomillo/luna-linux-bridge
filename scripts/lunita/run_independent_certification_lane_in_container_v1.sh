#!/usr/bin/env bash
set -Eeuo pipefail

: "${LUNITA_XDG_STATE_HOME:?LUNITA_XDG_STATE_HOME is required}"
: "${LUNITA_ROOTFS_REAL:?LUNITA_ROOTFS_REAL is required}"
: "${RUNNER_TEMP:?RUNNER_TEMP is required}"
: "${GITHUB_WORKSPACE:?GITHUB_WORKSPACE is required}"

CERT_STATE="$RUNNER_TEMP/lunita-stability-state"
CERT_CANDIDATE="$RUNNER_TEMP/lunita-stability-candidate"
mkdir -p "$CERT_STATE" "$CERT_CANDIDATE" "$CERT_STATE/worker_outputs" "$CERT_STATE/lunita_certification_evidence"

export XDG_STATE_HOME="$LUNITA_XDG_STATE_HOME"
export LUNITA_CERTIFICATION_PROFILE=V1_8_DIRECT
export LUNITA_STATE_DIR="$CERT_STATE"
export LUNITA_OUTPUT_DIR="$CERT_STATE/worker_outputs"
export LUNITA_EVIDENCE_DIR="$CERT_STATE/lunita_certification_evidence"
export LUNITA_CANDIDATE_DIR="$CERT_CANDIDATE"
export LUNITA_CANDIDATE_MANIFEST="$GITHUB_WORKSPACE/LUNITA_V1_8_CANDIDATE_FREEZE.json"
export LUNITA_ROOTFS="$LUNITA_ROOTFS_REAL"
export LUNITA_SQUASHFS_IMAGE="$RUNNER_TEMP/lunita-squashfs/LUNITA.squashfs"
export LUNITA_SQUASHFS_CHECKSUM="$RUNNER_TEMP/lunita-squashfs/LUNITA.squashfs.sha256"
export LUNITA_SQUASHFS_PACKAGE_RECEIPT="$RUNNER_TEMP/lunita-squashfs/LUNITA_SQUASHFS_PACKAGE_RECEIPT.json"
export LUNITA_TARGET_RUNTIME_RECEIPT_DIR="$LUNITA_XDG_STATE_HOME/lunita/runtime_validation"
export FLATPAK_SYSTEM_DIR="$LUNITA_ROOTFS_REAL/var/lib/flatpak"
export QT_QPA_PLATFORM=xcb
export DISPLAY="${DISPLAY:-:99}"
if [ ! -S "/tmp/.X11-unix/X${DISPLAY#:}" ]; then
  if [ "$(id -u)" -eq 0 ]; then
    apt-get update
    apt-get install -y --no-install-recommends xvfb
  fi
  Xvfb "$DISPLAY" -screen 0 1280x800x24 -nolisten tcp >/tmp/lunita-xvfb.log 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    [ -S "/tmp/.X11-unix/X${DISPLAY#:}" ] && break
    sleep 0.25
  done
fi
if [ ! -S /tmp/lunita-dbus/bus ]; then
  if [ "$(id -u)" -eq 0 ]; then
    apt-get install -y --no-install-recommends dbus
  fi
  mkdir -p /tmp/lunita-dbus
  dbus-daemon --session --address=unix:path=/tmp/lunita-dbus/bus --nofork --nopidfile >/tmp/lunita-dbus.log 2>&1 &
  for _ in 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20; do
    [ -S /tmp/lunita-dbus/bus ] && break
    sleep 0.25
  done
fi
export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/lunita-dbus/bus

LANE="$GITHUB_WORKSPACE/recovery/lunita-custoszv9/lunita_stability_certification_lane_v1.py"
test -f "$LANE"
python3.12 - "$LANE" "$LUNITA_EVIDENCE_DIR/lane_state.json" <<'PY'
import json, os, pathlib, signal, subprocess, sys, time
lane = pathlib.Path(sys.argv[1])
state_path = pathlib.Path(sys.argv[2])
for attempt in range(180):
    run = subprocess.run([sys.executable, str(lane), "--once"], text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False)
    print(run.stdout, flush=True)
    if run.returncode != 0:
        raise SystemExit(f"Certification lane exited {run.returncode}")
    try:
        state = json.loads(state_path.read_text(encoding="utf-8"))
        tick = state.get("last_tick") or {}
    except (OSError, ValueError):
        tick = {}
        state = {}
    if tick.get("independent_report_status") == "PASS_INDEPENDENT_VALIDATION":
        print("PASS_G23_INPUT: hash-bound independent report is complete; S32/G24 remain distinct.", flush=True)
        raise SystemExit(0)
    jobs = [state.get("jasp_job"), state.get("inventory_job")]
    active = False
    for job in jobs:
        pid = (job or {}).get("pid")
        if isinstance(pid, int) and pid > 1:
            try:
                os.kill(pid, 0)
                active = True
            except OSError:
                pass
    if (tick.get("cajita_heavy_lane") or {}).get("active"):
        active = True
    jasp_done = str(tick.get("jasp_status", "")).startswith(("PASS_", "BLOCKED_"))
    inventory_done = str(tick.get("inventory_status", "")).startswith(("PASS_", "BLOCKED_"))
    if not active and jasp_done and inventory_done:
        print("BEGIN_BOUNDED_JASP_FAILURE_DIAGNOSTICS", flush=True)
        output_dir = pathlib.Path(os.environ["LUNITA_OUTPUT_DIR"])
        patterns = (
            "JASP_UNITTEST_FLATPAK_*.log",
            "JASP_UNITTEST_RELIABILITY_*.log",
            "JASP_UNITTEST_WEIGHT_GAIN_*.log",
            "JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_*.json",
            "JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_*_save.log",
            "JASP_UNITTEST_ROUNDTRIP_DEATH_PENALTY_*_rerun.log",
        )
        for pattern in patterns:
            for evidence in sorted(output_dir.glob(pattern)):
                try:
                    content = evidence.read_text(encoding="utf-8", errors="replace").splitlines()
                    excerpt = content[-180:]
                    print(f"\n===== {evidence.name} ({len(content)} lines; last {len(excerpt)}) =====", flush=True)
                    print("\n".join(excerpt), flush=True)
                except OSError as exc:
                    print(f"DIAGNOSTIC_READ_FAILED {evidence}: {type(exc).__name__}: {exc}", flush=True)
        print("END_BOUNDED_JASP_FAILURE_DIAGNOSTICS", flush=True)
        raise SystemExit("BLOCKED: the independent JASP/rootfs lane completed with one or more failed checks.")
    print(f"WAITING_FOR_INDEPENDENT_EVIDENCE attempt={attempt + 1}/180", flush=True)
    time.sleep(30)
raise SystemExit("BLOCKED: independent evidence did not complete within the bounded run window.")
PY
