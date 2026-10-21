#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1041-1044. No certification."""
from __future__ import annotations

SPECS = {1041: ('QUARANTINE_CONTINUITY_FABRIC',
        'CONTINUITY_FABRIC',
        'quarantine cannot silently destroy required capability; route to safe existing/substitute '
        'provider'),
 1042: ('QUARANTINED_UTILITY_ANALYZER',
        'ANALYZER',
        'identify legitimate function actually consumed, not implementation details'),
 1043: ('UTILITY_REQUIREMENT_EXTRACTOR',
        'REQUIREMENTS_ENGINE',
        'utility→typed functional/nonfunctional/security requirements'),
 1044: ('UTILITY_SEMANTIC_CONTRACT',
        'CONTRACT',
        'implementation-independent inputs/outputs/invariants/errors/resources')}


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
