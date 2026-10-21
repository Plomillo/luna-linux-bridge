#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 669-672. No certification."""
from __future__ import annotations

SPECS = {669: ('GPU_HEALTH_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'driver/memory/temp/clocks/errors with vendor-neutral contract'),
 670: ('RAM_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'non-destructive first; offline destructive tests only authorized; error evidence retained'),
 671: ('STORAGE_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'device identity, health counters, errors, temperatures and trend'),
 672: ('FILESYSTEM_HEALTH_ENGINE',
       'DIAGNOSTIC_ENGINE',
       'read-only inspection by default; repair separated to 688')}


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
