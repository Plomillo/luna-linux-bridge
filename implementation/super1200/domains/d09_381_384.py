#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 381-384. No certification."""
from __future__ import annotations

SPECS = {381: ('JAVA_ANDROID_PROVIDER',
       'PROGRAMMING_LANGUAGE_TOOLCHAIN',
       'JDK vendor/version/toolchain target pinned'),
 382: ('RUST_ANDROID_PROVIDER',
       'PROGRAMMING_LANGUAGE_TOOLCHAIN',
       'rustup/toolchain/target/cargo locks'),
 383: ('CROSS_COMPILE_ARM64', 'TOOLCHAIN_CAPABILITY', 'target triple/sysroot/API/ABI verified'),
 384: ('CROSS_COMPILE_ARMV7', 'TOOLCHAIN_CAPABILITY', 'target triple/sysroot/API/ABI verified')}


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
