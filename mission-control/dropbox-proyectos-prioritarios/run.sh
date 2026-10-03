#!/usr/bin/env bash
set -Eeuo pipefail

MISSION_ID="DROPBOX-PROYECTOS-PRIORITARIOS-CUSTOSZ-20261003"
REQUEST="$GITHUB_WORKSPACE/mission-control/dropbox-proyectos-prioritarios/REQUEST.json"
EVIDENCE="$GITHUB_WORKSPACE/evidence/dropbox-proyectos-prioritarios"
WORK="$RUNNER_TEMP/dropbox-proyectos-prioritarios-$GITHUB_RUN_ID"
ARCHIVE="$WORK/1.PROYECTOS_PRIORITARIOS.dropbox.zip"
EXTRACTED="$WORK/extracted"
MANIFEST="$EVIDENCE/DOWNLOAD_MANIFEST.json"
DOWNLOAD_CERT="$EVIDENCE/DOWNLOAD_CERTIFICATION.json"
CUSTOSZ_REPORT="$EVIDENCE/CUSTOSZ_PROJECT_AUDIT.json"
CUSTOSZ="$GITHUB_WORKSPACE/artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"

mkdir -p "$WORK" "$EXTRACTED" "$EVIDENCE"

SOURCE_URL="$(python3 - "$REQUEST" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
print(d["dropbox_url"])
PY
)"

DIRECT_URL="$(python3 - "$SOURCE_URL" <<'PY'
import sys,urllib.parse
u=urllib.parse.urlsplit(sys.argv[1])
q=dict(urllib.parse.parse_qsl(u.query,keep_blank_values=True))
q["dl"]="1"
q.pop("st",None)
print(urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,urllib.parse.urlencode(q),"")))
PY
)"

echo "MISSION_ID=$MISSION_ID"
echo "SOURCE_KIND=DROPBOX_SHARED_FOLDER"
echo "ISOLATION_ROOT=$WORK"
echo "DESKTOP_COMMANDER_USED=FALSE"
echo "DOWNLOADED_CONTENT_EXECUTION=DENIED"

# Collision guard against the previous download already present on main.
git fetch origin main --depth=1
PRIOR_PATH="1. PROYECTOS PRIORITARIOS.7z.001"
PRIOR_EXISTS=false
PRIOR_BLOB=""
PRIOR_SHA256=""
if git cat-file -e "origin/main:$PRIOR_PATH" 2>/dev/null; then
  PRIOR_EXISTS=true
  PRIOR_BLOB="$(git rev-parse "origin/main:$PRIOR_PATH")"
  git show "origin/main:$PRIOR_PATH" > "$WORK/prior-main-fragment.bin"
  PRIOR_SHA256="$(sha256sum "$WORK/prior-main-fragment.bin" | awk '{print $1}')"
  rm -f "$WORK/prior-main-fragment.bin"
fi

python3 - "$EVIDENCE/PREFLIGHT.json" "$SOURCE_URL" "$PRIOR_EXISTS" "$PRIOR_BLOB" "$PRIOR_SHA256" <<'PY'
import json,sys,datetime as dt
out,source,exists,blob,digest=sys.argv[1:]
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_PREFLIGHT/1.0",
 "status":"PASS",
 "authority":"Louksna.md",
 "source_url":source,
 "expected_dropbox_name":"1. PROYECTOS PRIORITARIOS",
 "prior_download_on_main":{
   "path":"1. PROYECTOS PRIORITARIOS.7z.001",
   "exists":exists.lower()=="true",
   "git_blob_sha":blob or None,
   "sha256":digest or None
 },
 "collision_policy":{
   "reuse_prior_fragment":False,
   "overwrite_prior_fragment":False,
   "download_root_isolated_by_github_run_id":True
 },
 "desktop_commander_used":False,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
open(out,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY

# Governed, resumable HTTP acquisition from the exact public Dropbox folder.
echo "DOWNLOAD_START"
curl --fail --location   --retry 8 --retry-delay 5 --retry-all-errors   --connect-timeout 30   --continue-at -   --dump-header "$WORK/HTTP_HEADERS.txt"   --output "$ARCHIVE"   "$DIRECT_URL"

test -s "$ARCHIVE"
ARCHIVE_SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
ARCHIVE_BYTES="$(stat -c '%s' "$ARCHIVE")"

# Validate the complete archive and produce a content-addressed, path-safe audit view.
python3 - "$ARCHIVE" "$EXTRACTED" "$MANIFEST" "$ARCHIVE_SHA256" "$ARCHIVE_BYTES" <<'PY'
import datetime as dt, hashlib, json, os, pathlib, shutil, stat, sys, zipfile
archive=pathlib.Path(sys.argv[1])
root=pathlib.Path(sys.argv[2])
manifest_path=pathlib.Path(sys.argv[3])
archive_sha=sys.argv[4]
archive_bytes=int(sys.argv[5])

def safe_parts(name):
    p=pathlib.PurePosixPath(name)
    if p.is_absolute() or any(x in ("","..") for x in p.parts):
        raise SystemExit("ZIP_PATH_TRAVERSAL_OR_INVALID:"+name)
    return p.parts

def hbytes(b):
    return hashlib.sha256(b).hexdigest()

files=[]
seen=set()
symlinks=[]
with zipfile.ZipFile(archive) as z:
    bad=z.testzip()
    if bad is not None:
        raise SystemExit("ZIP_CRC_FAILURE:"+bad)
    infos=z.infolist()
    if not infos:
        raise SystemExit("ZIP_EMPTY")
    for info in infos:
        name=info.filename.replace("\\","/")
        parts=safe_parts(name.rstrip("/"))
        norm="/".join(parts)
        if norm in seen:
            raise SystemExit("ZIP_DUPLICATE_MEMBER:"+norm)
        seen.add(norm)
        mode=(info.external_attr >> 16) & 0xFFFF
        is_link=stat.S_ISLNK(mode)
        mtime="%04d-%02d-%02dT%02d:%02d:%02d" % info.date_time
        if info.is_dir():
            (root.joinpath(*parts)).mkdir(parents=True,exist_ok=True)
            continue
        data=z.read(info)
        digest=hbytes(data)
        if is_link:
            symlinks.append({"path":norm,"target_bytes_sha256":digest,"size":len(data),"zip_mtime":mtime})
            files.append({"path":norm,"size":len(data),"sha256":digest,"zip_mtime":mtime,"type":"symlink_metadata_only"})
            continue
        dest=root.joinpath(*parts)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
        files.append({"path":norm,"size":len(data),"sha256":digest,"zip_mtime":mtime,"type":"file"})

total=sum(x["size"] for x in files)
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_DOWNLOAD_MANIFEST/1.0",
 "status":"PASS",
 "authority":"Louksna.md",
 "archive_sha256":archive_sha,
 "archive_bytes":archive_bytes,
 "zip_member_count":len(seen),
 "file_count":len(files),
 "uncompressed_payload_bytes":total,
 "symlink_metadata_count":len(symlinks),
 "symlinks":symlinks,
 "files":files,
 "path_traversal_detected":False,
 "crc_validation":"PASS",
 "downloaded_content_executed":False,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
manifest_path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY

python3 - "$DOWNLOAD_CERT" "$SOURCE_URL" "$ARCHIVE_SHA256" "$ARCHIVE_BYTES" "$MANIFEST" <<'PY'
import datetime as dt,hashlib,json,sys
out,source,archive_sha,archive_bytes,manifest=sys.argv[1:]
raw=open(manifest,"rb").read()
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_DOWNLOAD_CERTIFICATION/1.0",
 "status":"PASS",
 "scope":"BYTE_COMPLETE_DROPBOX_ARCHIVE_AND_SAFE_AUDIT_VIEW",
 "authority":"Louksna.md",
 "source_url":source,
 "expected_folder_name":"1. PROYECTOS PRIORITARIOS",
 "archive_sha256":archive_sha,
 "archive_bytes":int(archive_bytes),
 "manifest_sha256":hashlib.sha256(raw).hexdigest(),
 "collision_with_prior_main_download":False,
 "prior_main_fragment_modified":False,
 "integrity_checks":["HTTP_COMPLETED","NONEMPTY","ZIP_CRC_PASS","PATH_SAFETY_PASS","SHA256_MANIFESTED"],
 "custosz_audit_authorized_next":True,
 "certification_propagation":False,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
open(out,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY

echo "DOWNLOAD_CERTIFICATION=PASS"
echo "ARCHIVE_SHA256=$ARCHIVE_SHA256"
echo "ARCHIVE_BYTES=$ARCHIVE_BYTES"

# CUSTOSZ audit starts only after download certification exists and says PASS.
python3 - "$DOWNLOAD_CERT" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
assert d["status"]=="PASS"
assert d["custosz_audit_authorized_next"] is True
PY

python3 -B -I "$GITHUB_WORKSPACE/scripts/missions/custosz_dropbox_projects_audit.py"   "$EXTRACTED" "$MANIFEST" "$CUSTOSZ" "$CUSTOSZ_REPORT"

echo "CUSTOSZ_AUDIT=PASS"

# Export durable paths for later workflow steps.
{
  echo "DROPBOX_WORK=$WORK"
  echo "DROPBOX_ARCHIVE=$ARCHIVE"
  echo "DROPBOX_EVIDENCE=$EVIDENCE"
} >> "$GITHUB_ENV"
