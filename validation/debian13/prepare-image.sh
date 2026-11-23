#!/bin/bash
# Offline preparation of the official Debian cloud image.
# Masks systemd-firstboot, grows the root filesystem, and injects the test user.
# Must run as root. Does not boot a container and does not modify the published artifact.
set -u
IMAGE="${1:?image}"
PUBKEY="${2:?pubkey}"
MNT=/mnt/louksna-d13

cleanup() {
  if mountpoint -q "$MNT"; then
    umount "$MNT" || umount -l "$MNT" || true
  fi
  if [ -e /dev/nbd0 ]; then
    qemu-nbd --disconnect /dev/nbd0 >/dev/null 2>&1 || true
  fi
}
trap cleanup EXIT

if ! lsmod | awk '{print $1}' | grep -qx nbd; then
  modprobe nbd max_part=16
fi
mkdir -p "$MNT"
qemu-nbd --disconnect /dev/nbd0 >/dev/null 2>&1 || true
qemu-nbd --connect=/dev/nbd0 --format=qcow2 --cache=writeback "$IMAGE"
for _ in $(seq 1 50); do
  if compgen -G "/dev/nbd0p*" >/dev/null; then
    break
  fi
  sleep 0.2
done
echo "PARTITIONS"
blkid /dev/nbd0 /dev/nbd0p* || true
best=""
bestsize=0
for part in /dev/nbd0p*; do
  [ -e "$part" ] || continue
  kind=$(blkid -o value -s TYPE "$part" || true)
  echo "PART $part $kind"
  if [ "$kind" = "ext4" ]; then
    size=$(blockdev --getsize64 "$part")
    if [ "$size" -gt "$bestsize" ]; then
      best=$part
      bestsize=$size
    fi
  fi
done
if [ -z "$best" ]; then
  echo NO_EXT4_ROOT
  exit 1
fi
echo "ROOT $best $bestsize"
partnum=${best#/dev/nbd0p}
growpart /dev/nbd0 "$partnum" || echo GROWPART_NOCHANGE
e2fsck -f -y "$best" || echo E2FSCK_WARN
resize2fs "$best"
mount "$best" "$MNT"
if ! grep -q 'Debian' "$MNT/etc/os-release"; then
  echo NOT_DEBIAN_ROOT
  exit 1
fi
python3 - "$MNT" "$PUBKEY" << 'PY'
import pathlib, secrets, sys
root = pathlib.Path(sys.argv[1])
pub = pathlib.Path(sys.argv[2]).read_text().strip()
machine = root / "etc" / "machine-id"
machine.write_text(secrets.token_hex(16) + "\n")
unit_dir = root / "etc" / "systemd" / "system"
unit_dir.mkdir(parents=True, exist_ok=True)
link = unit_dir / "systemd-firstboot.service"
if link.is_symlink() or link.exists():
    link.unlink()
link.symlink_to("/dev/null")
sshd = None
for candidate in (root / "usr/lib/systemd/system/ssh.service", root / "lib/systemd/system/ssh.service"):
    if candidate.is_file():
        sshd = candidate
        break
if sshd is not None:
    wants = root / "etc/systemd/system/multi-user.target.wants"
    wants.mkdir(parents=True, exist_ok=True)
    enabled = wants / "ssh.service"
    if enabled.is_symlink() or enabled.exists():
        enabled.unlink()
    enabled.symlink_to("/usr/lib/systemd/system/ssh.service")
(root / "etc/hostname").write_text("louksna-d13\n")
cfg = root / "etc/cloud/cloud.cfg.d"
cfg.mkdir(parents=True, exist_ok=True)
(cfg / "99-louksna.cfg").write_text("datasource_list: [ NoCloud, None ]\n")
passwd = (root / "etc/passwd").read_text().splitlines()
uids = set()
for line in passwd:
    parts = line.split(":")
    if len(parts) > 2 and parts[2].isdigit():
        uids.add(int(parts[2]))
existing = [line.split(":") for line in passwd if line.startswith("louksna:")]
if existing:
    uid = int(existing[0][2])
else:
    uid = 1000
    while uid in uids:
        uid += 1
    with (root / "etc/passwd").open("a") as fh:
        fh.write(f"louksna:x:{uid}:{uid}:LOUKSNA validation:/home/louksna:/bin/bash\n")
    with (root / "etc/shadow").open("a") as fh:
        fh.write("louksna:!:19000:0:99999:7:::\n")
    with (root / "etc/group").open("a") as fh:
        fh.write(f"louksna:x:{uid}:\n")
    gshadow = root / "etc/gshadow"
    if gshadow.is_file():
        with gshadow.open("a") as fh:
            fh.write("louksna:!::\n")
group_file = root / "etc/group"
lines = group_file.read_text().splitlines()
out = []
for line in lines:
    parts = line.split(":")
    if parts and parts[0] in {"sudo", "audio", "video", "netdev", "cdrom"} and len(parts) >= 4:
        members = [item for item in parts[3].split(",") if item]
        if "louksna" not in members:
            members.append("louksna")
        parts[3] = ",".join(members)
        line = ":".join(parts)
    out.append(line)
group_file.write_text("\n".join(out) + "\n")
home = root / "home" / "louksna"
ssh = home / ".ssh"
ssh.mkdir(parents=True, exist_ok=True)
(ssh / "authorized_keys").write_text(pub + "\n")
for path in (home, ssh):
    path.chmod(0o700)
(ssh / "authorized_keys").chmod(0o600)
import os
os.chown(home, uid, uid)
os.chown(ssh, uid, uid)
os.chown(ssh / "authorized_keys", uid, uid)
sudoers = root / "etc/sudoers.d/louksna"
sudoers.write_text("louksna ALL=(ALL) NOPASSWD:ALL\n")
sudoers.chmod(0o440)
print(f"INJECTED uid={uid}")
PY
# The nocloud image has no openssh-server. Install it on first boot from apt.
cat > "$MNT/usr/local/sbin/louksna-bootstrap.sh" << 'EOF'
#!/bin/bash
echo BOOTSTRAP_BEGIN
export DEBIAN_FRONTEND=noninteractive
for _ in $(seq 1 60); do
  if getent hosts deb.debian.org >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
set -e
apt-get update
apt-get install -y openssh-server
install -d -m 755 /run/sshd
rm -f /etc/ssh/sshd_not_to_be_run
systemctl enable ssh.service
systemctl restart ssh.service
/usr/sbin/sshd -t
systemctl is-active ssh.service
echo BOOTSTRAP_OK
EOF
chmod 755 "$MNT/usr/local/sbin/louksna-bootstrap.sh"
mkdir -p "$MNT/etc/systemd/system/multi-user.target.wants" "$MNT/etc/systemd/network"
cat > "$MNT/etc/systemd/system/louksna-bootstrap.service" << 'EOF'
[Unit]
Description=Install OpenSSH for the LOUKSNA validation
After=systemd-networkd.service systemd-resolved.service
Wants=systemd-networkd.service
[Service]
Type=oneshot
ExecStart=/usr/local/sbin/louksna-bootstrap.sh
TimeoutStartSec=600
StandardOutput=journal+console
StandardError=journal+console
[Install]
WantedBy=multi-user.target
EOF
ln -sfn /etc/systemd/system/louksna-bootstrap.service "$MNT/etc/systemd/system/multi-user.target.wants/louksna-bootstrap.service"
cat > "$MNT/etc/systemd/network/10-louksna.network" << 'EOF'
[Match]
Name=en*
Name=eth*

[Network]
DHCP=yes
DNS=1.1.1.1
DNS=8.8.8.8
EOF
rm -f "$MNT/etc/ssh/sshd_not_to_be_run"
echo BOOTSTRAP_UNIT_INSTALLED
echo PREPARE_OK
if ! umount "$MNT"; then
  echo UMOUNT_FAIL
  exit 1
fi
qemu-nbd --disconnect /dev/nbd0
trap - EXIT
echo PREPARE_DETACHED
