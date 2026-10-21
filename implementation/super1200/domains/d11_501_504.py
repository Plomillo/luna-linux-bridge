#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 501-504. No certification."""
from __future__ import annotations

SPECS = {501: ('CURIOSITY_ENGINE',
       'RESEARCH_ORCHESTRATOR',
       'unknown→questions→value→bounded research; cannot mutate state'),
 502: ('QUESTION_GENERATOR',
       'REASONING_ENGINE',
       'questions grounded in explicit unknown/claim and testability'),
 503: ('UNKNOWN_TO_RESEARCH_PIPELINE',
       'WORKFLOW',
       'UNKNOWN→question→plan→evidence→residual uncertainty'),
 504: ('RESEARCH_PRIORITY_ENGINE',
       'DECISION_ENGINE',
       'impact×information value×cost×urgency; safety blockers override score')}


def _bind(ctx, name: str, kind: str, hardening: str):
    if not isinstance(ctx, dict):
        return {"error": "missing_ctx"}
    claimed = ctx.get("canonical_name")
    if claimed not in (None, name):
        raise ValueError(f"identity mismatch for {name}")
    return {
        "binding": name.lower(),
        "kind": kind,
        "hardening": hardening,
        "status": "bound",
    }


def run(capability_id: int, ctx=None):
    if capability_id not in SPECS:
        raise ValueError(f"unregistered capability {capability_id}")
    name, kind, hardening = SPECS[capability_id]
    result = _bind(ctx, name, kind, hardening)
    result["canonical_name"] = name
    result["capability_id"] = capability_id
    result["certification_granted"] = False
    return result


FUNCS = {
    cid: (spec[0], (lambda ctx, cid=cid: run(cid, ctx)))
    for cid, spec in SPECS.items()
}
