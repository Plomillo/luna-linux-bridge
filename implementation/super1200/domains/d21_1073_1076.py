#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1073-1076. No certification."""
from __future__ import annotations

SPECS = {1073: ('SUBSTITUTE_INDEPENDENT_VALIDATION',
        'G23_INTERFACE',
        'independent validator reconstructs candidate evidence'),
 1074: ('SUBSTITUTE_CERTIFICATION',
        'G24_INTERFACE',
        'scope-limited certification only after favorable 1073'),
 1075: ('SUBSTITUTE_CANARY',
        'DEPLOYMENT_ENGINE',
        'limited authorized exposure and health monitoring'),
 1076: ('SUBSTITUTE_PROMOTION_ENGINE',
        'PROMOTION_ENGINE',
        'EXPERIMENTAL→CANDIDATE→VALIDATED→CERTIFIED→ACTIVE with separate operational auth')}


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
