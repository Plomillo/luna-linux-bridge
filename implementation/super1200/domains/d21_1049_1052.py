#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1049-1052. No certification."""
from __future__ import annotations

SPECS = {1049: ('TRUSTED_SOURCE_SUBSTITUTION',
        'RECOVERY_PATTERN',
        'trusted source+exact version/hash+compatibility; no identity masquerading'),
 1050: ('FUNCTIONAL_EQUIVALENCE_ANALYZER',
        'VALIDATION_ENGINE',
        'differential tests against utility contract, not brand/name'),
 1051: ('SAFE_SUBSTITUTE_FACTORY',
        'FACTORY',
        'only if no adequate existing provider; clean-room, minimal scope, full evidence'),
 1052: ('CLEAN_ROOM_REQUIREMENTS',
        'SECURITY_CONTRACT',
        'requirements isolated from dangerous implementation content and provenance documented')}


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
