#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 681-684. No certification."""
from __future__ import annotations

SPECS = {681: ('REPAIRABILITY_CLASSIFIER',
       'CLASSIFIER',
       'SOFTWARE/FIRMWARE/CONFIG/MITIGATABLE/PHYSICAL/UNKNOWN with evidence'),
 682: ('REPAIR_PLAN_ENGINE',
       'PLANNER',
       'diagnosis→minimal changes→checkpoint→verification→rollback plan'),
 683: ('REPAIR_RISK_ANALYZER',
       'RISK_ENGINE',
       'blast radius, irreversibility, privilege, downtime and data-loss risk'),
 684: ('SAFE_REPAIR_SANDBOX', 'SANDBOX', 'reproduce repair against copy/VM before host')}


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
