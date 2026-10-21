#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 239-242. No certification."""
from __future__ import annotations

FUNCS = {
    239: ("SPECIALIST_ROUTING", lambda ctx: {"routing": "specialist", "domain": ctx.get("domain") if isinstance(ctx, dict) else None, "status": "bound"}),
    240: ("MODEL_CASCADE", lambda ctx: {"cascade": "ordered", "stages": ctx.get("stages", []) if isinstance(ctx, dict) else [], "status": "bound"}),
    241: ("CONFIDENCE_ROUTING", lambda ctx: {"routing": "confidence", "threshold": 0.7, "status": "bound"}),
    242: ("COST_AWARE_ROUTING", lambda ctx: {"routing": "cost_aware", "budget": ctx.get("budget") if isinstance(ctx, dict) else None, "status": "bound"}),
}

def run(capability_id: int, ctx=None):
    if capability_id not in FUNCS:
        raise ValueError(f"unregistered capability {capability_id}")
    name, fn = FUNCS[capability_id]
    result = fn(ctx)
    result["canonical_name"] = name
    result["capability_id"] = capability_id
    result["certification_granted"] = False
    return result
