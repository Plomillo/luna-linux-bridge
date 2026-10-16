"""Hash-chained append-only JSONL journal with inter-process locking."""
from __future__ import annotations
import json,os,threading
from pathlib import Path
from typing import Any
from .model import canonical_json,sha256_bytes
_LOCK=threading.RLock()
REQUIRED=("operation_id","mission_id","sequence_id","timestamp_utc","actor","tool_and_version","source_identity","input_hash_and_size","output_hash_and_size","validation_result","authorization_evidence_reference","dependency_context","rollback_pointer","status")
def _lock(fd:int)->None:
 if os.name=="nt":
  import msvcrt
  os.lseek(fd,0,os.SEEK_SET)
  try:msvcrt.locking(fd,msvcrt.LK_LOCK,1)
  except OSError:os.write(fd,b"0");os.lseek(fd,0,os.SEEK_SET);msvcrt.locking(fd,msvcrt.LK_LOCK,1)
 else:
  import fcntl
  fcntl.flock(fd,fcntl.LOCK_EX)
def _unlock(fd:int)->None:
 if os.name=="nt":
  import msvcrt
  os.lseek(fd,0,os.SEEK_SET);msvcrt.locking(fd,msvcrt.LK_UNLCK,1)
 else:
  import fcntl
  fcntl.flock(fd,fcntl.LOCK_UN)
def _hash(row:dict[str,Any])->str:
 value=dict(row);value.pop("current_event_hash",None)
 return sha256_bytes(canonical_json(value).encode("utf-8"))
def append_event(path:str|Path,event:dict[str,Any])->dict[str,Any]:
 missing=[k for k in REQUIRED if k not in event]
 if missing:raise ValueError("EVIDENCE_FIELDS_MISSING:"+",".join(missing))
 p=Path(path);p.parent.mkdir(parents=True,exist_ok=True);lockp=p.with_suffix(p.suffix+".lock")
 with _LOCK:
  fd=os.open(str(lockp),os.O_CREAT|os.O_RDWR,0o600)
  try:
   _lock(fd);checked=verify_journal(p)
   if checked["status"]!="PASS":raise ValueError("JOURNAL_PREEXISTING_INTEGRITY_FAILURE")
   row=dict(event);row["previous_event_hash"]=checked["last_hash"];row["current_event_hash"]=_hash(row)
   line=(canonical_json(row)+"\n").encode("utf-8");out=os.open(str(p),os.O_CREAT|os.O_WRONLY|os.O_APPEND,0o600)
   try:
    if os.write(out,line)!=len(line):raise OSError("SHORT_EVIDENCE_WRITE")
    os.fsync(out)
   finally:os.close(out)
   return row
  finally:_unlock(fd);os.close(fd)
def verify_journal(path:str|Path)->dict[str,Any]:
 p=Path(path)
 if not p.exists():return {"status":"PASS","event_count":0,"last_hash":"0"*64}
 previous="0"*64;count=0
 try:
  with p.open("r",encoding="utf-8") as stream:
   for no,line in enumerate(stream,1):
    if not line.endswith("\n"):return {"status":"FAIL","reason":"UNTERMINATED_EVENT","line":no}
    row=json.loads(line)
    if not isinstance(row,dict):raise ValueError("EVENT_NOT_OBJECT")
    if row.get("previous_event_hash")!=previous:return {"status":"FAIL","reason":"PREVIOUS_HASH_MISMATCH","line":no}
    current=row.get("current_event_hash")
    if current!=_hash(row):return {"status":"FAIL","reason":"CURRENT_HASH_MISMATCH","line":no}
    previous=current;count+=1
 except (OSError,UnicodeError,json.JSONDecodeError,ValueError) as exc:return {"status":"FAIL","reason":"JOURNAL_UNREADABLE_OR_MALFORMED","detail":str(exc)}
 return {"status":"PASS","event_count":count,"last_hash":previous}
