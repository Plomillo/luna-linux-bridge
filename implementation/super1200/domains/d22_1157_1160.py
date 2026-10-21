#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1157-1160. No certification."""
from __future__ import annotations

SPECS = {1157: ('THREAT_INTELLIGENCE_CONFLICT_RESOLUTION',
        'CONFLICT_ENGINE',
        'preserve conflicting intelligence and contextualize source/version/time'),
 1158: ('THREAT_KNOWLEDGE_STALENESS_ENGINE',
        'VALIDITY_ENGINE',
        'age/source supersession/indicator expiry triggers revalidation'),
 1159: ('OFFLINE_THREAT_REASONING_ENGINE',
        'DEFENSIVE_REASONING_ENGINE',
        'use locally cached validated knowledge with freshness/coverage limitations explicit'),
 1160: ('PREDICTIVE_DEFENSE_ENGINE',
        'PREDICTIVE_DEFENSIVE_ENGINE',
        'historical patterns→explicit threat hypotheses with uncertainty; predictions never '
        'treated as facts')}


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
