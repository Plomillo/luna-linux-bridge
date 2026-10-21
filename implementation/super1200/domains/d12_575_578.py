#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 575-578. No certification."""
from __future__ import annotations

SPECS = {575: ('DEPENDENCY_RISK_SCORE',
       'RISK_ENGINE',
       'provenance/vulnerability/maintenance/license/transitive exposure'),
 576: ('SECURITY_POSTURE_SCORE', 'RISK_METRIC', 'control/evidence vector, not proof of security'),
 577: ('REPRODUCIBILITY_SCORE', 'METRIC_ENGINE', 'environment/build/test/replay coverage'),
 578: ('TRACEABILITY_SCORE',
       'METRIC_ENGINE',
       'requirement→claim→implementation→test→evidence chain coverage')}


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
