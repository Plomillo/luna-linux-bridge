#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 610-613. No certification."""
from __future__ import annotations

SPECS = {610: ('HOW_TO_GENERATOR', 'CONTENT_ENGINE', 'task prerequisites/steps/verification/rollback'),
 611: ('TUTORIAL_GENERATOR', 'CONTENT_ENGINE', 'guided learning sequence with verified exercises'),
 612: ('DIATAXIS_CLASSIFIER',
       'CLASSIFIER',
       'classify tutorial/how-to/reference/explanation with multi-label exceptions'),
 613: ('EXPOSITORY_ARCHITECTURE_ENGINE',
       'CONTENT_ENGINE',
       'prerequisites→concept→mechanism→example→limits structure')}


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
