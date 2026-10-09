#!/bin/bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

PLAN="${1:-}"
OUT="${2:-}"
MANIFEST="${3:-}"

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
WORK="$STATE_ROOT/PART_4_R2/migration-v4"
SRCM="$WORK/source-ntfs"
TMPM="$WORK/temp-ext4"
FINALM="$WORK/final-ext4"
FINAL_MOUNT="$HOME/PROYECTOS"
VERIFY="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)/part4_r2_verify_tree.py"

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
mkdir -p "$OUT" "$WORK" "$SRCM" "$TMPM" "$FINALM"
chmod 700 "$OUT" "$WORK" "$SRCM" "$TMPM" "$FINALM"

for c in python3 sha256sum sfdisk partx partprobe udevadm lsblk findmnt ntfsresize mount umount mkfs.ext4 rsync sync e2fsck resize2fs blkid stat; do need "$c"; done
[ -x "$RUNUSER" ] || hold RUNUSER_MISSING
[ "$(sha256sum "$RUNUSER"|awk '{print $1}')" = "$RUNUSER_SHA" ] || hold RUNUSER_HASH_DRIFT
sudo -n true >/dev/null 2>&1 || hold NONINTERACTIVE_SUDO_REQUIRED
sudo -n "$RUNUSER" -u "$TARGET_USER" -- bash --noprofile --norc -c 'sudo -k >/dev/null 2>&1 || true; test "$(sudo -n id -u)" = 0; test "$(sudo -n id -un)" = root' || hold PRIVILEGE_ROUNDTRIP_FAILED
[ "$(sha256sum "$MANIFEST"|awk '{print $1}')" = "$EXPECTED_MANIFEST_SHA" ] || hold MANIFEST_DIGEST_MISMATCH
[ "$(json_get status)" = PASS ] || hold PLAN_NOT_PASS
[ "$(json_get stage)" = NTFS_FILESYSTEM_SHRUNK_P3_BOUNDARY_ORIGINAL ] || hold PLAN_STAGE_MISMATCH
[ "$(json_get source_failure_run)" = 36661752109 ] || hold SOURCE_FAILURE_BINDING_MISMATCH

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
json.dump({"schema":"LOUKSNA_R4_PART4_R2_STORAGE_RESUME_V4/1.0","status":"RUNNING","events":[],"started_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())},open(sys.argv[1],"w"),indent=2)
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

assert_entry_geometry
[ "$(blkid_uuid "$P3")" = "$OLD_UUID" ] || hold P3_UUID_ENTRY_MISMATCH
if findmnt -n -S "$P3" >/dev/null 2>&1; then hold P3_MUST_BE_UNMOUNTED_AT_RESUME_ENTRY; fi

INFO="$OUT/NTFS_INFO_ENTRY.txt"
LC_ALL=C sudo -n ntfsresize --info --force "$P3" > "$INFO" 2>&1
python3 - "$INFO" "$FS_TARGET" "$((P3_ORIGINAL_SIZE*512))" <<'PY'
import re,sys
t=open(sys.argv[1],errors="replace").read()
fs=int(sys.argv[2]); dev=int(sys.argv[3])
m=re.search(r"Current volume size:\s*([0-9]+) bytes",t); n=re.search(r"Current device size:\s*([0-9]+) bytes",t)
assert m and n,t[-2000:]
vol=int(m.group(1)); device=int(n.group(1))
assert 0 <= fs-vol < 4096,(vol,fs)
assert device==dev,(device,dev)
PY
event LIVE_NTFS_SHRINK_RECONFIRMED

sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_RESUME_CHECKPOINT.sfdisk"
sha256sum "$OUT/PARTITION_TABLE_RESUME_CHECKPOINT.sfdisk" > "$OUT/PARTITION_TABLE_RESUME_CHECKPOINT.sha256"
event GPT_CHECKPOINT_BEFORE_BOUNDARY_SHRINK

sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRCM"
python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE_RESUME_ENTRY.json"
sudo -n umount "$SRCM"
event SOURCE_REVERIFIED_AFTER_NTFS_SHRINK

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

resize_partition_sfdisk 3 "$P3_SHRUNK_SIZE"
test "$(cat /sys/class/block/nvme0n1p3/size)" = "$P3_SHRUNK_SIZE" || hold KERNEL_P3_SIZE_AFTER_SHRINK
python3 - "$(parse_geometry)" "$P3_START" "$P3_SHRUNK_SIZE" <<'PY'
import json,sys
g={int(k):tuple(v) for k,v in json.loads(sys.argv[1]).items()}
assert g[3]==(int(sys.argv[2]),int(sys.argv[3])),g
assert g[1]==(2048,532480) and g[2]==(534528,32768) and g[5]==(854411576,144420552) and g[4]==(998832128,1368064)
PY
event P3_PARTITION_SHRUNK_SFDISK

sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRCM"
python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE_POST_BOUNDARY.json"
sudo -n umount "$SRCM"
event SOURCE_VERIFIED_POST_BOUNDARY

sudo -n parted -s "$DISK" unit s mkpart LOUKSNA_TMP ext4 "${TEMP_START}s" "${TEMP_END}s"
sudo -n partprobe "$DISK" || true
sudo -n partx -u "$DISK" || true
sudo -n udevadm settle

TMPDEV="$(python3 - "$TEMP_START" <<'PY'
import glob,sys
want=int(sys.argv[1]); hits=[]
for p in glob.glob("/sys/class/block/nvme0n1p*/start"):
    try:
        if int(open(p).read().strip())==want: hits.append("/dev/"+p.split("/")[-2])
    except Exception: pass
assert len(hits)==1,hits
print(hits[0])
PY
)"
[ -b "$TMPDEV" ] || hold TEMP_DEVICE_NOT_BLOCK
TMPNUM="${TMPDEV##*p}"
sudo -n mkfs.ext4 -F -m 0 -N 1000000 -L LOUKSNA_TMP "$TMPDEV"
event TEMP_EXT4_CREATED

sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRCM"
sudo -n mount -t ext4 "$TMPDEV" "$TMPM"
sudo -n chown "$(id -u):$(id -g)" "$TMPM"
TEMP_AVAIL="$(df -B1 --output=avail "$TMPM"|tail -1|tr -d ' ')"
TEMP_IFREE="$(df -i --output=iavail "$TMPM"|tail -1|tr -d ' ')"
[ "$TEMP_AVAIL" -ge $((EXPECTED_BYTES+1000000000)) ] || hold TEMP_BYTES_TOO_SMALL
[ "$TEMP_IFREE" -ge 600000 ] || hold TEMP_INODES_TOO_SMALL

python3 "$VERIFY" --root "$SRCM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_SOURCE_PRECOPY.json"
mkdir -p "$TMPM/PROYECTOS"
sudo -n rsync -aHAX --delete --numeric-ids "$SRCM/PROYECTOS/" "$TMPM/PROYECTOS/"
sync
python3 "$VERIFY" --root "$TMPM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_TEMP.json"
event TEMP_COPY_VERIFIED

sudo -n umount "$SRCM"
if findmnt -n -S "$P3" >/dev/null 2>&1; then hold P3_STILL_MOUNTED_BEFORE_REFORMAT; fi
python3 "$VERIFY" --root "$TMPM/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/VERIFY_TEMP_PREREFORMAT.json"
event ROLLBACK_COPY_REVERIFIED

sudo -n mkfs.ext4 -F -m 0 -N 1000000 -L LOUKSNA_PROJECTS "$P3"
sudo -n mount -t ext4 "$P3" "$FINALM"
sudo -n chown "$(id -u):$(id -g)" "$FINALM"
event P3_REFORMATTED_EXT4

sudo -n rsync -aHAX --delete --numeric-ids "$TMPM/PROYECTOS/" "$FINALM/"
sync
python3 "$VERIFY" --root "$FINALM" --manifest "$MANIFEST" --out "$OUT/VERIFY_P3_PREEXPAND.json"
event P3_COPY_VERIFIED

sudo -n umount "$FINALM"
sudo -n umount "$TMPM"

if [ -e "/sys/class/block/nvme0n1p$TMPNUM" ]; then
  sudo -n parted -s "$DISK" rm "$TMPNUM"
fi
sudo -n partprobe "$DISK" || true
sudo -n partx -u "$DISK" || true
sudo -n udevadm settle
event TEMP_PARTITION_RETIRED

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
event FINAL_TREE_VERIFIED

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
t=p.with_name("fstab.louksna-part4-r2-v4.tmp"); t.write_text("\n".join(new)+"\n",encoding="utf-8"); os.chmod(t,0o644); os.replace(t,p)
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
s.update({"storage_resume_v4_material_pass":True,"ntfs_shrunk":True,"ext4_created":True,"projects_migrated_hash_equivalent":True,
          "ntfs_retired":True,"final_linux_layout":False,"part4_r2_final_g24":False,
          "final_projects_mount":os.path.expanduser("~/PROYECTOS"),"final_projects_uuid":newuuid,
          "updated_at_utc":d["finished_at_utc"]})
tmp=sp+".tmp"; json.dump(s,open(tmp,"w"),indent=2,sort_keys=True); os.replace(tmp,sp)
PY
trap - ERR
event MATERIAL_RESUME_PASS
exit 0
