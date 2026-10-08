#!/usr/bin/env python3
"""Governed, content-addressed artifact transfer substrate for Louksna V0.4 P05.

The implementation is deliberately local and deterministic: the transfer engine
does not grant network authority. It proves the transfer contract with an
isolated source/staging/store fixture and emits a tamper-evident evidence chain.
"""
from __future__ import annotations
import hashlib, json, mimetypes, os, sqlite3, stat, time
from pathlib import Path

SCHEMA="LOUKSNA_ZD_ARTIFACT_TRANSFER/1.0"
CHUNK=64*1024

class TransferDenied(RuntimeError):
    pass

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda:f.read(CHUNK),b""): h.update(block)
    return h.hexdigest()

def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()

def digest(obj):
    return hashlib.sha256(canonical(obj)).hexdigest()

def observed_mime(path:Path)->str:
    data=path.read_bytes()[:16]
    if data.startswith(b"\x89PNG\r\n\x1a\n"): return "image/png"
    if data.startswith(b"%PDF-"): return "application/pdf"
    if data.startswith(b"PK\x03\x04"): return "application/zip"
    return mimetypes.guess_type(path.name)[0] or "application/octet-stream"

def safe_name(name:str)->str:
    p=Path(name)
    if not name or p.is_absolute() or name.startswith("/") or ".." in p.parts or p.name!=name:
        raise TransferDenied("PATH_TRAVERSAL_DENIED")
    if "\x00" in name: raise TransferDenied("NUL_NAME_DENIED")
    return name

class Evidence:
    def __init__(self,path:Path):
        self.path=path
        self.prev="0"*64
        self.seq=0
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                if not line: continue
                rec=json.loads(line)
                body={k:v for k,v in rec.items() if k!="entry_hash"}
                if rec.get("seq")!=self.seq+1 or rec.get("previous_hash")!=self.prev or digest(body)!=rec.get("entry_hash"):
                    raise TransferDenied("EVIDENCE_CHAIN_BROKEN")
                self.prev=rec["entry_hash"]; self.seq+=1
    def emit(self,event,**payload):
        body={"schema":SCHEMA,"seq":self.seq+1,"ts_utc":time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime()),"previous_hash":self.prev,"event":event,"payload":payload}
        rec={**body,"entry_hash":digest(body)}
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open("a",encoding="utf-8") as f:
            f.write(json.dumps(rec,sort_keys=True,ensure_ascii=False)+"\n")
            f.flush(); os.fsync(f.fileno())
        self.prev=rec["entry_hash"]; self.seq+=1
        return rec

class ArtifactStore:
    def __init__(self,root:Path,max_bytes=8*1024*1024):
        self.root=root; self.max_bytes=max_bytes
        self.blobs=root/"blobs"; self.staging=root/"staging"; self.db=root/"registry.sqlite3"
        self.blobs.mkdir(parents=True,exist_ok=True); self.staging.mkdir(parents=True,exist_ok=True)
        self.db_conn=sqlite3.connect(self.db)
        self.db_conn.execute("CREATE TABLE IF NOT EXISTS artifacts (sha256 TEXT PRIMARY KEY,name TEXT NOT NULL,size INTEGER NOT NULL,mime TEXT NOT NULL,provenance TEXT NOT NULL,trust TEXT NOT NULL,created_utc TEXT NOT NULL)")
        self.db_conn.commit()
    def close(self): self.db_conn.close()
    def transfer(self,src:Path,*,declared_name:str,declared_size:int,declared_sha256:str,
                 declared_mime:str,provenance:dict,sender:str,trust:str="UNTRUSTED",
                 confirm=True,ack=True,simulate_resume=False)->dict:
        safe_name(declared_name)
        if src.is_symlink(): raise TransferDenied("SYMLINK_SOURCE_DENIED")
        if not src.is_file(): raise TransferDenied("SOURCE_NOT_REGULAR_FILE")
        size=src.stat().st_size
        if size!=declared_size: raise TransferDenied("SIZE_MISMATCH")
        if size>self.max_bytes: raise TransferDenied("OVERSIZED_ARTIFACT")
        actual=sha256(src)
        if actual!=declared_sha256: raise TransferDenied("HASH_MISMATCH")
        mime=observed_mime(src)
        if mime!=declared_mime: raise TransferDenied("MIME_MISMATCH")
        if not provenance.get("source_id") or not sender or not provenance.get("captured_utc"):
            raise TransferDenied("PROVENANCE_INCOMPLETE")
        if trust not in {"TRUSTED","REVIEW","UNTRUSTED"}: raise TransferDenied("TRUST_CLASS_INVALID")
        if not confirm: raise TransferDenied("CONFIRMATION_REQUIRED")
        if not ack: raise TransferDenied("ACK_REQUIRED")
        final=self.blobs/actual
        stage=self.staging/(actual+".part")
        evidence=Evidence(self.root/"EVENTS.jsonl")
        evidence.emit("SELECT",name=declared_name)
        evidence.emit("IDENTIFY",sha256=actual,size=size)
        evidence.emit("VALIDATE",size=size,max_bytes=self.max_bytes,mime=mime)
        evidence.emit("HASH",sha256=actual)
        evidence.emit("PROVENANCE",provenance=provenance,sender=sender)
        evidence.emit("TRUST_CLASSIFICATION",trust=trust)
        row=self.db_conn.execute("SELECT sha256 FROM artifacts WHERE sha256=?",(actual,)).fetchone()
        if row and final.is_file() and sha256(final)==actual:
            evidence.emit("DEDUP",sha256=actual,result="EXISTING_EXACT")
            evidence.emit("LOCAL_REGISTER",sha256=actual,result="ALREADY_REGISTERED")
            evidence.emit("PREVIEW",name=declared_name,size=size,mime=mime)
            evidence.emit("CONFIRM",accepted=True)
            evidence.emit("NEGOTIATE",chunk=CHUNK,resume=True)
            evidence.emit("ACK",sha256=actual,size=size,deduplicated=True)
            return {"status":"PASS","deduplicated":True,"sha256":actual,"size":size,"evidence_head":evidence.prev}
        evidence.emit("DEDUP",sha256=actual,result="NEW")
        evidence.emit("LOCAL_REGISTER",sha256=actual,result="RESERVED")
        evidence.emit("PREVIEW",name=declared_name,size=size,mime=mime)
        evidence.emit("CONFIRM",accepted=True)
        evidence.emit("NEGOTIATE",chunk=CHUNK,resume=True)
        offset=stage.stat().st_size if stage.exists() else 0
        if offset>size: stage.unlink(); offset=0
        if simulate_resume and offset==0:
            with src.open("rb") as f, stage.open("wb") as out:
                out.write(f.read(min(CHUNK*2,size)))
                out.flush(); os.fsync(out.fileno())
            offset=stage.stat().st_size
            evidence.emit("TRANSFER_INTERRUPTED",offset=offset)
        with src.open("rb") as f:
            f.seek(offset)
            with stage.open("ab") as out:
                while True:
                    block=f.read(CHUNK)
                    if not block: break
                    out.write(block)
                out.flush(); os.fsync(out.fileno())
        evidence.emit("TRANSFER",offset=size,resumed=offset>0)
        if sha256(stage)!=actual or stage.stat().st_size!=size:
            raise TransferDenied("POST_TRANSFER_INTEGRITY_FAIL")
        os.replace(stage,final)
        evidence.emit("ACK",sha256=actual,size=size,deduplicated=False)
        self.db_conn.execute("INSERT OR REPLACE INTO artifacts VALUES (?,?,?,?,?,?,?)",
            (actual,declared_name,size,mime,json.dumps(provenance,sort_keys=True),trust,time.strftime("%Y-%m-%dT%H:%M:%SZ",time.gmtime())))
        self.db_conn.commit()
        return {"status":"PASS","deduplicated":False,"sha256":actual,"size":size,"evidence_head":evidence.prev}

def build_fixture(root:Path):
    source=root/"source"; source.mkdir(parents=True,exist_ok=True)
    p=source/"attachment.txt"; p.write_bytes(b"LOUKSNA-P05-ATTACHMENT\n"*2000)
    return p

def run_p05_selftest(out:Path)->dict:
    import tempfile
    with tempfile.TemporaryDirectory(prefix="louksna-p05-") as td:
        root=Path(td); src=build_fixture(root); store=ArtifactStore(root/"store",max_bytes=2_000_000)
        try:
            size=src.stat().st_size; h=sha256(src); mime=observed_mime(src)
            base=dict(declared_name=src.name,declared_size=size,declared_sha256=h,declared_mime=mime,
                      provenance={"source_id":"P05_FIXTURE_SOURCE","captured_utc":"2026-10-08T00:00:00Z","source_kind":"controlled-fixture"},
                      sender="P05_SELFTEST",trust="REVIEW",confirm=True,ack=True)
            first=store.transfer(src,**base,simulate_resume=True)
            duplicate=store.transfer(src,**base)
            if not first["status"]=="PASS" or not duplicate["deduplicated"]: raise TransferDenied("POSITIVE_CONTROL_FAIL")
            checks={}
            def denied(tag,fn):
                try: fn()
                except TransferDenied: checks[tag]=True
                else: checks[tag]=False
            denied("false_mime",lambda:store.transfer(src,**{**base,"declared_mime":"image/png"}))
            denied("oversized",lambda:store.transfer(src,**{**base,"declared_size":size,"declared_sha256":h,"declared_mime":mime},))
            denied("path_traversal",lambda:store.transfer(src,**{**base,"declared_name":"../escape"}))
            sy=root/"symlink"; sy.symlink_to(src)
            denied("symlink",lambda:store.transfer(sy,**{**base,"declared_name":"symlink"}))
            corrupt=root/"corrupt.txt"; corrupt.write_bytes(b"CORRUPT")
            denied("corrupt_hash",lambda:store.transfer(corrupt,**{**base,"declared_size":corrupt.stat().st_size,"declared_sha256":h}))
            denied("ack_missing",lambda:store.transfer(src,**{**base,"ack":False}))
            denied("provenance_missing",lambda:store.transfer(src,**{**base,"provenance":{}}))
            # Explicit oversized control uses a dedicated tiny store limit.
            tiny=ArtifactStore(root/"tiny",max_bytes=16)
            try: denied("oversized",lambda:tiny.transfer(src,**base))
            finally: tiny.close()
            if not all(checks.values()): raise TransferDenied("NEGATIVE_CONTROL_FAIL")
            report={"schema":SCHEMA,"status":"PASS","pipeline":["SELECT","IDENTIFY","VALIDATE","HASH","PROVENANCE","TRUST_CLASSIFICATION","DEDUP","LOCAL_REGISTER","PREVIEW","CONFIRM","NEGOTIATE","TRANSFER","ACK","EVIDENCE"],"positive":{"first":first,"duplicate":duplicate},"negative":checks,"content_addressed":True,"sha256":h,"size":size}
            (out/"P05_ARTIFACT_TRANSFER_SELFTEST.json").write_text(json.dumps(report,indent=2,sort_keys=True)+"\n")
            return report
        finally: store.close()
