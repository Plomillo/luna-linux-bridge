#!/usr/bin/env python3
"""D10 reviewed name-specific material for capabilities 470-473. No certification."""
from __future__ import annotations

SPECS = {470: ('ENGINE_SECURITY_TEMPLATE',
       'TEMPLATE',
       'threat model, privileges, network/filesystem scope, secrets and incident controls'),
 471: ('ENGINE_CERTIFICATION_TEMPLATE',
       'TEMPLATE',
       'claims/evidence/tests/G23/G24/scope/exclusions/auth separation'),
 472: ('ENGINE_DEPENDENCY_ANALYZER',
       'ANALYZER',
       'direct/transitive/native/runtime deps and hidden dynamic deps'),
 473: ('ENGINE_NON_DUPLICATION_GATE',
       'G16_GATE',
       'semantic/provider overlap check before new engine implementation')}


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
