#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 251-254. No certification."""
from __future__ import annotations

SPECS = {251: ('AUTHORSHIP_PROVENANCE_ENGINE',
       'PROVENANCE_ENGINE',
       'prompt/context/model/tool/source/transformation/output identity'),
 252: ('GENERATION_RECEIPT', 'RECEIPT_SCHEMA', 'immutable generation metadata and digest'),
 253: ('CONTENT_BUILD_MANIFEST',
       'MANIFEST',
       'inputs/transforms/providers/environment/output declarations'),
 254: ('PROMPT_IDENTITY',
       'IDENTITY_PRIMITIVE',
       'prompt/instruction hash, version and source without exposing protected secrets')}


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
