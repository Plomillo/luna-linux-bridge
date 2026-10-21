#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 861-864. No certification."""
from __future__ import annotations

SPECS = {861: ('SECURITY_METACOGNITIVE_DEFENSE_FABRIC',
       'SECURITY_FABRIC',
       'observe→analyze→hypothesize→recommend→authorize→act→verify; security never self-certifies'),
 862: ('SECURITY_ADVISER_REGISTRY',
       'REGISTRY',
       'advisor identity/domain/version/authority/evidence/provider'),
 863: ('DOMAIN_SECURITY_ADVISER',
       'SECURITY_COMPONENT_INTERFACE',
       'domain-specific observations/recommendations with no execution authority'),
 864: ('SECURITY_OBSERVER',
       'SECURITY_ROLE',
       'read-only collection, explicit coverage and zero mutation')}


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
