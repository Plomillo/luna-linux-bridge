#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 853-856. No certification."""
from __future__ import annotations

SPECS = {853: ('STORAGE_PRESSURE_MANAGER',
       'RESOURCE_ENGINE',
       'prioritize transient caches before evidence/checkpoints/rollback roots'),
 854: ('MAINTENANCE_PARALLELIZER',
       'SCHEDULER',
       'parallelize only independent maintenance DAG nodes within budgets'),
 855: ('MAINTENANCE_CRITICAL_PATH',
       'ANALYZER',
       'duration/resource critical path from observed task graph'),
 856: ('TOIL_DETECTOR', 'ANALYZER', 'repeated manual maintenance frequency/cost/error evidence')}


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
