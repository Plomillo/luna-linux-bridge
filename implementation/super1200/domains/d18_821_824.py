#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 821-824. No certification."""
from __future__ import annotations

SPECS = {821: ('UPDATE_FABRIC',
       'UPDATE_FABRIC',
       'classify→risk→preflight→simulate→canary→rollout→health→rollback→cert impact'),
 822: ('UPDATE_CLASSIFIER',
       'CLASSIFIER',
       'SECURITY/BUGFIX/COMPATIBILITY/FEATURE/MAJOR_MIGRATION with evidence'),
 823: ('UPDATE_RISK_SCORER',
       'RISK_ENGINE',
       'criticality/change radius/security/irreversibility/provider trust'),
 824: ('PATCH_ELIGIBILITY_GATE',
       'GATE',
       'fix scope, evidence, minimality, tests and target compatibility')}


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
