#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 317-320. No certification."""
from __future__ import annotations

SPECS = {317: ('NEGATIVE_RESULT_REGISTRY',
       'REGISTRY',
       'negative experiments/failures searchable by scope and cause'),
 318: ('UNKNOWN_REGISTRY',
       'REGISTRY',
       'unknown reason, affected decisions, owner, required evidence and escalation'),
 319: ('HISTORICAL_METHOD_ENGINE',
       'DOMAIN_ENGINE',
       'source criticism, chronology, provenance, context and inference boundaries'),
 320: ('PRIMARY_SOURCE_REGISTRY',
       'SOURCE_REGISTRY',
       'source identity, edition, location, date, authenticity status and hash')}


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
