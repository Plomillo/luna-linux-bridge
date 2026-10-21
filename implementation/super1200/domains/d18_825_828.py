#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 825-828. No certification."""
from __future__ import annotations

SPECS = {825: ('PATCH_MINIMALITY_ANALYZER',
       'ANALYZER',
       'detect unrelated refactors/features in corrective patch'),
 826: ('PATCH_DEPENDENCY_ANALYZER',
       'ANALYZER',
       'hidden prerequisites/adjacent commits/version dependencies'),
 827: ('PATCH_BACKPORT_ENGINE',
       'PATCH_ENGINE',
       'adapt fix to older line with tests; never blind cherry-pick'),
 828: ('PATCH_FORWARD_PORT_ENGINE',
       'PATCH_ENGINE',
       'propagate corrected semantics to newer branches')}


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
