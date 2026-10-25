#!/usr/bin/env python3
"""Build a deterministic ZIP-container distributed with the .macrodown extension."""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, stat, zipfile
from pathlib import Path
from cajita_externalized_packaging import prepare_distribution_registry, distribution_contract, verify_all_archives
from cajita_tokenizer_materializer import MANIFEST_NAME as TOKENIZER_MANIFEST_NAME, load_tokenizer_manifest, prepare_compressed_tokenizers
SCHEMA="CAJITA_RUNTIME_MACRODOWN/1.0"
DEFAULT_RAW_CAP_BYTES=1_500_000_000
DEFAULT_COMBINED_CAP_BYTES=470_000_000
MANIFEST_NAME="MACRODOWN_MANIFEST.json"
BINARY_SUFFIXES={".7z",".zip",".gz",".xz",".whl",".nupkg",".gguf",".parquet",".pdf"}
EXCLUDED_DIRS={".git","__pycache__",".pytest_cache"}
EXCLUDED_SUFFIXES={".pyc",".pyo",".tmp",".part"}
# Historical container name. It is not a second runtime identity.
DISTRIBUTION_CONTAINER_FILENAME="CAJITA_LUNA_RUNTIME_V10.macrodown"
# Content hash is independent of mode. This member is an executable engine;
# every other member stays 0644 so the archive remains deterministic.
EXECUTABLE_MEMBER_PATHS=frozenset({
    "6. Sistema Inteligente/Consola/quickjs-linux-x86_64-2026-06-04/qjs",
})

def canonical_runtime_identity(root):
    """Identity comes from the packaged runtime constant and the weight manifest, not from the filename."""
    root=Path(root)
    runtime_source=(root/"cajita_runtime.py").read_text(encoding="utf-8")
    found=re.search(r'^CANDIDATE_ID = "([A-Z0-9_]+)"$', runtime_source, re.M)
    if not found:
        raise RuntimeError("RUNTIME_CANDIDATE_ID_LITERAL_MISSING")
    runtime_id=found.group(1)
    manifest_path=root/"CAJITA_RUNTIME_V1"/"weights_manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise RuntimeError("WEIGHTS_MANIFEST_MISSING_FOR_IDENTITY")
    weights=json.loads(manifest_path.read_text(encoding="utf-8"))
    weight_id=weights.get("candidate_id")
    if weight_id!=runtime_id:
        raise RuntimeError("RUNTIME_WEIGHT_IDENTITY_DIVERGENCE:"+runtime_id+"!="+str(weight_id))
    return runtime_id

def member_mode(rel):
    return 0o755 if rel in EXECUTABLE_MEMBER_PATHS else 0o644

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def _under_externalized_tree(rel, excluded_roots):
    return any(rel == item or rel.startswith(item + "/") for item in excluded_roots)

def iter_files(root,output):
    result=[]
    contract=distribution_contract(root)
    excluded_roots={item["expanded_relpath"] for item in contract}
    placement=json.loads((Path(root)/"EXTERNALIZED_ASSET_PLACEMENT.json").read_text(encoding="utf-8"))
    archive_history=placement.get("factory_reconciliation",{}).get("archives",[])
    archive_source_paths={row.get("source_path") for row in archive_history if isinstance(row,dict) and isinstance(row.get("source_path"),str)}
    externalized_container_paths={item["container_relpath"] for item in contract}
    build_only_archive_paths=archive_source_paths-externalized_container_paths
    tokenizer_manifest=load_tokenizer_manifest(root) if (Path(root)/TOKENIZER_MANIFEST_NAME).is_file() else {"entries":[]}
    tokenizer_source_paths={row["source_path"] for row in tokenizer_manifest.get("entries",[]) if row.get("packed")}
    for base,dirs,names in os.walk(root,topdown=True,followlinks=False):
        bp=Path(base)
        kept=[]
        for d in dirs:
            directory=bp/d
            if directory.is_symlink(): raise RuntimeError("SYMLINK_REFUSED:"+directory.relative_to(root).as_posix())
            rel_dir=directory.relative_to(root).as_posix()
            if d in EXCLUDED_DIRS or _under_externalized_tree(rel_dir,excluded_roots): continue
            kept.append(d)
        dirs[:]=sorted(kept)
        for name in sorted(names):
            p=bp/name
            if p.is_symlink(): raise RuntimeError("SYMLINK_REFUSED:"+p.relative_to(root).as_posix())
            if p.suffix.lower() in EXCLUDED_SUFFIXES or p.name==MANIFEST_NAME: continue
            if not p.is_file(): raise RuntimeError("NON_REGULAR_FILE:"+str(p))
            if p.resolve()==output.resolve(): continue
            rel=p.relative_to(root).as_posix()
            if rel in {"module_registry.json", "command_subdomain_routing.json"} or rel in build_only_archive_paths or rel in tokenizer_source_paths or _under_externalized_tree(rel,excluded_roots): continue
            if rel.startswith("../") or rel.startswith("/"): raise RuntimeError("PATH_ESCAPE:"+rel)
            # Deliver the generated distribution-only routes under the canonical
            # runtime path. The full source routing catalog remains in the repo.
            archive_rel = "command_subdomain_routing.json" if rel == "CAJITA_DISTRIBUTION_ROUTING.json" else rel
            result.append((archive_rel,p))
    if not any(rel == "CAJITA_DISTRIBUTION_MODULE_REGISTRY.json" for rel,_ in result):
        raise RuntimeError("DISTRIBUTION_MODULE_REGISTRY_MISSING_FROM_PAYLOAD")
    if not any(rel == "command_subdomain_routing.json" for rel,_ in result):
        raise RuntimeError("DISTRIBUTION_ROUTING_CATALOG_MISSING_FROM_PAYLOAD")
    return sorted(result,key=lambda x:x[0].encode("utf-8"))

def manifest_bytes(root,files,raw_cap_bytes,combined_cap_bytes,companion_bytes,companion_sha256,externalized_contract):
    domain_map={
      "1. Cerebro":("D01_CEREBRO","cerebro"),
      "2. Orquestación":("D02_ORQUESTACION","orquestacion"),
      "3. Transcripción":("D03_TRANSCRIPCION","transcripcion"),
      "4. Traductor Inteligente":("D04_TRADUCTOR_INTELIGENTE","traductor_inteligente"),
      "5. Inteligencia documental":("D05_INTELIGENCIA_DOCUMENTAL","inteligencia_documental"),
      "6. Sistema Inteligente":("D06_SISTEMA_INTELIGENTE","sistema_inteligente")}
    records=[]; total=0
    for rel,p in files:
        top=rel.split("/",1)[0]; size=p.stat().st_size; total+=size
        records.append({"path":rel,"size_bytes":size,"sha256":sha256_file(p),
          "domain_id":domain_map.get(top,(None,None))[0],
          "route_type":domain_map.get(top,(None,None))[1],
          "zip_method":"STORED" if p.suffix.lower() in BINARY_SUFFIXES else "DEFLATED"})
    tokenizer_manifest_path=Path(root)/TOKENIZER_MANIFEST_NAME
    tokenizer_manifest=json.loads(tokenizer_manifest_path.read_text(encoding="utf-8")) if tokenizer_manifest_path.is_file() else {"entries":[]}
    m={"schema":SCHEMA,"format":"ZIP archive with deterministic metadata; file extension .macrodown",
      "candidate_id":canonical_runtime_identity(root),
      "distribution_container_filename":DISTRIBUTION_CONTAINER_FILENAME,
      "distribution_filename_is_historical_container_name":True,
      "runtime_identity_source":"cajita_runtime.CANDIDATE_ID_MATCHES_WEIGHTS_MANIFEST",
      "hard_cap_raw_bytes":raw_cap_bytes,
      "hard_cap_archive_bytes":max(0,combined_cap_bytes-companion_bytes),
      "combined_distribution_cap_bytes":combined_cap_bytes,
      "companion_artifact":{"path":"Louksna1.md","size_bytes":companion_bytes,"sha256":companion_sha256},
      "gross_payload_bytes":0,
      "gross_payload_bytes_excluding_manifest":total,"file_count_excluding_manifest":len(records),
      "manifest_is_self_excluded_from_file_hash_table":True,
      "domain_order":["D01_CEREBRO","D02_ORQUESTACION","D03_TRANSCRIPCION","D04_TRADUCTOR_INTELIGENTE","D05_INTELIGENCIA_DOCUMENTAL","D06_SISTEMA_INTELIGENTE"],
      "domains":[
       {"id":"D01_CEREBRO","route_type":"cerebro","root":"1. Cerebro/"},
       {"id":"D02_ORQUESTACION","route_type":"orquestacion","root":"2. Orquestación/"},
       {"id":"D03_TRANSCRIPCION","route_type":"transcripcion","root":"3. Transcripción/"},
       {"id":"D04_TRADUCTOR_INTELIGENTE","route_type":"traductor_inteligente","root":"4. Traductor Inteligente/"},
       {"id":"D05_INTELIGENCIA_DOCUMENTAL","route_type":"inteligencia_documental","root":"5. Inteligencia documental/"},
       {"id":"D06_SISTEMA_INTELIGENTE","route_type":"sistema_inteligente","root":"6. Sistema Inteligente/"}],
      "runtime_entrypoint":"cajita_runtime.py","rebuild_script":"reproduce_macrodown.py",
      "external_22_domain_repository_included":False,
      "lossless_tokenizer_compression":{
        "policy":"GZIP_LEVEL9_MTIME0_HASH_PINNED_TEMPORARY_VIEW",
        "manifest":"CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json",
        "source_tokenizer_bytes_excluded_only_when_registered_gzip_is_smaller":True,
        "semantic_change":False,
        "source_files_preserved_in_repository":True,
        "entries":[{"id":row["id"],"source_path":row["source_path"],"source_bytes":row["source_bytes"],"source_sha256":row["source_sha256"],"packed":row["packed"],"compressed_path":row["compressed_path"],"compressed_bytes":row["compressed_bytes"],"compressed_sha256":row["compressed_sha256"]} for row in tokenizer_manifest.get("entries",[])],
        "source_bytes_total":tokenizer_manifest.get("source_bytes_total",0),
        "compressed_bytes_total":tokenizer_manifest.get("compressed_bytes_total",0),
        "bytes_saved_total":tokenizer_manifest.get("bytes_saved_total",0),
        "quality_equivalence":"NOT_ESTABLISHED",
        "certification":"NOT_GRANTED"
      },
      "externalized_asset_policy":{
        "policy":"PACK_COMPRESSED_CONTAINER_ONCE_AND_RECONSTRUCT_EXPANDED_TREE_ON_DEMAND",
        "source_only_registry_excluded":"module_registry.json",
        "distribution_registry":"CAJITA_DISTRIBUTION_MODULE_REGISTRY.json",
        "expanded_materialization_trees_included":False,
        "compressed_containers_included":True,
        "reconstruction_helper":"cajita_externalized_asset_loader.py",
        "reconstruction_requires_explicit_materialization":True,
        "consumer_adapter_validation":"NOT_ESTABLISHED",
        "native_smoke_validation":"REQUIRED",
        "certification":"NOT_GRANTED",
        "assets":[{"id":item["id"],"container_path":item["container_relpath"],"container_bytes":item["container_bytes"],"container_sha256":item["container_sha256"],"expanded_path":item["expanded_relpath"],"expanded_bytes":item["expanded_bytes"],"expanded_file_count":item["expanded_file_count"],"expanded_tree_sha256":item["expanded_tree_sha256"],"module_descriptor_sha256":item["module_descriptor_sha256"]} for item in externalized_contract]
      },
      "files":records}
    for _ in range(10):
        enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
        new_total=total+len(enc)
        if m["gross_payload_bytes"]==new_total: break
        m["gross_payload_bytes"]=new_total
    enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    m["gross_payload_bytes"]=total+len(enc)
    enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    gross=total+len(enc)
    if gross>raw_cap_bytes: raise RuntimeError(f"RAW_BUILD_TREE_OVER_CAP:{gross}>{raw_cap_bytes}")
    return enc,gross

def add_stream(zf,rel,path):
    zi=zipfile.ZipInfo(rel,date_time=(2024,1,1,0,0,0))
    zi.create_system=3; zi.external_attr=(stat.S_IFREG|member_mode(rel))<<16
    zi.compress_type=zipfile.ZIP_STORED if path.suffix.lower() in BINARY_SUFFIXES else zipfile.ZIP_DEFLATED
    zi.extra=b""; zi.comment=b""
    with zf.open(zi,"w",force_zip64=True) as dst, path.open("rb") as src:
        shutil.copyfileobj(src,dst,length=8*1024*1024)

def build(root,output,raw_cap_bytes=DEFAULT_RAW_CAP_BYTES,combined_cap_bytes=DEFAULT_COMBINED_CAP_BYTES,companion_bytes=0,companion_sha256=None):
    root=Path(root).resolve(); output=Path(output).resolve()
    domains=["1. Cerebro","2. Orquestación","3. Transcripción","4. Traductor Inteligente","5. Inteligencia documental","6. Sistema Inteligente"]
    missing=[d for d in domains if not (root/d).is_dir()]
    if missing: raise RuntimeError("DOMAIN_ROOTS_MISSING:"+",".join(missing))
    if not (root/"cajita_runtime.py").is_file(): raise RuntimeError("RUNTIME_ENTRYPOINT_MISSING")
    externalized_contract=prepare_distribution_registry(root)
    tokenizer_manifest=prepare_compressed_tokenizers(root)
    reconstruction=verify_all_archives(root)
    if reconstruction.get("status")!="PASS_CONTAINER_RECONSTRUCTION_ONLY" or reconstruction.get("asset_count")!=10:
        raise RuntimeError("EXTERNALIZED_ASSET_RECONSTRUCTION_GATE_NOT_PASS")
    files=iter_files(root,output); manifest,gross=manifest_bytes(root,files,raw_cap_bytes,combined_cap_bytes,companion_bytes,companion_sha256,externalized_contract)
    output.parent.mkdir(parents=True,exist_ok=True); temp=output.with_name(output.name+".building")
    try:
        if temp.exists(): temp.unlink()
        with zipfile.ZipFile(temp,"w",allowZip64=True,compression=zipfile.ZIP_DEFLATED,compresslevel=9,strict_timestamps=True) as zf:
            for rel,p in files: add_stream(zf,rel,p)
            zi=zipfile.ZipInfo(MANIFEST_NAME,date_time=(2024,1,1,0,0,0))
            zi.create_system=3; zi.external_attr=(stat.S_IFREG|0o644)<<16
            zi.compress_type=zipfile.ZIP_DEFLATED; zi.extra=b""; zi.comment=b""
            zf.writestr(zi,manifest,compress_type=zipfile.ZIP_DEFLATED,compresslevel=9)
        archive_size=temp.stat().st_size
        if gross>raw_cap_bytes: raise RuntimeError(f"RAW_BUILD_TREE_OVER_CAP:{gross}>{raw_cap_bytes}")
        combined_size=archive_size+companion_bytes
        if combined_size>combined_cap_bytes: raise RuntimeError(f"COMBINED_DISTRIBUTION_OVER_CAP:archive={archive_size},companion={companion_bytes},combined={combined_size},cap={combined_cap_bytes}")
        with zipfile.ZipFile(temp,"r") as zf:
            if zf.testzip(): raise RuntimeError("ZIP_CRC_FAILURE")
            names=zf.namelist()
            if len(names)!=len(set(names)): raise RuntimeError("DUPLICATE_MEMBERS")
            if MANIFEST_NAME not in names or "cajita_runtime.py" not in names: raise RuntimeError("RUNTIME_OR_MANIFEST_MISSING")
            for d in domains:
                if not any(n.startswith(d+"/") for n in names): raise RuntimeError("EMPTY_DOMAIN:"+d)
        # Persist exactly the same self-excluding manifest embedded in the validated archive.
        # This prevents the tracked inventory from drifting from the delivered package.
        manifest_target=root/MANIFEST_NAME
        manifest_temp=manifest_target.with_name(MANIFEST_NAME+".building")
        manifest_temp.write_bytes(manifest)
        os.replace(manifest_temp,manifest_target)
        if manifest_target.read_bytes()!=manifest:
            raise RuntimeError("SOURCE_MANIFEST_EMBEDDED_MANIFEST_MISMATCH")
        os.replace(temp,output); digest=sha256_file(output)
        output.with_suffix(output.suffix+".sha256").write_text(digest+"  "+output.name+"\n",encoding="ascii")
        return {"status":"PASS","output":str(output),"archive_bytes":output.stat().st_size,
          "gross_raw_payload_bytes":gross,"raw_build_tree_ceiling_bytes":raw_cap_bytes,
          "combined_distribution_cap_bytes":combined_cap_bytes,"companion_bytes":companion_bytes,
          "combined_distribution_bytes":archive_size+companion_bytes,
          "member_count":len(files)+1,"sha256":digest,"rebuildable":True,
          "externalized_asset_reconstruction":{
              "status":reconstruction.get("status"),
              "asset_count":reconstruction.get("asset_count"),
              "passed_count":reconstruction.get("passed_count"),
              "failed_count":reconstruction.get("failed_count"),
              "assets":[{"id":item.get("id"),"status":item.get("status"),"bytes":item.get("bytes"),"file_count":item.get("file_count"),"tree_sha256":item.get("tree_sha256"),"container_sha256":item.get("container_sha256")} for item in reconstruction.get("assets",[])],
              "consumer_adapter_validation":reconstruction.get("consumer_adapter_validation"),
              "native_smoke_validation":reconstruction.get("native_smoke_validation"),
              "global_certification":"NOT_GRANTED"
          }}
    finally:
        if temp.exists(): temp.unlink()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parent))
    ap.add_argument("--output",default=None)
    ap.add_argument("--raw-cap-bytes",type=int,default=DEFAULT_RAW_CAP_BYTES)
    ap.add_argument("--combined-cap-bytes",type=int,default=DEFAULT_COMBINED_CAP_BYTES)
    ap.add_argument("--companion-bytes",type=int,default=0)
    ap.add_argument("--companion-sha256",default=None)
    ap.add_argument("--prepare-distribution-registry",action="store_true",help="Validate source-registry/descriptor bindings and write the distribution-only registry; the explicit loader verification performs the container round-trip.")
    a=ap.parse_args(); root=Path(a.root).resolve()
    if a.prepare_distribution_registry:
        contract=prepare_distribution_registry(root)
        tokenizer_manifest=prepare_compressed_tokenizers(root)
        print(json.dumps({"status":"PASS_DISTRIBUTION_REGISTRY_PREPARED","asset_count":len(contract),"externalized_expanded_bytes":sum(x["expanded_bytes"] for x in contract),"compressed_container_bytes":sum(x["container_bytes"] for x in contract),"tokenizer_count":len(tokenizer_manifest.get("entries",[])),"tokenizer_source_bytes":tokenizer_manifest.get("source_bytes_total",0),"tokenizer_compressed_bytes":tokenizer_manifest.get("compressed_bytes_total",0),"tokenizer_bytes_saved":tokenizer_manifest.get("bytes_saved_total",0),"tokenizer_manifest":"CAJITA_COMPRESSED_TOKENIZER_MANIFEST.json","semantic_change":False,"certification":"NOT_GRANTED"},ensure_ascii=False,indent=2))
        return
    output=Path(a.output).resolve() if a.output else root.parent/"CAJITA_LUNA_RUNTIME_V10.macrodown"
    if min(a.raw_cap_bytes,a.combined_cap_bytes)<1 or a.companion_bytes<0:
        ap.error("byte limits must be positive and companion bytes must be non-negative")
    if a.companion_sha256 is not None and (len(a.companion_sha256)!=64 or any(c not in "0123456789abcdef" for c in a.companion_sha256)):
        ap.error("companion sha256 must be 64 lowercase hexadecimal characters")
    print(json.dumps(build(root,output,a.raw_cap_bytes,a.combined_cap_bytes,a.companion_bytes,a.companion_sha256),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
