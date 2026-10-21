#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 885-888. No certification."""
from __future__ import annotations

SPECS = {885: ('BEHAVIORAL_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'observed behaviors in isolated environment; no offensive automation'),
 886: ('STATIC_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'format-aware parsing under resource/sandbox controls'),
 887: ('DYNAMIC_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'authorized isolated execution with no uncontrolled Internet/host access'),
 888: ('MALWARE_SANDBOX',
       'SANDBOX',
       'ephemeral, network-isolated, resource-capped, reset-verified')}


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
