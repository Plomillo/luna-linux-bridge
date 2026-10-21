#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 413-416. No certification."""
from __future__ import annotations

SPECS = {413: ('APT_REPOSITORY_PROVIDER',
       'EXT_PACKAGE_MANAGER_PROVIDER',
       'sources pinned, signatures, snapshot/repo identity and dependency resolution'),
 414: ('FILESYSTEM_LAYOUT_ENGINE',
       'OS_ENGINE',
       'paths/permissions/ownership/mount semantics and migration rules'),
 415: ('BOOTLOADER_ENGINE',
       'BOOT_ENGINE',
       'boot entries, kernel/initramfs identities, fallback entry and recovery path'),
 416: ('GRUB_PROVIDER',
       'EXT_OS_COMPONENT',
       'version/config/install target and fallback boot verification')}


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
