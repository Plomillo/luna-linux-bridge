#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 805-808. No certification."""
from __future__ import annotations

SPECS = {805: ('VERSION_SKEW_POLICY', 'POLICY', 'explicit supported version combinations and expiry'),
 806: ('COMPATIBILITY_MATRIX',
       'MATRIX/REGISTRY',
       'provider×API×runtime×OS×arch plus evidence/date'),
 807: ('DEPRECATION_REGISTRY',
       'REGISTRY',
       'deprecated object/replacement/reason/notice/migration/retirement conditions'),
 808: ('DEPRECATION_CLOCK',
       'POLICY_ENGINE',
       'notice→migration→retirement deadlines with exception governance')}


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
