#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 586-589. No certification."""
from __future__ import annotations

SPECS = {586: ('PEDAGOGICAL_FABRIC',
       'PEDAGOGY_FABRIC',
       'learning objects→prerequisites→objectives→practice→assessment→evidence'),
 587: ('LEARNING_OBJECT_REGISTRY',
       'REGISTRY',
       'object ID/type/source/version/prerequisites/outcomes'),
 588: ('PREREQUISITE_GRAPH', 'GRAPH', 'acyclic prerequisite relations with rationale'),
 589: ('KNOWLEDGE_GRAPH_PEDAGOGICAL_VIEW',
       'GRAPH_VIEW',
       'derived projection from 23 without duplicating knowledge')}


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
