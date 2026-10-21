#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1029-1032. No certification."""
from __future__ import annotations

SPECS = {1029: ('SANITIZATION_DIFF', 'DIFF_ENGINE', 'component/semantic/functional differences explicit'),
 1030: ('SANITIZATION_RECEIPT',
        'RECEIPT',
        'original/result hashes, plan, changes, tools, tests, residual risk'),
 1031: ('SANITIZATION_ROLLBACK',
        'RECOVERY_PATTERN',
        'preserve original quarantined evidence; release state reversible, never overwrite '
        'original'),
 1032: ('SANITIZATION_SANDBOX_VALIDATION',
        'VALIDATION_ENGINE',
        'test sanitized artifact in isolated environment before release')}


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
