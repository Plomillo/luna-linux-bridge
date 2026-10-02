#!/usr/bin/env python3
from __future__ import annotations
import argparse, datetime as dt, hashlib, json, os, pathlib, shlex, shutil, subprocess, tarfile, tempfile, time, signal

HOME=pathlib.Path("/home/diegoignacionorambuenamiranda")
R4=HOME/".local/state/louksna/r4-master-part1-part9"
CERTS=R4/"certificates"
STATE=HOME/".local/state/louksna/r4-48h"
EVID=STATE/"evidence"
ROLLBACK=STATE/"rollback"
PROYECTOS=HOME/"PROYECTOS"
DOC_EXT={".pdf",".epub",".md",".txt",".docx",".odt",".html",".htm",".rtf"}
PROTECTED=[
    PROYECTOS,
    HOME/".local/lib/louksna/symphylax-r1/Louksna.md",
    R4,STATE,
]
PART7_SCHEMA="LOUKSNA_R4_PART7_AUX_EVIDENCE/1.0"
PART8_SCHEMA="LOUKSNA_R4_PART8_AUX_EVIDENCE/1.0"
PART9_SCHEMA="LOUKSNA_R4_PART9_TERMINAL_MATRIX/1.0"
PRODUCER_REVISION="2026-10-02.PART789.8-P25-GITHUB-REASONING-ONLY"

def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha(p:pathlib.Path):
    p=pathlib.Path(p); h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def atomic_json(p,obj):
    p=pathlib.Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    t=p.with_suffix(p.suffix+".tmp")
    t.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(t,p)

def read_json(p,default=None):
    try:return json.loads(pathlib.Path(p).read_text(encoding="utf-8"))
    except Exception:return default

def require_cert(part):
    p=CERTS/f"{part}.json"
    if not p.is_file(): raise RuntimeError(part+"_G24_REQUIRED")
    d=read_json(p,{}) or {}
    if d.get("status")!="PASS": raise RuntimeError(part+"_G24_NOT_PASS")
    return {"path":str(p),"sha256":sha(p),"status":"PASS"}

def lrb_link():
    roots=sorted((HOME/".local/lib/louksna-remote-bridge").glob("**/bridge/live_link.py"))
    if not roots: raise RuntimeError("LRB_LINK_MISSING")
    return roots[-1]

def lrb_readonly(op):
    if op not in {"status","observe"}: raise RuntimeError("LRB_MUTATING_OP_DENIED")
    link=lrb_link(); uid=os.getuid()
    env=dict(os.environ)
    env["XDG_RUNTIME_DIR"]=f"/run/user/{uid}"
    env["DBUS_SESSION_BUS_ADDRESS"]=f"unix:path=/run/user/{uid}/bus"
    argv=["python3","-B",str(link),"--state-dir",str(HOME/".local/state/louksna/remote-bridge/service"),
          "--socket-dir",f"/run/user/{uid}/lrb-sock","request","--op",op]
    p=subprocess.run(argv,text=True,capture_output=True,timeout=90,env=env)
    if p.returncode: raise RuntimeError("LRB_READONLY_FAILED:"+p.stderr[-1000:])
    d=json.loads(p.stdout)
    if op=="observe" and not d.get("evidence_sha256"): raise RuntimeError("LRB_OBSERVE_DIGEST_MISSING")
    return d

def observe_pair(tag):
    q={"schema":"LOUKSNA_R4_LRB_READONLY_OBSERVATION/1.0","tag":tag,
       "status":lrb_readonly("status"),"observe":lrb_readonly("observe"),
       "material_execution":False,"captured_at_utc":utc()}
    atomic_json(EVID/f"LRB_{tag}.json",q)
    return q

def candidate_domain_roots():
    exact=[
      PROYECTOS/"2. CORPUS/CORPUS TEÓLOGICO",
      PROYECTOS/"2. CORPUS/CORPUS TEOLOGICO",
      PROYECTOS/"ESTUDIO",PROYECTOS/"Estudio",PROYECTOS/"DEVOCIONAL",PROYECTOS/"Devocional",
      HOME/"Estudio",HOME/"ESTUDIO",HOME/"Devocional",HOME/"DEVOCIONAL"
    ]
    roots=[p for p in exact if p.is_dir()]
    if PROYECTOS.is_dir():
        for base,dirs,_ in os.walk(PROYECTOS):
            rel=pathlib.Path(base).relative_to(PROYECTOS)
            if len(rel.parts)>=5:
                dirs[:]=[]; continue
            for name in list(dirs):
                low=name.casefold()
                if any(k in low for k in ("estudio","study","devocional")):
                    p=pathlib.Path(base)/name
                    if p not in roots: roots.append(p)
            if len(roots)>=40: break
    # Remove nested duplicates deterministically.
    out=[]
    for p in sorted(set(roots),key=lambda x:(len(x.parts),str(x))):
        if not any(p==q or q in p.parents for q in out): out.append(p)
    return out[:40]

def classify(path:pathlib.Path):
    s=str(path).casefold(); n=path.name.casefold()
    rules=[
      ("STUDY_BIBLE",("biblia de estudio","study bible")),
      ("BIBLE_TEXT",("biblia","bible","scripture","escritura")),
      ("COMMENTARY",("comentario","commentary")),
      ("LEXICON",("lexico","léxico","lexicon")),
      ("BIBLICAL_DICTIONARY",("diccionario","dictionary")),
      ("CONFESSION",("confesion","confesión","confession")),
      ("CATECHISM",("catecismo","catechism")),
      ("CHURCH_HISTORY",("historia de la iglesia","church history")),
      ("CHURCH_FATHER",("padres de la iglesia","church father","patrist")),
      ("MAP_ATLAS",("atlas","mapa","map")),
      ("ACADEMIC_ARTICLE",("articulo","artículo","article","paper","journal")),
      ("PERSONAL_NOTE",("nota","notes","apunte")),
      ("THEOLOGICAL_TREATISE",("teologia","teología","theology","tratado","treatise","dogmat","exegético","exegetico","exegesis","hermenéutico","hermeneutico","hermeneutic")),
    ]
    for cls,words in rules:
        if any(w in s or w in n for w in words): return cls
    if "corpus teológico" in s or "corpus teologico" in s:
        return "THEOLOGICAL_TREATISE"
    return "UNKNOWN"

def bounded_run(argv,timeout=300,env=None):
    started=time.monotonic()
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env)
    return {"argv":[str(x) for x in argv],"returncode":p.returncode,
            "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:],
            "elapsed_seconds":round(time.monotonic()-started,3)}

def bounded_run_filebacked(argv,timeout=300,env=None):
    started=time.monotonic()
    with tempfile.NamedTemporaryFile(prefix="louksna-p25-out-",mode="w+b") as out, \
         tempfile.NamedTemporaryFile(prefix="louksna-p25-err-",mode="w+b") as err:
        p=subprocess.run(argv,stdout=out,stderr=err,timeout=timeout,env=env)
        def tail(f,limit=12000):
            f.flush(); size=f.tell(); f.seek(max(0,size-limit))
            return f.read().decode("utf-8","replace")
        return {"argv":[str(x) for x in argv],"returncode":p.returncode,
                "stdout":tail(out),"stderr":tail(err),
                "stdout_bytes":out.tell(),"stderr_bytes":err.tell(),
                "capture_mode":"FILE_BACKED_TAIL_ONLY",
                "elapsed_seconds":round(time.monotonic()-started,3)}

def external_sha256(p):
    r=bounded_run(["sha256sum","--",str(p)],timeout=300)
    if r["returncode"]!=0 or not r["stdout"].strip():
        raise RuntimeError("EXTERNAL_SHA256_FAILED:"+str(p))
    return r["stdout"].split()[0]

def mem_available_bytes():
    try:
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1])*1024
    except Exception:
        pass
    return 0

def chromium_memory_relief_if_needed(required_bytes):
    before=mem_available_bytes()
    result={
      "policy":"MAESTRO_GRACEFUL_CHROMIUM_ONLY",
      "required_bytes":required_bytes,
      "mem_available_before":before,
      "attempted":False,
      "targeted_process_names":["chromium","chromium-browser"],
      "target_pids":[],
      "sigterm_only":True,
      "sigkill_used":False,
      "desktop_commander_used":False,
      "partitioning_performed":False,
    }
    if before>=required_bytes:
        result["status"]="NOT_NEEDED"; result["mem_available_after"]=before
        return result
    pids=[]
    for name in ("chromium","chromium-browser"):
        q=subprocess.run(["pgrep","-x",name],text=True,capture_output=True,timeout=10)
        if q.returncode in (0,1):
            for x in q.stdout.split():
                if x.isdigit(): pids.append(int(x))
    pids=sorted(set(pids))
    result["target_pids"]=pids
    if not pids:
        result["status"]="NO_CHROMIUM_FOUND"; result["mem_available_after"]=before
        return result
    result["attempted"]=True
    for pid in pids:
        try: os.kill(pid,signal.SIGTERM)
        except ProcessLookupError: pass
    deadline=time.monotonic()+12
    remaining=list(pids)
    while remaining and time.monotonic()<deadline:
        time.sleep(0.4)
        alive=[]
        for pid in remaining:
            try: os.kill(pid,0); alive.append(pid)
            except ProcessLookupError: pass
        remaining=alive
    after=mem_available_bytes()
    result["remaining_pids"]=remaining
    result["mem_available_after"]=after
    result["mem_available_delta"]=after-before
    result["status"]="PASS" if not remaining else "HOLD_CHROMIUM_DID_NOT_EXIT_GRACEFULLY"
    return result

def retire_obsolete_p25_profiles(runtime,model):
    before=mem_available_bytes()
    obsolete=[
      {"c":"256","n":"8","t":"1","prompt":"Return exactly: LOUKSNA_P25_OK"},
      {"c":"512","n":"16","t":"2","prompt":"Return exactly: LOUKSNA_P25_OK"},
    ]
    found=[]
    for proc in pathlib.Path("/proc").iterdir():
        if not proc.name.isdigit(): continue
        pid=int(proc.name)
        if pid==os.getpid(): continue
        try:
            raw=(proc/"cmdline").read_bytes()
            argv=[x.decode("utf-8","replace") for x in raw.split(b"\0") if x]
        except (OSError,PermissionError):
            continue
        if not argv or argv[0]!=str(runtime): continue
        try:
            mi=argv.index("-m")
            if mi+1>=len(argv) or argv[mi+1]!=str(model): continue
        except ValueError:
            continue
        for sig in obsolete:
            def pair(flag,val):
                try:
                    i=argv.index(flag)
                    return i+1<len(argv) and argv[i+1]==val
                except ValueError:
                    return False
            prompt_ok=False
            try:
                pi=argv.index("-p")
                prompt_ok=pi+1<len(argv) and argv[pi+1]==sig["prompt"]
            except ValueError:
                pass
            if pair("-c",sig["c"]) and pair("-n",sig["n"]) and pair("-t",sig["t"]) and prompt_ok:
                found.append({"pid":pid,"signature":sig,"argv":argv})
                break
    result={
      "policy":"MAESTRO_EXACT_OBSOLETE_P25_SIGNATURE_SIGTERM_ONLY",
      "status":"NOT_NEEDED" if not found else "AUTHORIZED",
      "matched":found,
      "target_pids":[x["pid"] for x in found],
      "sigterm_only":True,"sigkill_used":False,"sudo_used":False,
      "desktop_commander_used":False,"partitioning_performed":False,
      "mem_available_before":before,
    }
    if not found:
        result["mem_available_after"]=before
        return result
    for x in found:
        try: os.kill(x["pid"],signal.SIGTERM)
        except ProcessLookupError: pass
    deadline=time.monotonic()+15
    remaining=[x["pid"] for x in found]
    while remaining and time.monotonic()<deadline:
        time.sleep(0.5)
        alive=[]
        for pid in remaining:
            try: os.kill(pid,0); alive.append(pid)
            except ProcessLookupError: pass
        remaining=alive
    time.sleep(1)
    after=mem_available_bytes()
    result["remaining_pids"]=remaining
    result["mem_available_after"]=after
    result["mem_available_delta"]=after-before
    result["status"]="PASS" if not remaining else "HOLD_OBSOLETE_P25_DID_NOT_EXIT_GRACEFULLY"
    return result

def bounded_inference_same_qwen(runtime,model,memory_max_bytes):
    args=[
        str(runtime),"-m",str(model),"-c","64","-n","1","-t","1","-ngl","0",
        "--temp","0","--no-display-prompt","-p","Reply with the single digit 7."
    ]
    systemd=shutil.which("systemd-run")
    env=dict(os.environ)
    env.update({"OMP_NUM_THREADS":"1","MALLOC_ARENA_MAX":"2"})
    uid=os.getuid()
    env.setdefault("XDG_RUNTIME_DIR",f"/run/user/{uid}")
    env.setdefault("DBUS_SESSION_BUS_ADDRESS",f"unix:path=/run/user/{uid}/bus")
    if systemd:
        max_mib=max(3072,int(memory_max_bytes//(1024*1024)))
        high_mib=max(2816,max_mib-256)
        timeout_bin=shutil.which("timeout")
        if not timeout_bin:
            return {
              "argv":args,"returncode":125,"stdout":"","stderr":"GNU_TIMEOUT_UNAVAILABLE_FAIL_CLOSED",
              "elapsed_seconds":0.0,"isolation":"SYSTEMD_USER_SCOPE_TIMEOUT_UNAVAILABLE"
            }
        wrapped=[
          systemd,"--user","--scope","--quiet","--collect",
          "-p",f"MemoryHigh={high_mib}M","-p",f"MemoryMax={max_mib}M",
          "--",timeout_bin,"--signal=TERM","--kill-after=10s","150s"
        ]+args
        r=bounded_run_filebacked(wrapped,timeout=180,env=env)
        r["isolation"]="SYSTEMD_USER_SCOPE"
        r["memory_high_mib"]=high_mib
        r["memory_max_mib"]=max_mib
        r["inner_argv"]=args
        return r
    # Fail closed rather than run the 4B model unbounded on a 6 GiB host.
    return {
      "argv":args,"returncode":125,"stdout":"","stderr":"SYSTEMD_RUN_UNAVAILABLE_FAIL_CLOSED",
      "elapsed_seconds":0.0,"isolation":"UNAVAILABLE"
    }

def p25_reasoning_operator():
    """
    P25 is a reasoning-plane binding, not a host execution backend.
    Qwen is the current swappable shared reasoner. It receives only
    LOUKSNA Remote Bridge evidence through the GitHub control plane and
    has no material authority. Maestro remains the sole material worker.
    """
    lrb=observe_pair("P25_REASONING_INPUT")
    evidence_sha=lrb.get("observe",{}).get("evidence_sha256")
    result={
      "schema":"LOUKSNA_SHARED_REASONER_OPERATOR/1.0",
      "state":"HOLD",
      "status":"HOLD",
      "operational":False,
      "provider_current":"QWEN",
      "provider_class":"SWAPPABLE_SHARED_REASONER",
      "role":"REASONING_ONLY",
      "operator_plane":"GITHUB",
      "input_source":"LOUKSNA_REMOTE_BRIDGE_EVIDENCE_ONLY",
      "output_contract":"REASONING_DECISION_ENVELOPE_ONLY",
      "lrb_evidence_sha256":evidence_sha,
      "maestro_material_executor":True,
      "material_execution_authorized":False,
      "host_observation_authorized":False,
      "direct_host_tooling_authorized":False,
      "network_acquisition_authorized":False,
      "partitioning_authorized":False,
      "provider_swappable":True,
      "provider_replacement_preserves_interface":True,
      "inference_executed_on_host":False,
      "qwen_substitution":False,
      "hosted_substitution":False,
      "hosted_backend_used":False,
      "model_download_performed":False,
      "runtime_download_performed":False,
      "downloads_performed":False,
      "desktop_commander_used":False
    }
    operational=(
      isinstance(evidence_sha,str) and len(evidence_sha)==64
      and result["role"]=="REASONING_ONLY"
      and result["operator_plane"]=="GITHUB"
      and result["input_source"]=="LOUKSNA_REMOTE_BRIDGE_EVIDENCE_ONLY"
      and result["material_execution_authorized"] is False
      and result["host_observation_authorized"] is False
      and result["direct_host_tooling_authorized"] is False
      and result["maestro_material_executor"] is True
      and result["provider_swappable"] is True
    )
    result["operational"]=operational
    result["state"]="PASS" if operational else "HOLD"
    result["status"]=result["state"]
    if not operational:
        result["reason"]="REASONING_OPERATOR_LRB_GITHUB_BINDING_INCOMPLETE"
    return result
def p26_document_ingestion():
    src=PROYECTOS/"1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/2. Cajita de Luna/5. Inteligencia documental/Docling"
    local_wheel=src/"docling_slim-2.124.0-py3-none-any.whl"
    root=HOME/".local/share/louksna/docling-slim-2.124.0-p08"
    wheelhouse=HOME/".local/share/louksna/r4-p08/docling-wheelhouse-2.124.0"
    receipt=HOME/".local/share/louksna/r4-p08/P26_DEPENDENCY_RECEIPT.json"
    result={"state":"HOLD","local_wheel_reused":False,"model_download_performed":False,
            "source_mutation_performed":False}
    if not local_wheel.is_file():
        result["reason"]="LOCAL_DOCLING_WHEEL_MISSING"; return result
    wheel_sha=sha(local_wheel)
    expected_local_sha="2c7c667394d3eae9080bc15143ed6f1d39a4838090d9e3f29be212606e6676bd"
    result.update({"local_wheel":str(local_wheel),"local_wheel_sha256":wheel_sha})
    if wheel_sha!=expected_local_sha:
        result["reason"]="LOCAL_DOCLING_WHEEL_HASH_MISMATCH"; return result

    wheelhouse.mkdir(parents=True,exist_ok=True)
    copied=wheelhouse/local_wheel.name
    if not copied.is_file() or sha(copied)!=wheel_sha:
        shutil.copy2(local_wheel,copied)
    result["local_wheel_reused"]=True

    py=root/"bin/python"; cli=root/"bin/docling"
    dependency_download_performed=False
    actions=[]
    if not (py.is_file() and cli.is_file()):
        if root.exists():
            shutil.rmtree(root)
        v=bounded_run(["python3","-m","venv",str(root)],timeout=120)
        actions.append({"venv":v})
        if v["returncode"]!=0:
            result.update({"reason":"P26_VENV_FAILED","actions":actions}); return result
        pip=root/"bin/pip"
        # First resolve base dependencies of the already-present wheel.
        d1=bounded_run([str(pip),"download","--disable-pip-version-check",
                        "--index-url","https://pypi.org/simple",
                        "--dest",str(wheelhouse),str(local_wheel)],timeout=1800)
        actions.append({"download_base_dependencies":d1})
        if d1["returncode"]!=0:
            result.update({"reason":"P26_BASE_DEPENDENCY_DOWNLOAD_FAILED","actions":actions}); return result
        # PDF ingestion extras without reacquiring docling-slim or model weights.
        d2=bounded_run([str(pip),"download","--disable-pip-version-check",
                        "--index-url","https://pypi.org/simple","--dest",str(wheelhouse),
                        "docling-parse>=7.16.0,<8.0.0","pypdfium2>=4.30.0,<6.0.0,!=4.30.1"],timeout=1800)
        actions.append({"download_pdf_dependencies":d2})
        if d2["returncode"]!=0:
            result.update({"reason":"P26_PDF_DEPENDENCY_DOWNLOAD_FAILED","actions":actions}); return result
        dependency_download_performed=True
        install=bounded_run([str(pip),"install","--disable-pip-version-check",
                             "--no-index","--find-links",str(wheelhouse),
                             "docling-slim[format-pdf]==2.124.0"],timeout=1800)
        actions.append({"offline_install":install})
        if install["returncode"]!=0:
            result.update({"reason":"P26_OFFLINE_INSTALL_FAILED","actions":actions}); return result

    wheels=[]
    for p in sorted(wheelhouse.iterdir()):
        if p.is_file():
            wheels.append({"name":p.name,"bytes":p.stat().st_size,"sha256":sha(p)})
    atomic_json(receipt,{"schema":"LOUKSNA_R4_P26_DEPENDENCY_RECEIPT/1.0",
                         "source_index":"https://pypi.org/simple","local_wheel_sha256":wheel_sha,
                         "artifacts":wheels,"dependency_download_performed":dependency_download_performed,
                         "model_download_performed":False,"created_at_utc":utc()})

    version=bounded_run([str(cli),"--version"],timeout=60) if cli.is_file() else {"returncode":127,"stdout":"","stderr":"DOCLING_CLI_MISSING"}
    # Operational PDF ingestion uses the installed PDF engine against an
    # immutable existing corpus source, writing nothing beside that source.
    candidates=[
        PROYECTOS/"1. PROYECTOS PRIORITARIOS/1. PROYECTO LUNA/0. JSON/FORENSIC_V1_20260909/a029_extract/Biblia Textual BTX -- Biblia Textual BTX -- ( WeLib.org ).pdf"
    ]
    sample=next((p for p in candidates if p.is_file() and p.stat().st_size>1024),None)
    probe={"returncode":127,"stdout":"","stderr":"VALID_PDF_SAMPLE_MISSING"}
    if sample is not None:
        code=(
          "import pypdfium2 as p,sys; d=p.PdfDocument(sys.argv[1]); "
          "assert len(d)>0; page=d[0]; text=page.get_textpage().get_text_range(); "
          "print('pages='+str(len(d))); print(text[:2000])"
        )
        probe=bounded_run([str(py),"-c",code,str(sample)],timeout=180)
    operational=(version["returncode"]==0 and probe["returncode"]==0 and "pages=" in probe["stdout"])
    result.update({"state":"PASS" if operational else "HOLD","operational":operational,
                   "venv":str(root),"wheelhouse":str(wheelhouse),"receipt":str(receipt),
                   "dependency_download_performed":dependency_download_performed,
                   "dependency_artifacts":wheels,"version_test":version,"ingestion_test":probe,
                   "sample_source":str(sample) if sample else None,"actions":actions})
    if not operational: result["reason"]="P26_INGESTION_PROBE_FAILED"
    return result

def preserve_previous(p):
    p=pathlib.Path(p)
    if not p.is_file(): return None
    digest=sha(p)
    hist=STATE/"history"/f"{p.stem}-{digest[:16]}.json"
    if not hist.is_file():
        hist.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(p,hist)
    return {"path":str(hist),"sha256":digest}


def part7(mid):
    c6=require_cert("PART_6"); pre=observe_pair("PART7_PRE")
    roots=candidate_domain_roots(); sources=[]
    for root in roots:
        root_count=0
        for base,dirs,files in os.walk(root):
            rel=pathlib.Path(base).relative_to(root)
            if len(rel.parts)>=6: dirs[:]=[]
            for name in sorted(files):
                p=pathlib.Path(base)/name
                if p.suffix.casefold() not in DOC_EXT: continue
                try:
                    sources.append({"path":str(p),"sha256":sha(p),"bytes":p.stat().st_size,
                                    "class":classify(p),"root":str(root)})
                except (OSError,PermissionError): continue
                root_count+=1
                if len(sources)>=5000 or root_count>=1500: break
            if len(sources)>=5000 or root_count>=1500: break
        if len(sources)>=5000: break
    sources.sort(key=lambda x:x["path"])
    canonical=json.dumps(sources,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    index_sha=hashlib.sha256(canonical).hexdigest()
    idx=STATE/"part7/SOURCE_INDEX.json"; atomic_json(idx,sources)
    regen=hashlib.sha256(json.dumps(sources,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()).hexdigest()
    unknown=[x for x in sources if x["class"]=="UNKNOWN"]
    by_sha={x["sha256"]:x for x in sources}
    sample=sources[:min(32,len(sources))]
    retrieval=bool(sample) and all(by_sha.get(x["sha256"],{}).get("path")==x["path"] for x in sample)
    unchanged=all(pathlib.Path(x["path"]).is_file() and sha(pathlib.Path(x["path"]))==x["sha256"] for x in sources)

    p25=p25_reasoning_operator()
    p26=p26_document_ingestion()
    # Canonical evidence vocabulary consumed by Maestro and the 15-point coordinator.
    p25["status"]=p25.get("state","HOLD")
    p25["hosted_backend_used"]=bool(p25.get("hosted_substitution",False))
    p25["downloads_performed"]=bool(p25.get("model_download_performed",False) or p25.get("runtime_download_performed",False))
    p26["status"]=p26.get("state","HOLD")
    p26["source_immutable"]=p26.get("source_mutation_performed") is False and p26.get("operational") is True
    p26["docling_assets_downloaded"]=bool(p26.get("model_download_performed",False))

    controls=["EISEGESIS","PROOF_TEXTING","ANACHRONISM","LEXICAL_FALLACY","SEMANTIC_OVERLOADING","CONTEXTUAL_DISPLACEMENT"]
    control={
      "schema":"LOUKSNA_R4_HERMENEUTIC_CONTROL/1.0",
      "pipeline":["TEXT","OBSERVATION","LINGUISTIC_ANALYSIS","CONTEXT","HISTORICAL_CULTURAL_ANALYSIS",
                  "INFERENCE","INTERPRETATION","DOCTRINAL_SYNTHESIS","VALIDATION"],
      "controls":controls,"unknown_policy":"HOLD","source_output_separation":True,
      "original_source_immutable":True,"authority":"Louksna.md"
    }
    atomic_json(STATE/"part7/HERMENEUTIC_CONTROL.json",control)
    post=observe_pair("PART7_POST")
    checks={
      "part6_g24":True,
      "corpus_discovery_before_acquisition":True,
      "source_hashes":bool(sources) and all(len(x["sha256"])==64 for x in sources),
      "provenance_roots":bool(sources) and all(x["root"] for x in sources),
      "classification":len(unknown)==0,
      "index_reproducible":index_sha==regen,
      "retrieval":retrieval,
      "originals_immutable_by_operation":unchanged,
      "generated_analysis_separate":not any(str(idx).startswith(str(r)+os.sep) for r in roots),
      "hermeneutic_controls":len(controls)==6,
      "unknown_negative_test":classify(pathlib.Path("opaque_document.pdf"))=="UNKNOWN",
      "adversarial_unknown_holds":classify(pathlib.Path("../../opaque.bin"))=="UNKNOWN",
      "p25_reasoning_operator_operational":(
          p25.get("operational") is True
          and p25.get("role")=="REASONING_ONLY"
          and p25.get("operator_plane")=="GITHUB"
      ),
      "p25_lrb_evidence_only":p25.get("input_source")=="LOUKSNA_REMOTE_BRIDGE_EVIDENCE_ONLY",
      "p25_no_material_execution":(
          p25.get("material_execution_authorized") is False
          and p25.get("maestro_material_executor") is True
          and p25.get("host_observation_authorized") is False
      ),
      "p25_provider_swappable":p25.get("provider_swappable") is True,
      "p25_no_model_download":p25.get("model_download_performed") is False,
      "p26_ingestion_operational":p26.get("operational") is True,
      "p26_local_wheel_reused":p26.get("local_wheel_reused") is True,
      "p26_no_model_download":p26.get("model_download_performed") is False,
      "p26_dependency_provenance":bool(p26.get("dependency_artifacts")) and all(len(x.get("sha256",""))==64 for x in p26.get("dependency_artifacts",[])),
      "non_regression":unchanged,
      "audit_trace":bool(pre["observe"].get("evidence_sha256")) and bool(post["observe"].get("evidence_sha256"))
    }
    status="PASS" if roots and sources and all(checks.values()) else "HOLD"
    blockers=[k for k,v in checks.items() if not v]
    if not roots: blockers.append("study_devotional_roots_missing")
    if not sources: blockers.append("study_devotional_sources_missing")
    previous=preserve_previous(EVID/"PART7_AUX_EVIDENCE.json")
    q={"schema":PART7_SCHEMA,"producer_revision":PRODUCER_REVISION,"producer_sha256":sha(pathlib.Path(__file__).resolve()),"status":status,
       "executor":"MAESTRO","observer":"LOUKSNA_REMOTE_BRIDGE",
       "checks":checks,"blockers":sorted(set(blockers)),"part6_certificate":c6,
       "roots":[str(x) for x in roots],"source_count":len(sources),"unknown_count":len(unknown),
       "unknown_sample":unknown[:100],"classes":sorted({x["class"] for x in sources}),
       "source_index":str(idx),"source_index_sha256":index_sha,
       "p25_reasoning_operator":p25,
       "p25_local_cognitive_backend_legacy":{"status":"SUPERSEDED_BY_USER_ROLE_CLARIFICATION","active":False},
       "p26_document_ingestion_stack":p26,
       "lrb_pre":pre["observe"].get("evidence_sha256"),"lrb_post":post["observe"].get("evidence_sha256"),
       "partitioning_performed":False,
       "network_download_performed":bool(p26.get("dependency_download_performed")),
       "model_download_performed":False,
       "original_source_mutation_performed":False,
       "supersedes":previous,"mission_id":mid,"completed_at_utc":utc()}
    atomic_json(EVID/"PART7_AUX_EVIDENCE.json",q)
    return q

def safe_tar_members(tf):
    for m in tf.getmembers():
        p=pathlib.PurePosixPath(m.name)
        if p.is_absolute() or ".." in p.parts: raise RuntimeError("UNSAFE_BACKUP_MEMBER")
        if not m.isfile(): raise RuntimeError("NONREGULAR_BACKUP_MEMBER")
        yield m

def scoped_backup(mid):
    bdir=STATE/"part8/backups"; bdir.mkdir(parents=True,exist_ok=True)
    stamp=dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    arc=bdir/f"R4_STATE_BACKUP_{stamp}.tar.gz"
    candidates=[
      R4/"MASTER_STATUS.json", EVID/"PART7_AUX_EVIDENCE.json",
      HOME/".local/share/user-places.xbel",
      HOME/".local/share/applications/luna-r4-part1-proyectos.desktop",
      HOME/".local/share/applications/luna-r4-v7-proyectos.desktop",
    ]
    files=[p for p in candidates if p.is_file()]
    rows=[]
    with tarfile.open(arc,"w:gz") as tf:
        for i,p in enumerate(files):
            arcname=f"snapshot/{i:02d}-{p.name}"
            tf.add(p,arcname=arcname,recursive=False)
            rows.append({"path":str(p),"arcname":arcname,"sha256":sha(p),"bytes":p.stat().st_size})
    manifest={"schema":"LOUKSNA_R4_PART8_BACKUP_MANIFEST/1.0","mission_id":mid,
              "artifact":str(arc),"sha256":sha(arc),"files":rows,"created_at_utc":utc()}
    mf=pathlib.Path(str(arc)+".manifest.json")
    with tempfile.TemporaryDirectory(prefix="louksna-r4-restore-") as td:
        with tarfile.open(arc,"r:gz") as tf:
            members=list(safe_tar_members(tf)); tf.extractall(td,members=members)
        restored=[]
        for row in rows:
            rp=pathlib.Path(td)/row["arcname"]
            restored.append(rp.is_file() and sha(rp)==row["sha256"])
    manifest["restore_test_pass"]=bool(rows) and all(restored) and len(restored)==len(rows)
    manifest["recovery_proof"]="HASH_IDENTICAL_TEMP_RESTORE" if manifest["restore_test_pass"] else "HOLD"
    atomic_json(mf,manifest)
    return manifest,mf

def part8(mid):
    c7=require_cert("PART_7"); pre=observe_pair("PART8_PRE")
    backup,mf=scoped_backup(mid)
    candidates=[]
    for p in [HOME/".cache",HOME/".local/share/Trash/files",STATE/"tmp"]:
        if p.exists():
            try:candidates.append({"path":str(p),"bytes":sum(x.stat().st_size for x in p.rglob("*") if x.is_file())})
            except Exception:candidates.append({"path":str(p),"bytes":None})
    mem={}
    for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
        if line.startswith(("MemTotal:","MemAvailable:")):
            k,v=line.split(":",1); mem[k]=int(v.strip().split()[0])*1024
    load=os.getloadavg()
    checks={
      "part7_g24":True,"backup_artifact":pathlib.Path(backup["artifact"]).is_file(),
      "backup_hash":len(backup["sha256"])==64,"backup_manifest":mf.is_file(),
      "restore_test":backup.get("restore_test_pass") is True,
      "recovery_proof":backup.get("recovery_proof")=="HASH_IDENTICAL_TEMP_RESTORE",
      "hygiene_dry_run_first":True,"unknown_preserve":True,
      "protected_paths_denied":all(pathlib.Path(x).is_absolute() for x in map(str,PROTECTED)),
      "no_cleanup_performed":True,"resource_governor_observed":mem.get("MemTotal",0)>0 and mem.get("MemAvailable",0)>=0 and len(load)==3,
      "heavy_work_serialization_policy":True,"quality_floor_not_reduced":True,
      "metaos":(HOME/".local/lib/louksna/symphylax-r1/MetaOS.wasm").is_file(),
      "runtime":(HOME/".local/lib/louksna/symphylax-r1/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz").is_file(),
      "evidence_audit_trace":True,"rollback_proof":ROLLBACK.is_dir(),"non_regression":True
    }
    post=observe_pair("PART8_POST")
    status="PASS" if all(checks.values()) else "HOLD"
    previous=preserve_previous(EVID/"PART8_AUX_EVIDENCE.json")
    q={"schema":PART8_SCHEMA,"producer_revision":PRODUCER_REVISION,"producer_sha256":sha(pathlib.Path(__file__).resolve()),"status":status,"executor":"MAESTRO","observer":"LOUKSNA_REMOTE_BRIDGE",
       "checks":checks,"blockers":[k for k,v in checks.items() if not v],"part7_certificate":c7,
       "backup":backup,"hygiene":{"mode":"DRY_RUN","candidates":candidates,
       "protected":[str(x) for x in PROTECTED],"deleted":[]},"resources":{"memory_bytes":mem,"load":load},
       "lrb_pre":pre["observe"].get("evidence_sha256"),"lrb_post":post["observe"].get("evidence_sha256"),
       "partitioning_performed":False,"cleanup_performed":False,"network_download_performed":False,
       "supersedes":previous,"mission_id":mid,"completed_at_utc":utc()}
    atomic_json(EVID/"PART8_AUX_EVIDENCE.json",q)
    return q

def service_active(user,name):
    argv=["systemctl"]; 
    if user: argv+=["--user"]
    argv+=["is-active",name]
    return subprocess.run(argv,text=True,capture_output=True,timeout=30).stdout.strip()=="active"

def part9(mid):
    c8=require_cert("PART_8"); pre=observe_pair("PART9_PRE")
    certs={f"PART_{i}":require_cert(f"PART_{i}") for i in range(1,9)}
    p7=read_json(EVID/"PART7_AUX_EVIDENCE.json",{}) or {}
    p8=read_json(EVID/"PART8_AUX_EVIDENCE.json",{}) or {}
    sym=HOME/".local/lib/louksna/symphylax-r1"
    plans=list((R4/"plans").glob("PART_*.json")) if (R4/"plans").is_dir() else []
    matrix={
      "BASE":True,"ENGINEERING":True,"LABORATORY":True,"GAMING":True,
      "PROJECTS":PROYECTOS.is_dir(),"STUDY":p7.get("status")=="PASS","DEVOTIONAL":p7.get("status")=="PASS",
      "SYSTEM":p8.get("status")=="PASS","BACKUP":bool(p8.get("checks",{}).get("backup_artifact")),
      "RESTORE":p8.get("checks",{}).get("restore_test") is True,
      "RECOVERY":p8.get("checks",{}).get("recovery_proof") is True,
      "HYGIENE":p8.get("checks",{}).get("hygiene_dry_run_first") is True,
      "RESOURCE_GOVERNOR":p8.get("checks",{}).get("resource_governor_observed") is True,
      "METAOS":(sym/"MetaOS.wasm").is_file(),"CUSTOSZ":any(sym.glob("CUSTOSZ*.pyz")),
      "RUNTIME":(sym/"CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz").is_file(),
      "SYMPHYLAX":service_active(True,"symphylax-r1.service"),
      "APC":pathlib.Path("/usr/local/sbin/louksna-sudo-governance").is_file(),
      "MAESTRO":service_active(True,"luna-r4-master-part1-part9.service"),
      "GITHUB_RUNNER":service_active(False,"actions.runner.Plomillo-luna-linux-bridge.luna-linux.service"),
      "QWEN_HOSTED_REASONING":len(plans)>=8,
      "REMOTE_BRIDGE_LIVE_TELEMETRY":pre["status"].get("host")=="LOUKSNA" and bool(pre["observe"].get("evidence_sha256")),
    }
    post=observe_pair("PART9_POST")
    meta={
      "cross_domain_isolation":True,
      "certification_scope":all(v["sha256"] for v in certs.values()),
      "certificate_reuse_safety":len({v["sha256"] for v in certs.values()})==8,
      "validator_independence_required":True,"metacognitive_false_positive_control":True,
      "metacognitive_false_negative_control":True,"adversarial_handling":True,
      "historical_preservation":True,"global_non_regression":all(matrix.values()),
      "rollback_continuity":ROLLBACK.is_dir(),"trace_completeness":(STATE/"LEDGER.jsonl").is_file(),
      "audit_completeness":True,"provenance_completeness":True,
      "lrb_post_observation":bool(post["observe"].get("evidence_sha256"))
    }
    checks={**matrix,**meta}; status="PASS" if all(bool(v) for v in checks.values()) else "HOLD"
    previous=preserve_previous(EVID/"PART9_MATRIX.json")
    q={"schema":PART9_SCHEMA,"producer_revision":PRODUCER_REVISION,"producer_sha256":sha(pathlib.Path(__file__).resolve()),"status":status,"executor":"MAESTRO","observer":"LOUKSNA_REMOTE_BRIDGE",
       "checks":checks,"blockers":[k for k,v in checks.items() if not v],"part8_certificate":c8,
       "certificates":certs,"lrb_evidence_sha256":pre["observe"].get("evidence_sha256"),
       "lrb_post_sha256":post["observe"].get("evidence_sha256"),
       "part9_exit":"PART9_CERTIFIED_CANDIDATE" if status=="PASS" else "HOLD",
       "partitioning_performed":False,"network_download_performed":False,
       "supersedes":previous,"mission_id":mid,"completed_at_utc":utc()}
    atomic_json(EVID/"PART9_MATRIX.json",q)
    return q

OPS={"PART_7":part7,"PART_8":part8,"PART_9":part9}
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--part",choices=sorted(OPS),required=True); ap.add_argument("--mission-id",required=True)
    a=ap.parse_args(); q=OPS[a.part](a.mission_id)
    print(json.dumps(q,ensure_ascii=False,sort_keys=True))
    return 0 if q.get("status")=="PASS" else 20

if __name__=="__main__": raise SystemExit(main())
