#!/usr/bin/env python3
"""D09 reviewed name-specific material for capabilities 365-368. No certification."""
from __future__ import annotations

SPECS = {365: ('REMOTE_ARROW', 'DATA_INTERFACE', 'schema and transport identity, zero-copy only when safe'),
 366: ('STREAMING_DATASET_PROVIDER',
       'DATA_PROVIDER_INTERFACE',
       'ordered/sharded stream, restart cursor, source version and sample provenance'),
 367: ('PARTIAL_TAR_READER', 'ARCHIVE_LIBRARY', 'index/range access and path traversal safeguards'),
 368: ('SHARD_INDEX', 'INDEX', 'shard identity, ranges, records, hashes and version')}


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
