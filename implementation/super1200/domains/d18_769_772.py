#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 769-772. No certification."""
from __future__ import annotations

SPECS = {769: ('ADAPTIVE_MAINTENANCE_ENGINE',
       'MAINTENANCE_ENGINE',
       'platform/API/hardware changes through compatibility and migration gates'),
 770: ('EVOLUTIONARY_MAINTENANCE_ENGINE',
       'MAINTENANCE_ENGINE',
       'feature extension through G16, architecture impact and non-regression'),
 771: ('MAINTENANCE_PRIORITY_ENGINE',
       'DECISION_ENGINE',
       'security/data-loss/regression/criticality/dependency impact before cosmetic work'),
 772: ('MAINTENANCE_COST_LEDGER',
       'LEDGER',
       'time/resources/intervention per maintained capability')}


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
