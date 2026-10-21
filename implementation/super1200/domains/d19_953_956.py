#!/usr/bin/env python3
"""D19 reviewed name-specific material for capabilities 953-956. No certification."""
from __future__ import annotations

SPECS = {953: ('LUNA_DEFENDER_FALSE_NEGATIVE_GATE',
       'GATE',
       'known threat corpus coverage and missed-behavior review'),
 954: ('LUNA_DEFENDER_ADVERSARIAL_EVALUATION',
       'DEFENSIVE_TEST_ENGINE',
       'safe laboratory evasion/resilience evaluation, no offensive deployment'),
 955: ('LUNA_DEFENDER_SELF_AUDIT',
       'AUDIT_ENGINE',
       'own deps/privileges/rules/update path/provider risk; cannot self-certify'),
 956: ('LUNA_DEFENDER_SELF_UPDATE',
       'UPDATE_ENGINE',
       'use 821–840; signed/provenance-gated, canary and rollback')}


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
