#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 425-428. No certification."""
from __future__ import annotations

SPECS = {425: ('DRIVER_COMPATIBILITY_ENGINE',
       'COMPATIBILITY_ENGINE',
       'hardware ID/kernel ABI/firmware/driver version matrix'),
 426: ('SECURE_UPDATE_FABRIC',
       'SECURITY_FABRIC',
       'metadata roles, expiry, rollback/freeze protection, mirrors and root rotation'),
 427: ('TUF_PROVIDER',
       'EXT_SECURITY_LIBRARY',
       'root/targets/snapshot/timestamp roles and metadata verification'),
 428: ('ROLLBACK_PROTECTION',
       'SECURITY_GATE',
       'monotonic trusted version/counters; authorized recovery exception explicit')}


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
