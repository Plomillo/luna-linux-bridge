#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 909-912. No certification."""
from __future__ import annotations

SPECS = {909: ('PATCH_AVAILABILITY_ENGINE',
       'RESEARCH_ENGINE',
       'exact fixed versions/patch refs/source provenance'),
 910: ('SECURITY_PATCH_PLANNER',
       'PLANNER',
       'vuln→authorized minimal update/backport→tests→rollback'),
 911: ('SECURITY_CONFIGURATION_ANALYZER',
       'SECURITY_ANALYZER',
       'configuration vs declared policy/baseline; recommendations separated from execution'),
 912: ('SECRET_EXPOSURE_DETECTOR',
       'DETECTOR',
       'redaction, no secret echo, entropy/pattern/context, revocation workflow')}


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
