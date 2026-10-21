#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 497-500. No certification."""
from __future__ import annotations

SPECS = {497: ('REPEATED_WORK_DETECTOR',
       'ANALYZER',
       'cluster equivalent mission steps by semantic contract'),
 498: ('HUMAN_FRICTION_DETECTOR',
       'ANALYTICS_ENGINE',
       'manual steps/retries/interruptions measured, no personality inference'),
 499: ('MODEL_FRICTION_DETECTOR',
       'ANALYTICS_ENGINE',
       'model-related retries/errors/escalations attributed only with evidence'),
 500: ('INFRASTRUCTURE_GAP_INFERENCE',
       'METACOGNITIVE_ANALYZER',
       'repeated failures→candidate missing capability, routed through G16 before creation')}


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
