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
P3="/dev/nvme0n1p3"
OLD_UUID="F2848A148489DC0B"
WINROOT="/media/diegoignacionorambuenamiranda/Windows"
KEEP="$WINROOT/PROYECTOS"
FINAL_MOUNT="$HOME/PROYECTOS"
STATE_ROOT="$HOME/.local/state/louksna/r4-master-part1-part9"
R2_STATE="$STATE_ROOT/PART_4_R2/STATE.json"
VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_verify_tree.py"
SOURCE_BYTES=200490852057
MANIFEST_SHA="99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e"

hold(){ echo "HOLD:$*" >&2; exit 20; }
need(){ command -v "$1" >/dev/null 2>&1 || hold "MISSING_COMMAND:$1"; }
need_exec(){ [ -x "$1" ] || hold "MISSING_COMMAND:$1"; }
blkid_uuid(){ sudo -n "$BLKID" -p -s UUID -o value "$1"; }
json_get(){ python3 - "$PLAN" "$1" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
cur=d
for p in sys.argv[2].split("."): cur=cur[p]
print(cur)
PY
}

validate_top_level(){
  local root="$1"
  [ -d "$root/PROYECTOS" ] || hold "PROYECTOS_MISSING"
  [ ! -L "$root/PROYECTOS" ] || hold "PROYECTOS_SYMLINK_REJECTED"
  mapfile -t top < <(find "$root" -mindepth 1 -maxdepth 1 -printf '%f\n' | sort)
  [ "${#top[@]}" -ge 1 ] || hold "EMPTY_SOURCE_ROOT"
  [ "${#top[@]}" -le 2 ] || hold "UNEXPECTED_TOP_LEVEL_COUNT:${#top[@]}:${top[*]}"
  local x
  for x in "${top[@]}"; do
    case "$x" in
      PROYECTOS) ;;
      "System Volume Information") ;;
      *) hold "UNEXPECTED_SURVIVOR:$x" ;;
    esac
  done
  if [ -e "$root/System Volume Information" ]; then
    local svi="$root/System Volume Information"
    [ -d "$svi" ] || hold "SVI_NOT_DIRECTORY"
    [ ! -L "$svi" ] || hold "SVI_SYMLINK_REJECTED"
    local rel
    while IFS= read -r rel; do
      case "$rel" in
        "."|"./Chkdsk"|"./MountPointManagerRemoteDatabase") ;;
        ./Chkdsk/Chkdsk*.log) ;;
        *) hold "SVI_UNEXPECTED_ENTRY:$rel" ;;
      esac
    done < <(cd "$svi" && find . -mindepth 0 -maxdepth 3 -printf '%p\n' | sort)
    local svi_bytes
    svi_bytes="$(du -sb --apparent-size "$svi" | awk '{print $1}')"
    [ "$svi_bytes" -le 67108864 ] || hold "SVI_TOO_LARGE:$svi_bytes"
  fi
}

[ -n "$MODE" ] || hold "MODE_REQUIRED"
[ -n "$OUT" ] || hold "OUT_REQUIRED"
mkdir -p "$OUT"

for c in python3 lsblk findmnt blockdev ntfsresize parted partprobe udevadm mkfs.ext4 resize2fs e2fsck rsync mount umount sfdisk sha256sum; do need "$c"; done
need_exec "$BLKID"
sudo -n true >/dev/null 2>&1 || hold "NONINTERACTIVE_SUDO_REQUIRED"

if [ "$MODE" = "plan" ]; then
  validate_top_level "$WINROOT"
  [ "$(findmnt -T "$WINROOT" -n -o SOURCE)" = "$P3" ] || hold "P3_SOURCE_MISMATCH"
  [ "$(findmnt -T "$WINROOT" -n -o FSTYPE)" = "ntfs3" ] || hold "P3_FSTYPE_MISMATCH"
  [ "$(blkid_uuid "$P3")" = "$OLD_UUID" ] || hold "P3_UUID_MISMATCH"
  nested="$(findmnt -R -n -o TARGET "$WINROOT" | tail -n +2 || true)"
  [ -z "$nested" ] || hold "NESTED_MOUNT:$nested"

  SS="$(sudo -n blockdev --getss "$DISK")"
  [ "$SS" -gt 0 ] || hold "BAD_SECTOR_SIZE"
  PARTED_RAW="$(sudo -n parted -m "$DISK" unit s print)"

  # ntfsresize refuses --info on a read-write mounted NTFS volume.
  # Open a bounded read-only planning window: unmount only for the probe,
  # remount immediately from the already-governed fstab, then revalidate.
  PLAN_REMOUNT_REQUIRED=0
  plan_restore_mount(){
    rc=$?
    if [ "${PLAN_REMOUNT_REQUIRED:-0}" -eq 1 ]; then
      sudo -n mount "$WINROOT" >/dev/null 2>&1 || true
    fi
    return "$rc"
  }
  trap plan_restore_mount EXIT

  sudo -n umount "$WINROOT" || hold "P3_UNMOUNT_FOR_NTFS_INFO_FAILED"
  PLAN_REMOUNT_REQUIRED=1

  set +e
  NTFS_INFO="$(LC_ALL=C sudo -n ntfsresize --info --force "$P3" 2>&1)"
  NTFS_INFO_RC=$?
  set -e

  sudo -n mount "$WINROOT" || hold "P3_REMOUNT_AFTER_NTFS_INFO_FAILED"
  PLAN_REMOUNT_REQUIRED=0
  trap - EXIT

  [ "$NTFS_INFO_RC" -eq 0 ] || {
    printf '%s\n' "$NTFS_INFO" > "$OUT/NTFS_INFO_ERROR.txt"
    hold "NTFS_INFO_FAILED_RC_$NTFS_INFO_RC"
  }

  [ "$(findmnt -T "$WINROOT" -n -o SOURCE)" = "$P3" ] || hold "P3_SOURCE_AFTER_NTFS_INFO"
  [ "$(findmnt -T "$WINROOT" -n -o FSTYPE)" = "ntfs3" ] || hold "P3_FSTYPE_AFTER_NTFS_INFO"
  [ "$(blkid_uuid "$P3")" = "$OLD_UUID" ] || hold "P3_UUID_AFTER_NTFS_INFO"
  validate_top_level "$WINROOT"

  export PARTED_RAW NTFS_INFO SS
  python3 - "$OUT/STORAGE_PLAN.json" <<'PY'
import json,os,re,sys,time,hashlib
raw=os.environ["PARTED_RAW"]; info=os.environ["NTFS_INFO"]; ss=int(os.environ["SS"])
parts={}
for line in raw.splitlines():
    if not re.match(r"^\d+:",line): continue
    f=line.rstrip(";").split(":")
    n=int(f[0]); start=int(f[1].rstrip("s")); end=int(f[2].rstrip("s")); size=int(f[3].rstrip("s"))
    parts[n]={"start_sector":start,"end_sector":end,"size_sectors":size,"fs":f[4] if len(f)>4 else "","name":f[5] if len(f)>5 else ""}
for n in (1,2,3,4,5):
    if n not in parts: raise SystemExit(f"HOLD:MISSING_PARTITION_{n}")
p3,p4,p5=parts[3],parts[4],parts[5]
if not (p3["end_sector"] + 1 == p5["start_sector"] and p5["end_sector"] < p4["start_sector"] <= p4["end_sector"]):
    raise SystemExit("HOLD:PARTITION_ORDER_UNEXPECTED")
m=None
for line in info.splitlines():
    q=re.search(r"resize at\s+([0-9]+)\s+bytes",line,re.I)
    if q: m=int(q.group(1))
if m is None:
    nums=[int(x) for x in re.findall(r"([0-9]{9,})\s+bytes",info)]
    if nums: m=min(nums)
if m is None: raise SystemExit("HOLD:NTFS_MINIMUM_UNPARSEABLE")
source=200490852057
align=max(1,1048576//ss)
def up(v,a): return ((v+a-1)//a)*a
# Reserve enough for one complete verified temporary ext4 copy plus 6 GB decimal.
temp_required=source+6_000_000_000
total_bytes=(p5["start_sector"]-p3["start_sector"])*ss
part_target_max=total_bytes-temp_required-2*1048576
part_target=(part_target_max//(align*ss))*(align*ss)
fs_target=part_target-536870912
if fs_target < m+268435456:
    raise SystemExit(f"HOLD:INSUFFICIENT_SHRINK_MARGIN:min={m}:fs_target={fs_target}")
part_sectors=part_target//ss
new_end=p3["start_sector"]+part_sectors-1
temp_start=up(new_end+1+align,align)
temp_end=(p5["start_sector"]-align)
temp_bytes=(temp_end-temp_start+1)*ss
if temp_bytes < temp_required:
    raise SystemExit(f"HOLD:TEMP_AREA_TOO_SMALL:{temp_bytes}:{temp_required}")
final_end=p5["start_sector"]-align
if final_end <= p3["start_sector"]: raise SystemExit("HOLD:FINAL_END_INVALID")
plan={
 "schema":"LOUKSNA_R4_PART4_R2_STORAGE_PLAN/1.0",
 "status":"PASS","disk":"/dev/nvme0n1","sector_size":ss,
 "source_partition":"/dev/nvme0n1p3","source_uuid":"F2848A148489DC0B",
 "source_regular_file_bytes":source,
 "certified_manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
 "ntfs_minimum_bytes":m,"ntfs_fs_target_bytes":fs_target,
 "p3_original":p3,"p4_original":p4,"p5":p5,
 "p3_new_end_sector":new_end,"p3_partition_target_bytes":part_target,
 "temp_start_sector":temp_start,"temp_end_sector":temp_end,"temp_bytes":temp_bytes,
 "final_p3_end_sector":final_end,
 "final_mount":os.path.expanduser("~/PROYECTOS"),
 "steps":[
   "UNMOUNT_P3","SHRINK_NTFS_FILESYSTEM","SHRINK_P3_BOUNDARY","CREATE_TEMP_EXT4",
   "VERIFY_SOURCE","COPY_TO_TEMP","VERIFY_TEMP","REFORMAT_P3_EXT4",
   "COPY_TEMP_TO_P3","VERIFY_P3","DELETE_TEMP_ONLY","EXPAND_P3","RESIZE_EXT4",
   "PERSIST_FINAL_MOUNT","VERIFY_FINAL"
 ],
 "rollback_contract":{
   "partition_table_dump_before_mutation":True,
   "before_p3_reformat":"ORIGINAL_NTFS_P3_REMAINS_SOURCE_OF_TRUTH",
   "after_p3_reformat_until_final_verify":"VERIFIED_TEMP_EXT4_REMAINS_RECOVERY_COPY",
   "after_final_verify":"VERIFIED_EXT4_P3_IS_PROTECTED_SOURCE"
 },
 "generated_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),
 "ntfs_info_raw":info,
 "parted_before_raw":raw
}
data=json.dumps(plan,indent=2,sort_keys=True)+"\n"
open(sys.argv[1],"w",encoding="utf-8").write(data)
open(sys.argv[1]+".sha256","w").write(hashlib.sha256(data.encode()).hexdigest()+"  STORAGE_PLAN.json\n")
print(data)
PY
  exit 0
fi

[ "$MODE" = "execute" ] || hold "UNKNOWN_MODE:$MODE"
[ -f "$PLAN" ] || hold "PLAN_MISSING"
[ -f "$MANIFEST" ] || hold "MANIFEST_MISSING"
[ "$(sha256sum "$MANIFEST" | awk '{print $1}')" = "$MANIFEST_SHA" ] || hold "MANIFEST_DIGEST_MISMATCH"
[ "$(json_get status)" = "PASS" ] || hold "PLAN_NOT_PASS"
[ "$(json_get source_uuid)" = "$OLD_UUID" ] || hold "PLAN_UUID_DRIFT"

SS="$(json_get sector_size)"
FS_TARGET="$(json_get ntfs_fs_target_bytes)"
NEW_END="$(json_get p3_new_end_sector)"
TEMP_START="$(json_get temp_start_sector)"
TEMP_END="$(json_get temp_end_sector)"
FINAL_END="$(json_get final_p3_end_sector)"
P5_START="$(json_get p5.start_sector)"
WORK="$STATE_ROOT/PART_4_R2/migration"
SRCM="$WORK/source-ntfs"
TMPM="$WORK/temp-ext4"
FINALM="$WORK/final-ext4"
mkdir -p "$WORK" "$SRCM" "$TMPM" "$FINALM"
chmod 700 "$WORK" "$SRCM" "$TMPM" "$FINALM"

REPORT="$OUT/MIGRATION_RESULT.json"
python3 - "$REPORT" <<'PY'
import json,sys,time
json.dump({"schema":"LOUKSNA_R4_PART4_R2_STORAGE_MIGRATION/1.0","status":"RUNNING","events":[],"started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())},open(sys.argv[1],"w"),indent=2)
PY
event(){
  python3 - "$REPORT" "$1" "${2:-PASS}" <<'PY'
import json,sys,time,os
p=sys.argv[1]; d=json.load(open(p)); d["events"].append({"event":sys.argv[2],"status":sys.argv[3],"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
tmp=p+".tmp"; json.dump(d,open(tmp,"w"),indent=2,sort_keys=True); os.replace(tmp,p)
PY
}
trap 'rc=$?; python3 - "$REPORT" "$rc" <<'"'"'PY'"'"'
import json,sys,time,os
p=sys.argv[1]; rc=int(sys.argv[2]); d=json.load(open(p)); d["status"]="HOLD"; d["exit_code"]=rc; d["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()); tmp=p+".tmp"; json.dump(d,open(tmp,"w"),indent=2,sort_keys=True); os.replace(tmp,p)
PY
exit $rc' ERR

# Fresh identity checks immediately before first storage mutation.
validate_top_level "$WINROOT"
[ "$(findmnt -T "$WINROOT" -n -o SOURCE)" = "$P3" ] || hold "P3_SOURCE_PREEXEC"
[ "$(blkid_uuid "$P3")" = "$OLD_UUID" ] || hold "P3_UUID_PREEXEC"

sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_BEFORE.sfdisk"
sha256sum "$OUT/PARTITION_TABLE_BEFORE.sfdisk" > "$OUT/PARTITION_TABLE_BEFORE.sha256"
event PARTITION_TABLE_CHECKPOINT

sudo -n umount "$WINROOT"
! findmnt -T "$P3" >/dev/null 2>&1 || true
event P3_UNMOUNTED

sudo -n ntfsresize --force --no-progress-bar --size "$FS_TARGET" "$P3"
event NTFS_FILESYSTEM_SHRUNK

sudo -n parted -s "$DISK" unit s resizepart 3 "${NEW_END}s"
sudo -n partprobe "$DISK" || true
sudo -n udevadm settle
event P3_PARTITION_SHRUNK

sudo -n parted -s "$DISK" unit s mkpart LOUKSNA_TMP ext4 "${TEMP_START}s" "${TEMP_END}s"
sudo -n partprobe "$DISK" || true
sudo -n udevadm settle
TMPDEV="$(python3 - "$TEMP_START" <<'PY'
import glob,os,sys
want=int(sys.argv[1]); hits=[]
for p in glob.glob("/sys/class/block/nvme0n1p*/start"):
    try:
        if int(open(p).read().strip())==want:
            hits.append("/dev/"+p.split("/")[-2])
    except: pass
if len(hits)!=1: raise SystemExit("TEMP_PARTITION_DETECTION:"+repr(hits))
print(hits[0])
PY
)"
[ -b "$TMPDEV" ] || hold "TEMP_DEVICE_NOT_BLOCK:$TMPDEV"
TMPNUM="${TMPDEV##*p}"
sudo -n mkfs.ext4 -F -L LOUKSNA_TMP "$TMPDEV"
event TEMP_EXT4_CREATED

sudo -n mount -t ntfs3 -o ro "$P3" "$SRCM"
sudo -n mount -t ext4 "$TMPDEV" "$TMPM"
sudo -n chown "$(id -u):$(id -g)" "$TMPM"
event SOURCE_AND_TEMP_MOUNTED

python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE.json"
event SOURCE_REVERIFIED

mkdir -p "$TMPM/PROYECTOS"
rsync -aH --delete --numeric-ids "$SRCM/PROYECTOS/" "$TMPM/PROYECTOS/"
sync
python3 "$VERIFY" --root "$TMPM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_TEMP.json"
event TEMP_COPY_VERIFIED

sudo -n umount "$SRCM"
sudo -n mkfs.ext4 -F -L LOUKSNA_PROJECTS "$P3"
sudo -n mount -t ext4 "$P3" "$FINALM"
sudo -n chown "$(id -u):$(id -g)" "$FINALM"
event P3_REFORMATTED_EXT4

rsync -aH --delete --numeric-ids "$TMPM/PROYECTOS/" "$FINALM/"
sync
python3 "$VERIFY" --root "$FINALM" --manifest "$MANIFEST" --out "$OUT/VERIFY_P3_PREEXPAND.json"
event P3_COPY_VERIFIED

sudo -n umount "$FINALM"
sudo -n umount "$TMPM"

# Retire only the temporary migration partition here.
# p2/p4 remain untouched until the separately certified final-merge phase.
if [ -e "/sys/class/block/nvme0n1p$TMPNUM" ]; then sudo -n parted -s "$DISK" rm "$TMPNUM"; fi
sudo -n partprobe "$DISK" || true
sudo -n udevadm settle
event TEMP_PARTITION_RETIRED

sudo -n parted -s "$DISK" unit s resizepart 3 "${FINAL_END}s"
sudo -n partprobe "$DISK" || true
sudo -n udevadm settle
sudo -n e2fsck -f -p "$P3" || rc=$?
if [ "${rc:-0}" -gt 1 ]; then hold "E2FSCK_FAILED:${rc:-0}"; fi
sudo -n resize2fs "$P3"
event P3_EXT4_EXPANDED

mkdir -p "$FINAL_MOUNT"
sudo -n mount -t ext4 "$P3" "$FINAL_MOUNT"
NEW_UUID="$(blkid_uuid "$P3")"
[ -n "$NEW_UUID" ] || hold "NEW_UUID_MISSING"
python3 "$VERIFY" --root "$FINAL_MOUNT" --manifest "$MANIFEST" --out "$OUT/VERIFY_FINAL.json"
event FINAL_TREE_VERIFIED

# Persist only the new Linux data mount. Preserve /etc/fstab before edit.
sudo -n cp -a /etc/fstab "$OUT/fstab.before"
export NEW_UUID FINAL_MOUNT OLD_UUID
sudo -n -E python3 - <<'PY'
import os,pathlib
p=pathlib.Path("/etc/fstab")
old=p.read_text(encoding="utf-8").splitlines()
new=[]
for line in old:
    s=line.strip()
    if not s or s.startswith("#"):
        new.append(line); continue
    f=s.split()
    if len(f)>=2 and (f[0] in {os.environ["OLD_UUID"],"UUID="+os.environ["OLD_UUID"]} or f[1]==os.environ["FINAL_MOUNT"]):
        continue
    new.append(line)
new.append(f'UUID={os.environ["NEW_UUID"]} {os.environ["FINAL_MOUNT"]} ext4 defaults,nofail,x-systemd.device-timeout=10 0 2')
tmp=p.with_name("fstab.louksna-part4-r2.tmp")
tmp.write_text("\n".join(new)+"\n",encoding="utf-8")
os.chmod(tmp,0o644); os.replace(tmp,p)
PY
event FSTAB_PERSISTED

sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_AFTER.sfdisk"
lsblk -b -J -o NAME,PATH,TYPE,SIZE,FSTYPE,FSAVAIL,FSUSE%,MOUNTPOINTS,UUID,PARTUUID,START > "$OUT/LSBLK_FINAL.json"
df -B1 "$FINAL_MOUNT" > "$OUT/DF_FINAL.txt"
sha256sum "$OUT/VERIFY_FINAL.json" "$OUT/PARTITION_TABLE_AFTER.sfdisk" "$OUT/LSBLK_FINAL.json" > "$OUT/FINAL_EVIDENCE.sha256"

python3 - "$REPORT" "$R2_STATE" "$NEW_UUID" "$TMPDEV" <<'PY'
import json,sys,time,os
rp,sp,newuuid,tmpdev=sys.argv[1:]
d=json.load(open(rp)); d["status"]="PASS"; d["new_p3_ext4_uuid"]=newuuid; d["temporary_partition"]=tmpdev
d["final_mount"]=os.path.expanduser("~/PROYECTOS"); d["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
tmp=rp+".tmp"; json.dump(d,open(tmp,"w"),indent=2,sort_keys=True); os.replace(tmp,rp)
s=json.load(open(sp))
s.update({
 "purge_scope_g23_g24":True,
 "windows_purged_preserving_projects":True,
 "post_purge_integrity":True,
 "ntfs_shrunk":True,
 "ext4_created":True,
 "projects_migrated_hash_equivalent":True,
 "ntfs_retired":True,
 "final_linux_layout":True,
 "part4_r2_final_g24":False,
 "final_projects_mount":os.path.expanduser("~/PROYECTOS"),
 "final_projects_uuid":newuuid,
 "migration_material_pass":True,
 "updated_at_utc":d["finished_at_utc"]
})
t=sp+".tmp"; json.dump(s,open(t,"w"),indent=2,sort_keys=True); os.replace(t,sp)
PY
trap - ERR
event MATERIAL_MIGRATION_PASS
exit 0