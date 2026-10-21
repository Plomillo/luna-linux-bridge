#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 353-356. No certification."""
from __future__ import annotations

SPECS = {353: ('COMPRESSION_DICTIONARY_TRAINING',
       'BUILD_TOOL',
       'training corpus hash, dictionary hash/version and compatibility'),
 354: ('ARCHIVE_INTEGRITY_MANIFEST',
       'MANIFEST',
       'entry path/type/size/hash/chunks/metadata and reconstruction validation'),
 355: ('PARTIAL_EXTRACTION_INTERFACE',
       'INTERFACE',
       'path traversal prevention, limits and exact selected-entry verification'),
 356: ('RANGE_FETCH_INTERFACE',
       'INTERFACE',
       'range validation, ETag/object identity, retries and hashes')}


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
