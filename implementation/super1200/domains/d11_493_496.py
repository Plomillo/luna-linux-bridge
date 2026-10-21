#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 493-496. No certification."""
from __future__ import annotations

SPECS = {493: ('RUNBOOK_GENERATOR',
       'FACTORY_TOOL',
       'generate executable/checkable steps from procedures and contracts'),
 494: ('RUNBOOK_VALIDATOR',
       'VALIDATION_ENGINE',
       'execute in sandbox/fixture, verify pre/post/failure/rollback'),
 495: ('RUNBOOK_PROMOTION',
       'PROMOTION_GATE',
       'only validated runbook becomes governed capability/procedure; no certification '
       'inheritance'),
 496: ('AUTOMATION_OPPORTUNITY_DETECTOR',
       'ANALYZER',
       'repetition/cost/error evidence; proposal only')}


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
