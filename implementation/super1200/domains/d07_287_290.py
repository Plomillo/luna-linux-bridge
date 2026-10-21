#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 287-290. No certification."""
from __future__ import annotations

SPECS = {287: ('CORPUS_MANAGER',
       'DATA_MANAGER',
       'document identity, consent/license, metadata, versions and access'),
 288: ('INTERVIEW_TRANSCRIPTION',
       'WORKFLOW',
       'audio identity, transcript alignment, speaker uncertainty and correction history'),
 289: ('CODING_ENGINE',
       'QUALITATIVE_ENGINE',
       'code application linked to exact excerpts and coder identity'),
 290: ('CODEBOOK_REGISTRY',
       'REGISTRY',
       'code definition, inclusion/exclusion, examples, version and supersession')}


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
