#!/usr/bin/env python3
"""D11 reviewed name-specific material for capabilities 513-516. No certification."""
from __future__ import annotations

SPECS = {513: ('INDEPENDENT_REPLICATION',
       'G23_SUPPORT_ENGINE',
       'independent actor/environment where required; no shared hidden state'),
 514: ('LITERATURE_REVIEW_ENGINE',
       'RESEARCH_ENGINE',
       'query/selection/source matrix and synthesis trace'),
 515: ('SYSTEMATIC_REVIEW_ENGINE',
       'RESEARCH_ENGINE',
       'predefined protocol, inclusion/exclusion, search log and bias assessment'),
 516: ('META_ANALYSIS_ENGINE',
       'STATISTICAL_ENGINE',
       'effect harmonization, heterogeneity, publication bias and model assumptions')}


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
