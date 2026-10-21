#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 961-964. No certification."""
from __future__ import annotations

SPECS = {961: ('SUSPICIOUS_OBJECT_INTAKE',
       'SECURITY_WORKFLOW',
       'object identity, source, hash, reason, risk and chain-of-custody before handling'),
 962: ('AUTOMATIC_CONTAINMENT_GATE',
       'SECURITY_GATE',
       'preauthorized containment criteria; destructive action excluded'),
 963: ('QUARANTINE_FABRIC',
       'SECURITY_FABRIC',
       'content-addressed storage+ACL+network/execution isolation+evidence+expiry'),
 964: ('CONTENT_ADDRESSED_QUARANTINE',
       'STORE',
       'quarantined object keyed by cryptographic identity, immutable original')}


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
