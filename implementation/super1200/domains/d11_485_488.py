#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 485-488. No certification."""
from __future__ import annotations

SPECS = {485: ('RETRY_COST_LEDGER',
       'METRIC_LEDGER',
       'retry count/time/resources/cause and blind-retry violations'),
 486: ('RESEARCH_COST_LEDGER', 'METRIC_LEDGER', 'query/source/time/tool cost and information gain'),
 487: ('VALIDATION_COST_LEDGER', 'METRIC_LEDGER', 'test/G23 effort and resource costs by scope'),
 488: ('CERTIFICATION_COST_LEDGER',
       'METRIC_LEDGER',
       'G24/evidence preparation cost without incentivizing gate reduction')}


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
