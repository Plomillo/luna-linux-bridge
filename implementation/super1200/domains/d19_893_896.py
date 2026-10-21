#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 893-896. No certification."""
from __future__ import annotations

SPECS = {893: ('DOCUMENT_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'macros/actions/embeddings/links parsed safely; malformed document limits'),
 894: ('ARCHIVE_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'depth/size/ratio/file-count limits and nested provenance'),
 895: ('EXECUTABLE_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'headers/imports/sections/signatures/metadata and sandbox escalation'),
 896: ('MEMORY_MALWARE_ANALYZER',
       'DEFENSIVE_ANALYZER',
       'read-only acquisition, host authorization, process/memory identity')}


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
