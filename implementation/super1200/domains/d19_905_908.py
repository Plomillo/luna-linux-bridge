#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 905-908. No certification."""
from __future__ import annotations

SPECS = {905: ('VULNERABILITY_APPLICABILITY_ENGINE',
       'SECURITY_ANALYZER',
       'installed component/version/config/platform match before vulnerable claim'),
 906: ('REACHABILITY_SECURITY_ANALYZER',
       'SECURITY_ANALYZER',
       'vulnerable component→actual call/data path reachability with uncertainty'),
 907: ('EXPLOITABILITY_CONTEXT_ENGINE',
       'RISK_ENGINE',
       'exposure/privilege/config/preconditions/mitigations contextualized defensively'),
 908: ('VULNERABILITY_PRIORITY_ENGINE',
       'DECISION_ENGINE',
       'applicability/reachability/exposure/impact/patch availability; CVSS alone insufficient')}


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
