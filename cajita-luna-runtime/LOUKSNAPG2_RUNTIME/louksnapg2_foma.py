#!/usr/bin/env python3
"""Source-bound Foma finite-state runtime; linguistic resources are separately pinned."""
from __future__ import annotations
import hashlib, json, os, shutil, subprocess, tempfile
from pathlib import Path

FOMA_SOURCE_REL=Path("4. Traductor Inteligente/Traducción de lenguas antiguas/foma-master/foma-master/foma")
TRANSDUCER_MANIFEST=Path(__file__).resolve().parent/"foma_transducers"/"manifest.json"
MAX_INPUT_CHARS=16384

class FomaRuntimeError(RuntimeError): pass

def sha256_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1024*1024),b""): h.update(block)
    return h.hexdigest()

def sha256_tree(root):
    root=Path(root).resolve(strict=True)
    if root.is_symlink() or not root.is_dir(): raise FomaRuntimeError("FOMA_SOURCE_DIRECTORY_INVALID")
    h=hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_symlink(): raise FomaRuntimeError("FOMA_SOURCE_SYMLINK_REJECTED:"+str(p.relative_to(root)))
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode()+b"\0")
            h.update(str(p.stat().st_size).encode()+b"\0")
            h.update(bytes.fromhex(sha256_file(p)))
    return h.hexdigest()

def source_directory(cajita_root):
    source=Path(cajita_root).resolve(strict=True)/FOMA_SOURCE_REL
    if source.is_symlink() or not source.is_dir() or not (source/"Makefile").is_file():
        raise FomaRuntimeError("FOMA_SOURCE_OR_MAKEFILE_MISSING")
    return source

def _run(command,cwd,timeout_seconds,input_text=None):
    try:
        p=subprocess.run(command,cwd=str(cwd),input=input_text,capture_output=True,text=True,
            errors="replace",timeout=timeout_seconds,check=False,
            env={**os.environ,"LC_ALL":"C","MAKEFLAGS":"-j1"})
    except subprocess.TimeoutExpired as e: raise FomaRuntimeError("FOMA_COMMAND_TIMEOUT:"+command[0]) from e
    except OSError as e: raise FomaRuntimeError("FOMA_COMMAND_LAUNCH_FAILED:"+command[0]+":"+str(e)[:160]) from e
    evidence={"command":command,"exit_code":p.returncode,"stdout_tail":p.stdout[-5000:],"stderr_tail":p.stderr[-5000:]}
    if p.returncode: raise FomaRuntimeError("FOMA_COMMAND_FAILED:"+command[0]+":"+str(p.returncode)+":"+p.stderr[-500:])
    return evidence

def _lookup_smoke(foma_bin,flookup_bin,work_dir):
    script=work_dir/"louksnapg2-foma-smoke.script"; fst=work_dir/"louksnapg2-foma-smoke.fst"
    script.write_text("regex c:d a:o t:g ;\nsave stack "+str(fst)+"\n",encoding="utf-8")
    compile_result=_run([str(foma_bin),"-q","-l",str(script)],work_dir,60)
    if not fst.is_file() or fst.is_symlink() or fst.stat().st_size<=0: raise FomaRuntimeError("FOMA_SMOKE_TRANSDUCER_NOT_WRITTEN")
    lookup=_run([str(flookup_bin),"-i","-x",str(fst)],work_dir,30,"cat\n")
    outputs=[x.strip() for x in lookup["stdout_tail"].splitlines() if x.strip()]
    if outputs!=["dog"]: raise FomaRuntimeError("FOMA_SMOKE_LOOKUP_MISMATCH:"+repr(outputs))
    return {"status":"PASS_FOMA_ENGINE_LOOKUP_SMOKE","fixture_input":"cat","fixture_output":"dog",
            "transducer_bytes":fst.stat().st_size,"transducer_sha256":sha256_file(fst),
            "compile":compile_result,"lookup":lookup}

def compile_foma_source(source_root,build_root,timeout_seconds=1200):
    source_root=Path(source_root).resolve(strict=True); build_root=Path(build_root).resolve()
    if build_root.exists() or build_root.is_symlink(): raise FomaRuntimeError("FOMA_BUILD_OUTPUT_ALREADY_EXISTS")
    build_root.mkdir(parents=True,exist_ok=False); source_sha=sha256_tree(source_root)
    copied=build_root/"source"; shutil.copytree(source_root,copied,symlinks=False)
    if sha256_tree(copied)!=source_sha: raise FomaRuntimeError("FOMA_SOURCE_COPY_HASH_MISMATCH")
    make=_run(["make","-j1","check"],copied,timeout_seconds)
    foma=copied/"foma"; flookup=copied/"flookup"
    for label,p in (("foma",foma),("flookup",flookup)):
        if p.is_symlink() or not p.is_file() or not os.access(p,os.X_OK):
            raise FomaRuntimeError("FOMA_EXECUTABLE_MISSING_OR_NOT_EXECUTABLE:"+label)
    smoke=_lookup_smoke(foma,flookup,build_root)
    return {"schema":"LOUKSNAPG2_FOMA_BUILD_EVIDENCE/1.0","status":"PASS_FOMA_ENGINE_LOOKUP_SMOKE",
        "source_tree_sha256":source_sha,"source_file_count":sum(1 for p in source_root.rglob("*") if p.is_file()),
        "build_method":"DISPOSABLE_COPY_MAKE_CHECK_JOBS_1","upstream_regression_tests":"PASS","make_check":make,
        "foma_binary_sha256":sha256_file(foma),"flookup_binary_sha256":sha256_file(flookup),
        "foma_binary_bytes":foma.stat().st_size,"flookup_binary_bytes":flookup.stat().st_size,
        "lookup_smoke":smoke,"source_tree_mutated":False,"linguistic_transducers_included":False,
        "latin_or_greek_translation_quality":"NOT_ESTABLISHED","certification":"NOT_GRANTED"}

class FomaEngine:
    def __init__(self,cajita_root,manifest_path=None):
        self.cajita_root=Path(cajita_root).resolve(strict=True); self.source_root=source_directory(self.cajita_root)
        self.manifest_path=Path(manifest_path or TRANSDUCER_MANIFEST).resolve()
        self.transducer_root=self.manifest_path.parent.resolve()

    def _manifest(self):
        p=self.manifest_path
        if p.is_symlink() or not p.is_file(): raise FomaRuntimeError("FOMA_TRANSLATION_MANIFEST_MISSING")
        try: m=json.loads(p.read_text(encoding="utf-8"))
        except (OSError,json.JSONDecodeError) as e: raise FomaRuntimeError("FOMA_TRANSLATION_MANIFEST_INVALID") from e
        if m.get("schema")!="LOUKSNAPG2_FOMA_TRANSLATION_RESOURCES/1.0": raise FomaRuntimeError("FOMA_TRANSLATION_MANIFEST_SCHEMA_MISMATCH")
        if not isinstance(m.get("transducers"),dict): raise FomaRuntimeError("FOMA_TRANSLATION_TRANSDUCER_TABLE_INVALID")
        return m

    def preflight(self):
        m=self._manifest(); rows=m["transducers"]
        return {"engine":"Foma","engine_source_status":"PRESENT","source_tree_sha256":sha256_tree(self.source_root),
            "manifest_sha256":sha256_file(self.manifest_path),
            "resource_status":"READY" if rows else "RESOURCES_NOT_PROVISIONED",
            "registered_transducer_count":len(rows),
            "compiler_available":bool(shutil.which("make") and shutil.which("cc") and shutil.which("flex") and shutil.which("bison")),
            "translation_quality":"NOT_ESTABLISHED","certification":"NOT_GRANTED"}

    def _binaries(self):
        foma_env=os.environ.get("FOMA_BIN","").strip(); lookup_env=os.environ.get("FLOOKUP_BIN","").strip()
        foma=Path(foma_env).resolve() if foma_env else (Path(shutil.which("foma")).resolve() if shutil.which("foma") else None)
        lookup=Path(lookup_env).resolve() if lookup_env else (Path(shutil.which("flookup")).resolve() if shutil.which("flookup") else None)
        if foma and lookup and foma.is_file() and lookup.is_file(): return foma,lookup
        digest=sha256_tree(self.source_root); cache=Path(tempfile.gettempdir())/("louksnapg2-foma-"+digest[:20])
        copied=cache/"source"; foma=copied/"foma"; lookup=copied/"flookup"
        if not (foma.is_file() and lookup.is_file()):
            if cache.exists(): shutil.rmtree(cache)
            report=compile_foma_source(self.source_root,cache,1200)
            if report.get("status")!="PASS_FOMA_ENGINE_LOOKUP_SMOKE": raise FomaRuntimeError("FOMA_RUNTIME_BUILD_NOT_PASS")
        else: _lookup_smoke(foma,lookup,cache)
        return foma,lookup

    def translate(self,text,*,src_lang,tgt_lang):
        src=src_lang.strip().lower() if isinstance(src_lang,str) else ""
        tgt=tgt_lang.strip().lower() if isinstance(tgt_lang,str) else ""
        src={"la":"lat","gr":"grc"}.get(src,src); tgt={"en":"eng","es":"spa"}.get(tgt,tgt)
        if src not in {"lat","grc"}: raise FomaRuntimeError("FOMA_SOURCE_LANGUAGE_NOT_REGISTERED")
        if tgt not in {"eng","spa"}: raise FomaRuntimeError("FOMA_TARGET_LANGUAGE_NOT_REGISTERED")
        if not isinstance(text,str) or not text.strip() or len(text)>MAX_INPUT_CHARS: raise FomaRuntimeError("FOMA_INPUT_EMPTY_OR_OVER_LIMIT")
        manifest=self._manifest(); key=src+"->"+tgt; row=manifest["transducers"].get(key)
        if not isinstance(row,dict): raise FomaRuntimeError("FOMA_TRANSLATION_RESOURCES_NOT_PROVISIONED:"+key)
        rel=row.get("path")
        if not isinstance(rel,str) or not rel or "\\" in rel or Path(rel).is_absolute(): raise FomaRuntimeError("FOMA_TRANSDUCER_PATH_INVALID")
        p=(self.transducer_root/rel).resolve(strict=True)
        if not p.is_relative_to(self.transducer_root) or p.is_symlink() or not p.is_file(): raise FomaRuntimeError("FOMA_TRANSDUCER_PATH_UNSAFE")
        size=p.stat().st_size; digest=sha256_file(p)
        if size!=int(row.get("bytes",-1)) or digest!=row.get("sha256"): raise FomaRuntimeError("FOMA_TRANSDUCER_IDENTITY_MISMATCH")
        _foma,lookup=self._binaries()
        result=_run([str(lookup),"-i","-x",str(p)],self.transducer_root,60,text.strip()+"\n")
        outputs=[x.strip() for x in result["stdout_tail"].splitlines() if x.strip() and x.strip() not in {"+?","???"}]
        if not outputs: raise FomaRuntimeError("FOMA_TRANSLATION_NO_ANALYSIS")
        output="\n".join(outputs)
        return {"schema":"LOUKSNAPG2_TASK_RESULT/2.0","status":"PASS_EXECUTION","execution_authorized":True,
            "domain_id":"D04_TRADUCCION_LENGUAS_ANTIGUAS","operation":"translate_ancient_text",
            "target_id":"D04_TRADUCCION_LENGUAS_ANTIGUAS","adapter_id":"LOUKSNAPG2_FOMA_ANCIENT_TRANSLATION_ADAPTER/1.0",
            "output_text":output,"output_sha256":hashlib.sha256(output.encode()).hexdigest(),
            "source_language":src,"target_language":tgt,"translation_strategy":"FOMA_FINITE_STATE_TRANSDUCER_LOOKUP",
            "general_translation_fallback_selected":False,
            "model_source_evidence":{"engine_source_tree_sha256":sha256_tree(self.source_root),
                "transducer_path":rel,"transducer_bytes":size,"transducer_sha256":digest,
                "manifest_sha256":sha256_file(self.manifest_path)},
            "semantic_quality_equivalence":"NOT_ESTABLISHED","certification":"NOT_GRANTED_BY_RUNTIME_CALL"}
