#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1021-1024. No certification."""
from __future__ import annotations

SPECS = {1021: ('TRUSTED_REBUILD_PREFERENCE',
        'SECURITY_POLICY',
        'source-available compromised binaries default to clean reproducible rebuild'),
 1022: ('KNOWN_GOOD_COMPONENT_SUBSTITUTION',
        'RECOVERY_PATTERN',
        'replacement exact identity/provenance/compatibility, not silent'),
 1023: ('SEMANTIC_PRESERVATION_GATE',
        'GATE',
        'required information/structure meaning preserved after sanitization'),
 1024: ('FUNCTIONAL_PRESERVATION_GATE',
        'GATE',
        'allowed required functionality remains while disallowed active behavior removed')}


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
