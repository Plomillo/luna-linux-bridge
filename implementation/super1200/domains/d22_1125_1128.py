#!/usr/bin/env python3
"""D22 reviewed name-specific material for capabilities 1125-1128. No certification."""
from __future__ import annotations

SPECS = {1125: ('MALWARE_VARIANT_GRAPH', 'GRAPH', 'sample/family variant relationships with evidence'),
 1126: ('MALWARE_LINEAGE_ENGINE',
        'ANALYSIS_ENGINE',
        'lineage hypotheses only where source/behavior/code evidence supports them'),
 1127: ('MALWARE_TIMELINE_ENGINE',
        'TIMELINE_ENGINE',
        'first-seen/observed evolution with temporal uncertainty'),
 1128: ('MALWARE_BEHAVIOR_KB',
        'KNOWLEDGE_BASE',
        'behaviors tied to evidence/families/platforms/time')}


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
