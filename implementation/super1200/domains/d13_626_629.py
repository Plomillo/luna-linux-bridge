#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 626-629. No certification."""
from __future__ import annotations

SPECS = {626: ('ADAPTIVE_PATH_ENGINE',
       'PEDAGOGY_ENGINE',
       'skip/reinforce only from demonstrated state and uncertainty'),
 627: ('DIFFICULTY_ESTIMATOR',
       'ANALYTICS_ENGINE',
       'content/item difficulty separated from learner performance'),
 628: ('COGNITIVE_LOAD_MONITOR',
       'PEDAGOGY_MONITOR',
       'operational proxy from novelty/steps/errors, not clinical inference'),
 629: ('CHUNKING_ENGINE', 'CONTENT_ENGINE', 'conceptual cohesion and prerequisite boundaries')}


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
