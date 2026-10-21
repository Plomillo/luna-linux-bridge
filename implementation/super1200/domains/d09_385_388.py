#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 385-388. No certification."""
from __future__ import annotations

SPECS = {385: ('APK_BUILD_ENGINE',
       'BUILD_ENGINE',
       'source/deps/SDK/toolchain/manifest/signing state exact'),
 386: ('AAB_BUILD_ENGINE', 'BUILD_ENGINE', 'same provenance as APK plus bundle validation'),
 387: ('APK_SIGNATURE_ENGINE',
       'SIGNING_ENGINE',
       'key custody separate, scheme/version/cert fingerprint and verification'),
 388: ('ANDROID_TEST_LAB',
       'LAB',
       'API/ABI/device matrix, instrumentation, resource and recovery tests')}


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
