#!/usr/bin/env python3
"""D13 reviewed name-specific material for capabilities 638-640. No certification."""
from __future__ import annotations

SPECS = {638: ('ACCESSIBILITY_ENGINE',
       'QUALITY_ENGINE',
       'semantic structure, keyboard, contrast metadata, alt text and document accessibility'),
 639: ('MULTILINGUAL_PEDAGOGY_ENGINE',
       'PEDAGOGY_ENGINE',
       'terminology/source/objective alignment across languages'),
 640: ('PEDAGOGICAL_CERTIFICATION_GATE',
       'CERTIFICATION_READINESS_GATE',
       'functional≠teachable; evidence of objectives/examples/assessments/accessibility required; '
       'G24 still separate')}


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
