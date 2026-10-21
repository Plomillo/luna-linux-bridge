#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 602-605. No certification."""
from __future__ import annotations

SPECS = {602: ('FADING_GUIDANCE_ENGINE',
       'PEDAGOGY_ENGINE',
       'progressive support reduction triggered by demonstrated competence'),
 603: ('DEEP_QUESTION_ENGINE',
       'CONTENT_ENGINE',
       'questions tied to causal/explanatory objectives and evidence'),
 604: ('MISCONCEPTION_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'misconception identity/domain/evidence/counterexample'),
 605: ('MISCONCEPTION_DETECTOR',
       'ANALYZER',
       'detect patterns probabilistically/explicitly, retain uncertainty')}


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
