#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 301-304. No certification."""
from __future__ import annotations

SPECS = {301: ('CLAIM_REGISTRY',
       'EPISTEMIC_REGISTRY',
       'claim ID plus semantic key subject/property/scope/context/version/time/unit'),
 302: ('CLAIM_IDENTITY',
       'IDENTITY_PRIMITIVE',
       'record identity separate from semantic claim key; collision checks'),
 303: ('CLAIM_EVIDENCE_GRAPH',
       'GRAPH',
       'support/refute/unknown/conflict edges with scope and provenance'),
 304: ('CLAIM_SUPPORT',
       'RELATION_TYPE',
       'support strength/method/scope explicit; no inferred support by proximity')}


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
