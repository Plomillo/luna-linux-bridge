#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 389-392. No certification."""
from __future__ import annotations

SPECS = {389: ('EMULATOR_PROVIDER',
       'EXT_PLATFORM_RUNTIME',
       'system image hash/API/device config/snapshot isolation'),
 390: ('ADB_PROVIDER',
       'EXT_BINARY_TOOL',
       'device identity, command allowlist, authorization and no silent host mutation'),
 391: ('DEVICE_CAPABILITY_DISCOVERY',
       'DISCOVERY_ENGINE',
       'hardware/OS/ABI/features/resources from observed state'),
 392: ('ANDROID_PERFORMANCE_PROFILER',
       'PROFILER',
       'CPU/GPU/RAM/battery traces tied to build/device identity')}


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
