#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
MANIFEST="$1"
V8="$2"
OUT="$3"
test -n "$MANIFEST" && test -n "$V8" && test -n "$OUT"
mkdir -p "$OUT"
P3=/dev/nvme0n1p3
DISK=/dev/nvme0n1
ROOT="$HOME/PROYECTOS"
SELF="$(cd -- "$(dirname -- "$0")" && pwd -P)"
VERIFY="$SELF/part4_r2_verify_tree_ext4_v9.py"
POSIX="$SELF/part4_r2_posix_fingerprint_v9.py"
hold(){ printf 'HOLD:%s\n' "$*" >&2; exit 20; }
digest(){ sha256sum "$1" | awk '{print $1}'; }
for c in sudo python3 sha256sum findmnt blkid sfdisk chmod stat cmp lsblk; do
  command -v "$c" >/dev/null 2>&1 || hold "MISSING_TOOL:$c"
done
test "$(hostname)" = LOUKSNA || hold HOST_MISMATCH
test "$(id -un)" = diegoignacionorambuenamiranda || hold USER_MISMATCH
sudo -n true || hold SUDO_UNAVAILABLE
test "$(digest "$MANIFEST")" = 99346fd6032b548b8de0b9bf7d8a671d1ccd048dd6d2309cd82b754866916d0e || hold FROZEN_MANIFEST_MISMATCH
test -f "$V8/POSIX_SOURCE.json" || hold V8_POSIX_SOURCE_MISSING
test -f "$V8/VERIFY_P3_PREEXPAND.json" || hold V8_P3_PREEXPAND_EVIDENCE_MISSING
test -f "$V8/POSIX_P3_PREEXPAND.json" || hold V8_P3_POSIX_EVIDENCE_MISSING
test "$(readlink -f "$(findmnt -n -o SOURCE /)")" = /dev/nvme0n1p5 || hold CURRENT_ROOT_NOT_P5
test "$(findmnt -n -o FSTYPE /)" = ext4 || hold CURRENT_ROOT_FS_DRIFT
test "$(readlink -f "$(findmnt -M "$ROOT" -n -o SOURCE)")" = "$P3" || hold PROJECTS_MOUNT_NOT_P3
test "$(findmnt -M "$ROOT" -n -o FSTYPE)" = ext4 || hold PROJECTS_NOT_EXT4
test "$(findmnt -rn -R "$ROOT" -o TARGET | wc -l)" = 1 || hold NESTED_MOUNT_PRESENT
test "$(sudo -n blkid -p -s UUID -o value "$P3")" = e084ec2a-af39-48b5-bb89-db2dc6a98332 || hold P3_UUID_MISMATCH
test "$(sudo -n blkid -p -s TYPE -o value "$P3")" = ext4 || hold P3_TYPE_MISMATCH
test "$(sudo -n blkid -p -s LABEL -o value "$P3")" = LOUKSNA_PROJECTS || hold P3_LABEL_MISMATCH
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_BEFORE.sfdisk"
cp -- /etc/fstab "$OUT/fstab.before"
python3 - "$OUT/PARTITION_TABLE_BEFORE.sfdisk" "$V8" <<'PY'
import json,pathlib,re,sys
p=pathlib.Path(sys.argv[1]); v=pathlib.Path(sys.argv[2]); d={}
for line in p.read_text(errors="replace").splitlines():
    m=re.match(r"^/dev/nvme0n1p(\d+)\s*:\s*start=\s*(\d+),\s*size=\s*(\d+)",line)
    if m:d[int(m.group(1))]=(int(m.group(2)),int(m.group(3)))
exp={1:(2048,532480),2:(534528,32768),3:(567296,853842233),
     4:(998832128,1368064),5:(854411576,144420552)}
assert d==exp,(d,exp)
for f in ("VERIFY_P3_PREEXPAND.json","POSIX_P3_PREEXPAND.json","POSIX_SOURCE.json"):
    q=json.loads((v/f).read_text())
    assert q.get("status")=="PASS",(f,q.get("status"))
a=json.loads((v/"VERIFY_P3_PREEXPAND.json").read_text())
b=json.loads((v/"POSIX_P3_PREEXPAND.json").read_text())
s=json.loads((v/"POSIX_SOURCE.json").read_text())
assert a["seen_records"]==498092 and a["regular_file_bytes"]==200490852057 and a["mismatch_count"]==0
assert b["matches_expected"] is True and b["fingerprint_sha256"]==s["fingerprint_sha256"]
assert s["fingerprint_sha256"]=="fa50cabb73c9fdb450af4fb3450959672418bd76015239a722d040c1c5603401"
PY
sudo -n python3 "$VERIFY" --root "$ROOT" --manifest "$MANIFEST" --out "$OUT/TREE_V9.json" --allow-root-empty-ext4-lostfound
sudo -n python3 "$POSIX" --root "$ROOT" --out "$OUT/POSIX_V9.json" --allow-root-empty-ext4-lostfound --expect "$V8/POSIX_SOURCE.json"
sudo -n chmod 0644 "$OUT/TREE_V9.json" "$OUT/POSIX_V9.json"
sudo -n sfdisk --dump "$DISK" > "$OUT/PARTITION_TABLE_AFTER.sfdisk"
cmp -s "$OUT/PARTITION_TABLE_BEFORE.sfdisk" "$OUT/PARTITION_TABLE_AFTER.sfdisk" || hold PARTITION_TABLE_CHANGED_DURING_PROBE
test "$(sudo -n blkid -p -s UUID -o value "$P3")" = e084ec2a-af39-48b5-bb89-db2dc6a98332 || hold P3_CHANGED_DURING_PROBE
test "$(digest /etc/fstab)" = "$(digest "$OUT/fstab.before")" || hold FSTAB_CHANGED_DURING_PROBE
test "$(readlink -f "$(findmnt -M "$ROOT" -n -o SOURCE)")" = "$P3" || hold MOUNT_CHANGED_DURING_PROBE
python3 - "$OUT" "$MANIFEST" "$VERIFY" "$POSIX" "$V8" <<'PY'
import datetime as dt,hashlib,json,pathlib,sys
out,man,ver,pos,v8=map(pathlib.Path,sys.argv[1:6])
d=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
t=json.loads((out/"TREE_V9.json").read_text())
p=json.loads((out/"POSIX_V9.json").read_text())
s=json.loads((v8/"POSIX_SOURCE.json").read_text())
assert t["status"]=="PASS" and t["mismatch_count"]==0
assert t["seen_records"]==498092 and t["regular_file_bytes"]==200490852057
assert p["status"]=="PASS" and p["matches_expected"] is True
assert p["fingerprint_sha256"]==s["fingerprint_sha256"]
for x in (t["root_technical_exclusion"],p["root_technical_exclusion"]):
    assert x["path"]=="lost+found"
r={"schema":"LOUKSNA_R4_PART4_R2_POSTBOUNDARY_V9_PROBE/1.0",
   "status":"PASS","source_run":36687767779,"boundary":"P3_ALREADY_EXT4_EXPANDED",
   "root_partition":"/dev/nvme0n1p5","projects_partition":"/dev/nvme0n1p3",
   "projects_uuid":"e084ec2a-af39-48b5-bb89-db2dc6a98332",
   "technical_exclusion":"ONLY_EMPTY_ROOT_EXT4_LOSTFOUND",
   "expected_records":498092,"expected_regular_file_bytes":200490852057,
   "source_posix_fingerprint":s["fingerprint_sha256"],
   "manifest_sha256":d(man),"v8_source_posix_sha256":d(v8/"POSIX_SOURCE.json"),
   "v8_p3_preexpand_sha256":d(v8/"VERIFY_P3_PREEXPAND.json"),
   "tree_sha256":d(out/"TREE_V9.json"),"posix_sha256":d(out/"POSIX_V9.json"),
   "partition_sha256":d(out/"PARTITION_TABLE_BEFORE.sfdisk"),
   "fstab_before_sha256":d(out/"fstab.before"),
   "verifier_sha256":d(ver),"posix_verifier_sha256":d(pos),
   "irreversible_mutation_authorized":False,"p2_p4_retirement_authorized":False,
   "checked_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()}
(out/"PROBE_V9.json").write_text(json.dumps(r,indent=2,sort_keys=True)+"\n")
print(json.dumps(r,indent=2,sort_keys=True))
PY
sha256sum "$OUT"/* > "$OUT/PROBE_EVIDENCE.sha256"
