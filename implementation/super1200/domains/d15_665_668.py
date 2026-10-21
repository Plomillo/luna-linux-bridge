#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 665-668. No certification."""
from __future__ import annotations

SPECS = {665: ('BATTERY_DEGRADATION_MODEL',
       'DIAGNOSTIC_MODEL',
       'physical degradation separated from calibration/config symptoms'),
 666: ('POWER_MANAGEMENT_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'governors/states/wakeups/consumption observed read-only first'),
 667: ('THERMAL_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'temperature/throttling/sustained loads with hardware limits'),
 668: ('CPU_HEALTH_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'errors/frequency/throttling/load and historical baseline')}


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
