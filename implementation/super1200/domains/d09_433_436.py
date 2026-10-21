#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 433-436. No certification."""
from __future__ import annotations

SPECS = {433: ('ROOT_ROTATION',
       'TRUST_ENGINE',
       'threshold-authorized root succession and historical verification'),
 434: ('UPDATE_CHANNELS',
       'UPDATE_POLICY',
       'stable/candidate/experimental identities, promotion criteria and no silent channel hop'),
 435: ('CANARY_DEPLOYMENT',
       'DEPLOYMENT_ENGINE',
       'bounded population/time, success/fail thresholds and rollback target'),
 436: ('STAGED_ROLLOUT', 'DEPLOYMENT_ENGINE', 'progressive stages gated by health/evidence')}


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
