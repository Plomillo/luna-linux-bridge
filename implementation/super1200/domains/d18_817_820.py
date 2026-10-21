#!/usr/bin/env python3
"""D18 reviewed name-specific material for capabilities 817-820. No certification."""
from __future__ import annotations

SPECS = {817: ('MIGRATION_REVERSIBILITY_ANALYZER',
       'RISK_ENGINE',
       'identify irreversible effects and valid rollback route'),
 818: ('MIGRATION_CHECKPOINT',
       'CHECKPOINT_ENGINE',
       'use recovery checkpoint identity/hash and restore oracle'),
 819: ('MIGRATION_POSTVALIDATION',
       'VALIDATION_ENGINE',
       'data invariants, consumers, performance and no-regression after migration'),
 820: ('MIGRATION_RECEIPT',
       'RECEIPT',
       'source/target/plan/actor/checkpoint/tests/result/rollback refs')}


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
