#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 873-876. No certification."""
from __future__ import annotations

SPECS = {873: ('SECURITY_HYPOTHESIS_ENGINE',
       'EPISTEMIC_ENGINE',
       'malicious/benign/alternative hypotheses until discriminating evidence'),
 874: ('SECURITY_CONSENSUS_ENGINE',
       'CONSENSUS_ENGINE',
       'combine independent detectors with provenance and calibrated confidence'),
 875: ('SECURITY_DISAGREEMENT_ENGINE',
       'CONFLICT_ENGINE',
       'retain detector disagreements and trigger additional evidence'),
 876: ('FALSE_POSITIVE_REGISTRY',
       'REGISTRY',
       'object/rule/version/context and correction evidence')}


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
