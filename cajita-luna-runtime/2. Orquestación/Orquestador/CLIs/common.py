from __future__ import annotations
import hashlib, os, shutil, subprocess, time
from pathlib import Path

def sha256_file(path):
    h=hashlib.sha256()
    try:
        with Path(path).open("rb") as f:
            for block in iter(lambda:f.read(1024*1024), b""): h.update(block)
        return h.hexdigest()
    except OSError: return None

def probe_version(binary, argv, timeout_seconds=20, input_text=None):
    env=os.environ.copy()
    resolved=shutil.which(binary, path=env.get("PATH"))
    if not resolved:
        return {"binary":binary,"argv":list(argv),"status":"ABSENT","reason":"EXECUTABLE_NOT_FOUND","shell":False,"mutations_performed":False}
    started=time.monotonic()
    kwargs={"stdout":subprocess.PIPE,"stderr":subprocess.PIPE,"text":True,"timeout":max(1,min(int(timeout_seconds),60)),"shell":False,"env":env,"check":False}
    kwargs["stdin"]=subprocess.DEVNULL if input_text is None else None
    if input_text is not None: kwargs["input"]=input_text
    try:
        p=subprocess.run([resolved,*list(argv)],**kwargs)
        return {"binary":binary,"resolved_path":resolved,"binary_sha256":sha256_file(resolved),"argv":list(argv),"returncode":p.returncode,"status":"PASS" if p.returncode==0 else "NONZERO_EXIT","stdout":(p.stdout or "")[:1200],"stderr":(p.stderr or "")[:800],"elapsed_seconds":round(time.monotonic()-started,3),"shell":False,"mutations_performed":False}
    except subprocess.TimeoutExpired:
        return {"binary":binary,"resolved_path":resolved,"argv":list(argv),"status":"TIMEOUT","elapsed_seconds":round(time.monotonic()-started,3),"shell":False,"mutations_performed":False}
    except OSError as e:
        return {"binary":binary,"resolved_path":resolved,"argv":list(argv),"status":"EXECUTION_ERROR","error_type":type(e).__name__,"shell":False,"mutations_performed":False}

def probe_domain(domain_id,candidates,official_source_verified=True):
    rows=[]
    for binary,argv,required in candidates:
        row=probe_version(binary,argv); row["required"]=bool(required); rows.append(row)
    required=[r for r in rows if r.get("required")]
    if not official_source_verified: status="BLOCKED_OFFICIAL_DISTRIBUTION_UNVERIFIED"
    elif required and all(r["status"]=="PASS" for r in required): status="AVAILABLE"
    elif any(r["status"] not in {"ABSENT"} for r in rows): status="PARTIAL"
    else: status="ABSENT"
    return {"domain_id":domain_id,"status":status,"probes":rows,"read_only":True,"mutations_performed":False,"certification":"NOT_GRANTED"}
