#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 481-484. No certification."""
from __future__ import annotations

SPECS = {481: ('FAILED_PATTERN_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'failed route, context, cause and avoid/retry conditions'),
 482: ('ROOT_CAUSE_PATTERN_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'root cause backed by incident/evidence, not symptom labels'),
 483: ('REPAIR_PATTERN_REGISTRY',
       'KNOWLEDGE_REGISTRY',
       'repair prerequisites, steps, risks, tests and rollback'),
 484: ('TIME_TO_RESOLUTION_LEDGER',
       'METRIC_LEDGER',
       'clock definitions, pause states and mission-class comparison')}


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
