#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 857-860. No certification."""
from __future__ import annotations

SPECS = {857: ('TOIL_ELIMINATION_ENGINE',
       'AUTOMATION_FACTORY',
       'toil→candidate automation→tests→G16→admission'),
 858: ('MAINTENANCE_COST_REGRESSION_GATE',
       'GATE',
       'block unjustified material increase in maintenance cost'),
 859: ('MAINTAINABILITY_NON_REGRESSION_GATE',
       'GATE',
       'changes cannot silently reduce diagnosability/repairability/updateability/rollback'),
 860: ('MAINTENANCE_COMPRESSION_RATIO',
       'METRIC_ENGINE',
       'functional coverage per unit human maintenance with quality constraints')}


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
