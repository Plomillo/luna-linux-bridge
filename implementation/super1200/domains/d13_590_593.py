#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 590-593. No certification."""
from __future__ import annotations

SPECS = {590: ('LEARNER_MODEL',
       'STATE_MODEL',
       'demonstrated learning state only; no unsupported psychological profiling'),
 591: ('KNOWLEDGE_STATE_ESTIMATOR',
       'ANALYTICS_ENGINE',
       'estimate from assessments with uncertainty; exposure≠mastery'),
 592: ('LEARNING_OBJECTIVE_ENGINE',
       'PEDAGOGY_ENGINE',
       'observable outcome, conditions and acceptance criteria'),
 593: ('COMPETENCY_REGISTRY', 'REGISTRY', 'competency definition/evidence/mastery criteria')}


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
