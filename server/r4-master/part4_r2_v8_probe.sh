#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
MANIFEST="$1"; OUT="$2"
mkdir -p "$OUT"; chmod 700 "$OUT"
DISK=/dev/nvme0n1; P3=/dev/nvme0n1p3
EXPECTED_SHA=99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e
HELPER=server/r4-master
TMP_PROBE="$OUT/temp-ro"; SRC_PROBE="$OUT/source-ro"
OWN_SRC=0; OWN_TMP=0
hold(){ printf 'HOLD:%s\n' "$*" >&2; exit 20; }
cleanup_mounts(){
  if [ "$OWN_TMP" = 1 ]; then sudo -n umount "$TMP_PROBE" || true; fi
  if [ "$OWN_SRC" = 1 ]; then sudo -n umount "$SRC_PROBE" || true; fi
}
trap cleanup_mounts EXIT
for c in sudo python3 sha256sum sfdisk findmnt blkid mount umount df stat; do command -v "$c" >/dev/null || hold "MISSING:$c"; done
[ "$(hostname)" = LOUKSNA ] || hold HOST_DRIFT
[ "$(id -un)" = diegoignacionorambuenamiranda ] || hold USER_DRIFT
sudo -n true || hold SUDO_UNAVAILABLE
sudo -n visudo -c >/dev/null || hold SUDO_POLICY_INVALID
test "$(systemctl is-active actions.runner.Plomillo-luna-linux-bridge.luna-linux.service)" = active || hold RUNNER_NOT_ACTIVE
test "$(sha256sum "$MANIFEST" | awk '{print $1}')" = "$EXPECTED_SHA" || hold MANIFEST_DRIFT
for f in part4_r2_verify_tree.py part4_r2_xattr_inventory.py part4_r2_posix_fingerprint_v8.py part4_r2_storage_resume_after_v7_capacity_fail_closed_v8.sh part4_r2_temp_cleanup_v8.sh; do
  test -f "$HELPER/$f" || hold "MISSING_SOURCE:$f"
done
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_LIVE.sfdisk"
TMPDEV="$(python3 - "$OUT/PARTITION_TABLE_LIVE.sfdisk" <<'PY'
import re,sys
d={}
for line in open(sys.argv[1],errors="replace"):
 m=re.match(r"^/dev/nvme0n1p(\d+)\s*:\s*start=\s*(\d+),\s*size=\s*(\d+)",line)
 if m: d[int(m.group(1))]=(int(m.group(2)),int(m.group(3)))
temp=(447199232,854409528-447199232+1)
hits=[n for n,v in d.items() if v==temp]
assert len(hits)==1 and hits[0] not in {1,2,3,4,5},(d,hits)
assert d=={1:(2048,532480),2:(534528,32768),3:(567296,446629888),4:(998832128,1368064),5:(854411576,144420552),hits[0]:temp},d
print(f"/dev/nvme0n1p{hits[0]}")
PY
)"
test -b "$TMPDEV" || hold TEMP_NOT_BLOCK
test "$(cat /sys/class/block/nvme0n1p3/size)" = 446629888 || hold P3_KERNEL_GEOMETRY_DRIFT
test "$(sudo -n blkid -p -s UUID -o value "$P3")" = F2848A148489DC0B || hold P3_UUID_DRIFT
test "$(sudo -n blkid -p -s TYPE -o value "$P3")" = ntfs || hold P3_NOT_NTFS
test "$(sudo -n blkid -p -s TYPE -o value "$TMPDEV")" = ext4 || hold TEMP_NOT_EXT4
test "$(sudo -n blkid -p -s LABEL -o value "$TMPDEV")" = LOUKSNA_TMP || hold TEMP_LABEL_DRIFT
TEMP_UUID="$(sudo -n blkid -p -s UUID -o value "$TMPDEV")"
P3_MP="$(findmnt -rn -S "$P3" -o TARGET | head -1 || true)"
TEMP_MP="$(findmnt -rn -S "$TMPDEV" -o TARGET | head -1 || true)"
V7ROOT="$HOME/.local/state/louksna/r4-master-part1-part9/PART_4_R2/migration-v7"
test -z "$P3_MP" || test "$P3_MP" = "$V7ROOT/source-ntfs" || hold "UNEXPECTED_P3_MOUNT:$P3_MP"
test -z "$TEMP_MP" || test "$TEMP_MP" = "$V7ROOT/temp-ext4" || hold "UNEXPECTED_TEMP_MOUNT:$TEMP_MP"
mkdir -p "$SRC_PROBE" "$TMP_PROBE"
if [ -n "$P3_MP" ]; then
 SRC="$P3_MP"
else
 sudo -n mount -t ntfs3 -o "ro,uid=$(id -u),gid=$(id -g),umask=0077" "$P3" "$SRC_PROBE"
 OWN_SRC=1; SRC="$SRC_PROBE"
fi
findmnt -rn -T "$SRC" -o OPTIONS | grep -Eq '(^|,)ro(,|$)' || hold SOURCE_NOT_READ_ONLY
python3 "$HELPER/part4_r2_verify_tree.py" --root "$SRC/PROYECTOS" --manifest "$MANIFEST" --out "$OUT/SOURCE_VERIFY.json"
python3 "$HELPER/part4_r2_xattr_inventory.py" --root "$SRC/PROYECTOS" --out "$OUT/SOURCE_XATTR.json"
python3 "$HELPER/part4_r2_posix_fingerprint_v8.py" --root "$SRC/PROYECTOS" --out "$OUT/SOURCE_POSIX.json"
if [ -n "$TEMP_MP" ]; then
 TMP="$TEMP_MP"
else
 sudo -n mount -t ext4 -o ro,noload "$TMPDEV" "$TMP_PROBE"
 OWN_TMP=1; TMP="$TMP_PROBE"
fi
[ "$(findmnt -rn -R "$TMP" -o TARGET | wc -l)" = 1 ] || hold TEMP_NESTED_MOUNT
python3 - "$TMP" "$OUT/TEMP_ROOT_AUDIT.json" <<'PY'
import json,os,pathlib,stat,sys,time
root=pathlib.Path(sys.argv[1]); names=sorted(os.listdir(root)); allowed=names in ([],["lost+found"],["PROYECTOS"],["PROYECTOS","lost+found"])
partial=root/"PROYECTOS"
p_exists=partial.exists() or partial.is_symlink()
p_ok=not p_exists or (partial.is_dir() and not partial.is_symlink() and partial.lstat().st_dev==root.lstat().st_dev and not os.path.ismount(partial))
d={"status":"PASS" if allowed and p_ok else "HOLD","top_level_names":names,"partial_present":p_exists,"partial_is_real_directory":p_ok,"temporary_mount":str(root),
   "checked_at_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())}
pathlib.Path(sys.argv[2]).write_text(json.dumps(d,indent=2,sort_keys=True)+"\n")
print(json.dumps(d))
if d["status"]!="PASS": raise SystemExit(23)
PY
read FS_TOTAL FS_USED FS_AVAIL < <(df -B1 --output=size,used,avail "$TMP" | tail -1)
read FS_IFREE < <(df --output=iavail "$TMP" | tail -1)
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_POSTSCAN.sfdisk"
cmp -s "$OUT/PARTITION_TABLE_LIVE.sfdisk" "$OUT/PARTITION_TABLE_POSTSCAN.sfdisk" || hold GEOMETRY_CHANGED_DURING_PROBE
test "$(sudo -n blkid -p -s UUID -o value "$P3")" = F2848A148489DC0B || hold SOURCE_CHANGED_DURING_PROBE
test "$(sudo -n blkid -p -s UUID -o value "$TMPDEV")" = "$TEMP_UUID" || hold TEMP_CHANGED_DURING_PROBE
export P3_MP TEMP_MP TMPDEV TEMP_UUID FS_TOTAL FS_USED FS_AVAIL FS_IFREE
python3 - "$OUT" <<'PY'
import datetime as dt,hashlib,json,os,pathlib,sys
r=pathlib.Path(sys.argv[1])
load=lambda name:json.loads((r/name).read_text())
sv=load("SOURCE_VERIFY.json"); sx=load("SOURCE_XATTR.json"); sp=load("SOURCE_POSIX.json"); ta=load("TEMP_ROOT_AUDIT.json")
assert sv["status"]=="PASS" and sv["mismatch_count"]==0 and sv["seen_records"]==498092 and sv["regular_file_bytes"]==200490852057
assert sx["status"]=="PASS" and sx["unexpected_count"]==0 and sx["records_scanned"]==498092
assert sp["status"]=="PASS" and sp["records"]==498092 and sp["directory_nlink_normalized"] is True
assert ta["status"]=="PASS"
h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
base=pathlib.Path("server/r4-master")
plan={"schema":"LOUKSNA_PART4_R2_V8_CLEANUP_PLAN/1.0","status":"PASS","source_failure_run":36682665542,
"stage":"P3_SHRUNK_TEMP_EXT4_PARTIAL_V6_V7_CAPACITY_HOLD","disk":"/dev/nvme0n1","source_partition":"/dev/nvme0n1p3","source_uuid":"F2848A148489DC0B",
"manifest_sha256":"99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e",
"temporary":{"device":os.environ["TMPDEV"],"uuid":os.environ["TEMP_UUID"],"fstype":"ext4","label":"LOUKSNA_TMP",
"start":447199232,"end":854409528,"size_sectors":854409528-447199232+1},
"geometry":{"p3_start":567296,"p3_original_size":853844280,"p3_shrunk_size":446629888,"p3_new_end":447197183,
"temp_start":447199232,"temp_end":854409528,"p3_final_size":853842233,"p3_final_end":854409528},
"preexisting_mounts":{"p3":os.environ["P3_MP"],"temp":os.environ["TEMP_MP"]},
"partial_present":ta["partial_present"],"temp_root_audit_sha256":h(r/"TEMP_ROOT_AUDIT.json"),
"source_verify_sha256":h(r/"SOURCE_VERIFY.json"),"source_xattr_sha256":h(r/"SOURCE_XATTR.json"),
"source_posix_sha256":h(r/"SOURCE_POSIX.json"),"source_posix_fingerprint":sp["fingerprint_sha256"],
"partition_checkpoint_sha256":h(r/"PARTITION_TABLE_LIVE.sfdisk"),
"cleanup_script_sha256":h(base/"part4_r2_temp_cleanup_v8.sh"),
"migration_script_sha256":h(base/"part4_r2_storage_resume_after_v7_capacity_fail_closed_v8.sh"),
"temporary_before":{"total_bytes":int(os.environ["FS_TOTAL"]),"used_bytes":int(os.environ["FS_USED"]),"available_bytes":int(os.environ["FS_AVAIL"]),"available_inodes":int(os.environ["FS_IFREE"])},
"required_after_cleanup_bytes":201490852057,"required_after_cleanup_inodes":600000,
"cleanup_scope":"TEMP_EXT4_PROYECTOS_PARTIAL_ONLY","p3_mutation_authorized":False,
"rollback":"P3_SHRUNK_NTFS_IS_SOURCE_OF_TRUTH",
"created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
(r/"CLEANUP_PLAN_V8.json").write_text(json.dumps(plan,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PASS","p3":"PRESERVED_NTFS","temp_partial":ta["partial_present"],"temp_before":plan["temporary_before"]}))
PY
