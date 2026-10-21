#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 598-601. No certification."""
from __future__ import annotations

SPECS = {598: ('RETRIEVAL_PRACTICE_ENGINE',
       'PEDAGOGY_ENGINE',
       'active-recall scheduling linked to objectives'),
 599: ('SPACED_REVIEW_ENGINE',
       'SCHEDULER',
       'review intervals from performance; bounded personalization'),
 600: ('INTERLEAVED_PRACTICE_ENGINE',
       'PEDAGOGY_ENGINE',
       'controlled mixing of skill categories and performance tracking'),
 601: ('WORKED_EXAMPLE_ENGINE',
       'CONTENT_ENGINE',
       'steps, rationale, source/version and correctness validation')}


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
