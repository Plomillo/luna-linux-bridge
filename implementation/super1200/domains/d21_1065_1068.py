#!/usr/bin/env python3
"""D21 reviewed name-specific material for capabilities 1065-1068. No certification."""
from __future__ import annotations

SPECS = {1065: ('SUBSTITUTE_SECURITY_TEST',
        'SECURITY_TEST',
        'static/dynamic/dependency/provenance/security-contract tests'),
 1066: ('SUBSTITUTE_ADVERSARIAL_TEST',
        'DEFENSIVE_TEST',
        'safe robustness/abuse testing before promotion'),
 1067: ('SUBSTITUTE_DIFFERENTIAL_TEST',
        'TEST_ENGINE',
        'legitimate original behavior versus candidate under contract fixtures'),
 1068: ('SUBSTITUTE_NON_REGRESSION', 'GATE', 'all required consumers/capabilities preserved')}


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
