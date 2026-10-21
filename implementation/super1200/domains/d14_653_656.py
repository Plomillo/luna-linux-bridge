#!/usr/bin/env python3
"""D14 reviewed name-specific material for capabilities 653-656. No certification."""
from __future__ import annotations

SPECS = {653: ('HYPOTHESIS_COMPETITION_ENGINE',
       'EPISTEMIC_ENGINE',
       'maintain alternatives, predictions and discrimination evidence'),
 654: ('BAYESIAN_BELIEF_UPDATE_ADAPTER',
       'ANALYTICS_ADAPTER',
       'only for probabilistically valid domains; priors/likelihoods explicit'),
 655: ('CONFIDENCE_CALIBRATION_ENGINE',
       'ANALYTICS_ENGINE',
       'predicted confidence versus historical outcomes by domain'),
 656: ('RESIDUAL_UNCERTAINTY_REPORT',
       'REPORT_ARTIFACT',
       'list unresolved claims, impact and tolerated/blocked status')}


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
