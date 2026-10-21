#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 634-637. No certification."""
from __future__ import annotations

SPECS = {634: ('PEDAGOGICAL_EVIDENCE_LEDGER',
       'LEDGER',
       'what taught/practiced/assessed/results with data minimization'),
 635: ('LEARNING_ANALYTICS_ENGINE',
       'ANALYTICS_ENGINE',
       'aggregate learning friction/error patterns; avoid unsupported profiling'),
 636: ('PEDAGOGICAL_COST_LEDGER',
       'METRIC_LEDGER',
       'time/attempts/friction per competency and version'),
 637: ('EXPLANATION_QUALITY_GATE',
       'QUALITY_GATE',
       'accuracy/clarity/prerequisites/examples/fact-inference separation')}


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
