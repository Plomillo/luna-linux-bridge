#!/usr/bin/env python3
"""Lightweight local session boundary for Zona Directiva.

The PC keeps the call. It does not run models, store weights, or act as a
GitHub runner. GitHub dispatch is not a file-transfer API.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any

WORKFLOW_DISPATCH_INPUT_CHAR_LIMIT = 65535
REPOSITORY_DISPATCH_BYTE_LIMIT = 64 * 1024
BIND_HOST = "127.0.0.1"

FORBIDDEN_LOCAL = (
    "LOCAL_HEAVY_COMPUTATION",
    "LOCAL_MODEL_STORAGE",
    "LOCAL_MODEL_INFERENCE",
    "LOCAL_GITHUB_RUNNER",
)


class SessionRejected(ValueError):
    pass


class LocalSession:
    def __init__(self, session_id: str) -> None:
        if not session_id or "/" in session_id:
            raise SessionRejected("INVALID_SESSION_ID")
        self.session_id = session_id
        self.turns: list[dict[str, Any]] = []
        self.models_stored = False
        self.inference_ran = False
        self.runner_installed = False

    def note_audio(self, payload: bytes) -> dict[str, Any]:
        if self.models_stored or self.inference_ran or self.runner_installed:
            raise SessionRejected("LOCAL_POLICY_BROKEN")
        encoded = json.dumps({"audio_sha256": hashlib.sha256(payload).hexdigest(), "bytes": len(payload)})
        fits_dispatch = len(encoded) <= WORKFLOW_DISPATCH_INPUT_CHAR_LIMIT
        record = {
            "session_id": self.session_id,
            "audio_sha256": hashlib.sha256(payload).hexdigest(),
            "audio_bytes": len(payload),
            "raw_audio_committed": False,
            "dispatch_metadata_fits_workflow_dispatch": fits_dispatch,
            "audio_bytes_fit_in_workflow_dispatch": len(payload) <= WORKFLOW_DISPATCH_INPUT_CHAR_LIMIT,
            "repository_dispatch_byte_limit": REPOSITORY_DISPATCH_BYTE_LIMIT,
            "bind_host": BIND_HOST,
            "forbidden_local": FORBIDDEN_LOCAL,
            "models_stored": False,
            "inference_ran": False,
            "certification": "NOT_GRANTED",
        }
        if len(payload) > REPOSITORY_DISPATCH_BYTE_LIMIT:
            record["transport"] = "BLOCKED_PAYLOAD_EXCEEDS_GITHUB_DISPATCH"
            record["status"] = "HOLD"
        else:
            record["transport"] = "METADATA_ONLY_UNTIL_AN_AUTHORIZED_CARRIER_EXISTS"
            record["status"] = "HOLD"
        self.turns.append({"sha256": record["audio_sha256"], "status": record["status"]})
        return record

    def refuse_model(self, label: str) -> dict[str, str]:
        return {"status": "REJECTED", "reason": "LOCAL_MODEL_STORAGE_FORBIDDEN", "label": label}
