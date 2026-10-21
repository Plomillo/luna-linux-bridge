#!/usr/bin/env python3
"""D12 reviewed name-specific material for capabilities 535-538. No certification."""
from __future__ import annotations

SPECS = {535: ('MEMORY_PRESSURE_SIMULATOR',
       'SIMULATOR',
       'bounded memory limits, OOM behavior and host safeguards'),
 536: ('CPU_PRESSURE_SIMULATOR', 'SIMULATOR', 'bounded CPU saturation and scheduling observations'),
 537: ('CLOCK_DRIFT_SIMULATOR',
       'SIMULATOR',
       'no host clock mutation by default; simulated time dependencies'),
 538: ('DEPENDENCY_FAILURE_SIMULATOR',
       'SIMULATOR',
       'unavailable/slow/corrupt upstream scenarios by declared dependency')}


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
