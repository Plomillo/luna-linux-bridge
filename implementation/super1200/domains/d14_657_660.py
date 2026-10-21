#!/usr/bin/env python3
"""D14 reviewed name-specific material for capabilities 657-660. No certification."""
from __future__ import annotations

SPECS = {657: ('UNCERTAINTY_CLOSURE_CRITERIA',
       'POLICY/GATE',
       'predefined evidence/decision threshold; closure is scoped, not absolute truth'),
 658: ('UNCERTAINTY_REOPENING_ENGINE',
       'STATE_ENGINE',
       'new contradictory/stale evidence reopens closure and invalidates dependents'),
 659: ('UNKNOWN_ESCALATION_ENGINE',
       'ESCALATION_ENGINE',
       'escalate blocker by criticality/age/dependency impact; no silent bypass'),
 660: ('UNCERTAINTY_KILL_RECEIPT',
       'RECEIPT',
       'initial unknown→hypotheses→tests→evidence→decision→residual')}


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
