#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 489-492. No certification."""
from __future__ import annotations

SPECS = {489: ('ARCHITECTURAL_COST_BASELINE',
       'BASELINE',
       'versioned cost distributions by mission/capability'),
 490: ('COST_REGRESSION_DETECTOR',
       'REGRESSION_ENGINE',
       'statistical/threshold detection against comparable baselines'),
 491: ('COST_IMPROVEMENT_DETECTOR',
       'ANALYTICS_ENGINE',
       'quantify improvement with confidence and no quality regression'),
 492: ('PROCEDURE_SYNTHESIS',
       'KNOWLEDGE_ENGINE',
       'repeatable successful patterns→candidate procedure; human/gate review before promotion')}


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
