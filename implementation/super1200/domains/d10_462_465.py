#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 462-465. No certification."""
from __future__ import annotations

SPECS = {462: ('CAPABILITY_EXTENSION_FACTORY',
       'FACTORY',
       'extend existing contract only after G16 and compatibility analysis'),
 463: ('COGNITIVE_EXTENSION_FACTORY',
       'FACTORY',
       'cognitive extension remains subordinate, evidence-bound and non-authoritative'),
 464: ('ENGINE_INTERFACE_GENERATOR',
       'FACTORY_TOOL',
       'generate typed API/interface from canonical capability contract'),
 465: ('ENGINE_MANIFEST_GENERATOR',
       'FACTORY_TOOL',
       'manifest includes identity/version/provider/deps/resources/evidence/rollback')}


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
