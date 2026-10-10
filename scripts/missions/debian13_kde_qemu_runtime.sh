#!/usr/bin/env bash
# CP-09 integrated disposable Debian 13 KDE/Xorg VM test (QEMU).
# This proves guest OS/desktop install-launch-rollback, not physical GPU/audio/microphone.
set -Eeuo pipefail
INPUT_DIR="${1:?usage: debian13_kde_qemu_runtime.sh PACKAGE_DIR OUTPUT_DIR EXPECTED_COMMIT}"
OUTPUT_DIR="${2:?output directory required}"
EXPECTED_COMMIT="${3:?expected candidate commit SHA required}"
mkdir -p "$OUTPUT_DIR"
REPORT="$OUTPUT_DIR/CP-09-debian13-kde-runtime.json"
LOG="$OUTPUT_DIR/CP-09-debian13-kde-runtime.log"
WORK="$OUTPUT_DIR/qemu-work"
mkdir -p "$WORK"
: > "$LOG"
INSTALL_STATUS=NOT_RUN
LAUNCH_STATUS=NOT_RUN
ROLLBACK_STATUS=NOT_RUN
GUEST_STATUS=NOT_RUN
PKG=""
QEMU_PID=""
VM_KEY="$WORK/vm_ssh_key"
log(){ printf '[%s] %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$LOG"; }
finish(){
  rc=$?
  set +e
  if [[ -n "$QEMU_PID" ]]; then sudo kill "$QEMU_PID" >/dev/null 2>&1; fi
  if [[ -f "$WORK/qemu.pid" ]]; then sudo kill "$(sudo cat "$WORK/qemu.pid")" >/dev/null 2>&1; fi
  python3 - "$REPORT" "$LOG" "$PKG" "$EXPECTED_COMMIT" "$INSTALL_STATUS" "$LAUNCH_STATUS" "$ROLLBACK_STATUS" "$GUEST_STATUS" "$rc" <<'PY'
import datetime,hashlib,json,os,pathlib,sys
report,log_path,pkg,commit,install,launch,rollback,guest,rc=sys.argv[1:]
log=pathlib.Path(log_path).read_bytes()
package=pathlib.Path(pkg) if pkg else None
digest=hashlib.sha256(package.read_bytes()).hexdigest() if package and package.is_file() else None
status="PASS" if guest=="PASS" and install==launch==rollback=="PASS" and int(rc)==0 else "HOLD"
d={"schema":"louksna.zd.v03.cp09-runtime-gate.v2","stage_id":"09","checkpoint_id":"CP-09",
"timestamp_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),
"repository":os.getenv("GITHUB_REPOSITORY"),"commit_sha":commit,"run_id":int(os.getenv("GITHUB_RUN_ID","0")),
"run_attempt":int(os.getenv("GITHUB_RUN_ATTEMPT","1")),"status":status,"result":status,
"runtime_environment":"DISPOSABLE_QEMU_VM","virtual_runtime_verified":status=="PASS",
"physical_runtime_verified":False,"guest_os":"Debian GNU/Linux 13","guest_desktop":"KDE Plasma/Xorg",
"guest_status":guest,"install_test":install,"launch_test":launch,"rollback_test":rollback,
"candidate_sha256":digest,"package_name":package.name if package else None,
"log_sha256":hashlib.sha256(log).hexdigest(),"evidence_sha256":[hashlib.sha256(log).hexdigest()],
"reason":"Disposable Debian 13 KDE/Xorg VM install/launch/rollback passed." if status=="PASS" else "HOLD: guest runtime or install/launch/rollback checks failed.",
"limitations":["QEMU guest with virtual display; does not prove physical GPU, monitor, audio, microphone, or full interactive correctness.",
"VM evidence is explicitly virtual and is not represented as a physical-host test."]}
pathlib.Path(report).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print(json.dumps(d,indent=2))
with open(os.environ["GITHUB_OUTPUT"],"a",encoding="utf-8") as out:
    out.write("status="+status+"\n")
PY
  if [[ "$rc" -eq 0 ]] && ! jq -e '.status == "PASS"' "$REPORT" >/dev/null; then rc=1; fi
  exit "$rc"
}
trap finish EXIT
mapfile -t PACKAGES < <(find "$INPUT_DIR" -type f -name '*.deb' -print | sort)
if [[ "${#PACKAGES[@]}" -ne 1 ]]; then log "Expected exactly one Debian package; found ${#PACKAGES[@]}"; exit 31; fi
PKG="$(realpath "${PACKAGES[0]}")"
[[ "$EXPECTED_COMMIT" =~ ^[0-9a-f]{40}$ ]] || { log "Invalid candidate SHA"; exit 32; }
log "candidate_sha=$EXPECTED_COMMIT"
sha256sum "$PKG" | tee -a "$LOG"
sudo apt-get -o Acquire::Retries=3 update >>"$LOG" 2>&1
sudo apt-get -o Acquire::Retries=3 install -y --no-install-recommends qemu-system-x86 qemu-utils cloud-image-utils openssh-client sshpass jq curl ca-certificates unzip >>"$LOG" 2>&1
qemu-system-x86_64 --version | tee -a "$LOG"
curl --fail --show-error --location --retry 3 https://cloud.debian.org/images/cloud/trixie/latest/debian-13-genericcloud-amd64.qcow2 -o "$WORK/debian-13.qcow2" >>"$LOG" 2>&1
ssh-keygen -q -t ed25519 -N '' -f "$VM_KEY"
PUBKEY="$(cat "$VM_KEY.pub")"
cat > "$WORK/user-data" <<EOF
#cloud-config
hostname: louksna-cp09
users:
  - name: louksna-test
    uid: 1000
    groups: [sudo, adm, audio, video]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    lock_passwd: true
    ssh_authorized_keys:
      - ${PUBKEY}
ssh_pwauth: false
package_update: true
packages:
  - openssh-server
  - sudo
  - dbus
  - dbus-x11
  - xserver-xorg
  - xserver-xorg-video-dummy
  - x11-xserver-utils
  - x11-utils
  - xauth
  - xinit
  - plasma-workspace
  - kwin-x11
  - konsole
  - python3
  - ca-certificates
write_files:
  - path: /etc/X11/Xwrapper.config
    permissions: '0644'
    content: |
      allowed_users=anybody
      needs_root_rights=yes
  - path: /etc/X11/xorg.conf.d/20-dummy.conf
    permissions: '0644'
    content: |
      Section "Device"
        Identifier "DummyDevice"
        Driver "dummy"
        VideoRam 256000
      EndSection
      Section "Monitor"
        Identifier "DummyMonitor"
        HorizSync 5.0-1000.0
        VertRefresh 5.0-200.0
        Modeline "1920x1080" 172.80 1920 2040 2248 2576 1080 1083 1088 1120
      EndSection
      Section "Screen"
        Identifier "DummyScreen"
        Device "DummyDevice"
        Monitor "DummyMonitor"
        DefaultDepth 24
        SubSection "Display"
          Depth 24
          Modes "1920x1080"
        EndSubSection
      EndSection
runcmd:
  - systemctl enable ssh
  - systemctl restart ssh
  - touch /var/lib/cloud/instance/cp09-ready
EOF
cat > "$WORK/meta-data" <<EOF
instance-id: louksna-cp09-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}
local-hostname: louksna-cp09
EOF
cloud-localds "$WORK/seed.iso" "$WORK/user-data" "$WORK/meta-data"
qemu-img create -f qcow2 -F qcow2 -b "$WORK/debian-13.qcow2" "$WORK/guest.qcow2" 24G >>"$LOG" 2>&1
ACCEL=tcg
if [[ -e /dev/kvm ]] && sudo qemu-system-x86_64 -machine q35,accel=kvm -cpu max -m 128 -nodefaults -display none -S -daemonize -pidfile "$WORK/probe.pid" 2>>"$LOG"; then
  ACCEL=kvm; sudo kill "$(sudo cat "$WORK/probe.pid")" >/dev/null 2>&1 || true
fi
log "QEMU_ACCEL=$ACCEL"
sudo qemu-system-x86_64 -machine "q35,accel=$ACCEL" -cpu max -smp 2 -m 4096 \
  -drive "file=$WORK/guest.qcow2,if=virtio,format=qcow2" \
  -drive "file=$WORK/seed.iso,media=cdrom,readonly=on" \
  -netdev user,id=net0,hostfwd=tcp:127.0.0.1:2222-:22 -device virtio-net-pci,netdev=net0 \
  -vga std -display none -serial "file:$WORK/vm-serial.log" -daemonize -pidfile "$WORK/qemu.pid"
QEMU_PID="$(sudo cat "$WORK/qemu.pid")"
SSH=(ssh -i "$VM_KEY" -p 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 louksna-test@127.0.0.1)
READY=0
for _ in $(seq 1 120); do
  if "${SSH[@]}" 'test -f /var/lib/cloud/instance/cp09-ready' >/dev/null 2>&1; then READY=1; break; fi
  sleep 5
done
if [[ "$READY" -ne 1 ]]; then tail -n 120 "$WORK/vm-serial.log" >>"$LOG" 2>&1 || true; log "Debian guest/cloud-init did not become ready"; exit 33; fi
"${SSH[@]}" 'sudo cloud-init status --wait; . /etc/os-release; test "$ID:$VERSION_ID" = "debian:13"; dpkg-query -W plasma-workspace kwin-x11 xserver-xorg-video-dummy' | tee -a "$LOG"
"${SSH[@]}" 'sudo install -d -o louksna-test -g louksna-test -m 0700 /run/user/1000; sudo -u louksna-test mkdir -p /home/louksna-test/.local/share; sudo -u louksna-test nohup env HOME=/home/louksna-test USER=louksna-test LOGNAME=louksna-test XDG_RUNTIME_DIR=/run/user/1000 dbus-run-session -- startx /usr/bin/startplasma-x11 -- :0 vt1 -keeptty -nolisten tcp > /home/louksna-test/.local/share/cp09-kde-session.log 2>&1 < /dev/null & for i in $(seq 1 60); do pgrep -x Xorg >/dev/null && pgrep -x kwin_x11 >/dev/null && break; sleep 2; done; pgrep -x Xorg; pgrep -x kwin_x11; tail -n 60 /home/louksna-test/.local/share/cp09-kde-session.log || true' | tee -a "$LOG"
scp -i "$VM_KEY" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$PKG" louksna-test@127.0.0.1:/tmp/candidate.deb
cat > "$WORK/guest-test.sh" <<'GUEST'
#!/usr/bin/env bash
set -uo pipefail
PKG="$(dpkg-deb -f /tmp/candidate.deb Package)"
rollback() {
  set +e
  sudo apt-get remove -y "$PKG" >/tmp/rollback.log 2>&1
  rc=$?
  if [[ "$rc" -eq 0 ]] && ! dpkg-query -W -f='${Status}' "$PKG" 2>/dev/null | grep -q 'install ok installed'; then
    echo ROLLBACK_PASS
  else
    echo ROLLBACK_FAIL
    touch /tmp/rollback-failed
  fi
}
trap rollback EXIT
sudo apt-get install -y /tmp/candidate.deb >/tmp/package-install.log 2>&1 || { cat /tmp/package-install.log; echo INSTALL_FAIL; exit 1; }
dpkg-query -W -f='${Package}\t${Version}\t${Status}\n' "$PKG" >/tmp/package-installed.tsv
pgrep -x Xorg >/dev/null && pgrep -x kwin_x11 >/dev/null || { echo "KDE/Xorg session process missing"; exit 3; }
uid="$(id -u louksna-test)"
XAUTH="$(pgrep -a Xorg | sed -n 's/.*-auth \([^ ]*\).*/\1/p' | head -n 1)"
if [[ -n "$XAUTH" ]] && sudo test -r "$XAUTH"; then sudo cp "$XAUTH" /home/louksna-test/.Xauthority; sudo chown louksna-test:louksna-test /home/louksna-test/.Xauthority; sudo chmod 600 /home/louksna-test/.Xauthority; fi
BIN="$(find /usr/bin /usr/local/bin -maxdepth 1 -type f -iname '*louksna*' -print -quit)"
test -n "$BIN" && test -x "$BIN" || { echo "LAUNCH_SMOKE_FAIL executable_missing"; exit 4; }
BASELINE_WINDOWS="$(xwininfo -root -tree | awk '/^[[:space:]]+0x[[:xdigit:]]+[[:space:]]/ { n++ } END { print n+0 }')"
sudo -u louksna-test env HOME=/home/louksna-test USER=louksna-test LOGNAME=louksna-test DISPLAY=:0 XAUTHORITY=/home/louksna-test/.Xauthority XDG_RUNTIME_DIR="/run/user/$uid" XDG_CURRENT_DESKTOP=KDE KDE_FULL_SESSION=true XDG_SESSION_TYPE=x11 "$BIN" >/tmp/louksna-launch.log 2>&1 &
APP_PID=$!
WINDOW_FOUND=0
for _ in $(seq 1 20); do
  if ! kill -0 "$APP_PID" 2>/dev/null; then
    echo "LAUNCH_SMOKE_FAIL application_exited_before_window"
    cat /tmp/louksna-launch.log
    exit 4
  fi
  CURRENT_WINDOWS="$(xwininfo -root -tree | awk '/^[[:space:]]+0x[[:xdigit:]]+[[:space:]]/ { n++ } END { print n+0 }')"
  if (( CURRENT_WINDOWS > BASELINE_WINDOWS )); then WINDOW_FOUND=1; break; fi
  sleep 1
done
if [[ "$WINDOW_FOUND" -ne 1 ]]; then
  kill "$APP_PID" >/dev/null 2>&1 || true
  wait "$APP_PID" 2>/dev/null || true
  echo "LAUNCH_SMOKE_FAIL no_new_X11_window baseline=$BASELINE_WINDOWS current=$CURRENT_WINDOWS"
  cat /tmp/louksna-launch.log
  exit 4
fi
echo "LAUNCH_SMOKE_PASS visible_window=1 baseline=$BASELINE_WINDOWS current=$CURRENT_WINDOWS"
kill -TERM "$APP_PID" >/dev/null 2>&1 || true
wait "$APP_PID" 2>/dev/null || true
GUEST
scp -i "$VM_KEY" -P 2222 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null "$WORK/guest-test.sh" louksna-test@127.0.0.1:/tmp/guest-test.sh
set +e
"${SSH[@]}" 'chmod +x /tmp/guest-test.sh && bash /tmp/guest-test.sh' 2>&1 | tee "$WORK/guest-test-output.log" | tee -a "$LOG"
RC=${PIPESTATUS[0]}
set -e
"${SSH[@]}" 'cat /tmp/package-install.log /tmp/package-installed.tsv /tmp/louksna-launch.log /tmp/rollback.log 2>/dev/null || true; cat /tmp/rollback-result.txt 2>/dev/null || true' | tee "$WORK/guest-package-evidence.log" | tee -a "$LOG"
if [[ "$RC" -eq 0 ]] && grep -q 'LAUNCH_SMOKE_PASS' "$WORK/guest-test-output.log" && grep -q 'ROLLBACK_PASS' "$WORK/guest-test-output.log"; then
  INSTALL_STATUS=PASS; LAUNCH_STATUS=PASS; ROLLBACK_STATUS=PASS; GUEST_STATUS=PASS
else
  grep -q 'INSTALL_FAIL' "$WORK/guest-test-output.log" && INSTALL_STATUS=FAIL
  grep -q 'LAUNCH_SMOKE_PASS' "$WORK/guest-test-output.log" && LAUNCH_STATUS=PASS || LAUNCH_STATUS=FAIL
  grep -q 'ROLLBACK_PASS' "$WORK/guest-test-output.log" && ROLLBACK_STATUS=PASS || ROLLBACK_STATUS=FAIL
  GUEST_STATUS=FAIL
  exit 34
fi
log "CP-09 disposable Debian 13 KDE/Xorg VM test passed; no physical-host claim."
