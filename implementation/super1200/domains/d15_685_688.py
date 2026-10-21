#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 685-688. No certification."""
from __future__ import annotations

SPECS = {685: ('CONFIGURATION_REPAIR_ENGINE',
       'REPAIR_ENGINE',
       'semantic config diff, backup, minimal patch, validation and rollback'),
 686: ('PACKAGE_REPAIR_ENGINE',
       'REPAIR_ENGINE',
       'package identity/deps/cache/source verification and reinstall/rollback'),
 687: ('BOOT_REPAIR_ENGINE',
       'REPAIR_ENGINE',
       'offline/checkpoint first; bootloader/initramfs/service repair by diagnosed cause'),
 688: ('FILESYSTEM_REPAIR_ORCHESTRATOR',
       'REPAIR_ORCHESTRATOR',
       'filesystem type/state determines tool; unmount/checkpoint where required; no blind fsck')}


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
