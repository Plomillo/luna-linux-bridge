#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 283-286. No certification."""
from __future__ import annotations

SPECS = {283: ('OPERATIONS_RESEARCH_ENGINE',
       'DECISION_ENGINE',
       'decision variables, constraints, objective, scenarios and sensitivity'),
 284: ('UNCERTAINTY_QUANTIFICATION',
       'ANALYSIS_ENGINE',
       'aleatory/epistemic distinction and confidence/credible intervals'),
 285: ('SENSITIVITY_ANALYSIS', 'ANALYSIS_ENGINE', 'rank assumptions/parameters by output impact'),
 286: ('QUALITATIVE_RESEARCH_FABRIC',
       'RESEARCH_FABRIC',
       'corpus/coding/memos/audit trail and interpretive distinction')}


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
