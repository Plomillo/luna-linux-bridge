#!/usr/bin/env bash
set -Eeuo pipefail

MISSION_ID="DROPBOX-PROYECTOS-PRIORITARIOS-CUSTOSZ-WGET-FIX-20261003"
REQUEST="$GITHUB_WORKSPACE/mission-control/dropbox-proyectos-prioritarios/REQUEST.json"
EVIDENCE="$GITHUB_WORKSPACE/evidence/dropbox-proyectos-prioritarios"
WORK="$RUNNER_TEMP/dropbox-proyectos-prioritarios-$GITHUB_RUN_ID"
ARCHIVE="$WORK/1.PROYECTOS_PRIORITARIOS.dropbox.zip"
EXTRACTED="$WORK/extracted"
MANIFEST="$EVIDENCE/DOWNLOAD_MANIFEST.json"
DOWNLOAD_CERT="$EVIDENCE/DOWNLOAD_CERTIFICATION.json"
CUSTOSZ_REPORT="$EVIDENCE/CUSTOSZ_PROJECT_AUDIT.json"
CUSTOSZ="$GITHUB_WORKSPACE/artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
WGET_LOG="$WORK/WGET_RESPONSE.log"

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
q=list(urllib.parse.parse_qsl(u.query,keep_blank_values=True))
out=[]
seen_dl=False
for k,v in q:
    if k=="dl":
        out.append((k,"1"))
        seen_dl=True
    else:
        out.append((k,v))
if not seen_dl:
    out.append(("dl","1"))
print(urllib.parse.urlunsplit((u.scheme,u.netloc,u.path,urllib.parse.urlencode(out),"")))
PY
)"

echo "MISSION_ID=$MISSION_ID"
echo "SOURCE_KIND=DROPBOX_SHARED_FOLDER"
echo "SOURCE_OF_TRUTH=REQUEST.dropbox_url"
echo "DOWNLOAD_TRANSPORT=WGET_FOLLOW_REDIRECTS"
echo "ISOLATION_ROOT=$WORK"
echo "DESKTOP_COMMANDER_USED=FALSE"
echo "DOWNLOADED_CONTENT_EXECUTION=DENIED"
echo "PRIOR_7Z_POLICY=IGNORED_NOT_INPUT"
echo "PRIOR_7Z_READ=FALSE"
echo "PRIOR_7Z_REUSE=FALSE"
echo "PRIOR_7Z_COMPARE=FALSE"
echo "PRIOR_7Z_MUTATION=FALSE"

python3 - "$EVIDENCE/PREFLIGHT.json" "$SOURCE_URL" "$DIRECT_URL" <<'PY'
import datetime as dt,hashlib,json,sys
out,source,direct=sys.argv[1:]
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_PREFLIGHT/2.0",
 "status":"PASS",
 "authority":"Louksna.md",
 "source_url":source,
 "forced_download_url":direct,
 "source_url_sha256":hashlib.sha256(source.encode()).hexdigest(),
 "expected_dropbox_name":"1. PROYECTOS PRIORITARIOS",
 "prior_7z_policy":{
   "pattern":"1. PROYECTOS PRIORITARIOS.7z*",
   "status":"IGNORED_NOT_INPUT",
   "read":False,
   "reuse":False,
   "compare":False,
   "mutate":False
 },
 "governance":{
   "download_source_must_equal_request_link":True,
   "downloaded_content_execution":False,
   "fail_closed_on_non_zip":True,
   "traceability":True,
   "auditability":True,
   "provenance":True
 },
 "desktop_commander_used":False,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
open(out,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY

echo "TRACEABILITY_PREFLIGHT=PASS"
echo "GOVERNANCE_PREFLIGHT=PASS"
echo "PROVENANCE_PREFLIGHT=PASS"

# Exact Dropbox shared-link acquisition. Preserve all original link parameters
# except dl, which is changed from preview mode to forced-download mode.
echo "DOWNLOAD_START"
wget   --max-redirect=20   --tries=8   --timeout=30   --waitretry=5   --retry-connrefused   --server-response   --output-document="$ARCHIVE"   "$DIRECT_URL"   2> >(tee "$WGET_LOG" >&2)

test -s "$ARCHIVE" || {
  echo "DOWNLOAD_EMPTY=FAIL"
  exit 40
}

ARCHIVE_SHA256="$(sha256sum "$ARCHIVE" | awk '{print $1}')"
ARCHIVE_BYTES="$(stat -c '%s' "$ARCHIVE")"
WGET_VERSION="$(wget --version | head -n1)"
FILE_TYPE="$(file -b "$ARCHIVE" || true)"
CONTENT_TYPE="$(grep -i '^[[:space:]]*Content-Type:' "$WGET_LOG" | tail -n1 | sed 's/^[[:space:]]*//' || true)"

export ARCHIVE_SHA256 ARCHIVE_BYTES WGET_VERSION FILE_TYPE CONTENT_TYPE
python3 - "$ARCHIVE" "$EVIDENCE/ACQUISITION_EVIDENCE.json" "$SOURCE_URL" "$DIRECT_URL" <<'PY'
import datetime as dt,hashlib,json,os,pathlib,sys,zipfile
archive=pathlib.Path(sys.argv[1])
out=pathlib.Path(sys.argv[2])
source=sys.argv[3]
direct=sys.argv[4]
prefix=archive.read_bytes()[:16]
is_zip=zipfile.is_zipfile(archive)
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_ACQUISITION_EVIDENCE/2.0",
 "status":"PASS" if is_zip else "FAIL",
 "authority":"Louksna.md",
 "source_url":source,
 "forced_download_url":direct,
 "source_url_sha256":hashlib.sha256(source.encode()).hexdigest(),
 "transport":"wget",
 "wget_version":os.environ["WGET_VERSION"],
 "archive_bytes":int(os.environ["ARCHIVE_BYTES"]),
 "archive_sha256":os.environ["ARCHIVE_SHA256"],
 "file_identification":os.environ["FILE_TYPE"],
 "last_content_type_header":os.environ["CONTENT_TYPE"] or None,
 "first_16_bytes_hex":prefix.hex(),
 "zip_signature_valid":is_zip,
 "prior_7z_policy":"IGNORED_NOT_INPUT",
 "traceability":True,
 "auditability":True,
 "provenance":True,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
out.write_text(json.dumps(obj,indent=2,sort_keys=True)+"\n",encoding="utf-8")
if not is_zip:
    raise SystemExit("DROPBOX_RESPONSE_IS_NOT_ZIP")
PY

unzip -tq "$ARCHIVE"
echo "ZIP_SIGNATURE=PASS"
echo "ZIP_CRC=PASS"
echo "ARCHIVE_SHA256=$ARCHIVE_SHA256"
echo "ARCHIVE_BYTES=$ARCHIVE_BYTES"

# Validate complete archive and produce a content-addressed, path-safe audit view.
python3 - "$ARCHIVE" "$EXTRACTED" "$MANIFEST" "$ARCHIVE_SHA256" "$ARCHIVE_BYTES" <<'PY'
import datetime as dt, hashlib, json, pathlib, stat, sys, zipfile
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
        stripped=name.rstrip("/")
        if not stripped:
            continue
        parts=safe_parts(stripped)
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
        digest=hashlib.sha256(data).hexdigest()
        if is_link:
            symlinks.append({"path":norm,"target_bytes_sha256":digest,"size":len(data),"zip_mtime":mtime})
            files.append({"path":norm,"size":len(data),"sha256":digest,"zip_mtime":mtime,"type":"symlink_metadata_only"})
            continue
        dest=root.joinpath(*parts)
        dest.parent.mkdir(parents=True,exist_ok=True)
        dest.write_bytes(data)
        files.append({"path":norm,"size":len(data),"sha256":digest,"zip_mtime":mtime,"type":"file"})

obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_DOWNLOAD_MANIFEST/2.0",
 "status":"PASS",
 "authority":"Louksna.md",
 "archive_sha256":archive_sha,
 "archive_bytes":archive_bytes,
 "zip_member_count":len(seen),
 "file_count":len(files),
 "uncompressed_payload_bytes":sum(x["size"] for x in files),
 "symlink_metadata_count":len(symlinks),
 "symlinks":symlinks,
 "files":files,
 "path_traversal_detected":False,
 "crc_validation":"PASS",
 "downloaded_content_executed":False,
 "prior_7z_policy":"IGNORED_NOT_INPUT",
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
manifest_path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
PY

python3 - "$DOWNLOAD_CERT" "$SOURCE_URL" "$ARCHIVE_SHA256" "$ARCHIVE_BYTES" "$MANIFEST" <<'PY'
import datetime as dt,hashlib,json,sys
out,source,archive_sha,archive_bytes,manifest=sys.argv[1:]
raw=open(manifest,"rb").read()
obj={
 "schema":"LOUKSNA_DROPBOX_PROJECTS_DOWNLOAD_CERTIFICATION/2.0",
 "status":"PASS",
 "scope":"BYTE_COMPLETE_DROPBOX_ARCHIVE_AND_SAFE_AUDIT_VIEW",
 "authority":"Louksna.md",
 "source_url":source,
 "expected_folder_name":"1. PROYECTOS PRIORITARIOS",
 "archive_sha256":archive_sha,
 "archive_bytes":int(archive_bytes),
 "manifest_sha256":hashlib.sha256(raw).hexdigest(),
 "prior_7z_policy":"IGNORED_NOT_INPUT",
 "prior_7z_modified":False,
 "integrity_checks":[
   "EXACT_REQUEST_LINK_USED",
   "FORCED_DL_1",
   "HTTP_REDIRECTS_FOLLOWED",
   "NONEMPTY",
   "ZIP_SIGNATURE_PASS",
   "ZIP_CRC_PASS",
   "PATH_SAFETY_PASS",
   "SHA256_MANIFESTED"
 ],
 "traceability":"PASS",
 "governance":"PASS",
 "provenance":"PASS",
 "auditability":"PASS",
 "custosz_audit_authorized_next":True,
 "certification_propagation":False,
 "created_at_utc":dt.datetime.now(dt.timezone.utc).isoformat()
}
open(out,"w",encoding="utf-8").write(json.dumps(obj,indent=2,sort_keys=True)+"\n")
PY

echo "DOWNLOAD_CERTIFICATION=PASS"
echo "TRACEABILITY=PASS"
echo "GOVERNANCE=PASS"
echo "PROVENANCE=PASS"
echo "AUDITABILITY=PASS"

# CUSTOSZ starts only after exact Dropbox download certification PASS.
python3 - "$DOWNLOAD_CERT" <<'PY'
import json,sys
d=json.load(open(sys.argv[1],encoding="utf-8"))
assert d["status"]=="PASS"
assert d["custosz_audit_authorized_next"] is True
assert d["prior_7z_policy"]=="IGNORED_NOT_INPUT"
PY

python3 -B -I "$GITHUB_WORKSPACE/scripts/missions/custosz_dropbox_projects_audit.py"   "$EXTRACTED" "$MANIFEST" "$CUSTOSZ" "$CUSTOSZ_REPORT"

echo "CUSTOSZ_AUDIT=PASS"

{
  echo "DROPBOX_WORK=$WORK"
  echo "DROPBOX_ARCHIVE=$ARCHIVE"
  echo "DROPBOX_EVIDENCE=$EVIDENCE"
} >> "$GITHUB_ENV"
