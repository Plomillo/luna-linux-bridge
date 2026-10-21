#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 243-246. No certification."""
from __future__ import annotations

SPECS = {243: ('CAPABILITY_AWARE_ROUTING',
       'ROUTING_ENGINE',
       'route from capability envelope and current evidence, not model brand'),
 244: ('FAILURE_AWARE_ROUTING',
       'ROUTING_ENGINE',
       'provider failure history, circuit-breakers and explicit fallback authorization'),
 245: ('REDUNDANT_REASONING',
       'REASONING_PATTERN',
       'independent redundant paths only for justified critical tasks; dedupe shared provenance'),
 246: ('DIVERSITY_ENFORCEMENT',
       'INDEPENDENCE_ENGINE',
       'measure common provider/model/data/tool ancestry; false diversity rejected')}


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
