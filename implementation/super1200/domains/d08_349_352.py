#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 349-352. No certification."""
from __future__ import annotations

SPECS = {349: ('CHUNKED_ARCHIVE_ENGINE',
       'ARCHIVE_ENGINE',
       'chunk index/hashes/random access and resumability'),
 350: ('STREAMING_COMPRESSION', 'COMPRESSION_ENGINE', 'bounded memory and stream integrity'),
 351: ('SEEKABLE_COMPRESSION',
       'COMPRESSION_ENGINE',
       'seek index integrity and partial decode tests'),
 352: ('DEDUPE_BEFORE_COMPRESSION',
       'DATA_ENGINE',
       'content identity, reference graph and reconstruction proof')}


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
