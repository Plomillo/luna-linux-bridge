#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 579-582. No certification."""
from __future__ import annotations

SPECS = {579: ('AUDITABILITY_SCORE', 'METRIC_ENGINE', 'event coverage/integrity/reconstructability'),
 580: ('CERTIFIABILITY_SCORE',
       'READINESS_METRIC',
       'evidence/gate readiness only; cannot imply certification'),
 581: ('PORTABILITY_SCORE',
       'METRIC_ENGINE',
       'platform assumptions/provider coupling/migration tests'),
 582: ('SELF_HOSTING_SCORE',
       'METRIC_ENGINE',
       'external service/runtime dependency vector and offline fallback')}


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
