#!/usr/bin/env python3
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
