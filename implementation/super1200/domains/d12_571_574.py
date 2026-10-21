#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 571-574. No certification."""
from __future__ import annotations

SPECS = {571: ('OPENSSF_SCORECARD_ADAPTER',
       'EXT_SERVICE_TOOL_ADAPTER',
       'external signals cached with version/time; advisory only'),
 572: ('BEST_PRACTICES_SELF_AUDIT',
       'AUDIT_ENGINE',
       'periodic controls with evidence; cannot self-certify'),
 573: ('REPOSITORY_HEALTH_SCORE',
       'METRIC_ENGINE',
       'multi-dimensional repository health with source metrics'),
 574: ('MAINTAINABILITY_SCORE',
       'METRIC_ENGINE',
       'change radius, testability, repairability and debt')}


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
