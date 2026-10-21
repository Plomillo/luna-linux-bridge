#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 521-524. No certification."""
from __future__ import annotations

SPECS = {521: ('CONCEPT_ALIGNMENT',
       'SEMANTIC_ENGINE',
       'equivalent/related/distinct/conflicting mappings with evidence'),
 522: ('TERMINOLOGY_DISAMBIGUATOR',
       'SEMANTIC_ENGINE',
       'term→discipline/sense/context; lexical ambiguity retained'),
 523: ('EPISTEMIC_BOUNDARY_ENGINE',
       'GOVERNANCE_ENGINE',
       'prevent inference crossing domains without justified bridge'),
 524: ('METHODOLOGICAL_COMPATIBILITY_ENGINE',
       'VALIDATION_ENGINE',
       'method assumptions/units/populations/evidence compatibility')}


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
