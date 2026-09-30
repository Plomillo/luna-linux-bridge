#!/usr/bin/env python3
"""Fail-closed adapter from a reasoning result into the existing LRB plan surface.

It deliberately does not execute anything.  The existing Remote Bridge remains
the operational boundary and preserves its external-gate requirements.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys

BRIDGE = Path(__file__).resolve().parents[1]
if str(BRIDGE) not in sys.path:
    sys.path.insert(0, str(BRIDGE))
HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import lrb_core
from interface import RESULT_SCHEMA, canonical_digest, validate_request


class AdapterHold(RuntimeError):
    pass


def bind_to_bridge(request, reasoning_result):
    request = validate_request(request)
    if not isinstance(reasoning_result, dict) or reasoning_result.get("schema") != RESULT_SCHEMA:
        raise AdapterHold("REASONING_RESULT_SCHEMA_INVALID")
    if reasoning_result.get("request_id") != request["request_id"]:
        raise AdapterHold("REQUEST_RESULT_BINDING_MISMATCH")
    authority = reasoning_result.get("authority")
    required_false = {"canonical", "execution", "root", "gate", "certification"}
    if not isinstance(authority, dict) or any(authority.get(k) is not False for k in required_false):
        raise AdapterHold("REASONING_AUTHORITY_NOT_FALSE")
    if reasoning_result.get("execution_allowed") is not False:
        raise AdapterHold("REASONING_EXECUTION_FLAG_INVALID")
    proposal = reasoning_result.get("proposal")
    if not isinstance(proposal, dict):
        raise AdapterHold("PROPOSAL_INVALID")
    model_expectation = json.dumps({
        "reasoning_request_id": request["request_id"],
        "reasoning_result_sha256": reasoning_result.get("result_sha256"),
        "proposal": proposal,
        "expected_result": reasoning_result.get("expected_result"),
        "failure_conditions": reasoning_result.get("failure_conditions"),
        "recovery_proposal": reasoning_result.get("recovery_proposal"),
    }, ensure_ascii=False, sort_keys=True)
    plan = lrb_core.validate_claims(
        request["objective"],
        model_expectation,
        reasoning_result.get("provider_id", "UNKNOWN_PROVIDER"),
        reasoning_result.get("material_binding", {}).get("model_sha256", "UNBOUND"),
    )
    plan.update({
        "reasoning_interface": "REASONING_INTERFACE/1.0",
        "reasoning_request_id": request["request_id"],
        "reasoning_result_sha256": reasoning_result.get("result_sha256"),
        "reasoning_evidence_refs": list(request["evidence_refs"]),
        "reasoning_binding_sha256": canonical_digest({
            "request": request,
            "result_sha256": reasoning_result.get("result_sha256"),
        }),
    })
    if plan.get("execution_allowed") is not False:
        raise AdapterHold("BRIDGE_EXECUTION_AUTHORITY_DRIFT")
    return plan
