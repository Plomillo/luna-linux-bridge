#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 271-274. No certification."""
from __future__ import annotations

SPECS = {271: ('SCIPY_PROVIDER', 'EXT_LIBRARY', 'package/BLAS/runtime identity and numerical tolerances'),
 272: ('STATSMODELS_PROVIDER',
       'EXT_LIBRARY',
       'model specification, package version and diagnostics'),
 273: ('BAYESIAN_ENGINE',
       'ANALYSIS_ENGINE',
       'priors/likelihood/model/diagnostics/posterior uncertainty explicit'),
 274: ('PYMC_PROVIDER', 'EXT_LIBRARY', 'version/backend/seeds/sampler settings and diagnostics')}


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
