#!/usr/bin/env python3
"""D16 reviewed name-specific material for capabilities 701-704. No certification."""
from __future__ import annotations

SPECS = {701: ('WINDOWS_COMPATIBILITY_FABRIC',
       'COMPATIBILITY_FABRIC',
       'app requirements→API/graphics/runtime/driver profile→benchmark→regression'),
 702: ('WINE_PROVIDER',
       'EXT_COMPATIBILITY_RUNTIME',
       'version/build/prefix/config/runtime provenance; AUTHORITY=NONE'),
 703: ('PROTON_PROVIDER',
       'EXT_COMPATIBILITY_RUNTIME',
       'version/runtime/container/prefix/game linkage'),
 704: ('WIN32_API_COMPATIBILITY_ANALYZER',
       'ANALYZER',
       'required API/DLL/runtime feature inventory')}


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
