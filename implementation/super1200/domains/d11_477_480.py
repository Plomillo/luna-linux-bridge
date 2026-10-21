#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 477-480. No certification."""
from __future__ import annotations

SPECS = {477: ('EXPERIENCE_LEDGER',
       'LEDGER',
       'append-only missions/results/failures/solutions/costs linked to exact capability/provider '
       'versions'),
 478: ('MISSION_HISTORY',
       'LEDGER_VIEW',
       'mission identity, intent, DAG, actions, evidence, terminal state'),
 479: ('MISSION_CLASSIFIER',
       'CLASSIFIER',
       'classification rules/version, multi-label and uncertainty'),
 480: ('SOLUTION_PATTERN_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'pattern preconditions, successful versions and evidence')}


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
