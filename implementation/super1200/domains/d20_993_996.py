#!/usr/bin/env python3
"""D20 reviewed name-specific material for capabilities 993-996. No certification."""
from __future__ import annotations

SPECS = {993: ('COMPROMISE_RECOVERY_ENGINE',
       'RECOVERY_ENGINE',
       'reuse recovery contract/checkpoints; restore known-good components, not blind cleaning'),
 994: ('POST_ERADICATION_VERIFICATION',
       'VALIDATION_ENGINE',
       'rescans/baseline/process/network/persistence checks with residual UNKNOWN reported'),
 995: ('REINFECTION_PREVENTION_ENGINE',
       'PREVENTION_ENGINE',
       'close root-cause vector via patch/config/policy/update and verify'),
 996: ('INCIDENT_KNOWLEDGE_COMPILER',
       'KNOWLEDGE_ENGINE',
       'incident→timeline/root cause/IOCs/rules/repair/prevention pattern')}


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
