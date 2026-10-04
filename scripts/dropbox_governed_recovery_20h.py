#!/usr/bin/env python3
from __future__ import annotations
import os, sys, json, time, hashlib, pathlib, subprocess, shutil, urllib.request, urllib.error, urllib.parse, zipfile, tempfile, re

MISSION_ID=os.environ.get("MISSION_ID","DROPBOX_MAIN_GOVERNED_RECOVERY_20H_20261004")
SHARED_LINK=os.environ.get("DROPBOX_SHARED_LINK","")
TARGET_NAME=os.environ.get("TARGET_NAME","1. PROYECTOS PRIORITARIOS")
HARD_CEILING=int(os.environ.get("HARD_CEILING_SECONDS","72000"))
START=time.time()
DEADLINE=START+HARD_CEILING
HOME=pathlib.Path.home()
STATE=pathlib.Path(os.environ.get("STATE_ROOT", str(HOME/".local/state/louksna/dropbox-main-governed-recovery-20h")))
CORPUS=pathlib.Path(os.environ.get("CORPUS_ROOT", str(HOME/".local/share/louksna/dropbox-main-governed-recovery-20h/corpus")))
EVID=STATE/"evidence"
LEDGER=EVID/"LEDGER.jsonl"
HEAD=EVID/"LEDGER_HEAD.json"
KNOWLEDGE=EVID/"KNOWLEDGE_EVENTS.jsonl"
STATUS=EVID/"STATUS.json"
EXPECTED=EVID/"EXPECTED_OBJECTS.json"
MANIFEST=EVID/"MATERIALIZED_MANIFEST.json"

for p in (STATE,EVID,CORPUS): p.mkdir(parents=True, exist_ok=True)

def utc():
    import datetime as dt
    return dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z")

def sha_bytes(b:bytes)->str: return hashlib.sha256(b).hexdigest()

def sha_file(p:pathlib.Path)->str:
    h=hashlib.sha256()
    with p.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def atomic(path, obj):
    path=pathlib.Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    os.replace(tmp,path)

def event(kind, **payload):
    prev=None
    if HEAD.exists():
        try: prev=json.loads(HEAD.read_text()).get("sha256")
        except Exception: pass
    row={"schema":"LOUKSNA_DROPBOX_EVENT/1.0","mission_id":MISSION_ID,"utc":utc(),"event":kind,
         "previous_event_sha256":prev,**payload}
    raw=json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode()
    row["event_sha256"]=sha_bytes(raw)
    with LEDGER.open("a",encoding="utf-8") as f:
        f.write(json.dumps(row,ensure_ascii=False,sort_keys=True)+"\n"); f.flush(); os.fsync(f.fileno())
    atomic(HEAD,{"sha256":row["event_sha256"],"event":kind,"utc":row["utc"]})
    with KNOWLEDGE.open("a",encoding="utf-8") as f:
        f.write(json.dumps({"schema":"KNOWLEDGE_EVENT/1.0","authority":"Louksna.md",
                            "marklogic_binding":"KNOWLEDGE_OPERATOR_COOPERATION_SCOPE_ONLY",
                            "qwen_role":"REASONING_ONLY","metaos_role":"OPERATIONAL_GOVERNOR",
                            **row},ensure_ascii=False,sort_keys=True)+"\n")
    return row

def run(argv, timeout=300, env=None):
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,env=env)
    return {"argv":[str(x) for x in argv],"returncode":p.returncode,
            "stdout":p.stdout[-12000:],"stderr":p.stderr[-12000:]}

def left():
    return max(0,int(DEADLINE-time.time()))

def check_deadline():
    if time.time()>=DEADLINE:
        event("HARD_CEILING_REACHED",hard_ceiling_seconds=HARD_CEILING)
        atomic(STATUS,{"state":"HOLD","reason":"HARD_CEILING_REACHED","mission_id":MISSION_ID,"utc":utc()})
        raise SystemExit(124)

def safe_rel(name):
    name=name.replace("\\","/").lstrip("/")
    parts=[p for p in name.split("/") if p not in ("",".","..")]
    return pathlib.Path(*parts)

def manifest_tree(root:pathlib.Path):
    rows=[]; total=0
    for p in sorted(x for x in root.rglob("*") if x.is_file()):
        rel=p.relative_to(root).as_posix()
        if rel.endswith(".louksna.part"): continue
        s=p.stat().st_size; total+=s
        rows.append({"path":rel,"size":s,"sha256":sha_file(p)})
    obj={"schema":"LOUKSNA_ACQUIRED_CORPUS_MANIFEST/1.0","mission_id":MISSION_ID,
         "authority":"Louksna.md","root":str(root),"object_count":len(rows),
         "bytes":total,"objects":rows,"utc":utc()}
    obj["manifest_sha256"]=sha_bytes(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())
    return obj

def provider_rclone():
    check_deadline()
    exe=shutil.which("rclone")
    if not exe:
        event("PROVIDER_RCLONE_UNAVAILABLE",reason="BINARY_MISSING")
        return False
    red=run([exe,"config","redacted"],timeout=60)
    if red["returncode"]!=0:
        event("PROVIDER_RCLONE_UNAVAILABLE",reason="CONFIG_REDACTED_FAILED",rc=red["returncode"])
        return False
    remotes=[]; current=None; typ=None
    for line in red["stdout"].splitlines():
        m=re.match(r"^\[([^\]]+)\]\s*$",line.strip())
        if m:
            if current and typ=="dropbox": remotes.append(current)
            current=m.group(1); typ=None; continue
        if current and line.strip().lower().startswith("type"):
            typ=line.split("=",1)[-1].strip().lower()
    if current and typ=="dropbox": remotes.append(current)
    event("RCLONE_DROPBOX_REMOTES_DISCOVERED",count=len(remotes),remotes=remotes)
    for remote in remotes:
        check_deadline()
        src=f"{remote}:{TARGET_NAME}"
        probe=run([exe,"lsf",src,"--max-depth","1"],timeout=120)
        if probe["returncode"]!=0:
            event("RCLONE_TARGET_NOT_RESOLVED",remote=remote,rc=probe["returncode"])
            continue
        expected_run=run([exe,"lsjson",src,"--recursive","--files-only"],timeout=min(900,max(60,left())))
        if expected_run["returncode"]==0:
            try:
                xs=json.loads(expected_run["stdout"])
                expected=[{"path":x.get("Path"),"size":x.get("Size"),"hashes":x.get("Hashes",{})} for x in xs]
                atomic(EXPECTED,{"provider":"RCLONE_DROPBOX","remote":remote,"count":len(expected),
                                 "bytes":sum(int(x.get("size") or 0) for x in expected),"objects":expected,"utc":utc()})
                event("EXPECTED_MANIFEST_CREATED",provider="RCLONE_DROPBOX",count=len(expected))
            except Exception as e:
                event("EXPECTED_MANIFEST_PARSE_FAILED",provider="RCLONE_DROPBOX",error=type(e).__name__)
        args=[exe,"copy",src,str(CORPUS),"--create-empty-src-dirs","--partial-suffix",".louksna.part",
              "--retries","5","--low-level-retries","10","--transfers","8","--checkers","16",
              "--stats","60s","--stats-one-line","--metadata"]
        event("RCLONE_COPY_START",remote=remote,source=src,remaining_seconds=left())
        rr=run(args,timeout=max(300,left()))
        event("RCLONE_COPY_END",remote=remote,rc=rr["returncode"],
              stdout_tail=rr["stdout"][-3000:],stderr_tail=rr["stderr"][-3000:])
        if rr["returncode"]==0:
            atomic(STATUS,{"state":"ACQUIRED_PENDING_COMPLETENESS","provider":"RCLONE_DROPBOX","utc":utc()})
            return True
    return False

def api_post(url, token, payload, content=False):
    data=json.dumps(payload,separators=(",",":")).encode()
    req=urllib.request.Request(url,data=data,method="POST",headers={
        "Authorization":"Bearer "+token,
        "Content-Type":"application/json",
        "User-Agent":"LouksnaDropboxRecovery/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r:
        return json.loads(r.read())

def provider_dropbox_api():
    check_deadline()
    token=os.environ.get("DROPBOX_ACCESS_TOKEN","").strip()
    if not token:
        event("PROVIDER_DROPBOX_API_UNAVAILABLE",reason="TOKEN_NOT_BOUND")
        return False
    event("PROVIDER_DROPBOX_API_START",token_present=True,token_logged=False)
    queue=[""]; files=[]; seen=set()
    try:
        while queue:
            check_deadline()
            rel=queue.pop(0)
            if rel in seen: continue
            seen.add(rel)
            payload={"path":rel,"recursive":False,"include_deleted":False,
                     "shared_link":{"url":SHARED_LINK},"limit":2000}
            d=api_post("https://api.dropboxapi.com/2/files/list_folder",token,payload)
            while True:
                for x in d.get("entries",[]):
                    tag=x.get(".tag")
                    p=x.get("path_display") or x.get("path_lower") or x.get("name")
                    if tag=="folder": queue.append(p)
                    elif tag=="file":
                        files.append({"path":p,"size":int(x.get("size") or 0),
                                      "id":x.get("id"),"rev":x.get("rev"),
                                      "content_hash":x.get("content_hash")})
                if not d.get("has_more"): break
                d=api_post("https://api.dropboxapi.com/2/files/list_folder/continue",token,{"cursor":d["cursor"]})
        if not files:
            event("DROPBOX_API_ENUMERATION_EMPTY")
            return False
        atomic(EXPECTED,{"provider":"DROPBOX_API_SHARED_LINK","count":len(files),
                         "bytes":sum(x["size"] for x in files),"objects":files,"utc":utc()})
        event("EXPECTED_MANIFEST_CREATED",provider="DROPBOX_API_SHARED_LINK",
              count=len(files),bytes=sum(x["size"] for x in files))
        for idx,x in enumerate(files,1):
            check_deadline()
            rel=safe_rel(x["path"])
            dest=CORPUS/rel; dest.parent.mkdir(parents=True,exist_ok=True)
            if dest.is_file() and dest.stat().st_size==x["size"]:
                if x.get("content_hash"):
                    # Dropbox content_hash is not SHA-256; size+later manifest remains independently recorded.
                    event("API_OBJECT_REUSE_EXISTING",path=rel.as_posix(),size=x["size"],ordinal=idx)
                    continue
            tmp=dest.with_suffix(dest.suffix+".louksna.part")
            arg={"url":SHARED_LINK,"path":x["path"]}
            req=urllib.request.Request("https://content.dropboxapi.com/2/sharing/get_shared_link_file",
                data=b"",method="POST",headers={
                    "Authorization":"Bearer "+token,
                    "Dropbox-API-Arg":json.dumps(arg,separators=(",",":")),
                    "User-Agent":"LouksnaDropboxRecovery/1.0"})
            with urllib.request.urlopen(req,timeout=300) as r, tmp.open("wb") as f:
                while True:
                    b=r.read(1024*1024)
                    if not b: break
                    f.write(b)
            if tmp.stat().st_size!=x["size"]:
                event("API_OBJECT_SIZE_MISMATCH",path=rel.as_posix(),expected=x["size"],actual=tmp.stat().st_size)
                return False
            os.replace(tmp,dest)
            event("API_OBJECT_ACQUIRED",path=rel.as_posix(),size=x["size"],ordinal=idx,total=len(files))
        atomic(STATUS,{"state":"ACQUIRED_PENDING_COMPLETENESS","provider":"DROPBOX_API_SHARED_LINK","utc":utc()})
        return True
    except Exception as e:
        event("PROVIDER_DROPBOX_API_FAILED",error=type(e).__name__,message=str(e)[:1000])
        return False

def browser_download_candidate():
    check_deadline()
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        event("PLAYWRIGHT_NOT_INSTALLED")
        return False
    dl_dir=STATE/"browser-downloads"; dl_dir.mkdir(parents=True,exist_ok=True)
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            page=browser.new_page(accept_downloads=True)
            page.goto(SHARED_LINK,wait_until="domcontentloaded",timeout=120000)
            event("BROWSER_PAGE_LOADED",title=page.title()[:300],url=page.url)
            for txt in ("Accept","Aceptar","Accept all","Aceptar todas"):
                try:
                    loc=page.get_by_text(txt,exact=True)
                    if loc.count(): loc.first.click(timeout=2000)
                except Exception: pass
            candidates=[
                page.get_by_role("button",name=re.compile("download",re.I)),
                page.get_by_text(re.compile("^Download$",re.I)),
                page.get_by_text(re.compile("^Descargar$",re.I)),
            ]
            got=None
            for loc in candidates:
                try:
                    if not loc.count(): continue
                    with page.expect_download(timeout=30000) as di:
                        loc.first.click()
                    got=di.value; break
                except Exception:
                    continue
            if got is None:
                # Some Dropbox folder UIs expose a menu first.
                for name in ("Download","Descargar"):
                    try:
                        loc=page.get_by_text(name,exact=False)
                        if not loc.count(): continue
                        with page.expect_download(timeout=30000) as di:
                            loc.last.click()
                        got=di.value; break
                    except Exception: continue
            if got is None:
                browser.close(); event("BROWSER_DOWNLOAD_NOT_STARTED"); return False
            path=dl_dir/(got.suggested_filename or "dropbox-folder.zip")
            got.save_as(str(path)); browser.close()
        event("BROWSER_DOWNLOAD_SAVED",path=str(path),size=path.stat().st_size)
        if not zipfile.is_zipfile(path):
            event("BROWSER_DOWNLOAD_NOT_ZIP",size=path.stat().st_size,sha256=sha_file(path)); return False
        with zipfile.ZipFile(path) as z:
            bad=z.testzip()
            if bad:
                event("BROWSER_ZIP_CRC_FAIL",member=bad); return False
            names=z.namelist()
            for n in names:
                q=safe_rel(n)
                if str(q) in ("","."): continue
                dest=CORPUS/q
                if n.endswith("/"): dest.mkdir(parents=True,exist_ok=True); continue
                dest.parent.mkdir(parents=True,exist_ok=True)
                with z.open(n) as src, dest.with_suffix(dest.suffix+".louksna.part").open("wb") as out:
                    shutil.copyfileobj(src,out,1024*1024)
                os.replace(dest.with_suffix(dest.suffix+".louksna.part"),dest)
            atomic(EXPECTED,{"provider":"DROPBOX_BROWSER_PACKAGE","package_sha256":sha_file(path),
                             "package_size":path.stat().st_size,"zip_members":len(names),
                             "completeness_basis":"DROPBOX_GENERATED_PACKAGE_INTERNAL_MANIFEST_ONLY","utc":utc()})
        atomic(STATUS,{"state":"ACQUIRED_PENDING_COMPLETENESS","provider":"DROPBOX_BROWSER_PACKAGE","utc":utc()})
        return True
    except Exception as e:
        event("PROVIDER_BROWSER_FAILED",error=type(e).__name__,message=str(e)[:1000])
        return False

def completeness():
    check_deadline()
    actual=manifest_tree(CORPUS); atomic(MANIFEST,actual)
    exp={}
    if EXPECTED.exists():
        try: exp=json.loads(EXPECTED.read_text())
        except Exception: pass
    provider=exp.get("provider")
    if provider in ("DROPBOX_API_SHARED_LINK","RCLONE_DROPBOX"):
        objs=exp.get("objects",[])
        expected_count=int(exp.get("count") or len(objs))
        expected_bytes=int(exp.get("bytes") or 0)
        actual_map={x["path"].lower().lstrip("/"):x for x in actual["objects"]}
        missing=[]
        for x in objs:
            p=str(x.get("path") or "").lower().lstrip("/")
            if p and p not in actual_map: missing.append(p)
        byte_match=(expected_bytes==actual["bytes"]) if expected_bytes else None
        ok=(not missing and actual["object_count"]==expected_count and (byte_match is not False))
        result={"provider":provider,"expected_count":expected_count,"actual_count":actual["object_count"],
                "expected_bytes":expected_bytes,"actual_bytes":actual["bytes"],"missing":missing[:1000],
                "missing_count":len(missing),"byte_match":byte_match,"status":"PASS" if ok else "FAIL",
                "basis":"SOURCE_ENUMERATION_VS_MATERIALIZED"}
    elif provider=="DROPBOX_BROWSER_PACKAGE":
        result={"provider":provider,"actual_count":actual["object_count"],"actual_bytes":actual["bytes"],
                "status":"PASS_PACKAGE_INTERNAL_ONLY","basis":"DROPBOX_GENERATED_ZIP_CRC_AND_MEMBER_EXTRACTION",
                "source_enumeration_independently_proven":False}
        ok=True
    else:
        result={"provider":provider or "UNKNOWN","status":"FAIL","reason":"EXPECTED_MANIFEST_MISSING_OR_UNKNOWN"}
        ok=False
    atomic(EVID/"COMPLETENESS.json",result)
    event("COMPLETENESS_EVALUATED",**{k:v for k,v in result.items() if k!="missing"})
    return ok,result,actual

def main():
    if not SHARED_LINK:
        raise SystemExit("DROPBOX_SHARED_LINK_REQUIRED")
    event("MISSION_START",authority="Louksna.md",assurance="PUAC2.md",
          target=TARGET_NAME,hard_ceiling_seconds=HARD_CEILING,
          old_7z_policy="IGNORED_NOT_INPUT",custosz_before_complete=False,
          main_role=["TRUST_ROOT","RECOVERY_ROOT","ACQUISITION_ROOT","CONTINUITY_ROOT"])
    atomic(STATUS,{"state":"DISCOVER","mission_id":MISSION_ID,"utc":utc()})
    providers=[
        ("RCLONE_DROPBOX",provider_rclone),
        ("DROPBOX_API_SHARED_LINK",provider_dropbox_api),
        ("DROPBOX_BROWSER_PACKAGE",browser_download_candidate),
    ]
    acquired=False
    for name,fn in providers:
        check_deadline()
        event("PROVIDER_ATTEMPT_START",provider=name)
        try: ok=fn()
        except subprocess.TimeoutExpired:
            event("PROVIDER_ATTEMPT_TIMEOUT",provider=name); ok=False
        except Exception as e:
            event("PROVIDER_ATTEMPT_EXCEPTION",provider=name,error=type(e).__name__,message=str(e)[:1000]); ok=False
        event("PROVIDER_ATTEMPT_END",provider=name,status="PASS" if ok else "FAIL")
        if ok:
            acquired=True; break
    if not acquired:
        atomic(STATUS,{"state":"HOLD","reason":"ALL_CURRENT_PROVIDER_STRATEGIES_EXHAUSTED",
                       "next_authorized_action":"QWEN_DIAGNOSIS_OVER_EVIDENCE_THEN_METAOS_REPLAN",
                       "mission_id":MISSION_ID,"utc":utc()})
        event("MISSION_HOLD",reason="ALL_CURRENT_PROVIDER_STRATEGIES_EXHAUSTED")
        raise SystemExit(3)

    ok,result,actual=completeness()
    if not ok:
        atomic(STATUS,{"state":"HOLD","reason":"COMPLETENESS_GATE_FAILED",
                       "mission_id":MISSION_ID,"utc":utc()})
        event("MISSION_HOLD",reason="COMPLETENESS_GATE_FAILED")
        raise SystemExit(4)
    ready={
        "schema":"LOUKSNA_DROPBOX_READY_FOR_G23/1.0",
        "mission_id":MISSION_ID,
        "authority":"Louksna.md",
        "assurance":"PUAC2.md",
        "state":"READY_FOR_G23",
        "provider":result.get("provider"),
        "materialized_manifest_sha256":actual["manifest_sha256"],
        "object_count":actual["object_count"],
        "bytes":actual["bytes"],
        "provenance_evidence":str(LEDGER),
        "traceability_evidence":str(LEDGER),
        "custosz_audit_authorized":False,
        "reason":"G23_AND_G24_ACQUISITION_REQUIRED_BEFORE_CUSTOSZ",
        "utc":utc()
    }
    atomic(EVID/"READY_FOR_G23.json",ready)
    atomic(STATUS,{"state":"READY_FOR_G23","provider":result.get("provider"),"utc":utc()})
    event("ACQUISITION_READY_FOR_G23",provider=result.get("provider"),
          object_count=actual["object_count"],bytes=actual["bytes"],
          manifest_sha256=actual["manifest_sha256"])
    print(json.dumps(ready,sort_keys=True))

if __name__=="__main__":
    main()
