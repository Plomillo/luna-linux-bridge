#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 697-700. No certification."""
from __future__ import annotations

SPECS = {697: ('OPTIMIZATION_CAUSALITY_GATE',
       'GATE',
       'control noise/repeats/alternative causes before attributing improvement'),
 698: ('OPTIMIZATION_ROLLBACK',
       'RECOVERY_PATTERN',
       'every optimization has exact revert target and post-rollback benchmark'),
 699: ('HARDWARE_SERVICE_RECOMMENDER',
       'DECISION_ENGINE',
       'recommend physical service only when software/firmware repair excluded or insufficient'),
 700: ('DO_NOT_FAKE_REPAIR_CONTROL',
       'SAFETY_GATE',
       'mitigation≠repair; physical degradation remains explicit')}


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
