#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 877-880. No certification."""
from __future__ import annotations

SPECS = {877: ('FALSE_NEGATIVE_REGISTRY',
       'REGISTRY',
       'missed threat/rule/tool/version/cause and corrective tests'),
 878: ('SECURITY_REGRESSION_ENGINE',
       'REGRESSION_ENGINE',
       'new changes/rules/providers tested against historical security corpus'),
 879: ('SECURITY_SELF_CRITIC',
       'METACOGNITIVE_ENGINE',
       'challenge own findings/assumptions/evidence/alternatives; advisory only'),
 880: ('SECURITY_NON_SELF_CERTIFICATION',
       'GOVERNANCE_GATE',
       'security producer cannot be sole G23/G24 actor')}


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
