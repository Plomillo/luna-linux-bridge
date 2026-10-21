#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1053-1056. No certification."""
from __future__ import annotations

SPECS = {1053: ('SAFE_REIMPLEMENTATION_PLANNER',
        'PLANNER',
        'requirements→architecture→dependencies→tests→security→rollback without copying unsafe '
        'code'),
 1054: ('MINIMAL_SUBSTITUTE_ENGINE',
        'IMPLEMENTATION_ENGINE',
        'implement only required utility; no feature creep/unsafe legacy behavior'),
 1055: ('SUBSTITUTE_PROVIDER_FACTORY',
        'FACTORY',
        'wrap safe implementation as provider without changing capability identity'),
 1056: ('SUBSTITUTE_SANDBOX', 'SANDBOX', 'candidate isolated until security/function tests pass')}


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
