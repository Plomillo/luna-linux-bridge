#!/usr/bin/env python3
"""Synchronous governance helpers imported by traceable derivation from MAIN.

No network, no credentials, no repository writes, no privilege escalation.
These helpers preserve the exact patterns used by MAIN for digest binding,
checked subprocesses, atomic state writes, and supervisor heartbeats.
"""
from __future__ import annotations
import hashlib, json, os, subprocess, time
from datetime import datetime, timezone
from pathlib import Path

MAIN_SOURCE_SHA = "a7d430a7f9f94eb82c017bf62c3b456ca5b0cdf9"
MAIN_SOURCE_BLOBS = {
    ".github/workflows/document-factory-operational-authorization.yml": "c909d8cf82fa3c8cbae3d5a10033f111dada2c62",
    ".github/workflows/document-factory-exact-g24-activation-20261005.yml": "5874a880d6169e3bec8eee4c016eb6c0525e658f",
    "scripts/assurance/metacognitive_trust_root.py": "eb1a8034addb92927289bd9d6a9cf123990fe9fd",
    "scripts/missions/document_factory_ffprobe_dispatch.py": "0183c165eec646efcc164a1a01a30d20ca2bdb4b",
    "scripts/missions/document_factory_ffprobe_supervisor.py": "7d8ecfa250487588d8217b1ce62b274abcb0ffcd",
}

def utc() -> str:
    return datetime.now(timezone.utc).isoformat()

def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def sha256_file(path) -> str:
    return sha256_bytes(Path(path).read_bytes())

def canonical_sha256(obj) -> str:
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return sha256_bytes(raw)

def run_checked(argv, timeout=60, cwd=None) -> str:
    p=subprocess.run(argv,text=True,capture_output=True,timeout=timeout,cwd=cwd)
    if p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(argv)+"\n"+p.stdout[-3000:]+"\n"+p.stderr[-3000:])
    return p.stdout.strip()

def atomic_json(path, obj) -> None:
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_name(p.name+".tmp-"+str(os.getpid()))
    fd=os.open(str(tmp),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as f:
            json.dump(obj,f,ensure_ascii=False,indent=2,sort_keys=True)
            f.write("\n"); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
        dfd=os.open(str(p.parent),os.O_DIRECTORY)
        try: os.fsync(dfd)
        finally: os.close(dfd)
    finally:
        if tmp.exists(): tmp.unlink()

def verify_exact_authorization(record, expected_head, expected_digest, expected_scope):
    r=json.loads(Path(record).read_text(encoding="utf-8"))
    failures=[]
    if r.get("status")!="PASS": failures.append("STATUS_NOT_PASS")
    if r.get("candidate_head_sha")!=expected_head: failures.append("HEAD_MISMATCH")
    if r.get("candidate_digest_sha256")!=expected_digest: failures.append("DIGEST_MISMATCH")
    if r.get("scope")!=expected_scope: failures.append("SCOPE_MISMATCH")
    if r.get("certification_propagation") is not False: failures.append("CERT_PROPAGATION_INVALID")
    if r.get("canonical_mutation") is not False: failures.append("CANONICAL_MUTATION_INVALID")
    if r.get("active_authorized") is not True: failures.append("ACTIVE_AUTHORIZATION_MISSING")
    if failures:
        raise RuntimeError("AUTHORIZATION_FAIL_CLOSED:"+",".join(failures))
    return r

def write_heartbeat(path, state, sequence, pid, child_pid=None, elapsed_seconds=None):
    obj={
        "schema":"LOUKSNA_SYNC_SUPERVISOR_HEARTBEAT/1.0",
        "state":state,
        "sequence":int(sequence),
        "pid":int(pid),
        "child_pid":int(child_pid) if child_pid is not None else None,
        "elapsed_seconds":elapsed_seconds,
        "observed_at_utc":utc(),
    }
    atomic_json(path,obj)
    return obj

def supervise_process(argv, heartbeat_path, completion_path, timeout_seconds, cwd=None):
    started=time.monotonic()
    p=subprocess.Popen(argv,text=True,cwd=cwd)
    seq=0
    while True:
        code=p.poll(); seq+=1
        elapsed=round(time.monotonic()-started,3)
        write_heartbeat(heartbeat_path,"RUNNING" if code is None else "EXITED",seq,os.getpid(),p.pid,elapsed)
        if code is not None: break
        if elapsed>timeout_seconds:
            p.terminate()
            raise TimeoutError("SUPERVISOR_GLOBAL_TIMEOUT")
        time.sleep(1)
    result={
        "schema":"LOUKSNA_SYNC_SUPERVISOR_COMPLETION/1.0",
        "status":"PASS" if code==0 else "FAIL",
        "exit_code":code,
        "supervisor_pid":os.getpid(),
        "child_pid":p.pid,
        "elapsed_seconds":round(time.monotonic()-started,3),
        "completed_at_utc":utc(),
    }
    atomic_json(completion_path,result)
    return result

def selftest():
    assert len(MAIN_SOURCE_SHA)==40
    assert all(len(v)==40 for v in MAIN_SOURCE_BLOBS.values())
    probe={"b":2,"a":1}
    assert canonical_sha256(probe)==hashlib.sha256(b'{"a":1,"b":2}').hexdigest()
    return {"status":"PASS","main_source_sha":MAIN_SOURCE_SHA,"source_blob_count":len(MAIN_SOURCE_BLOBS)}

if __name__=="__main__":
    print(json.dumps(selftest(),sort_keys=True))
