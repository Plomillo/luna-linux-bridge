#!/usr/bin/env python3
"""D14 reviewed name-specific material for capabilities 649-652. No certification."""
from __future__ import annotations

SPECS = {649: ('EVIDENCE_GAP_ANALYZER',
       'ANALYZER',
       'claim acceptance criteria minus current valid evidence'),
 650: ('INFORMATION_ACQUISITION_PLANNER',
       'PLANNER',
       'select local inspection/research/experiment/provider based on cost/risk/value'),
 651: ('VALUE_OF_INFORMATION_ENGINE',
       'DECISION_ENGINE',
       'estimate expected decision impact of additional evidence'),
 652: ('CHEAPEST_DISCRIMINATING_TEST',
       'TEST_PLANNER',
       'minimize cost/risk while separating live hypotheses')}


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
