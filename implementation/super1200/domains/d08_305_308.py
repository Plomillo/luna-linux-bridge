#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 305-308. No certification."""
from __future__ import annotations

SPECS = {305: ('CLAIM_CONTRADICTION',
       'RELATION_ENGINE',
       'declare contradiction only when semantic claim keys align'),
 306: ('CLAIM_UNCERTAINTY', 'EPISTEMIC_PRIMITIVE', 'uncertainty type/range/cause and propagation'),
 307: ('CLAIM_SCOPE',
       'EPISTEMIC_PRIMITIVE',
       'object/context/population/environment/exclusions explicitly bounded'),
 308: ('CLAIM_TEMPORAL_VALIDITY',
       'EPISTEMIC_PRIMITIVE',
       'valid-from/until, observation date and expiry triggers')}


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
