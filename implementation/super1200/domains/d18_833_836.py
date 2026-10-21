#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 833-836. No certification."""
from __future__ import annotations

SPECS = {833: ('UPDATE_STAGED_ROLLOUT',
       'DEPLOYMENT_ENGINE',
       'progressive cohorts gated by observed health'),
 834: ('UPDATE_HEALTH_MONITOR',
       'MONITOR',
       'post-update functional/performance/security/error signals and freshness'),
 835: ('UPDATE_ABORT_ENGINE',
       'CONTROL_ENGINE',
       'stop rollout on explicit negative predicates; preserve evidence'),
 836: ('UPDATE_AUTO_ROLLBACK',
       'RECOVERY_ENGINE',
       'bounded preauthorized rollback followed by live verification')}


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
