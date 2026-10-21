#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 777-780. No certification."""
from __future__ import annotations

SPECS = {777: ('MAINTENANCE_SLA_ENGINE',
       'POLICY_ENGINE',
       'severity→response/repair/validation objectives; historical measurements'),
 778: ('MAINTENANCE_HEALTH_SCORE',
       'METRIC_ENGINE',
       'diagnosability/repairability/updateability/debt/test status vector'),
 779: ('MAINTENANCE_READINESS_GATE',
       'GATE',
       'no new capability without owner/diagnosis/update/rollback/test plan'),
 780: ('MAINTENANCE_CERTIFICATION_GATE',
       'CERTIFICATION_READINESS_GATE',
       'maintenance evidence feeds G23/G24 but does not replace them')}


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
