#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 630-633. No certification."""
from __future__ import annotations

SPECS = {630: ('PROGRESSIVE_DISCLOSURE_ENGINE',
       'PRESENTATION_ENGINE',
       'layers preserve correctness while adding depth'),
 631: ('EXPERTISE_LEVEL_ADAPTER',
       'PRESENTATION_ADAPTER',
       'change exposition, never underlying facts/contracts'),
 632: ('TEACH_BACK_ENGINE',
       'ASSESSMENT_ENGINE',
       'compare learner reconstruction to objective/rubric with uncertainty'),
 633: ('TRANSFER_ASSESSMENT_ENGINE',
       'ASSESSMENT_ENGINE',
       'novel-task evaluation distinct from memorized examples')}


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
