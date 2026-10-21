#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 661-664. No certification."""
from __future__ import annotations

SPECS = {661: ('MACHINE_HEALTH_FABRIC',
       'DIAGNOSTIC_FABRIC',
       'hardware/firmware/kernel/driver/software evidence joined without conflation'),
 662: ('HARDWARE_INVENTORY_ENGINE',
       'DISCOVERY_ENGINE',
       'stable hardware IDs, firmware, buses and observed timestamps'),
 663: ('SENSOR_TELEMETRY_ENGINE',
       'OBSERVABILITY_ENGINE',
       'sensor identity/unit/range/freshness and unavailable sensors as UNKNOWN'),
 664: ('BATTERY_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'design/current capacity, cycles, temperature and uncertainty')}


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
