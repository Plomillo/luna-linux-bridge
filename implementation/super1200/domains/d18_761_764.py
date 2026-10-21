#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 761-764. No certification."""
from __future__ import annotations

SPECS = {761: ('MAINTENANCE_FABRIC',
       'MAINTENANCE_FABRIC',
       'common maintenance state, planning, change, compatibility, update, evidence and rollback'),
 762: ('MAINTENANCE_REGISTRY',
       'REGISTRY',
       'object owner/criticality/deps/support lifecycle/maintainer contract'),
 763: ('MAINTAINER_INTERFACE',
       'INTERFACE',
       'inspect/check/repair/update/rollback common verbs and receipts'),
 764: ('MAINTENANCE_STATE_MACHINE',
       'STATE_MACHINE',
       'HEALTHY→DEGRADED→REQUIRED→REPAIRING→VALIDATING→HEALTHY/HOLD/ROLLBACK')}


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
