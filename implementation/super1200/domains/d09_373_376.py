#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 373-376. No certification."""
from __future__ import annotations

SPECS = {373: ('RSYNC_PROVIDER',
       'EXT_BINARY_TOOL',
       'version, SSH/transport scope, path allowlist and dry-run'),
 374: ('CAS_SYNC', 'SYNC_ENGINE', 'compare content IDs, transfer missing objects, verify root'),
 375: ('RESUMABLE_FETCH',
       'NETWORK_ENGINE',
       'resume offset/object identity/ETag/hash and corrupted partial cleanup'),
 376: ('BANDWIDTH_BUDGET',
       'RESOURCE_POLICY',
       'per-task/host/provider limits and throttling evidence')}


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
