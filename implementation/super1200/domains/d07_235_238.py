#!/usr/bin/env python3
"""D07 reviewed name-specific material for capabilities 235-238. No certification."""
from __future__ import annotations

FUNCS = {
    235: ("DEBATE_ENGINE", lambda ctx: {"debate": "structured", "rounds": ctx.get("rounds", 1) if isinstance(ctx, dict) else 1, "status": "bound"}),
    236: ("CRITIC_ENGINE", lambda ctx: {"critic": "adversarial", "score": 0.0, "status": "bound"}),
    237: ("JUDGE_ENGINE", lambda ctx: {"judge": "consensus", "decision": "pending", "status": "bound"}),
    238: ("CONSENSUS_ENGINE", lambda ctx: {"consensus": "majority", "threshold": 0.5, "status": "bound"}),
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
