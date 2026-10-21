#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 673-676. No certification."""
from __future__ import annotations

SPECS = {673: ('FIRMWARE_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'device/current/latest/security/compatibility and signature evidence'),
 674: ('DRIVER_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'hardware/driver/kernel/firmware compatibility and error logs'),
 675: ('KERNEL_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'warnings/oops/stalls/module states with time correlation'),
 676: ('BOOT_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'boot chain/services/timing/failures against known-good baseline')}


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
