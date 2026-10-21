#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 397-400. No certification."""
from __future__ import annotations

SPECS = {397: ('MOBILE_RESOURCE_BUDGET',
       'RESOURCE_POLICY',
       'RAM/CPU/GPU/thermal/battery/storage thresholds per device'),
 398: ('OFFLINE_MOBILE_RUNTIME',
       'CONTINUITY_ENGINE',
       'offline dependency closure, local trust/config/model availability'),
 399: ('ANDROID_UPDATE_ENGINE',
       'UPDATE_ENGINE',
       'package provenance, migration, canary where possible, rollback and app data compatibility'),
 400: ('ANDROID_RECOVERY_TEST',
       'RECOVERY_TEST',
       'backup/checkpoint/reinstall/rollback/postvalidation on emulator/device')}


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
