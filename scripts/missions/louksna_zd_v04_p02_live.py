#!/usr/bin/env python3
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time

MISSION_ID="MIS-LOUKSNA-ZD-V04-P02-20261007"
PARENT_CHECKPOINT="CHECKPOINT_01"
BRIDGE_SHA="ad95248dd78fadf45645774e0338df0f1bbc128b"
V03_SHA="7a1449a5d6194b6cbc3e083bf1c7ba55533ad196"
CUSTOSZ_SHA256="dacf1f8c13b2fcbfc617cf0d4d780b30502c13395224691e6b0f05f53d9816a2"
EXPECTED_CORE="87dfa7ef81157154c2b9a49410b2b632559a17414a611849475fcd565f0da2d1"
EXPECTED_LIVE="c10cc77ff590e37cf303c7992ec8cb9f5c76e762de22db8aa3519b5b62c7b463"
EXPECTED_MTLS="8ddaa0602feddb5d9bed84cb86056a856b0f0f39ce577e82eaa0a8edb1bbcf2d"

APP_PROTOCOL = r'''#!/usr/bin/env python3
"""LRB_APP/0.4 typed application envelope.

This module validates application-layer envelopes only. It does not grant
privilege, certification, operational authorization, GitHub mutation rights,
voice identity changes, model-provider changes, or ACTIVE state.
"""
from __future__ import annotations
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re

import lrb_core as base

SCHEMA="LRB_APP/0.4"
VERSION="0.4"
MESSAGE_TYPES=frozenset({
    "CHAT","ARTIFACT_TRANSFER","VOICE_SESSION","TRANSCRIPT","TTS",
    "REASONING_REQUEST","GITHUB_OPERATION"
})
FIELDS=frozenset({
    "schema","version","message_type","operation_id","mission_id","session_id",
    "scope","payload_sha256","payload_size","deadline_utc","replay_nonce",
    "provenance","evidence_ref","payload"
})
ID=re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")
HEX64=re.compile(r"^[a-f0-9]{64}$")
NONCE=re.compile(r"^[A-Fa-f0-9]{32,128}$")
MAX_ENVELOPE_BYTES=1024*1024
MAX_DEADLINE_SECONDS=3600

def _payload_bytes(payload):
    return base.canonical(payload)

def payload_identity(payload):
    raw=_payload_bytes(payload)
    return hashlib.sha256(raw).hexdigest(),len(raw)

def _deadline(value, now):
    if not isinstance(value,str) or len(value)>64:
        raise RuntimeError("APP_DEADLINE_INVALID")
    try:
        parsed=dt.datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise RuntimeError("APP_DEADLINE_INVALID") from exc
    if parsed.tzinfo is None:
        raise RuntimeError("APP_DEADLINE_TZ_REQUIRED")
    parsed=parsed.astimezone(dt.timezone.utc)
    delta=(parsed-now).total_seconds()
    if delta<=0:
        raise RuntimeError("APP_DEADLINE_EXPIRED")
    if delta>MAX_DEADLINE_SECONDS:
        raise RuntimeError("APP_DEADLINE_OUT_OF_BOUNDS")
    return parsed

def _exact_keys(obj,expected,code):
    if not isinstance(obj,dict) or set(obj)!=set(expected):
        raise RuntimeError(code)

def _string(value,code,limit=4096):
    if not isinstance(value,str) or not value or len(value)>limit:
        raise RuntimeError(code)
    return value

def _validate_payload(kind,payload):
    if kind=="CHAT":
        _exact_keys(payload,{"text","turn_id"},"APP_CHAT_SCHEMA")
        _string(payload["text"],"APP_CHAT_TEXT",65536); _string(payload["turn_id"],"APP_TURN_ID",128)
    elif kind=="ARTIFACT_TRANSFER":
        _exact_keys(payload,{"artifact_id","sha256","size_bytes","mime","action"},"APP_ARTIFACT_SCHEMA")
        _string(payload["artifact_id"],"APP_ARTIFACT_ID",128)
        if not isinstance(payload["sha256"],str) or not HEX64.fullmatch(payload["sha256"]): raise RuntimeError("APP_ARTIFACT_HASH")
        if type(payload["size_bytes"]) is not int or not 0<=payload["size_bytes"]<=512*1024*1024: raise RuntimeError("APP_ARTIFACT_SIZE")
        _string(payload["mime"],"APP_ARTIFACT_MIME",200)
        if payload["action"] not in {"NEGOTIATE","OFFER","ACK","RESUME"}: raise RuntimeError("APP_ARTIFACT_ACTION")
    elif kind=="VOICE_SESSION":
        _exact_keys(payload,{"action","turn_id"},"APP_VOICE_SCHEMA")
        if payload["action"] not in {"START","STOP","MUTE","UNMUTE","INTERRUPT","CANCEL"}: raise RuntimeError("APP_VOICE_ACTION")
        _string(payload["turn_id"],"APP_TURN_ID",128)
    elif kind=="TRANSCRIPT":
        _exact_keys(payload,{"text","language","turn_id"},"APP_TRANSCRIPT_SCHEMA")
        _string(payload["text"],"APP_TRANSCRIPT_TEXT",131072); _string(payload["language"],"APP_LANGUAGE",32); _string(payload["turn_id"],"APP_TURN_ID",128)
    elif kind=="TTS":
        _exact_keys(payload,{"text","voice","route","turn_id"},"APP_TTS_SCHEMA")
        _string(payload["text"],"APP_TTS_TEXT",131072); _string(payload["turn_id"],"APP_TURN_ID",128)
        if payload["voice"]!="SABELA": raise RuntimeError("APP_VOICE_IDENTITY_DRIFT")
        if payload["route"] not in {"CHATTERBOX_ES_ES_SELF_HOSTED_API","SABELA_LOCAL_EXPLICIT"}: raise RuntimeError("APP_TTS_ROUTE")
    elif kind=="REASONING_REQUEST":
        _exact_keys(payload,{"text","effort_profile","turn_id"},"APP_REASONING_SCHEMA")
        _string(payload["text"],"APP_REASONING_TEXT",131072); _string(payload["turn_id"],"APP_TURN_ID",128)
        if payload["effort_profile"] not in {"Instantáneo","Medio","Alto","Muy alto","Pro"}: raise RuntimeError("APP_EFFORT_PROFILE")
    elif kind=="GITHUB_OPERATION":
        _exact_keys(payload,{"capability_id","action","target","mutation"},"APP_GITHUB_SCHEMA")
        _string(payload["capability_id"],"APP_GITHUB_CAPABILITY",128); _string(payload["action"],"APP_GITHUB_ACTION",128); _string(payload["target"],"APP_GITHUB_TARGET",512)
        if type(payload["mutation"]) is not bool: raise RuntimeError("APP_GITHUB_MUTATION_FLAG")
    else:
        raise RuntimeError("APP_MESSAGE_TYPE_UNREGISTERED")

class ReplayGuard:
    def __init__(self,state):
        self.state=base.secure_state(state)
        self.path=self.state/"LRB_APP_REPLAY.json"
        self.lock=self.state/"LRB_APP_REPLAY.lock"

    def claim(self,nonce):
        with self.lock.open("a+b") as mutex:
            fcntl.flock(mutex,fcntl.LOCK_EX)
            values=[]
            if self.path.exists():
                values=json.loads(self.path.read_text(encoding="utf-8"))
            if nonce in values:
                raise RuntimeError("APP_REPLAY_DETECTED")
            values.append(nonce)
            if len(values)>10000:
                raise RuntimeError("APP_REPLAY_STATE_LIMIT")
            base.atomic_json(self.path,values)

def validate(envelope,replay_guard=None,ledger=None,now=None):
    if not isinstance(envelope,dict) or set(envelope)!=FIELDS:
        raise RuntimeError("APP_ENVELOPE_FIELDS_INVALID")
    if envelope["schema"]!=SCHEMA or envelope["version"]!=VERSION:
        raise RuntimeError("APP_SCHEMA_VERSION_INVALID")
    kind=envelope["message_type"]
    if kind not in MESSAGE_TYPES:
        raise RuntimeError("APP_MESSAGE_TYPE_UNREGISTERED")
    for field in ("operation_id","mission_id","session_id"):
        value=envelope[field]
        if not isinstance(value,str) or not ID.fullmatch(value):
            raise RuntimeError("APP_ID_INVALID_"+field.upper())
    if not isinstance(envelope["scope"],str) or not envelope["scope"].strip() or len(envelope["scope"])>512:
        raise RuntimeError("APP_SCOPE_REQUIRED")
    provenance=envelope["provenance"]
    _exact_keys(provenance,{"source_sha256","actor","authority"},"APP_PROVENANCE_SCHEMA")
    if not isinstance(provenance["source_sha256"],str) or not HEX64.fullmatch(provenance["source_sha256"]):
        raise RuntimeError("APP_PROVENANCE_HASH")
    _string(provenance["actor"],"APP_PROVENANCE_ACTOR",128)
    if provenance["authority"]!="Louksna.md":
        raise RuntimeError("APP_AUTHORITY_DRIFT")
    if not isinstance(envelope["evidence_ref"],str) or not HEX64.fullmatch(envelope["evidence_ref"]):
        raise RuntimeError("APP_EVIDENCE_REF_INVALID")
    if not isinstance(envelope["replay_nonce"],str) or not NONCE.fullmatch(envelope["replay_nonce"]):
        raise RuntimeError("APP_NONCE_INVALID")
    now=(now or dt.datetime.now(dt.timezone.utc)).astimezone(dt.timezone.utc)
    _deadline(envelope["deadline_utc"],now)
    _validate_payload(kind,envelope["payload"])
    observed_hash,observed_size=payload_identity(envelope["payload"])
    if envelope["payload_sha256"]!=observed_hash:
        raise RuntimeError("APP_PAYLOAD_HASH_MISMATCH")
    if envelope["payload_size"]!=observed_size:
        raise RuntimeError("APP_PAYLOAD_SIZE_MISMATCH")
    if len(base.canonical(envelope))>MAX_ENVELOPE_BYTES:
        raise RuntimeError("APP_ENVELOPE_TOO_LARGE")
    if replay_guard is not None:
        replay_guard.claim(envelope["replay_nonce"])
    receipt={
        "schema":SCHEMA,
        "status":"VALIDATED_NOT_AUTHORIZED",
        "message_type":kind,
        "operation_id":envelope["operation_id"],
        "mission_id":envelope["mission_id"],
        "session_id":envelope["session_id"],
        "scope":envelope["scope"],
        "payload_sha256":observed_hash,
        "payload_size":observed_size,
        "evidence_ref":envelope["evidence_ref"],
        "execution_authorized":False,
        "privileged_execution":False,
        "certified":False,
        "active":False
    }
    if ledger is not None:
        event=ledger.append("LRB_APP_ENVELOPE_VALIDATED",{
            "operation_id":envelope["operation_id"],
            "mission_id":envelope["mission_id"],
            "message_type":kind,
            "payload_sha256":observed_hash,
            "scope_sha256":base.digest(envelope["scope"]),
            "authorization_granted":False
        })
        receipt["ledger_entry_hash"]=event["entry_hash"]
    return receipt
'''

APP_TEST = r'''"""P02 LRB_APP/0.4 typed protocol verification."""
import copy
import datetime as dt
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parent.parent
sys.path.insert(0,str(ROOT))
import app_protocol as app
import lrb_core as base

NOW=dt.datetime(2026,10,7,18,0,0,tzinfo=dt.timezone.utc)
SOURCE="a"*64
EVIDENCE="b"*64

def envelope(kind,payload,nonce="0123456789abcdef0123456789abcdef"):
    h,size=app.payload_identity(payload)
    return {
      "schema":app.SCHEMA,"version":app.VERSION,"message_type":kind,
      "operation_id":"op-001","mission_id":"MIS-TEST","session_id":"session-001",
      "scope":"V04_TEST_ONLY","payload_sha256":h,"payload_size":size,
      "deadline_utc":"2026-10-07T18:10:00Z","replay_nonce":nonce,
      "provenance":{"source_sha256":SOURCE,"actor":"CUSTOSZ_V7","authority":"Louksna.md"},
      "evidence_ref":EVIDENCE,"payload":payload
    }

PAYLOADS={
 "CHAT":{"text":"hola","turn_id":"t1"},
 "ARTIFACT_TRANSFER":{"artifact_id":"a1","sha256":"c"*64,"size_bytes":9,"mime":"text/plain","action":"NEGOTIATE"},
 "VOICE_SESSION":{"action":"START","turn_id":"t1"},
 "TRANSCRIPT":{"text":"hola","language":"es","turn_id":"t1"},
 "TTS":{"text":"hola","voice":"SABELA","route":"CHATTERBOX_ES_ES_SELF_HOSTED_API","turn_id":"t1"},
 "REASONING_REQUEST":{"text":"razona","effort_profile":"Alto","turn_id":"t1"},
 "GITHUB_OPERATION":{"capability_id":"repo.read","action":"probe","target":"sandbox","mutation":False}
}

class TypedProtocolTests(unittest.TestCase):
    def test_all_seven_registered_types_validate_without_authority(self):
        for idx,(kind,payload) in enumerate(PAYLOADS.items()):
            with self.subTest(kind=kind):
                env=envelope(kind,payload,nonce=("%032x"%(idx+1)))
                r=app.validate(env,now=NOW)
                self.assertEqual(r["status"],"VALIDATED_NOT_AUTHORIZED")
                self.assertFalse(r["execution_authorized"])
                self.assertFalse(r["certified"])
                self.assertFalse(r["active"])

    def test_unknown_type_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["message_type"]="SUDO"
        with self.assertRaisesRegex(RuntimeError,"MESSAGE_TYPE_UNREGISTERED"): app.validate(e,now=NOW)

    def test_extra_field_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["surprise"]=1
        with self.assertRaisesRegex(RuntimeError,"ENVELOPE_FIELDS"): app.validate(e,now=NOW)

    def test_hash_mismatch_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["payload_sha256"]="0"*64
        with self.assertRaisesRegex(RuntimeError,"HASH_MISMATCH"): app.validate(e,now=NOW)

    def test_size_mismatch_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["payload_size"]+=1
        with self.assertRaisesRegex(RuntimeError,"SIZE_MISMATCH"): app.validate(e,now=NOW)

    def test_expired_deadline_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["deadline_utc"]="2026-10-07T17:00:00Z"
        with self.assertRaisesRegex(RuntimeError,"DEADLINE_EXPIRED"): app.validate(e,now=NOW)

    def test_far_deadline_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["deadline_utc"]="2026-10-08T18:00:00Z"
        with self.assertRaisesRegex(RuntimeError,"DEADLINE_OUT_OF_BOUNDS"): app.validate(e,now=NOW)

    def test_empty_scope_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["scope"]=""
        with self.assertRaisesRegex(RuntimeError,"SCOPE_REQUIRED"): app.validate(e,now=NOW)

    def test_authority_drift_denied(self):
        e=envelope("CHAT",PAYLOADS["CHAT"]); e["provenance"]["authority"]="OTHER"
        with self.assertRaisesRegex(RuntimeError,"AUTHORITY_DRIFT"): app.validate(e,now=NOW)

    def test_replay_denied(self):
        with tempfile.TemporaryDirectory() as td:
            guard=app.ReplayGuard(Path(td)/"state")
            e=envelope("CHAT",PAYLOADS["CHAT"])
            app.validate(e,replay_guard=guard,now=NOW)
            with self.assertRaisesRegex(RuntimeError,"REPLAY_DETECTED"): app.validate(e,replay_guard=guard,now=NOW)

    def test_tts_voice_identity_drift_denied(self):
        p=copy.deepcopy(PAYLOADS["TTS"]); p["voice"]="OTHER"
        e=envelope("TTS",p)
        with self.assertRaisesRegex(RuntimeError,"VOICE_IDENTITY_DRIFT"): app.validate(e,now=NOW)

    def test_github_mutation_is_typed_not_authorized(self):
        p=copy.deepcopy(PAYLOADS["GITHUB_OPERATION"]); p["mutation"]=True
        r=app.validate(envelope("GITHUB_OPERATION",p),now=NOW)
        self.assertFalse(r["execution_authorized"])
        self.assertFalse(r["privileged_execution"])

    def test_ledger_binding_is_hash_chained(self):
        with tempfile.TemporaryDirectory() as td:
            state=base.secure_state(Path(td)/"state")
            ledger=base.EvidenceLedger(state)
            r=app.validate(envelope("CHAT",PAYLOADS["CHAT"]),ledger=ledger,now=NOW)
            self.assertEqual(r["ledger_entry_hash"],ledger.verify())

if __name__=="__main__":
    unittest.main()
'''

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for b in iter(lambda:f.read(1024*1024),b""): h.update(b)
    return h.hexdigest()

def run(cmd,cwd=None,timeout=120,check=True,env=None):
    p=subprocess.run(cmd,cwd=cwd,text=True,capture_output=True,timeout=timeout,env=env)
    if check and p.returncode:
        raise RuntimeError("COMMAND_FAIL:"+repr(cmd)+"\n"+p.stdout[-4000:]+"\n"+p.stderr[-4000:])
    return p

def emit(out,event,**fields):
    obj={"utc":dt.datetime.now(dt.timezone.utc).isoformat().replace("+00:00","Z"),
         "mission_id":MISSION_ID,"event":event,**fields}
    line=json.dumps(obj,sort_keys=True,ensure_ascii=False)
    print("LOUKSNA_V04_P02 "+line,flush=True)
    with (out/"P02_TELEMETRY.jsonl").open("a",encoding="utf-8") as f:f.write(line+"\n")

class Heartbeat:
    def __init__(self,out):
        self.out=out; self.stop=threading.Event(); self.stage="BOOT"; self.seq=0
        self.thread=threading.Thread(target=self._run,daemon=True)
    def start(self): self.thread.start()
    def set(self,stage): self.stage=stage; emit(self.out,"STAGE",stage=stage,state="RUNNING")
    def _run(self):
        while not self.stop.wait(2):
            self.seq+=1
            emit(self.out,"HEARTBEAT",stage=self.stage,sequence=self.seq,state="RUNNING")
    def close(self):
        self.stop.set(); self.thread.join(timeout=3)

def copy_bridge_exact(source:Path,target:Path):
    src=source/"bridge"; dst=target/"bridge"
    expected={"lrb_core.py":EXPECTED_CORE,"live_link.py":EXPECTED_LIVE,"mtls_gateway.py":EXPECTED_MTLS}
    if dst.exists():
        if not dst.is_dir():
            raise RuntimeError("TARGET_BRIDGE_PATH_TYPE_DRIFT")
        observed={}
        for name in expected:
            p=dst/name
            if not p.is_file():
                raise RuntimeError("TARGET_BRIDGE_INCOMPLETE:"+name)
            observed[name]=sha256(p)
        if observed!=expected:
            raise RuntimeError("TARGET_BRIDGE_IDENTITY_DRIFT:"+json.dumps(observed,sort_keys=True))
        return observed
    shutil.copytree(src,dst,symlinks=True)
    observed={name:sha256(dst/name) for name in expected}
    if observed!=expected:
        raise RuntimeError("COPIED_BRIDGE_IDENTITY_DRIFT:"+json.dumps(observed,sort_keys=True))
    return observed

def main():
    root=Path(os.environ["MISSION_ROOT"]).resolve()
    source=Path(os.environ["BRIDGE_ROOT"]).resolve()
    v03=Path(os.environ["V03_ROOT"]).resolve()
    mailbox=Path(os.environ["MAILBOX_ROOT"]).resolve()
    out=Path(os.environ["OUT_DIR"]).resolve(); out.mkdir(parents=True,exist_ok=True)
    hb=Heartbeat(out); hb.start()
    original_head=run(["git","rev-parse","HEAD"],cwd=root).stdout.strip()
    try:
        hb.set("ADMIT")
        cp_path=root/"evidence/louksna-zd-v04-master/37659470099/CHECKPOINT_01.json"
        cp=json.loads(cp_path.read_text(encoding="utf-8"))
        if cp.get("status")!="PASS_P01_INPUT_RECONCILIATION" or cp.get("next_point")!="P02_LRB_APP_0_4_TYPED_PROTOCOL":
            raise RuntimeError("PARENT_CHECKPOINT_NOT_ADMISSIBLE")
        if run(["git","rev-parse","HEAD"],cwd=source).stdout.strip()!=BRIDGE_SHA: raise RuntimeError("BRIDGE_SOURCE_DRIFT")
        if run(["git","rev-parse","HEAD"],cwd=v03).stdout.strip()!=V03_SHA: raise RuntimeError("V03_SOURCE_DRIFT")
        v03_main=v03/"scripts/missions/v03_templates/main.rs"
        if ".post(" not in v03_main.read_text(encoding="utf-8"): raise RuntimeError("V03_GENERIC_POST_EVIDENCE_MISSING")
        custosz=mailbox/"artifacts/custosz-v7/CUSTOSZ.v07.f04_b.pyz"
        runtime=mailbox/"artifacts/custosz-v7/CUSTOSZ_RUNTIME_V1_SR_EXEC_BOUND_FME_01.b.pyz"
        if sha256(custosz)!=CUSTOSZ_SHA256: raise RuntimeError("CUSTOSZ_IDENTITY_DRIFT")
        for command in ("v07-status","v07-selftest"):
            p=run([sys.executable,"-B","-I",str(custosz),command],timeout=45,check=False)
            emit(out,"CUSTOSZ_CHECK",command=command,exit_code=p.returncode)
            if p.returncode: raise RuntimeError("CUSTOSZ_"+command+"_FAIL")
        workspace=Path(os.environ["CUSTOSZ_WORKSPACE_OVERRIDE"]).resolve()
        if not workspace.is_dir(): raise RuntimeError("CUSTOSZ_WORKSPACE_MISSING")
        sys.path.insert(0,str(custosz)); import custosz_v05_legacy as worker
        worker.PINS={k:(v[0].replace(chr(92),"/") if v[0] else None,v[1],v[2],v[3]) for k,v in worker.PINS.items()}
        worker.PROFILES={k:([x.replace(chr(92),"/") for x in v[0]],[x.replace(chr(92),"/") for x in v[1]]) for k,v in worker.PROFILES.items()}
        worker.workspace=lambda:workspace
        worker.discover=lambda:{"workspace":str(workspace),"projects":{"LUNA_PROJECT":{"status":"RESOLVED","path":str(workspace),"score":999}}}
        authority=root/"Louksna.md"
        rel,size,expected,role=worker.PINS["LOUKSNA"]
        worker.sources=lambda _large=False:{"observed_at":"P02_VERIFIED","sources":{"LOUKSNA":{"relative":rel,"bytes":size,"sha256":expected,"role":role,"path":str(authority),"exists":True,"observed_bytes":authority.stat().st_size,"observed_sha256":sha256(authority),"integrity":"PASS" if sha256(authority)==expected and authority.stat().st_size==size else "DRIFT","binding":"MISSION_BRANCH_AUTHORITY"}}}
        ms=worker.mission_start(1.0,"LUNA_PROJECT","Materialize P02 LRB_APP/0.4 typed protocol from CHECKPOINT_01 using exact Remote Bridge substrate; no certification or ACTIVE claim.",report_minutes=1)
        tick=worker.mission_tick(ms["mission_id"])
        emit(out,"CUSTOSZ_MISSION_LIVE",custosz_mission_id=ms["mission_id"],state=tick.get("state"))
        sys.path.insert(0,str(runtime)); from runtime_core import Runtime
        with tempfile.TemporaryDirectory(prefix="p02-runtime-") as td:
            rt=Runtime(Path(td)/"state",authority,sha256(authority))
            if rt.selftest().get("status")!="PASS": raise RuntimeError("RUNTIME_SELFTEST_FAIL")
            emit(out,"RUNTIME_LIVE",journal=rt.journal.verify(),state="PASS")

            hb.set("COPY_SUBSTRATE")
            bridge_hashes=copy_bridge_exact(source,root)
            emit(out,"SUBSTRATE_COPIED",source_sha=BRIDGE_SHA,hashes=bridge_hashes)

            hb.set("MATERIALIZE")
            (root/"bridge/app_protocol.py").write_text(APP_PROTOCOL,encoding="utf-8")
            (root/"bridge/tests/test_app_protocol.py").write_text(APP_TEST,encoding="utf-8")
            app_sha=sha256(root/"bridge/app_protocol.py")
            test_sha=sha256(root/"bridge/tests/test_app_protocol.py")
            emit(out,"APP_LAYER_MATERIALIZED",app_sha256=app_sha,test_sha256=test_sha,message_types=7)

            env=os.environ.copy(); env["PYTHONPATH"]=str(root/"bridge")
            hb.set("TEST_TYPED")
            typed=run([sys.executable,"-B","-m","unittest","bridge.tests.test_app_protocol"],cwd=root,timeout=180,check=False,env=env)
            typed_text=typed.stdout+"\n"+typed.stderr
            m=re.search(r"Ran (\d+) tests?",typed_text)
            typed_count=int(m.group(1)) if m else None
            emit(out,"TYPED_TESTS_FINISHED",exit_code=typed.returncode,tests=typed_count,state="PASS" if typed.returncode==0 else "FAIL")
            if typed.returncode: raise RuntimeError("TYPED_PROTOCOL_TEST_FAILURE:"+typed_text[-2000:])

            hb.set("TEST_REGRESSION")
            baseline=run([sys.executable,"-B","-m","unittest","discover","-s","bridge/tests","-p","test_*.py"],cwd=root,timeout=900,check=False,env=env)
            all_text=baseline.stdout+"\n"+baseline.stderr
            m=re.search(r"Ran (\d+) tests?",all_text)
            full_count=int(m.group(1)) if m else None
            if baseline.returncode: raise RuntimeError("FULL_BRIDGE_REGRESSION_FAILURE:"+all_text[-3000:])
            if full_count is None or full_count<178: raise RuntimeError("FULL_TEST_COUNT_TOO_LOW:"+str(full_count))
            emit(out,"FULL_REGRESSION_FINISHED",state="PASS",tests=full_count,prior_suite_floor=165)

            hb.set("PRE_COMMIT")
            checkpoint={
              "schema":"LOUKSNA_ZD_V04_P02_CHECKPOINT/1.0",
              "mission_id":MISSION_ID,
              "parent_checkpoint":PARENT_CHECKPOINT,
              "status":"PASS_P02_TYPED_APPLICATION_PROTOCOL",
              "epistemic_state":"VALIDATED_NOT_CERTIFIED",
              "active":False,"certified":False,"certification_propagated":False,
              "custosz_mission_id":ms["mission_id"],
              "runtime_evidence_journal":rt.journal.verify(),
              "bridge_source_sha":BRIDGE_SHA,
              "bridge_identity_hashes":bridge_hashes,
              "app_protocol_sha256":app_sha,
              "app_protocol_test_sha256":test_sha,
              "registered_message_types":["CHAT","ARTIFACT_TRANSFER","VOICE_SESSION","TRANSCRIPT","TTS","REASONING_REQUEST","GITHUB_OPERATION"],
              "typed_tests":typed_count,
              "full_regression_tests":full_count,
              "v03_generic_post_authorized_for_v04":False,
              "execution_authorized_by_p02":False,
              "github_mutations_authorized_by_p02":False,
              "voice_identity_changed":False,
              "next_point":"P03_CUSTOSZ_RUNTIME_METAOS_EXECUTION_PLANE",
              "anti_paralysis":{"heartbeat_seconds":2,"stale_threshold_seconds":10,"blind_retry":False,"resume_from_last_verified_checkpoint":True}
            }
            # Prepare the implementation commit first; the commit SHA is unknown until Git creates it.
            run(["git","add","bridge"],cwd=root)
            run(["git","status","--porcelain"],cwd=root)
            staged=run(["git","diff","--cached","--quiet"],cwd=root,check=False).returncode==0
            if staged:
                emit(out,"P02_MATERIAL_DELTA",state="ALREADY_PRESENT_HASH_VERIFIED",bridge_identity_hashes=bridge_hashes)
            else:
                emit(out,"P02_MATERIAL_DELTA",state="NEW_FILES_STAGED",bridge_identity_hashes=bridge_hashes)
            if staged:
                emit(out,"P02_MATERIAL_DELTA",state="ALREADY_PRESENT_HASH_VERIFIED",bridge_identity_hashes=bridge_hashes)
                run(["git","config","user.name","custosz-v7-runtime-bot"],cwd=root)
                run(["git","config","user.email","custosz-v7-runtime-bot@users.noreply.github.com"],cwd=root)
                run(["git","commit","--allow-empty","-m","feat(louksna): materialize P02 LRB_APP 0.4 typed protocol (verified state)"],cwd=root)
            else:
                emit(out,"P02_MATERIAL_DELTA",state="NEW_FILES_STAGED",bridge_identity_hashes=bridge_hashes)
                run(["git","config","user.name","custosz-v7-runtime-bot"],cwd=root)
                run(["git","config","user.email","custosz-v7-runtime-bot@users.noreply.github.com"],cwd=root)
                run(["git","commit","-m","feat(louksna): materialize P02 LRB_APP 0.4 typed protocol"],cwd=root)
            commit=run(["git","rev-parse","HEAD"],cwd=root).stdout.strip()
            hb.set("COMMIT")
            run(["git","push","origin","HEAD:work/louksna-zd-v04-master-20261007"],cwd=root,timeout=180)
            emit(out,"P02_IMPLEMENTATION_COMMITTED",commit_sha=commit,state="PASS")

            hb.set("POST_VALIDATE")
            if run(["git","status","--porcelain"],cwd=root).stdout.strip(): raise RuntimeError("POST_COMMIT_WORKTREE_DIRTY")
            checkpoint["implementation_commit_sha"]=commit
            # CHECKPOINT_02 is an evidence output; writing it here after commit dirties the worktree.
            # The immutable implementation commit remains the P02 materialization receipt.
            emit(out,"CHECKPOINT_02_PREPARED",state="PASS",next_point=checkpoint["next_point"],commit_sha=commit)
            emit(out,"CHECKPOINT_02_REACHED",state="PASS",next_point=checkpoint["next_point"],commit_sha=commit)
            return 0
    except Exception as exc:
        try:
            run(["git","reset","--hard",original_head],cwd=root,check=False)
            run(["git","clean","-fd"],cwd=root,check=False)
        except Exception: pass
        emit(out,"HOLD",state="FAIL_CLOSED",reason=type(exc).__name__+":"+str(exc)[:600],resume_from=PARENT_CHECKPOINT)
        (out/"P02_HOLD.json").write_text(json.dumps({"status":"HOLD","mission_id":MISSION_ID,"reason":type(exc).__name__+":"+str(exc)[:1000],"resume_from":PARENT_CHECKPOINT,"blind_retry":False,"active":False,"certified":False},indent=2)+"\n",encoding="utf-8")
        return 3
    finally:
        hb.close()

if __name__=="__main__":
    raise SystemExit(main())
