#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 797-800. No certification."""
from __future__ import annotations

SPECS = {797: ('SCHEMA_DIFF_ENGINE', 'DIFF_ENGINE', 'field/type/constraint/default/migration impact'),
 798: ('PERFORMANCE_DIFF_ENGINE',
       'DIFF_ENGINE',
       'matched benchmark deltas with statistical thresholds'),
 799: ('SECURITY_DIFF_ENGINE',
       'DIFF_ENGINE',
       'privilege/network/dependency/attack-surface/policy changes'),
 800: ('CHANGE_RECEIPT',
       'RECEIPT',
       'cause/scope/diff/tests/evidence/result/rollback/actor/authorization')}


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
