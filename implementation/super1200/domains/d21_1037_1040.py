#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1037-1040. No certification."""
from __future__ import annotations

SPECS = {1037: ('READ_ONLY_SAFE_VIEW',
        'SAFE_VIEW_INTERFACE',
        'render/inspect without executing active content; isolation mandatory'),
 1038: ('SANITIZATION_POLICY_ENGINE',
        'POLICY_ENGINE',
        'per-format allowed removals/transcodes/HOLD conditions and versioned policy'),
 1039: ('SANITIZER_SELF_TEST_CORPUS',
        'TEST_DATASET',
        'benign/malicious/malformed cases, hashes, provenance and no unnecessary live malware'),
 1040: ('ARTIFACT_RECOVERY_CERTIFICATION_GATE',
        'ASSURANCE_GATE',
        'clean/recovered claim only after preservation, security, residual-risk, G23/G24 as '
        'applicable')}


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
