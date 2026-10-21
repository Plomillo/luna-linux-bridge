#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 505-508. No certification."""
from __future__ import annotations

SPECS = {505: ('INFORMATION_GAIN_ESTIMATOR',
       'ANALYTICS_ENGINE',
       'expected decision-relevant uncertainty reduction'),
 506: ('EXPERIMENT_VALUE_ESTIMATOR',
       'ANALYTICS_ENGINE',
       'expected information/decision gain versus cost/risk'),
 507: ('STOP_RESEARCH_CRITERIA', 'POLICY', 'closure criteria defined before unbounded research'),
 508: ('DIMINISHING_RETURNS_DETECTOR',
       'ANALYTICS_ENGINE',
       'marginal evidence/information gain trend')}


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
