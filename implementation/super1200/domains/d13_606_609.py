#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 606-609. No certification."""
from __future__ import annotations

SPECS = {606: ('COUNTEREXAMPLE_GENERATOR',
       'CONTENT_ENGINE',
       'counterexamples validated against the target rule/claim'),
 607: ('SOCRATIC_TUTOR_ENGINE',
       'PEDAGOGY_ENGINE',
       'questions adapt to objective/evidence without fabricating learner traits'),
 608: ('EXPLANATION_GENERATOR',
       'CONTENT_ENGINE',
       'fact/inference/examples separated; references and uncertainty'),
 609: ('REFERENCE_GENERATOR',
       'CONTENT_ENGINE',
       'precise lookup-oriented output derived from current contracts')}


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
