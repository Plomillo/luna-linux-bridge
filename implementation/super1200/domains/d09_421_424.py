#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 421-424. No certification."""
from __future__ import annotations

SPECS = {421: ('AB_UPDATE_PROVIDER',
       'UPDATE_PROVIDER',
       'slot identity, atomic switch, boot-success marker and fallback'),
 422: ('RECOVERY_IMAGE_FACTORY',
       'FACTORY',
       'minimal signed recovery image, offline tools and restore tests'),
 423: ('HARDWARE_ABSTRACTION_REGISTRY',
       'REGISTRY',
       'machine/model/component/firmware/driver compatibility entries'),
 424: ('DEVICE_TREE_PROVIDER',
       'OS_COMPONENT_PROVIDER',
       'DT source/binary hash, hardware target and overlay provenance')}


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
