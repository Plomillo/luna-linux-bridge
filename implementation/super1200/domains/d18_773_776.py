#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 773-776. No certification."""
from __future__ import annotations

SPECS = {773: ('MAINTENANCE_DEBT_LEDGER', 'LEDGER', 'deferred work/reason/risk/owner/due trigger'),
 774: ('MAINTENANCE_DEBT_INTEREST',
       'METRIC_ENGINE',
       'measure extra future work/outage/risk caused by deferral'),
 775: ('MAINTENANCE_BUDGET_ENGINE',
       'RESOURCE_PLANNER',
       'allocate time/resources by criticality/debt/return'),
 776: ('MAINTENANCE_WINDOW_ENGINE',
       'SCHEDULER',
       'choose window from dependencies/load/recovery availability/authorization')}


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
