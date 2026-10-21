#!/usr/bin/env python3
"""D17 reviewed name-specific material for capabilities 737-740. No certification."""
from __future__ import annotations

SPECS = {737: ('BLUE_TEAM_ENGINE',
       'ASSURANCE_ROLE_ENGINE',
       'respond to evidenced weaknesses and verify fixes'),
 738: ('DEVILS_ADVOCATE_ENGINE',
       'REASONING_ENGINE',
       'generate strongest counterposition; never treated as evidence by itself'),
 739: ('SENIOR_REVIEW_PROTOCOL',
       'REVIEW_PROTOCOL',
       'architecture/security/operations/tests/maintainability roles with independent findings'),
 740: ('WISDOM_CONSTRAINT_ENGINE',
       'DECISION_GATE',
       'benefit/necessity/timing/risk/complexity/reversibility before technically possible work')}


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
