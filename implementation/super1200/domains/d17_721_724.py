#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 721-724. No certification."""
from __future__ import annotations

SPECS = {721: ('METACOGNITIVE_ORDER_REGISTRY',
       'REGISTRY',
       'formal definitions/boundaries for reasoning orders'),
 722: ('FIRST_ORDER_OBJECT_REASONING', 'REASONING_LAYER', 'object-level claims/evidence only'),
 723: ('SECOND_ORDER_REASONING',
       'METACOGNITIVE_LAYER',
       'evaluate method/assumptions of first-order reasoning'),
 724: ('THIRD_ORDER_GOVERNANCE',
       'GOVERNANCE_LAYER',
       'evaluate rules/authority applied to reasoning')}


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
