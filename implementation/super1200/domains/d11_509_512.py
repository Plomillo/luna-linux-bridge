#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 509-512. No certification."""
from __future__ import annotations

SPECS = {509: ('SOURCE_DIVERSIFICATION',
       'RESEARCH_POLICY',
       'independent source classes and provenance diversity'),
 510: ('ADVERSARIAL_RESEARCH',
       'RESEARCH_ENGINE',
       'actively seek disconfirming evidence within legal/safe bounds'),
 511: ('COUNTEREVIDENCE_SEARCH',
       'RESEARCH_ENGINE',
       'query opposite/support alternatives and preserve negative evidence'),
 512: ('REPLICATION_ENGINE',
       'VALIDATION_ENGINE',
       're-run same method/data/environment and compare')}


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
