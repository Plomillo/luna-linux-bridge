#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 275-278. No certification."""
from __future__ import annotations

SPECS = {275: ('STAN_PROVIDER',
       'PROBABILISTIC_LANGUAGE_TOOLCHAIN',
       'model source/compiler/version/sampler/seeds and diagnostics'),
 276: ('EXPERIMENT_DESIGN_ENGINE',
       'RESEARCH_ENGINE',
       'hypothesis, variables, controls, sampling and analysis plan fixed before data'),
 277: ('POWER_ANALYSIS', 'STATISTICAL_ENGINE', 'effect assumptions, alpha/power/model documented'),
 278: ('CAUSAL_INFERENCE_ENGINE',
       'ANALYSIS_ENGINE',
       'causal graph, assumptions, identification strategy and sensitivity')}


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
