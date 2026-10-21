#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1069-1072. No certification."""
from __future__ import annotations

SPECS = {1069: ('SUBSTITUTE_UNCERTAINTY_REPORT',
        'REPORT_ARTIFACT',
        'explicit unproven equivalence/security/performance areas'),
 1070: ('SUBSTITUTE_CANDIDATE_IDENTITY',
        'IDENTITY_PRIMITIVE',
        'new provider/candidate identity; never silently replaces original'),
 1071: ('SUBSTITUTE_PRECOMMIT_GATE',
        'GATE',
        'all mandatory candidate tests/evidence complete before any activation attempt'),
 1072: ('SUBSTITUTE_CHECKPOINT',
        'CHECKPOINT',
        'verified prior state/checkpoint and rollback target')}


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
