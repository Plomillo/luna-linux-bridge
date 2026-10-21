#!/usr/bin/env python3
"""D16 reviewed name-specific material for capabilities 709-712. No certification."""
from __future__ import annotations

SPECS = {709: ('GAME_COMPATIBILITY_KB',
       'KNOWLEDGE_BASE',
       'game/build/provider/config/hardware/result provenance'),
 710: ('GAME_PROFILE_ENGINE',
       'PROFILE_ENGINE',
       'per-title runtime/graphics/input/resource settings versioned'),
 711: ('FRAME_TIME_ANALYZER',
       'PERFORMANCE_ANALYZER',
       'distribution/percentiles/pacing/stutter, not average FPS only'),
 712: ('SHADER_STUTTER_ANALYZER',
       'PERFORMANCE_ANALYZER',
       'compile/cache events correlated with frame-time spikes')}


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
