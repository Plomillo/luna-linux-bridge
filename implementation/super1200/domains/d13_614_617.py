#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 614-617. No certification."""
from __future__ import annotations

SPECS = {614: ('ABSTRACTION_LADDER_ENGINE',
       'PEDAGOGY_ENGINE',
       'map concrete examples↔models↔formalization'),
 615: ('MULTIMODAL_EXPLANATION_ENGINE',
       'CONTENT_ORCHESTRATOR',
       'each modality must add information and retain shared source identity'),
 616: ('ANALOGY_ENGINE', 'CONTENT_ENGINE', 'map similarities and explicit failure limits'),
 617: ('EXAMPLE_PROVENANCE_ENGINE',
       'PROVENANCE_ENGINE',
       'example→source/version/runtime/result links')}


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
