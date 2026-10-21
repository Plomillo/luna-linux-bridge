#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 417-420. No certification."""
from __future__ import annotations

SPECS = {417: ('UEFI_PROVIDER',
       'PLATFORM_STANDARD_PROVIDER',
       'firmware identity, variables access boundary and no uncontrolled writes'),
 418: ('SECURE_BOOT_PROVIDER',
       'SECURITY_PROVIDER',
       'key hierarchy, signed boot chain, enrollment evidence and recovery'),
 419: ('OS_INSTALLER_FACTORY',
       'FACTORY',
       'hardware discovery, disk plan, dry-run, backup/checkpoint, install and rollback evidence'),
 420: ('OS_UPDATE_FRAMEWORK',
       'UPDATE_FABRIC',
       'trusted metadata, staged activation, migration, rollback, health and non-regression')}


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
