#!/usr/bin/env python3
"""D15 reviewed name-specific material for capabilities 693-696. No certification."""
from __future__ import annotations

SPECS = {693: ('BACKGROUND_ACTIVITY_ANALYZER',
       'ANALYZER',
       'process/service activity, purpose/dependency and user/system ownership'),
 694: ('LATENCY_DIAGNOSTICS',
       'DIAGNOSTIC_ENGINE',
       'scheduler/I/O/network/audio/graphics latency decomposition'),
 695: ('RESOURCE_LEAK_DETECTOR',
       'DETECTOR',
       'longitudinal memory/fd/thread/process growth and reproducible trigger'),
 696: ('BEFORE_AFTER_BENCHMARK_GATE',
       'GATE',
       'matched workload/environment/statistics before accepting optimization')}


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
