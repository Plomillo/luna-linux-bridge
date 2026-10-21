#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 741-744. No certification."""
from __future__ import annotations

SPECS = {741: ('LIFETIME_ARCHITECTURE_FABRIC',
       'LONGEVITY_FABRIC',
       'provider-independent contracts, reconstructability, migration, archival and succession'),
 742: ('TECHNOLOGY_OBSOLESCENCE_WATCH',
       'MONITOR',
       'support/EOL/security/format/provider status with timestamps'),
 743: ('CAPABILITY_SUCCESSION_ENGINE',
       'EVOLUTION_ENGINE',
       'provider replacement preserving capability identity; new evidence mandatory'),
 744: ('FORMAT_LONGEVITY_ENGINE',
       'LONGEVITY_ENGINE',
       'document format openness/tool availability/reconstruction/migration plan')}


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
