#!/usr/bin/env python3
"""D16 reviewed name-specific material for capabilities 713-716. No certification."""
from __future__ import annotations

SPECS = {713: ('CPU_GPU_BOTTLENECK_CLASSIFIER',
       'CLASSIFIER',
       'utilization/frame-time/counters and UNKNOWN when inconclusive'),
 714: ('GAME_MEMORY_ANALYZER', 'PERFORMANCE_ANALYZER', 'RAM/VRAM/page/cache pressure and leaks'),
 715: ('GAME_IO_ANALYZER', 'PERFORMANCE_ANALYZER', 'asset reads/latency/cache/storage bottlenecks'),
 716: ('GAME_CONFIGURATION_OPTIMIZER',
       'OPTIMIZATION_ENGINE',
       'Pareto quality/performance/latency/power with rollback')}


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
