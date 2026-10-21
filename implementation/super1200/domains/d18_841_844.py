#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 841-844. No certification."""
from __future__ import annotations

SPECS = {841: ('MAINTENANCE_INCREMENTALITY_ENGINE',
       'OPTIMIZATION_ENGINE',
       'perform only causally invalidated maintenance work'),
 842: ('MAINTENANCE_CACHE', 'CACHE', 'cache diagnostics/plans keyed by object/env/policy/version'),
 843: ('VALIDATION_CACHE',
       'CACHE',
       'valid test evidence keyed by exact inputs/environment/criteria'),
 844: ('CERTIFICATION_CACHE',
       'EVIDENCE_CACHE',
       'cache evidence fragments only; never cached G24 authority for new subject')}


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
