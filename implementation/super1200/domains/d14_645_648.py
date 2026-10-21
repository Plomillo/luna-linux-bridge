#!/usr/bin/env python3
"""D14 reviewed name-specific material for capabilities 645-648. No certification."""
from __future__ import annotations

SPECS = {645: ('UNCERTAINTY_LEDGER',
       'LEDGER',
       'origin/state/evidence/actions/residual/closure history append-only'),
 646: ('UNCERTAINTY_DEPENDENCY_GRAPH',
       'GRAPH',
       'unknown→claims→decisions→operations reverse propagation'),
 647: ('UNCERTAINTY_PROPAGATION_ENGINE',
       'EPISTEMIC_ENGINE',
       'uncertainty cannot disappear through transforms without evidence'),
 648: ('QUESTION_FROM_UNCERTAINTY_ENGINE',
       'REASONING_ENGINE',
       'convert uncertainty origin to falsifiable/observable questions')}


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
