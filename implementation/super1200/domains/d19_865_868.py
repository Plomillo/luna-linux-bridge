#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 865-868. No certification."""
from __future__ import annotations

SPECS = {865: ('SECURITY_ANALYST',
       'SECURITY_ENGINE',
       'signals→hypotheses/evidence/uncertainty; no automatic verdict'),
 866: ('SECURITY_RECOMMENDER',
       'SECURITY_ENGINE',
       'proposed actions include evidence/risk/rollback and require authorization'),
 867: ('SECURITY_EXECUTOR_BOUNDARY',
       'AUTHORITY_BOUNDARY',
       'hard separation observer/analyst/recommender/executor'),
 868: ('SECURITY_AUTHORIZATION_GATE',
       'AUTHORIZATION_GATE',
       'UNKNOWN/CONFLICT/insufficient authority→DENY; least privilege and expiry')}


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
