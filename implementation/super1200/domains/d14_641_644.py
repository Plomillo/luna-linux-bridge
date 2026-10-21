#!/usr/bin/env python3
"""D14 reviewed name-specific material for capabilities 641-644. No certification."""
from __future__ import annotations

SPECS = {641: ('UNCERTAINTY_REDUCTION_FABRIC',
       'EPISTEMIC_FABRIC',
       'UNKNOWN→origin→hypotheses→evidence gaps→tests→residual uncertainty→closure/reopen'),
 642: ('UNCERTAINTY_ORIGIN_ANALYZER',
       'ANALYZER',
       'classify missing data, contradiction, ambiguity, inaccessible state, model limits or '
       'causal gap'),
 643: ('UNCERTAINTY_TAXONOMY',
       'ONTOLOGY',
       'epistemic/aleatory/instrumental/temporal/semantic/causal/operational/identity classes'),
 644: ('UNCERTAINTY_BUDGET',
       'POLICY',
       'tolerances defined before decision; critical UNKNOWN remains deny')}


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
