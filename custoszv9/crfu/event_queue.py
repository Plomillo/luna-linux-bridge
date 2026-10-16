"""Persistent event-driven mission queue with bounded transitions and hash-linked state events.

The queue does not execute tasks by itself and does not grant execution authorization.
Callers dispatch work on new events; there is no busy-wait loop or polling thread.
"""
from __future__ import annotations
import hashlib,json,sqlite3
from contextlib import closing
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from .model import TaskContract,canonical_json,sha256_bytes

ALLOWED={
 "RECEIVED":{"PREFLIGHT","BLOCKED","DENIED"},
 "PREFLIGHT":{"READY","BLOCKED","WAITING_FOR_EVENT","DENIED"},
 "READY":{"RUNNING","BLOCKED"},
 "RUNNING":{"WAITING_FOR_EVENT","CHECKPOINTED","VALIDATING","COMPLETED","FAILED","BLOCKED"},
 "WAITING_FOR_EVENT":{"READY","BLOCKED","FAILED"},
 "CHECKPOINTED":{"RUNNING","VALIDATING","RECOVERING","BLOCKED"},
 "VALIDATING":{"RUNNING","COMPLETED","RECOVERING","FAILED","BLOCKED"},
 "RECOVERING":{"RUNNING","BLOCKED","FAILED"},
 "COMPLETED":set(),"FAILED":set(),"BLOCKED":set(),"DENIED":set()
}
def utc_now()->str:return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00","Z")
def _hash_event(value:dict[str,Any])->str:
 return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()

class QueueConflict(RuntimeError):pass
class InvalidTransition(RuntimeError):pass

class PersistentMissionQueue:
 def __init__(self,path:str|Path):
  self.path=Path(path);self.path.parent.mkdir(parents=True,exist_ok=True)
  with closing(self._connect()) as db:
   db.execute("CREATE TABLE IF NOT EXISTS missions(mission_id TEXT PRIMARY KEY,task_json TEXT NOT NULL,state TEXT NOT NULL,updated_at TEXT NOT NULL,next_action TEXT,wait_condition TEXT,wait_deadline_utc TEXT,checkpoint_reference TEXT)")
   db.execute("CREATE TABLE IF NOT EXISTS mission_events(event_seq INTEGER PRIMARY KEY AUTOINCREMENT,mission_id TEXT NOT NULL,event_type TEXT NOT NULL,from_state TEXT,to_state TEXT NOT NULL,timestamp_utc TEXT NOT NULL,payload_json TEXT NOT NULL,previous_event_hash TEXT NOT NULL,event_hash TEXT NOT NULL)")
 def _connect(self)->sqlite3.Connection:
  db=sqlite3.connect(str(self.path),timeout=10,isolation_level=None)
  db.row_factory=sqlite3.Row
  db.execute("PRAGMA busy_timeout=10000")
  db.execute("PRAGMA foreign_keys=ON")
  return db
 def _append(self,db:sqlite3.Connection,mission_id:str,event_type:str,from_state:str|None,to_state:str,payload:dict[str,Any])->None:
  last=db.execute("SELECT event_hash FROM mission_events ORDER BY event_seq DESC LIMIT 1").fetchone()
  previous=last["event_hash"] if last else "0"*64
  timestamp=utc_now();payload_text=canonical_json(payload)
  material={"mission_id":mission_id,"event_type":event_type,"from_state":from_state,"to_state":to_state,
            "timestamp_utc":timestamp,"payload_json":payload_text,"previous_event_hash":previous}
  digest=_hash_event(material)
  db.execute("INSERT INTO mission_events(mission_id,event_type,from_state,to_state,timestamp_utc,payload_json,previous_event_hash,event_hash) VALUES(?,?,?,?,?,?,?,?)",
   (mission_id,event_type,from_state,to_state,timestamp,payload_text,previous,digest))
 def submit(self,task_value:Any)->dict[str,Any]:
  task,issues=TaskContract.validate(task_value)
  if issues or task is None:raise ValueError("TASK_CONTRACT_INVALID:"+",".join(issues))
  mission=task.task_id;raw=canonical_json(dict(task.value))
  db=self._connect()
  try:
   db.execute("BEGIN IMMEDIATE")
   old=db.execute("SELECT task_json,state,updated_at FROM missions WHERE mission_id=?",(mission,)).fetchone()
   if old:
    if old["task_json"]!=raw:
     db.rollback();raise QueueConflict("MISSION_ID_REUSED_WITH_DIFFERENT_TASK")
    db.commit();return {"mission_id":mission,"state":old["state"],"idempotent_duplicate":True}
   now=utc_now()
   db.execute("INSERT INTO missions(mission_id,task_json,state,updated_at) VALUES(?,?,?,?)",(mission,raw,"RECEIVED",now))
   self._append(db,mission,"MISSION_SUBMITTED",None,"RECEIVED",{"task_sha256":sha256_bytes(raw.encode("utf-8"))})
   db.commit();return {"mission_id":mission,"state":"RECEIVED","idempotent_duplicate":False}
  except Exception:
   if db.in_transaction:db.rollback()
   raise
  finally:db.close()
 def transition(self,mission_id:str,expected_state:str,new_state:str,*,event_type:str,payload:dict[str,Any]|None=None,fields:dict[str,Any]|None=None)->dict[str,Any]:
  if new_state not in ALLOWED.get(expected_state,set()):raise InvalidTransition(f"TRANSITION_FORBIDDEN:{expected_state}->{new_state}")
  fields=fields or {};allowed_fields={"next_action","wait_condition","wait_deadline_utc","checkpoint_reference"}
  if set(fields)-allowed_fields:raise ValueError("UNRECOGNIZED_STATE_FIELDS")
  if new_state=="WAITING_FOR_EVENT":
   condition=fields.get("wait_condition");deadline=fields.get("wait_deadline_utc")
   if not isinstance(condition,str) or not condition.strip() or not isinstance(deadline,str) or not deadline.strip():
    raise ValueError("WAIT_CONDITION_AND_DEADLINE_REQUIRED")
   try:parsed=datetime.fromisoformat(deadline.replace("Z","+00:00"))
   except ValueError:raise ValueError("WAIT_DEADLINE_INVALID")
   if parsed.tzinfo is None:raise ValueError("WAIT_DEADLINE_MUST_BE_TIMEZONE_AWARE")
  db=self._connect()
  try:
   db.execute("BEGIN IMMEDIATE")
   row=db.execute("SELECT state FROM missions WHERE mission_id=?",(mission_id,)).fetchone()
   if not row:raise KeyError("MISSION_NOT_FOUND")
   if row["state"]!=expected_state:raise QueueConflict("MISSION_STATE_CHANGED:"+str(row["state"]))
   now=utc_now()
   db.execute("UPDATE missions SET state=?,updated_at=?,next_action=COALESCE(?,next_action),wait_condition=COALESCE(?,wait_condition),wait_deadline_utc=COALESCE(?,wait_deadline_utc),checkpoint_reference=COALESCE(?,checkpoint_reference) WHERE mission_id=? AND state=?",
    (new_state,now,fields.get("next_action"),fields.get("wait_condition"),fields.get("wait_deadline_utc"),fields.get("checkpoint_reference"),mission_id,expected_state))
   data=dict(payload or {});data["state_fields"]=fields
   self._append(db,mission_id,event_type,expected_state,new_state,data)
   db.commit()
   return self.get(mission_id)
  except Exception:
   if db.in_transaction:db.rollback()
   raise
  finally:db.close()
 def claim_next_ready(self)->dict[str,Any]|None:
  """Atomically claim one ready item after a dispatch event; returns immediately if none."""
  db=self._connect()
  try:
   db.execute("BEGIN IMMEDIATE")
   row=db.execute("SELECT mission_id FROM missions WHERE state='READY' ORDER BY updated_at,mission_id LIMIT 1").fetchone()
   if not row:db.commit();return None
   mission=row["mission_id"]
   db.execute("UPDATE missions SET state='RUNNING',updated_at=? WHERE mission_id=? AND state='READY'",(utc_now(),mission))
   self._append(db,mission,"READY_MISSION_CLAIMED","READY","RUNNING",{"queue_claim":"ONE_AT_A_TIME_TRANSACTION"})
   db.commit();return self.get(mission)
  except Exception:
   if db.in_transaction:db.rollback()
   raise
  finally:db.close()
 def emit_signal(self,signal_key:str)->dict[str,Any]:
  """Wake only tasks whose declared wait condition matches the event key."""
  if not isinstance(signal_key,str) or not signal_key.strip():raise ValueError("SIGNAL_KEY_REQUIRED")
  now=datetime.now(timezone.utc);resumed=[];expired=[]
  db=self._connect()
  try:
   db.execute("BEGIN IMMEDIATE")
   rows=db.execute("SELECT mission_id,wait_condition,wait_deadline_utc FROM missions WHERE state='WAITING_FOR_EVENT' ORDER BY mission_id").fetchall()
   for row in rows:
    deadline=row["wait_deadline_utc"]
    try:due=datetime.fromisoformat(deadline.replace("Z","+00:00")) if deadline else None
    except ValueError:due=None
    mission=row["mission_id"]
    if due is None or due<=now:
     db.execute("UPDATE missions SET state='BLOCKED',updated_at=? WHERE mission_id=? AND state='WAITING_FOR_EVENT'",(utc_now(),mission))
     self._append(db,mission,"WAIT_DEADLINE_EXPIRED","WAITING_FOR_EVENT","BLOCKED",{"signal_key":signal_key,"deadline":deadline})
     expired.append(mission)
    elif row["wait_condition"]==signal_key:
     db.execute("UPDATE missions SET state='READY',updated_at=?,wait_condition=NULL,wait_deadline_utc=NULL WHERE mission_id=? AND state='WAITING_FOR_EVENT'",(utc_now(),mission))
     self._append(db,mission,"WAIT_CONDITION_SATISFIED","WAITING_FOR_EVENT","READY",{"signal_key":signal_key})
     resumed.append(mission)
   db.commit()
   return {"signal_key":signal_key,"resumed":resumed,"expired":expired}
  except Exception:
   if db.in_transaction:db.rollback()
   raise
  finally:db.close()
 def get(self,mission_id:str)->dict[str,Any]:
  with closing(self._connect()) as db:
   row=db.execute("SELECT * FROM missions WHERE mission_id=?",(mission_id,)).fetchone()
  if not row:raise KeyError("MISSION_NOT_FOUND")
  result=dict(row);result["task"]=json.loads(result.pop("task_json"));return result
 def verify_event_chain(self)->dict[str,Any]:
  previous="0"*64;count=0
  with closing(self._connect()) as db:
   rows=db.execute("SELECT mission_id,event_type,from_state,to_state,timestamp_utc,payload_json,previous_event_hash,event_hash FROM mission_events ORDER BY event_seq").fetchall()
  for no,row in enumerate(rows,1):
   if row["previous_event_hash"]!=previous:return {"status":"FAIL","reason":"PREVIOUS_EVENT_HASH_MISMATCH","event_number":no}
   material={"mission_id":row["mission_id"],"event_type":row["event_type"],"from_state":row["from_state"],"to_state":row["to_state"],
             "timestamp_utc":row["timestamp_utc"],"payload_json":row["payload_json"],"previous_event_hash":previous}
   if _hash_event(material)!=row["event_hash"]:return {"status":"FAIL","reason":"EVENT_HASH_MISMATCH","event_number":no}
   previous=row["event_hash"];count+=1
  return {"status":"PASS","event_count":count,"last_hash":previous}
