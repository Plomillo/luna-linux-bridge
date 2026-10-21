#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 345-348. No certification."""
from __future__ import annotations

SPECS = {345: ('TEXT_CORPUS_COMPRESSION', 'DOMAIN_ENGINE', 'encoding/normalization/seek needs preserved'),
 346: ('SOURCE_TREE_COMPRESSION',
       'DOMAIN_ENGINE',
       'permissions/symlinks/git metadata policy and reconstruction tests'),
 347: ('BINARY_COMPRESSION',
       'DOMAIN_ENGINE',
       'executable/library integrity and signature implications'),
 348: ('SOLID_ARCHIVE_ENGINE',
       'ARCHIVE_ENGINE',
       'solid grouping, recovery cost, memory budget and manifest')}


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
