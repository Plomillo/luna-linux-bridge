#!/usr/bin/env python3
"""D16 reviewed name-specific material for capabilities 705-708. No certification."""
from __future__ import annotations

SPECS = {705: ('DIRECTX_TRANSLATION_FABRIC',
       'GRAPHICS_FABRIC',
       'Direct3D version→translation backend→driver requirements'),
 706: ('VULKAN_CAPABILITY_ENGINE',
       'DISCOVERY_ENGINE',
       'device/driver/extensions/features/limits exact'),
 707: ('MESA_PROVIDER', 'EXT_SYSTEM_LIBRARY', 'version/driver/backend/kernel compatibility'),
 708: ('GRAPHICS_DRIVER_MATRIX',
       'COMPATIBILITY_MATRIX',
       'GPU×kernel×driver×Mesa/vendor×Vulkan×app version')}


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
