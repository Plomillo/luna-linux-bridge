#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 247-250. No certification."""
from __future__ import annotations

SPECS = {247: ('CROSS_MODEL_VALIDATION',
       'VALIDATION_ENGINE',
       'cross-check outputs without treating model agreement as G23'),
 248: ('MODEL_DISAGREEMENT_ANALYZER',
       'ANALYZER',
       'classify factual/methodological/semantic disagreement and route to uncertainty engine'),
 249: ('MULTI_AGENT_TRACE',
       'TRACE_ENGINE',
       'actor/input/output/tool/timestamps/causal parent per contribution'),
 250: ('MULTI_AGENT_PROVENANCE',
       'PROVENANCE_ENGINE',
       'composition provenance and responsibility boundaries')}


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
