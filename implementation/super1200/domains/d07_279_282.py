#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 279-282. No certification."""
from __future__ import annotations

SPECS = {279: ('TIME_SERIES_ENGINE',
       'ANALYSIS_ENGINE',
       'time index, stationarity/seasonality assumptions, leakage prevention'),
 280: ('SURVIVAL_ANALYSIS',
       'ANALYSIS_ENGINE',
       'censoring/event definitions, model assumptions and uncertainty'),
 281: ('MONTE_CARLO_ENGINE',
       'SIMULATION_ENGINE',
       'seed/distribution/sample count/convergence and reproducibility'),
 282: ('OPTIMIZATION_ENGINE',
       'MATHEMATICAL_ENGINE',
       'objective/constraints/solver/version/tolerances and feasibility evidence')}


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
