#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 757-760. No certification."""
from __future__ import annotations

SPECS = {757: ('ECOSYSTEM_NON_DUPLICATION_GATE',
       'G16_GATE',
       'compare semantic functions/providers with entire registry before admission'),
 758: ('AMBITION_EXPANSION_ENGINE',
       'PLANNER',
       'goal→missing capability/dependency/evidence map, never auto-create'),
 759: ('AMBITION_CONTRACTION_ENGINE',
       'DECOMMISSION_PLANNER',
       'identify safely removable providers/caches/services while retaining history/rollback'),
 760: ('ANTI_HEADACHE_SCORE',
       'METRIC_ENGINE',
       'human interventions/time/retries/searches/manual steps/recurrent failures/recovery')}


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
