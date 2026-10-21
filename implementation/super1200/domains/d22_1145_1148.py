#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1145-1148. No certification."""
from __future__ import annotations

SPECS = {1145: ('BEHAVIORAL_NEAREST_NEIGHBOR',
        'ANALYTICS_ENGINE',
        'nearest known behaviors as investigative leads, not family proof'),
 1146: ('NOVELTY_DETECTOR',
        'DETECTOR',
        'out-of-distribution behavior versus historical KB with confidence'),
 1147: ('HISTORICAL_PRIOR_ENGINE',
        'EPISTEMIC_ENGINE',
        'history influences prior belief but cannot override current evidence'),
 1148: ('THREAT_PATTERN_GENERALIZER',
        'KNOWLEDGE_ENGINE',
        'extract defensive commonalities with support counts/provenance')}


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
