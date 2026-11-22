#!/bin/bash
# Debian 13 QEMU validation on the GitHub-hosted ubuntu-24.04 runner.
# Does not re-run the 36 historical tests or the 803 preserved cases.
# A green workflow is not product certification. G24 stays closed unless G23 passes.
set -u
ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT"
export GH_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
EVIDENCE="$ROOT/evidence"
WORKDIR="${RUNNER_TEMP:-/tmp}/louksna-vm"
mkdir -p "$EVIDENCE/vm" "$EVIDENCE/artifacts" "$EVIDENCE/luna" "$EVIDENCE/blockers" "$EVIDENCE/certification" "$EVIDENCE/cases" "$WORKDIR"
export EVIDENCE REPO="$ROOT"
FINAL=0
SSH_BASE=(-i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=20)

log() { echo "STAGE $(date -u +%H:%M:%S) $*"; }

preflight() {
  log PRECHECK
  python3 - << 'PY' > "$EVIDENCE/vm/vm-capabilities.json"
import json, os
from pathlib import Path
mem = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    key, value = line.split(":", 1)
    mem[key] = value.strip()
df = os.statvfs("/")
print(json.dumps({
    "nproc": os.cpu_count(),
    "arch": os.uname().machine,
    "mem_total": mem.get("MemTotal"),
    "mem_available": mem.get("MemAvailable"),
    "disk_free_bytes": df.f_bavail * df.f_frsize,
    "disk_total_bytes": df.f_blocks * df.f_frsize,
    "kvm_node": Path("/dev/kvm").exists(),
    "kvm_rw": os.access("/dev/kvm", os.R_OK | os.W_OK),
    "runner": os.environ.get("RUNNER_OS", ""),
    "runner_environment": os.environ.get("RUNNER_ENVIRONMENT", ""),
    "image": os.environ.get("ImageOS", ""),
}, indent=2))
PY
  cat "$EVIDENCE/vm/vm-capabilities.json"
  free_b=$(python3 -c 'import json;print(json.load(open("'"$EVIDENCE"'/vm/vm-capabilities.json"))["disk_free_bytes"])')
  if [ "$free_b" -lt $((12 * 1024 * 1024 * 1024)) ]; then
    echo "DISK_BELOW_12G" | tee "$EVIDENCE/vm/disk-stop.txt"
    FINAL=2
    return 1
  fi
}

audit() {
  log AUDIT
  python3 validation/debian13/audit.py || FINAL=2
}

host_575() {
  log HOST_575
  LOUKSNA_SUITE="$ROOT/louksna/mra_suite" \
    LOUKSNA_PROBE_OUT="$EVIDENCE/blockers/host-575.json" \
    python3 validation/debian13/probe_original.py 575 | tee "$EVIDENCE/blockers/host-575.txt" || true
}

fetch_artifacts() {
  log ARTIFACTS
  gh run download 45010622254 --repo Plomillo/luna-linux-bridge --name louksna-installers --dir "$EVIDENCE/artifacts" || {
    echo GH_DOWNLOAD_FAIL | tee "$EVIDENCE/artifacts/download-fail.txt"
    FINAL=2
    return 1
  }
  python3 - << 'PY'
import hashlib, pathlib, sys
root = pathlib.Path("evidence/artifacts")
want = {
    "LOUKSNA.deb": "fa372953f47c61019202995754cec7d688adf973c4491218e3b4db2465163657",
    "LOUKSNA.sh": "d74a0b5eefeba4a5777c87b97008169a540aee25861fb883f0943379cf7db8f7",
}
bad = False
for name, digest in want.items():
    path = root / name
    got = hashlib.sha256(path.read_bytes()).hexdigest()
    print(name, got, "OK" if got == digest else "MISMATCH")
    bad = bad or got != digest
sys.exit(1 if bad else 0)
PY
  if [ $? -ne 0 ]; then
    echo ARTIFACT_HASH_FAIL | tee "$EVIDENCE/artifacts/hash-fail.txt"
    FINAL=2
    return 1
  fi
}

boot_vm() {
  log VM
  sudo apt-get update
  sudo apt-get install -y qemu-system-x86 qemu-utils cloud-image-utils cloud-guest-utils e2fsprogs gdisk parted curl ca-certificates python3
  local image="debian-13-nocloud-amd64.qcow2"
  local url="https://cloud.debian.org/images/cloud/trixie/latest/${image}"
  local sums="$WORKDIR/SHA512SUMS"
  curl -fL --retry 5 -o "$sums" "https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS"
  curl -fL --retry 5 -o "$WORKDIR/$image" "$url"
  (cd "$WORKDIR" && sha512sum -c SHA512SUMS --ignore-missing)
  if [ $? -ne 0 ]; then
    echo IMAGE_HASH_FAIL | tee "$EVIDENCE/vm/image-hash-fail.txt"
    FINAL=2
    return 1
  fi
  local image_sha
  image_sha=$(awk -v name="$image" '$2==name || $2==("*" name) {print $1}' "$sums")
  qemu-img info "$WORKDIR/$image" > "$EVIDENCE/vm/image-info.txt"
  qemu-img resize "$WORKDIR/$image" 16G
  ssh-keygen -t ed25519 -f "$WORKDIR/vmkey" -N "" -q
  local pub
  pub=$(cat "$WORKDIR/vmkey.pub")
  cat > "$WORKDIR/meta-data" << EOF
instance-id: louksna-d13
local-hostname: louksna-d13
EOF
  cat > "$WORKDIR/user-data" << EOF
#cloud-config
hostname: louksna-d13
preserve_hostname: true
package_update: false
package_upgrade: false
users:
  - name: louksna
    gecos: LOUKSNA validation
    groups: [sudo, audio, video, netdev]
    shell: /bin/bash
    lock_passwd: true
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ${pub}
ssh_pwauth: false
disable_root: true
EOF
  cloud-localds "$WORKDIR/seed.img" "$WORKDIR/user-data" "$WORKDIR/meta-data"
  log IMAGE_PREPARE
  if ! sudo bash "$ROOT/validation/debian13/prepare-image.sh" "$WORKDIR/$image" "$WORKDIR/vmkey.pub" > "$EVIDENCE/vm/image-prepare.log" 2>&1; then
    echo IMAGE_PREPARE_FAIL | tee "$EVIDENCE/vm/image-prepare-fail.txt"
    tail -n 40 "$EVIDENCE/vm/image-prepare.log" || true
  fi
  if [ -e /dev/kvm ]; then
    sudo chmod a+rw /dev/kvm || true
  fi
  local accel="tcg"
  if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    accel="kvm"
  fi
  local cpu="qemu64"
  if [ "$accel" = "kvm" ]; then
    cpu="host"
  fi
  python3 - << PY
import json
p = "evidence/vm/vm-capabilities.json"
data = json.load(open(p))
data["accel"] = "$accel"
data["image_name"] = "$image"
data["image_url"] = "$url"
data["image_sha512"] = "$image_sha"
data["image_reason"] = "debian-13-nocloud reached systemd and then stopped at systemd-firstboot, so sshd never started. The image is still the official nocloud build. firstboot is masked offline and the test user is injected before boot."
data["memory_mb"] = 6144
data["smp"] = 4
data["virtual_disk"] = "16G sparse"
json.dump(data, open(p, "w"), indent=2)
PY
  python3 - "$WORKDIR/serial.sock" "$EVIDENCE/vm/boot.log" << 'PY' &
import os, select, socket, sys
path, log_path = sys.argv[1], sys.argv[2]
try:
    os.unlink(path)
except FileNotFoundError:
    pass
srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
srv.bind(path)
srv.listen(1)
srv.settimeout(90)
try:
    conn, _ = srv.accept()
except socket.timeout:
    sys.exit(0)
sent = False
buf = b""
with open(log_path, "ab", buffering=0) as log:
    while True:
        ready, _, _ = select.select([conn], [], [], 5)
        if not ready:
            continue
        data = conn.recv(65536)
        if not data:
            break
        log.write(data)
        buf = (buf + data)[-12000:]
        if not sent and (b"Press any key" in buf or b"Please configure your system" in buf):
            try:
                conn.send(b"\n")
            except OSError:
                break
            sent = True
            log.write(b"\n[host sent newline to dismiss systemd-firstboot]\n")
PY
  echo $! > "$WORKDIR/serial-tap.pid"
  for _ in $(seq 1 50); do
    if [ -S "$WORKDIR/serial.sock" ]; then
      break
    fi
    sleep 0.1
  done
  sleep 0.3
  # none discards samples so the evidence artifact does not grow for the whole run.
  local audio=(-audiodev none,id=snd0 -device intel-hda -device hda-output,audiodev=snd0)
  qemu-system-x86_64 \
    -machine q35,accel="$accel" \
    -cpu "$cpu" \
    -m 6144 \
    -smp 4 \
    -drive "file=$WORKDIR/$image,if=virtio,format=qcow2" \
    -drive "file=$WORKDIR/seed.img,if=virtio,format=raw,readonly=on" \
    -netdev user,id=n0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=n0 \
    -device virtio-vga \
    -display none \
    "${audio[@]}" \
    -chardev socket,id=ser0,path="$WORKDIR/serial.sock",client=on \
    -serial chardev:ser0 \
    -pidfile "$WORKDIR/qemu.pid" \
    -daemonize \
    -D "$EVIDENCE/vm/qemu.log"
  echo "$accel" > "$EVIDENCE/vm/accel.txt"
  python3 - << PY
import json
json.dump({
    "accel": "$accel",
    "cpu": "$cpu",
    "memory_mb": 6144,
    "smp": 4,
    "image": "$image",
    "image_url": "$url",
    "image_sha512": "$image_sha",
    "display": "virtio-vga",
    "audio": "intel-hda hda-output",
    "firmware": "image-bootloader",
}, open("evidence/vm/vm-config.json", "w"), indent=2)
PY
}

wait_ssh() {
  local i
  for i in $(seq 1 120); do
    if [ -f "$WORKDIR/qemu.pid" ] && ! kill -0 "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null; then
      echo QEMU_DIED | tee "$EVIDENCE/vm/qemu-died.txt"
      tail -n 80 "$EVIDENCE/vm/boot.log" || true
      tail -n 80 "$EVIDENCE/vm/qemu.log" || true
      return 1
    fi
    if ssh "${SSH_BASE[@]}" -o ConnectTimeout=5 -p 2222 louksna@127.0.0.1 true; then
      echo "SSH_READY $i"
      return 0
    fi
    sleep 10
  done
  echo SSH_TIMEOUT | tee "$EVIDENCE/vm/ssh-timeout.txt"
  echo "--- boot.log tail ---"
  tail -n 120 "$EVIDENCE/vm/boot.log" || true
  echo "--- qemu.log tail ---"
  tail -n 80 "$EVIDENCE/vm/qemu.log" || true
  return 1
}

guest() {
  ssh "${SSH_BASE[@]}" -p 2222 louksna@127.0.0.1 "$@"
}

gates() {
  log G23
  python3 validation/debian13/g23_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g23-stdout.txt" || true
  python3 validation/debian13/g24_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g24-stdout.txt" || true
}

main() {
  preflight || true
  audit
  host_575
  if [ "$FINAL" -ne 0 ]; then
    gates
    return 0
  fi
  sudo apt-get update
  sudo apt-get install -y gh curl ca-certificates python3
  fetch_artifacts || { gates; return 0; }
  boot_vm || { gates; return 0; }
  if ! wait_ssh; then
    FINAL=2
    gates
    return 0
  fi
  scp "${SSH_BASE[@]}" -P 2222 \
    "$EVIDENCE/artifacts/LOUKSNA.deb" "$EVIDENCE/artifacts/LOUKSNA.sh" \
    louksna@127.0.0.1:/var/tmp/
  scp "${SSH_BASE[@]}" -P 2222 \
    validation/debian13/guest-install.sh louksna@127.0.0.1:/var/tmp/guest-install.sh
  scp "${SSH_BASE[@]}" -P 2222 \
    validation/debian13/probe_original.py louksna@127.0.0.1:/var/tmp/probe_original.py
  scp "${SSH_BASE[@]}" -P 2222 \
    validation/luna/agent.py louksna@127.0.0.1:/var/tmp/luna-agent.py
  scp "${SSH_BASE[@]}" -r -P 2222 \
    "$ROOT/louksna/mra_suite" louksna@127.0.0.1:/var/tmp/mra_suite_src
  guest "sudo bash /var/tmp/guest-install.sh" | tee "$EVIDENCE/vm/guest-install.stdout" || FINAL=2
  guest "sudo cp /var/log/louksna-guest-install.log /var/tmp/guest-install.log || true"
  scp "${SSH_BASE[@]}" -P 2222 \
    louksna@127.0.0.1:/var/tmp/guest-install.log "$EVIDENCE/vm/guest-install.log" || true
  log REBOOT
  guest "sudo systemctl reboot" || true
  sleep 20
  if ! wait_ssh; then
    echo REBOOT_SSH_TIMEOUT | tee "$EVIDENCE/vm/reboot-timeout.txt"
    FINAL=2
    gates
    return 0
  fi
  guest "for i in \$(seq 1 36); do if pgrep -x plasmashell >/dev/null && ps -C kwin_wayland >/dev/null 2>&1; then echo GRAPHICAL_READY \$i; exit 0; fi; sleep 5; done; echo GRAPHICAL_TIMEOUT; exit 1" | tee "$EVIDENCE/vm/graphical-wait.txt" || true
  guest "sudo python3 /var/tmp/luna-agent.py --out /var/tmp/luna-out" | tee "$EVIDENCE/luna/luna-stdout.txt" || FINAL=2
  guest "sudo rm -rf /usr/lib/louksna/mra_suite/__pycache__ /opt/louksna-sh/usr/lib/louksna/mra_suite/__pycache__; sudo mkdir -p /usr/lib/louksna/luna /opt/louksna-sh/usr/lib/louksna/luna /usr/lib/louksna/mra_suite /opt/louksna-sh/usr/lib/louksna/mra_suite && sudo cp /var/tmp/mra_suite_src/*.py /usr/lib/louksna/mra_suite/ && sudo cp /var/tmp/mra_suite_src/*.py /opt/louksna-sh/usr/lib/louksna/mra_suite/ && sudo cp /var/tmp/luna-agent.py /usr/lib/louksna/luna/agent.py && sudo cp /var/tmp/luna-agent.py /opt/louksna-sh/usr/lib/louksna/luna/agent.py && sudo python3 /usr/lib/louksna/luna/agent.py --manifest && sudo python3 /opt/louksna-sh/usr/lib/louksna/luna/agent.py --manifest" | tee "$EVIDENCE/luna/agent-integration.txt" || FINAL=2
  guest "sudo python3 /var/tmp/probe_original.py" | tee "$EVIDENCE/blockers/probe-stdout.txt" || true
  guest "sudo cat /var/tmp/blocker-register.json" > "$EVIDENCE/blockers/guest-blocker-register.json" || true
  python3 - << 'PY'
import json
from pathlib import Path
guest = Path("evidence/blockers/guest-blocker-register.json")
host = Path("evidence/blockers/host-575.json")
rows = json.loads(guest.read_text()) if guest.is_file() else []
if host.is_file():
    one = json.loads(host.read_text())
    if isinstance(one, dict) and one.get("status") == "PASS_FUNCTIONAL":
        rows = [row for row in rows if row.get("n") != 575]
        one["where"] = "github-hosted-runner"
        rows.append(one)
    elif not any(row.get("n") == 575 for row in rows) and isinstance(one, dict):
        one["where"] = "github-hosted-runner"
        rows.append(one)
Path("evidence/blockers/blocker-register.json").write_text(json.dumps(rows, indent=2) + "\n")
PY
  guest "sudo cat /var/tmp/luna-out/agent-53-case-execution.json" > "$EVIDENCE/luna/agent-53-case-execution.json" || FINAL=2
  guest "sudo cat /var/tmp/luna-out/agent-manifest.json" > "$EVIDENCE/luna/agent-manifest.json" || true
  guest "grep -E '^(VERSION_ID|ID|PRETTY_NAME)=' /etc/os-release; echo ---; tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/debian-version.txt" || true
  guest "tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/pid1.txt" || true
  guest "systemctl is-system-running || true; systemctl --no-pager --failed || true" > "$EVIDENCE/vm/systemd-status.txt" || true
  guest "loginctl list-sessions --no-legend || true; echo ---; for s in \$(loginctl list-sessions --no-legend | awk '{print \$1}'); do loginctl show-session \$s -p Id -p Name -p Type -p State -p Display; echo ---; done" > "$EVIDENCE/vm/loginctl-sessions.txt" || true
  guest "uid=\$(id -u louksna); echo UID:\$uid; ls -l /run/user/\$uid 2>/dev/null || true; echo ---; ls /usr/share/wayland-sessions 2>/dev/null || true" > "$EVIDENCE/vm/display-session.txt" || true
  guest "uid=\$(id -u louksna); sock=\$(find /run/user/\$uid -maxdepth 1 -type s -name 'wayland-*' 2>/dev/null | head -n 1); if [ -n \"\$sock\" ]; then echo WAYLAND_SOCKET=yes; echo \"\$sock\"; else echo WAYLAND_SOCKET=no; fi; if ps -C kwin_wayland >/dev/null 2>&1; then echo KWIN=yes; else echo KWIN=no; fi; if pgrep -x plasmashell >/dev/null; then echo PLASMA=yes; else echo PLASMA=no; fi" > "$EVIDENCE/vm/wayland-checks.txt" || true
  guest "ls -l /dev/dri 2>/dev/null || echo NO_DRI" > "$EVIDENCE/vm/graphics-checks.txt" || true
  guest "uid=\$(id -u louksna); if [ -d /dev/snd ]; then echo SND=yes; ls /dev/snd; else echo SND=no; fi; if XDG_RUNTIME_DIR=/run/user/\$uid pactl info >/tmp/pactl.txt 2>/tmp/pactl.err; then echo PACTL=yes; else echo PACTL=no; fi" > "$EVIDENCE/vm/audio-checks.txt" || true
  guest "getent hosts deb.debian.org || true; ping -c 1 -W 5 deb.debian.org || true" > "$EVIDENCE/vm/network-checks.txt" || true
  gates
  if [ "$FINAL" -eq 0 ]; then
    python3 - << 'PY'
import json, sys
from pathlib import Path
v = json.loads(Path("evidence/certification/certification-verdict.json").read_text())
sys.exit(0 if v.get("product_certification") == "CERTIFIED" else 2)
PY
    FINAL=$?
  fi
}

cleanup() {
  if [ -f "$WORKDIR/serial-tap.pid" ]; then
    kill "$(cat "$WORKDIR/serial-tap.pid")" 2>/dev/null || true
  fi
  if [ -f "$WORKDIR/qemu.pid" ]; then
    kill "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null || true
  fi
}
trap cleanup EXIT
main
log "FINAL $FINAL"
exit "$FINAL"
