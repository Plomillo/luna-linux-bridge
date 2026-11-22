#!/bin/bash
# Debian 13 QEMU validation on the GitHub-hosted ubuntu-24.04 runner.
# Does not re-run the 36 historical tests or the 803 preserved cases.
set -u
ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT"
export GH_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
EVIDENCE="$ROOT/evidence"
WORKDIR="${RUNNER_TEMP:-/tmp}/louksna-vm"
mkdir -p "$EVIDENCE/vm" "$EVIDENCE/artifacts" "$EVIDENCE/luna" "$EVIDENCE/blockers" "$EVIDENCE/certification" "$WORKDIR"
export EVIDENCE REPO="$ROOT"
FINAL=0

log() { echo "STAGE $(date -u +%H:%M:%S) $*"; }

preflight() {
  log PRECHECK
  python3 - << 'PY' > "$EVIDENCE/vm/vm-capabilities.json"
import json, os, shutil
from pathlib import Path
def slurp(path):
    p = Path(path)
    return p.read_text().strip() if p.is_file() else ""
mem = {}
for line in Path("/proc/meminfo").read_text().splitlines():
    k, v = line.split(":", 1)
    mem[k] = v.strip()
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
    "image": os.environ.get("ImageOS", ""),
}, indent=2))
PY
  cat "$EVIDENCE/vm/vm-capabilities.json"
  free_b=$(python3 -c 'import json;print(json.load(open("'"$EVIDENCE"'/vm/vm-capabilities.json"))["disk_free_bytes"])')
  if [ "$free_b" -lt $((8 * 1024 * 1024 * 1024)) ]; then
    echo "DISK_BELOW_8G" | tee "$EVIDENCE/vm/disk-stop.txt"
    FINAL=2
    return 1
  fi
}

audit() {
  log AUDIT
  python3 validation/debian13/audit.py || FINAL=2
}

fetch_artifacts() {
  log ARTIFACTS
  gh run download 45010622254 --repo Plomillo/luna-linux-bridge --name louksna-installers --dir "$EVIDENCE/artifacts"
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
  sudo apt-get install -y qemu-system-x86 qemu-utils cloud-image-utils curl ca-certificates
  local url="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-nocloud-amd64.qcow2"
  local sums="$WORKDIR/SHA512SUMS"
  curl -fL --retry 3 -o "$sums" "https://cloud.debian.org/images/cloud/trixie/latest/SHA512SUMS"
  curl -fL --retry 3 -o "$WORKDIR/debian-13-nocloud-amd64.qcow2" "$url"
  (cd "$WORKDIR" && sha512sum -c SHA512SUMS --ignore-missing)
  if [ $? -ne 0 ]; then
    echo IMAGE_HASH_FAIL | tee "$EVIDENCE/vm/image-hash-fail.txt"
    FINAL=2
    return 1
  fi
  qemu-img info "$WORKDIR/debian-13-nocloud-amd64.qcow2" > "$EVIDENCE/vm/image-info.txt"
  qemu-img resize "$WORKDIR/debian-13-nocloud-amd64.qcow2" 12G
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
users:
  - name: louksna
    gecos: LOUKSNA validation
    groups: [sudo, audio, video, render, netdev]
    shell: /bin/bash
    sudo: ALL=(ALL) NOPASSWD:ALL
    ssh_authorized_keys:
      - ${pub}
ssh_pwauth: false
disable_root: true
EOF
  cloud-localds "$WORKDIR/seed.img" "$WORKDIR/user-data" "$WORKDIR/meta-data"
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
p="evidence/vm/vm-capabilities.json"
data=json.load(open(p))
data["accel"]="$accel"
data["image_url"]="https://cloud.debian.org/images/cloud/trixie/latest/debian-13-nocloud-amd64.qcow2"
data["image_sha512"]="f401bd078ca7b0d854592df16997972240ce5d4ac68c43f776bbea7f173594771bc979261c89b06022f2f2faf3cc7c3e3c6ff9d701eb2fed9c8a8103b0dc64ea"
json.dump(data, open(p,"w"), indent=2)
PY
  local audio=()
  if qemu-system-x86_64 -audiodev help >/tmp/audio-help.txt 2>&1; then
    audio=(-audiodev wav,id=snd0,path="$EVIDENCE/vm/guest.wav" -device intel-hda -device hda-duplex,audiodev=snd0)
  fi
  qemu-system-x86_64 \
    -machine q35,accel="$accel" \
    -cpu "$cpu" \
    -m 6144 \
    -smp 4 \
    -drive "file=$WORKDIR/debian-13-nocloud-amd64.qcow2,if=virtio,format=qcow2" \
    -drive "file=$WORKDIR/seed.img,if=virtio,format=raw" \
    -netdev user,id=n0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=n0 \
    -device virtio-vga \
    -display none \
    "${audio[@]}" \
    -serial "file:$EVIDENCE/vm/boot.log" \
    -pidfile "$WORKDIR/qemu.pid" \
    -daemonize
  echo "$accel" > "$EVIDENCE/vm/accel.txt"
}

wait_ssh() {
  local i
  for i in $(seq 1 180); do
    if ssh -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5 -p 2222 louksna@127.0.0.1 true; then
      echo "SSH_READY $i"
      return 0
    fi
    sleep 10
  done
  echo SSH_TIMEOUT | tee "$EVIDENCE/vm/ssh-timeout.txt"
  return 1
}

guest() {
  ssh -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -p 2222 louksna@127.0.0.1 "$@"
}

copy_to_guest() {
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 "$@" louksna@127.0.0.1:/var/tmp/
}

collect_guest_text() {
  guest "grep -E '^(VERSION_ID|ID|PRETTY_NAME)=' /etc/os-release; echo ---; tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/debian-version.txt" || true
  guest "tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/pid1.txt" || true
  guest "systemctl is-system-running || true; systemctl --no-pager --failed || true" > "$EVIDENCE/vm/systemd-status.txt" || true
  guest "loginctl list-sessions --no-legend || true; echo ---; for s in \$(loginctl list-sessions --no-legend | awk '{print \$1}'); do loginctl show-session \$s -p Id -p Name -p Type -p State -p Display; echo ---; done" > "$EVIDENCE/vm/loginctl-sessions.txt" || true
  guest "uid=\$(id -u louksna); echo UID:\$uid; ls -l /run/user/\$uid 2>/dev/null || true; echo ---; ls /usr/share/wayland-sessions 2>/dev/null || true" > "$EVIDENCE/vm/display-session.txt" || true
  guest "uid=\$(id -u louksna); sock=\$(find /run/user/\$uid -maxdepth 1 -type s -name 'wayland-*' 2>/dev/null | head -n 1); if [ -n \"\$sock\" ]; then echo WAYLAND_SOCKET=yes; echo \"\$sock\"; else echo WAYLAND_SOCKET=no; fi; if pgrep -f kwin >/dev/null; then echo KWIN=yes; else echo KWIN=no; fi; if pgrep -x plasmashell >/dev/null; then echo PLASMA=yes; else echo PLASMA=no; fi" > "$EVIDENCE/vm/wayland-checks.txt" || true
  guest "ls -l /dev/dri 2>/dev/null || echo NO_DRI" > "$EVIDENCE/vm/graphics-checks.txt" || true
  guest "if [ -d /dev/snd ]; then echo SND=yes; ls /dev/snd; else echo SND=no; fi; if command -v pactl >/dev/null && pactl info >/tmp/pactl.txt 2>/tmp/pactl.err; then echo PACTL=yes; else echo PACTL=no; fi" > "$EVIDENCE/vm/audio-checks.txt" || true
  guest "getent hosts deb.debian.org || true; ping -c 1 -W 5 deb.debian.org || true" > "$EVIDENCE/vm/network-checks.txt" || true
}

main() {
  preflight || return 0
  audit
  sudo apt-get update
  sudo apt-get install -y gh curl ca-certificates python3
  fetch_artifacts || return 0
  boot_vm || return 0
  if ! wait_ssh; then
    FINAL=2
    return 0
  fi
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
    "$EVIDENCE/artifacts/LOUKSNA.deb" "$EVIDENCE/artifacts/LOUKSNA.sh" \
    louksna@127.0.0.1:/var/tmp/
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
    validation/debian13/guest-install.sh louksna@127.0.0.1:/var/tmp/guest-install.sh
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
    validation/debian13/probe_original.py louksna@127.0.0.1:/var/tmp/probe_original.py
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
    validation/luna/agent.py louksna@127.0.0.1:/var/tmp/luna-agent.py
  guest "sudo bash /var/tmp/guest-install.sh" | tee "$EVIDENCE/vm/guest-install.stdout" || FINAL=2
  guest "sudo cp /var/log/louksna-guest-install.log /var/tmp/guest-install.log || true"
  scp -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -P 2222 \
    louksna@127.0.0.1:/var/tmp/guest-install.log "$EVIDENCE/vm/guest-install.log" || true
  log REBOOT
  guest "sudo systemctl reboot" || true
  sleep 20
  if ! wait_ssh; then
    echo REBOOT_SSH_TIMEOUT | tee "$EVIDENCE/vm/reboot-timeout.txt"
    FINAL=2
    return 0
  fi
  # Graphical target may still be starting.
  sleep 40
  guest "sudo python3 /var/tmp/luna-agent.py --out /var/tmp/luna-out" | tee "$EVIDENCE/luna/luna-stdout.txt" || FINAL=2
  guest "sudo python3 /var/tmp/probe_original.py" | tee "$EVIDENCE/blockers/probe-stdout.txt" || true
  guest "sudo cat /var/tmp/blocker-register.json" > "$EVIDENCE/blockers/blocker-register.json" || true
  guest "sudo cat /var/tmp/luna-out/agent-53-case-execution.json" > "$EVIDENCE/luna/agent-53-case-execution.json" || FINAL=2
  guest "sudo cat /var/tmp/luna-out/agent-manifest.json" > "$EVIDENCE/luna/agent-manifest.json" || true
  collect_guest_text
  log G23
  python3 validation/debian13/g23_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g23-stdout.txt" || true
  python3 validation/debian13/g24_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g24-stdout.txt" || true
  if [ "$FINAL" -eq 0 ]; then
    python3 - << 'PY'
import json, sys
from pathlib import Path
v=json.loads(Path("evidence/certification/certification-verdict.json").read_text())
sys.exit(0 if v.get("product_certification")=="CERTIFIED" else 2)
PY
    FINAL=$?
  fi
}

cleanup() {
  if [ -f "$WORKDIR/qemu.pid" ]; then
    kill "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null || true
  fi
}
trap cleanup EXIT
main
log "FINAL $FINAL"
exit "$FINAL"
