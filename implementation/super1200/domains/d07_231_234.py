#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 231-234. No certification."""
from __future__ import annotations

FUNCS = {
    231: ("MULTI_AI_ARCHITECTURE_FACTORY", lambda ctx: {"factory": "multi_ai", "status": "bound", "ctx_hash": hash(str(ctx))} if ctx else {"error": "missing_ctx"}),
    232: ("AGENT_GRAPH_FACTORY", lambda ctx: {"graph": "agent", "nodes": ctx.get("nodes", []) if isinstance(ctx, dict) else [], "status": "bound"}),
    233: ("ROUTER_FACTORY", lambda ctx: {"router": "capability_aware", "routes": ctx.get("routes", []) if isinstance(ctx, dict) else [], "status": "bound"}),
    234: ("ENSEMBLE_ENGINE", lambda ctx: {"ensemble": "weighted", "members": ctx.get("members", []) if isinstance(ctx, dict) else [], "status": "bound"}),
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
