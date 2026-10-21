#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 401-404. No certification."""
from __future__ import annotations

SPECS = {401: ('OS_FACTORY',
       'OS_FACTORY',
       'manifest-driven source/packages/kernel/rootfs/boot/update/recovery'),
 402: ('KERNEL_BUILD_ENGINE',
       'BUILD_ENGINE',
       'source commit/config/toolchain/patches/modules/reproducibility'),
 403: ('LINUX_KERNEL_PROVIDER',
       'EXT_OS_COMPONENT',
       'version/config/signature/source provenance and hardware compatibility'),
 404: ('INIT_SYSTEM_PROVIDER',
       'PROVIDER_INTERFACE',
       'service lifecycle contract independent of provider')}


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
