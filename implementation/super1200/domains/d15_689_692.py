#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 689-692. No certification."""
from __future__ import annotations

SPECS = {689: ('DRIVER_REPAIR_ENGINE',
       'REPAIR_ENGINE',
       'current/target compatibility, package provenance, fallback driver and rollback'),
 690: ('FIRMWARE_UPDATE_ORCHESTRATOR',
       'UPDATE_ORCHESTRATOR',
       'exact hardware match, power preconditions, signed firmware, recovery availability'),
 691: ('PERFORMANCE_REGRESSION_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'baseline/change chronology, resource components and causality tests'),
 692: ('BLOAT_ATTRIBUTION_ENGINE',
       'ANALYZER',
       'attribute RAM/CPU/disk to process/package/service over time')}


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
