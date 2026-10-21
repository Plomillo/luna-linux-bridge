#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 725-728. No certification."""
from __future__ import annotations

SPECS = {725: ('FOURTH_ORDER_ARCHITECTURE',
       'ARCHITECTURE_LAYER',
       'evaluate structures that create/change governance rules'),
 726: ('FIFTH_ORDER_EVOLUTION',
       'EVOLUTION_LAYER',
       'evaluate mechanisms by which architecture evolves itself; no self-authorization'),
 727: ('NTH_ORDER_EXTENSION_INTERFACE',
       'EXTENSION_INTERFACE',
       'future orders require new explicit identity/contracts without redefining 721–726'),
 728: ('META_ASSUMPTION_REGISTRY',
       'REGISTRY',
       'assumption identity, dependencies, evidence and falsification status')}


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
