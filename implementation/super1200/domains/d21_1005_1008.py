#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1005-1008. No certification."""
from __future__ import annotations

SPECS = {1005: ('CONTENT_VALUE_CLASSIFIER',
        'CLASSIFIER',
        'essential information/legitimate active function/disposable executable metadata'),
 1006: ('SANITIZATION_FEASIBILITY_ENGINE',
        'DECISION_ENGINE',
        'safety+semantic/function preservation feasibility; otherwise '
        'HOLD/extraction/substitution'),
 1007: ('SURGICAL_REMOVAL_PLANNER',
        'PLANNER',
        'minimal components/actions to remove while preserving required content'),
 1008: ('SAFE_RECONSTRUCTION_ENGINE',
        'SANITIZATION_ENGINE',
        'rebuild from explicitly accepted components rather than mutate opaque binary when '
        'possible')}


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
