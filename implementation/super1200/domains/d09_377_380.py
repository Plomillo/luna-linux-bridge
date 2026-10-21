#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 377-380. No certification."""
from __future__ import annotations

SPECS = {377: ('ANDROID_PLATFORM_FABRIC',
       'PLATFORM_FABRIC',
       'SDK/NDK/toolchain/device/runtime/build/test/update integrated under one manifest'),
 378: ('ANDROID_SDK_PROVIDER',
       'EXT_PLATFORM_TOOLCHAIN',
       'SDK components/packages pinned with licenses/hashes'),
 379: ('ANDROID_NDK_PROVIDER', 'EXT_PLATFORM_TOOLCHAIN', 'NDK revision/ABI/API level pinned'),
 380: ('KOTLIN_PROVIDER',
       'PROGRAMMING_LANGUAGE_TOOLCHAIN',
       'compiler/runtime/build plugin versions pinned')}


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
