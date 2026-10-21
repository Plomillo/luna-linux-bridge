#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 547-550. No certification."""
from __future__ import annotations

SPECS = {547: ('ADR_REGISTRY',
       'DECISION_REGISTRY',
       'immutable ADR versions, supersession and evidence links'),
 548: ('DECISION_ID', 'IDENTITY_PRIMITIVE', 'stable unique decision identity'),
 549: ('DECISION_CONTEXT', 'DECISION_RECORD', 'problem, constraints, assumptions, time and scope'),
 550: ('ALTERNATIVES_CONSIDERED',
       'DECISION_RECORD',
       'alternatives and rejection evidence preserved')}


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
