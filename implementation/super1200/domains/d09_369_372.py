#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 369-372. No certification."""
from __future__ import annotations

SPECS = {369: ('CONTENT_DEFINED_CHUNKING',
       'DATA_ENGINE',
       'algorithm/parameters/version and deterministic boundaries'),
 370: ('MERKLE_CHUNK_STORE',
       'CONTENT_STORE',
       'Merkle root/chunk hashes, immutable addressing and proof verification'),
 371: ('DISTRIBUTED_CONTENT_CACHE',
       'CACHE_FABRIC',
       'CAS verification, eviction safety and untrusted-cache handling'),
 372: ('DELTA_TRANSFER', 'TRANSPORT_ENGINE', 'base/target identity and post-apply hash')}


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
