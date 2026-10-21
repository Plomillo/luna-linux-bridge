#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 291-294. No certification."""
from __future__ import annotations

SPECS = {291: ('THEMATIC_ANALYSIS',
       'QUALITATIVE_ENGINE',
       'theme→codes→evidence trace and interpretive uncertainty'),
 292: ('CONTENT_ANALYSIS', 'QUALITATIVE_ENGINE', 'unit/coding scheme/counting/inference scope'),
 293: ('DISCOURSE_ANALYSIS',
       'QUALITATIVE_ENGINE',
       'context, speaker, corpus, method and interpretation separated'),
 294: ('NARRATIVE_ANALYSIS',
       'QUALITATIVE_ENGINE',
       'narrative units, chronology, perspective and evidence links')}


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
