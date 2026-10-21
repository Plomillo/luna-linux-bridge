#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 729-732. No certification."""
from __future__ import annotations

SPECS = {729: ('REASONING_STRATEGY_REGISTRY',
       'REGISTRY',
       'strategy preconditions/domain/cost/failure modes/evidence'),
 730: ('STRATEGY_SELECTION_ENGINE',
       'DECISION_ENGINE',
       'select strategy from problem class/evidence/history, explain selection'),
 731: ('STRATEGY_PERFORMANCE_HISTORY', 'LEDGER', 'strategy×problem×result×cost history'),
 732: ('EXPERT_HEURISTIC_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'heuristic source/scope/success/failure/evidence; advisory only')}


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
