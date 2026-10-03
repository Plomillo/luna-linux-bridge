#!/usr/bin/env python3
import hashlib
import json

REQUEST_SCHEMA = "LOUKSNA_KNOWLEDGE_REQUEST/1.0"
RESULT_SCHEMA = "LOUKSNA_KNOWLEDGE_RESULT/1.0"
FALSE_AUTHORITY = {
    "canonical": False,
    "execution": False,
    "root": False,
    "gate": False,
    "certification": False,
}

def canonical_digest(obj):
    raw=json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(",",":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

def validate_result(obj):
    if not isinstance(obj,dict) or obj.get("schema") != RESULT_SCHEMA:
        raise ValueError("RESULT_SCHEMA_INVALID")
    if obj.get("authority") != FALSE_AUTHORITY:
        raise ValueError("AUTHORITY_DRIFT")
    if obj.get("execution_allowed") is not False:
        raise ValueError("EXECUTION_AUTHORITY_DRIFT")
    return obj
