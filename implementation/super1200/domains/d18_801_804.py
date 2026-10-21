#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 801-804. No certification."""
from __future__ import annotations

SPECS = {801: ('COMPATIBILITY_FABRIC',
       'COMPATIBILITY_FABRIC',
       'version/schema/API/ABI/platform/provider compatibility matrix and migration'),
 802: ('BACKWARD_COMPATIBILITY_GATE',
       'GATE',
       'new producer/provider tested against supported old consumers'),
 803: ('FORWARD_COMPATIBILITY_ANALYZER',
       'ANALYZER',
       'old consumer handling of newer producer/data; unknown fields semantics'),
 804: ('ROUND_TRIP_PRESERVATION_GATE', 'GATE', 'A→B→A preserves protected semantics/data')}


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
