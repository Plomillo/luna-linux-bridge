#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1077-1080. No certification."""
from __future__ import annotations

SPECS = {1077: ('SUBSTITUTE_ROLLBACK',
        'RECOVERY_ENGINE',
        'restore prior authorized provider/state and verify'),
 1078: ('QUARANTINE_DEPENDENCY_RELEASE',
        'CONTINUITY_ENGINE',
        'unblock dependent missions only after substitute/clean provider authorized'),
 1079: ('SUBSTITUTE_LEARNING_ENGINE',
        'KNOWLEDGE_ENGINE',
        'successful/failed substitutions become patterns, not auto-promotions'),
 1080: ('SECURITY_CONTINUITY_GATE',
        'GATE',
        'security action must reduce risk while preserving required availability via governed '
        'alternatives when possible')}


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
