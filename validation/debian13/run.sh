#!/bin/bash
# Debian 13 QEMU validation on the GitHub-hosted ubuntu-24.04 runner.
# Does not re-run the 36 historical tests or the 803 preserved cases.
# A green workflow is not product certification. G24 stays closed unless G23 passes.
set -uo pipefail
ROOT="${GITHUB_WORKSPACE:-$(pwd)}"
cd "$ROOT"
export GH_TOKEN="${GITHUB_TOKEN:-${GH_TOKEN:-}}"
EVIDENCE="$ROOT/evidence"
WORKDIR="${RUNNER_TEMP:-/tmp}/louksna-vm"
mkdir -p "$EVIDENCE/vm" "$EVIDENCE/artifacts" "$EVIDENCE/luna" "$EVIDENCE/blockers" "$EVIDENCE/certification" "$EVIDENCE/cases" "$WORKDIR"
export EVIDENCE REPO="$ROOT"
FINAL=0
SSH_BASE=(-4 -i "$WORKDIR/vmkey" -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o IdentitiesOnly=yes -o ServerAliveInterval=30 -o ServerAliveCountMax=20)

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
  if [ "${GITHUB_ACTIONS:-}" = "true" ]; then
    case "${RUNNER_ENVIRONMENT:-}/${ImageOS:-}" in
      github-hosted/ubuntu24*) ;;
      *)
        echo RUNNER_NOT_STANDARD | tee "$EVIDENCE/vm/runner-stop.txt"
        FINAL=2
        return 1
        ;;
    esac
  fi
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
  python3 - << 'PY'
import json
from pathlib import Path
Path("evidence/artifacts/provenance.json").write_text(json.dumps({
    "repository": "Plomillo/luna-linux-bridge",
    "branch": "work/luna-v3-reconstruction-20261119",
    "commit": "db77c2f27da8060f0362ac8f36cc8860de94c882",
    "workflow": "louksna-canonical-build",
    "run_id": "45010622254",
    "artifact": "louksna-installers",
    "role": "immutable reference build, not this validation run",
    "deb_sha256": "fa372953f47c61019202995754cec7d688adf973c4491218e3b4db2465163657",
    "sh_sha256": "d74a0b5eefeba4a5777c87b97008169a540aee25861fb883f0943379cf7db8f7",
    "verified_before_use": True,
}, indent=2) + "\n")
PY
}

boot_vm() {
  log VM
  sudo apt-get update
  sudo apt-get install -y qemu-system-x86 qemu-utils cloud-image-utils cloud-guest-utils e2fsprogs gdisk parted curl ca-certificates python3 pulseaudio
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
  qemu-img resize "$WORKDIR/$image" 20G
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
    FINAL=2
    return 1
  fi
  if [ -e /dev/kvm ]; then
    sudo chmod a+rw /dev/kvm || true
  fi
  local audio_backend="wav"
  local runtime="${XDG_RUNTIME_DIR:-$WORKDIR/runtime}"
  mkdir -p "$runtime"
  chmod 700 "$runtime"
  if XDG_RUNTIME_DIR="$runtime" pulseaudio --start --exit-idle-time=-1; then
    if XDG_RUNTIME_DIR="$runtime" pactl load-module module-null-sink sink_name=louksna sink_properties=device.description=louksna; then
      audio_backend="pa"
    fi
  fi
  echo "$audio_backend" > "$EVIDENCE/vm/audio-backend.txt"
  if [ "$audio_backend" = "pa" ]; then
    local ready=0
    for _ in $(seq 1 25); do
      if [ -S "$runtime/pulse/native" ]; then
        ready=1
        break
      fi
      sleep 0.2
    done
    if [ "$ready" -ne 1 ]; then
      echo PA_SOCKET_ABSENT | tee "$EVIDENCE/vm/pa-socket-absent.txt"
      audio_backend="wav"
      echo wav > "$EVIDENCE/vm/audio-backend.txt"
    fi
  fi
  echo "$runtime" > "$EVIDENCE/vm/audio-runtime.txt"
  python3 - << PY
import json
p = "evidence/vm/vm-capabilities.json"
data = json.load(open(p))
data["image_name"] = "$image"
data["image_url"] = "$url"
data["image_sha512"] = "$image_sha"
data["image_reason"] = "official debian-13-nocloud. systemd-firstboot is masked in the image before boot."
data["memory_mb"] = 6144
data["smp"] = 4
data["virtual_disk"] = "20G sparse"
data["audio_backend"] = "$audio_backend"
json.dump(data, open(p, "w"), indent=2)
PY
  : > "$EVIDENCE/vm/boot.log"
  launch_qemu() {
    local accel="$1"
    local cpu="$2"
    local -a audio
    if [ "$audio_backend" = "pa" ]; then
      audio=(-audiodev "pa,id=snd0,server=unix:${runtime}/pulse/native" -device intel-hda -device hda-duplex,audiodev=snd0)
    else
      audio=(-audiodev "wav,id=snd0,path=${EVIDENCE}/vm/host-playback.wav" -device intel-hda -device hda-output,audiodev=snd0)
    fi
    qemu-system-x86_64 \
      -machine "pc,accel=${accel}" \
      -cpu "$cpu" \
      -m 6144 \
      -smp 4 \
      -drive "file=${WORKDIR}/${image},if=virtio,format=qcow2" \
      -drive "file=${WORKDIR}/seed.img,if=virtio,format=raw,readonly=on" \
      -netdev user,id=n0,hostfwd=tcp::2222-:22 \
      -device virtio-net-pci,netdev=n0 \
      -vga virtio \
      -vnc 127.0.0.1:1 \
      -monitor "unix:${WORKDIR}/monitor.sock,server,nowait" \
      "${audio[@]}" \
      -serial "file:${EVIDENCE}/vm/boot.log" \
      -pidfile "$WORKDIR/qemu.pid" \
      -daemonize \
      -D "$EVIDENCE/vm/qemu.log"
  }
  qemu-system-x86_64 --version > "$EVIDENCE/vm/qemu-version.txt" || true
  local accel="tcg"
  local cpu="qemu64"
  rm -f "$WORKDIR/qemu.pid" "$WORKDIR/monitor.sock"
  start_alive() {
    local try_accel="$1"
    local try_cpu="$2"
    rm -f "$WORKDIR/qemu.pid" "$WORKDIR/monitor.sock"
    : > "$EVIDENCE/vm/boot.log"
    if ! launch_qemu "$try_accel" "$try_cpu"; then
      if [ -f "$WORKDIR/qemu.pid" ]; then
        kill "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null || true
      fi
      return 1
    fi
    sleep 2
    if [ ! -f "$WORKDIR/qemu.pid" ] || ! kill -0 "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null; then
      if [ -f "$WORKDIR/qemu.pid" ]; then
        kill "$(cat "$WORKDIR/qemu.pid")" 2>/dev/null || true
      fi
      return 1
    fi
    accel="$try_accel"
    cpu="$try_cpu"
    return 0
  }
  if [ -r /dev/kvm ] && [ -w /dev/kvm ]; then
    if ! start_alive kvm host; then
      echo KVM_START_FAIL | tee "$EVIDENCE/vm/kvm-start-fail.txt"
      cp "$EVIDENCE/vm/qemu.log" "$EVIDENCE/vm/qemu-kvm.log" 2>/dev/null || true
    fi
  fi
  if [ "$accel" != "kvm" ]; then
    if ! start_alive tcg qemu64; then
      if [ "$audio_backend" = "pa" ]; then
        echo PA_START_FAIL | tee "$EVIDENCE/vm/pa-start-fail.txt"
        audio_backend="wav"
        echo wav > "$EVIDENCE/vm/audio-backend.txt"
        if ! start_alive tcg qemu64; then
          echo QEMU_START_FAIL | tee "$EVIDENCE/vm/qemu-start-fail.txt"
          FINAL=2
          return 1
        fi
      else
        echo QEMU_START_FAIL | tee "$EVIDENCE/vm/qemu-start-fail.txt"
        FINAL=2
        return 1
      fi
    fi
  fi
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
    "display": "vnc://127.0.0.1:5901",
    "graphics": "virtio-vga",
    "audio_backend": "$audio_backend",
    "firmware": "image-bootloader",
    "monitor": "unix",
}, open("evidence/vm/vm-config.json", "w"), indent=2)
caps = json.load(open("evidence/vm/vm-capabilities.json"))
caps["accel"] = "$accel"
caps["audio_backend"] = "$audio_backend"
json.dump(caps, open("evidence/vm/vm-capabilities.json", "w"), indent=2)
PY
}

screendump() {
  local dest="$1"
  python3 - "$WORKDIR/monitor.sock" "$dest" << 'PY'
import socket, sys
sock, dest = sys.argv[1], sys.argv[2]
try:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(8)
    client.connect(sock)
    try:
        client.recv(4096)
    except socket.timeout:
        pass
    client.sendall(f"screendump {dest}\n".encode())
    data = b""
    while True:
        try:
            chunk = client.recv(4096)
        except socket.timeout:
            break
        if not chunk:
            break
        data += chunk
    sys.stdout.write(data.decode(errors="replace")[:500])
except OSError as exc:
    print(f"SCREENDUMP_FAIL {exc}")
    raise SystemExit(1)
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

overlay_suite() {
  if ! guest bash -s << 'EOS' | tee "$EVIDENCE/vm/suite-overlay.txt"
set -u
src=""
for candidate in /var/tmp/mra_suite /var/tmp/mra_suite_src /var/tmp/mra_suite_src/mra_suite; do
  if [ -f "$candidate/os_w.py" ]; then
    src=$candidate
    break
  fi
done
if [ -z "$src" ]; then
  echo OVERLAY_SOURCE_ABSENT
  find /var/tmp -name os_w.py -maxdepth 3 || true
  exit 1
fi
if ! grep -q '_apt_index_facts' "$src/os_w.py"; then
  echo OVERLAY_SOURCE_STALE "$src"
  exit 1
fi
sudo rm -rf /usr/lib/louksna/mra_suite/__pycache__ /opt/louksna-sh/usr/lib/louksna/mra_suite/__pycache__
sudo mkdir -p /usr/lib/louksna/mra_suite /opt/louksna-sh/usr/lib/louksna/mra_suite
sudo cp "$src"/*.py /usr/lib/louksna/mra_suite/
sudo cp "$src"/*.py /opt/louksna-sh/usr/lib/louksna/mra_suite/
sudo python3 -c 'import sys; sys.path.insert(0, "/usr/lib/louksna/mra_suite"); import hyp_w, os_w, part2b_w; assert hasattr(os_w, "_apt_index_facts"), os_w.__file__; assert hasattr(part2b_w, "_graphical_facts"), part2b_w.__file__; assert hasattr(hyp_w, "_kde_wayland"), hyp_w.__file__; print("OVERLAY_IMPORT_OK", os_w.__file__)'
EOS
  then
    echo OVERLAY_FAIL | tee -a "$EVIDENCE/vm/suite-overlay.txt"
    FINAL=2
    return 1
  fi
}

gates() {
  log G23
  python3 validation/debian13/g23_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g23-stdout.txt" || true
  python3 validation/debian13/g24_check.py "$EVIDENCE" | tee "$EVIDENCE/certification/g24-stdout.txt" || true
  mkdir -p "$EVIDENCE/resumption"
  gh run list --repo Plomillo/luna-linux-bridge --branch work/luna-v3-reconstruction-20261119 --workflow louksna-debian13-kde-wayland-validation.yml --limit 10 --json databaseId,status,conclusion,headSha,createdAt,url,event > "$EVIDENCE/resumption/run-inventory.json" || echo '[]' > "$EVIDENCE/resumption/run-inventory.json"
  python3 - << 'PY'
import json
from pathlib import Path
root = Path("evidence/resumption")
root.mkdir(parents=True, exist_ok=True)
g23_path = Path("evidence/certification/independent-validation.json")
g24_path = Path("evidence/certification/certification-verdict.json")
g23 = json.loads(g23_path.read_text()) if g23_path.is_file() else {"verdict": "ABSENT", "failures": ["G23_NOT_RUN"]}
g24 = json.loads(g24_path.read_text()) if g24_path.is_file() else {"verdict": "CLOSED", "product_certification": "NOT_CERTIFIED"}
(root / "unfinished-stages.json").write_text(json.dumps({
    "g23": g23.get("verdict"),
    "g24": g24.get("verdict"),
    "product_certification": g24.get("product_certification"),
    "open_failures": g23.get("failures", []),
    "historical_36_reexecuted": 0,
    "original_803_reexecuted": 0,
}, indent=2) + "\n")
(root / "resumption-log.json").write_text(json.dumps({
    "reference_run": "45010622254",
    "previous_validation_run": "45114379983",
    "previous_failure": "Run 45114379983 installed the Android SDK, then SUB-045 reinstalled the immutable deb and wiped the repaired suite. The probe correctly refused that suite. SUB-033 failed because the 12G disk no longer had 3G free.",
    "this_executor": "validation/debian13/run.sh",
    "active_at_start": False,
}, indent=2) + "\n")
PY
}

main() {
  mkdir -p "$EVIDENCE/resumption"
  python3 - << 'PY'
import json, os, subprocess
from pathlib import Path
root = Path(os.environ["EVIDENCE"]) / "resumption"
root.mkdir(parents=True, exist_ok=True)
def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True).stdout.strip()
state = {
    "resumed_from_run": "45114379983",
    "reference_run": "45010622254",
    "reference_commit": "db77c2f27da8060f0362ac8f36cc8860de94c882",
    "head": git("rev-parse", "HEAD"),
    "branch": git("rev-parse", "--abbrev-ref", "HEAD"),
    "previous_failure": "run 45114379983 installed a real Android SDK and a repaired suite, then the deb reinstall restored the unconditional blockers and the 12G disk missed the 3G free check",
    "historical_36_reexecuted": 0,
    "original_803_reexecuted": 0,
}
(root / "resumption-state.json").write_text(json.dumps(state, indent=2) + "\n")
PY
  if ! preflight; then
    gates
    return 0
  fi
  audit
  host_575
  if [ "$FINAL" -ne 0 ]; then
    gates
    return 0
  fi
  sudo apt-get update
  sudo apt-get install -y gh curl ca-certificates python3
  fetch_artifacts || { gates; return 0; }
  python3 validation/debian13/derive_installers.py \
    "$EVIDENCE/artifacts/LOUKSNA.deb" \
    "$EVIDENCE/artifacts/LOUKSNA.sh" \
    validation/luna/agent.py \
    "$EVIDENCE/artifacts/derived" | tee "$EVIDENCE/artifacts/derived-build.txt" || FINAL=2
  boot_vm || { gates; return 0; }
  if ! wait_ssh; then
    FINAL=2
    gates
    return 0
  fi
  scp "${SSH_BASE[@]}" -P 2222 \
    "$EVIDENCE/artifacts/LOUKSNA.deb" "$EVIDENCE/artifacts/LOUKSNA.sh" \
    validation/debian13/guest-install.sh \
    validation/debian13/android-sdk.sh \
    validation/debian13/probe_original.py \
    validation/debian13/as_session.py \
    validation/debian13/play_tone.py \
    validation/debian13/expectations.json \
    validation/luna/agent.py \
    louksna@127.0.0.1:/var/tmp/
  guest "cp /var/tmp/agent.py /var/tmp/luna-agent.py"
  scp "${SSH_BASE[@]}" -r -P 2222 \
    "$ROOT/louksna/mra_suite" louksna@127.0.0.1:/var/tmp/
  guest "sudo bash /var/tmp/guest-install.sh" | tee "$EVIDENCE/vm/guest-install.stdout" || FINAL=2
  guest "sudo cp /var/log/louksna-guest-install.log /var/tmp/guest-install.log || true"
  scp "${SSH_BASE[@]}" -P 2222 \
    louksna@127.0.0.1:/var/tmp/guest-install.log "$EVIDENCE/vm/guest-install.log" || true
  log REBOOT
  guest "sudo systemctl reboot" || true
  sleep 25
  if ! wait_ssh; then
    echo REBOOT_SSH_TIMEOUT | tee "$EVIDENCE/vm/reboot-timeout.txt"
    FINAL=2
    gates
    return 0
  fi
  guest "for i in \$(seq 1 60); do if pgrep -x plasmashell >/dev/null && ps -C kwin_wayland >/dev/null 2>&1; then echo GRAPHICAL_READY \$i; exit 0; fi; sleep 5; done; echo GRAPHICAL_TIMEOUT; systemctl status sddm --no-pager || true; journalctl -u sddm -b --no-pager | tail -n 80 || true; exit 1" | tee "$EVIDENCE/vm/graphical-wait.txt" || FINAL=2
  screendump "$EVIDENCE/vm/screen.ppm" | tee "$EVIDENCE/vm/screendump.txt" || echo SCREENDUMP_FAIL | tee -a "$EVIDENCE/vm/screendump.txt"
  log AUDIO
  backend=$(cat "$EVIDENCE/vm/audio-backend.txt" 2>/dev/null || echo wav)
  runtime=$(cat "$EVIDENCE/vm/audio-runtime.txt" 2>/dev/null || echo "$WORKDIR/runtime")
  if [ "$backend" = "pa" ]; then
    XDG_RUNTIME_DIR="$runtime" timeout 12 parecord -d louksna.monitor --file-format=wav "$EVIDENCE/vm/host-capture.wav" > "$EVIDENCE/vm/parecord.txt" 2>&1 &
    echo $! > "$WORKDIR/parecord.pid"
    sleep 1
  fi
  guest "python3 /var/tmp/play_tone.py /tmp/louksna-tone.wav && sudo python3 /var/tmp/as_session.py bash -lc 'paplay /tmp/louksna-tone.wav || pw-play /tmp/louksna-tone.wav'" | tee "$EVIDENCE/vm/guest-playback.txt" || true
  if [ -f "$WORKDIR/parecord.pid" ]; then
    wait "$(cat "$WORKDIR/parecord.pid")" || true
  fi
  python3 - << 'PY'
import json, struct, wave
from pathlib import Path
candidates = [Path("evidence/vm/host-capture.wav"), Path("evidence/vm/host-playback.wav")]
chosen = next((path for path in candidates if path.is_file() and path.stat().st_size > 44), None)
record = {"non_silent": False, "peak": 0, "path": str(chosen) if chosen else "", "bytes": chosen.stat().st_size if chosen else 0}
if chosen:
    try:
        with wave.open(str(chosen)) as handle:
            raw = handle.readframes(min(handle.getnframes(), 300000))
        peak = 0
        count = len(raw) // 2
        for index in range(0, count, 40):
            value = abs(struct.unpack_from("<h", raw, index * 2)[0])
            if value > peak:
                peak = value
        record["peak"] = peak
        record["non_silent"] = peak > 500
    except (wave.Error, EOFError) as exc:
        record["error"] = str(exc)
Path("evidence/vm/audio-playback.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(record))
PY
  guest "sudo python3 /var/tmp/as_session.py id -u; sudo python3 /var/tmp/as_session.py whoami" | tee "$EVIDENCE/luna/session-identity.txt" || FINAL=2
  python3 - << 'PY'
import json
from pathlib import Path
text = Path("evidence/luna/session-identity.txt").read_text().split()
euid = int(text[0]) if text and text[0].isdigit() else -1
user = text[1] if len(text) > 1 else ""
Path("evidence/luna/privilege.json").write_text(json.dumps({
    "euid": euid,
    "user": user,
    "helper": "runuser from an administrative ssh step; the recorded id is the dropped user",
    "admin_commands": ["SUB-030", "SUB-044", "SUB-045", "dpkg", "installer"],
}, indent=2) + "\n")
PY
  guest "mkdir -p /home/louksna/luna-out && sudo python3 /var/tmp/as_session.py python3 /var/tmp/luna-agent.py --out /home/louksna/luna-out" | tee "$EVIDENCE/luna/luna-stdout.txt" || FINAL=2
  for name in agent-53-case-execution.json agent-manifest.json agent-capabilities.json agent-failure-analysis.json agent-revalidation.json agent-run-status.json; do
    guest "cat /home/louksna/luna-out/$name" > "$EVIDENCE/luna/$name" || FINAL=2
  done
  cp "$EVIDENCE/luna/agent-53-case-execution.json" "$EVIDENCE/cases/substitute-53-results.json" 2>/dev/null || true
  python3 - << 'PY' || FINAL=2
import json
from pathlib import Path
path = Path("evidence/luna/agent-53-case-execution.json")
reg_path = Path("evidence/cases/substitute-53-register.json")
if not path.is_file() or not reg_path.is_file():
    raise SystemExit("substitute results missing")
rows = json.loads(path.read_text())
reg = json.loads(reg_path.read_text())
reg["SUBSTITUTE_53_EXECUTED"] = len(rows)
reg["SUBSTITUTE_53_RESOLVED"] = sum(1 for row in rows if row.get("pass") is True)
reg["SUBSTITUTE_53_CERTIFIED"] = 0
reg["not_originals"] = True
reg_path.write_text(json.dumps(reg, indent=2) + "\n")
PY
  if [ -f "$EVIDENCE/artifacts/derived/LOUKSNA-luna-derived.deb" ]; then
    scp "${SSH_BASE[@]}" -P 2222 \
      "$EVIDENCE/artifacts/derived/LOUKSNA-luna-derived.deb" \
      "$EVIDENCE/artifacts/derived/LOUKSNA-luna-derived.sh" \
      louksna@127.0.0.1:/var/tmp/
    guest "sudo dpkg -i /var/tmp/LOUKSNA-luna-derived.deb || sudo apt-get install -f -y" | tee "$EVIDENCE/luna/derived-deb-install.txt" || FINAL=2
    guest "sudo sh /var/tmp/LOUKSNA-luna-derived.sh --prefix /opt/louksna-sh" | tee "$EVIDENCE/luna/derived-sh-install.txt" || FINAL=2
    guest "sudo python3 /var/tmp/as_session.py /usr/bin/luna --manifest" > "$EVIDENCE/luna/agent-deb-manifest.txt" || FINAL=2
    guest "sudo python3 /var/tmp/as_session.py /opt/louksna-sh/usr/bin/luna --manifest" > "$EVIDENCE/luna/agent-sh-manifest.txt" || FINAL=2
    python3 - << 'PY' || FINAL=2
import json
from pathlib import Path
for src, dest in (
    ("evidence/luna/agent-deb-manifest.txt", "evidence/luna/agent-deb-verification.json"),
    ("evidence/luna/agent-sh-manifest.txt", "evidence/luna/agent-sh-verification.json"),
):
    text = Path(src).read_text().strip()
    start = text.find("{")
    data = json.loads(text[start:] if start >= 0 else text)
    data["executed_as"] = "louksna"
    data["identity"] = "derived-installer"
    data["originals_replaced"] = False
    Path(dest).write_text(json.dumps(data, indent=2) + "\n")
PY
  fi
  overlay_suite || true
  guest "sudo python3 /var/tmp/as_session.py systemctl --user start xdg-desktop-portal.service xdg-desktop-portal-kde.service" | tee "$EVIDENCE/vm/portals-start.txt" || echo PORTAL_START_NONZERO | tee -a "$EVIDENCE/vm/portals-start.txt"
  guest "ps -eo args | grep -E 'xdg-desktop-portal|kwin_wayland|plasmashell' | grep -v grep || true" | tee "$EVIDENCE/vm/session-processes.txt" || true
  if ! guest "sudo python3 /var/tmp/probe_original.py" | tee "$EVIDENCE/blockers/probe-stdout.txt"; then
    echo PROBE_FAIL | tee -a "$EVIDENCE/blockers/probe-stdout.txt"
    FINAL=2
  fi
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
        one["note"] = "observed live github-hosted ubuntu-24.04 environment; a runs-on label alone is not the evidence"
        rows.append(one)
    elif not any(row.get("n") == 575 for row in rows) and isinstance(one, dict):
        one["where"] = "github-hosted-runner"
        rows.append(one)
Path("evidence/blockers/blocker-register.json").write_text(json.dumps(rows, indent=2) + "\n")
Path("evidence/blockers/blocker-resolution-log.json").write_text(json.dumps({
    "probe_harness": "root",
    "reason": "apt-get and runuser inside the original probes require an administrative process; the Plasma session itself is louksna. The repaired suite is copied after installer reinstall so dpkg does not restore the unconditional blockers.",
    "rows": rows,
}, indent=2) + "\n")
PY
  guest "grep -E '^(VERSION_ID|ID|PRETTY_NAME)=' /etc/os-release; echo ---; tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/debian-version.txt" || true
  guest "tr -d '\\0' < /proc/1/comm" > "$EVIDENCE/vm/pid1.txt" || true
  guest "systemctl is-system-running || true; systemctl --no-pager --failed || true" > "$EVIDENCE/vm/systemd-status.txt" || true
  guest "loginctl list-sessions --no-legend || true; echo ---; for s in \$(loginctl list-sessions --no-legend | awk '{print \$1}'); do loginctl show-session \$s -p Id -p Name -p Type -p State -p Display; echo ---; done" > "$EVIDENCE/vm/loginctl-sessions.txt" || true
  guest "uid=\$(id -u louksna); echo UID:\$uid; ls -l /run/user/\$uid 2>/dev/null || true; echo ---; ls /usr/share/wayland-sessions 2>/dev/null || true" > "$EVIDENCE/vm/display-session.txt" || true
  guest "uid=\$(id -u louksna); sock=\$(find /run/user/\$uid -maxdepth 1 -type s -name 'wayland-*' 2>/dev/null | head -n 1); if [ -n \"\$sock\" ]; then echo WAYLAND_SOCKET=yes; echo \"\$sock\"; else echo WAYLAND_SOCKET=no; fi; if ps -C kwin_wayland >/dev/null 2>&1; then echo KWIN=yes; else echo KWIN=no; fi; if pgrep -x plasmashell >/dev/null; then echo PLASMA=yes; else echo PLASMA=no; fi" > "$EVIDENCE/vm/wayland-checks.txt" || true
  guest "ls -l /dev/dri 2>/dev/null || echo NO_DRI" > "$EVIDENCE/vm/graphics-checks.txt" || true
  guest "uid=\$(id -u louksna); if [ -d /dev/snd ]; then echo SND=yes; ls /dev/snd; else echo SND=no; fi; if XDG_RUNTIME_DIR=/run/user/\$uid pactl info >/tmp/pactl.txt 2>/tmp/pactl.err; then echo PACTL=yes; else echo PACTL=no; fi" > "$EVIDENCE/vm/audio-checks.txt" || true
  guest "getent hosts deb.debian.org || true; ping -c 1 -W 5 deb.debian.org || true" > "$EVIDENCE/vm/network-checks.txt" || true
  python3 - << 'PY'
import json
from pathlib import Path
screen = Path("evidence/vm/screen.ppm")
text = Path("evidence/vm/graphics-checks.txt").read_text() if Path("evidence/vm/graphics-checks.txt").is_file() else ""
way = Path("evidence/vm/wayland-checks.txt").read_text() if Path("evidence/vm/wayland-checks.txt").is_file() else ""
Path("evidence/vm/graphics-checks.json").write_text(json.dumps({
    "display": "vnc",
    "device": "virtio-vga",
    "screendump_bytes": screen.stat().st_size if screen.is_file() else 0,
    "dri": text.strip(),
    "wayland": way.strip(),
}, indent=2) + "\n")
PY
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
