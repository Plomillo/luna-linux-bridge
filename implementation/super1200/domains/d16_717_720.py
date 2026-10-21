#!/usr/bin/env python3
"""D16 reviewed name-specific material for capabilities 717-720. No certification."""
from __future__ import annotations

SPECS = {717: ('GAMESCOPE_PROVIDER',
       'EXT_GRAPHICS_RUNTIME',
       'version/backend/session/options and fallback'),
 718: ('GAME_REGRESSION_BENCHMARK',
       'BENCHMARK_ENGINE',
       'frozen scenes/workloads across provider/config changes'),
 719: ('COMPATIBILITY_PATCH_FACTORY',
       'FACTORY',
       'patch only after evidenced gap; upstream applicability, tests, rollback'),
 720: ('WINE_EVOLUTION_LAB',
       'LAB',
       'isolated experiments, upstream comparison and no fork unless gap demonstrated')}


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
