#!/usr/bin/env python3
"""Exact FFprobe certification mission binding for CUSTOSZ V7.
Additive candidate surface; no certification propagation and no main mutation.
"""
from pathlib import Path
import hashlib

MISSION_REL = "missions/inbox/document-factory-ffprobe-exact-cert-20261006/MISSION_ORIGINAL.md"
MISSION_ID = "MIS-DOCUMENT-FACTORY-FFPROBE-EXACT-CERT-20261006"
WORK_SHA = "3cc413cea40d77c7bb119e29d09d72b4eac44909"
LEGACY_CANDIDATE_SHA = "3774cb102ad6318fc824b2cb87c5055e9f5f4b0b"
EXPECTED_SOURCE_SHA256 = "PLACEHOLDER_COMPUTED_AT_RUNTIME"

def source_digest(root: Path) -> str:
    return hashlib.sha256((root / MISSION_REL).read_bytes()).hexdigest()

def validate(root: Path) -> dict:
    p = root / MISSION_REL
    if not p.is_file():
        raise SystemExit("MISSION_SOURCE_MISSING")
    text = p.read_text(encoding="utf-8")
    required = (MISSION_ID, WORK_SHA, LEGACY_CANDIDATE_SHA,
                "TARGET_TERMINAL_STATE = CERTIFIED_NOT_ACTIVE",
                "CERTIFICATION_PROPAGATION = FORBIDDEN",
                "REMOTE_DESKTOP_COMMANDER = PROHIBITED")
    missing = [x for x in required if x not in text]
    if missing:
        raise SystemExit("MISSION_BINDING_FAIL:" + repr(missing))
    return {
        "mission_id": MISSION_ID,
        "mission_rel": MISSION_REL,
        "source_sha256": source_digest(root),
        "work_sha": WORK_SHA,
        "legacy_candidate_sha": LEGACY_CANDIDATE_SHA,
        "terminal_state": "CERTIFIED_NOT_ACTIVE",
        "certification_propagated": False,
        "desktop_commander": "FORBIDDEN",
        "binding": "PASS",
    }
