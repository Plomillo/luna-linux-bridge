#!/usr/bin/env python3
"""Reproducible Cajita materialization and Louksna1 candidate factory."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, stat, subprocess, sys, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath

from cajita_architecture_binding import register_architecture_binding

SCHEMA = "CAJITA_LOUKSNA1_FACTORY/1.0"
RAW_CAP = 1_500_000_000
RUNTIME_ARCHIVE_CAP = 470_000_000
COMBINED_CAP = 479_000_000
MATERIALIZATION_SOURCE_COMMIT = "f2771dd76c2c99967bbf1f7b032f8e6d15b0e387"
ARCHIVE_SUFFIXES = {".zip", ".7z"}
WEIGHT_PATHS = (
 "1. Cerebro/model.safetensors",
 "3. Transcripción/model.safetensors",
 "4. Traductor Inteligente/Traducción general/model.safetensors",
 "5. Inteligencia documental/INTELDOC_GLOBAL_30MB_CANDIDATE_V9/docling/compact_upstream_hf_candidate/quantized_weights.bin",
 "6. Sistema Inteligente/Análisis Avanzado/model.safetensors",
 "6. Sistema Inteligente/Anti-Alucinaciones/model.onnx",
)

def utc():
 return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00","Z")

def canon(obj):
 return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def sha_bytes(data):
 return hashlib.sha256(data).hexdigest()

def sha_file(path):
 h=hashlib.sha256()
 with Path(path).open("rb") as f:
  for block in iter(lambda:f.read(4*1024*1024),b""): h.update(block)
 return h.hexdigest()

def safe_rel(value):
 value=value.replace("\\","/")
 p=PurePosixPath(value)
 if not value or value.startswith("/") or re.match(r"^[A-Za-z]:",value):
  raise RuntimeError("ARCHIVE_ABSOLUTE_PATH_REJECTED:"+value[:160])
 if any(part in {"..",""} for part in p.parts) or p.as_posix() in {"",".",".."}:
  raise RuntimeError("ARCHIVE_PATH_TRAVERSAL_REJECTED:"+value[:160])
 return p

def check_tree(root):
 root=root.resolve()
 for base,dirs,files in os.walk(root,followlinks=False):
  for name in dirs+files:
   p=Path(base)/name
   if p.is_symlink() or not p.resolve().is_relative_to(root):
    raise RuntimeError("SYMLINK_OR_PATH_ESCAPE:"+str(p))
   if p.is_file() and not stat.S_ISREG(p.stat().st_mode):
    raise RuntimeError("NON_REGULAR_FILE:"+str(p))

def tree_rows(root, exclude_descriptor=True):
 rows=[]
 for base,dirs,files in os.walk(root,topdown=True,followlinks=False):
  bp=Path(base)
  dirs[:]=sorted(d for d in dirs if not (bp/d).is_symlink())
  for name in sorted(files):
   p=bp/name
   if p.is_symlink() or not p.is_file(): raise RuntimeError("NON_REGULAR_TREE_ENTRY:"+str(p))
   if exclude_descriptor and name=="CAJITA_MODULE.json": continue
   rows.append({"path":p.relative_to(root).as_posix(),"bytes":p.stat().st_size,"sha256":sha_file(p)})
 return sorted(rows,key=lambda x:x["path"].encode())

def tree_hash(root):
 return sha_bytes(canon(tree_rows(root,True)))

def merge_tree(src,dest):
 check_tree(src)
 dest.mkdir(parents=True,exist_ok=True)
 for base,dirs,files in os.walk(src,topdown=True,followlinks=False):
  rel=Path(base).relative_to(src); target=dest/rel
  target.mkdir(parents=True,exist_ok=True)
  for d in dirs: (target/d).mkdir(parents=True,exist_ok=True)
  for name in files:
   s=Path(base)/name; t=target/name
   if t.exists():
    if not t.is_file() or t.is_symlink() or s.stat().st_size!=t.stat().st_size or sha_file(s)!=sha_file(t):
     raise RuntimeError("DESTINATION_CONTENT_COLLISION:"+str(t))
   else: shutil.copy2(s,t)

def validate_7z(archive):
 p=subprocess.run(["7z","l","-slt",str(archive)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=120)
 if p.returncode: raise RuntimeError("7Z_LIST_FAILED:"+p.stdout[-300:])
 paths=[line[7:] for line in p.stdout.splitlines() if line.startswith("Path = ")]
 for name in paths[1:]: safe_rel(name)

def extract(archive,dest,tmp_parent):
 tmp=Path(tempfile.mkdtemp(prefix="cajita-extract-",dir=tmp_parent))
 try:
  if archive.suffix.lower()==".zip":
   with zipfile.ZipFile(archive) as z:
    bad=z.testzip()
    if bad: raise RuntimeError("ZIP_CRC_FAILURE:"+bad)
    names=[i.filename for i in z.infolist()]
    if len(names)!=len(set(names)): raise RuntimeError("ZIP_DUPLICATE_MEMBER")
    for info in z.infolist():
     if not info.filename.rstrip("/"): continue
     rel=safe_rel(info.filename.rstrip("/"))
     mode=(info.external_attr>>16)&0xFFFF
     if stat.S_ISLNK(mode): raise RuntimeError("ZIP_SYMLINK_REJECTED:"+info.filename)
     out=tmp.joinpath(*rel.parts)
     if not out.resolve().is_relative_to(tmp.resolve()): raise RuntimeError("ZIP_PATH_ESCAPE")
     if info.is_dir(): out.mkdir(parents=True,exist_ok=True)
     else:
      out.parent.mkdir(parents=True,exist_ok=True)
      with z.open(info) as src,out.open("wb") as dst: shutil.copyfileobj(src,dst,1024*1024)
      os.chmod(out,0o755 if mode&0o111 else 0o644)
  elif archive.suffix.lower()==".7z":
   validate_7z(archive)
   test=subprocess.run(["7z","t","-bd",str(archive)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=600)
   if test.returncode: raise RuntimeError("7Z_TEST_FAILED:"+test.stdout[-300:])
   run=subprocess.run(["7z","x","-y","-bd","-o"+str(tmp),str(archive)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=900)
   if run.returncode: raise RuntimeError("7Z_EXTRACTION_FAILED:"+run.stdout[-500:])
  else: raise RuntimeError("UNSUPPORTED_ARCHIVE_SUFFIX")
  check_tree(tmp)
  if not tree_rows(tmp,False): raise RuntimeError("EMPTY_ARCHIVE:"+str(archive))
  merge_tree(tmp,dest)
 finally: shutil.rmtree(tmp,ignore_errors=True)

def measure(root,exclude_manifest=True):
 total=0; count=0
 for p in root.rglob("*"):
  if p.is_symlink(): raise RuntimeError("SYMLINK_IN_RUNTIME:"+str(p))
  if p.is_file() and not (exclude_manifest and p.name=="MACRODOWN_MANIFEST.json"):
   total+=p.stat().st_size; count+=1
 return count,total

def verify_weights(runtime,manifest):
 out=[]
 for w in manifest.get("artifacts",[]):
  p=runtime/w["path"]
  if not p.is_file() or p.is_symlink() or p.stat().st_size!=int(w["bytes"]) or sha_file(p)!=w["sha256"]:
   raise RuntimeError("WEIGHT_HASH_OR_SIZE_MISMATCH:"+w["path"])
  out.append({"id":w["id"],"path":w["path"],"bytes":p.stat().st_size,"sha256":sha_file(p),"status":"PASS"})
 if len(out)!=6: raise RuntimeError("WEIGHT_COUNT_NOT_SIX")
 return out


EXTERNALIZED_CONTAINER_IDS = frozenset({
 "APACHE_JENA_6_2_0",
 "PLAYWRIGHT_1_63_0_SOURCE",
 "ONNX_RUNTIME_1_29_0_CP311",
 "DAGGER_0_21_8_LINUX_AMD64",
 "OPA_STATIC_LINUX_AMD64_CANDIDATE",
 "RQLITE_10_2_7_LINUX_AMD64",
 "SQLITE_SOURCE_3_53_4",
 "CMAKE_4_4_3_WINDOWS_X64_OFFICIAL_BASE",
 "AVALONIA_12_1_1_NUGET",
 "TAURI_2_11_5_SOURCE_ZIP",
})


def externalized_container_contract(runtime):
 runtime=Path(runtime).resolve()
 placement_path=runtime/"EXTERNALIZED_ASSET_PLACEMENT.json"
 if placement_path.is_symlink() or not placement_path.is_file():
  raise RuntimeError("EXTERNALIZED_CONTAINER_PLACEMENT_MISSING")
 placement=json.loads(placement_path.read_text(encoding="utf-8"))
 assets=placement.get("assets")
 if not isinstance(assets,list) or len(assets)!=len(EXTERNALIZED_CONTAINER_IDS):
  raise RuntimeError("EXTERNALIZED_CONTAINER_REGISTRY_COUNT_INVALID")
 result={}
 seen_ids=set()
 prefix="cajita-luna-runtime/"
 for asset in assets:
  if not isinstance(asset,dict):
   raise RuntimeError("EXTERNALIZED_CONTAINER_REGISTRY_ROW_INVALID")
  asset_id=asset.get("id")
  meta=asset.get("compact_runtime_container")
  if not isinstance(asset_id,str) or asset_id in seen_ids or not isinstance(meta,dict):
   raise RuntimeError("EXTERNALIZED_CONTAINER_REGISTRY_ID_COLLISION_OR_METADATA_MISSING")
  seen_ids.add(asset_id)
  archive_path=meta.get("path")
  if not isinstance(archive_path,str) or not archive_path.startswith(prefix):
   raise RuntimeError("EXTERNALIZED_CONTAINER_PATH_PREFIX_INVALID:"+str(asset_id))
  rel=safe_rel(archive_path[len(prefix):]).as_posix()
  if Path(rel).suffix.lower()!=".7z" or asset.get("placed_path")!=archive_path:
   raise RuntimeError("EXTERNALIZED_CONTAINER_PATH_BINDING_INVALID:"+str(asset_id))
  size=meta.get("size_bytes")
  digest=meta.get("sha256")
  if isinstance(size,bool) or not isinstance(size,int) or size<=0:
   raise RuntimeError("EXTERNALIZED_CONTAINER_SIZE_INVALID:"+str(asset_id))
  if not isinstance(digest,str) or len(digest)!=64 or any(c not in "0123456789abcdef" for c in digest):
   raise RuntimeError("EXTERNALIZED_CONTAINER_SHA256_INVALID:"+str(asset_id))
  if rel in result:
   raise RuntimeError("EXTERNALIZED_CONTAINER_PATH_COLLISION:"+rel)
  result[rel]={"id":asset_id,"bytes":size,"sha256":digest}
 if seen_ids!=EXTERNALIZED_CONTAINER_IDS:
  raise RuntimeError("EXTERNALIZED_CONTAINER_CANONICAL_ID_SET_MISMATCH")
 return dict(sorted(result.items(),key=lambda item:item[0].encode("utf-8")))


def validate_packaged_archive_member_set(names, externalized_contract):
 actual={name for name in names if Path(name).suffix.lower() in ARCHIVE_SUFFIXES}
 expected=set(externalized_contract)
 if actual!=expected:
  raise RuntimeError("EXTERNALIZED_ARCHIVE_MEMBER_SET_MISMATCH:"+json.dumps({
   "missing_registered":sorted(expected-actual),
   "unexpected_archives":sorted(actual-expected),
  },ensure_ascii=False,separators=(",",":")))
 return sorted(actual,key=lambda name:name.encode("utf-8"))


def load_registered_materialized_modules(runtime, registry):
 if registry.get("schema")!="CAJITA_MODULE_REGISTRY/1.0":
  raise RuntimeError("MATERIALIZED_MODULE_REGISTRY_SCHEMA_MISMATCH")
 entries=registry.get("modules")
 if not isinstance(entries,list) or not entries:
  raise RuntimeError("MATERIALIZED_MODULE_REGISTRY_EMPTY_WITH_NO_ARCHIVES")
 declared=registry.get("materialized_module_count")
 if isinstance(declared,bool) or declared!=len(entries):
  raise RuntimeError("MATERIALIZED_MODULE_REGISTRY_COUNT_MISMATCH")
 out=[]; seen=set()
 for row in entries:
  if not isinstance(row,dict): raise RuntimeError("MATERIALIZED_MODULE_REGISTRY_ROW_INVALID")
  key=row.get("module_key")
  if not isinstance(key,str) or key in seen: raise RuntimeError("MATERIALIZED_MODULE_KEY_DUPLICATE_OR_INVALID")
  seen.add(key)
  relative=safe_rel(key)
  folder=runtime.joinpath(*relative.parts)
  descriptor=folder/"CAJITA_MODULE.json"
  expected_manifest=(relative/"CAJITA_MODULE.json").as_posix()
  if row.get("manifest")!=expected_manifest: raise RuntimeError("MATERIALIZED_MODULE_MANIFEST_PATH_MISMATCH:"+key)
  if folder.is_symlink() or not folder.is_dir() or descriptor.is_symlink() or not descriptor.is_file():
   raise RuntimeError("MATERIALIZED_MODULE_DESCRIPTOR_MISSING:"+key)
  check_tree(folder)
  descriptor_bytes=descriptor.read_bytes()
  descriptor_sha=sha_bytes(descriptor_bytes)
  if descriptor_sha!=row.get("manifest_sha256"): raise RuntimeError("MATERIALIZED_MODULE_DESCRIPTOR_HASH_MISMATCH:"+key)
  data=json.loads(descriptor_bytes.decode("utf-8"))
  if data.get("schema")!="CAJITA_MATERIALIZED_MODULE/1.0" or data.get("module_key")!=key:
   raise RuntimeError("MATERIALIZED_MODULE_DESCRIPTOR_IDENTITY_MISMATCH:"+key)
  if data.get("canonical_asset_id")!=row.get("canonical_asset_id"):
   raise RuntimeError("MATERIALIZED_MODULE_ASSET_ID_MISMATCH:"+key)
  materialization=data.get("materialization",{})
  rows_now=tree_rows(folder,True)
  actual_tree=sha_bytes(canon(rows_now))
  actual_bytes=sum(x["bytes"] for x in rows_now)
  mismatch=(materialization.get("status")!="PASS"
      or materialization.get("file_count")!=len(rows_now)
      or materialization.get("bytes")!=actual_bytes
      or materialization.get("tree_sha256")!=actual_tree
      or row.get("tree_sha256")!=actual_tree
      or row.get("file_count")!=len(rows_now)
      or row.get("bytes")!=actual_bytes)
  if mismatch:
   details={"descriptor_file_count":materialization.get("file_count"),"actual_file_count":len(rows_now),
    "registry_file_count":row.get("file_count"),"descriptor_bytes":materialization.get("bytes"),
    "actual_bytes":actual_bytes,"registry_bytes":row.get("bytes"),
    "descriptor_tree_sha256":materialization.get("tree_sha256"),"registry_tree_sha256":row.get("tree_sha256"),
    "actual_tree_sha256":actual_tree,"materialization_status":materialization.get("status")}
   raise RuntimeError("MATERIALIZED_MODULE_TREE_INTEGRITY_MISMATCH:"+key+":"+json.dumps(details,sort_keys=True,separators=(",",":")))
  out.append({**data,"module_manifest_path":expected_manifest,"module_manifest_sha256":descriptor_sha})
 return sorted(out,key=lambda item:item["module_key"].encode("utf-8"))


def restore_materialized_modules_from_source_archives(runtime, repo_root, prior_reconciliation):
 runtime=Path(runtime).resolve(); repo_root=Path(repo_root).resolve()
 history=prior_reconciliation.get("archives",[])
 if not isinstance(history,list) or not history:
  raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_HISTORY_MISSING")
 source_archives=[]
 for row in history:
  if not isinstance(row,dict) or not isinstance(row.get("source_path"),str):
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_HISTORY_ROW_INVALID")
  rel=safe_rel(row["source_path"])
  repo_rel=(PurePosixPath("cajita-luna-runtime")/rel).as_posix()
  refspec=MATERIALIZATION_SOURCE_COMMIT+":"+repo_rel
  exists=subprocess.run(["git","-C",str(repo_root),"cat-file","-e",refspec],
   stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,check=False)
  if exists.returncode!=0:
   continue
  proc=subprocess.run(["git","-C",str(repo_root),"show",refspec],stdout=subprocess.PIPE,
   stderr=subprocess.PIPE,check=False,timeout=1200)
  if proc.returncode:
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_GIT_SHOW_FAILED:"+rel.as_posix()+":"+proc.stderr.decode("utf-8",errors="replace")[-240:])
  payload=proc.stdout
  actual_sha=sha_bytes(payload); actual_bytes=len(payload)
  if actual_sha!=row.get("source_sha256") or actual_bytes!=int(row.get("source_bytes",-1)):
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_IDENTITY_MISMATCH:"+rel.as_posix())
  source_archives.append((rel,payload,actual_sha,actual_bytes))
 if not source_archives:
  raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVES_UNRECOVERABLE_FROM_PINNED_COMMIT")
 # Reset only paths that the historical evidence identifies as extracted modules.
 # Ancestor paths are deleted before nested paths, so one removal is sufficient.
 expanded=[]
 for row in history:
  rel=safe_rel(row.get("expanded_path",""))
  if not rel.parts or rel.as_posix() in {".",".."}:
   raise RuntimeError("MATERIALIZED_EXPANDED_PATH_INVALID")
  folder=runtime.joinpath(*rel.parts)
  if folder.resolve().is_relative_to(runtime) is False:
   raise RuntimeError("MATERIALIZED_EXPANDED_PATH_ESCAPE")
  expanded.append((len(rel.parts),rel.as_posix(),folder))
 removed=[]
 for depth,rel,folder in sorted(expanded,key=lambda x:(x[0],x[1].encode("utf-8"))):
  if folder.is_symlink():
   raise RuntimeError("MATERIALIZED_EXPANDED_PATH_SYMLINK:"+rel)
  if not folder.exists():
   continue
  if not folder.is_dir():
   raise RuntimeError("MATERIALIZED_EXPANDED_PATH_NOT_DIRECTORY:"+rel)
  shutil.rmtree(folder)
  removed.append(rel)
 restored=[]
 for rel,payload,digest,size in source_archives:
  target=runtime.joinpath(*rel.parts)
  if not target.resolve().is_relative_to(runtime) or target.is_symlink():
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_PATH_ESCAPE:"+rel.as_posix())
  if target.exists():
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_DESTINATION_COLLISION:"+rel.as_posix())
  target.parent.mkdir(parents=True,exist_ok=True)
  target.write_bytes(payload)
  if target.stat().st_size!=size or sha_file(target)!=digest:
   raise RuntimeError("MATERIALIZED_SOURCE_ARCHIVE_POSTWRITE_MISMATCH:"+rel.as_posix())
  restored.append({"path":rel.as_posix(),"bytes":size,"sha256":digest})
 return {"status":"PASS_SOURCE_ARCHIVE_REPLAY_REQUIRED","source_commit":MATERIALIZATION_SOURCE_COMMIT,
  "archive_count_restored":len(restored),"archives":restored,"expanded_module_paths_reset":sorted(set(removed)),
  "reason":"RECORDED_MODULE_TREE_DRIFT; REPLAY_SOURCE_ARCHIVES_AND_REVALIDATE"}

def factory_materialize(runtime,rollback,raw_cap,repo_root=None):
 placement_path=runtime/"EXTERNALIZED_ASSET_PLACEMENT.json"
 routing_path=runtime/"command_subdomain_routing.json"
 placement=json.loads(placement_path.read_text(encoding="utf-8"))
 routing=json.loads(routing_path.read_text(encoding="utf-8"))
 original=json.loads((runtime/"MACRODOWN_MANIFEST.json").read_text(encoding="utf-8"))
 original_files={r["path"]:r for r in original.get("files",[])}
 module_registry_path=runtime/"module_registry.json"
 if module_registry_path.is_symlink() or not module_registry_path.is_file():
  raise RuntimeError("MATERIALIZED_MODULE_REGISTRY_MISSING")
 prior_registry=json.loads(module_registry_path.read_text(encoding="utf-8"))
 prior_reconciliation=placement.get("factory_reconciliation",{})
 if not isinstance(prior_reconciliation,dict): prior_reconciliation={}
 prior_archive_rows=prior_reconciliation.get("archives",[])
 prior_readme_rows=prior_reconciliation.get("readmes_removed",[])
 source_tree_recovery=None
 if prior_registry.get("materialized_module_count",0):
  source_archives_present=any(p.is_file() and not p.is_symlink() and p.suffix.lower() in ARCHIVE_SUFFIXES for p in runtime.rglob("*"))
  if not source_archives_present:
   try:
    load_registered_materialized_modules(runtime,prior_registry)
   except RuntimeError as exc:
    recoverable=("MATERIALIZED_MODULE_TREE_INTEGRITY_MISMATCH:",
     "MATERIALIZED_MODULE_DESCRIPTOR_HASH_MISMATCH:",
     "MATERIALIZED_MODULE_DESCRIPTOR_MISSING:",
     "MATERIALIZED_MODULE_DESCRIPTOR_IDENTITY_MISMATCH:")
    if repo_root is None or not str(exc).startswith(recoverable):
     raise
    source_tree_recovery=restore_materialized_modules_from_source_archives(runtime,repo_root,prior_reconciliation)
 registered={}
 for a in placement.get("assets",[]):
  prefix="cajita-luna-runtime/"
  if a.get("placed_path","").startswith(prefix): registered[a["placed_path"][len(prefix):]]=a
 processed=set(); records=[]; removed_bytes=0
 while True:
  pending=sorted([p for p in runtime.rglob("*") if p.is_file() and p.suffix.lower() in ARCHIVE_SUFFIXES and not p.is_symlink() and p.relative_to(runtime).as_posix() not in processed],key=lambda p:p.relative_to(runtime).as_posix().encode())
  if not pending: break
  if len(processed)+len(pending)>200: raise RuntimeError("ARCHIVE_EXPANSION_COUNT_LIMIT")
  for archive in pending:
   rel=archive.relative_to(runtime).as_posix(); oldsha=sha_file(archive); oldsize=archive.stat().st_size
   oldrow=original_files.get(rel)
   if oldrow and (int(oldrow.get("size_bytes",-1))!=oldsize or oldrow.get("sha256")!=oldsha):
    raise RuntimeError("SOURCE_MANIFEST_MISMATCH:"+rel)
   asset=registered.get(rel)
   if asset:
    ex=asset.get("expanded_path",""); prefix="cajita-luna-runtime/"
    if not ex.startswith(prefix): raise RuntimeError("EXPANSION_PATH_INVALID:"+rel)
    dest=runtime.joinpath(*safe_rel(ex[len(prefix):]).parts)
   else: dest=archive.with_suffix("")
   if dest==archive or not dest.resolve().is_relative_to(runtime.resolve()): raise RuntimeError("INVALID_EXPANSION_DESTINATION:"+rel)
   backup=rollback/rel; backup.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(archive,backup)
   extract(archive,dest,rollback)
   count,expanded_bytes=measure(dest,False)
   rec={"source_path":rel,"source_sha256":oldsha,"source_bytes":oldsize,"expanded_path":dest.relative_to(runtime).as_posix(),"expanded_file_count_at_extract":count,"expanded_bytes_at_extract":expanded_bytes,"archive_removed_from_runtime":True,"rollback_path":str(backup.relative_to(rollback)).replace("\\","/"),"asset_id":asset.get("id") if asset else None}
   archive.unlink(); processed.add(rel); removed_bytes+=oldsize; records.append(rec)
   _,raw=measure(runtime,False)
   if raw>raw_cap: raise RuntimeError(f"RAW_STAGING_CEILING_EXCEEDED:{raw}>{raw_cap}")
 archives=[p.relative_to(runtime).as_posix() for p in runtime.rglob("*") if p.is_file() and p.suffix.lower() in ARCHIVE_SUFFIXES]
 if archives: raise RuntimeError("ARCHIVES_REMAIN:"+",".join(archives[:20]))
 readmes=[]
 for p in sorted(runtime.rglob("*"),key=lambda p:len(p.parts),reverse=True):
  if p.is_file() and p.name.upper().startswith("README"):
   readmes.append({"path":p.relative_to(runtime).as_posix(),"bytes":p.stat().st_size,"sha256":sha_file(p)})
   p.unlink()
 if any(p.is_file() and p.name.upper().startswith("README") for p in runtime.rglob("*")): raise RuntimeError("READMES_REMAIN")

 modules={}
 for rec in records: modules[rec["expanded_path"]]=modules.get(rec["expanded_path"],[])
 for rec in records: modules[rec["expanded_path"]].append(rec)
 module_records=[]
 for rel,source_rows in sorted(modules.items()):
  folder=runtime/rel
  descriptor=folder/"CAJITA_MODULE.json"
  if descriptor.exists(): raise RuntimeError("MODULE_DESCRIPTOR_COLLISION:"+rel)
  rows=tree_rows(folder,True); byte_count=sum(x["bytes"] for x in rows)
  data={"schema":"CAJITA_MATERIALIZED_MODULE/1.0","module_key":rel,"identity_type":"PATH_SCOPED_NO_CANONICAL_ID_REASSIGNMENT","canonical_asset_id":next((r["asset_id"] for r in source_rows if r["asset_id"]),None),"source_archives":[{"path":r["source_path"],"bytes":r["source_bytes"],"sha256":r["source_sha256"]} for r in source_rows],"materialization":{"status":"PASS","file_count":len(rows),"bytes":byte_count,"tree_sha256":sha_bytes(canon(rows))},"consumer_adapter":"NOT_PROVEN_BY_EXTRACTION","functional_smoke":"REQUIRED","certification":"NOT_GRANTED"}
  descriptor.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
  module_records.append({**data,"module_manifest_path":descriptor.relative_to(runtime).as_posix(),"module_manifest_sha256":sha_file(descriptor)})

 # The distributed runtime is already materialized on subsequent builds: source
 # ZIP/7Z containers are intentionally absent. Re-use prior records only after
 # validating descriptor hashes, every module file, and exact recorded tree hashes.
 prior_modules=load_registered_materialized_modules(runtime,prior_registry) if prior_registry.get("materialized_module_count",0) else []
 new_keys={m["module_key"] for m in module_records}
 for module in prior_modules:
  if module["module_key"] not in new_keys: module_records.append(module)
 module_records.sort(key=lambda item:item["module_key"].encode("utf-8"))
 if not module_records: raise RuntimeError("NO_MATERIALIZED_MODULES_VERIFIED")

 by_path={r["source_path"]:r for r in records}; by_id={m.get("canonical_asset_id"):m for m in module_records if m.get("canonical_asset_id")}
 for a in placement.get("assets",[]):
  prefix="cajita-luna-runtime/"; rel=a.get("placed_path","")
  rel=rel[len(prefix):] if rel.startswith(prefix) else rel
  r=by_path.get(rel)
  if not r: continue
  m=by_id.get(a["id"])
  a["factory_reconciliation"]={"status":"MATERIALIZED_HASH_VERIFIED","source_archive_sha256_actual":r["source_sha256"],"source_archive_bytes_actual":r["source_bytes"],"historical_hash_match":r["source_sha256"]==a.get("sha256"),"archive_removed_from_runtime":True,"module_path":r["expanded_path"],"module_manifest":m["module_manifest_path"] if m else None,"module_manifest_sha256":m["module_manifest_sha256"] if m else None}
  a["included_in_current_macrodown_manifest"]=False
  a["materialized_module_path"]=r["expanded_path"]
  if m:
   a["expanded_file_count"]=m["materialization"]["file_count"]; a["expanded_bytes"]=m["materialization"]["bytes"]; a["expanded_tree_sha256"]=m["materialization"]["tree_sha256"]
  a["placement"]="MATERIALIZED_DIRECTORY"
 # Merge historical extraction/removal evidence instead of erasing it on archive-free reruns.
 def merge_history(old_rows,new_rows,path_key,hash_key):
  merged={}
  for row in list(old_rows or [])+list(new_rows or []):
   if not isinstance(row,dict) or not row.get(path_key) or not row.get(hash_key):
    raise RuntimeError("MATERIALIZATION_HISTORY_ROW_INVALID")
   merged[(row[path_key],row[hash_key])]=row
  return sorted(merged.values(),key=lambda row:(str(row[path_key]).encode("utf-8"),str(row[hash_key])))
 archive_history=merge_history(prior_archive_rows,records,"source_path","source_sha256")
 readme_history=merge_history(prior_readme_rows,readmes,"path","sha256")
 total_removed_bytes=sum(int(row["source_bytes"]) for row in archive_history)
 placement["factory_reconciliation"]={"schema":SCHEMA,"generated_at_utc":utc(),"archive_count_materialized":len(archive_history),"archive_bytes_removed":total_removed_bytes,"archives":archive_history,"readmes_removed":readme_history,"module_count":len(module_records),"rollback_copies_retained_outside_runtime":bool(records) or bool(prior_reconciliation.get("rollback_copies_retained_outside_runtime",False)),"all_zip_7z_removed":True,"last_run_archive_count_materialized":len(records),"last_run_readme_count_removed":len(readmes),"materialized_module_revalidation":"PASS","source_tree_recovery":source_tree_recovery or prior_reconciliation.get("source_tree_recovery"),"certification":"NOT_GRANTED"}
 placement["status"]="MATERIALIZATION_COMPLETE_PENDING_FUNCTION_AND_G23_G24"
 placement["certification"]="NOT_GRANTED"
 placement_path.write_text(json.dumps(placement,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")

 for a in routing.get("support_assets",[]):
  rel=a.get("relative_path",""); r=by_path.get(rel)
  if r:
   m=by_id.get(r["asset_id"])
   a.update({"source_archive_path":rel,"source_archive_sha256":r["source_sha256"],"source_archive_bytes":r["source_bytes"],"materialized_path":r["expanded_path"],"expanded_bytes":m["materialization"]["bytes"] if m else None,"expanded_tree_sha256":m["materialization"]["tree_sha256"] if m else None,"module_manifest_path":m["module_manifest_path"] if m else None,"module_manifest_sha256":m["module_manifest_sha256"] if m else None,"activation_status":"MATERIALIZED_NOT_FUNCTIONALLY_VALIDATED","archive_removed_from_runtime":True})
 routing["materialization"]={"schema":"CAJITA_MATERIALIZATION_REGISTRY/1.0","archive_policy":"ZIP_7Z_MATERIALIZED_DURING_BUILD_AND_REMOVED","readme_policy":"ALL_README_PREFIX_FILES_REMOVED","module_registry":"module_registry.json","module_count":len(module_records),"archive_count_removed":len(archive_history),"archive_count_this_run":len(records),"certification":"NOT_GRANTED"}
 routing["state"]["status"]="ROUTING_MAP_REGISTERED_MATERIALIZED_MODULES_EXECUTION_REMAINS_FAIL_CLOSED"
 routing["state"]["task_dispatch"]="PLAN_ONLY_UNTIL_TASK_ADAPTERS_AND_RESOURCE_EVIDENCE_PASS"
 routing["state"]["certification"]="NOT_GRANTED"
 routing_path.write_text(json.dumps(routing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 registry={"schema":"CAJITA_MODULE_REGISTRY/1.0","generated_at_utc":utc(),"domain_order":routing.get("domain_order",[]),"canonical_engine_count":len(routing.get("engine_registry",[])),"canonical_command_count":len(routing.get("route_profiles",[])),"materialized_module_count":len(module_records),"modules":[{"module_key":m["module_key"],"canonical_asset_id":m["canonical_asset_id"],"path":m["module_key"],"manifest":m["module_manifest_path"],"manifest_sha256":m["module_manifest_sha256"],"tree_sha256":m["materialization"]["tree_sha256"],"bytes":m["materialization"]["bytes"],"file_count":m["materialization"]["file_count"],"state":"MATERIALIZED_HASH_VERIFIED","consumer_adapter":"NOT_PROVEN_BY_EXTRACTION","execution":"NOT_GRANTED_WITHOUT_ADAPTER_AND_SMOKE","certification":"NOT_GRANTED"} for m in module_records],"certification":"NOT_GRANTED"}
 (runtime/"module_registry.json").write_text(json.dumps(registry,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 _,raw=measure(runtime,False)
 if raw>raw_cap: raise RuntimeError(f"RAW_STAGING_CEILING_EXCEEDED:{raw}>{raw_cap}")
 return {"archive_count":len(archive_history),"archive_count_this_run":len(records),"archive_bytes_removed":total_removed_bytes,"archives":archive_history,"readme_count":len(readme_history),"readme_count_this_run":len(readmes),"readmes_removed":readme_history,"module_count":len(module_records),"modules":module_records,"materialized_module_revalidation":"PASS","source_tree_recovery":source_tree_recovery,"raw_tree_bytes_after_materialization":raw}


def build_native_engine_overlays(runtime,source_commit,runner=subprocess.run):
 """Build pinned Foma/Trealla executables into the product runtime and emit hash-bound receipts."""
 runtime=Path(runtime).resolve()
 if not re.fullmatch(r"[0-9a-f]{40}",str(source_commit)): raise RuntimeError("NATIVE_ENGINE_SOURCE_COMMIT_INVALID")
 routing_path=runtime/"command_subdomain_routing.json"
 if routing_path.is_symlink() or not routing_path.is_file(): raise RuntimeError("NATIVE_ENGINE_ROUTING_MISSING")
 routing=json.loads(routing_path.read_text(encoding="utf-8"))
 route_paths={row.get("id"):safe_rel(row.get("path","")) for row in routing.get("targets",[]) if isinstance(row,dict)}
 required={"D04_TRADUCCION_LENGUAS_ANTIGUAS","D04_HERMENEUTICA_HG"}
 if not required.issubset(route_paths): raise RuntimeError("NATIVE_ENGINE_TARGET_ROUTE_MISSING")
 foma_module=runtime.joinpath(*route_paths["D04_TRADUCCION_LENGUAS_ANTIGUAS"].parts)
 trealla_module=runtime.joinpath(*route_paths["D04_HERMENEUTICA_HG"].parts)
 foma_source=foma_module/"foma-master"/"foma-master"/"foma"
 trealla_source=trealla_module/"trealla-2.100.24"/"trealla-2.100.24"
 for label,path in (("FOMA",foma_source),("TREALLA",trealla_source)):
  if path.is_symlink() or not path.is_dir() or not (path/"Makefile").is_file():
   raise RuntimeError("NATIVE_ENGINE_SOURCE_TREE_MISSING:"+label+":"+str(path))
  tree_rows(path,False)
 receipt_path=runtime/"NATIVE_ENGINE_BUILD_RECEIPTS.json"
 if receipt_path.exists() or receipt_path.is_symlink(): raise RuntimeError("NATIVE_ENGINE_BUILD_RECEIPT_COLLISION")
 def run(command,cwd,timeout,label):
  proc=runner(command,cwd=str(cwd),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=timeout,check=False)
  output=proc.stdout or ""
  if proc.returncode!=0: raise RuntimeError("NATIVE_ENGINE_BUILD_COMMAND_FAILED:"+label+":"+str(proc.returncode)+":"+output[-2500:])
  return {"command":list(command),"return_code":proc.returncode,"output_tail":output[-2500:]}
 def executable(root,name):
  candidates=[p for p in root.rglob(name) if p.is_file() and not p.is_symlink() and (p.stat().st_mode&0o111)]
  if not candidates: raise RuntimeError("NATIVE_ENGINE_EXECUTABLE_MISSING:"+name+":"+str(root))
  return min(candidates,key=lambda p:(len(p.relative_to(root).parts),p.relative_to(root).as_posix().encode("utf-8")))
 def copy_shared_libraries(build_root,source_root):
  copied=[]
  for path in sorted(build_root.rglob("*"),key=lambda p:p.relative_to(build_root).as_posix().encode("utf-8")):
   if not (path.name.endswith(".so") or ".so." in path.name): continue
   if path.is_symlink():
    resolved=path.resolve()
    if not resolved.is_file() or not resolved.is_relative_to(build_root): raise RuntimeError("NATIVE_ENGINE_SHARED_LIBRARY_LINK_ESCAPE:"+str(path))
    data=resolved.read_bytes()
   elif path.is_file(): data=path.read_bytes()
   else: continue
   rel=path.relative_to(build_root); dest=source_root/rel; dest.parent.mkdir(parents=True,exist_ok=True)
   if dest.exists() or dest.is_symlink():
    if dest.is_symlink() or not dest.is_file() or sha_file(dest)!=sha_bytes(data): raise RuntimeError("NATIVE_ENGINE_SHARED_LIBRARY_COLLISION:"+str(dest))
   else:
    dest.write_bytes(data); os.chmod(dest,0o644)
   copied.append({"path":dest.relative_to(runtime).as_posix(),"bytes":len(data),"sha256":sha_bytes(data)})
  return copied
 def verify_linkage(binary,label):
  proc=runner(["ldd",str(binary)],cwd=str(binary.parent),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20,check=False)
  output=proc.stdout or ""
  if "not found" in output: raise RuntimeError("NATIVE_ENGINE_LINKED_LIBRARY_MISSING:"+label+":"+output[-2000:])
  if proc.returncode not in (0,1) or (proc.returncode==1 and "not a dynamic executable" not in output.lower() and "statically linked" not in output.lower()):
   raise RuntimeError("NATIVE_ENGINE_LINKAGE_CHECK_FAILED:"+label+":"+str(proc.returncode)+":"+output[-1000:])
  return {"return_code":proc.returncode,"output_tail":output[-2000:],"output_sha256":sha_bytes(output.encode("utf-8"))}
 def build_one(label,target_id,source,command,checks,binary_names,readme_placeholder=False):
  source_tree_sha=tree_hash(source)
  with tempfile.TemporaryDirectory(prefix="cajita-native-"+label.lower()+"-") as tmp:
   build_root=Path(tmp)/source.name; shutil.copytree(source,build_root,symlinks=False)
   placeholder=False
   temporary_test_mode_repairs=[]
   # Some source ZIPs record shell test harnesses as mode 0644 even though the
   # upstream Makefile invokes them as ./run.sh. Repair only the temporary build
   # copy, bind it to the original file hash, and leave the source tree untouched.
   if label=="FOMA" and checks:
    test_runner=build_root/"tests"/"run.sh"
    if test_runner.is_symlink() or not test_runner.is_file():
     raise RuntimeError("NATIVE_ENGINE_TEST_RUNNER_MISSING_OR_UNSAFE:FOMA:tests/run.sh")
    before_mode=stat.S_IMODE(test_runner.stat().st_mode)
    before_sha=sha_file(test_runner)
    os.chmod(test_runner,before_mode|0o111)
    if sha_file(test_runner)!=before_sha or not (test_runner.stat().st_mode&0o111):
     raise RuntimeError("NATIVE_ENGINE_TEST_RUNNER_MODE_REPAIR_FAILED:FOMA:tests/run.sh")
    temporary_test_mode_repairs.append({
     "path":"tests/run.sh","original_mode":oct(before_mode),
     "temporary_build_mode":oct(stat.S_IMODE(test_runner.stat().st_mode)),
     "sha256":before_sha,"scope":"TEMPORARY_BUILD_COPY_ONLY",
     "source_tree_mutated":False
    })
   if readme_placeholder and not (build_root/"README.md").is_file():
    (build_root/"README.md").write_text("Build-only prerequisite for pinned Trealla source; not shipped in runtime.\n",encoding="utf-8")
    placeholder=True
   commands=[run(command,build_root,900,label+"_BUILD")]
   for check_command in checks: commands.append(run(check_command,build_root,900,label+"_REGRESSION"))
   libraries=copy_shared_libraries(build_root,source)
   outputs=[]
   for name in binary_names:
    built=executable(build_root,name); dest=source/name
    if dest.exists() or dest.is_symlink(): raise RuntimeError("NATIVE_ENGINE_BINARY_DESTINATION_COLLISION:"+label+":"+str(dest))
    dest.parent.mkdir(parents=True,exist_ok=True); shutil.copy2(built,dest); os.chmod(dest,dest.stat().st_mode|0o111)
    outputs.append({"name":name,"path":dest.relative_to(runtime).as_posix(),"bytes":dest.stat().st_size,"sha256":sha_file(dest),"linkage":verify_linkage(dest,label+"_"+name)})
  return {"target_id":target_id,"source_path":source.relative_to(runtime).as_posix(),"source_commit":source_commit,
          "source_tree_sha256_before_build":source_tree_sha,"build_commands":commands,
          "temporary_readme_prerequisite_created":placeholder,"temporary_test_mode_repairs":temporary_test_mode_repairs,
          "binary_artifacts":outputs,"shared_libraries":libraries,
          "build_status":"PASS","runtime_compile_required":False,"certification":"NOT_GRANTED"}
 versions={}
 for name,command in (("make",["make","--version"]),("compiler",["cc","--version"])):
  proc=runner(command,cwd=str(runtime),stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20,check=False)
  if proc.returncode!=0: raise RuntimeError("NATIVE_ENGINE_TOOLCHAIN_VERSION_UNAVAILABLE:"+name+":"+str(proc.returncode))
  versions[name]=(proc.stdout or "").splitlines()[0][:240]
 foma=build_one("FOMA","D04_TRADUCCION_LENGUAS_ANTIGUAS",foma_source,["make","-j1"],[["make","check"]],["foma","flookup"])
 trealla=build_one("TREALLA","D04_HERMENEUTICA_HG",trealla_source,["make","-j1",'GIT_VERSION="2.100.24"',"NOFFI=1","NOSSL=1","NOTHREADS=1","ISOCLINE=1"],[],["tpl"],True)
 receipt={"schema":"CAJITA_NATIVE_ENGINE_BUILD_RECEIPTS/1.0","source_commit":source_commit,"build_environment":versions,
          "builds":[foma,trealla],"runtime_compile_required":False,"model_weight_downloads":0,
          "remote_commander_used":False,"certification":"NOT_GRANTED"}
 receipt_path.write_text(json.dumps(receipt,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
 routing.setdefault("materialization",{})["native_engine_build_receipt"]="NATIVE_ENGINE_BUILD_RECEIPTS.json"
 routing["materialization"]["native_engine_build_receipt_sha256"]=sha_file(receipt_path)
 routing["materialization"]["native_engine_build_status"]="PASS_TWO_PINNED_SOURCE_BUILDS"
 routing["materialization"]["native_engine_runtime_compile_required"]=False
 routing_path.write_text(json.dumps(routing,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
 return receipt


def append_runtime_policy(runtime,factory_data):
 p=runtime/"CajitadeLuna.md"; original=p.read_bytes()
 text=f"""

---

## Política de fabricación V10: módulos materializados y distribución conjunta

Esta sección es aditiva; se preserva el documento histórico y se aplica a esta fabricación para resolver el empaquetado durante la construcción, no durante cada ejecución.

- Cada archivo ZIP o 7Z del runtime se valida y extrae durante la fabricación. Solo se elimina el contenedor después de la prueba de integridad y la verificación de colisiones. Se conserva una copia de rollback fuera del runtime distribuible.
- Se eliminan todos los archivos cuyo nombre comienza por README, sin distinguir mayúsculas. Sus rutas, tamaños y SHA-256 quedan registrados en el manifiesto de fabricación.
- Cada paquete extraído queda identificado como módulo mediante CAJITA_MODULE.json y module_registry.json. La materialización no autoriza a dar por conectado un consumidor: adaptador, smoke nativo y medición de recursos siguen siendo pruebas separadas.
- Los seis artefactos de pesos deben mantener exactamente tamaño y SHA-256. No se reemplazan modelos ni motores por motivos de tamaño.
- El árbol de trabajo materializado tiene un techo de fabricación separado de {RAW_CAP} bytes. La puerta de distribución conjunta mide el archivo .macrodown más Louksna1.md, con máximo decimal exacto de {COMBINED_CAP} bytes. El techo del árbol de trabajo no amplía el presupuesto del producto final.
- La ejecución sigue siendo secuencial y bajo demanda. La autorización de una tarea no equivale a autorización de efectos ajenos a ella.
- El sistema antiparálisis mantiene un diario persistente encadenado por SHA-256, limita a tres las observaciones idénticas sin progreso y pasa a HOLD_CONSCIOUS al agotarlas. No realiza reintentos automáticos con efectos desconocidos ni sin idempotencia y checkpoint verificado.
- Ningún estado de certificación se hereda automáticamente. La certificación integral exige evidencia independiente G23 y una decisión G24 separada.
- Foma y Trealla se compilan durante la fabricación desde sus árboles fuente fijados; los ejecutables incluidos, hashes, toolchain y resultados de enlace quedan en NATIVE_ENGINE_BUILD_RECEIPTS.json. El runtime final no necesita compilar esos dos motores al ejecutarlos.

Estado de fabricación: {factory_data["archive_count"]} contenedores ZIP/7Z retirados tras extracción; {factory_data["readme_count"]} README retirados; {factory_data["module_count"]} módulos de ruta registrados; {len(factory_data.get("native_engine_builds", []))} motores nativos compilados y hash-vinculados. La validación funcional completa y la certificación global permanecen pendientes de sus gates independientes.
"""
 p.write_bytes(original+text.encode("utf-8"))

def make_louksna1(repo_root,runtime,out_doc):
 source=repo_root/"LOUKSNAMEJORADA.md"
 if not source.is_file() or source.is_symlink(): raise RuntimeError("PROTECTED_ARCHITECTURE_MISSING")
 base=source.read_bytes(); base_hash=sha_bytes(base); cajita=(runtime/"CajitadeLuna.md").read_bytes()
 marker=f"""

---

# Unificación gobernada de Cajita de Luna

Fórmula: LOUKSNAMEJORADA.md + runtime definido por CajitadeLuna.md → LOUKSNA1.md.

El prefijo de este archivo preserva byte por byte LOUKSNAMEJORADA.md; el archivo fuente no se modifica. Se incorpora íntegramente CajitadeLuna.md y el runtime distribuible se entrega por separado como CAJITA_LUNA_RUNTIME_V10.macrodown. El registro LOUKSNA1_RELEASE_MANIFEST.json vincula los tamaños y SHA-256 exactos de ambos artefactos.

## Invariantes

- Fuente protegida: SHA-256 {base_hash}; prefijo byte exacto confirmado.
- Se mantienen seis dominios, orden canónico, 15 motores, 14 comandos y las identidades existentes.
- ZIP/7Z se materializan durante la fabricación y se retiran del runtime después de verificar la extracción; no se empaquetan junto al mismo árbol expandido.
- README* se excluyen del runtime y se registran en evidencia.
- Cada módulo de ruta declara procedencia, integridad y estado del adaptador sin recibir identidad canónica inventada.
- Los 21 destinos canónicos se registran como módulos de ruta; D02_MULTI_INTERDISCIPLINAR se vincula al prefijo byte-exacto de LOUKSNAMEJORADA.md. Se preservan como declaraciones de procedencia AX0001-AX12414, 11.757 axiomas declarados materializados, 657 brechas históricas, B1-B134 y 18 frameworks. El enlace por hash no se presenta como ejecución de grafo ni como validación semántica.
- Presupuesto conjunto de distribución: .macrodown + este documento ≤ {COMBINED_CAP} bytes decimales.
- Antiparálisis persistente, diario verificable por cadena SHA-256 y HOLD_CONSCIOUS al tercer estancamiento idéntico. Sin bucles infinitos ni reintentos automáticos para efectos desconocidos.
- Presencia, integridad, smoke, G23 y G24 son estados distintos.

## Alcance y certificación

La evidencia independiente debe vincular los SHA-256 del documento y del paquete distribuible. Ningún PASS de fabricación se convierte automáticamente en certificación integral. La decisión global queda NOT_GRANTED hasta completar G23 y G24 y probar adaptadores funcionales, calidad y recursos dentro del alcance declarado.
"""
 out_doc.parent.mkdir(parents=True,exist_ok=True)
 out_doc.write_bytes(base+marker.encode()+b"\n\n---\n\n# Documento central del runtime Cajita de Luna (copia literal)\n\n"+cajita)
 if not out_doc.read_bytes().startswith(base): raise RuntimeError("LOUKSNAMEJORADA_PREFIX_NOT_BYTE_EXACT")
 return {"path":out_doc.name,"bytes":out_doc.stat().st_size,"sha256":sha_file(out_doc),"source_sha256":base_hash,"prefix_byte_exact":True,"cajita_doc_sha256":sha_bytes(cajita)}

def main():
 ap=argparse.ArgumentParser()
 ap.add_argument("--repo-root",default="."); ap.add_argument("--output-dir",required=True)
 ap.add_argument("--raw-cap-bytes",type=int,default=RAW_CAP); ap.add_argument("--combined-cap-bytes",type=int,default=COMBINED_CAP)
 a=ap.parse_args(); repo=Path(a.repo_root).resolve(); out=Path(a.output_dir).resolve()
 runtime_source=repo/"cajita-luna-runtime"; stage_parent=out/"stage"; runtime=stage_parent/"cajita-luna-runtime"; rollback=out/"rollback-source-archives"
 out.mkdir(parents=True,exist_ok=True)
 if stage_parent.exists(): shutil.rmtree(stage_parent)
 stage_parent.mkdir(parents=True); rollback.mkdir(parents=True,exist_ok=True)
 report={"schema":SCHEMA,"generated_at_utc":utc(),"status":"RUNNING","certification":"NOT_GRANTED","blockers":[]}
 report_path=out/"factory-report.json"
 try:
  report["source_commit"]=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
  shutil.copytree(runtime_source,runtime,symlinks=True)
  weights=json.loads((runtime/"CAJITA_RUNTIME_V1/weights_manifest.json").read_text(encoding="utf-8"))
  report["weights_before"]=verify_weights(runtime,weights)
  data=factory_materialize(runtime,rollback,a.raw_cap_bytes,repo_root=repo)
  native_receipt=build_native_engine_overlays(runtime,report["source_commit"])
  data["native_engine_builds"]=native_receipt["builds"]
  data["native_engine_build_receipt_sha256"]=sha_file(runtime/"NATIVE_ENGINE_BUILD_RECEIPTS.json")
  raw_after_native_build=measure(runtime,False)[1]
  if raw_after_native_build>a.raw_cap_bytes: raise RuntimeError(f"RAW_STAGING_CEILING_EXCEEDED_AFTER_NATIVE_BUILD:{raw_after_native_build}>{a.raw_cap_bytes}")
  data["raw_tree_bytes_after_native_build"]=raw_after_native_build
  report["materialization"]=data
  report["native_engine_build_receipts"]=native_receipt
  append_runtime_policy(runtime,data)
  routing=json.loads((runtime/"command_subdomain_routing.json").read_text(encoding="utf-8"))
  expected=["D01_CEREBRO","D02_ORQUESTACION","D03_TRANSCRIPCION","D04_TRADUCTOR_INTELIGENTE","D05_INTELIGENCIA_DOCUMENTAL","D06_SISTEMA_INTELIGENTE"]
  if routing.get("domain_order")!=expected or len(routing.get("engine_registry",[]))!=15 or len(routing.get("route_profiles",[]))!=14 or len(routing.get("targets",[]))!=21 or len(routing.get("support_assets",[]))!=10:
   raise RuntimeError("CANONICAL_TAXONOMY_INVARIANT_FAILED")
  report["weights_after"]=verify_weights(runtime,weights)
  report["weights_preserved"]=report["weights_before"]==report["weights_after"]
  if not report["weights_preserved"]: raise RuntimeError("WEIGHT_IDENTITY_CHANGED")
  doc=out/"Louksna1.md"; report["louksna1"]=make_louksna1(repo,runtime,doc)
  report["axiom_interdisciplinary_binding"]=register_architecture_binding(repo,runtime,doc)
  registry=json.loads((runtime/"module_registry.json").read_text(encoding="utf-8"))
  if registry.get("canonical_target_module_count")!=21 or len(registry.get("target_modules",[]))!=21:
   raise RuntimeError("CANONICAL_TARGET_MODULE_COUNT_MISMATCH")
  if registry.get("axiom_interdisciplinary_binding",{}).get("state")!="SOURCE_BOUND_BLOCK_ENGINE_GRAPH_BOUND":
   raise RuntimeError("AXIOM_INTERDISCIPLINARY_BINDING_MISSING")
  pkg=out/"CAJITA_LUNA_RUNTIME_V10.macrodown"
  builder=subprocess.run([sys.executable,str(runtime/"reproduce_macrodown.py"),"--root",str(runtime),"--output",str(pkg),"--raw-cap-bytes",str(a.raw_cap_bytes),"--combined-cap-bytes",str(a.combined_cap_bytes),"--companion-bytes",str(doc.stat().st_size),"--companion-sha256",sha_file(doc)],text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=1800)
  report["builder_output"]=builder.stdout[-12000:]
  if builder.returncode or not pkg.is_file(): raise RuntimeError("MACRODOWN_BUILD_FAILED:"+builder.stdout[-1800:])
  built=json.loads(builder.stdout); 
  with zipfile.ZipFile(pkg) as z:
   if z.testzip(): raise RuntimeError("MACRODOWN_CRC_FAILED")
   names=z.namelist()
   if len(names)!=len(set(names)): raise RuntimeError("MACRODOWN_DUPLICATE_MEMBERS")
   if any(Path(n).name.upper().startswith("README") for n in names): raise RuntimeError("README_STILL_PACKAGED")
   externalized_archives=externalized_container_contract(runtime)
   validate_packaged_archive_member_set(names,externalized_archives)
   manifest=json.loads(z.read("MACRODOWN_MANIFEST.json")); table={x["path"]:x for x in manifest["files"]}
   if set(table)!=set(names)-{"MACRODOWN_MANIFEST.json"}: raise RuntimeError("MACRODOWN_MANIFEST_MEMBER_SET_MISMATCH")
   for name,row in table.items():
    content=z.read(name)
    if len(content)!=int(row["size_bytes"]) or sha_bytes(content)!=row["sha256"]: raise RuntimeError("MACRODOWN_MEMBER_HASH_MISMATCH:"+name)
   for name,expected in externalized_archives.items():
    content=z.read(name)
    if len(content)!=expected["bytes"] or sha_bytes(content)!=expected["sha256"]:
     raise RuntimeError("EXTERNALIZED_ARCHIVE_CONTENT_IDENTITY_MISMATCH:"+expected["id"]+":"+name)
  archive_bytes=pkg.stat().st_size
  if archive_bytes>RUNTIME_ARCHIVE_CAP:
   raise RuntimeError(f"CAJITA_RUNTIME_ARCHIVE_OVER_CAP:{archive_bytes}>{RUNTIME_ARCHIVE_CAP}")
  combined=archive_bytes+doc.stat().st_size
  if combined>a.combined_cap_bytes: raise RuntimeError(f"COMBINED_DISTRIBUTION_OVER_CAP:{combined}>{a.combined_cap_bytes}")
  release={"schema":"LOUKSNA1_RELEASE_MANIFEST/1.0","source_commit":report["source_commit"],"generated_at_utc":utc(),
   "protected_architecture":{"path":"LOUKSNAMEJORADA.md","sha256":report["louksna1"]["source_sha256"],"modified":False,"prefix_byte_exact":True},
   "louksna1":{"path":doc.name,"bytes":doc.stat().st_size,"sha256":sha_file(doc)},
   "runtime_distribution":{"path":pkg.name,"bytes":pkg.stat().st_size,"sha256":sha_file(pkg)},
   "externalized_archives":[{"id":meta["id"],"path":name,"bytes":meta["bytes"],"sha256":meta["sha256"]} for name,meta in externalized_archives.items()],
   "externalized_archive_contract_status":"PASS_EXACTLY_TEN_REGISTERED_SHA256_PINNED_7Z_CONTAINERS",
   "cajita_runtime_archive":{"path":pkg.name,"bytes":archive_bytes,"cap_bytes":RUNTIME_ARCHIVE_CAP,"status":"PASS"},
   "combined_distribution":{"bytes":combined,"cap_bytes":a.combined_cap_bytes,"status":"PASS"},
   "axiom_interdisciplinary_binding":{"path":report["axiom_interdisciplinary_binding"]["binding_path"],"sha256":report["axiom_interdisciplinary_binding"]["binding_sha256"],"target_module_count":report["axiom_interdisciplinary_binding"]["target_module_count"],"declared_materialized_axioms":11757,"declared_historical_gaps":657,"block_count":134,"framework_count":18,"source_binding":"PASS_STRUCTURAL_BLOCK_ROUTING_ONLY"},
   "gates":{"G23":"NOT_PERFORMED","G24":"NOT_GRANTED"},"global_certification":"NOT_GRANTED",
   "functional_scope":"MATERIALIZATION_HASHES_STRUCTURE_PACKAGE_CRC_PENDING_NATIVE_TASK_ADAPTERS_AND_HARDWARE_SMOKE",
   "status":"BUILT_CANDIDATE_PENDING_G23_G24"}
  (out/"LOUKSNA1_RELEASE_MANIFEST.json").write_text(json.dumps(release,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  report["distribution"]={"archive_bytes":pkg.stat().st_size,"archive_sha256":sha_file(pkg),"louksna1_bytes":doc.stat().st_size,"louksna1_sha256":sha_file(doc),"combined_bytes":combined,"combined_cap_bytes":a.combined_cap_bytes,"status":"PASS","raw_tree_bytes":built["gross_raw_payload_bytes"]}
  report["status"]="PASS_MANUFACTURED_CANDIDATE_PENDING_G23_G24"; report["next_gate"]="INDEPENDENT_G23_G24_AND_REAL_ONE_CPU_1_GIB_FUNCTIONAL_TESTS"
  report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({"status":report["status"],"report":str(report_path),"distribution":report["distribution"]},ensure_ascii=False))
  return 0
 except Exception as exc:
  report["status"]="HOLD" if "OVER_CAP" in str(exc) or "CEILING_EXCEEDED" in str(exc) else "FAIL_CLOSED"
  report["blockers"].append(type(exc).__name__+":"+str(exc)[:3000]); report["finished_at_utc"]=utc()
  report_path.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
  print(json.dumps({"status":report["status"],"blockers":report["blockers"],"report":str(report_path)},ensure_ascii=False),file=sys.stderr)
  return 2

if __name__=="__main__":
 raise SystemExit(main())
