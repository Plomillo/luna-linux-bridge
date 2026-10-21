#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 945-948. No certification."""
from __future__ import annotations

SPECS = {945: ('LUNA_DEFENDER_MULTI_SCANNER',
       'ORCHESTRATION_ENGINE',
       'parallel bounded scans, engine independence and normalized findings'),
 946: ('LUNA_DEFENDER_CONSENSUS',
       'CONSENSUS_ENGINE',
       'combine 942–945 while preserving disagreement/uncertainty'),
 947: ('LUNA_DEFENDER_MACHINE_BASELINE',
       'BASELINE',
       'reuse 678/922/929 rather than duplicate machine state'),
 948: ('LUNA_DEFENDER_REPOSITORY_BASELINE',
       'BASELINE',
       'reuse repository integrity/protection state')}


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
