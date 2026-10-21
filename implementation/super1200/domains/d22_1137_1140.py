#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1137-1140. No certification."""
from __future__ import annotations

SPECS = {1137: ('DEFENSE_EVASION_KB',
        'KNOWLEDGE_BASE',
        'evasion indicators/detection gaps/mitigations for defender improvement only'),
 1138: ('LATERAL_MOVEMENT_KB',
        'KNOWLEDGE_BASE',
        'propagation indicators/detection/containment knowledge'),
 1139: ('COMMAND_CONTROL_INDICATOR_KB',
        'KNOWLEDGE_BASE',
        'C2 indicators/patterns/provenance/expiry and detection mappings'),
 1140: ('IMPACT_PATTERN_KB',
        'KNOWLEDGE_BASE',
        'observed impact categories and recovery/prevention mappings')}


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
