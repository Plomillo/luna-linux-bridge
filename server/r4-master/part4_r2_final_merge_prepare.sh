#!/bin/bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"
BLKID="/usr/sbin/blkid"

MODE="${1:-}"
PLAN="${2:-}"
OUT="${3:-}"
MANIFEST="${4:-}"

DISK="/dev/nvme0n1"
EFI="/dev/nvme0n1p1"
NEWROOT_DEV="/dev/nvme0n1p3"
OLDROOT_DEV="/dev/nvme0n1p5"
OWNER="diegoignacionorambuenamiranda"
HOME_DIR="/home/$OWNER"
PROJECTS_MOUNT="$HOME_DIR/PROYECTOS"
STATE_ROOT="$HOME_DIR/.local/state/louksna/r4-master-part1-part9"
WORK="$STATE_ROOT/PART_4_R2/final-merge"
NEWROOT_MNT="$WORK/newroot"
VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_verify_tree_v2.py"
MANIFEST_SHA="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
PROJECT_BYTES=200490852057

hold(){ echo "HOLD:$*" >&2; exit 20; }
need(){ command -v "$1" >/dev/null 2>&1 || hold "MISSING_COMMAND:$1"; }
need_exec(){ [ -x "$1" ] || hold "MISSING_COMMAND:$1"; }
blkid_uuid(){ sudo -n "$BLKID" -p -s UUID -o value "$1"; }
verify_tree_privileged(){
  local root="$1" manifest="$2" out="$3"
  shift 3
  sudo -n python3 "$VERIFY" --root "$root" --manifest "$manifest" --out "$out" "$@"
  sudo -n chown "$OWNER:$OWNER" "$out"
  chmod 600 "$out"
}

for c in python3 lsblk findmnt blockdev df du rsync mount umount sfdisk sha256sum chroot grub-install update-grub update-initramfs efibootmgr; do need "$c"; done
need_exec "$BLKID"
sudo -n true >/dev/null 2>&1 || hold "NONINTERACTIVE_SUDO_REQUIRED"
[ -n "$MODE" ] || hold "MODE_REQUIRED"
[ -n "$OUT" ] || hold "OUT_REQUIRED"
mkdir -p "$OUT"

root_source="$(readlink -f "$(findmnt -n -o SOURCE /)")"
[ "$root_source" = "$OLDROOT_DEV" ] || hold "CURRENT_ROOT_NOT_OLDROOT:$root_source"
[ "$(findmnt -n -o FSTYPE /)" = "ext4" ] || hold "CURRENT_ROOT_NOT_EXT4"

P3_MOUNT_TARGET="$(findmnt -rn -S "$NEWROOT_DEV" -o TARGET | head -1 || true)"
if [ "$P3_MOUNT_TARGET" = "$PROJECTS_MOUNT" ]; then
  P3_MOUNT_CONTEXT="PROJECTS_MOUNT"
elif [ "$P3_MOUNT_TARGET" = "$NEWROOT_MNT" ]; then
  P3_MOUNT_CONTEXT="FINAL_MERGE_STAGED_NEWROOT"
else
  hold "P3_MOUNT_CONTEXT_UNEXPECTED:${P3_MOUNT_TARGET:-UNMOUNTED}"
fi
[ "$(findmnt -T "$P3_MOUNT_TARGET" -n -o FSTYPE)" = "ext4" ] || hold "P3_NOT_EXT4"

efi_source="$(readlink -f "$(findmnt -T /boot/efi -n -o SOURCE)")"
[ "$efi_source" = "$EFI" ] || hold "EFI_SOURCE_MISMATCH:$efi_source"
[ "$(findmnt -T /boot/efi -n -o FSTYPE)" = "vfat" ] || hold "EFI_FSTYPE_MISMATCH"

for stale in /dev/nvme0n1p2 /dev/nvme0n1p4; do
  [ ! -b "$stale" ] || hold "WINDOWS_RESIDUAL_PARTITION_PRESENT:$stale"
done
[ -b "$OLDROOT_DEV" ] || hold "OLDROOT_MISSING"
[ -b "$NEWROOT_DEV" ] || hold "NEWROOT_DEVICE_MISSING"

P3_UUID="$(blkid_uuid "$NEWROOT_DEV")"
P5_UUID="$(blkid_uuid "$OLDROOT_DEV")"
EFI_UUID="$(blkid_uuid "$EFI")"
[ -n "$P3_UUID" ] && [ -n "$P5_UUID" ] && [ -n "$EFI_UUID" ] || hold "UUID_MISSING"

P3_FREE="$(df -B1 --output=avail "$P3_MOUNT_TARGET" | tail -1 | tr -d ' ')"
ROOT_USED="$(df -B1 --output=used / | tail -1 | tr -d ' ')"
MARGIN=10000000000
[ "$P3_FREE" -gt $((ROOT_USED+MARGIN)) ] || hold "INSUFFICIENT_P3_FREE_FOR_ROOT_COPY:$P3_FREE:$ROOT_USED"

PARTED_RAW="$(sudo -n parted -m "$DISK" unit s print)" || hold "PARTED_READ_FAILED"
LSBLK_RAW="$(lsblk -b -J -o NAME,PATH,TYPE,SIZE,FSTYPE,FSAVAIL,FSUSE%,MOUNTPOINTS,UUID,PARTUUID,START)"

if [ "$MODE" = "plan" ]; then
  export PARTED_RAW LSBLK_RAW P3_UUID P5_UUID EFI_UUID P3_FREE ROOT_USED P3_MOUNT_CONTEXT P3_MOUNT_TARGET
  python3 - "$OUT/FINAL_MERGE_PLAN.json" <<'PY'
import hashlib,json,os,re,sys,time
raw=os.environ["PARTED_RAW"]
parts={}
for line in raw.splitlines():
    if not re.match(r"^\d+:",line): continue
    f=line.rstrip(";").split(":")
    n=int(f[0]); parts[n]={
      "start_sector":int(f[1].rstrip("s")),"end_sector":int(f[2].rstrip("s")),
      "size_sectors":int(f[3].rstrip("s")),"fs":f[4] if len(f)>4 else "",
      "name":f[5] if len(f)>5 else ""
    }
if set(parts)!={1,3,5}: raise SystemExit("HOLD:EXPECTED_ONLY_P1_P3_P5:"+repr(sorted(parts)))
if not (parts[1]["end_sector"] < parts[3]["start_sector"] < parts[3]["end_sector"] < parts[5]["start_sector"] < parts[5]["end_sector"]):
    raise SystemExit("HOLD:PARTITION_ORDER")
plan={
 "schema":"LOUKSNA_R4_PART4_R2_FINAL_MERGE_PLAN/1.0","status":"PASS",
 "disk":"/dev/nvme0n1","efi":"/dev/nvme0n1p1","new_root":"/dev/nvme0n1p3","old_root":"/dev/nvme0n1p5",
 "efi_uuid":os.environ["EFI_UUID"],"new_root_uuid":os.environ["P3_UUID"],"old_root_uuid":os.environ["P5_UUID"],
 "new_root_free_bytes":int(os.environ["P3_FREE"]),"old_root_used_bytes":int(os.environ["ROOT_USED"]),
 "required_margin_bytes":10_000_000_000,
 "certified_projects_manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
 "partitions":parts,
 "final_layout":"EFI_P1_PLUS_SINGLE_MAIN_EXT4_ROOT_P3",
 "old_root_retirement_condition":"VERIFIED_BOOT_FROM_P3_PLUS_POSTBOOT_G23_G24",
 "projects_final_path":"/home/diegoignacionorambuenamiranda/PROYECTOS",
 "p3_mount_context":os.environ["P3_MOUNT_CONTEXT"],
 "p3_mount_target":os.environ["P3_MOUNT_TARGET"],
 "resume_from_staged_newroot_allowed":True,
 "normal_alignment_gap_allowed":True,
 "rollback_contract":{
   "before_reboot":"P5_REMAINS_UNMODIFIED_BOOTABLE_ROOT",
   "after_reboot_before_p5_delete":"P5_REMAINS_RECOVERY_ROOT",
   "after_p5_delete":"P3_IS_VERIFIED_BOOTED_ROOT_AND_PROYECTOS_HASH_PASS",
   "partition_table_checkpoint_required":True,
   "fstab_checkpoint_required":True,
   "grub_checkpoint_required":True
 },
 "lsblk":json.loads(os.environ["LSBLK_RAW"]),
 "parted":raw,
 "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
}
data=json.dumps(plan,indent=2,sort_keys=True)+"\n"
open(sys.argv[1],"w",encoding="utf-8").write(data)
open(sys.argv[1]+".sha256","w").write(hashlib.sha256(data.encode()).hexdigest()+"  FINAL_MERGE_PLAN.json\n")
print(data)
PY
  exit 0
fi

[ "$MODE" = "prepare" ] || hold "UNKNOWN_MODE:$MODE"
[ -f "$PLAN" ] || hold "PLAN_MISSING"
[ -f "$MANIFEST" ] || hold "MANIFEST_MISSING"
[ "$(sha256sum "$MANIFEST" | awk '{print $1}')" = "$MANIFEST_SHA" ] || hold "MANIFEST_DIGEST_MISMATCH"
python3 - "$PLAN" "$P3_UUID" "$P5_UUID" "$EFI_UUID" <<'PY'
import json,sys
d=json.load(open(sys.argv[1]))
assert d["status"]=="PASS"
assert d["new_root"]=="/dev/nvme0n1p3"
assert d["old_root"]=="/dev/nvme0n1p5"
assert d["efi"]=="/dev/nvme0n1p1"
assert d["new_root_uuid"]==sys.argv[2]
assert d["old_root_uuid"]==sys.argv[3]
assert d["efi_uuid"]==sys.argv[4]
assert d["certified_projects_manifest_sha256"]=="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"
PY

mkdir -p "$WORK" "$NEWROOT_MNT"
chmod 700 "$WORK"
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_PREBOOT.sfdisk"
cp -a /etc/fstab "$OUT/fstab.oldroot.before"
sudo -n cat /boot/grub/grub.cfg > "$OUT/grub.cfg.oldroot.before"
(sudo -n efibootmgr -v || true) > "$OUT/efibootmgr.before.txt"
sha256sum "$OUT/PARTITION_TABLE_PREBOOT.sfdisk" "$OUT/fstab.oldroot.before" "$OUT/grub.cfg.oldroot.before" > "$OUT/CHECKPOINTS.sha256"

python3 "$VERIFY" --root "$PROJECTS_MOUNT" --manifest "$MANIFEST" --out "$OUT/VERIFY_PROJECTS_BEFORE_RELOCATION.json" --allow-ext4-root-lost-found

if [ "$P3_MOUNT_CONTEXT" = "PROJECTS_MOUNT" ]; then
  sudo -n umount "$PROJECTS_MOUNT"
  sudo -n mount -t ext4 "$NEWROOT_DEV" "$NEWROOT_MNT"
elif [ "$P3_MOUNT_CONTEXT" = "FINAL_MERGE_STAGED_NEWROOT" ]; then
  [ "$(readlink -f "$(findmnt -n -o SOURCE "$NEWROOT_MNT")")" = "$NEWROOT_DEV" ] || hold "STAGED_NEWROOT_SOURCE_MISMATCH"
else
  hold "UNKNOWN_P3_MOUNT_CONTEXT:$P3_MOUNT_CONTEXT"
fi

# Relocate only manifest-owned top-level project entries into the future Debian home path.
sudo -n python3 - "$NEWROOT_MNT" "$MANIFEST" "$OWNER" <<'PY'
import gzip,json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]); man=pathlib.Path(sys.argv[2]); owner=sys.argv[3]
tops=set()
with gzip.open(man,"rt",encoding="utf-8") as f:
    for line in f:
        p=json.loads(line)["path"]
        tops.add(pathlib.PurePosixPath(p).parts[0])
dest=root/"home"/owner/"PROYECTOS"
dest.mkdir(parents=True,exist_ok=True)
source_present=[n for n in sorted(tops) if os.path.lexists(root/n)]
dest_present=[n for n in sorted(tops) if os.path.lexists(dest/n)]
if source_present and dest_present:
    raise SystemExit("HOLD:MIXED_RELOCATION_STATE")
if source_present:
    if len(source_present)!=len(tops): raise SystemExit("HOLD:SOURCE_TOPLEVEL_INCOMPLETE")
    for n in sorted(tops):
        os.rename(root/n,dest/n)
elif len(dest_present)!=len(tops):
    raise SystemExit("HOLD:RELOCATED_TOPLEVEL_INCOMPLETE")
PY

sudo -n chown "$OWNER:$OWNER" "$NEWROOT_MNT/home/$OWNER/PROYECTOS"
verify_tree_privileged "$NEWROOT_MNT/home/$OWNER/PROYECTOS" "$MANIFEST" "$OUT/VERIFY_PROJECTS_AFTER_RELOCATION.json"

# Two-pass live root copy. -x preserves filesystem boundary and therefore never
# re-enters the P3 new-root mount or EFI/pseudo filesystems.
sudo -n rsync -aHAXx --numeric-ids   --exclude="/home/$OWNER/PROYECTOS/***"   --exclude="/lost+found"   / "$NEWROOT_MNT/"
sync
sleep 2
sudo -n rsync -aHAXx --numeric-ids   --exclude="/home/$OWNER/PROYECTOS/***"   --exclude="/lost+found"   / "$NEWROOT_MNT/"
sync

# Ensure the certified project tree survived root materialization.
verify_tree_privileged "$NEWROOT_MNT/home/$OWNER/PROYECTOS" "$MANIFEST" "$OUT/VERIFY_PROJECTS_AFTER_ROOT_COPY.json"

# Build the new root's fstab deterministically.
sudo -n env P3_UUID="$P3_UUID" EFI_UUID="$EFI_UUID" OWNER="$OWNER" python3 - "$NEWROOT_MNT/etc/fstab" <<'PY'
import os,pathlib,sys
p=pathlib.Path(sys.argv[1])
old=p.read_text(encoding="utf-8").splitlines() if p.exists() else []
kept=[]
for line in old:
    s=line.strip()
    if not s or s.startswith("#"):
        kept.append(line); continue
    f=s.split()
    if len(f)<2: continue
    if f[1] in {"/",f"/home/{os.environ['OWNER']}/PROYECTOS","/boot/efi"}:
        continue
    kept.append(line)
new=[
  f"UUID={os.environ['P3_UUID']} / ext4 defaults,errors=remount-ro 0 1",
  f"UUID={os.environ['EFI_UUID']} /boot/efi vfat umask=0077 0 1",
  *kept
]
p.write_text("\n".join(new)+"\n",encoding="utf-8")
os.chmod(p,0o644)
PY

# Prepare chroot and boot chain on P3; P5 remains untouched and bootable.
for d in dev proc sys run; do sudo -n mkdir -p "$NEWROOT_MNT/$d"; done
sudo -n mount --rbind /dev "$NEWROOT_MNT/dev"; sudo -n mount --make-rslave "$NEWROOT_MNT/dev"
sudo -n mount -t proc proc "$NEWROOT_MNT/proc"
sudo -n mount --rbind /sys "$NEWROOT_MNT/sys"; sudo -n mount --make-rslave "$NEWROOT_MNT/sys"
sudo -n mount --rbind /run "$NEWROOT_MNT/run"; sudo -n mount --make-rslave "$NEWROOT_MNT/run"
sudo -n mkdir -p "$NEWROOT_MNT/boot/efi"
sudo -n mount "$EFI" "$NEWROOT_MNT/boot/efi"

sudo -n chroot "$NEWROOT_MNT" /usr/sbin/update-initramfs -u -k all
# Install the candidate bootloader under a distinct EFI/NVRAM identity.
# The existing Debian EFI entry is intentionally left untouched as rollback.
sudo -n chroot "$NEWROOT_MNT" /usr/sbin/grub-install --target=x86_64-efi --efi-directory=/boot/efi --bootloader-id=LOUKSNA-P3 --recheck
sudo -n chroot "$NEWROOT_MNT" /usr/sbin/update-grub

sudo -n grep -F "$P3_UUID" "$NEWROOT_MNT/etc/fstab" >/dev/null || hold "NEW_FSTAB_MISSING_P3_UUID"
sudo -n grep -F "$P3_UUID" "$NEWROOT_MNT/boot/grub/grub.cfg" >/dev/null || hold "NEW_GRUB_MISSING_P3_UUID"
sudo -n test -x "$NEWROOT_MNT/usr/bin/python3" || hold "NEWROOT_PYTHON_MISSING"
sudo -n test -e "$NEWROOT_MNT/etc/os-release" || hold "NEWROOT_OS_RELEASE_MISSING"
sudo -n test -d "$NEWROOT_MNT/home/$OWNER/actions-runner" || hold "NEWROOT_RUNNER_MISSING"
sudo -n test -f "$NEWROOT_MNT/home/$OWNER/.local/state/louksna/r4-master-part1-part9/PART_4_R2/STATE.json" || hold "NEWROOT_STATE_MISSING"

# Install one-shot postboot dispatcher into the future root.
sudo -n mkdir -p "$NEWROOT_MNT/usr/local/lib/louksna"
sudo -n tee "$NEWROOT_MNT/usr/local/lib/louksna/part4-r2-postboot-dispatch.sh" >/dev/null <<'EOS'
#!/bin/bash
set -Eeuo pipefail
OWNER="diegoignacionorambuenamiranda"
HOME_DIR="/home/$OWNER"
MARK="$HOME_DIR/.local/state/louksna/r4-master-part1-part9/PART_4_R2/POSTBOOT_DISPATCHED"
export HOME="$HOME_DIR"
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME_DIR/.local/bin"
[ ! -e "$MARK" ] || exit 0
for i in $(seq 1 90); do
  if /usr/bin/gh auth status >/dev/null 2>&1; then
    TS="$(date -u +%Y%m%dT%H%M%SZ)"
    TRIGGER="mission-control/r4-part4-r2-final-merge-postboot/BOOT-$TS.json"
    BODY="$(printf '{"schema":"LOUKSNA_R4_PART4_R2_POSTBOOT_TRIGGER/1.0","host":"LOUKSNA","root":"/dev/nvme0n1p3","utc":"%s"}' "$TS" | base64 -w0)"
    if /usr/bin/gh api --method PUT "repos/Plomillo/luna-linux-bridge/contents/$TRIGGER"       -f message="handoff(PART4-R2): resume final merge after P3 boot"       -f content="$BODY"       -f branch="staging/luna-r4-master-part1-part9-20260929"; then
      mkdir -p "$(dirname "$MARK")"
      date -u +%FT%TZ > "$MARK"
      exit 0
    fi
  fi
  sleep 10
done
exit 1
EOS
sudo -n chmod 0755 "$NEWROOT_MNT/usr/local/lib/louksna/part4-r2-postboot-dispatch.sh"
sudo -n tee "$NEWROOT_MNT/etc/systemd/system/louksna-part4-r2-postboot-dispatch.service" >/dev/null <<EOF
[Unit]
Description=LOUKSNA PART4-R2 postboot final-merge dispatcher
After=network-online.target actions.runner.Plomillo-luna-linux-bridge.luna-linux.service
Wants=network-online.target
ConditionPathExists=!$HOME_DIR/.local/state/louksna/r4-master-part1-part9/PART_4_R2/POSTBOOT_DISPATCHED

[Service]
Type=oneshot
User=$OWNER
Environment=HOME=$HOME_DIR
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$HOME_DIR/.local/bin
ExecStart=/usr/local/lib/louksna/part4-r2-postboot-dispatch.sh
TimeoutStartSec=1000

[Install]
WantedBy=multi-user.target
EOF
sudo -n chroot "$NEWROOT_MNT" /usr/bin/systemctl enable louksna-part4-r2-postboot-dispatch.service

sudo -n cat "$NEWROOT_MNT/etc/fstab" > "$OUT/fstab.newroot"
sudo -n cat "$NEWROOT_MNT/boot/grub/grub.cfg" > "$OUT/grub.cfg.newroot"
(sudo -n efibootmgr -v || true) > "$OUT/efibootmgr.after-grub-install.txt"
python3 - "$OUT/efibootmgr.after-grub-install.txt" "$OUT/CANDIDATE_BOOT_ENTRY.json" <<'PY'
import json,re,sys
txt=open(sys.argv[1],encoding="utf-8",errors="replace").read()
hits=[]
for line in txt.splitlines():
    m=re.match(r"Boot([0-9A-Fa-f]{4})\*?\s+LOUKSNA-P3\b",line)
    if m: hits.append(m.group(1).upper())
if len(hits)!=1: raise SystemExit("HOLD:CANDIDATE_BOOT_ENTRY_NOT_UNIQUE:"+repr(hits))
json.dump({"schema":"LOUKSNA_R4_PART4_R2_CANDIDATE_BOOT_ENTRY/1.0","label":"LOUKSNA-P3","bootnum":hits[0]},open(sys.argv[2],"w"),indent=2,sort_keys=True)
PY
sha256sum "$OUT/fstab.newroot" "$OUT/grub.cfg.newroot" "$OUT/VERIFY_PROJECTS_AFTER_ROOT_COPY.json" "$OUT/CANDIDATE_BOOT_ENTRY.json" > "$OUT/PREBOOT_EVIDENCE.sha256"

export P3_UUID P5_UUID EFI_UUID
python3 - "$OUT/PREBOOT_STATE.json" <<'PY'
import hashlib,json,os,pathlib,sys,time
out=pathlib.Path(sys.argv[1])
files=["VERIFY_PROJECTS_BEFORE_RELOCATION.json","VERIFY_PROJECTS_AFTER_RELOCATION.json","VERIFY_PROJECTS_AFTER_ROOT_COPY.json","fstab.newroot","grub.cfg.newroot","PARTITION_TABLE_PREBOOT.sfdisk","CANDIDATE_BOOT_ENTRY.json"]
base=out.parent
r={
 "schema":"LOUKSNA_R4_PART4_R2_FINAL_MERGE_PREBOOT/1.0","status":"PASS",
 "current_root":"/dev/nvme0n1p5","candidate_root":"/dev/nvme0n1p3","efi":"/dev/nvme0n1p1",
 "candidate_root_uuid":os.environ["P3_UUID"],"old_root_uuid":os.environ["P5_UUID"],"efi_uuid":os.environ["EFI_UUID"],
 "projects_final_path":"/home/diegoignacionorambuenamiranda/PROYECTOS",
 "projects_manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
 "old_root_preserved":True,"existing_efi_entry_preserved":True,"candidate_boot_entry_label":"LOUKSNA-P3","postboot_dispatch_installed":True,
 "evidence_sha256":{n:hashlib.sha256((base/n).read_bytes()).hexdigest() for n in files},
 "prepared_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
}
raw=json.dumps(r,indent=2,sort_keys=True)+"\n"; out.write_text(raw); print(raw)
PY

# Tear down chroot mounts and leave P3 unmounted until certified boot switch.
sudo -n umount "$NEWROOT_MNT/boot/efi"
sudo -n umount -R "$NEWROOT_MNT/run" || true
sudo -n umount -R "$NEWROOT_MNT/sys" || true
sudo -n umount "$NEWROOT_MNT/proc" || true
sudo -n umount -R "$NEWROOT_MNT/dev" || true
sudo -n umount "$NEWROOT_MNT"
exit 0
