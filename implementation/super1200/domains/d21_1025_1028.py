#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1025-1028. No certification."""
from __future__ import annotations

SPECS = {1025: ('MALICIOUS_BEHAVIOR_ABSENCE_GATE',
        'SECURITY_GATE',
        'rescans/sandbox demonstrate detected behavior absent within test coverage'),
 1026: ('RESIDUAL_RISK_ANALYZER',
        'RISK_ENGINE',
        'explicit untested/unknown surfaces; CLEAN prohibited when proof insufficient'),
 1027: ('SANITIZED_ARTIFACT_IDENTITY',
        'IDENTITY_PRIMITIVE',
        'sanitized output always new artifact ID/hash/version'),
 1028: ('ORIGINAL_TO_SANITIZED_PROVENANCE',
        'PROVENANCE_RELATION',
        'original→operations→output graph with tool/version/evidence')}


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
