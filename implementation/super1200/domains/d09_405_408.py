#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 405-408. No certification."""
from __future__ import annotations

SPECS = {405: ('SYSTEMD_PROVIDER',
       'EXT_OS_COMPONENT',
       'unit files, sandboxing, resource controls and rollback'),
 406: ('INITRAMFS_FACTORY', 'FACTORY', 'module/file manifest, hooks, hashes and boot test'),
 407: ('ROOTFS_FACTORY',
       'FACTORY',
       'filesystem/package manifest, permissions, ownership and hash tree'),
 408: ('BUILDROOT_PROVIDER',
       'EXT_OS_BUILD_TOOLCHAIN',
       'release/config/package hashes/toolchain provenance')}


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
