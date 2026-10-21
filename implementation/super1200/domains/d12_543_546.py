#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 543-546. No certification."""
from __future__ import annotations

SPECS = {543: ('PARTIAL_WRITE_SIMULATOR', 'SIMULATOR', 'transaction/journal/crash fixtures on copies'),
 544: ('RECOVERY_TIME_OBJECTIVE',
       'METRIC/POLICY',
       'RTO per capability/domain measured from incidents/tests'),
 545: ('RECOVERY_POINT_OBJECTIVE',
       'METRIC/POLICY',
       'RPO per state/data class and checkpoint frequency'),
 546: ('RESILIENCE_SCORE',
       'METRIC_ENGINE',
       'vector from tested fault coverage/RTO/RPO/recovery success, not self-certification')}


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
