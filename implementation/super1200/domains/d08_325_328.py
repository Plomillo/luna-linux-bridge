#!/usr/bin/env python3
"""D08 reviewed name-specific material for capabilities 325-328. No certification."""
from __future__ import annotations

SPECS = {325: ('PALEOGRAPHY_PROVIDER',
       'PROVIDER_INTERFACE',
       'image/source identity, model limits and expert review'),
 326: ('CHRONOLOGY_ENGINE',
       'DOMAIN_ENGINE',
       'event/observed/recorded times, uncertainty and causal distinction'),
 327: ('GEOGRAPHICAL_CONTEXT_ENGINE',
       'DOMAIN_ENGINE',
       'place identity, historical validity and source'),
 328: ('ARCHAEOLOGICAL_EVIDENCE_ADAPTER',
       'DOMAIN_ADAPTER',
       'evidence type/source/date/context and no disciplinary conflation')}


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
