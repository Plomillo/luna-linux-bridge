#!/usr/bin/env python3
"""Deterministic build of CUSTOSZV9.pyz preserving the tracked V8 baseline byte-for-byte."""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, sys, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

ROOT=Path(__file__).resolve().parent
BASELINE=ROOT/"CUSTOSZV8.pyz"
DIST=ROOT/"dist"
STAGE=ROOT/"build"/"custoszv9-stage"
EXPECTED_BASELINE_SIZE=99400
MIN_ZIP_EPOCH=315532800
FORMAL_NAMES=(
 "TaskAndStateModel.agda","ResourceBudgetModel.agda","PlanSoundness.agda",
 "ContractComposition.agda","EquivalenceTransport.agda","MigrationCoherence.agda",
 "RecoveryInvariant.agda","ModelImplementationCorrespondence.agda"
)
def digest_file(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for block in iter(lambda:f.read(1024*1024),b""):h.update(block)
 return h.hexdigest()
def resolve_source()->tuple[str,int]:
 commit=os.environ.get("CUSTOSZV9_SOURCE_COMMIT") or os.environ.get("GITHUB_SHA") or "UNBOUND_LOCAL_BUILD"
 if commit!="UNBOUND_LOCAL_BUILD":
  if not re.fullmatch(r"[0-9a-f]{40}",commit):raise SystemExit("SOURCE_COMMIT_SHA_INVALID")
  try:
   stamp=int(subprocess.run(["git","show","-s","--format=%ct",commit],cwd=ROOT,capture_output=True,text=True,timeout=10,check=True).stdout.strip())
   head=subprocess.run(["git","rev-parse","HEAD"],cwd=ROOT,capture_output=True,text=True,timeout=10,check=True).stdout.strip()
  except (OSError,ValueError,subprocess.SubprocessError):raise SystemExit("SOURCE_COMMIT_OR_TIMESTAMP_UNRESOLVED")
  if head!=commit:raise SystemExit("CHECKED_OUT_SOURCE_COMMIT_MISMATCH")
 else:stamp=MIN_ZIP_EPOCH
 return commit,max(MIN_ZIP_EPOCH,stamp)
def deterministic_zip(source:Path,target:Path,epoch:int)->None:
 dt=datetime.fromtimestamp(min(max(epoch,MIN_ZIP_EPOCH),4354819198),timezone.utc)
 if dt.year>2107:dt=dt.replace(year=2107,month=12,day=31,hour=23,minute=59,second=58)
 ztime=(dt.year,dt.month,dt.day,dt.hour,dt.minute,dt.second-(dt.second%2))
 target.parent.mkdir(parents=True,exist_ok=True)
 with target.open("wb") as raw:
  raw.write(b"#!/usr/bin/env python3\n")
  with zipfile.ZipFile(raw,"w",compression=zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True) as z:
   for p in sorted(x for x in source.rglob("*") if x.is_file()):
    if p.is_symlink():raise SystemExit("SYMLINK_IN_PACKAGE_SOURCE")
    name=p.relative_to(source).as_posix()
    if name.startswith("/") or ".." in PurePosixPath(name).parts:raise SystemExit("UNSAFE_PACKAGE_MEMBER")
    info=zipfile.ZipInfo(name,date_time=ztime);info.compress_type=zipfile.ZIP_DEFLATED
    info.create_system=3;info.external_attr=(0o100644<<16);info.flag_bits|=0x800
    z.writestr(info,p.read_bytes(),compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
def main()->int:
 if not BASELINE.is_file():raise SystemExit("PROTECTED_V8_BASELINE_MISSING")
 sha0=digest_file(BASELINE);size0=BASELINE.stat().st_size
 if size0!=EXPECTED_BASELINE_SIZE:raise SystemExit(f"V8_BASELINE_SIZE_MISMATCH:{size0}")
 commit,epoch=resolve_source()
 if STAGE.exists():shutil.rmtree(STAGE)
 STAGE.mkdir(parents=True)
 shutil.copytree(ROOT/"custoszv9",STAGE/"custoszv9",ignore=shutil.ignore_patterns("__pycache__","*.pyc"))
 data=STAGE/"custoszv9"/"data";data.mkdir(parents=True,exist_ok=True)
 embedded=data/"CUSTOSZV8.pyz";shutil.copyfile(BASELINE,embedded)
 members=[]
 try:
  with zipfile.ZipFile(BASELINE,"r") as z:
   names=z.namelist()
   if "custoszv8/core.py" not in names or "custoszv8/cli.py" not in names:
    raise SystemExit("V8_REQUIRED_PACKAGE_MEMBERS_MISSING")
   for name in sorted(names):
    if not name.startswith("custoszv8/") or name.endswith("/"):continue
    rel=PurePosixPath(name)
    if rel.is_absolute() or any(p in {"",".",".."} for p in rel.parts):raise SystemExit("UNSAFE_V8_ARCHIVE_MEMBER")
    target=STAGE.joinpath(*rel.parts);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_bytes(z.read(name));members.append(name)
 except (OSError,zipfile.BadZipFile,RuntimeError) as exc:raise SystemExit(f"V8_ARCHIVE_INSPECTION_FAILED:{type(exc).__name__}:{exc}")
 if not {"custoszv8/core.py","custoszv8/cli.py"}.issubset(set(members)):raise SystemExit("V8_COMPATIBILITY_LAYER_INCOMPLETE")
 # Formal proof sources remain repository/evidence inputs only. Do not copy them
 # into the operational ZIPAPP; the independent Agda/Cubical workflow checks them.
 formal_src=ROOT/"formal"/"crfu"
 formal_checks={}
 for name in FORMAL_NAMES:
  source=formal_src/name
  if not source.is_file():raise SystemExit("FORMAL_SOURCE_MISSING:"+name)
  formal_checks[name]={"sha256":digest_file(source),"size_bytes":source.stat().st_size,
                       "embedded_in_runtime":False,"repository_path":"formal/crfu/"+name}
 scope_path=data/"certification_scope.json"
 if not scope_path.is_file():raise SystemExit("CERTIFICATION_SCOPE_MISSING")
 scope_record=json.loads(scope_path.read_text(encoding="utf-8"))
 expected_scope="CUSTOSZV9_CRFU_STANDALONE_SOFTWARE_AND_EXACT_V8_BYTE_PRESERVATION"
 if scope_record.get("schema")!="CUSTOSZV9_STANDALONE_SOFTWARE_SCOPE/1.0" or scope_record.get("scope_id")!=expected_scope:
  raise SystemExit("CERTIFICATION_SCOPE_IDENTITY_INVALID")
 scope_evidence={"scope_id":scope_record["scope_id"],"source_path":"custoszv9/data/certification_scope.json",
                 "sha256":digest_file(scope_path),"byte_size":scope_path.stat().st_size,
                 "embedded_byte_exact":True}
 manifest={
  "schema":"CUSTOSZV9_BUILD_MANIFEST/1.0",
  "artifact_id":"CUSTOSZV9","artifact_filename":"CUSTOSZV9.pyz",
  "artifact_status":"PROPOSED_UNCERTIFIED_SUCCESSOR","source_commit":commit,
  "assurance_scope":scope_evidence,
  "baseline":{"filename":"CUSTOSZV8.pyz","sha256":sha0,"size_bytes":size0,
              "embedded_path":"custoszv9/data/CUSTOSZV8.pyz","embedded_bytes_match":True,
              "repository_blob_sha1":"d9689914a7dd908ebb5a17eeda071aecbd652ab5"},
  "v8_functional_layer":{"package_members_copied":len(members),"package_member_names":members,
                         "source":"exact tracked CUSTOSZV8.pyz archive members","second_runtime_started":False},
  "formal_assurance":{"sources":formal_checks,"sources_embedded":False,
                      "source_storage":"REPOSITORY_ONLY_SEPARATE_EVIDENCE_BUNDLE",
                      "producer_toolchain_executed":False,"toolchain_executed":False,
                      "proof_of_implementation":False,
                      "status":"SOURCE_HASHES_RECORDED_NOT_EMBEDDED_EXTERNAL_VALIDATION_REQUIRED",
                      "hott_univalence_status":"EXTERNAL_CUBICAL_SCOPE_NOT_PART_OF_RUNTIME_PACKAGE"},
  "governance":{"canonical_authority":"Louksna.md","protected_baseline":"LUNACORE_final_formalized_v25.md",
    "doctrine":"EXTEND_DO_NOT_REPLACE","canonical_gates":"G01-G24_NOT_GRANTED",
    "PUAC_C25_C32":"LOCAL_CONTROLS_NOT_CANONICALLY_ADMITTED","G23":"NOT_GRANTED","G24":"NOT_GRANTED",
    "canonical_promotion":"NOT_AUTHORIZED","activation_authorized":False},
  "build":{"epoch_source":"source_commit_timestamp_or_fixed_local_epoch","source_date_epoch":epoch,
           "deterministic_zip":True,"runtime_dependencies_added":[]}
 }
 (data/"build_manifest.json").write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 entry=STAGE/"__main__.py";entry.write_text("from custoszv9.cli import main\nraise SystemExit(main())\n",encoding="utf-8")
 target=DIST/"CUSTOSZV9.pyz"
 deterministic_zip(STAGE,target,epoch)
 with zipfile.ZipFile(target,"r") as z:
  if z.testzip() is not None:raise SystemExit("FINAL_ZIP_CRC_FAILURE")
  if "custoszv9/data/CUSTOSZV8.pyz" not in z.namelist():raise SystemExit("EMBEDDED_BASELINE_MISSING")
  embedded_bytes=z.read("custoszv9/data/CUSTOSZV8.pyz")
  if hashlib.sha256(embedded_bytes).hexdigest()!=sha0 or len(embedded_bytes)!=size0:raise SystemExit("EMBEDDED_BASELINE_BYTE_IDENTITY_FAILED")
  names=z.namelist()
  if "custoszv8/core.py" not in names or "custoszv9/crfu/coordinator.py" not in names:raise SystemExit("REQUIRED_FUNCTIONAL_MEMBER_MISSING")
  if any(name.endswith(".agda") or "/formal_sources/" in "/"+name or name.startswith("formal/") for name in names):
   raise SystemExit("FORMAL_PROOF_SOURCE_MUST_NOT_BE_EMBEDDED")
  if json.loads(z.read("custoszv9/data/build_manifest.json"))["formal_assurance"]["sources_embedded"] is not False:
   raise SystemExit("FORMAL_SOURCE_EMBEDDING_STATUS_INVALID")
 sha1=digest_file(BASELINE)
 if sha0!=sha1 or BASELINE.stat().st_size!=size0:raise SystemExit("PROTECTED_V8_BASELINE_CHANGED_DURING_BUILD")
 report={"schema":"CUSTOSZV9_BUILD_REPORT/1.0","status":"PASS_BUILD_ONLY_NOT_CERTIFIED",
  "artifact_path":"dist/CUSTOSZV9.pyz","source_commit":commit,
  "baseline_sha256":sha0,"baseline_size_bytes":size0,"baseline_unchanged":True,
  "embedded_baseline_byte_exact":True,"v8_package_members_copied":len(members),
  "package_sha256":digest_file(target),"package_size_bytes":target.stat().st_size,"zip_crc":"PASS",
  "formal_toolchain_status":"NOT_EXECUTED_IN_PACKAGE_BUILD;EXTERNAL_ASSURANCE_REQUIRED",
  "formal_sources_embedded":False,"formal_source_hashes_recorded":True,
  "G22":"NOT_GRANTED","G23":"NOT_GRANTED","G24":"NOT_GRANTED",
  "release_eligible":False,"certification":"NOT_GRANTED","canonical_promotion":"NOT_AUTHORIZED"}
 evidence=ROOT/"evidence";evidence.mkdir(parents=True,exist_ok=True)
 (evidence/"custoszv9-build-report.json").write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 print(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2))
 return 0
if __name__=="__main__":raise SystemExit(main())
