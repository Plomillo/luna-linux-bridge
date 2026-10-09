#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:$PATH"
PLAN="$1"; CERT="$2"; OUT="$3"
mkdir -p "$OUT"; chmod 700 "$OUT"
STATE_ROOT="$HOME/.local/state/louksna/r4-master-part1-part9"
TMPM="$STATE_ROOT/PART_4_R2/migration-v8-clean/temp-ext4"
P3=/dev/nvme0n1p3; DISK=/dev/nvme0n1
REPORT="$OUT/CLEANUP_RESULT_V8.json"
hold(){ printf 'HOLD:%s\n' "$*" >&2; exit 20; }
value(){ python3 - "$PLAN" "$1" <<'PY'
import json,sys
p=json.load(open(sys.argv[1]))
for k in sys.argv[2].split("."): p=p[k]
print(p if not isinstance(p,bool) else str(p).lower())
PY
}
digest(){ sha256sum "$1" | awk '{print $1}'; }
[ "$(id -un)" = diegoignacionorambuenamiranda ] || hold USER_DRIFT
[ "$HOME" = /home/diegoignacionorambuenamiranda ] || hold HOME_DRIFT
test -f "$PLAN" && test -f "$CERT" || hold PLAN_OR_CERT_MISSING
[ "$(value status)" = PASS ] || hold PLAN_NOT_PASS
[ "$(value source_failure_run)" = 36682665542 ] || hold SOURCE_RUN_DRIFT
[ "$(value cleanup_scope)" = TEMP_EXT4_PROYECTOS_PARTIAL_ONLY ] || hold BAD_SCOPE
[ "$(digest "$0")" = "$(value cleanup_script_sha256)" ] || hold SCRIPT_HASH_DRIFT
python3 - "$CERT" "$PLAN" <<'PY'
import hashlib,json,sys
cert=json.load(open(sys.argv[1])); p=open(sys.argv[2],"rb").read()
assert cert["status"]=="PASS"
assert cert["scope"]=="TEMP_EXT4_PROYECTOS_PARTIAL_ONLY"
assert cert["plan_sha256"]==hashlib.sha256(p).hexdigest()
assert cert["p3_mutation_authorized"] is False
PY
sudo -n true || hold SUDO_UNAVAILABLE
[ "$(sudo -n blkid -p -s UUID -o value "$P3")" = F2848A148489DC0B ] || hold P3_UUID_DRIFT
[ "$(sudo -n blkid -p -s TYPE -o value "$P3")" = ntfs ] || hold P3_NOT_NTFS
test "$(cat /sys/class/block/nvme0n1p3/size)" = 446629888 || hold P3_SIZE_DRIFT
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_PRECLEAN.sfdisk"
[ "$(digest "$OUT/PARTITION_TABLE_PRECLEAN.sfdisk")" = "$(value partition_checkpoint_sha256)" ] || hold GEOMETRY_DRIFT
TMPDEV="$(value temporary.device)"; TMP_UUID="$(value temporary.uuid)"
[ -b "$TMPDEV" ] || hold TEMP_DEVICE_MISSING
[ "$(sudo -n blkid -p -s UUID -o value "$TMPDEV")" = "$TMP_UUID" ] || hold TEMP_UUID_DRIFT
[ "$(sudo -n blkid -p -s TYPE -o value "$TMPDEV")" = ext4 ] || hold TEMP_FS_DRIFT
[ "$(sudo -n blkid -p -s LABEL -o value "$TMPDEV")" = LOUKSNA_TMP ] || hold TEMP_LABEL_DRIFT
P3_MP="$(findmnt -rn -S "$P3" -o TARGET | head -1 || true)"
TMP_OLD="$(findmnt -rn -S "$TMPDEV" -o TARGET | head -1 || true)"
[ "$P3_MP" = "$(value preexisting_mounts.p3)" ] || hold P3_MOUNT_DRIFT
[ "$TMP_OLD" = "$(value preexisting_mounts.temp)" ] || hold TEMP_MOUNT_DRIFT
if [ -n "$P3_MP" ]; then
 findmnt -rn -T "$P3_MP" -o OPTIONS | grep -Eq '(^|,)ro(,|$)' || hold P3_MOUNT_NOT_RO
fi
if [ -n "$TMP_OLD" ]; then sudo -n umount "$TMP_OLD" || hold STALE_TEMP_BUSY; fi
test -z "$(findmnt -rn -S "$TMPDEV" -o TARGET || true)" || hold TEMP_STILL_MOUNTED
mkdir -p "$TMPM"
[ ! -L "$TMPM" ] || hold TEMP_MOUNTPOINT_IS_SYMLINK
sudo -n mount -t ext4 "$TMPDEV" "$TMPM"
[ "$(findmnt -rn -S "$TMPDEV" -o TARGET | head -1)" = "$TMPM" ] || hold TEMP_MOUNT_UNEXPECTED
[ "$(findmnt -rn -R "$TMPM" -o TARGET | wc -l)" = 1 ] || hold NESTED_MOUNT_PRESENT
[ "$(sudo -n blkid -p -s UUID -o value "$TMPDEV")" = "$TMP_UUID" ] || hold TEMP_UUID_CHANGED
python3 - "$TMPM" "$PLAN" <<'PY'
import json,os,pathlib,sys
root=pathlib.Path(sys.argv[1]); p=json.load(open(sys.argv[2]))
names=sorted(os.listdir(root))
assert names in ([],["lost+found"],["PROYECTOS"],["PROYECTOS","lost+found"]),names
partial=root/"PROYECTOS"
present=partial.exists() or partial.is_symlink()
assert present is p["partial_present"],"PARTIAL_EXISTENCE_DRIFT"
if present:
 assert partial.is_dir() and not partial.is_symlink() and not os.path.ismount(partial)
 assert partial.stat().st_dev==root.stat().st_dev
PY
read PRE_TOTAL PRE_USED PRE_AVAIL < <(df -B1 --output=size,used,avail "$TMPM" | tail -1)
read PRE_IFREE < <(df --output=iavail "$TMPM" | tail -1)
PARTIAL_BYTES=0
if [ "$(value partial_present)" = true ]; then
 PARTIAL_BYTES="$(sudo -n du -sx -B1 "$TMPM/PROYECTOS" | awk '{print $1}')"
 sudo -n rm -rf --one-file-system -- "$TMPM/PROYECTOS"
fi
sync
[ ! -e "$TMPM/PROYECTOS" ] && [ ! -L "$TMPM/PROYECTOS" ] || hold TEMP_PARTIAL_REMAINS
python3 - "$TMPM" <<'PY'
import os,sys
names=sorted(os.listdir(sys.argv[1]))
assert names in ([],["lost+found"]),names
PY
read POST_TOTAL POST_USED POST_AVAIL < <(df -B1 --output=size,used,avail "$TMPM" | tail -1)
read POST_IFREE < <(df --output=iavail "$TMPM" | tail -1)
[ "$POST_TOTAL" -eq "$PRE_TOTAL" ] || hold TEMP_CAPACITY_CHANGED
[ "$POST_AVAIL" -ge 201490852057 ] || hold TEMP_STILL_TOO_SMALL
[ "$POST_IFREE" -ge 600000 ] || hold TEMP_INODES_TOO_SMALL
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_POSTCLEAN.sfdisk"
cmp -s "$OUT/PARTITION_TABLE_PRECLEAN.sfdisk" "$OUT/PARTITION_TABLE_POSTCLEAN.sfdisk" || hold DISK_GEOMETRY_CHANGED
[ "$(sudo -n blkid -p -s UUID -o value "$P3")" = F2848A148489DC0B ] || hold SOURCE_UUID_CHANGED
[ "$(sudo -n blkid -p -s TYPE -o value "$P3")" = ntfs ] || hold SOURCE_TYPE_CHANGED
sudo -n umount "$TMPM" || hold TEMP_UMOUNT_FAILED
test -z "$(findmnt -rn -S "$TMPDEV" -o TARGET || true)" || hold TEMP_MOUNT_REMAINS
export PRE_TOTAL PRE_USED PRE_AVAIL PRE_IFREE POST_TOTAL POST_USED POST_AVAIL POST_IFREE PARTIAL_BYTES P3_MP TMPDEV TMP_UUID
python3 - "$PLAN" "$REPORT" "$OUT/MIGRATION_PLAN_V8.json" <<'PY'
import datetime as dt,hashlib,json,os,pathlib,sys
plan_path,report_path,migration_path=map(pathlib.Path,sys.argv[1:])
p=json.loads(plan_path.read_text()); h=lambda x:hashlib.sha256(x.read_bytes()).hexdigest()
post={k:int(os.environ["POST_"+k]) for k in ("TOTAL","USED","AVAIL","IFREE")}
pre={k:int(os.environ["PRE_"+k]) for k in ("TOTAL","USED","AVAIL","IFREE")}
assert post["AVAIL"]>=p["required_after_cleanup_bytes"] and post["IFREE"]>=p["required_after_cleanup_inodes"]
r={"schema":"LOUKSNA_PART4_R2_V8_TEMP_CLEANUP/1.0","status":"PASS","scope":"TEMP_EXT4_PROYECTOS_PARTIAL_ONLY",
"source_failure_run":36682665542,"temp_device":os.environ["TMPDEV"],"temp_uuid":os.environ["TMP_UUID"],
"p3_preserved_ntfs":True,"p3_old_uuid":"F2848A148489DC0B","p3_reformatted":False,
"partial_allocated_bytes_before":int(os.environ["PARTIAL_BYTES"]),
"before":{"total_bytes":pre["TOTAL"],"used_bytes":pre["USED"],"available_bytes":pre["AVAIL"],"available_inodes":pre["IFREE"]},
"after":{"total_bytes":post["TOTAL"],"used_bytes":post["USED"],"available_bytes":post["AVAIL"],"available_inodes":post["IFREE"],"top_level":["lost+found"]},
"source_plan_sha256":h(plan_path),"pre_sfdisk_sha256":h(report_path.parent/"PARTITION_TABLE_PRECLEAN.sfdisk"),
"post_sfdisk_sha256":h(report_path.parent/"PARTITION_TABLE_POSTCLEAN.sfdisk"),
"temporary_unmounted":True,"source_rollback":"P3_SHRUNK_NTFS_SOURCE_OF_TRUTH",
"finished_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
report_path.write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
m={"schema":"LOUKSNA_R4_PART4_R2_MIGRATION_PLAN_V8/1.0","status":"PASS",
"stage":"P3_SHRUNK_TEMP_EXT4_CLEANED_V8_PRECOPY","source_failure_run":36682665542,
"source_partition":"/dev/nvme0n1p3","source_uuid":"F2848A148489DC0B",
"manifest_sha256":p["manifest_sha256"],"geometry":p["geometry"],"ntfs":{"fs_target_bytes":228137631744},
"temporary":p["temporary"],"preexisting_mounts":{"p3":os.environ["P3_MP"],"temp":""},
"script":"server/r4-master/part4_r2_storage_resume_after_v7_capacity_fail_closed_v8.sh",
"script_sha256":p["migration_script_sha256"],
"source_posix_fingerprint":p["source_posix_fingerprint"],
"source_verify_sha256":p["source_verify_sha256"],"source_xattr_sha256":p["source_xattr_sha256"],
"source_posix_sha256":p["source_posix_sha256"],
"cleanup_report_sha256":h(report_path),"cleanup_plan_sha256":h(plan_path),
"capacity":{"available_bytes":post["AVAIL"],"available_inodes":post["IFREE"],
"required_bytes":p["required_after_cleanup_bytes"],"required_inodes":p["required_after_cleanup_inodes"]},
"rollback_contract":{"before_p3_reformat":"SHRUNK_NTFS_P3_REMAINS_SOURCE_OF_TRUTH",
"after_temp_verify_before_p3_reformat":"SHRUNK_NTFS_P3_AND_VERIFIED_TEMP_EXT4",
"after_p3_reformat_until_final_verify":"VERIFIED_TEMP_EXT4_IS_RECOVERY_COPY",
"after_final_verify":"VERIFIED_EXT4_P3_IS_PROTECTED_SOURCE"},
"created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
migration_path.write_text(json.dumps(m,indent=2,sort_keys=True)+"\n")
print(json.dumps({"status":"PASS","before":r["before"],"after":r["after"],"p3_reformatted":False,"migration_plan_sha256":h(migration_path)},sort_keys=True))
PY
