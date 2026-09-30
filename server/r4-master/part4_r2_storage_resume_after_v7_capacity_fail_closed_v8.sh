#!/bin/bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

PLAN="${1:-}"
OUT="${2:-}"
MANIFEST="${3:-}"
CLEANUP_REPORT="${4:-}"

DISK=/dev/nvme0n1
P3=/dev/nvme0n1p3
OLD_UUID=F2848A148489DC0B
TARGET_USER=diegoignacionorambuenamiranda
RUNUSER=/usr/sbin/runuser
RUNUSER_SHA=ea71a94cb0097f3e1d5ce2fa8fb775bf1bd1ddd74960fad3ee22d7d8d1ef4488
EXPECTED_MANIFEST_SHA=99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e
EXPECTED_RECORDS=498092
EXPECTED_BYTES=200490852057
STATE_ROOT="$HOME/.local/state/louksna/r4-master-part1-part9"
R2_STATE="$STATE_ROOT/PART_4_R2/STATE.json"
WORK="$STATE_ROOT/PART_4_R2/migration-v8"
SRCM="$WORK/source-ntfs"
TMPM="$WORK/temp-ext4"
FINALM="$WORK/final-ext4"
FINAL_MOUNT="$HOME/PROYECTOS"
VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_verify_tree.py"
POSIX_VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_posix_fingerprint_v8.py"
XATTR_VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_xattr_inventory.py"

hold(){ echo "HOLD:$*" >&2; exit 20; }
need(){ command -v "$1" >/dev/null 2>&1 || hold "MISSING_COMMAND:$1"; }
json_get(){ python3 - "$PLAN" "$1" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
v=d
for p in sys.argv[2].split("."): v=v[p]
print(v)
PY
}
blkid_uuid(){ sudo -n /usr/sbin/blkid -p -s UUID -o value "$1"; }

[ -f "$PLAN" ] || hold PLAN_MISSING
[ -f "$MANIFEST" ] || hold MANIFEST_MISSING
[ -f "$CLEANUP_REPORT" ] || hold CLEANUP_REPORT_MISSING
[ "$(sha256sum "$CLEANUP_REPORT" | awk '{print $1}')" = "$(json_get cleanup_report_sha256)" ] || hold CLEANUP_REPORT_DRIFT
[ "$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["status"])' "$CLEANUP_REPORT")" = PASS ] || hold CLEANUP_NOT_PASS
mkdir -p "$OUT" "$WORK" "$SRCM" "$TMPM" "$FINALM"
chmod 700 "$OUT" "$WORK" "$SRCM" "$TMPM" "$FINALM"

for c in python3 sha256sum sfdisk partx partprobe udevadm lsblk findmnt ntfsresize mount umount mkfs.ext4 rsync sync e2fsck resize2fs blkid stat; do need "$c"; done
[ -x "$RUNUSER" ] || hold RUNUSER_MISSING
[ "$(sha256sum "$RUNUSER"|awk '{print $1}')" = "$RUNUSER_SHA" ] || hold RUNUSER_HASH_DRIFT
sudo -n true >/dev/null 2>&1 || hold NONINTERACTIVE_SUDO_REQUIRED
sudo -n "$RUNUSER" -u "$TARGET_USER" -- bash --noprofile --norc -c 'sudo -k >/dev/null 2>&1 || true; test "$(sudo -n id -u)" = 0; test "$(sudo -n id -un)" = root' || hold PRIVILEGE_ROUNDTRIP_FAILED
[ "$(sha256sum "$MANIFEST"|awk '{print $1}')" = "$EXPECTED_MANIFEST_SHA" ] || hold MANIFEST_DIGEST_MISMATCH
[ "$(json_get status)" = PASS ] || hold PLAN_NOT_PASS
[ "$(json_get stage)" = P3_SHRUNK_TEMP_EXT4_CLEANED_V8_PRECOPY ] || hold PLAN_STAGE_MISMATCH
[ "$(json_get source_failure_run)" = 36682665542 ] || hold SOURCE_FAILURE_BINDING_MISMATCH

P3_START="$(json_get geometry.p3_start)"
P3_ORIGINAL_SIZE="$(json_get geometry.p3_original_size)"
P3_SHRUNK_SIZE="$(json_get geometry.p3_shrunk_size)"
P3_NEW_END="$(json_get geometry.p3_new_end)"
TEMP_START="$(json_get geometry.temp_start)"
TEMP_END="$(json_get geometry.temp_end)"
FINAL_P3_SIZE="$(json_get geometry.p3_final_size)"
FINAL_P3_END="$(json_get geometry.p3_final_end)"
FS_TARGET="$(json_get ntfs.fs_target_bytes)"

REPORT="$OUT/MIGRATION_RESUME_RESULT.json"
python3 - "$REPORT" <<'PY'
import json,sys,time
json.dump({"schema":"LOUKSNA_R4_PART4_R2_STORAGE_RESUME_V8/1.0","status":"RUNNING","events":[],"started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())},open(sys.argv[1],"w"),indent=2)
PY

event(){
  python3 - "$REPORT" "$1" "${2:-PASS}" <<'PY'
import json,sys,time,os
p,e,s=sys.argv[1:]; d=json.load(open(p)); d["events"].append({"event":e,"status":s,"utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())})
t=p+".tmp"; json.dump(d,open(t,"w"),indent=2,sort_keys=True); os.replace(t,p)
PY
}

trap 'rc=$?; python3 - "$REPORT" "$rc" <<'"'"'PY'"'"'
import json,sys,time,os
p=sys.argv[1]; rc=int(sys.argv[2]); d=json.load(open(p)); d["status"]="HOLD"; d["exit_code"]=rc; d["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()); t=p+".tmp"; json.dump(d,open(t,"w"),indent=2,sort_keys=True); os.replace(t,p)
PY
exit $rc' ERR

parse_geometry(){
  sudo -n sfdisk --dump "$DISK" | python3 -c '
import re,sys,json
d={}
for line in sys.stdin:
 m=re.match(r"^/dev/nvme0n1p(\d+)\s*:\s*start=\s*(\d+),\s*size=\s*(\d+)",line)
 if m:d[int(m.group(1))]=(int(m.group(2)),int(m.group(3)))
print(json.dumps({str(k):list(v) for k,v in sorted(d.items())},sort_keys=True))
'
}

assert_entry_geometry(){
  local g
  g="$(parse_geometry)"
  python3 - "$g" "$P3_START" "$P3_ORIGINAL_SIZE" <<'PY'
import json,sys
g={int(k):tuple(v) for k,v in json.loads(sys.argv[1]).items()}
p3=(int(sys.argv[2]),int(sys.argv[3]))
exp={1:(2048,532480),2:(534528,32768),3:p3,5:(854411576,144420552),4:(998832128,1368064)}
assert g==exp,(g,exp)
PY
}

# V8 resumes from the exact fail-closed checkpoint left by run 36682665542.
# P3 is already physically shrunk, the original NTFS is still authoritative,
# and the temporary ext4 exists but PROYECTOS had not started copying.
TMPDEV="$(json_get temporary.device)"
TEMP_UUID="$(json_get temporary.uuid)"
TEMP_SIZE="$((TEMP_END-TEMP_START+1))"
[ -b "$TMPDEV" ] || hold TEMP_DEVICE_NOT_BLOCK
TMPNUM="${TMPDEV##*p}"
[[ "$TMPNUM" =~ ^[0-9]+$ ]] || hold TEMP_PARTITION_NUMBER_INVALID

python3 - "$(parse_geometry)" "$P3_START" "$P3_SHRUNK_SIZE" "$TMPNUM" "$TEMP_START" "$TEMP_SIZE" <<'PY'
import json,sys
g={int(k):tuple(v) for k,v in json.loads(sys.argv[1]).items()}
p3=(int(sys.argv[2]),int(sys.argv[3])); tn=int(sys.argv[4]); temp=(int(sys.argv[5]),int(sys.argv[6]))
exp={1:(2048,532480),2:(534528,32768),3:p3,5:(854411576,144420552),4:(998832128,1368064),tn:temp}
assert tn not in {1,2,3,4,5},tn
assert g==exp,(g,exp)
PY
event V8_ENTRY_GEOMETRY_CONFIRMED

[ "$(cat /sys/class/block/nvme0n1p3/size)" = "$P3_SHRUNK_SIZE" ] || hold KERNEL_P3_NOT_SHRUNK
[ "$(blkid_uuid "$P3")" = "$OLD_UUID" ] || hold P3_UUID_ENTRY_MISMATCH
[ "$(sudo -n blkid -p -s TYPE -o value "$P3")" = ntfs ] || hold P3_NOT_NTFS
[ "$(sudo -n blkid -p -s TYPE -o value "$TMPDEV")" = ext4 ] || hold TEMP_NOT_EXT4
[ "$(sudo -n blkid -p -s LABEL -o value "$TMPDEV")" = LOUKSNA_TMP ] || hold TEMP_LABEL_MISMATCH
[ "$(blkid_uuid "$TMPDEV")" = "$TEMP_UUID" ] || hold TEMP_UUID_MISMATCH

normalize_mount(){
  local dev="$1" expected="$2" mp
  mp="$(findmnt -rn -S "$dev" -o TARGET | head -1 || true)"
  if [ -n "$mp" ]; then
    [ -n "$expected" ] || hold "UNPLANNED_MOUNT:$dev:$mp"
    [ "$mp" = "$expected" ] || hold "MOUNT_DRIFT:$dev:expected=$expected:actual=$mp"
    sudo -n umount "$mp"
  else
    [ -z "$expected" ] || hold "EXPECTED_MOUNT_MISSING:$dev:$expected"
  fi
}
normalize_mount "$P3" "$(json_get preexisting_mounts.p3)"
normalize_mount "$TMPDEV" "$(json_get preexisting_mounts.temp)"
findmnt -n -S "$P3" >/dev/null 2>&1 && hold P3_MOUNT_REMAINS_AFTER_NORMALIZE
findmnt -n -S "$TMPDEV" >/dev/null 2>&1 && hold TEMP_MOUNT_REMAINS_AFTER_NORMALIZE
event V8_STALE_MOUNTS_NORMALIZED

sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_V8_ENTRY.sfdisk"
sha256sum "$OUT/PARTITION_TABLE_V8_ENTRY.sfdisk" > "$OUT/PARTITION_TABLE_V8_ENTRY.sha256"

sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRCM"
python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE_V8_ENTRY.json"
sudo -n umount "$SRCM"
event SOURCE_REVERIFIED_V8_ENTRY
event P3_ALREADY_SHRUNK_V8
event TEMP_EXT4_REUSED_V8

sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRCM"
sudo -n mount -t ext4 "$TMPDEV" "$TMPM"
sudo -n chown "$(id -u):$(id -g)" "$TMPM"
[ -z "$(findmnt -rn -R "$TMPM" -o TARGET | tail -n +2)" ] || hold TEMP_NESTED_MOUNTS
[ ! -e "$TMPM/PROYECTOS" ] && [ ! -L "$TMPM/PROYECTOS" ] || hold TEMP_NOT_CLEAN
python3 - "$TMPM" <<'PY'
import os,sys
entries=set(os.listdir(sys.argv[1]))
assert entries in (set(),{"lost+found"}),entries
PY
TEMP_AVAIL="$(df -B1 --output=avail "$TMPM"|tail -1|tr -d ' ')"
TEMP_IFREE="$(df --output=iavail "$TMPM"|tail -1|tr -d ' ')"
[ "$TEMP_AVAIL" -ge $((EXPECTED_BYTES+1000000000)) ] || hold TEMP_BYTES_TOO_SMALL
[ "$TEMP_IFREE" -ge 600000 ] || hold TEMP_INODES_TOO_SMALL
python3 - "$OUT/CAPACITY_PRECOPY.json" "$TEMP_AVAIL" "$TEMP_IFREE" "$EXPECTED_BYTES" <<'PY'
import json,sys
out,avail,inodes,src=sys.argv[1],*map(int,sys.argv[2:])
assert avail>=src+1000000000 and inodes>=600000
json.dump({"status":"PASS","available_bytes":avail,"available_inodes":inodes,"required_bytes":src+1000000000,"expected_source_bytes":src},open(out,"w"),indent=2)
PY

python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE_PRECOPY.json"
python3 "$XATTR_VERIFY" --root "$SRCM/PROYECTOS" --out "$OUT/XATTR_SOURCE.json"
python3 "$POSIX_VERIFY" --root "$SRCM/PROYECTOS" --out "$OUT/POSIX_SOURCE.json"
python3 - "$OUT/POSIX_SOURCE.json" "$PLAN" <<'PY'
import json,sys
actual=json.load(open(sys.argv[1])); plan=json.load(open(sys.argv[2])); assert actual["fingerprint_sha256"]==plan["source_posix_fingerprint"],"SOURCE_POSIX_DRIFT"
PY
event SOURCE_METADATA_POLICY_VERIFIED
mkdir -p "$TMPM/PROYECTOS"
sudo -n rsync -aHA --no-xattrs --delete --numeric-ids "$SRCM/PROYECTOS/" "$TMPM/PROYECTOS/"
sync
python3 "$VERIFY" --root "$TMPM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_TEMP.json"
python3 "$POSIX_VERIFY" --root "$TMPM/PROYECTOS" --out "$OUT/POSIX_TEMP.json" --expect "$OUT/POSIX_SOURCE.json"
event TEMP_COPY_CONTENT_AND_POSIX_VERIFIED

sudo -n umount "$SRCM"
if findmnt -n -S "$P3" >/dev/null 2>&1; then hold P3_STILL_MOUNTED_BEFORE_REFORMAT; fi
python3 "$VERIFY" --root "$TMPM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_TEMP_PREREFORMAT.json"
python3 "$POSIX_VERIFY" --root "$TMPM/PROYECTOS" --out "$OUT/POSIX_TEMP_PREREFORMAT.json" --expect "$OUT/POSIX_SOURCE.json"
event ROLLBACK_COPY_REVERIFIED

sudo -n mkfs.ext4 -F -m 0 -N 1000000 -L LOUKSNA_PROJECTS "$P3"
sudo -n mount -t ext4 "$P3" "$FINALM"
sudo -n chown "$(id -u):$(id -g)" "$FINALM"
event P3_REFORMATTED_EXT4

sudo -n rsync -aHA --no-xattrs --delete --numeric-ids "$TMPM/PROYECTOS/" "$FINALM/"
sync
python3 "$VERIFY" --root "$FINALM" --manifest "$MANIFEST" --out "$OUT/VERIFY_P3_PREEXPAND.json"
python3 "$POSIX_VERIFY" --root "$FINALM" --out "$OUT/POSIX_P3_PREEXPAND.json" --expect "$OUT/POSIX_SOURCE.json"
event P3_COPY_CONTENT_AND_POSIX_VERIFIED

sudo -n umount "$FINALM"
sudo -n umount "$TMPM"

if [ -e "/sys/class/block/nvme0n1p$TMPNUM" ]; then
  [ "$(blkid_uuid "$TMPDEV")" = "$(json_get temporary.uuid)" ] || hold TEMP_UUID_DRIFT_BEFORE_RETIRE
  sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_BEFORE_TEMP_RETIRE.sfdisk"
  sudo -n parted -s "$DISK" rm "$TMPNUM"
else
  hold TEMP_PARTITION_DISAPPEARED
fi
sudo -n partprobe "$DISK" || true
sudo -n partx -u "$DISK" || true
sudo -n udevadm settle
event TEMP_PARTITION_RETIRED

resize_partition_sfdisk(){
  local num new_size before spec
  num="$1"
  new_size="$2"
  before="$OUT/sfdisk-before-p${num}-$(date +%s%N).txt"
  spec="$OUT/sfdisk-spec-p${num}-$(date +%s%N).txt"
  sudo -n sfdisk --dump "$DISK" > "$before"
  python3 - "$before" "$num" "$new_size" "$spec" <<'PY'
import re,sys,pathlib
p=pathlib.Path(sys.argv[1]); num=int(sys.argv[2]); new=int(sys.argv[3]); out=pathlib.Path(sys.argv[4])
prefix=f"/dev/nvme0n1p{num}"
hits=[x for x in p.read_text(errors="replace").splitlines() if x.startswith(prefix+" ")]
assert len(hits)==1,hits
rhs=hits[0].split(":",1)[1].strip()
rhs,n=re.subn(r"\bsize=\s*\d+",f"size={new}",rhs,count=1)
assert n==1,rhs
out.write_text(rhs+"\n")
PY
  sudo -n sfdisk --force --no-reread -N "$num" "$DISK" < "$spec"
  sudo -n partx -u --nr "$num" "$DISK" || true
  sudo -n partprobe "$DISK" || true
  sudo -n udevadm settle
}

python3 - "$(parse_geometry)" "$P3_START" "$P3_SHRUNK_SIZE" <<'PY'
import json,sys
g={int(k):tuple(v) for k,v in json.loads(sys.argv[1]).items()}
assert g=={1:(2048,532480),2:(534528,32768),3:(int(sys.argv[2]),int(sys.argv[3])),5:(854411576,144420552),4:(998832128,1368064)},g
PY
resize_partition_sfdisk 3 "$FINAL_P3_SIZE"
test "$(cat /sys/class/block/nvme0n1p3/size)" = "$FINAL_P3_SIZE" || hold KERNEL_P3_SIZE_AFTER_EXPAND
sudo -n e2fsck -f -p "$P3" || rc=$?
if [ "${rc:-0}" -gt 1 ]; then hold "E2FSCK_FAILED:${rc:-0}"; fi
sudo -n resize2fs "$P3"
event P3_EXT4_EXPANDED

mkdir -p "$FINAL_MOUNT"
sudo -n mount -t ext4 "$P3" "$FINAL_MOUNT"
NEW_UUID="$(blkid_uuid "$P3")"
[ -n "$NEW_UUID" ] || hold NEW_UUID_MISSING
[ "$NEW_UUID" != "$OLD_UUID" ] || hold NEW_UUID_EQUALS_OLD
python3 "$VERIFY" --root "$FINAL_MOUNT" --manifest "$MANIFEST" --out "$OUT/VERIFY_FINAL.json"
python3 "$POSIX_VERIFY" --root "$FINAL_MOUNT" --out "$OUT/POSIX_FINAL.json" --expect "$OUT/POSIX_SOURCE.json"
event FINAL_TREE_AND_POSIX_VERIFIED

sudo -n cp -a /etc/fstab "$OUT/fstab.before"
export NEW_UUID FINAL_MOUNT OLD_UUID
sudo -n -E python3 - <<'PY'
import os,pathlib
p=pathlib.Path("/etc/fstab"); old=p.read_text(encoding="utf-8").splitlines(); new=[]
for line in old:
    s=line.strip()
    if not s or s.startswith("#"): new.append(line); continue
    f=s.split()
    if len(f)>=2 and (f[0] in {os.environ["OLD_UUID"],"UUID="+os.environ["OLD_UUID"]} or f[1] in {os.environ["FINAL_MOUNT"],"/media/diegoignacionorambuenamiranda/Windows"}):
        continue
    new.append(line)
new.append(f'UUID={os.environ["NEW_UUID"]} {os.environ["FINAL_MOUNT"]} ext4 defaults,nofail,x-systemd.device-timeout=10 0 2')
t=p.with_name("fstab.louksna-part4-r2-v8.tmp"); t.write_text("\n".join(new)+"\n",encoding="utf-8"); os.chmod(t,0o644); os.replace(t,p)
PY
event FSTAB_PERSISTED

sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_AFTER.sfdisk"
lsblk -b -J -o NAME,PATH,TYPE,SIZE,FSTYPE,FSAVAIL,FSUSE%,MOUNTPOINTS,UUID,PARTUUID,START > "$OUT/LSBLK_FINAL.json"
df -B1 "$FINAL_MOUNT" > "$OUT/DF_FINAL.txt"

python3 - "$OUT/PARTITION_TABLE_AFTER.sfdisk" "$P3_START" "$FINAL_P3_SIZE" <<'PY'
import re,sys
d={}
for line in open(sys.argv[1],errors="replace"):
 m=re.match(r"^/dev/nvme0n1p(\d+)\s*:\s*start=\s*(\d+),\s*size=\s*(\d+)",line)
 if m:d[int(m.group(1))]=(int(m.group(2)),int(m.group(3)))
exp={1:(2048,532480),2:(534528,32768),3:(int(sys.argv[2]),int(sys.argv[3])),5:(854411576,144420552),4:(998832128,1368064)}
assert d==exp,(d,exp)
PY

sha256sum "$OUT"/* | sort > "$OUT/FINAL_EVIDENCE.sha256"

python3 - "$REPORT" "$R2_STATE" "$NEW_UUID" "$TMPDEV" <<'PY'
import json,sys,time,os,pathlib
rp,sp,newuuid,tmpdev=sys.argv[1:]
d=json.load(open(rp)); d["status"]="PASS"; d["new_p3_ext4_uuid"]=newuuid; d["temporary_partition"]=tmpdev
d["final_mount"]=os.path.expanduser("~/PROYECTOS"); d["finished_at_utc"]=time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())
t=rp+".tmp"; json.dump(d,open(t,"w"),indent=2,sort_keys=True); os.replace(t,rp)
p=pathlib.Path(sp)
s=json.loads(p.read_text()) if p.exists() else {}
s.update({"storage_resume_v8_material_pass":True,"ntfs_shrunk":True,"ext4_created":True,"projects_migrated_hash_equivalent":True,"projects_posix_metadata_equivalent":True,"raw_ntfs_wsl_xattrs_transported":False,
          "xattr_transport_policy":"NTFS3_LX_TO_POSIX_STAT_PLUS_RSYNC_ACL_NO_RAW_XATTRS","ntfs_retired":True,"final_linux_layout":False,"part4_r2_final_g24":False,
          "final_projects_mount":os.path.expanduser("~/PROYECTOS"),"final_projects_uuid":newuuid,
          "updated_at_utc":d["finished_at_utc"]})
tmp=sp+".tmp"; json.dump(s,open(tmp,"w"),indent=2,sort_keys=True); os.replace(tmp,sp)
PY
trap - ERR
event MATERIAL_RESUME_V8_PASS
exit 0
