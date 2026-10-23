#!/usr/bin/env python3
"""Build a deterministic ZIP-container distributed with the .macrodown extension."""
from __future__ import annotations
import argparse, hashlib, json, os, shutil, stat, zipfile
from pathlib import Path
SCHEMA="CAJITA_RUNTIME_MACRODOWN/1.0"
HARD_CAP_BYTES=479_000_000
MANIFEST_NAME="MACRODOWN_MANIFEST.json"
BINARY_SUFFIXES={".safetensors",".onnx",".bin",".7z",".zip",".gz",".xz",".whl",".nupkg",".model",".gguf",".parquet",".pdf"}
EXCLUDED_DIRS={".git","__pycache__",".pytest_cache"}
EXCLUDED_SUFFIXES={".pyc",".pyo",".tmp",".part"}

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda:f.read(8*1024*1024),b""): h.update(chunk)
    return h.hexdigest()

def iter_files(root,output):
    result=[]
    for base,dirs,names in os.walk(root,topdown=True,followlinks=False):
        bp=Path(base)
        dirs[:]=sorted(d for d in dirs if d not in EXCLUDED_DIRS and not (bp/d).is_symlink())
        for name in sorted(names):
            p=bp/name
            if p.is_symlink(): raise RuntimeError("SYMLINK_REFUSED:"+p.relative_to(root).as_posix())
            if p.suffix.lower() in EXCLUDED_SUFFIXES or p.name==MANIFEST_NAME: continue
            if not p.is_file(): raise RuntimeError("NON_REGULAR_FILE:"+str(p))
            if p.resolve()==output.resolve(): continue
            rel=p.relative_to(root).as_posix()
            if rel.startswith("../") or rel.startswith("/"): raise RuntimeError("PATH_ESCAPE:"+rel)
            result.append((rel,p))
    return sorted(result,key=lambda x:x[0].encode("utf-8"))

def manifest_bytes(root,files):
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
    m={"schema":SCHEMA,"format":"ZIP archive with deterministic metadata; file extension .macrodown",
      "candidate_id":"CAJITA_LUNA_RUNTIME_V9_20261023","hard_cap_raw_bytes":HARD_CAP_BYTES,
      "hard_cap_archive_bytes":HARD_CAP_BYTES,"gross_payload_bytes":0,
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
      "external_22_domain_repository_included":False,"files":records}
    for _ in range(10):
        enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
        new_total=total+len(enc)
        if m["gross_payload_bytes"]==new_total: break
        m["gross_payload_bytes"]=new_total
    enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    m["gross_payload_bytes"]=total+len(enc)
    enc=(json.dumps(m,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n").encode()
    gross=total+len(enc)
    if gross>HARD_CAP_BYTES: raise RuntimeError(f"RAW_PAYLOAD_OVER_CAP:{gross}>{HARD_CAP_BYTES}")
    return enc,gross

def add_stream(zf,rel,path):
    zi=zipfile.ZipInfo(rel,date_time=(2024,1,1,0,0,0))
    zi.create_system=3; zi.external_attr=(stat.S_IFREG|0o644)<<16
    zi.compress_type=zipfile.ZIP_STORED if path.suffix.lower() in BINARY_SUFFIXES else zipfile.ZIP_DEFLATED
    zi.extra=b""; zi.comment=b""
    with zf.open(zi,"w",force_zip64=True) as dst, path.open("rb") as src:
        shutil.copyfileobj(src,dst,length=8*1024*1024)

def build(root,output):
    root=Path(root).resolve(); output=Path(output).resolve()
    domains=["1. Cerebro","2. Orquestación","3. Transcripción","4. Traductor Inteligente","5. Inteligencia documental","6. Sistema Inteligente"]
    missing=[d for d in domains if not (root/d).is_dir()]
    if missing: raise RuntimeError("DOMAIN_ROOTS_MISSING:"+",".join(missing))
    if not (root/"cajita_runtime.py").is_file(): raise RuntimeError("RUNTIME_ENTRYPOINT_MISSING")
    files=iter_files(root,output); manifest,gross=manifest_bytes(root,files)
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
        if gross>HARD_CAP_BYTES: raise RuntimeError(f"RAW_PAYLOAD_OVER_CAP:{gross}")
        if archive_size>HARD_CAP_BYTES: raise RuntimeError(f"ARCHIVE_OVER_CAP:{archive_size}")
        with zipfile.ZipFile(temp,"r") as zf:
            if zf.testzip(): raise RuntimeError("ZIP_CRC_FAILURE")
            names=zf.namelist()
            if len(names)!=len(set(names)): raise RuntimeError("DUPLICATE_MEMBERS")
            if MANIFEST_NAME not in names or "cajita_runtime.py" not in names: raise RuntimeError("RUNTIME_OR_MANIFEST_MISSING")
            for d in domains:
                if not any(n.startswith(d+"/") for n in names): raise RuntimeError("EMPTY_DOMAIN:"+d)
        os.replace(temp,output); digest=sha256_file(output)
        output.with_suffix(output.suffix+".sha256").write_text(digest+"  "+output.name+"\n",encoding="ascii")
        return {"status":"PASS","output":str(output),"archive_bytes":output.stat().st_size,
          "gross_raw_payload_bytes":gross,"hard_cap_bytes":HARD_CAP_BYTES,
          "member_count":len(files)+1,"sha256":digest,"rebuildable":True}
    finally:
        if temp.exists(): temp.unlink()

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",default=str(Path(__file__).resolve().parent))
    ap.add_argument("--output",default=None)
    a=ap.parse_args(); root=Path(a.root).resolve()
    output=Path(a.output).resolve() if a.output else root.parent/"CAJITA_LUNA_RUNTIME_V9.macrodown"
    print(json.dumps(build(root,output),ensure_ascii=False,indent=2))
if __name__=="__main__": main()
